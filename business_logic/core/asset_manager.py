import logging
from typing import Dict, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseAssetManager(ABC):
    """자산 관리 기본 클래스"""
    
    @abstractmethod
    def get_balance(self, currency: str) -> float:
        """잔고 조회"""
        pass
    
    @abstractmethod
    def get_account_info(self) -> Dict:
        """계정 정보 조회"""
        pass


class RealAssetManager(BaseAssetManager):
    """실제 자산 관리 클래스"""
    
    def __init__(self, upbit_client, target_coin: str):
        self.upbit = upbit_client
        self.target_coin = target_coin
    
    def get_balance(self, currency: str) -> float:
        """실제 잔고 조회"""
        try:
            return self.upbit.get_balance(currency)
        except Exception as e:
            logger.error(f"잔고 조회 오류: {e}")
            return 0.0
    
    def get_account_info(self) -> Optional[Dict]:
        """실제 계정 정보 조회"""
        try:
            balances = self.upbit.get_balances()
            krw_balance = self.upbit.get_balance("KRW")
            coin_balance = self.upbit.get_balance(self.target_coin)
            
            return {
                "krw_balance": krw_balance,
                "coin_balance": coin_balance,
                "balances": balances
            }
        except Exception as e:
            logger.error(f"계정 정보 조회 오류: {e}")
            return None


class VirtualAssetManager(BaseAssetManager):
    """가상 자산 관리 클래스"""
    
    def __init__(self, target_coin: str, seed_money: float = 1000000):
        self.target_coin = target_coin
        self.virtual_assets = {
            "KRW": seed_money,
            target_coin: 0.0
        }
        self.seed_money = seed_money
    
    def get_balance(self, currency: str) -> float:
        """가상 잔고 조회"""
        return self.virtual_assets.get(currency, 0.0)
    
    def get_account_info(self) -> Dict:
        """가상 계정 정보 조회"""
        return {
            "krw_balance": self.virtual_assets["KRW"],
            "coin_balance": self.virtual_assets[self.target_coin],
            "seed_money": self.seed_money
        }
    
    def update_balance(self, currency: str, amount: float):
        """잔고 업데이트"""
        if currency in self.virtual_assets:
            self.virtual_assets[currency] = amount
        else:
            logger.warning(f"알 수 없는 통화: {currency}")
    
    def add_balance(self, currency: str, amount: float):
        """잔고 추가"""
        if currency in self.virtual_assets:
            self.virtual_assets[currency] += amount
        else:
            logger.warning(f"알 수 없는 통화: {currency}")
    
    def subtract_balance(self, currency: str, amount: float) -> bool:
        """잔고 차감"""
        if currency not in self.virtual_assets:
            logger.warning(f"알 수 없는 통화: {currency}")
            return False
        
        if self.virtual_assets[currency] >= amount:
            self.virtual_assets[currency] -= amount
            return True
        else:
            logger.warning(f"잔고 부족: {currency}, 필요={amount}, 보유={self.virtual_assets[currency]}")
            return False
    
    def calculate_total_value(self, current_price: float) -> Dict:
        """총 자산 가치 계산"""
        try:
            coin_value = self.virtual_assets[self.target_coin] * current_price
            total_value = self.virtual_assets["KRW"] + coin_value
            profit_loss = total_value - self.seed_money
            profit_rate = (profit_loss / self.seed_money) * 100 if self.seed_money > 0 else 0
            
            return {
                "total_value": total_value,
                "coin_value": coin_value,
                "profit_loss": profit_loss,
                "profit_rate": profit_rate
            }
        except Exception as e:
            logger.error(f"총 자산 가치 계산 오류: {e}")
            return {
                "total_value": self.virtual_assets["KRW"],
                "coin_value": 0.0,
                "profit_loss": 0.0,
                "profit_rate": 0.0
            }