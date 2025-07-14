#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
암호화폐 자동 매매 프로그램 런처
"""

import subprocess
import sys
import os

def main():
    """메인 함수"""
    print("\n=== 암호화폐 자동 매매 프로그램 ===")
    print("1. 비트코인 자동 매매")
    print("2. 이더리움 자동 매매")
    print("3. 솔라나 자동 매매")
    print("4. 페페 자동 매매")
    print("5. 마스크 네트워크 자동 매매")
    
    while True:
        try:
            choice = input("\n번호를 선택하세요 (1-5): ").strip()
            
            if choice in ['1', '2', '3', '4', '5']:
                coin_map = {
                    '1': 'BTC',
                    '2': 'ETH', 
                    '3': 'SOL',
                    '4': 'PEPE',
                    '5': 'MASK'
                }
                
                selected_coin = coin_map[choice]
                
                # bitcoin_auto_trader.py 실행
                print(f"\n{selected_coin} 자동 매매 프로그램을 시작합니다...")
                
                # 환경 변수로 선택된 코인 전달
                env = os.environ.copy()
                env['SELECTED_COIN'] = selected_coin
                
                subprocess.run([sys.executable, 'bitcoin_auto_trader.py'], env=env)
                break
            else:
                print("올바른 번호를 입력하세요 (1-5)")
        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"오류 발생: {e}")

if __name__ == "__main__":
    main()