#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
가상 암호화폐 트레이딩 시뮬레이터

실제 거래 없이 가상 자산을 사용하여 매매 전략을 테스트하는 시뮬레이터입니다.
100만원의 시드머니로 시작하여 실제 시세를 기반으로 가상 매매를 수행합니다.
"""

import datetime
import json
import os

# Business Logic Imports
from business_logic.core.trading_engine import TradingEngine
from business_logic.core.asset_manager import VirtualAssetManager
from business_logic.executors.trading_executor import VirtualTradeExecutor
from business_logic.utils.coin_selector import select_coin, get_coin_name
from business_logic.utils.logger import setup_logger
from business_logic.utils.format_helper import format_profit_rate, format_currency, format_percentage
from business_logic.utils.profit_calculator import calculate_total_profit_summary

# 로깅 설정
logger = setup_logger('test_trading_simulator', 'test_trading_simulator.log')


class TestTradingSimulator:
    """테스트 모드 트레이딩 시뮬레이터"""
    
    def __init__(self, target_coin: str, seed_money: float = 10000000):
        """
        시뮬레이터 초기화
        
        Args:
            target_coin: 대상 코인 심볼
            seed_money: 초기 시드머니 (기본 천만원)
        """
        self.target_coin = target_coin
        self.seed_money = seed_money
        
        # 가상 모드 매니저들 초기화 (지속성 지원)
        self.asset_manager = VirtualAssetManager(target_coin, seed_money, use_persistence=True)
        self.trade_executor = VirtualTradeExecutor(target_coin)
        
        # 트레이딩 엔진 초기화 (테스트 모드)
        self.engine = TradingEngine(
            target_coin=target_coin,
            asset_manager=self.asset_manager,
            trade_executor=self.trade_executor,
            is_test_mode=True
        )
        
        logger.info(f"테스트 시뮬레이터 초기화 완료 - 대상 코인: {get_coin_name(target_coin)}")
        logger.info(f"시드머니: {seed_money:,.0f}원")
    
    def get_account_summary(self) -> dict:
        """계정 요약 정보 조회"""
        try:
            account_info = self.asset_manager.get_account_info()
            current_price = self.engine.get_current_price()
            
            if current_price:
                value_info = self.asset_manager.calculate_total_value(current_price)
                account_info.update(value_info)
            
            return account_info
        except Exception as e:
            logger.error(f"계정 요약 정보 조회 오류: {e}")
            return {}
    
    def print_account_summary(self):
        """계정 요약 정보 출력"""
        try:
            account_info = self.get_account_summary()
            current_price = self.engine.get_current_price()
            
            if not current_price:
                print("현재 가격 정보를 가져올 수 없습니다.")
                return
            
            print("=" * 60)
            print(f"🧪 {get_coin_name(self.target_coin)} 테스트 시뮬레이터")
            print("=" * 60)
            print(f"현재 가격: {current_price:,.0f}원")
            print(f"시드머니: {self.seed_money:,.0f}원")
            print(f"가상 원화 잔고: {account_info.get('krw_balance', 0):,.0f}원")
            print(f"가상 {self.target_coin} 잔고: {account_info.get('coin_balance', 0):.8f}{self.target_coin}")
            print(f"총 자산 가치: {account_info.get('total_value', 0):,.0f}원")
            print(f"총 수익/손실: {account_info.get('profit_loss', 0):,.0f}원 ({account_info.get('profit_rate', 0):.2f}%)")
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
    
    def save_balance(self):
        """현재 잔고 상태 저장"""
        try:
            current_price = self.engine.get_current_price()
            if current_price:
                position_info = self.engine.get_position_info()
                stats = self.engine.get_statistics()
                self.asset_manager.save_balance(position_info, stats, current_price)
                logger.info("💾 잔고 정보 저장 완료")
        except Exception as e:
            logger.error(f"잔고 저장 오류: {e}")
    
    def get_balance_summary(self):
        """저장된 잔고 요약 정보 출력"""
        try:
            summary = self.asset_manager.get_balance_summary()
            print(summary)
        except Exception as e:
            logger.error(f"잔고 요약 출력 오류: {e}")
    
    def reset_balance(self, initial_krw: float = 10000000):
        """잔고 초기화"""
        try:
            self.asset_manager.reset_balance(initial_krw)
            self.seed_money = initial_krw
            # 엔진 재시작
            self.engine.stop_trading()
            logger.info("잔고 초기화 완료. 프로그램을 다시 시작하세요.")
        except Exception as e:
            logger.error(f"잔고 초기화 오류: {e}")

    def print_final_report(self):
        """최종 테스트 결과 리포트 출력"""
        try:
            # 잔고 저장
            self.save_balance()
            
            account_info = self.get_account_summary()
            stats = self.engine.get_statistics()
            
            print("\n" + "=" * 80)
            print("📊 최종 테스트 결과 리포트")
            print("=" * 80)
            
            # 정확한 수익 계산
            current_price = self.engine.get_current_price()
            if current_price:
                position = self.engine.get_position_info()
                profit_summary = calculate_total_profit_summary(
                    position=position,
                    current_price=current_price,
                    initial_seed=self.seed_money,
                    current_krw=account_info.get('krw_balance', 0),
                    current_coin=account_info.get('coin_balance', 0)
                )
                
                print(f"시드머니: {format_currency(self.seed_money)}")
                print(f"최종 자산: {format_currency(profit_summary['total_value'])}")
                print(f"자산 변화: {format_currency(profit_summary['asset_profit'])} ({format_percentage(profit_summary['asset_profit_rate'])})")
                
                if profit_summary['realized_profit'] != 0:
                    print(f"실현 손익: {format_currency(profit_summary['realized_profit'])}")
                
                if profit_summary['unrealized_profit'] != 0:
                    print(f"미실현 손익: {format_currency(profit_summary['unrealized_profit'])} ({format_profit_rate(profit_summary['unrealized_rate'])})")
            else:
                print(f"시드머니: {format_currency(self.seed_money)}")
                print(f"최종 자산: {format_currency(account_info.get('total_value', 0))}")
                print(f"총 수익/손실: {format_currency(account_info.get('profit_loss', 0))} ({format_percentage(account_info.get('profit_rate', 0))})")
            
            print(f"총 거래 수: {stats['total_trades']}")
            
            if stats['total_trades'] > 0:
                print(f"승률: {stats['win_count']}/{stats['total_trades']} ({format_percentage(stats['win_rate'])})")
                print(f"평균 거래당 수익: {format_currency(stats['avg_profit_per_trade'])}")
            
            print(f"거래 수익: {format_currency(stats['total_profit'])}")
            print("=" * 80)
            
            # 거래 내역 출력 (최근 10건)
            trade_history = self.trade_executor.get_trade_history()
            if trade_history:
                print("\n📋 최근 거래 내역 (최대 10건):")
                for trade in trade_history[-10:]:
                    timestamp = trade['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                    trade_type = trade['type'].upper()
                    price = trade['price']
                    amount = trade['amount']
                    
                    print(f"  {timestamp} - {trade_type}: {price:,.0f}원, {amount:.8f}{self.target_coin}")
                    
                    if trade['type'] == 'sell':
                        profit = trade.get('profit', 0)
                        profit_rate = trade.get('profit_rate', 0)
                        print(f"    수익: {profit:,.0f}원 ({profit_rate:.2%})")
            
        except Exception as e:
            logger.error(f"최종 리포트 출력 오류: {e}")
    
    def save_test_results(self, filename: str = None):
        """테스트 결과 저장"""
        if filename is None:
            filename = f"test_results_{self.target_coin}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            account_info = self.get_account_summary()
            stats = self.engine.get_statistics()
            config = self.engine.get_config()
            trade_history = self.trade_executor.get_trade_history()
            
            results = {
                "test_info": {
                    "target_coin": self.target_coin,
                    "seed_money": self.seed_money,
                    "end_time": datetime.datetime.now().isoformat(),
                    "config": config
                },
                "final_results": {
                    "total_value": account_info.get('total_value', 0),
                    "profit_loss": account_info.get('profit_loss', 0),
                    "profit_rate": account_info.get('profit_rate', 0),
                    "total_trades": stats['total_trades'],
                    "win_count": stats['win_count'],
                    "loss_count": stats['loss_count'],
                    "win_rate": stats['win_rate'],
                    "trading_profit": stats['total_profit']
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
    
    def get_config(self):
        """현재 설정 조회"""
        return self.engine.get_config()


def main():
    """메인 함수"""
    print("🧪 가상 암호화폐 트레이딩 시뮬레이터 시작")
    print("💡 실제 거래 없이 가상 자산으로 매매 전략을 테스트합니다.")
    
    # 매매 모드 선택
    print("\n📋 테스트 모드를 선택하세요:")
    print("1. 단일 코인 테스트 (기존 방식)")
    print("2. 다중 코인 테스트 (새로운 방식)")
    
    while True:
        mode_choice = input("\n모드를 선택하세요 (1-2): ").strip()
        if mode_choice == "1":
            # 단일 코인 선택
            selected_coin = select_coin()
            break
        elif mode_choice == "2":
            # 다중 코인 테스트로 이동
            print("\n다중 코인 테스트는 multi_coin_test_simulator.py를 사용해주세요.")
            print("python3 multi_coin_test_simulator.py")
            return
        else:
            print("올바른 번호를 입력하세요.")
    
    # 시드머니 설정
    seed_money = 10000000  # 1000만원
    
    # 시뮬레이터 초기화
    simulator = TestTradingSimulator(selected_coin, seed_money)
    
    # 계정 요약 정보 출력
    simulator.print_account_summary()
    
    # 사용자 입력 처리
    print("\n📋 사용 가능한 명령어:")
    print("  start    - 테스트 시작")
    print("  stop     - 테스트 중지")
    print("  status   - 현재 상태 확인")
    print("  report   - 최종 리포트 보기")
    print("  save     - 결과 저장")
    print("  config   - 현재 설정 보기")
    print("  balance  - 저장된 잔고 요약 보기")
    print("  reset    - 잔고 초기화 (1000만원)")
    print("  quit     - 프로그램 종료")
    
    while True:
        try:
            command = input("\n명령어를 입력하세요: ").strip().lower()
            
            if command == "start":
                print("🚀 테스트를 시작합니다...")
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
                
            elif command == "config":
                print("⚙️ 현재 설정:")
                config = simulator.get_config()
                for key, value in config.items():
                    print(f"  {key}: {value}")
            
            elif command == "balance":
                print("💰 저장된 잔고 요약:")
                simulator.get_balance_summary()
            
            elif command == "reset":
                confirm = input("⚠️ 잔고를 초기화하시겠습니까? (y/n): ").strip().lower()
                if confirm == 'y':
                    simulator.reset_balance()
                else:
                    print("❌ 초기화를 취소했습니다.")
                    
            elif command == "quit":
                print("👋 프로그램을 종료합니다...")
                simulator.stop_trading()
                break
                
            else:
                print("❌ 올바른 명령어를 입력하세요.")
                
        except KeyboardInterrupt:
            print("\n🛑 프로그램을 중지합니다...")
            simulator.stop_trading()
            break
        except Exception as e:
            logger.error(f"명령어 처리 오류: {e}")
            print(f"❌ 오류가 발생했습니다: {e}")


if __name__ == "__main__":
    main()