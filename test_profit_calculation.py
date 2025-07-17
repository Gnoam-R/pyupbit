#!/usr/bin/env python3
"""수익 계산 로직 테스트"""

import json
import pyupbit
from business_logic.utils.profit_calculator import calculate_total_profit_summary
from business_logic.utils.format_helper import format_currency, format_percentage, format_profit_rate

def test_profit_calculation():
    """수익 계산 테스트"""
    
    # 잔고 파일에서 데이터 로드
    balance_file = "/Users/gnoam/Documents/pyupbit/balance_data/BTC_balance.json"
    with open(balance_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 현재 BTC 가격 조회
    try:
        current_price = pyupbit.get_current_price("KRW-BTC")
        print(f"현재 BTC 가격: {format_currency(current_price)}")
    except:
        current_price = 163000000
        print(f"가격 조회 실패, 예상 가격 사용: {format_currency(current_price)}")
    
    # 데이터 추출
    position = data["position"]
    balances = data["balances"]
    initial_seed = data["initial_seed_money"]
    
    # 수익 계산
    profit_summary = calculate_total_profit_summary(
        position=position,
        current_price=current_price,
        initial_seed=initial_seed,
        current_krw=balances["KRW"],
        current_coin=balances["BTC"]
    )
    
    print("\n" + "=" * 60)
    print("💰 개선된 수익 계산 결과")
    print("=" * 60)
    
    print(f"초기 투자금: {format_currency(profit_summary['initial_seed'])}")
    print(f"현재 원화: {format_currency(profit_summary['current_krw'])}")
    print(f"현재 코인: {profit_summary['current_coin']:.8f}BTC")
    print(f"코인 가치: {format_currency(profit_summary['coin_value'])}")
    print(f"총 자산: {format_currency(profit_summary['total_value'])}")
    print()
    print(f"자산 변화: {format_currency(profit_summary['asset_profit'])} ({format_percentage(profit_summary['asset_profit_rate'])})")
    print(f"실현 손익: {format_currency(profit_summary['realized_profit'])}")
    print(f"미실현 손익: {format_currency(profit_summary['unrealized_profit'])} ({format_profit_rate(profit_summary['unrealized_rate'])})")
    print(f"총 예상 손익: {format_currency(profit_summary['total_expected_profit'])}")
    
    # 검증
    print(f"\n🔍 검증:")
    asset_vs_expected = profit_summary['asset_profit'] - profit_summary['total_expected_profit']
    print(f"자산 변화 vs 예상 손익 차이: {format_currency(asset_vs_expected)}")
    
    if abs(asset_vs_expected) < 1000:
        print("✅ 수익 계산이 일관성 있게 계산됨")
    else:
        print("⚠️ 수익 계산에 불일치가 있음")
    
    print("=" * 60)

if __name__ == "__main__":
    test_profit_calculation()