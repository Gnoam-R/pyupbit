#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
멀티 코인 자동 매매 프로그램

이 프로그램은 pyupbit 라이브러리를 활용하여 다음 기능들을 구현합니다:
1. 멀티 코인 동시 거래 (BTC, ETH, MASK, SOL, PEPE)
2. 실시간 시세 모니터링
3. 기술적 분석 기반 자동 매매
4. 자산 배분 관리
5. 리스크 관리 및 손절/익절
6. 포트폴리오 관리
7. 실시간 로그 및 알림

주요 전략:
- 이동평균선 기반 매매 신호
- RSI 과매수/과매도 지표
- 볼린저 밴드 브레이크아웃
- 스토캐스틱 오실레이터
- MACD 다이버전스
"""

import pyupbit
import os
import sys
import time
import datetime
import schedule
from threading import Thread

# Business Logic Imports
from business_logic.core.multi_coin_trader import MultiCoinTrader
from business_logic.utils.logger import setup_logger

# 로깅 설정
logger = setup_logger('multi_coin_trader', 'bitcoin_trader.log')


def load_api_keys():
    """API 키 로드"""
    try:
        with open("upbit_keys.txt", "r") as f:
            lines = f.readlines()
            access_key = lines[0].strip()
            secret_key = lines[1].strip()
            return access_key, secret_key
    except FileNotFoundError:
        logger.error("upbit_keys.txt 파일이 없습니다. API 키를 직접 설정하세요.")
        return None, None
    except Exception as e:
        logger.error(f"API 키 로드 오류: {e}")
        return None, None


def main():
    """메인 함수"""
    print("=" * 100)
    print("멀티 코인 자동 매매 프로그램")
    print("지원 코인: BTC, ETH, MASK, SOL, PEPE")
    print("=" * 100)
    
    # API 키 로드
    access_key, secret_key = load_api_keys()
    if not access_key or not secret_key:
        return
    
    # 업비트 클라이언트 초기화
    upbit = pyupbit.Upbit(access_key, secret_key)
    
    # 계정 정보 확인
    try:
        balances = upbit.get_balances()
        if not balances:
            logger.error("계정 정보 조회 실패. API 키를 확인하세요.")
            return
        
        krw_balance = upbit.get_balance("KRW")
        logger.info(f"KRW 잔고: {krw_balance:,.0f}원")
        
    except Exception as e:
        logger.error(f"계정 정보 확인 오류: {e}")
        return
    
    # 멀티 코인 트레이더 초기화 (실제 거래 모드)
    trader = MultiCoinTrader(upbit_client=upbit, is_test_mode=False)
    
    # 초기 상태 출력
    trader.print_status()
    
    # 사용자 입력 처리
    while True:
        print("\n명령어:")
        print("1. start - 자동 매매 시작")
        print("2. stop - 자동 매매 중지")
        print("3. status - 현재 상태 확인")
        print("4. portfolio - 포트폴리오 요약")
        print("5. history - 거래 내역")
        print("6. config - 설정 확인")
        print("7. quit - 프로그램 종료")
        
        command = input("\n명령어를 입력하세요: ").strip().lower()
        
        if command in ["1", "start"]:
            logger.info("자동 매매 시작")
            trader.start_trading()
        
        elif command in ["2", "stop"]:
            logger.info("자동 매매 중지")
            trader.stop_trading()
        
        elif command in ["3", "status"]:
            trader.print_status()
        
        elif command in ["4", "portfolio"]:
            summary = trader.get_portfolio_summary()
            print("\n포트폴리오 요약:")
            print(f"총 거래 수: {summary['total_trades']}")
            print(f"총 수익: {summary['total_profit']:,.0f}원")
            print(f"승률: {summary['win_rate']:.1f}%")
            print(f"활성 포지션: {summary['active_positions']}")
        
        elif command in ["5", "history"]:
            history = trader.get_trade_history()
            print(f"\n최근 거래 내역 (최대 10건):")
            for trade in history[-10:]:
                print(f"{trade['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} - "
                      f"[{trade['coin']}] {trade['type'].upper()}: {trade['price']:,.0f}원")
        
        elif command in ["6", "config"]:
            config = trader.config
            print("\n현재 설정:")
            for key, value in config.items():
                print(f"  {key}: {value}")
        
        elif command in ["7", "quit"]:
            trader.stop_trading()
            logger.info("프로그램 종료")
            break
        
        else:
            print("올바른 명령어를 입력하세요.")


if __name__ == "__main__":
    main()