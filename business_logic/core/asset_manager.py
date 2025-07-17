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
    
    def check_minimum_balance(self, min_krw: float = 10000) -> bool:
        """최소 잔고 확인"""
        try:
            krw_balance = self.get_balance("KRW")
            if krw_balance < min_krw:
                logger.warning(f"⚠️ 원화 잔고 부족: {krw_balance:,.0f}원 (최소 필요: {min_krw:,.0f}원)")
                return False
            return True
        except Exception as e:
            logger.error(f"잔고 확인 오류: {e}")
            return False


class VirtualAssetManager(BaseAssetManager):
    """가상 자산 관리 클래스"""
    
    def __init__(self, target_coin: str, seed_money: float = 10000000, use_persistence: bool = True):
        self.target_coin = target_coin
        self.use_persistence = use_persistence
        self.seed_money = seed_money
        
        # 지속성 지원
        if use_persistence:
            from ..utils.balance_persistence import BalancePersistence
            self.persistence = BalancePersistence(target_coin)
            
            # 기존 잔고 로드 시도
            saved_data = self.persistence.load_balance()
            if saved_data:
                self.virtual_assets = saved_data["balances"]
                # seed_money는 항상 초기 투자금으로 고정
                self.seed_money = saved_data.get("initial_seed_money", seed_money)
                logger.info(f"💾 기존 잔고 복원: KRW={self.virtual_assets['KRW']:,.0f}, {target_coin}={self.virtual_assets[target_coin]:.8f}")
                logger.info(f"💰 초기 시드머니: {self.seed_money:,.0f}원")
            else:
                self.virtual_assets = {
                    "KRW": seed_money,
                    target_coin: 0.0
                }
                logger.info(f"💰 새 잔고 시작: {seed_money:,.0f}원")
        else:
            self.virtual_assets = {
                "KRW": seed_money,
                target_coin: 0.0
            }
            self.persistence = None
    
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
    
    def save_balance(self, position_info: Dict, trading_stats: Dict, current_price: float):
        """잔고 정보 저장"""
        if self.persistence:
            value_info = self.calculate_total_value(current_price)
            self.persistence.save_balance(
                krw_balance=self.virtual_assets["KRW"],
                coin_balance=self.virtual_assets[self.target_coin],
                total_value=value_info["total_value"],
                profit_loss=value_info["profit_loss"],
                profit_rate=value_info["profit_rate"],
                position_info=position_info,
                trading_stats=trading_stats,
                seed_money=self.seed_money
            )
    
    def save_trade_record(self, trade_record: Dict):
        """거래 기록 저장"""
        if self.persistence:
            self.persistence.save_trade_history(trade_record)
    
    def get_balance_summary(self) -> str:
        """잔고 요약 정보"""
        if self.persistence:
            return self.persistence.get_balance_summary()
        else:
            return "지속성 기능이 비활성화되어 있습니다."
    
    def reset_balance(self, initial_krw: float = 10000000):
        """잔고 초기화"""
        if self.persistence:
            self.persistence.reset_balance(initial_krw)
            # 메모리 상태도 초기화
            self.virtual_assets = {
                "KRW": initial_krw,
                self.target_coin: 0.0
            }
            self.seed_money = initial_krw
            logger.info(f"✅ 잔고 초기화 완료: {initial_krw:,.0f}원")
        else:
            logger.warning("지속성 기능이 비활성화되어 있어 초기화할 수 없습니다.")