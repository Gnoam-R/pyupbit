import time
import datetime
import logging
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..core.asset_manager import RealAssetManager, VirtualAssetManager
from ..core.asset_allocation import AssetAllocationManager, create_equal_weight_allocation
from ..strategies.multi_coin_strategy import MultiCoinTradingStrategy
from ..executors.trading_executor import RealTradeExecutor, VirtualTradeExecutor
from ..utils.config import TradingConfig
from ..utils.coin_selector import COIN_CONFIG

logger = logging.getLogger(__name__)


class MultiCoinTrader:
    """멀티 코인 트레이더"""
    
    def __init__(self, upbit_client=None, is_test_mode: bool = False, seed_money: float = 1000000):
        """
        Args:
            upbit_client: 업비트 클라이언트 (실제 거래 시 필요)
            is_test_mode: 테스트 모드 여부
            seed_money: 시드머니 (테스트 모드에서만 사용)
        """
        self.is_test_mode = is_test_mode
        self.running = False
        self.supported_coins = list(COIN_CONFIG.keys())
        
        # 설정 로드
        self.config_manager = TradingConfig()
        self.config = self.config_manager.get_config()
        
        # 멀티 코인 전략 초기화
        self.strategy = MultiCoinTradingStrategy(self.config, is_test_mode)
        
        # 자산 매니저 초기화
        if is_test_mode:
            # 테스트 모드: 가상 자산 매니저 사용
            self.asset_managers = {}
            for coin in self.supported_coins:
                self.asset_managers[coin] = VirtualAssetManager(coin, seed_money / len(self.supported_coins))
            
            # 전체 KRW 자산 매니저 (자산 배분용)
            self.main_asset_manager = VirtualAssetManager("KRW", seed_money)
        else:
            # 실제 거래 모드: 실제 자산 매니저 사용
            if upbit_client is None:
                raise ValueError("실제 거래 모드에서는 upbit_client가 필요합니다")
            
            self.asset_managers = {}
            for coin in self.supported_coins:
                self.asset_managers[coin] = RealAssetManager(upbit_client, coin)
            
            self.main_asset_manager = RealAssetManager(upbit_client, "KRW")
        
        # 거래 실행자 초기화
        self.trade_executors = {}
        if is_test_mode:
            for coin in self.supported_coins:
                self.trade_executors[coin] = VirtualTradeExecutor(coin)
        else:
            for coin in self.supported_coins:
                self.trade_executors[coin] = RealTradeExecutor(upbit_client, coin)
        
        # 자산 배분 매니저 초기화 (균등 배분 전략 사용)
        allocation_strategy = create_equal_weight_allocation(self.supported_coins)
        self.allocation_manager = AssetAllocationManager(allocation_strategy, self.config["min_order_amount"])
        
        # 거래 내역 및 통계
        self.trade_history = []
        self.last_status_print = datetime.datetime.now()
        
        mode_text = "테스트 모드" if is_test_mode else "실제 거래 모드"
        logger.info(f"멀티 코인 트레이더 초기화 완료 - {mode_text}")
        logger.info(f"지원 코인: {', '.join(self.supported_coins)}")
    
    def get_current_prices(self) -> Dict[str, float]:
        """모든 코인의 현재가 조회"""
        prices = {}
        for coin in self.supported_coins:
            price = self.strategy.get_current_price_for_coin(coin)
            prices[coin] = price
        return prices
    
    def get_total_krw_balance(self) -> float:
        """전체 KRW 잔고 조회"""
        return self.main_asset_manager.get_balance("KRW")
    
    def execute_buy_order_for_coin(self, coin: str, current_price: float) -> bool:
        """특정 코인 매수 주문 실행"""
        try:
            # 현재 KRW 잔고 조회
            krw_balance = self.get_total_krw_balance()
            if krw_balance < self.config["min_order_amount"]:
                logger.warning(f"KRW 잔고 부족: {krw_balance:,.0f}원")
                return False
            
            # 현재 가격 정보 조회
            current_prices = self.get_current_prices()
            
            # 해당 코인의 배분 금액 계산
            buy_amount = self.allocation_manager.get_buy_amount_for_coin(coin, krw_balance, current_prices)
            
            if buy_amount < self.config["min_order_amount"]:
                logger.warning(f"{coin} 배분 금액 부족: {buy_amount:,.0f}원")
                return False
            
            # 실제 거래 실행
            result = self.trade_executors[coin].execute_buy_order(current_price, {"buy_ratio": buy_amount / krw_balance, **self.config}, self.main_asset_manager)
            
            if result:
                # 포지션 매니저에 포지션 기록
                buy_volume = buy_amount / current_price
                position_manager = self.strategy.get_position_manager_for_coin(coin)
                position_manager.open_position(current_price, buy_volume)
                
                # 거래 내역 기록
                self.trade_history.append({
                    "timestamp": datetime.datetime.now(),
                    "coin": coin,
                    "type": "buy",
                    "price": current_price,
                    "amount": buy_volume,
                    "total_krw": buy_amount,
                    "reason": "signal"
                })
                
                logger.info(f"[{coin}] 매수 완료: {current_price:,.0f}원, {buy_volume:.8f}{coin}, {buy_amount:,.0f}원")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"[{coin}] 매수 주문 오류: {e}")
            return False
    
    def execute_sell_order_for_coin(self, coin: str, current_price: float, reason: str = "signal") -> bool:
        """특정 코인 매도 주문 실행"""
        try:
            position_manager = self.strategy.get_position_manager_for_coin(coin)
            position_info = position_manager.get_position_info()
            
            if not position_info["is_holding"]:
                logger.warning(f"[{coin}] 포지션 없음 - 매도 불가")
                return False
            
            # 실제 거래 실행
            result = self.trade_executors[coin].execute_sell_order(current_price, self.config, position_info, self.asset_managers[coin])
            
            if result:
                # 포지션 매니저에 포지션 정리 기록
                sell_volume = position_info["buy_amount"] * self.config["sell_ratio"]
                position_manager.close_position(current_price, sell_volume, reason)
                
                # 거래 내역 기록
                sell_amount = sell_volume * current_price
                profit = (current_price - position_info["buy_price"]) * sell_volume
                
                self.trade_history.append({
                    "timestamp": datetime.datetime.now(),
                    "coin": coin,
                    "type": "sell",
                    "price": current_price,
                    "amount": sell_volume,
                    "total_krw": sell_amount,
                    "profit": profit,
                    "reason": reason
                })
                
                logger.info(f"[{coin}] 매도 완료: {current_price:,.0f}원, {sell_volume:.8f}{coin}, 수익: {profit:,.0f}원")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"[{coin}] 매도 주문 오류: {e}")
            return False
    
    def process_trading_opportunities(self) -> Dict[str, int]:
        """매매 기회 처리"""
        results = {"buy_executed": 0, "sell_executed": 0, "errors": 0}
        
        try:
            # 매매 기회 분석
            buy_opportunities, sell_opportunities = self.strategy.get_trading_opportunities()
            
            # 매도 기회 우선 처리 (손절/익절 포함)
            for opportunity in sell_opportunities:
                coin = opportunity["coin"]
                price = opportunity["current_price"]
                reason = opportunity["reason"]
                
                if self.execute_sell_order_for_coin(coin, price, reason):
                    results["sell_executed"] += 1
                else:
                    results["errors"] += 1
            
            # 매수 기회 처리
            for opportunity in buy_opportunities:
                coin = opportunity["coin"]
                price = opportunity["current_price"]
                
                if self.execute_buy_order_for_coin(coin, price):
                    results["buy_executed"] += 1
                else:
                    results["errors"] += 1
            
        except Exception as e:
            logger.error(f"매매 기회 처리 오류: {e}")
            results["errors"] += 1
        
        return results
    
    def print_status(self):
        """현재 상태 출력"""
        try:
            portfolio_summary = self.strategy.get_portfolio_summary()
            current_prices = self.get_current_prices()
            
            print("=" * 100)
            print(f"[{'테스트 모드' if self.is_test_mode else '실제 거래'}] 멀티 코인 트레이더 상태 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 100)
            
            # 전체 통계
            print(f"전체 거래 수: {portfolio_summary['total_trades']}")
            print(f"전체 수익: {portfolio_summary['total_profit']:,.0f}원")
            print(f"승률: {portfolio_summary['win_rate']:.1f}% ({portfolio_summary['win_count']}/{portfolio_summary['total_trades']})")
            print(f"활성 포지션: {portfolio_summary['active_positions']}/{len(self.supported_coins)}")
            
            # KRW 잔고
            krw_balance = self.get_total_krw_balance()
            print(f"KRW 잔고: {krw_balance:,.0f}원")
            
            print("\n" + "-" * 100)
            print("코인별 상세 정보:")
            print("-" * 100)
            
            # 각 코인별 상세 정보
            for coin in self.supported_coins:
                detail = portfolio_summary['coin_details'][coin]
                position = detail['position']
                stats = detail['statistics']
                current_price = current_prices.get(coin, 0)
                
                print(f"\n[{coin}] 현재가: {current_price:,.0f}원")
                
                if position['is_holding']:
                    profit_rate = (current_price - position['buy_price']) / position['buy_price'] * 100
                    print(f"  포지션: 보유 중 (매수가: {position['buy_price']:,.0f}원, 수익률: {profit_rate:+.2f}%)")
                    print(f"  보유량: {position['buy_amount']:.8f}{coin}")
                else:
                    print(f"  포지션: 없음")
                
                print(f"  거래 통계: {stats['total_trades']}회, 수익: {stats['total_profit']:,.0f}원")
                if stats['total_trades'] > 0:
                    print(f"  승률: {stats['win_rate']:.1f}% ({stats['win_count']}/{stats['total_trades']})")
            
            print("=" * 100)
            
        except Exception as e:
            logger.error(f"상태 출력 오류: {e}")
    
    def trading_loop(self):
        """메인 트레이딩 루프"""
        try:
            # 매매 기회 처리
            results = self.process_trading_opportunities()
            
            # 결과 로깅
            if results["buy_executed"] > 0 or results["sell_executed"] > 0:
                logger.info(f"매매 실행 완료 - 매수: {results['buy_executed']}, 매도: {results['sell_executed']}")
            
            if results["errors"] > 0:
                logger.warning(f"매매 오류 발생: {results['errors']}건")
            
            # 주기적 상태 출력 (10분마다)
            current_time = datetime.datetime.now()
            if (current_time - self.last_status_print).total_seconds() > 600:  # 10분
                self.print_status()
                self.last_status_print = current_time
            
        except Exception as e:
            logger.error(f"트레이딩 루프 오류: {e}")
    
    def start_trading(self):
        """자동 매매 시작"""
        self.running = True
        mode_text = "테스트 모드" if self.is_test_mode else "실제 거래 모드"
        logger.info(f"멀티 코인 자동 매매 시작 - {mode_text}")
        
        try:
            while self.running:
                self.trading_loop()
                time.sleep(self.config["trading_interval"])
        
        except KeyboardInterrupt:
            self.stop_trading()
        except Exception as e:
            logger.error(f"자동 매매 실행 오류: {e}")
            self.stop_trading()
    
    def stop_trading(self):
        """자동 매매 중지"""
        self.running = False
        logger.info("멀티 코인 자동 매매 중지")
        
        if self.is_test_mode:
            self.print_final_report()
    
    def print_final_report(self):
        """최종 리포트 출력 (테스트 모드에서만)"""
        if not self.is_test_mode:
            return
        
        try:
            portfolio_summary = self.strategy.get_portfolio_summary()
            
            print("\n" + "=" * 100)
            print("최종 멀티 코인 테스트 결과 리포트")
            print("=" * 100)
            
            print(f"총 거래 수: {portfolio_summary['total_trades']}")
            print(f"총 수익: {portfolio_summary['total_profit']:,.0f}원")
            print(f"승률: {portfolio_summary['win_rate']:.1f}%")
            print(f"승리: {portfolio_summary['win_count']}회, 패배: {portfolio_summary['loss_count']}회")
            
            print("\n코인별 최종 결과:")
            print("-" * 50)
            
            for coin in self.supported_coins:
                detail = portfolio_summary['coin_details'][coin]
                stats = detail['statistics']
                position = detail['position']
                
                print(f"\n[{coin}]")
                print(f"  거래 수: {stats['total_trades']}")
                print(f"  수익: {stats['total_profit']:,.0f}원")
                print(f"  승률: {stats['win_rate']:.1f}% ({stats['win_count']}/{stats['total_trades']})")
                
                if position['is_holding']:
                    print(f"  미청산 포지션: {position['buy_amount']:.8f}{coin} (매수가: {position['buy_price']:,.0f}원)")
            
            print("=" * 100)
            
        except Exception as e:
            logger.error(f"최종 리포트 출력 오류: {e}")
    
    def get_portfolio_summary(self) -> Dict:
        """포트폴리오 요약 정보 반환"""
        return self.strategy.get_portfolio_summary()
    
    def get_trade_history(self) -> List[Dict]:
        """거래 내역 반환"""
        return self.trade_history.copy()