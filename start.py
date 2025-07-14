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
    print("모드를 선택하세요:")
    print("1. 실제 거래 모드")
    print("2. 테스트 모드 (시뮬레이션)")
    
    while True:
        try:
            mode_choice = input("\n모드를 선택하세요 (1-2): ").strip()
            
            if mode_choice in ['1', '2']:
                if mode_choice == '1':
                    # 실제 거래 모드
                    print("\n=== 실제 거래 모드 ===")
                    print("1. 비트코인 자동 매매")
                    print("2. 이더리움 자동 매매")
                    print("3. 솔라나 자동 매매")
                    print("4. 페페 자동 매매")
                    print("5. 마스크 네트워크 자동 매매")
                    
                    coin_choice = input("\n코인을 선택하세요 (1-5): ").strip()
                    
                    if coin_choice in ['1', '2', '3', '4', '5']:
                        coin_map = {
                            '1': 'BTC',
                            '2': 'ETH', 
                            '3': 'SOL',
                            '4': 'PEPE',
                            '5': 'MASK'
                        }
                        
                        selected_coin = coin_map[coin_choice]
                        
                        # bitcoin_auto_trader.py 실행
                        print(f"\n{selected_coin} 실제 거래 모드를 시작합니다...")
                        
                        # 환경 변수로 선택된 코인 전달
                        env = os.environ.copy()
                        env['SELECTED_COIN'] = selected_coin
                        
                        subprocess.run([sys.executable, 'bitcoin_auto_trader.py'], env=env)
                        break
                    else:
                        print("올바른 번호를 입력하세요 (1-5)")
                        
                elif mode_choice == '2':
                    # 테스트 모드
                    print(f"\n테스트 모드 (시뮬레이션)를 시작합니다...")
                    subprocess.run([sys.executable, 'test_trading_simulator.py'])
                    break
                    
            else:
                print("올바른 번호를 입력하세요 (1-2)")
        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"오류 발생: {e}")

if __name__ == "__main__":
    main()