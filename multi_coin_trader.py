#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
멀티 코인 자동 매매 프로그램

이 프로그램은 여러 코인을 동시에 모니터링하고 포트폴리오를 관리하여
최적의 수익을 추구하는 자동 매매 시스템입니다.

주요 기능:
1. 10개 코인 동시 모니터링 (BTC, ETH, BNB, SOL, ADA, DOGE, MATIC, DOT, AVAX, SHIB)
2. 포트폴리오 기반 리스크 관리
3. 기술적 분석 기반 매매 신호
4. 자동 리밸런싱
5. 실시간 포트폴리오 추적
"""

import pyupbit
import time
import datetime
import logging
from typing import Dict, List, Optional
import json
import os
from threading import Thread
import schedule

# Business Logic Imports
from business_logic.strategies.portfolio_strategy import PortfolioTradingStrategy
from business_logic.utils.config import TradingConfig
from business_logic.utils.logger import setup_logger

# 로깅 설정
logger = setup_logger('multi_coin_trader', 'multi_coin_trader.log')


class MultiCoinAutoTrader:
    """멀티 코인 자동 매매 클래스"""
    
    def __init__(self, access_key: str, secret_key: str, initial_balance: float = 1000000):
        """
        멀티 코인 자동 매매 초기화
        
        Args:
            access_key: 업비트 API 액세스 키
            secret_key: 업비트 API 시크릿 키
            initial_balance: 초기 잔고 (실제 거래 시 무시됨)
        """
        self.upbit = pyupbit.Upbit(access_key, secret_key)
        self.running = False
        self.initial_balance = initial_balance
        
        # 설정 관리
        self.config_manager = TradingConfig("multi_coin_config.json")
        config = self.config_manager.get_config()
        
        # 멀티 코인 설정 추가
        multi_coin_config = {
            "max_positions": 5,
            "position_size": 0.2,
            "analysis_interval": 300,  # 5분
            "min_score_for_buy": 70,
            "min_score_for_sell": 40,
            "emergency_stop_loss": 0.05,
            "daily_max_loss": 0.03
        }
        config.update(multi_coin_config)
        
        # 포트폴리오 전략 초기화
        self.strategy = PortfolioTradingStrategy(config, initial_balance)
        
        # 통계 정보
        self.session_stats = {
            "start_time": datetime.datetime.now(),
            "total_signals": 0,
            "executed_trades": 0,
            "errors": 0
        }
        
        logger.info("멀티 코인 자동 매매 시스템 초기화 완료")
        logger.info(f"지원 코인: {', '.join(self.strategy.supported_coins)}")
    
    def is_real_trading_mode(self) -> bool:
        """실제 거래 모드 확인"""
        return hasattr(self.upbit, 'get_balances')
    
    def get_real_account_info(self) -> Optional[Dict]:
        """실제 계정 정보 조회"""
        if not self.is_real_trading_mode():
            return None
        
        try:
            balances = self.upbit.get_balances()
            krw_balance = self.upbit.get_balance("KRW")
            
            return {
                "krw_balance": krw_balance,
                "balances": balances,
                "total_krw_value": sum(
                    balance['balance'] * balance['avg_buy_price'] 
                    for balance in balances if balance['currency'] != 'KRW'
                ) + krw_balance
            }
        except Exception as e:
            logger.error(f"실제 계정 정보 조회 오류: {e}")
            return None
    
    def execute_real_trade(self, signal: Dict) -> Dict:
        """실제 거래 실행"""
        if not self.is_real_trading_mode():
            return {"success": False, "reason": "API 키 없음"}
        
        try:
            coin_symbol = signal["coin"]
            ticker = f"KRW-{coin_symbol}"
            
            if signal["action"] == "buy":
                # 실제 매수
                krw_balance = self.upbit.get_balance("KRW")
                buy_amount = krw_balance * self.strategy.position_size
                
                if buy_amount < 5000:
                    return {"success": False, "reason": "매수 금액 부족"}
                
                current_price = pyupbit.get_current_price(ticker)
                if not current_price:
                    return {"success": False, "reason": "가격 정보 없음"}
                
                # 시장가 매수
                result = self.upbit.buy_market_order(ticker, buy_amount)
                
                if result:
                    logger.info(f"실제 매수 완료: {coin_symbol} {buy_amount:,.0f}원")
                    return {
                        "success": True,
                        "action": "buy",
                        "coin": coin_symbol,
                        "amount": buy_amount,
                        "order_id": result.get('uuid')
                    }
                else:
                    return {"success": False, "reason": "매수 주문 실패"}
            
            elif signal["action"] == "sell":
                # 실제 매도
                coin_balance = self.upbit.get_balance(coin_symbol)
                if coin_balance <= 0:
                    return {"success": False, "reason": "보유 코인 없음"}
                
                # 부분 매도 또는 전량 매도
                sell_amount = coin_balance
                if signal.get("urgency") == "medium":
                    sell_amount = coin_balance * 0.5
                
                # 시장가 매도
                result = self.upbit.sell_market_order(ticker, sell_amount)
                
                if result:
                    logger.info(f"실제 매도 완료: {coin_symbol} {sell_amount:.8f}개")
                    return {
                        "success": True,
                        "action": "sell",
                        "coin": coin_symbol,
                        "amount": sell_amount,
                        "order_id": result.get('uuid')
                    }
                else:
                    return {"success": False, "reason": "매도 주문 실패"}
            
            return {"success": False, "reason": "알 수 없는 액션"}
            
        except Exception as e:
            logger.error(f"실제 거래 실행 오류: {e}")
            return {"success": False, "reason": str(e)}
    
    def trading_loop(self):
        """메인 트레이딩 루프"""
        try:
            # 시장 분석
            analysis_result = self.strategy.analyze_market_opportunities()
            
            if analysis_result["action"] == "wait":
                logger.debug(f"대기 중: {analysis_result['reason']}")
                return
            
            if analysis_result["action"] == "error":
                logger.error(f"분석 오류: {analysis_result['reason']}")
                self.session_stats["errors"] += 1
                return
            
            # 거래 신호 생성
            signals = self.strategy.generate_trading_signals(analysis_result)
            
            if not signals:
                logger.debug("거래 신호 없음")
                return
            
            # 신호 실행
            for signal in signals:
                self.session_stats["total_signals"] += 1
                
                # 시뮬레이션 거래 (포트폴리오 관리)
                sim_result = self.strategy.execute_trading_signal(signal)
                
                if sim_result["success"]:
                    logger.info(f"시뮬레이션 거래 성공: {signal['action']} {signal['coin']}")
                    
                    # 실제 거래 실행 (API 키가 있는 경우)
                    if self.is_real_trading_mode():
                        real_result = self.execute_real_trade(signal)
                        if real_result["success"]:
                            logger.info(f"실제 거래 성공: {signal['action']} {signal['coin']}")
                            self.session_stats["executed_trades"] += 1
                        else:
                            logger.warning(f"실제 거래 실패: {real_result['reason']}")
                    else:
                        logger.info("시뮬레이션 모드 - 실제 거래 없음")
                else:
                    logger.warning(f"시뮬레이션 거래 실패: {sim_result['reason']}")
        
        except Exception as e:
            logger.error(f"트레이딩 루프 오류: {e}")
            self.session_stats["errors"] += 1
    
    def print_status(self):
        """현재 상태 출력"""
        try:
            print("\\n" + "=" * 100)
            print("멀티 코인 자동 매매 시스템 상태")
            print("=" * 100)
            
            # 세션 통계
            runtime = datetime.datetime.now() - self.session_stats["start_time"]
            print(f"운영 시간: {runtime}")
            print(f"총 신호 수: {self.session_stats['total_signals']}")
            print(f"실행된 거래: {self.session_stats['executed_trades']}")
            print(f"오류 수: {self.session_stats['errors']}")
            
            # 포트폴리오 상태
            self.strategy.print_portfolio_status()
            
            # 거래 기회 요약
            print("\\n현재 거래 기회:")
            opportunities = self.strategy.get_trading_opportunities_summary()
            print(opportunities)
            
            # 실제 계정 정보 (있는 경우)
            if self.is_real_trading_mode():
                real_account = self.get_real_account_info()
                if real_account:
                    print("\\n실제 계정 정보:")
                    print(f"원화 잔고: {real_account['krw_balance']:,.0f}원")
                    print(f"총 자산 가치: {real_account['total_krw_value']:,.0f}원")
            
            print("=" * 100)
            
        except Exception as e:
            logger.error(f"상태 출력 오류: {e}")
    
    def print_detailed_market_analysis(self):
        """상세 시장 분석 출력"""
        try:
            analysis_result = self.strategy.analyze_market_opportunities()
            
            if analysis_result["action"] != "analyzed":
                print(f"분석 불가: {analysis_result.get('reason', '알 수 없음')}")
                return
            
            print("\\n" + "=" * 100)
            print("상세 시장 분석")
            print("=" * 100)
            
            # 시장 요약
            market_summary = analysis_result["market_summary"]
            print(f"시장 트렌드: {market_summary['market_trend']}")
            print(f"시장 건강도: {market_summary['health_score']:.1f}/100")
            print(f"강세 코인: {market_summary['bullish_count']}개")
            print(f"약세 코인: {market_summary['bearish_count']}개")
            
            # 상위 코인
            print("\\n상위 코인 (점수순):")
            for coin in market_summary['top_coins']:
                print(f"  {coin['symbol']}: {coin['score']:.1f}점")
            
            # 매수 후보
            buy_candidates = analysis_result["buy_candidates"]
            if buy_candidates:
                print("\\n매수 후보:")
                for coin in buy_candidates:
                    print(f"  {coin.symbol}: {coin.overall_score:.1f}점 "
                          f"(RSI: {coin.rsi:.1f}, MACD: {coin.macd_signal}, BB: {coin.bb_position})")
            
            # 매도 후보
            sell_candidates = analysis_result["sell_candidates"]
            if sell_candidates:
                print("\\n매도 후보:")
                for coin in sell_candidates:
                    print(f"  {coin.symbol}: {coin.overall_score:.1f}점 "
                          f"(RSI: {coin.rsi:.1f}, MACD: {coin.macd_signal}, BB: {coin.bb_position})")
            
            # 리스크 분석
            risk_analysis = analysis_result["risk_analysis"]
            print(f"\\n리스크 레벨: {risk_analysis['risk_level']}")
            print(f"리스크 상태: {risk_analysis['reason']}")
            
            print("=" * 100)
            
        except Exception as e:
            logger.error(f"상세 분석 출력 오류: {e}")
    
    def start_trading(self):
        """자동 매매 시작"""
        self.running = True
        logger.info("멀티 코인 자동 매매 시작")
        
        # 주기적 상태 출력 스케줄
        schedule.every(10).minutes.do(self.print_status)
        
        try:
            while self.running:
                # 스케줄된 작업 실행
                schedule.run_pending()
                
                # 트레이딩 루프 실행
                self.trading_loop()
                
                # 대기 (1분)
                time.sleep(60)
        
        except KeyboardInterrupt:
            self.stop_trading()
        except Exception as e:
            logger.error(f"자동 매매 실행 오류: {e}")
            self.stop_trading()
    
    def stop_trading(self):
        """자동 매매 중지"""
        self.running = False
        logger.info("멀티 코인 자동 매매 중지")
        
        # 최종 상태 출력
        self.print_status()


def main():
    """메인 함수"""
    print("=" * 100)
    print("멀티 코인 자동 매매 시스템")
    print("10개 코인 동시 모니터링 및 포트폴리오 관리")
    print("=" * 100)
    
    # API 키 설정
    ACCESS_KEY = "YOUR_ACCESS_KEY"
    SECRET_KEY = "YOUR_SECRET_KEY"
    
    # 파일에서 API 키 로드 시도
    try:
        with open("upbit_keys.txt", "r") as f:
            lines = f.readlines()
            ACCESS_KEY = lines[0].strip()
            SECRET_KEY = lines[1].strip()
        print("API 키 로드 완료 - 실제 거래 모드")
    except FileNotFoundError:
        print("upbit_keys.txt 파일이 없습니다 - 시뮬레이션 모드")
        ACCESS_KEY = None
        SECRET_KEY = None
    except Exception as e:
        print(f"API 키 로드 오류: {e} - 시뮬레이션 모드")
        ACCESS_KEY = None
        SECRET_KEY = None
    
    # 초기 잔고 설정 (시뮬레이션용)
    initial_balance = 1000000  # 100만원
    
    # 트레이더 초기화
    trader = MultiCoinAutoTrader(ACCESS_KEY, SECRET_KEY, initial_balance)
    
    # 초기 상태 출력
    trader.print_status()
    
    # 사용자 입력 루프
    while True:
        print("\\n명령어:")
        print("1. start - 자동 매매 시작")
        print("2. stop - 자동 매매 중지")
        print("3. status - 현재 상태 확인")
        print("4. analysis - 상세 시장 분석")
        print("5. config - 설정 확인")
        print("6. quit - 프로그램 종료")
        
        command = input("\\n명령어를 입력하세요: ").strip().lower()
        
        if command in ["1", "start"]:
            trader.start_trading()
        elif command in ["2", "stop"]:
            trader.stop_trading()
        elif command in ["3", "status"]:
            trader.print_status()
        elif command in ["4", "analysis"]:
            trader.print_detailed_market_analysis()
        elif command in ["5", "config"]:
            print("현재 설정:")
            config = trader.config_manager.get_config()
            for key, value in config.items():
                print(f"  {key}: {value}")
        elif command in ["6", "quit"]:
            trader.stop_trading()
            break
        else:
            print("올바른 명령어를 입력하세요.")


if __name__ == "__main__":
    main()