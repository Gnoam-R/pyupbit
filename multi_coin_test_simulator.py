#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
멀티 코인 테스트 시뮬레이터

실제 거래 없이 10개 코인을 동시에 모니터링하고
포트폴리오 기반 매매 전략을 테스트하는 시뮬레이터입니다.
"""

import time
import datetime
import logging
from typing import Dict, List, Optional
import json
import schedule

# Business Logic Imports
from business_logic.strategies.portfolio_strategy import PortfolioTradingStrategy
from business_logic.utils.config import TradingConfig
from business_logic.utils.logger import setup_logger

# 로깅 설정
logger = setup_logger('multi_coin_test_simulator', 'multi_coin_test_simulator.log')


class MultiCoinTestSimulator:
    """멀티 코인 테스트 시뮬레이터"""
    
    def __init__(self, seed_money: float = 1000000):
        """
        멀티 코인 테스트 시뮬레이터 초기화
        
        Args:
            seed_money: 시드머니 (기본 100만원)
        """
        self.seed_money = seed_money
        self.running = False
        
        # 설정 관리
        self.config_manager = TradingConfig("multi_coin_test_config.json")
        config = self.config_manager.get_config()
        
        # 테스트 모드 설정
        test_config = {
            "max_positions": 3,  # 테스트를 위해 3개로 제한
            "position_size": 0.25,  # 포지션당 25%
            "analysis_interval": 60,  # 1분 (테스트용)
            "min_score_for_buy": 65,  # 매수 기준 완화
            "min_score_for_sell": 45,  # 매도 기준 완화
            "stop_loss": 0.03,  # 3% 손절
            "take_profit": 0.10,  # 10% 익절
            "daily_max_loss": 0.05  # 일일 최대 손실 5%
        }
        config.update(test_config)
        
        # 포트폴리오 전략 초기화
        self.strategy = PortfolioTradingStrategy(config, seed_money)
        
        # 테스트 통계
        self.test_stats = {
            "start_time": datetime.datetime.now(),
            "total_signals": 0,
            "buy_signals": 0,
            "sell_signals": 0,
            "successful_trades": 0,
            "failed_trades": 0,
            "max_portfolio_value": seed_money,
            "min_portfolio_value": seed_money,
            "analysis_count": 0
        }
        
        logger.info(f"멀티 코인 테스트 시뮬레이터 초기화 완료")
        logger.info(f"시드머니: {seed_money:,.0f}원")
        logger.info(f"지원 코인: {', '.join(self.strategy.supported_coins)}")
    
    def update_test_stats(self, analysis_result: Dict, signals: List[Dict]):
        """테스트 통계 업데이트"""
        self.test_stats["analysis_count"] += 1
        self.test_stats["total_signals"] += len(signals)
        
        for signal in signals:
            if signal["action"] == "buy":
                self.test_stats["buy_signals"] += 1
            elif signal["action"] == "sell":
                self.test_stats["sell_signals"] += 1
        
        # 포트폴리오 가치 추적
        if analysis_result["action"] == "analyzed":
            portfolio_value = analysis_result["portfolio_summary"]["total_value"]
            self.test_stats["max_portfolio_value"] = max(self.test_stats["max_portfolio_value"], portfolio_value)
            self.test_stats["min_portfolio_value"] = min(self.test_stats["min_portfolio_value"], portfolio_value)
    
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
                return
            
            # 거래 신호 생성
            signals = self.strategy.generate_trading_signals(analysis_result)
            
            # 통계 업데이트
            self.update_test_stats(analysis_result, signals)
            
            if not signals:
                logger.debug("거래 신호 없음")
                return
            
            # 신호 실행
            for signal in signals:
                logger.info(f"거래 신호: {signal['action']} {signal['coin']} (이유: {signal['reason']})")
                
                result = self.strategy.execute_trading_signal(signal)
                
                if result["success"]:
                    logger.info(f"거래 성공: {signal['action']} {signal['coin']}")
                    self.test_stats["successful_trades"] += 1
                    
                    # 상세 로그
                    if signal["action"] == "buy":
                        logger.info(f"매수 완료: {result['coin']} {result['quantity']:.8f}개 @ {result['price']:,.0f}원")
                    elif signal["action"] == "sell":
                        logger.info(f"매도 완료: {result['coin']} {result['quantity']:.8f}개 @ {result['price']:,.0f}원")
                else:
                    logger.warning(f"거래 실패: {result['reason']}")
                    self.test_stats["failed_trades"] += 1
        
        except Exception as e:
            logger.error(f"트레이딩 루프 오류: {e}")
    
    def print_status(self):
        """현재 상태 출력"""
        try:
            print("\\n" + "=" * 100)
            print("멀티 코인 테스트 시뮬레이터 상태")
            print("=" * 100)
            
            # 테스트 통계
            runtime = datetime.datetime.now() - self.test_stats["start_time"]
            print(f"테스트 시간: {runtime}")
            print(f"분석 횟수: {self.test_stats['analysis_count']}")
            print(f"총 신호 수: {self.test_stats['total_signals']}")
            print(f"매수 신호: {self.test_stats['buy_signals']}")
            print(f"매도 신호: {self.test_stats['sell_signals']}")
            print(f"성공한 거래: {self.test_stats['successful_trades']}")
            print(f"실패한 거래: {self.test_stats['failed_trades']}")
            
            # 포트폴리오 성과
            max_value = self.test_stats["max_portfolio_value"]
            min_value = self.test_stats["min_portfolio_value"]
            max_return = (max_value - self.seed_money) / self.seed_money * 100
            min_return = (min_value - self.seed_money) / self.seed_money * 100
            
            print(f"최대 포트폴리오 가치: {max_value:,.0f}원 ({max_return:+.2f}%)")
            print(f"최소 포트폴리오 가치: {min_value:,.0f}원 ({min_return:+.2f}%)")
            
            # 포트폴리오 상태
            self.strategy.print_portfolio_status()
            
            # 거래 기회 요약
            print("\\n현재 거래 기회:")
            opportunities = self.strategy.get_trading_opportunities_summary()
            print(opportunities)
            
            print("=" * 100)
            
        except Exception as e:
            logger.error(f"상태 출력 오류: {e}")
    
    def print_detailed_coin_analysis(self):
        """상세 코인 분석 출력"""
        try:
            analysis_result = self.strategy.analyze_market_opportunities()
            
            if analysis_result["action"] != "analyzed":
                print(f"분석 불가: {analysis_result.get('reason', '알 수 없음')}")
                return
            
            print("\\n" + "=" * 100)
            print("상세 코인 분석")
            print("=" * 100)
            
            # 모든 코인 지표 출력
            coin_metrics = analysis_result["coin_metrics"]
            current_prices = analysis_result["current_prices"]
            
            print(f"{'코인':<6} {'가격':<10} {'점수':<6} {'RSI':<6} {'MACD':<8} {'BB':<10} {'모멘텀':<6} {'거래량':<6}")
            print("-" * 70)
            
            for coin in sorted(coin_metrics, key=lambda x: x.overall_score, reverse=True):
                price_str = f"{coin.current_price:,.0f}" if coin.current_price else "N/A"
                print(f"{coin.symbol:<6} {price_str:<10} {coin.overall_score:<6.1f} {coin.rsi:<6.1f} "
                      f"{coin.macd_signal:<8} {coin.bb_position:<10} {coin.momentum_score:<6.1f} {coin.volume_score:<6.1f}")
            
            print("=" * 100)
            
        except Exception as e:
            logger.error(f"상세 분석 출력 오류: {e}")
    
    def run_backtest(self, duration_minutes: int = 60):
        """백테스트 실행"""
        print(f"\\n백테스트 시작: {duration_minutes}분간 실행")
        
        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(minutes=duration_minutes)
        
        backtest_stats = {
            "start_value": self.strategy.get_portfolio_status()["portfolio_summary"]["total_value"],
            "trades": []
        }
        
        try:
            while datetime.datetime.now() < end_time and self.running:
                self.trading_loop()
                time.sleep(30)  # 30초마다 실행
                
                # 진행률 출력
                elapsed = datetime.datetime.now() - start_time
                progress = (elapsed.total_seconds() / (duration_minutes * 60)) * 100
                if int(progress) % 10 == 0:
                    print(f"백테스트 진행률: {progress:.1f}%")
        
        except KeyboardInterrupt:
            print("백테스트 중단됨")
        
        # 백테스트 결과
        final_value = self.strategy.get_portfolio_status()["portfolio_summary"]["total_value"]
        total_return = (final_value - backtest_stats["start_value"]) / backtest_stats["start_value"] * 100
        
        print(f"\\n백테스트 결과:")
        print(f"시작 가치: {backtest_stats['start_value']:,.0f}원")
        print(f"종료 가치: {final_value:,.0f}원")
        print(f"총 수익률: {total_return:+.2f}%")
        print(f"실행 시간: {datetime.datetime.now() - start_time}")
    
    def start_trading(self):
        """자동 매매 시작"""
        self.running = True
        logger.info("멀티 코인 테스트 시뮬레이터 시작")
        
        # 주기적 상태 출력 스케줄
        schedule.every(5).minutes.do(self.print_status)
        
        try:
            while self.running:
                # 스케줄된 작업 실행
                schedule.run_pending()
                
                # 트레이딩 루프 실행
                self.trading_loop()
                
                # 대기 (30초)
                time.sleep(30)
        
        except KeyboardInterrupt:
            self.stop_trading()
        except Exception as e:
            logger.error(f"시뮬레이터 실행 오류: {e}")
            self.stop_trading()
    
    def stop_trading(self):
        """자동 매매 중지"""
        self.running = False
        logger.info("멀티 코인 테스트 시뮬레이터 중지")
        
        # 최종 리포트
        self.print_final_report()
    
    def print_final_report(self):
        """최종 테스트 리포트"""
        try:
            portfolio_status = self.strategy.get_portfolio_status()
            portfolio_summary = portfolio_status["portfolio_summary"]
            
            print("\\n" + "=" * 100)
            print("최종 테스트 리포트")
            print("=" * 100)
            
            # 기본 정보
            runtime = datetime.datetime.now() - self.test_stats["start_time"]
            print(f"테스트 기간: {runtime}")
            print(f"시드머니: {self.seed_money:,.0f}원")
            print(f"최종 자산: {portfolio_summary['total_value']:,.0f}원")
            print(f"총 수익: {portfolio_summary['total_pnl']:,.0f}원 ({portfolio_summary['total_return']:.2f}%)")
            
            # 거래 통계
            print(f"\\n거래 통계:")
            print(f"총 신호 수: {self.test_stats['total_signals']}")
            print(f"성공한 거래: {self.test_stats['successful_trades']}")
            print(f"실패한 거래: {self.test_stats['failed_trades']}")
            print(f"총 거래 수: {portfolio_summary['total_trades']}")
            
            # 성과 지표
            max_dd = (self.test_stats["max_portfolio_value"] - self.test_stats["min_portfolio_value"]) / self.test_stats["max_portfolio_value"] * 100
            print(f"\\n성과 지표:")
            print(f"최대 드로다운: {max_dd:.2f}%")
            print(f"최대 포트폴리오 가치: {self.test_stats['max_portfolio_value']:,.0f}원")
            print(f"최소 포트폴리오 가치: {self.test_stats['min_portfolio_value']:,.0f}원")
            
            # 포지션 요약
            if portfolio_summary['positions']:
                print(f"\\n최종 포지션:")
                for symbol, pos in portfolio_summary['positions'].items():
                    print(f"  {symbol}: {pos['unrealized_pnl']:,.0f}원 (비중: {pos['weight']:.1f}%)")
            
            print("=" * 100)
            
        except Exception as e:
            logger.error(f"최종 리포트 출력 오류: {e}")
    
    def save_test_results(self, filename: str = None):
        """테스트 결과 저장"""
        if filename is None:
            filename = f"multi_coin_test_results_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            portfolio_status = self.strategy.get_portfolio_status()
            
            results = {
                "test_info": {
                    "start_time": self.test_stats["start_time"].isoformat(),
                    "end_time": datetime.datetime.now().isoformat(),
                    "seed_money": self.seed_money,
                    "supported_coins": self.strategy.supported_coins,
                    "config": self.config_manager.get_config()
                },
                "test_stats": self.test_stats,
                "final_portfolio": portfolio_status["portfolio_summary"]
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"테스트 결과 저장 완료: {filename}")
            print(f"테스트 결과가 {filename}에 저장되었습니다.")
            
        except Exception as e:
            logger.error(f"테스트 결과 저장 오류: {e}")


def main():
    """메인 함수"""
    print("=" * 100)
    print("멀티 코인 테스트 시뮬레이터")
    print("10개 코인 포트폴리오 기반 매매 전략 테스트")
    print("=" * 100)
    
    # 시드머니 설정
    seed_money = 1000000  # 100만원
    
    # 시뮬레이터 초기화
    simulator = MultiCoinTestSimulator(seed_money)
    
    # 초기 상태 출력
    simulator.print_status()
    
    # 사용자 입력 루프
    while True:
        print("\\n명령어:")
        print("1. start - 테스트 시작")
        print("2. stop - 테스트 중지")
        print("3. status - 현재 상태 확인")
        print("4. analysis - 상세 코인 분석")
        print("5. backtest - 백테스트 실행")
        print("6. report - 최종 리포트")
        print("7. save - 결과 저장")
        print("8. config - 설정 확인")
        print("9. quit - 프로그램 종료")
        
        command = input("\\n명령어를 입력하세요: ").strip().lower()
        
        if command in ["1", "start"]:
            simulator.start_trading()
        elif command in ["2", "stop"]:
            simulator.stop_trading()
        elif command in ["3", "status"]:
            simulator.print_status()
        elif command in ["4", "analysis"]:
            simulator.print_detailed_coin_analysis()
        elif command in ["5", "backtest"]:
            duration = input("백테스트 실행 시간(분, 기본 60): ").strip()
            try:
                duration = int(duration) if duration else 60
                simulator.run_backtest(duration)
            except ValueError:
                print("올바른 숫자를 입력하세요.")
        elif command in ["6", "report"]:
            simulator.print_final_report()
        elif command in ["7", "save"]:
            simulator.save_test_results()
        elif command in ["8", "config"]:
            print("현재 설정:")
            config = simulator.config_manager.get_config()
            for key, value in config.items():
                print(f"  {key}: {value}")
        elif command in ["9", "quit"]:
            simulator.stop_trading()
            break
        else:
            print("올바른 명령어를 입력하세요.")


if __name__ == "__main__":
    main()