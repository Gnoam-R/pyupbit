#!/usr/bin/env python3
"""잔고 상태 수정 스크립트"""

import json
import os
import pyupbit
from datetime import datetime

def fix_balance_file():
    """잔고 파일 상태 수정"""
    
    balance_file = "/Users/gnoam/Documents/pyupbit/balance_data/BTC_balance.json"
    
    if not os.path.exists(balance_file):
        print("❌ 잔고 파일이 존재하지 않습니다.")
        return
    
    try:
        with open(balance_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("=" * 60)
        print("🔧 잔고 파일 수정")
        print("=" * 60)
        
        # 현재 BTC 가격 조회
        try:
            current_btc_price = pyupbit.get_current_price("KRW-BTC")
            print(f"현재 BTC 가격: {current_btc_price:,.0f}원")
        except:
            current_btc_price = 160000000  # 대략적인 가격
            print(f"BTC 가격 조회 실패, 예상 가격 사용: {current_btc_price:,.0f}원")
        
        # 현재 잔고 정보
        balances = data.get('balances', {})
        krw_balance = balances.get('KRW', 0)
        btc_balance = balances.get('BTC', 0)
        initial_seed = data.get('initial_seed_money', 10000000)
        
        print(f"\n현재 잔고:")
        print(f"  KRW: {krw_balance:,.0f}원")
        print(f"  BTC: {btc_balance:.8f}BTC")
        print(f"  초기 시드머니: {initial_seed:,.0f}원")
        
        # 올바른 총 자산 가치 계산
        btc_value = btc_balance * current_btc_price
        total_value = krw_balance + btc_value
        profit_loss = total_value - initial_seed
        profit_rate = (profit_loss / initial_seed) * 100 if initial_seed > 0 else 0
        
        print(f"\n계산된 올바른 값:")
        print(f"  BTC 가치: {btc_value:,.0f}원")
        print(f"  총 자산 가치: {total_value:,.0f}원")
        print(f"  손익: {profit_loss:,.0f}원")
        print(f"  수익률: {profit_rate:.2f}%")
        
        # 포지션 정보 수정
        position = data.get('position', {})
        if position.get('is_holding'):
            # 포지션이 있다면 매수 거래가 1번 있었어야 함
            if position.get('total_trades') == 0:
                print(f"\n🔧 포지션 정보 수정:")
                print(f"  거래 수 0 → 1로 수정")
                position['total_trades'] = 1
                
                # 실제 매수 수량과 기록된 매수 수량 동기화
                recorded_buy_amount = position.get('buy_amount', 0)
                actual_btc_balance = btc_balance
                
                if abs(recorded_buy_amount - actual_btc_balance) > 0.00000001:
                    print(f"  매수 수량 동기화: {recorded_buy_amount:.8f} → {actual_btc_balance:.8f}BTC")
                    position['buy_amount'] = actual_btc_balance
        
        # performance 정보 업데이트
        data['performance'] = {
            "total_value": total_value,
            "profit_loss": profit_loss,
            "profit_rate": profit_rate
        }
        
        # trading_stats도 position과 동기화
        data['trading_stats'] = {
            "total_trades": position.get('total_trades', 0),
            "win_count": position.get('win_count', 0),
            "loss_count": position.get('loss_count', 0),
            "win_rate": (position.get('win_count', 0) / max(1, position.get('total_trades', 1))) * 100,
            "total_profit": position.get('total_profit', 0),
            "avg_profit_per_trade": position.get('total_profit', 0) / max(1, position.get('total_trades', 1))
        }
        
        # 마지막 업데이트 시간 갱신
        data['last_updated'] = datetime.now().isoformat()
        
        # 백업 생성
        backup_file = balance_file + '.backup'
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n💾 백업 파일 생성: {backup_file}")
        
        # 수정된 파일 저장
        with open(balance_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 잔고 파일 수정 완료!")
        print(f"📊 수정된 내용:")
        print(f"  - 성과 정보 재계산")
        print(f"  - 포지션과 거래 통계 동기화")
        print(f"  - 마지막 업데이트 시간 갱신")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 잔고 파일 수정 중 오류: {e}")

if __name__ == "__main__":
    fix_balance_file()