#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
멀티 코인 테스트 모드 시뮬레이터

실제 거래 없이 내부적으로 가상 자산을 관리하여 멀티 코인 매매 로직을 테스트하는 시뮬레이터입니다.
모든 지원 코인(BTC, ETH, MASK, SOL, PEPE)에 대해 동시에 매매 전략을 테스트합니다.
기본 100만원의 시드머니로 시작하여 실제 시세를 기반으로 가상 매매를 수행합니다.
"""

import datetime
import json
import os

# Business Logic Imports
from business_logic.core.multi_coin_trader import MultiCoinTrader
from business_logic.utils.logger import setup_logger

# 로깅 설정
logger = setup_logger('multi_coin_simulator', 'test_trading_simulator.log')


class MultiCoinTradingSimulator:
    """멀티 코인 테스트 모드 시뮬레이터"""
    
    def __init__(self, seed_money: float = 1000000):
        """
        멀티 코인 시뮬레이터 초기화
        
        Args:
            seed_money: 시드머니 (기본 100만원)
        """
        self.seed_money = seed_money
        self.start_time = None
        
        # 멀티 코인 트레이더 초기화 (테스트 모드)
        self.trader = MultiCoinTrader(upbit_client=None, is_test_mode=True, seed_money=seed_money)
        
        logger.info(f"멀티 코인 테스트 시뮬레이터 초기화 완료")
        logger.info(f"시드머니: {seed_money:,.0f}원")
        logger.info(f"지원 코인: {', '.join(self.trader.supported_coins)}")
    
    def start_simulation(self):
        """시뮬레이션 시작"""
        self.start_time = datetime.datetime.now()
        logger.info("멀티 코인 테스트 시뮬레이션 시작")
        
        # 초기 상태 출력
        self.trader.print_status()
        
        # 트레이더 시작
        self.trader.start_trading()
    
    def stop_simulation(self):
        """시뮬레이션 중지"""
        self.trader.stop_trading()
        logger.info("멀티 코인 테스트 시뮬레이션 중지")
    
    def get_simulation_results(self) -> dict:
        """시뮬레이션 결과 반환"""
        portfolio_summary = self.trader.get_portfolio_summary()
        trade_history = self.trader.get_trade_history()
        
        # 총 자산 가치 계산
        total_value = 0
        current_prices = self.trader.get_current_prices()
        
        for coin in self.trader.supported_coins:
            asset_manager = self.trader.asset_managers[coin]
            coin_balance = asset_manager.get_balance(coin)
            krw_balance = asset_manager.get_balance("KRW")
            
            if coin in current_prices and current_prices[coin]:
                coin_value = coin_balance * current_prices[coin]
                total_value += krw_balance + coin_value
        
        # 전체 KRW 잔고 추가
        total_value += self.trader.get_total_krw_balance()
        
        return {
            "test_info": {
                "seed_money": self.seed_money,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": datetime.datetime.now().isoformat(),
                "supported_coins": self.trader.supported_coins,
                "config": self.trader.config
            },
            "portfolio_summary": portfolio_summary,
            "financial_results": {
                "initial_value": self.seed_money,
                "final_value": total_value,
                "total_profit_loss": total_value - self.seed_money,
                "profit_rate": ((total_value - self.seed_money) / self.seed_money) * 100
            },
            "trade_history": [
                {
                    "timestamp": trade['timestamp'].isoformat(),
                    "coin": trade['coin'],
                    "type": trade['type'],
                    "price": trade['price'],
                    "amount": trade['amount'],
                    "total_krw": trade['total_krw'],
                    "profit": trade.get('profit', 0),
                    "reason": trade['reason']
                } for trade in trade_history
            ]
        }
    
    def save_results(self, filename: str = None):
        """결과 저장"""
        if filename is None:
            filename = f"multi_coin_test_results_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            results = self.get_simulation_results()
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"테스트 결과 저장 완료: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"테스트 결과 저장 오류: {e}")
            return None
    
    def print_detailed_report(self):
        """상세 리포트 출력"""
        results = self.get_simulation_results()
        
        print("\n" + "=" * 100)
        print("멀티 코인 테스트 시뮬레이션 상세 리포트")
        print("=" * 100)
        
        # 기본 정보
        test_info = results['test_info']
        print(f"시드머니: {test_info['seed_money']:,.0f}원")
        print(f"지원 코인: {', '.join(test_info['supported_coins'])}")
        if test_info['start_time']:
            start_time = datetime.datetime.fromisoformat(test_info['start_time'])
            end_time = datetime.datetime.fromisoformat(test_info['end_time'])
            duration = end_time - start_time
            print(f"테스트 기간: {duration}")
        
        # 재무 결과
        financial = results['financial_results']
        print(f"\n최종 자산: {financial['final_value']:,.0f}원")
        print(f"총 손익: {financial['total_profit_loss']:,.0f}원 ({financial['profit_rate']:+.2f}%)")
        
        # 포트폴리오 요약
        portfolio = results['portfolio_summary']
        print(f"\n거래 통계:")
        print(f"  총 거래 수: {portfolio['total_trades']}")
        print(f"  승률: {portfolio['win_rate']:.1f}% ({portfolio['win_count']}/{portfolio['total_trades']})")
        print(f"  거래 수익: {portfolio['total_profit']:,.0f}원")
        print(f"  활성 포지션: {portfolio['active_positions']}")
        
        # 코인별 상세 결과
        print(f"\n코인별 상세 결과:")
        print("-" * 80)
        
        for coin, details in portfolio['coin_details'].items():
            position = details['position']
            stats = details['statistics']
            
            print(f"\n[{coin}]")
            print(f"  현재가: {details['current_price']:,.0f}원" if details['current_price'] else "  현재가: 조회 실패")
            print(f"  거래 수: {stats['total_trades']}")
            print(f"  수익: {stats['total_profit']:,.0f}원")
            print(f"  승률: {stats['win_rate']:.1f}% ({stats['win_count']}/{stats['total_trades']})")
            
            if position['is_holding']:
                print(f"  포지션: 보유 중 (매수가: {position['buy_price']:,.0f}원)")
                print(f"  보유량: {position['buy_amount']:.8f}{coin}")
            else:
                print(f"  포지션: 없음")
        
        # 최근 거래 내역
        trade_history = results['trade_history']
        if trade_history:
            print(f"\n최근 거래 내역 (최대 20건):")
            print("-" * 80)
            for trade in trade_history[-20:]:
                timestamp = datetime.datetime.fromisoformat(trade['timestamp'])
                print(f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} - "
                      f"[{trade['coin']}] {trade['type'].upper()}: {trade['price']:,.0f}원")
                if trade['type'] == 'sell' and trade['profit'] != 0:
                    print(f"  -> 수익: {trade['profit']:,.0f}원")
        
        print("=" * 100)


def main():
    """메인 함수"""
    print("=" * 100)
    print("멀티 코인 자동 매매 테스트 시뮬레이터")
    print("실제 거래 없이 가상 자산으로 멀티 코인 매매 로직을 테스트합니다.")
    print("지원 코인: BTC, ETH, MASK, SOL, PEPE")
    print("=" * 100)
    
    # 시드머니 설정
    seed_money = 1000000  # 100만원
    
    # 시뮬레이터 초기화
    simulator = MultiCoinTradingSimulator(seed_money)
    
    print(f"\n시드머니: {seed_money:,.0f}원")
    print(f"모든 지원 코인에 대해 동시에 매매 전략을 테스트합니다.")
    
    # 사용자 입력 처리
    while True:
        print("\n명령어:")
        print("1. start - 테스트 시작")
        print("2. stop - 테스트 중지")
        print("3. status - 현재 상태 확인")
        print("4. portfolio - 포트폴리오 요약")
        print("5. history - 거래 내역")
        print("6. report - 상세 리포트")
        print("7. save - 결과 저장")
        print("8. quit - 프로그램 종료")
        
        command = input("\n명령어를 입력하세요: ").strip().lower()
        
        if command in ["1", "start"]:
            simulator.start_simulation()
        
        elif command in ["2", "stop"]:
            simulator.stop_simulation()
        
        elif command in ["3", "status"]:
            simulator.trader.print_status()
        
        elif command in ["4", "portfolio"]:
            summary = simulator.trader.get_portfolio_summary()
            print("\n포트폴리오 요약:")
            print(f"총 거래 수: {summary['total_trades']}")
            print(f"총 수익: {summary['total_profit']:,.0f}원")
            print(f"승률: {summary['win_rate']:.1f}%")
            print(f"활성 포지션: {summary['active_positions']}")
        
        elif command in ["5", "history"]:
            history = simulator.trader.get_trade_history()
            print(f"\n최근 거래 내역 (최대 10건):")
            for trade in history[-10:]:
                print(f"{trade['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} - "
                      f"[{trade['coin']}] {trade['type'].upper()}: {trade['price']:,.0f}원")
        
        elif command in ["6", "report"]:
            simulator.print_detailed_report()
        
        elif command in ["7", "save"]:
            filename = simulator.save_results()
            if filename:
                print(f"결과가 {filename}에 저장되었습니다.")
        
        elif command in ["8", "quit"]:
            simulator.stop_simulation()
            logger.info("프로그램 종료")
            break
        
        else:
            print("올바른 명령어를 입력하세요.")


if __name__ == "__main__":
    main()