#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
다중 코인 암호화폐 자동 매매 프로그램

여러 코인을 동시에 모니터링하고 자동 매매를 수행합니다.
"""

import pyupbit
import time
import os
import sys

# Business Logic Imports
from business_logic.core.multi_coin_engine import MultiCoinTradingEngine
from business_logic.core.asset_manager import RealAssetManager
from business_logic.executors.trading_executor import RealTradeExecutor
from business_logic.utils.coin_selector import select_coins, get_all_coin_names
from business_logic.utils.logger import setup_logger
from business_logic.utils.format_helper import format_currency

# 로깅 설정
logger = setup_logger('multi_coin_auto_trader', 'multi_coin_trader.log')


class MultiCoinRealTrader:
    """다중 코인 실제 암호화폐 자동 매매 클래스"""
    
    def __init__(self, access_key: str, secret_key: str, target_coins: list):
        self.upbit = pyupbit.Upbit(access_key, secret_key)
        self.target_coins = target_coins
        
        # 비즈니스 로직 모듈 초기화
        self.asset_manager = RealAssetManager(self.upbit, target_coins[0])  # 첫 번째 코인을 기본으로 설정
        self.trade_executor = RealTradeExecutor(self.upbit, target_coins[0])
        
        # 다중 코인 엔진 초기화
        self.engine = MultiCoinTradingEngine(
            target_coins, 
            self.asset_manager, 
            self.trade_executor,
            is_test_mode=False
        )
        
        logger.info(f"다중 코인 트레이더 초기화 완료 - 대상 코인: {', '.join(target_coins)}")
    
    def validate_api_keys(self) -> bool:
        """API 키 유효성 검사"""
        try:
            balances = self.upbit.get_balances()
            if balances is None:
                logger.error("API 키 검증 실패: 잔고 조회 불가")
                return False
            
            logger.info("✅ API 키 검증 성공")
            return True
        except Exception as e:
            logger.error(f"API 키 검증 오류: {e}")
            return False
    
    def print_account_summary(self):
        """계정 요약 정보 출력"""
        try:
            account_info = self.asset_manager.get_account_info()
            if not account_info:
                logger.error("계정 정보 조회 실패")
                return
            
            print("=" * 80)
            print(f"🪙 {get_all_coin_names(self.target_coins)} 다중 코인 자동 매매 프로그램")
            print("=" * 80)
            print(f"원화 잔고: {format_currency(account_info['krw_balance'])}")
            
            # 각 코인별 잔고 표시
            for coin in self.target_coins:
                coin_balance = self.asset_manager.get_balance(coin)
                current_price = self.engine.get_current_price(coin)
                
                if coin_balance > 0:
                    coin_value = coin_balance * current_price if current_price else 0
                    print(f"{coin} 잔고: {coin_balance:.8f} (약 {format_currency(coin_value)})")
                else:
                    print(f"{coin} 잔고: 0")
            
            print("=" * 80)
            
            # 최소 잔고 확인
            if not self.asset_manager.check_minimum_balance(10000):
                print("⚠️  원화 잔고가 부족합니다. 최소 10,000원 이상 보유해야 합니다.")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"계정 요약 정보 출력 오류: {e}")
            return False
    
    def start_trading(self):
        """자동 매매 시작"""
        # 시작 전 최종 잔고 확인
        if not self.asset_manager.check_minimum_balance(10000):
            print("🚫 잔고 부족으로 자동 매매를 시작할 수 없습니다.")
            return
        
        print(f"🚀 {get_all_coin_names(self.target_coins)} 자동 매매 시작!")
        self.engine.start_trading()
    
    def stop_trading(self):
        """자동 매매 중지"""
        self.engine.stop_trading()
    
    def print_status(self):
        """현재 상태 출력"""
        self.engine.print_status()


def load_api_keys() -> tuple:
    """API 키 로드"""
    try:
        # 환경 변수에서 먼저 확인
        access_key = os.environ.get('UPBIT_ACCESS_KEY')
        secret_key = os.environ.get('UPBIT_SECRET_KEY')
        
        if access_key and secret_key:
            logger.info("환경 변수에서 API 키 로드 완료")
            return access_key, secret_key
        
        # 파일에서 로드
        if os.path.exists("upbit_keys.txt"):
            with open("upbit_keys.txt", "r") as f:
                lines = f.readlines()
                if len(lines) >= 2:
                    access_key = lines[0].strip()
                    secret_key = lines[1].strip()
                    logger.info("파일에서 API 키 로드 완료")
                    return access_key, secret_key
        
        logger.error("API 키를 찾을 수 없습니다")
        return None, None
        
    except Exception as e:
        logger.error(f"API 키 로드 오류: {e}")
        return None, None


def main():
    """메인 함수"""
    print("🚀 다중 코인 암호화폐 자동 매매 프로그램 시작")
    print("⚠️  주의: 이 프로그램은 실제 자산으로 거래를 수행합니다!")
    
    # API 키 로드
    access_key, secret_key = load_api_keys()
    if not access_key or not secret_key:
        print("❌ API 키를 설정해주세요.")
        print("방법 1: 환경 변수 설정")
        print("  export UPBIT_ACCESS_KEY='your_access_key'")
        print("  export UPBIT_SECRET_KEY='your_secret_key'")
        print("방법 2: upbit_keys.txt 파일 생성")
        print("  첫 번째 줄: access_key")
        print("  두 번째 줄: secret_key")
        return
    
    # 다중 코인 선택
    selected_coins = select_coins(multi=True)
    
    if not selected_coins:
        print("❌ 코인이 선택되지 않았습니다.")
        return
    
    # 트레이더 초기화
    trader = MultiCoinRealTrader(access_key, secret_key, selected_coins)
    
    # API 키 검증
    if not trader.validate_api_keys():
        print("❌ API 키 검증 실패. 키를 확인해주세요.")
        return
    
    # 계정 요약 정보 출력
    if not trader.print_account_summary():
        print("❌ 계정 정보 조회 실패 또는 잔고 부족")
        return
    
    # 사용자 입력 처리
    print("\\n📋 사용 가능한 명령어:")
    print("  start  - 자동 매매 시작")
    print("  stop   - 자동 매매 중지")
    print("  status - 현재 상태 확인")
    print("  quit   - 프로그램 종료")
    
    while True:
        try:
            command = input("\\n명령어를 입력하세요: ").strip().lower()
            
            if command == "start":
                print("🚀 자동 매매를 시작합니다...")
                trader.start_trading()
            elif command == "stop":
                print("🛑 자동 매매를 중지합니다...")
                trader.stop_trading()
            elif command == "status":
                trader.print_status()
            elif command == "quit":
                print("👋 프로그램을 종료합니다.")
                trader.stop_trading()
                break
            else:
                print("❌ 올바른 명령어를 입력하세요.")
                
        except KeyboardInterrupt:
            print("\\n👋 프로그램을 종료합니다.")
            trader.stop_trading()
            break
        except Exception as e:
            logger.error(f"명령 처리 오류: {e}")
            print(f"❌ 오류가 발생했습니다: {e}")


if __name__ == "__main__":
    main()