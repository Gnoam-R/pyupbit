from abc import ABC, abstractmethod
import logging
from typing import Dict, Optional
import pyupbit
import datetime
from ..utils.coin_selector import get_coin_info
from ..utils.format_helper import format_currency, format_profit_rate

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
            
            # 코인별 최소 주문량 확인
            coin_info = get_coin_info(self.target_coin)
            min_amount = coin_info.get("min_amount", 0.01)
            
            if buy_volume < min_amount:
                logger.warning(f"매수 수량 부족: {buy_volume:.8f}{self.target_coin} (최소: {min_amount})")
                return False
            
            # 매수 주문
            result = self.upbit.buy_limit_order(self.target_ticker, adjusted_price, buy_volume)
            
            if result:
                logger.info(f"💰 매수 주문 성공: 가격={format_currency(adjusted_price)}, 수량={buy_volume:.8f}{self.target_coin}, "
                           f"총액={format_currency(buy_amount)}")
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
            
            # 코인별 최소 주문량 확인
            coin_info = get_coin_info(self.target_coin)
            min_amount = coin_info.get("min_amount", 0.01)
            
            if sell_volume < min_amount:
                logger.warning(f"매도 수량 부족: {sell_volume:.8f}{self.target_coin} (최소: {min_amount})")
                return False
            
            # 가격 단위 조정
            adjusted_price = pyupbit.get_tick_size(current_price * 1.001)
            
            # 매도 주문
            result = self.upbit.sell_limit_order(self.target_ticker, adjusted_price, sell_volume)
            
            if result:
                logger.info(f"💸 매도 주문 성공: 가격={format_currency(adjusted_price)}, 수량={sell_volume:.8f}{self.target_coin}")
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
            
            # 코인별 최소 주문량 확인
            coin_info = get_coin_info(self.target_coin)
            min_amount = coin_info.get("min_amount", 0.01)
            
            if buy_volume < min_amount:
                logger.warning(f"매수 수량 부족: {buy_volume:.8f}{self.target_coin} (최소: {min_amount})")
                return False
            
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
                
                # 거래 기록 저장
                asset_manager.save_trade_record(trade_record)
                
                # 자산 정보 추가 표시
                krw_balance = asset_manager.get_balance("KRW")
                coin_balance = asset_manager.get_balance(self.target_coin)
                
                logger.info(f"💰 [가상] 매수 주문 성공: 가격={format_currency(current_price)}, 수량={buy_volume:.8f}{self.target_coin}, "
                           f"총액={format_currency(buy_amount)}")
                logger.info(f"💰 현재 잔고 - KRW: {format_currency(krw_balance)}, {self.target_coin}: {coin_balance:.8f}")
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
            
            # 매도 수량 계산 - 실제 보유량과 포지션 중 적은 쪽 기준
            position_amount = position.get("buy_amount", 0)
            sell_volume = min(position_amount, actual_coin_balance) * config["sell_ratio"]
            
            # 최소 주문량 확인
            from ..utils.coin_selector import get_coin_info
            coin_info = get_coin_info(self.target_coin)
            min_amount = coin_info.get("min_amount", 0.00000001)
            
            # 매도 수량이 최소 주문량보다 적으면 전량 매도
            if sell_volume < min_amount:
                if actual_coin_balance >= min_amount:
                    sell_volume = actual_coin_balance
                    logger.info(f"⚠️ 매도 수량이 최소 주문량 미만, 전량 매도: {sell_volume:.8f}{self.target_coin}")
                else:
                    logger.warning(f"❌ 매도 수량 부족: {sell_volume:.8f}{self.target_coin} (최소: {min_amount:.8f}, 보유: {actual_coin_balance:.8f})")
                    return False
            
            sell_amount = sell_volume * current_price
            
            # 가상 자산 업데이트
            if asset_manager.subtract_balance(self.target_coin, sell_volume):
                asset_manager.add_balance("KRW", sell_amount)
                
                # 거래 내역 기록
                buy_price = position.get("buy_price", current_price)
                profit = (current_price - buy_price) * sell_volume
                profit_rate = (current_price - buy_price) / buy_price if buy_price > 0 else 0
                
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
                
                # 거래 기록 저장
                asset_manager.save_trade_record(trade_record)
                
                # 자산 정보 추가 표시
                krw_balance = asset_manager.get_balance("KRW")
                coin_balance = asset_manager.get_balance(self.target_coin)
                
                logger.info(f"💸 [가상] 매도 주문 성공: 가격={format_currency(current_price)}, 수량={sell_volume:.8f}{self.target_coin}, "
                           f"수익={format_currency(profit)} ({format_profit_rate(profit_rate)})")
                logger.info(f"💸 현재 잔고 - KRW: {format_currency(krw_balance)}, {self.target_coin}: {coin_balance:.8f}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"가상 매도 주문 오류: {e}")
            return False
    
    def get_trade_history(self):
        """거래 내역 반환"""
        return self.trade_history.copy()