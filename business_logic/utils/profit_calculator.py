"""수익 계산 유틸리티"""

from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


def calculate_unrealized_profit(position: Dict, current_price: float) -> Tuple[float, float]:
    """
    현재 포지션의 미실현 손익 계산
    
    Args:
        position: 포지션 정보
        current_price: 현재 가격
        
    Returns:
        (미실현 손익, 미실현 수익률)
    """
    if not position.get("is_holding", False) or position.get("buy_price", 0) == 0:
        return 0.0, 0.0
    
    buy_price = position["buy_price"]
    buy_amount = position["buy_amount"]
    
    unrealized_profit = (current_price - buy_price) * buy_amount
    unrealized_rate = (current_price - buy_price) / buy_price
    
    return unrealized_profit, unrealized_rate


def calculate_total_profit_summary(position: Dict, current_price: float, initial_seed: float, 
                                 current_krw: float, current_coin: float) -> Dict:
    """
    총 수익 요약 계산
    
    Args:
        position: 포지션 정보
        current_price: 현재 가격
        initial_seed: 초기 시드머니
        current_krw: 현재 원화 잔고
        current_coin: 현재 코인 잔고
        
    Returns:
        수익 요약 딕셔너리
    """
    # 현재 총 자산 가치
    coin_value = current_coin * current_price
    total_value = current_krw + coin_value
    
    # 자산 변화 기준 손익
    asset_profit = total_value - initial_seed
    asset_profit_rate = (asset_profit / initial_seed) * 100 if initial_seed > 0 else 0
    
    # 거래 기준 손익
    realized_profit = position.get("total_profit", 0)
    
    # 미실현 손익
    unrealized_profit, unrealized_rate = calculate_unrealized_profit(position, current_price)
    
    # 총 예상 손익 (실현 + 미실현)
    total_expected_profit = realized_profit + unrealized_profit
    
    return {
        "initial_seed": initial_seed,
        "current_krw": current_krw,
        "current_coin": current_coin,
        "coin_value": coin_value,
        "total_value": total_value,
        "asset_profit": asset_profit,
        "asset_profit_rate": asset_profit_rate,
        "realized_profit": realized_profit,
        "unrealized_profit": unrealized_profit,
        "unrealized_rate": unrealized_rate,
        "total_expected_profit": total_expected_profit,
        "current_price": current_price
    }


def get_profit_status_text(profit_summary: Dict) -> str:
    """수익 상태를 텍스트로 표현"""
    lines = []
    
    # 기본 정보
    lines.append(f"💰 총 자산: {profit_summary['total_value']:,.0f}원")
    lines.append(f"   └ 원화: {profit_summary['current_krw']:,.0f}원")
    lines.append(f"   └ 코인: {profit_summary['coin_value']:,.0f}원 ({profit_summary['current_coin']:.8f})")
    
    # 손익 정보
    lines.append(f"📈 자산 변화: {profit_summary['asset_profit']:,.0f}원 ({profit_summary['asset_profit_rate']:.2f}%)")
    
    if profit_summary['realized_profit'] != 0:
        lines.append(f"💵 실현 손익: {profit_summary['realized_profit']:,.0f}원")
    
    if profit_summary['unrealized_profit'] != 0:
        lines.append(f"📊 미실현 손익: {profit_summary['unrealized_profit']:,.0f}원 ({profit_summary['unrealized_rate']:.2%})")
    
    return "\n".join(lines)


def validate_profit_consistency(position: Dict, asset_profit: float, realized_profit: float, 
                               unrealized_profit: float, tolerance: float = 1000.0) -> bool:
    """
    수익 계산의 일관성 검증
    
    Args:
        position: 포지션 정보
        asset_profit: 자산 변화 기준 손익
        realized_profit: 실현 손익
        unrealized_profit: 미실현 손익
        tolerance: 허용 오차 (원)
        
    Returns:
        일관성 여부
    """
    if not position.get("is_holding", False):
        # 포지션이 없으면 실현 손익 = 자산 변화 손익이어야 함
        return abs(asset_profit - realized_profit) <= tolerance
    else:
        # 포지션이 있으면 실현 + 미실현 ≈ 자산 변화 손익
        total_expected = realized_profit + unrealized_profit
        return abs(asset_profit - total_expected) <= tolerance