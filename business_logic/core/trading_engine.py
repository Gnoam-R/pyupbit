import time
import logging
from typing import Dict, Optional
from datetime import datetime
import schedule

from .market_data import MarketDataProvider
from .technical_analysis import TechnicalAnalyzer
from ..strategies.priority_strategy import PriorityTradingStrategy
from ..utils.config import TradingConfig
from ..utils.format_helper import format_profit_rate, format_currency, format_percentage

logger = logging.getLogger(__name__)


class TradingEngine:
    """통합 트레이딩 엔진"""
    
    def __init__(self, target_coin: str, asset_manager, trade_executor, is_test_mode: bool = False):
        self.target_coin = target_coin
        self.asset_manager = asset_manager
        self.trade_executor = trade_executor
        self.is_test_mode = is_test_mode
        self.running = False
        
        # 비즈니스 로직 모듈 초기화
        self.config_manager = TradingConfig()
        self.market_data = MarketDataProvider(target_coin)
        self.technical_analyzer = TechnicalAnalyzer()
        self.strategy = PriorityTradingStrategy(
            self.config_manager.get_config(), 
            self.technical_analyzer, 
            is_test_mode=is_test_mode
        )
        
        # 저장된 포지션 정보 복원 (가상 모드에서만)
        if is_test_mode and hasattr(asset_manager, 'persistence') and asset_manager.persistence:
            saved_data = asset_manager.persistence.load_balance()
            if saved_data and saved_data.get("position"):
                from .position_manager import PositionManager
                self.strategy.position_manager = PositionManager(saved_data["position"])
        
        logger.info(f"TradingEngine 초기화 완료 - 대상 코인: {target_coin}, 테스트 모드: {is_test_mode}")
    
    def get_current_price(self) -> Optional[float]:
        """현재가 조회"""
        return self.market_data.get_current_price()
    
    def get_position_info(self) -> Dict:
        """포지션 정보 조회"""
        return self.strategy.get_position_manager().get_position_info()
    
    def get_statistics(self) -> Dict:
        """거래 통계 조회"""
        return self.strategy.get_position_manager().get_statistics()
    
    def get_config(self) -> Dict:
        """설정 조회"""
        return self.config_manager.get_config()
    
    def trading_loop(self):
        """메인 트레이딩 루프"""
        try:
            current_price = self.get_current_price()
            if not current_price:
                logger.warning("현재가 조회 실패")
                return
            
            # 손절/익절 확인
            stop_action = self.strategy.check_stop_loss_take_profit(current_price)
            if stop_action:
                stop_info = {'selected_strategy': f'손절/익절 ({stop_action})'}
                self.execute_sell_order(current_price, stop_action, stop_info)
                return
            
            # OHLCV 데이터 조회
            df = self.market_data.get_ohlcv_data("minute5", 100)
            if df is None or len(df) < 50:
                logger.warning("OHLCV 데이터 부족")
                return
            
            # 기술적 지표 계산
            indicators = self.strategy.calculate_technical_indicators(df)
            if not indicators:
                logger.warning("기술적 지표 계산 실패")
                return
            
            # 매매 신호 판단
            position = self.get_position_info()
            if not position["is_holding"]:
                # 매수 신호 확인
                should_buy, buy_info = self.strategy.generate_buy_signal(df, indicators)
                if should_buy:
                    self.execute_buy_order(current_price, buy_info)
            else:
                # 매도 신호 확인
                should_sell, sell_info = self.strategy.generate_sell_signal(df, indicators)
                if should_sell:
                    self.execute_sell_order(current_price, "signal", sell_info)
            
            # 가상 모드에서는 주기적으로 잔고 저장
            if self.is_test_mode and hasattr(self.asset_manager, 'save_balance'):
                self.asset_manager.save_balance(
                    self.get_position_info(),
                    self.get_statistics(),
                    current_price
                )
        
        except Exception as e:
            logger.error(f"트레이딩 루프 오류: {e}")
    
    def execute_buy_order(self, current_price: float, strategy_info: Dict = None) -> bool:
        """매수 주문 실행"""
        config = self.config_manager.get_config()
        result = self.trade_executor.execute_buy_order(current_price, config, self.asset_manager)
        if result:
            # 포지션 매니저에 포지션 오픈 기록
            buy_amount = self.asset_manager.get_balance("KRW") * config["buy_ratio"]
            buy_volume = buy_amount / current_price
            self.strategy.get_position_manager().open_position(current_price, buy_volume)
            
            # 전략 정보 로그 기록
            if strategy_info and 'selected_strategy' in strategy_info:
                strategy_name = self.strategy.strategy_names.get(strategy_info['selected_strategy'], strategy_info['selected_strategy'])
                logger.info(f"🟢 매수 실행 완료 - 사용 전략: {strategy_name}")
        return result
    
    def execute_sell_order(self, current_price: float, reason: str = "signal", strategy_info: Dict = None) -> bool:
        """매도 주문 실행"""
        config = self.config_manager.get_config()
        position = self.get_position_info()
        result = self.trade_executor.execute_sell_order(current_price, config, position, self.asset_manager)
        if result:
            # 포지션 매니저에 포지션 클로즈 기록
            sell_volume = position["buy_amount"] * config["sell_ratio"]
            actual_coin_balance = self.asset_manager.get_balance(self.target_coin)
            if sell_volume > actual_coin_balance:
                sell_volume = actual_coin_balance
            
            self.strategy.get_position_manager().close_position(
                current_price, 
                sell_volume, 
                actual_coin_balance,
                reason
            )
            
            # 전략 정보 로그 기록
            if strategy_info and 'selected_strategy' in strategy_info:
                strategy_name = self.strategy.strategy_names.get(strategy_info['selected_strategy'], strategy_info['selected_strategy'])
                logger.info(f"🔴 매도 실행 완료 - 사용 전략: {strategy_name}")
        return result
    
    def print_status(self):
        """현재 상태 출력"""
        try:
            current_price = self.get_current_price()
            account_info = self.asset_manager.get_account_info()
            position = self.get_position_info()
            stats = self.get_statistics()
            
            if not current_price:
                logger.warning("현재가 조회 실패로 상태 출력 불가")
                return
            
            # 총 자산 가치 계산
            if hasattr(self.asset_manager, 'calculate_total_value'):
                value_info = self.asset_manager.calculate_total_value(current_price)
                total_value = value_info.get("total_value", 0)
                profit_loss = value_info.get("profit_loss", 0)
                profit_rate = value_info.get("profit_rate", 0)
            else:
                total_value = account_info.get("krw_balance", 0)
                profit_loss = 0
                profit_rate = 0
            
            print("=" * 80)
            print(f"{'[테스트 모드]' if self.is_test_mode else ''} 현재 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"현재 가격: {format_currency(current_price)}")
            print(f"원화 잔고: {format_currency(account_info.get('krw_balance', 0))}")
            print(f"{self.target_coin} 잔고: {account_info.get('coin_balance', 0):.8f}{self.target_coin}")
            
            if self.is_test_mode:
                print(f"총 자산 가치: {format_currency(total_value)}")
                print(f"총 수익/손실: {format_currency(profit_loss)} ({format_percentage(profit_rate)})")
            
            if position["is_holding"]:
                current_profit_rate = (current_price - position["buy_price"]) / position["buy_price"]
                print(f"포지션: 보유 중 (매수가: {format_currency(position['buy_price'])}, "
                      f"수익률: {format_profit_rate(current_profit_rate)})")
            else:
                print("포지션: 없음")
            
            print(f"총 거래 수: {stats['total_trades']}")
            if stats['total_trades'] > 0:
                print(f"승률: {stats['win_count']}/{stats['total_trades']} ({format_percentage(stats['win_rate'])})")
                print(f"평균 거래당 수익: {format_currency(stats['avg_profit_per_trade'])}")
            print(f"누적 거래 수익: {format_currency(stats['total_profit'])}")
            
            # 가상 모드에서는 총 수익률도 표시
            if self.is_test_mode and abs(profit_rate) >= 0.01:  # 0.01% 이상만 표시
                print(f"총 수익률: {format_percentage(profit_rate)} (자산 증감: {format_currency(profit_loss)})")
            print("=" * 80)
            
        except Exception as e:
            logger.error(f"상태 출력 오류: {e}")
    
    def start_trading(self):
        """자동 매매 시작"""
        self.running = True
        mode_str = "테스트 모드" if self.is_test_mode else "실제 모드"
        logger.info(f"자동 매매 시작 - {mode_str}")
        
        # 주기적 상태 출력 스케줄
        interval = 5 if self.is_test_mode else 10
        schedule.every(interval).minutes.do(self.print_status)
        
        try:
            while self.running:
                # 스케줄된 작업 실행
                schedule.run_pending()
                
                # 트레이딩 루프 실행
                self.trading_loop()
                
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
        schedule.clear()
        mode_str = "테스트 모드" if self.is_test_mode else "실제 모드"
        logger.info(f"자동 매매 중지 - {mode_str}")