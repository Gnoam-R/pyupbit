from abc import ABC, abstractmethod
import logging
from typing import Dict, Optional
import pyupbit
import datetime

logger = logging.getLogger(__name__)


class BaseTradeExecutor(ABC):
    """트레이드 실행 기본 클래스"""
    
    @abstractmethod
    def execute_buy_order(self, current_price: float, config: Dict, asset_manager) -> bool:
        """매수 주문 실행"""
        pass
    
    @abstractmethod
    def execute_sell_order(self, current_price: float, config: Dict, position: Dict, asset_manager) -> bool:
        """매도 주문 실행"""
        pass


class RealTradeExecutor(BaseTradeExecutor):
    """실제 거래 실행 클래스"""
    
    def __init__(self, upbit_client, target_coin: str):
        self.upbit = upbit_client
        self.target_coin = target_coin
        self.target_ticker = f"KRW-{target_coin}"
    
    def execute_buy_order(self, current_price: float, config: Dict, asset_manager) -> bool:
        """실제 매수 주문 실행"""
        try:
            account_info = asset_manager.get_account_info()
            if not account_info:
                return False
            
            krw_balance = account_info["krw_balance"]
            buy_amount = krw_balance * config["buy_ratio"]
            
            if buy_amount < config["min_order_amount"]:
                logger.warning(f"매수 가능 금액 부족: {buy_amount:,.0f}원")
                return False
            
            # 가격 단위 조정
            adjusted_price = pyupbit.get_tick_size(current_price * 0.999)
            buy_volume = buy_amount / adjusted_price
            
            # 매수 주문
            result = self.upbit.buy_limit_order(self.target_ticker, adjusted_price, buy_volume)
            
            if result:
                logger.info(f"매수 주문 성공: 가격={adjusted_price:,.0f}원, 수량={buy_volume:.8f}{self.target_coin}, "
                           f"총액={buy_amount:,.0f}원")
                return True
            else:
                logger.error("매수 주문 실패")
                return False
        except Exception as e:
            logger.error(f"매수 주문 오류: {e}")
            return False
    
    def execute_sell_order(self, current_price: float, config: Dict, position: Dict, asset_manager) -> bool:
        """실제 매도 주문 실행"""
        try:
            if not position.get("is_holding", False):
                return False
            
            sell_volume = position["buy_amount"] * config["sell_ratio"]
            
            # 가격 단위 조정
            adjusted_price = pyupbit.get_tick_size(current_price * 1.001)
            
            # 매도 주문
            result = self.upbit.sell_limit_order(self.target_ticker, adjusted_price, sell_volume)
            
            if result:
                logger.info(f"매도 주문 성공: 가격={adjusted_price:,.0f}원, 수량={sell_volume:.8f}{self.target_coin}")
                return True
            else:
                logger.error("매도 주문 실패")
                return False
        except Exception as e:
            logger.error(f"매도 주문 오류: {e}")
            return False


class VirtualTradeExecutor(BaseTradeExecutor):
    """가상 거래 실행 클래스"""
    
    def __init__(self, target_coin: str):
        self.target_coin = target_coin
        self.trade_history = []
    
    def execute_buy_order(self, current_price: float, config: Dict, asset_manager) -> bool:
        """가상 매수 주문 실행"""
        try:
            krw_balance = asset_manager.get_balance("KRW")
            buy_amount = krw_balance * config["buy_ratio"]
            
            if buy_amount < config["min_order_amount"]:
                logger.warning(f"매수 가능 금액 부족: {buy_amount:,.0f}원")
                return False
            
            buy_volume = buy_amount / current_price
            
            # 가상 자산 업데이트
            if asset_manager.subtract_balance("KRW", buy_amount):
                asset_manager.add_balance(self.target_coin, buy_volume)
                
                # 거래 내역 기록
                trade_record = {
                    "timestamp": datetime.datetime.now(),
                    "type": "buy",
                    "price": current_price,
                    "amount": buy_volume,
                    "total_krw": buy_amount,
                    "reason": "signal"
                }
                self.trade_history.append(trade_record)
                
                logger.info(f"[가상] 매수 주문 성공: 가격={current_price:,.0f}원, 수량={buy_volume:.8f}{self.target_coin}, "
                           f"총액={buy_amount:,.0f}원")
                return True
            
            return False
        except Exception as e:
            logger.error(f"가상 매수 주문 오류: {e}")
            return False
    
    def execute_sell_order(self, current_price: float, config: Dict, position: Dict, asset_manager) -> bool:
        """가상 매도 주문 실행"""
        try:
            if not position.get("is_holding", False):
                return False
            
            actual_coin_balance = asset_manager.get_balance(self.target_coin)
            if actual_coin_balance <= 0:
                logger.warning(f"매도 불가: 보유 코인 수량이 0입니다.")
                return False
            
            sell_volume = position["buy_amount"] * config["sell_ratio"]
            
            # 실제 보유량보다 많이 팔려고 하는 경우 조정
            if sell_volume > actual_coin_balance:
                sell_volume = actual_coin_balance
                logger.warning(f"매도 수량 조정: {sell_volume:.8f}{self.target_coin} (보유량 전량)")
            
            sell_amount = sell_volume * current_price
            
            # 가상 자산 업데이트
            if asset_manager.subtract_balance(self.target_coin, sell_volume):
                asset_manager.add_balance("KRW", sell_amount)
                
                # 거래 내역 기록
                profit = (current_price - position["buy_price"]) * sell_volume
                profit_rate = (current_price - position["buy_price"]) / position["buy_price"]
                
                trade_record = {
                    "timestamp": datetime.datetime.now(),
                    "type": "sell",
                    "price": current_price,
                    "amount": sell_volume,
                    "total_krw": sell_amount,
                    "profit": profit,
                    "profit_rate": profit_rate,
                    "reason": "signal"
                }
                self.trade_history.append(trade_record)
                
                logger.info(f"[가상] 매도 주문 성공: 가격={current_price:,.0f}원, 수량={sell_volume:.8f}{self.target_coin}, "
                           f"수익={profit:,.0f}원 ({profit_rate:.2%})")
                return True
            
            return False
        except Exception as e:
            logger.error(f"가상 매도 주문 오류: {e}")
            return False
    
    def get_trade_history(self):
        """거래 내역 반환"""
        return self.trade_history.copy()