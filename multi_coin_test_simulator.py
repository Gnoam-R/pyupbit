#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
다중 코인 테스트 트레이딩 시뮬레이터

여러 코인을 동시에 테스트하는 가상 트레이딩 시뮬레이터입니다.
실제 거래 없이 가상 자산으로 매매 전략을 테스트할 수 있습니다.
"""

import time
import datetime
import json
import os

# Business Logic Imports
from business_logic.core.multi_coin_engine import MultiCoinTradingEngine
from business_logic.core.asset_manager import VirtualAssetManager
from business_logic.executors.trading_executor import VirtualTradeExecutor
from business_logic.utils.coin_selector import select_coins, get_all_coin_names
from business_logic.utils.logger import setup_logger
from business_logic.utils.format_helper import format_currency, format_percentage

# 로깅 설정
logger = setup_logger('multi_coin_test_simulator', 'multi_coin_test_simulator.log')


class MultiCoinTestSimulator:
    """다중 코인 테스트 시뮬레이터"""
    
    def __init__(self, target_coins: list, seed_money: float = 10000000):
        self.target_coins = target_coins
        self.seed_money = seed_money
        
        # 비즈니스 로직 모듈 초기화
        self.asset_manager = VirtualAssetManager(target_coins[0], seed_money, use_persistence=False)
        self.trade_executor = VirtualTradeExecutor(target_coins[0])
        
        # 다중 코인 엔진 초기화
        self.engine = MultiCoinTradingEngine(
            target_coins,
            self.asset_manager,
            self.trade_executor,
            is_test_mode=True
        )
        
        logger.info(f"다중 코인 테스트 시뮬레이터 초기화 완료")
        logger.info(f"대상 코인: {', '.join(target_coins)}")
        logger.info(f"시드머니: {seed_money:,.0f}원")
    
    def print_account_summary(self):
        """계정 요약 정보 출력"""
        try:
            account_info = self.asset_manager.get_account_info()
            
            print("=" * 80)
            print(f"🧪 {get_all_coin_names(self.target_coins)} 다중 코인 테스트 시뮬레이터")
            print("=" * 80)
            print(f"시드머니: {format_currency(self.seed_money)}")
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
            
        except Exception as e:
            logger.error(f"계정 요약 정보 출력 오류: {e}")
    
    def start_trading(self):
        """자동 매매 시작"""
        print(f"🚀 {get_all_coin_names(self.target_coins)} 테스트 시작!")
        self.engine.start_trading()
    
    def stop_trading(self):
        """자동 매매 중지"""
        self.engine.stop_trading()
    
    def print_status(self):
        """현재 상태 출력"""
        self.engine.print_status()
    
    def get_account_summary(self):
        """계정 요약 정보 반환"""
        account_info = self.asset_manager.get_account_info()
        
        # 총 자산 가치 계산
        total_value = account_info['krw_balance']
        prices = self.engine.get_all_current_prices()
        
        for coin in self.target_coins:
            coin_balance = self.asset_manager.get_balance(coin)
            current_price = prices.get(coin, 0)
            if coin_balance > 0 and current_price > 0:
                total_value += coin_balance * current_price
        
        profit_loss = total_value - self.seed_money
        profit_rate = (profit_loss / self.seed_money) * 100 if self.seed_money > 0 else 0
        
        return {
            'total_value': total_value,
            'profit_loss': profit_loss,
            'profit_rate': profit_rate,
            'krw_balance': account_info['krw_balance']
        }
    
    def print_final_report(self):
        """최종 테스트 결과 리포트 출력"""
        try:
            account_info = self.get_account_summary()
            combined_stats = self.engine.get_combined_statistics()
            
            print("\\n" + "=" * 80)
            print("📊 최종 다중 코인 테스트 결과 리포트")
            print("=" * 80)
            print(f"대상 코인: {get_all_coin_names(self.target_coins)}")
            print(f"시드머니: {format_currency(self.seed_money)}")
            print(f"최종 자산: {format_currency(account_info['total_value'])}")
            print(f"총 수익/손실: {format_currency(account_info['profit_loss'])} ({format_percentage(account_info['profit_rate'])})")
            print(f"총 거래 수: {combined_stats['total_trades']}")
            
            if combined_stats['total_trades'] > 0:
                print(f"승률: {combined_stats['win_count']}/{combined_stats['total_trades']} ({format_percentage(combined_stats['win_rate'])})")
                print(f"평균 거래당 수익: {format_currency(combined_stats['avg_profit_per_trade'])}")
            
            print(f"거래 수익: {format_currency(combined_stats['total_profit'])}")
            print("=" * 80)
            
            # 각 코인별 상세 결과
            print("\\n📋 코인별 상세 결과:")
            all_stats = self.engine.get_all_statistics()
            for coin in self.target_coins:
                stats = all_stats[coin]
                print(f"  {coin}:")
                print(f"    거래 수: {stats['total_trades']}")
                if stats['total_trades'] > 0:
                    print(f"    승률: {stats['win_count']}/{stats['total_trades']} ({format_percentage(stats['win_rate'])})")
                    print(f"    수익: {format_currency(stats['total_profit'])}")
                else:
                    print(f"    거래 없음")
            
            print("=" * 80)
            
        except Exception as e:
            logger.error(f"최종 리포트 출력 오류: {e}")
    
    def save_test_results(self, filename: str = None):
        """테스트 결과 저장"""
        if filename is None:
            coin_names = "_".join(self.target_coins)
            filename = f"multi_coin_test_results_{coin_names}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            account_info = self.get_account_summary()
            combined_stats = self.engine.get_combined_statistics()
            all_stats = self.engine.get_all_statistics()
            trade_history = self.trade_executor.get_trade_history()
            
            results = {
                "test_info": {
                    "target_coins": self.target_coins,
                    "seed_money": self.seed_money,
                    "end_time": datetime.datetime.now().isoformat(),
                },
                "final_results": {
                    "total_value": account_info['total_value'],
                    "profit_loss": account_info['profit_loss'],
                    "profit_rate": account_info['profit_rate'],
                    "combined_stats": combined_stats,
                    "coin_stats": all_stats
                },
                "trade_history": [
                    {
                        "timestamp": trade['timestamp'].isoformat(),
                        "type": trade['type'],
                        "price": trade['price'],
                        "amount": trade['amount'],
                        "total_krw": trade['total_krw'],
                        "profit": trade.get('profit', 0),
                        "profit_rate": trade.get('profit_rate', 0),
                        "reason": trade['reason']
                    } for trade in trade_history
                ]
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"테스트 결과 저장 완료: {filename}")
            print(f"✅ 테스트 결과가 저장되었습니다: {filename}")
            
        except Exception as e:
            logger.error(f"테스트 결과 저장 오류: {e}")
            print(f"❌ 테스트 결과 저장 중 오류가 발생했습니다: {e}")


def main():
    """메인 함수"""
    print("🧪 다중 코인 가상 트레이딩 시뮬레이터 시작")
    print("💡 실제 거래 없이 가상 자산으로 여러 코인의 매매 전략을 동시에 테스트합니다.")
    
    # 다중 코인 선택
    selected_coins = select_coins(multi=True)
    
    if not selected_coins:
        print("❌ 코인이 선택되지 않았습니다.")
        return
    
    # 시드머니 설정
    seed_money = 10000000  # 1000만원
    
    # 시뮬레이터 초기화
    simulator = MultiCoinTestSimulator(selected_coins, seed_money)
    
    # 계정 요약 정보 출력
    simulator.print_account_summary()
    
    # 사용자 입력 처리
    print("\\n📋 사용 가능한 명령어:")
    print("  start    - 테스트 시작")
    print("  stop     - 테스트 중지")
    print("  status   - 현재 상태 확인")
    print("  report   - 최종 리포트")
    print("  save     - 결과 저장")
    print("  quit     - 프로그램 종료")
    
    while True:
        try:
            command = input("\\n명령어를 입력하세요: ").strip().lower()
            
            if command == "start":
                print("🧪 테스트를 시작합니다...")
                simulator.start_trading()
            elif command == "stop":
                print("🛑 테스트를 중지합니다...")
                simulator.stop_trading()
            elif command == "status":
                simulator.print_status()
            elif command == "report":
                simulator.print_final_report()
            elif command == "save":
                simulator.save_test_results()
            elif command == "quit":
                print("👋 프로그램을 종료합니다.")
                simulator.stop_trading()
                break
            else:
                print("❌ 올바른 명령어를 입력하세요.")
                
        except KeyboardInterrupt:
            print("\\n👋 프로그램을 종료합니다.")
            simulator.stop_trading()
            break
        except Exception as e:
            logger.error(f"명령 처리 오류: {e}")
            print(f"❌ 오류가 발생했습니다: {e}")


if __name__ == "__main__":
    main()