#!/usr/bin/env python3
"""잔고 상태 디버깅 스크립트"""

import json
import os
from business_logic.utils.balance_persistence import BalancePersistence

def debug_balance_file():
    """잔고 파일 상태 디버깅"""
    
    balance_file = "/Users/gnoam/Documents/pyupbit/balance_data/BTC_balance.json"
    
    if not os.path.exists(balance_file):
        print("❌ 잔고 파일이 존재하지 않습니다.")
        return
    
    try:
        with open(balance_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("=" * 60)
        print("📊 잔고 파일 분석")
        print("=" * 60)
        
        # 기본 정보
        print(f"코인: {data.get('coin_symbol', 'N/A')}")
        print(f"마지막 업데이트: {data.get('last_updated', 'N/A')}")
        print(f"초기 시드머니: {data.get('initial_seed_money', 'N/A'):,.0f}원")
        
        # 잔고 정보
        balances = data.get('balances', {})
        print(f"\n💰 현재 잔고:")
        print(f"  KRW: {balances.get('KRW', 0):,.0f}원")
        print(f"  BTC: {balances.get('BTC', 0):.8f}BTC")
        
        # 성과 정보
        performance = data.get('performance', {})
        print(f"\n📈 성과:")
        print(f"  총 자산 가치: {performance.get('total_value', 0):,.0f}원")
        print(f"  손익: {performance.get('profit_loss', 0):,.0f}원")
        print(f"  수익률: {performance.get('profit_rate', 0):.2f}%")
        
        # 포지션 정보
        position = data.get('position', {})
        print(f"\n📊 포지션:")
        print(f"  보유 중: {position.get('is_holding', False)}")
        if position.get('is_holding'):
            print(f"  매수가: {position.get('buy_price', 0):,.0f}원")
            print(f"  매수량: {position.get('buy_amount', 0):.8f}BTC")
            print(f"  매수 시간: {position.get('buy_time', 'N/A')}")
        print(f"  총 거래 수익: {position.get('total_profit', 0):,.0f}원")
        print(f"  총 거래 수: {position.get('total_trades', 0)}")
        print(f"  승/패: {position.get('win_count', 0)}/{position.get('loss_count', 0)}")
        
        # 거래 통계
        stats = data.get('trading_stats', {})
        print(f"\n📋 거래 통계:")
        print(f"  총 거래 수: {stats.get('total_trades', 0)}")
        print(f"  승률: {stats.get('win_rate', 0):.1f}%")
        print(f"  총 거래 수익: {stats.get('total_profit', 0):,.0f}원")
        print(f"  평균 거래당 수익: {stats.get('avg_profit_per_trade', 0):,.0f}원")
        
        # 문제점 분석
        print(f"\n⚠️  잠재적 문제점:")
        issues = []
        
        if not data.get('initial_seed_money'):
            issues.append("initial_seed_money가 설정되지 않음")
        
        if position.get('is_holding') and position.get('total_trades') == 0:
            issues.append("포지션을 보유 중이지만 거래 기록이 없음")
        
        if position.get('total_profit') != stats.get('total_profit'):
            issues.append(f"포지션 수익({position.get('total_profit')})과 거래 통계 수익({stats.get('total_profit')})이 다름")
        
        current_value = balances.get('KRW', 0) + balances.get('BTC', 0) * 160000000  # 대략적인 BTC 가격
        calculated_profit = current_value - data.get('initial_seed_money', 10000000)
        recorded_profit = performance.get('profit_loss', 0)
        
        if abs(calculated_profit - recorded_profit) > 1000:  # 1000원 이상 차이
            issues.append(f"계산된 손익({calculated_profit:,.0f})과 기록된 손익({recorded_profit:,.0f})이 다름")
        
        if not issues:
            print("  문제점이 발견되지 않았습니다.")
        else:
            for issue in issues:
                print(f"  - {issue}")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 잔고 파일 분석 중 오류: {e}")

if __name__ == "__main__":
    debug_balance_file()