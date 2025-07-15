import time
import datetime
import logging
from typing import Dict, Optional
import schedule
from threading import Thread

from .market_data import MarketDataProvider
from .asset_manager import BaseAssetManager
from .technical_analysis import TechnicalAnalyzer
from ..strategies.technical_strategy import TechnicalTradingStrategy
from ..executors.trading_executor import BaseTradeExecutor
from ..utils.config import TradingConfig
from ..utils.logger import setup_logger

logger = logging.getLogger(__name__)


class TradingEngine:
    """통합 트레이딩 엔진 - 실제/테스트 모드 공통 로직"""
    
    def __init__(self, target_coin: str, asset_manager: BaseAssetManager, 
                 trade_executor: BaseTradeExecutor, is_test_mode: bool = False):
        """
        트레이딩 엔진 초기화
        
        Args:
            target_coin: 대상 코인 심볼
            asset_manager: 자산 관리자 (실제/가상)
            trade_executor: 거래 실행자 (실제/가상)
            is_test_mode: 테스트 모드 여부
        """
        self.target_coin = target_coin
        self.asset_manager = asset_manager
        self.trade_executor = trade_executor
        self.is_test_mode = is_test_mode
        self.running = False
        
        # 공통 모듈 초기화
        self.config_manager = TradingConfig()
        self.market_data = MarketDataProvider(target_coin)
        self.technical_analyzer = TechnicalAnalyzer()
        self.strategy = TechnicalTradingStrategy(
            self.config_manager.get_config(), 
            self.technical_analyzer, 
            is_test_mode=is_test_mode
        )
        
        # 웹소켓 매니저 (실제 모드에서만 사용)
        self.websocket_manager = None
        
        mode = "테스트" if is_test_mode else "실제"
        logger.info(f"{mode} 모드 트레이딩 엔진 초기화 완료 - 대상 코인: {target_coin}")
    
    def get_account_info(self) -> Optional[Dict]:
        """계정 정보 조회"""
        return self.asset_manager.get_account_info()
    
    def get_current_price(self) -> Optional[float]:
        """현재가 조회"""
        return self.market_data.get_current_price()
    
    def trading_loop(self):
        """메인 트레이딩 루프"""
        try:
            current_price = self.get_current_price()
            if not current_price:
                return
            
            # 손절/익절 확인
            stop_action = self.strategy.check_stop_loss_take_profit(current_price)
            if stop_action:
                self.execute_sell_order(current_price, stop_action)
                return
            
            # OHLCV 데이터 조회
            df = self.market_data.get_ohlcv_data("minute5", 100)
            if df is None or len(df) < 50:
                return
            
            # 기술적 지표 계산
            indicators = self.strategy.calculate_technical_indicators(df)
            if not indicators:
                return
            
            # 매매 신호 판단
            position = self.strategy.get_position_manager().get_position_info()
            if not position["is_holding"]:
                # 매수 신호 확인
                if self.strategy.generate_buy_signal(df, indicators):
                    self.execute_buy_order(current_price)
            else:
                # 매도 신호 확인
                if self.strategy.generate_sell_signal(df, indicators):
                    self.execute_sell_order(current_price, "signal")
        
        except Exception as e:
            logger.error(f"트레이딩 루프 오류: {e}")
    
    def execute_buy_order(self, current_price: float) -> bool:
        """매수 주문 실행"""
        config = self.config_manager.get_config()
        
        # 매수 전 계산
        if hasattr(self.asset_manager, 'get_balance'):
            krw_balance = self.asset_manager.get_balance("KRW")
        else:
            account_info = self.asset_manager.get_account_info()
            krw_balance = account_info.get("krw_balance", 0) if account_info else 0
            
        buy_amount = krw_balance * config["buy_ratio"]
        buy_volume = buy_amount / current_price
        
        # 거래 실행
        result = self.trade_executor.execute_buy_order(current_price, config, self.asset_manager)
        
        if result:
            # 포지션 매니저에 포지션 오픈 기록 (실제 거래된 정보로)
            self.strategy.get_position_manager().open_position(current_price, buy_volume)
        
        return result
    
    def execute_sell_order(self, current_price: float, reason: str = "signal") -> bool:
        """매도 주문 실행"""
        config = self.config_manager.get_config()
        position = self.strategy.get_position_manager().get_position_info()
        
        # 매도 전 계산
        sell_volume = position["buy_amount"] * config["sell_ratio"]
        
        # 실제 보유량 체크 (가상 모드에서)
        if hasattr(self.asset_manager, 'get_balance'):
            actual_balance = self.asset_manager.get_balance(self.target_coin)
            if sell_volume > actual_balance:
                sell_volume = actual_balance
                logger.warning(f"매도 수량 조정: {sell_volume:.8f}{self.target_coin} (보유량 전량)")
        
        # 거래 실행
        result = self.trade_executor.execute_sell_order(current_price, config, position, self.asset_manager)
        
        if result:
            # 포지션 매니저에 포지션 클로즈 기록 (실제 거래된 수량으로)
            self.strategy.get_position_manager().close_position(current_price, sell_volume, reason)
        
        return result
    
    def print_status(self):
        """현재 상태 출력"""
        try:
            current_price = self.get_current_price()
            account_info = self.get_account_info()
            position = self.strategy.get_position_manager().get_position_info()
            stats = self.strategy.get_position_manager().get_statistics()
            
            if not current_price or not account_info:
                return
            
            mode_prefix = "[테스트]" if self.is_test_mode else ""
            
            print("=" * 80)
            print(f"{mode_prefix} 현재 시간: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"현재 가격: {current_price:,.0f}원")
            print(f"원화 잔고: {account_info.get('krw_balance', 0):,.0f}원")
            print(f"{self.target_coin} 잔고: {account_info.get('coin_balance', 0):.8f}{self.target_coin}")
            
            # 가상 모드에서만 총 자산 정보 표시
            if self.is_test_mode and hasattr(self.asset_manager, 'calculate_total_value'):
                value_info = self.asset_manager.calculate_total_value(current_price)
                print(f"총 자산 가치: {value_info['total_value']:,.0f}원")
                print(f"총 수익/손실: {value_info['profit_loss']:,.0f}원 ({value_info['profit_rate']:.2f}%)")
            
            if position["is_holding"]:
                profit_rate = (current_price - position["buy_price"]) / position["buy_price"]
                print(f"포지션: 보유 중 (매수가: {position['buy_price']:,.0f}원, "
                      f"수익률: {profit_rate:.2%})")
            else:
                print("포지션: 없음")
            
            print(f"총 거래 수: {stats['total_trades']}")
            print(f"승률: {stats['win_count']}/{stats['total_trades']} ({stats['win_rate']:.1f}%)")
            print(f"총 수익: {stats['total_profit']:,.0f}원")
            print("=" * 80)
            
        except Exception as e:
            logger.error(f"상태 출력 오류: {e}")
    
    def start_websocket_monitoring(self):
        """웹소켓 실시간 모니터링 시작 (실제 모드에서만)"""
        if self.is_test_mode:
            return
            
        try:
            from pyupbit import WebSocketManager
            
            def websocket_handler():
                self.websocket_manager = WebSocketManager("ticker", [f"KRW-{self.target_coin}"])
                while self.running:
                    try:
                        data = self.websocket_manager.get()
                        if data != 'ConnectionClosedError':
                            # 실시간 데이터 처리
                            current_price = data.get('trade_price', 0)
                            change_rate = data.get('signed_change_rate', 0) * 100
                            
                            # 급격한 가격 변동 알림
                            if abs(change_rate) > 2:  # 2% 이상 변동
                                logger.warning(f"급격한 가격 변동 감지: {change_rate:.2f}%")
                    except Exception as e:
                        logger.error(f"웹소켓 데이터 처리 오류: {e}")
                        time.sleep(1)
            
            websocket_thread = Thread(target=websocket_handler, daemon=True)
            websocket_thread.start()
            logger.info("웹소켓 모니터링 시작")
            
        except Exception as e:
            logger.error(f"웹소켓 모니터링 시작 오류: {e}")
    
    def start_trading(self):
        """자동 매매 시작"""
        self.running = True
        mode = "테스트" if self.is_test_mode else "실제"
        logger.info(f"{mode} 모드 자동 매매 시작")
        
        # 웹소켓 모니터링 시작 (실제 모드에서만)
        self.start_websocket_monitoring()
        
        # 주기적 상태 출력 스케줄
        interval = 5 if self.is_test_mode else 10
        schedule.every(interval).minutes.do(self.print_status)
        
        try:
            config = self.config_manager.get_config()
            while self.running:
                # 스케줄된 작업 실행
                schedule.run_pending()
                
                # 트레이딩 루프 실행
                self.trading_loop()
                
                # 대기
                time.sleep(config["trading_interval"])
        
        except KeyboardInterrupt:
            self.stop_trading()
        except Exception as e:
            logger.error(f"자동 매매 실행 오류: {e}")
            self.stop_trading()
    
    def stop_trading(self):
        """자동 매매 중지"""
        self.running = False
        if self.websocket_manager:
            self.websocket_manager.terminate()
        
        mode = "테스트" if self.is_test_mode else "실제"
        logger.info(f"{mode} 모드 자동 매매 중지")
    
    def get_position_info(self) -> Dict:
        """포지션 정보 조회"""
        return self.strategy.get_position_manager().get_position_info()
    
    def get_statistics(self) -> Dict:
        """거래 통계 조회"""
        return self.strategy.get_position_manager().get_statistics()
    
    def save_config(self):
        """설정 저장"""
        self.config_manager.save_config()
    
    def load_config(self):
        """설정 로드"""
        self.config_manager.load_config()
        # 전략에 새로운 설정 적용
        self.strategy.config = self.config_manager.get_config()
    
    def get_config(self) -> Dict:
        """현재 설정 조회"""
        return self.config_manager.get_config()