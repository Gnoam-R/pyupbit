import time
import logging
from typing import Dict, List, Optional
from datetime import datetime
import schedule
import concurrent.futures
from threading import Lock

from .market_data import MarketDataProvider
from .technical_analysis import TechnicalAnalyzer
from ..strategies.technical_strategy import TechnicalTradingStrategy
from ..utils.config import TradingConfig
from ..utils.format_helper import format_currency, format_percentage, format_profit_rate

logger = logging.getLogger(__name__)


class MultiCoinTradingEngine:
    """다중 코인 트레이딩 엔진"""
    
    def __init__(self, coin_symbols: List[str], asset_manager, trade_executor, is_test_mode: bool = False):
        self.coin_symbols = coin_symbols
        self.asset_manager = asset_manager
        self.trade_executor = trade_executor
        self.is_test_mode = is_test_mode
        self.running = False
        
        # 설정 관리
        self.config_manager = TradingConfig()
        self.technical_analyzer = TechnicalAnalyzer()
        
        # 각 코인별 엔진 초기화
        self.coin_engines = {}
        self.coin_locks = {}
        
        for coin in coin_symbols:
            self.coin_engines[coin] = {
                'market_data': MarketDataProvider(coin),
                'strategy': TechnicalTradingStrategy(
                    self.config_manager.get_config(), 
                    self.technical_analyzer, 
                    is_test_mode=is_test_mode
                )
            }
            self.coin_locks[coin] = Lock()
        
        # 전체 잠금
        self.global_lock = Lock()
        
        logger.info(f"다중 코인 트레이딩 엔진 초기화 완료: {', '.join(coin_symbols)}")
    
    def get_current_price(self, coin: str) -> Optional[float]:
        """특정 코인의 현재가 조회"""
        return self.coin_engines[coin]['market_data'].get_current_price()
    
    def get_all_current_prices(self) -> Dict[str, float]:
        """모든 코인의 현재가 조회"""
        prices = {}
        for coin in self.coin_symbols:
            price = self.get_current_price(coin)
            if price:
                prices[coin] = price
        return prices
    
    def get_position_info(self, coin: str) -> Dict:
        """특정 코인의 포지션 정보"""
        return self.coin_engines[coin]['strategy'].get_position_manager().get_position_info()
    
    def get_all_positions(self) -> Dict[str, Dict]:
        """모든 코인의 포지션 정보"""
        positions = {}
        for coin in self.coin_symbols:
            positions[coin] = self.get_position_info(coin)
        return positions
    
    def get_statistics(self, coin: str) -> Dict:
        """특정 코인의 거래 통계"""
        return self.coin_engines[coin]['strategy'].get_position_manager().get_statistics()
    
    def get_all_statistics(self) -> Dict[str, Dict]:
        """모든 코인의 거래 통계"""
        stats = {}
        for coin in self.coin_symbols:
            stats[coin] = self.get_statistics(coin)
        return stats
    
    def get_combined_statistics(self) -> Dict:
        """통합 통계 정보"""
        all_stats = self.get_all_statistics()
        
        total_trades = sum(stats['total_trades'] for stats in all_stats.values())
        total_wins = sum(stats['win_count'] for stats in all_stats.values())
        total_profit = sum(stats['total_profit'] for stats in all_stats.values())
        
        win_rate = (total_wins / max(1, total_trades)) * 100
        avg_profit = total_profit / max(1, total_trades)
        
        return {
            'total_trades': total_trades,
            'win_count': total_wins,
            'loss_count': total_trades - total_wins,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_profit_per_trade': avg_profit
        }
    
    def trading_loop_single_coin(self, coin: str):
        """단일 코인 트레이딩 루프"""
        try:
            with self.coin_locks[coin]:
                engine = self.coin_engines[coin]
                current_price = engine['market_data'].get_current_price()
                
                if not current_price:
                    return
                
                # 손절/익절 확인
                strategy = engine['strategy']
                stop_action = strategy.check_stop_loss_take_profit(current_price)
                
                if stop_action:
                    position = strategy.get_position_manager().get_position_info()
                    if self.execute_sell_order(coin, current_price, position, stop_action):
                        return
                
                # OHLCV 데이터 조회
                df = engine['market_data'].get_ohlcv_data("minute5", 100)
                if df is None or len(df) < 50:
                    return
                
                # 기술적 지표 계산
                indicators = strategy.calculate_technical_indicators(df)
                if not indicators:
                    return
                
                # 매매 신호 판단
                position = strategy.get_position_manager().get_position_info()
                
                if not position["is_holding"]:
                    # 매수 신호 확인
                    if strategy.generate_buy_signal(df, indicators):
                        # 전체 잠금으로 동시 매수 방지
                        with self.global_lock:
                            if self.can_buy_more_coins():
                                self.execute_buy_order(coin, current_price)
                else:
                    # 매도 신호 확인
                    if strategy.generate_sell_signal(df, indicators):
                        self.execute_sell_order(coin, current_price, position, "signal")
                        
        except Exception as e:
            logger.error(f"{coin} 트레이딩 루프 오류: {e}")
    
    def can_buy_more_coins(self) -> bool:
        """더 많은 코인을 매수할 수 있는지 확인"""
        # 현재 보유 중인 코인 수 확인
        holding_count = sum(1 for coin in self.coin_symbols 
                           if self.get_position_info(coin)["is_holding"])
        
        # 최대 동시 보유 코인 수 제한 (설정에서 가져올 수 있음)
        max_concurrent_holdings = min(3, len(self.coin_symbols))  # 최대 3개 또는 전체 코인 수
        
        return holding_count < max_concurrent_holdings
    
    def execute_buy_order(self, coin: str, current_price: float) -> bool:
        """매수 주문 실행"""
        try:
            config = self.config_manager.get_config()
            
            # 실제 매매에서는 잔고 확인
            if not self.is_test_mode:
                if not self.asset_manager.check_minimum_balance(config["min_order_amount"]):
                    logger.warning(f"🚫 {coin} 매수 불가: 잔고 부족")
                    return False
            
            # 매수 실행
            result = self.trade_executor.execute_buy_order(current_price, config, self.asset_manager)
            
            if result:
                # 포지션 매니저에 기록
                buy_amount = self.asset_manager.get_balance("KRW") * config["buy_ratio"]
                buy_volume = buy_amount / current_price
                
                strategy = self.coin_engines[coin]['strategy']
                strategy.get_position_manager().open_position(current_price, buy_volume)
                
                logger.info(f"✅ {coin} 매수 완료: {format_currency(current_price)}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"{coin} 매수 주문 오류: {e}")
            return False
    
    def execute_sell_order(self, coin: str, current_price: float, position: Dict, reason: str) -> bool:
        """매도 주문 실행"""
        try:
            config = self.config_manager.get_config()
            
            # 매도 실행
            result = self.trade_executor.execute_sell_order(current_price, config, position, self.asset_manager)
            
            if result:
                # 포지션 매니저에 기록
                sell_volume = position["buy_amount"] * config["sell_ratio"]
                actual_balance = self.asset_manager.get_balance(coin)
                
                if sell_volume > actual_balance:
                    sell_volume = actual_balance
                
                strategy = self.coin_engines[coin]['strategy']
                strategy.get_position_manager().close_position(current_price, sell_volume, actual_balance, reason)
                
                logger.info(f"✅ {coin} 매도 완료: {format_currency(current_price)} ({reason})")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"{coin} 매도 주문 오류: {e}")
            return False
    
    def print_status(self):
        """현재 상태 출력"""
        try:
            print("=" * 100)
            print(f"{'[테스트 모드]' if self.is_test_mode else ''}다중 코인 트레이딩 현황 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 100)
            
            # 전체 통계
            combined_stats = self.get_combined_statistics()
            print(f"📊 전체 통계:")
            print(f"   총 거래 수: {combined_stats['total_trades']}")
            if combined_stats['total_trades'] > 0:
                print(f"   승률: {combined_stats['win_count']}/{combined_stats['total_trades']} ({format_percentage(combined_stats['win_rate'])})")
                print(f"   총 수익: {format_currency(combined_stats['total_profit'])}")
            
            # 각 코인별 현황
            prices = self.get_all_current_prices()
            positions = self.get_all_positions()
            
            print(f"\n💰 코인별 현황:")
            for coin in self.coin_symbols:
                price = prices.get(coin, 0)
                position = positions.get(coin, {})
                stats = self.get_statistics(coin)
                
                status = "보유중" if position.get("is_holding", False) else "대기중"
                
                info = f"   {coin}: {format_currency(price)} ({status})"
                
                if position.get("is_holding", False):
                    profit_rate = (price - position["buy_price"]) / position["buy_price"]
                    info += f" - 수익률: {format_profit_rate(profit_rate)}"
                
                if stats['total_trades'] > 0:
                    info += f" [거래: {stats['total_trades']}회, 수익: {format_currency(stats['total_profit'])}]"
                
                print(info)
            
            # 계정 정보
            if hasattr(self.asset_manager, 'get_account_info'):
                account_info = self.asset_manager.get_account_info()
                if account_info:
                    print(f"\n💳 계정 정보:")
                    print(f"   원화 잔고: {format_currency(account_info.get('krw_balance', 0))}")
                    
                    # 보유 코인 잔고
                    for coin in self.coin_symbols:
                        balance = self.asset_manager.get_balance(coin)
                        if balance > 0:
                            print(f"   {coin} 잔고: {balance:.8f}")
            
            print("=" * 100)
            
        except Exception as e:
            logger.error(f"상태 출력 오류: {e}")
    
    def start_trading(self):
        """자동 매매 시작"""
        self.running = True
        mode_str = "테스트 모드" if self.is_test_mode else "실제 모드"
        logger.info(f"🚀 다중 코인 자동 매매 시작 - {mode_str}")
        logger.info(f"💎 대상 코인: {', '.join(self.coin_symbols)}")
        
        # 실제 매매에서는 잔고 확인
        if not self.is_test_mode:
            config = self.config_manager.get_config()
            if not self.asset_manager.check_minimum_balance(config["min_order_amount"]):
                logger.error("🚫 잔고 부족으로 매매를 시작할 수 없습니다")
                return
        
        # 주기적 상태 출력 스케줄
        schedule.every(10).minutes.do(self.print_status)
        
        try:
            while self.running:
                # 스케줄된 작업 실행
                schedule.run_pending()
                
                # 동시 처리를 위한 ThreadPoolExecutor 사용
                with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.coin_symbols)) as executor:
                    futures = []
                    
                    for coin in self.coin_symbols:
                        future = executor.submit(self.trading_loop_single_coin, coin)
                        futures.append(future)
                    
                    # 모든 작업 완료 대기
                    concurrent.futures.wait(futures)
                
                # 대기
                config = self.config_manager.get_config()
                time.sleep(config.get("trading_interval", 60))
                
        except KeyboardInterrupt:
            self.stop_trading()
        except Exception as e:
            logger.error(f"자동 매매 실행 오류: {e}")
            self.stop_trading()
    
    def stop_trading(self):
        """자동 매매 중지"""
        self.running = False
        logger.info("🛑 다중 코인 자동 매매 중지")
        
        # 최종 상태 출력
        self.print_status()