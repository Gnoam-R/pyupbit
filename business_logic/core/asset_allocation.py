import logging
from typing import Dict, List, Optional
from abc import ABC, abstractmethod
from ..utils.coin_selector import COIN_CONFIG

logger = logging.getLogger(__name__)


class BaseAssetAllocationStrategy(ABC):
    """자산 배분 전략 기본 클래스"""
    
    @abstractmethod
    def calculate_allocation(self, available_krw: float, coin_prices: Dict[str, float]) -> Dict[str, float]:
        """각 코인별 배분 금액 계산"""
        pass
    
    @abstractmethod
    def get_buy_amount_for_coin(self, coin: str, available_krw: float, coin_prices: Dict[str, float]) -> float:
        """특정 코인의 매수 금액 계산"""
        pass


class EqualWeightAllocation(BaseAssetAllocationStrategy):
    """균등 배분 전략"""
    
    def __init__(self, supported_coins: List[str], allocation_ratio: float = 0.8):
        """
        Args:
            supported_coins: 지원하는 코인 목록
            allocation_ratio: 전체 자산 중 투자에 사용할 비율 (기본 80%)
        """
        self.supported_coins = supported_coins
        self.allocation_ratio = allocation_ratio
        self.coin_weight = 1.0 / len(supported_coins)  # 각 코인의 가중치
        
        logger.info(f"균등 배분 전략 초기화 - 코인 수: {len(supported_coins)}, 각 코인 가중치: {self.coin_weight:.2%}")
    
    def calculate_allocation(self, available_krw: float, coin_prices: Dict[str, float]) -> Dict[str, float]:
        """각 코인별 배분 금액 계산"""
        total_investment = available_krw * self.allocation_ratio
        per_coin_allocation = total_investment * self.coin_weight
        
        allocation = {}
        for coin in self.supported_coins:
            if coin in coin_prices and coin_prices[coin] is not None:
                allocation[coin] = per_coin_allocation
            else:
                allocation[coin] = 0
                logger.warning(f"{coin} 가격 정보 없음 - 배분 금액 0원")
        
        return allocation
    
    def get_buy_amount_for_coin(self, coin: str, available_krw: float, coin_prices: Dict[str, float]) -> float:
        """특정 코인의 매수 금액 계산"""
        if coin not in self.supported_coins:
            return 0
        
        allocation = self.calculate_allocation(available_krw, coin_prices)
        return allocation.get(coin, 0)


class WeightedAllocation(BaseAssetAllocationStrategy):
    """가중 배분 전략"""
    
    def __init__(self, coin_weights: Dict[str, float], allocation_ratio: float = 0.8):
        """
        Args:
            coin_weights: 코인별 가중치 (합계가 1.0이 되어야 함)
            allocation_ratio: 전체 자산 중 투자에 사용할 비율 (기본 80%)
        """
        self.coin_weights = coin_weights
        self.allocation_ratio = allocation_ratio
        self.supported_coins = list(coin_weights.keys())
        
        # 가중치 합계 검증
        total_weight = sum(coin_weights.values())
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"가중치 합계가 1.0이 아님: {total_weight:.3f}")
            # 정규화
            self.coin_weights = {coin: weight / total_weight for coin, weight in coin_weights.items()}
        
        logger.info(f"가중 배분 전략 초기화 - 가중치: {self.coin_weights}")
    
    def calculate_allocation(self, available_krw: float, coin_prices: Dict[str, float]) -> Dict[str, float]:
        """각 코인별 배분 금액 계산"""
        total_investment = available_krw * self.allocation_ratio
        
        allocation = {}
        for coin, weight in self.coin_weights.items():
            if coin in coin_prices and coin_prices[coin] is not None:
                allocation[coin] = total_investment * weight
            else:
                allocation[coin] = 0
                logger.warning(f"{coin} 가격 정보 없음 - 배분 금액 0원")
        
        return allocation
    
    def get_buy_amount_for_coin(self, coin: str, available_krw: float, coin_prices: Dict[str, float]) -> float:
        """특정 코인의 매수 금액 계산"""
        if coin not in self.coin_weights:
            return 0
        
        allocation = self.calculate_allocation(available_krw, coin_prices)
        return allocation.get(coin, 0)


class DynamicAllocation(BaseAssetAllocationStrategy):
    """동적 배분 전략 (시장 상황에 따라 배분 비율 조정)"""
    
    def __init__(self, base_weights: Dict[str, float], allocation_ratio: float = 0.8):
        """
        Args:
            base_weights: 기본 가중치
            allocation_ratio: 전체 자산 중 투자에 사용할 비율 (기본 80%)
        """
        self.base_weights = base_weights
        self.allocation_ratio = allocation_ratio
        self.supported_coins = list(base_weights.keys())
        
        logger.info(f"동적 배분 전략 초기화 - 기본 가중치: {self.base_weights}")
    
    def _adjust_weights_by_market_conditions(self, coin_prices: Dict[str, float]) -> Dict[str, float]:
        """시장 상황에 따라 가중치 조정"""
        # 여기서는 간단한 예시로 가격 변동성을 고려한 조정
        # 실제로는 더 복잡한 알고리즘을 사용할 수 있음
        
        adjusted_weights = self.base_weights.copy()
        
        # 예시: 가격이 높은 코인의 가중치를 약간 줄임
        # 실제 구현에서는 더 정교한 로직 사용
        for coin in adjusted_weights:
            if coin in coin_prices and coin_prices[coin] is not None:
                # 비트코인 가격을 기준으로 상대적 가중치 조정
                if coin == "BTC":
                    continue
                
                # 간단한 예시: 가격이 매우 높으면 가중치를 약간 줄임
                if coin_prices[coin] > 1000000:  # 100만원 이상
                    adjusted_weights[coin] *= 0.9
                elif coin_prices[coin] > 100000:  # 10만원 이상
                    adjusted_weights[coin] *= 0.95
        
        # 정규화
        total_weight = sum(adjusted_weights.values())
        if total_weight > 0:
            adjusted_weights = {coin: weight / total_weight for coin, weight in adjusted_weights.items()}
        
        return adjusted_weights
    
    def calculate_allocation(self, available_krw: float, coin_prices: Dict[str, float]) -> Dict[str, float]:
        """각 코인별 배분 금액 계산"""
        total_investment = available_krw * self.allocation_ratio
        
        # 시장 상황에 따라 가중치 조정
        adjusted_weights = self._adjust_weights_by_market_conditions(coin_prices)
        
        allocation = {}
        for coin, weight in adjusted_weights.items():
            if coin in coin_prices and coin_prices[coin] is not None:
                allocation[coin] = total_investment * weight
            else:
                allocation[coin] = 0
                logger.warning(f"{coin} 가격 정보 없음 - 배분 금액 0원")
        
        return allocation
    
    def get_buy_amount_for_coin(self, coin: str, available_krw: float, coin_prices: Dict[str, float]) -> float:
        """특정 코인의 매수 금액 계산"""
        if coin not in self.base_weights:
            return 0
        
        allocation = self.calculate_allocation(available_krw, coin_prices)
        return allocation.get(coin, 0)


class AssetAllocationManager:
    """자산 배분 매니저"""
    
    def __init__(self, strategy: BaseAssetAllocationStrategy, min_order_amount: float = 5000):
        """
        Args:
            strategy: 자산 배분 전략
            min_order_amount: 최소 주문 금액
        """
        self.strategy = strategy
        self.min_order_amount = min_order_amount
        
        logger.info(f"자산 배분 매니저 초기화 - 최소 주문 금액: {min_order_amount:,.0f}원")
    
    def get_allocation_for_all_coins(self, available_krw: float, coin_prices: Dict[str, float]) -> Dict[str, float]:
        """모든 코인의 배분 금액 계산"""
        raw_allocation = self.strategy.calculate_allocation(available_krw, coin_prices)
        
        # 최소 주문 금액 필터링
        filtered_allocation = {}
        for coin, amount in raw_allocation.items():
            if amount >= self.min_order_amount:
                filtered_allocation[coin] = amount
            else:
                if amount > 0:
                    logger.debug(f"{coin} 배분 금액({amount:,.0f}원)이 최소 주문 금액 미만으로 제외")
                filtered_allocation[coin] = 0
        
        return filtered_allocation
    
    def get_buy_amount_for_coin(self, coin: str, available_krw: float, coin_prices: Dict[str, float]) -> float:
        """특정 코인의 매수 금액 계산"""
        amount = self.strategy.get_buy_amount_for_coin(coin, available_krw, coin_prices)
        
        if amount < self.min_order_amount:
            return 0
        
        return amount
    
    def change_strategy(self, new_strategy: BaseAssetAllocationStrategy):
        """자산 배분 전략 변경"""
        self.strategy = new_strategy
        logger.info(f"자산 배분 전략 변경: {type(new_strategy).__name__}")
    
    def get_strategy_info(self) -> Dict:
        """현재 전략 정보 반환"""
        return {
            "strategy_type": type(self.strategy).__name__,
            "min_order_amount": self.min_order_amount,
            "supported_coins": getattr(self.strategy, 'supported_coins', [])
        }


# 기본 전략 팩토리 함수들
def create_equal_weight_allocation(supported_coins: List[str] = None, allocation_ratio: float = 0.8) -> EqualWeightAllocation:
    """균등 배분 전략 생성"""
    if supported_coins is None:
        supported_coins = list(COIN_CONFIG.keys())
    
    return EqualWeightAllocation(supported_coins, allocation_ratio)


def create_btc_focused_allocation(allocation_ratio: float = 0.8) -> WeightedAllocation:
    """비트코인 중심 배분 전략 생성"""
    weights = {
        "BTC": 0.5,   # 50%
        "ETH": 0.2,   # 20%
        "SOL": 0.15,  # 15%
        "MASK": 0.1,  # 10%
        "PEPE": 0.05  # 5%
    }
    
    return WeightedAllocation(weights, allocation_ratio)


def create_dynamic_allocation(allocation_ratio: float = 0.8) -> DynamicAllocation:
    """동적 배분 전략 생성"""
    base_weights = {
        "BTC": 0.3,   # 30%
        "ETH": 0.25,  # 25%
        "SOL": 0.2,   # 20%
        "MASK": 0.15, # 15%
        "PEPE": 0.1   # 10%
    }
    
    return DynamicAllocation(base_weights, allocation_ratio)