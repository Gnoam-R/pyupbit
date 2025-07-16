#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
실제 암호화폐 자동 매매 프로그램

실제 업비트 API를 사용하여 실제 자산으로 매매를 수행합니다.
"""

import pyupbit
import os
import sys

# Business Logic Imports
from business_logic.core.trading_engine import TradingEngine
from business_logic.core.asset_manager import RealAssetManager
from business_logic.executors.trading_executor import RealTradeExecutor
from business_logic.utils.coin_selector import select_coin, get_coin_name
from business_logic.utils.logger import setup_logger
from business_logic.utils.format_helper import format_profit_rate, format_currency, format_percentage

# 로깅 설정
logger = setup_logger('bitcoin_auto_trader', 'bitcoin_trader.log')


class RealCryptoTrader:
    """실제 암호화폐 자동 매매 클래스"""
    
    def __init__(self, access_key: str, secret_key: str, target_coin: str):
        """
        실제 트레이더 초기화
        
        Args:
            access_key: 업비트 API 액세스 키
            secret_key: 업비트 API 시크릿 키
            target_coin: 대상 코인 심볼
        """
        self.target_coin = target_coin
        self.upbit = pyupbit.Upbit(access_key, secret_key)
        
        # 실제 모드 매니저들 초기화
        self.asset_manager = RealAssetManager(self.upbit, target_coin)
        self.trade_executor = RealTradeExecutor(self.upbit, target_coin)
        
        # 트레이딩 엔진 초기화 (실제 모드)
        self.engine = TradingEngine(
            target_coin=target_coin,
            asset_manager=self.asset_manager,
            trade_executor=self.trade_executor,
            is_test_mode=False
        )
        
        logger.info(f"실제 트레이더 초기화 완료 - 대상 코인: {get_coin_name(target_coin)}")
    
    def validate_api_keys(self) -> bool:
        """API 키 유효성 검증"""
        try:
            account_info = self.asset_manager.get_account_info()
            if account_info is None:
                logger.error("API 키 검증 실패: 계정 정보를 가져올 수 없습니다.")
                return False
            
            logger.info("API 키 검증 성공")
            return True
        except Exception as e:
            logger.error(f"API 키 검증 오류: {e}")
            return False
    
    def print_account_summary(self):
        """계정 요약 정보 출력"""
        try:
            account_info = self.asset_manager.get_account_info()
            current_price = self.engine.get_current_price()
            
            if not account_info or not current_price:
                print("계정 정보를 가져올 수 없습니다.")
                return
            
            print("=" * 60)
            print(f"🪙 {get_coin_name(self.target_coin)} 실제 자동 매매 프로그램")
            print("=" * 60)
            print(f"현재 가격: {current_price:,.0f}원")
            print(f"원화 잔고: {account_info['krw_balance']:,.0f}원")
            print(f"{self.target_coin} 잔고: {account_info['coin_balance']:.8f}{self.target_coin}")
            print("=" * 60)
            
        except Exception as e:
            logger.error(f"계정 요약 정보 출력 오류: {e}")
    
    def start_trading(self):
        """자동 매매 시작"""
        self.engine.start_trading()
    
    def stop_trading(self):
        """자동 매매 중지"""
        self.engine.stop_trading()
    
    def print_status(self):
        """현재 상태 출력"""
        self.engine.print_status()
    
    def get_config(self):
        """현재 설정 조회"""
        return self.engine.get_config()
    
    def save_config(self):
        """설정 저장"""
        self.engine.save_config()
    
    def load_config(self):
        """설정 로드"""
        self.engine.load_config()


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
        
        logger.error("API 키를 찾을 수 없습니다.")
        return None, None
        
    except Exception as e:
        logger.error(f"API 키 로드 오류: {e}")
        return None, None


def main():
    """메인 함수"""
    print("🚀 실제 암호화폐 자동 매매 프로그램 시작")
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
    
    # 코인 선택
    selected_coin = select_coin()
    
    # 트레이더 초기화
    trader = RealCryptoTrader(access_key, secret_key, selected_coin)
    
    # API 키 검증
    if not trader.validate_api_keys():
        print("❌ API 키 검증 실패. 키를 확인해주세요.")
        return
    
    # 계정 요약 정보 출력
    trader.print_account_summary()
    
    # 사용자 입력 처리
    print("\n📋 사용 가능한 명령어:")
    print("  start  - 자동 매매 시작")
    print("  stop   - 자동 매매 중지")
    print("  status - 현재 상태 확인")
    print("  config - 현재 설정 보기")
    print("  quit   - 프로그램 종료")
    
    while True:
        try:
            command = input("\n명령어를 입력하세요: ").strip().lower()
            
            if command == "start":
                print("🚀 자동 매매를 시작합니다...")
                trader.start_trading()
                
            elif command == "stop":
                print("🛑 자동 매매를 중지합니다...")
                trader.stop_trading()
                
            elif command == "status":
                trader.print_status()
                
            elif command == "config":
                print("⚙️ 현재 설정:")
                config = trader.get_config()
                for key, value in config.items():
                    print(f"  {key}: {value}")
                    
            elif command == "quit":
                print("👋 프로그램을 종료합니다...")
                trader.stop_trading()
                break
                
            else:
                print("❌ 올바른 명령어를 입력하세요.")
                
        except KeyboardInterrupt:
            print("\n🛑 프로그램을 중지합니다...")
            trader.stop_trading()
            break
        except Exception as e:
            logger.error(f"명령어 처리 오류: {e}")
            print(f"❌ 오류가 발생했습니다: {e}")


if __name__ == "__main__":
    main()