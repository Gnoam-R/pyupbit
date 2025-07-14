#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
테스트 모드 암호화폐 자동 매매 시뮬레이터

실제 거래 없이 내부적으로 가상 자산을 관리하여 매매 로직을 테스트하는 시뮬레이터입니다.
100만원의 시드머니로 시작하여 실제 시세를 기반으로 가상 매매를 수행합니다.
"""

import pyupbit
import pandas as pd
import numpy as np
import time
import datetime
import logging
from typing import Dict, List, Optional, Tuple
import json
import os
from threading import Thread
import schedule

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_trading_simulator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TestTradingSimulator:
    def __init__(self, target_coin: str = "BTC", seed_money: float = 1000000):
        """
        테스트 모드 매매 시뮬레이터 초기화
        
        Args:
            target_coin: 대상 코인 (BTC, ETH, MASK, SOL, PEPE 등)
            seed_money: 시드머니 (기본 100만원)
        """
        self.target_coin = target_coin
        self.target_ticker = f"KRW-{target_coin}"
        self.running = False
        
        # 가상 자산 관리
        self.virtual_assets = {
            "KRW": seed_money,  # 원화 잔고
            target_coin: 0.0    # 코인 잔고
        }
        
        # 초기 시드머니 기록
        self.seed_money = seed_money
        
        # 매매 설정
        self.config = {
            "buy_ratio": 0.1,  # 매수 비율 (보유 원화의 10%)
            "sell_ratio": 0.5,  # 매도 비율 (보유 비트코인의 50%)
            "stop_loss": 0.03,  # 손절 비율 (3%)
            "take_profit": 0.05,  # 익절 비율 (5%)
            "min_order_amount": 5000,  # 최소 주문 금액
            "trading_interval": 60,  # 매매 판단 주기 (초)
            "ma_short": 5,  # 단기 이동평균
            "ma_long": 20,  # 장기 이동평균
            "rsi_period": 14,  # RSI 기간
            "rsi_oversold": 30,  # RSI 과매도 기준
            "rsi_overbought": 70,  # RSI 과매수 기준
            "bb_period": 20,  # 볼린저 밴드 기간
            "bb_std": 2,  # 볼린저 밴드 표준편차
            "stoch_k": 14,  # 스토캐스틱 %K 기간
            "stoch_d": 3,  # 스토캐스틱 %D 기간
            "macd_fast": 12,  # MACD 빠른 EMA
            "macd_slow": 26,  # MACD 느린 EMA
            "macd_signal": 9,  # MACD 신호선
        }
        
        # 포지션 관리
        self.position = {
            "is_holding": False,
            "buy_price": 0,
            "buy_amount": 0,
            "buy_time": None,
            "total_profit": 0,
            "win_count": 0,
            "loss_count": 0,
            "total_trades": 0
        }
        
        # 거래 내역 기록
        self.trade_history = []
        
        # 지원 코인 목록
        self.supported_coins = {
            "BTC": {"name": "비트코인", "min_order": 5000},
            "ETH": {"name": "이더리움", "min_order": 5000},
            "MASK": {"name": "마스크 네트워크", "min_order": 5000},
            "SOL": {"name": "솔라나", "min_order": 5000},
            "PEPE": {"name": "페페", "min_order": 5000}
        }
        
        logger.info(f"테스트 모드 시뮬레이터 초기화 완료 - 대상 코인: {self.supported_coins.get(target_coin, {}).get('name', target_coin)}")
        logger.info(f"시드머니: {seed_money:,.0f}원")
        
    def get_virtual_account_info(self) -> Dict:
        """가상 계정 정보 조회"""
        return {
            "krw_balance": self.virtual_assets["KRW"],
            "coin_balance": self.virtual_assets[self.target_coin],
            "total_value": self.calculate_total_value(),
            "profit_loss": self.calculate_total_value() - self.seed_money,
            "profit_rate": (self.calculate_total_value() - self.seed_money) / self.seed_money * 100
        }
    
    def calculate_total_value(self) -> float:
        """총 자산 가치 계산"""
        try:
            current_price = self.get_current_price()
            if current_price is None:
                return self.virtual_assets["KRW"]
            
            coin_value = self.virtual_assets[self.target_coin] * current_price
            return self.virtual_assets["KRW"] + coin_value
        except Exception as e:
            logger.error(f"총 자산 가치 계산 오류: {e}")
            return self.virtual_assets["KRW"]
    
    def get_current_price(self) -> float:
        """현재가 조회"""
        try:
            return pyupbit.get_current_price(self.target_ticker)
        except Exception as e:
            logger.error(f"현재가 조회 오류: {e}")
            return None
    
    def get_ohlcv_data(self, interval: str = "minute5", count: int = 200) -> pd.DataFrame:
        """OHLCV 데이터 조회"""
        try:
            df = pyupbit.get_ohlcv(self.target_ticker, interval=interval, count=count)
            return df
        except Exception as e:
            logger.error(f"OHLCV 데이터 조회 오류: {e}")
            return None
    
    def calculate_rsi(self, prices, period=14):
        """RSI 계산"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_bollinger_bands(self, prices, period=20, std_dev=2):
        """볼린저 밴드 계산"""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return upper_band, sma, lower_band
    
    def calculate_stochastic(self, high, low, close, k_period=14, d_period=3):
        """스토캐스틱 계산"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()
        return k_percent, d_percent
    
    def calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """MACD 계산"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        macd_histogram = macd - macd_signal
        return macd, macd_signal, macd_histogram
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> Dict:
        """기술적 지표 계산"""
        try:
            indicators = {}
            
            # 이동평균선
            indicators['ma_short'] = df['close'].rolling(window=self.config['ma_short']).mean()
            indicators['ma_long'] = df['close'].rolling(window=self.config['ma_long']).mean()
            
            # RSI
            indicators['rsi'] = self.calculate_rsi(df['close'], self.config['rsi_period'])
            
            # 볼린저 밴드
            indicators['bb_upper'], indicators['bb_middle'], indicators['bb_lower'] = self.calculate_bollinger_bands(
                df['close'], self.config['bb_period'], self.config['bb_std']
            )
            
            # 스토캐스틱
            indicators['stoch_k'], indicators['stoch_d'] = self.calculate_stochastic(
                df['high'], df['low'], df['close'], 
                self.config['stoch_k'], self.config['stoch_d']
            )
            
            # MACD
            indicators['macd'], indicators['macd_signal'], indicators['macd_histogram'] = self.calculate_macd(
                df['close'], self.config['macd_fast'], self.config['macd_slow'], self.config['macd_signal']
            )
            
            return indicators
        except Exception as e:
            logger.error(f"기술적 지표 계산 오류: {e}")
            return None
    
    def generate_buy_signal(self, df: pd.DataFrame, indicators: Dict) -> bool:
        """매수 신호 생성"""
        try:
            current_price = df['close'].iloc[-1]
            
            # 이동평균선 골든크로스
            ma_signal = (indicators['ma_short'].iloc[-1] > indicators['ma_long'].iloc[-1] and
                        indicators['ma_short'].iloc[-2] <= indicators['ma_long'].iloc[-2])
            
            # RSI 과매도
            rsi_signal = indicators['rsi'].iloc[-1] < self.config['rsi_oversold']
            
            # 볼린저 밴드 하단 터치
            bb_signal = current_price <= indicators['bb_lower'].iloc[-1]
            
            # 스토캐스틱 과매도
            stoch_signal = (indicators['stoch_k'].iloc[-1] < 20 and 
                           indicators['stoch_d'].iloc[-1] < 20)
            
            # MACD 상승 전환
            macd_signal = (indicators['macd'].iloc[-1] > indicators['macd_signal'].iloc[-1] and
                          indicators['macd'].iloc[-2] <= indicators['macd_signal'].iloc[-2])
            
            # 가격 상승 추세
            price_trend = df['close'].iloc[-1] > df['close'].iloc[-5]
            
            # 신호 종합 (1개 이상 신호 발생 시 매수 - 테스트를 위해 완화)
            signals = [ma_signal, rsi_signal, bb_signal, stoch_signal, macd_signal, price_trend]
            buy_signal = sum(signals) >= 1
            
            if buy_signal:
                logger.info(f"매수 신호 발생: MA={ma_signal}, RSI={rsi_signal}, BB={bb_signal}, "
                           f"STOCH={stoch_signal}, MACD={macd_signal}, TREND={price_trend}")
            
            return buy_signal
        except Exception as e:
            logger.error(f"매수 신호 생성 오류: {e}")
            return False
    
    def generate_sell_signal(self, df: pd.DataFrame, indicators: Dict) -> bool:
        """매도 신호 생성"""
        try:
            current_price = df['close'].iloc[-1]
            
            # 이동평균선 데드크로스
            ma_signal = (indicators['ma_short'].iloc[-1] < indicators['ma_long'].iloc[-1] and
                        indicators['ma_short'].iloc[-2] >= indicators['ma_long'].iloc[-2])
            
            # RSI 과매수
            rsi_signal = indicators['rsi'].iloc[-1] > self.config['rsi_overbought']
            
            # 볼린저 밴드 상단 터치
            bb_signal = current_price >= indicators['bb_upper'].iloc[-1]
            
            # 스토캐스틱 과매수
            stoch_signal = (indicators['stoch_k'].iloc[-1] > 80 and 
                           indicators['stoch_d'].iloc[-1] > 80)
            
            # MACD 하락 전환
            macd_signal = (indicators['macd'].iloc[-1] < indicators['macd_signal'].iloc[-1] and
                          indicators['macd'].iloc[-2] >= indicators['macd_signal'].iloc[-2])
            
            # 가격 하락 추세
            price_trend = df['close'].iloc[-1] < df['close'].iloc[-5]
            
            # 신호 종합 (1개 이상 신호 발생 시 매도 - 테스트를 위해 완화)
            signals = [ma_signal, rsi_signal, bb_signal, stoch_signal, macd_signal, price_trend]
            sell_signal = sum(signals) >= 1
            
            if sell_signal:
                logger.info(f"매도 신호 발생: MA={ma_signal}, RSI={rsi_signal}, BB={bb_signal}, "
                           f"STOCH={stoch_signal}, MACD={macd_signal}, TREND={price_trend}")
            
            return sell_signal
        except Exception as e:
            logger.error(f"매도 신호 생성 오류: {e}")
            return False
    
    def check_stop_loss_take_profit(self, current_price: float) -> Optional[str]:
        """손절/익절 확인"""
        if not self.position["is_holding"]:
            return None
        
        buy_price = self.position["buy_price"]
        profit_rate = (current_price - buy_price) / buy_price
        
        if profit_rate <= -self.config["stop_loss"]:
            logger.info(f"손절 조건 충족: 수익률 {profit_rate:.2%}")
            return "stop_loss"
        elif profit_rate >= self.config["take_profit"]:
            logger.info(f"익절 조건 충족: 수익률 {profit_rate:.2%}")
            return "take_profit"
        
        return None
    
    def execute_virtual_buy_order(self, current_price: float) -> bool:
        """가상 매수 주문 실행"""
        try:
            krw_balance = self.virtual_assets["KRW"]
            buy_amount = krw_balance * self.config["buy_ratio"]
            
            if buy_amount < self.config["min_order_amount"]:
                logger.warning(f"매수 가능 금액 부족: {buy_amount:,.0f}원")
                return False
            
            # 매수 수량 계산
            buy_volume = buy_amount / current_price
            
            # 가상 자산 업데이트
            self.virtual_assets["KRW"] -= buy_amount
            self.virtual_assets[self.target_coin] += buy_volume
            
            # 포지션 업데이트
            self.position.update({
                "is_holding": True,
                "buy_price": current_price,
                "buy_amount": buy_volume,
                "buy_time": datetime.datetime.now()
            })
            
            # 거래 내역 기록
            trade_record = {
                "timestamp": datetime.datetime.now(),
                "type": "buy",
                "price": current_price,
                "amount": buy_volume,
                "total_krw": buy_amount,
                "reason": "signal"
            }
            self.trade_history.append(trade_record)
            
            logger.info(f"[테스트] 매수 주문 성공: 가격={current_price:,.0f}원, 수량={buy_volume:.8f}{self.target_coin}, "
                       f"총액={buy_amount:,.0f}원")
            return True
            
        except Exception as e:
            logger.error(f"가상 매수 주문 오류: {e}")
            return False
    
    def execute_virtual_sell_order(self, current_price: float, reason: str = "signal") -> bool:
        """가상 매도 주문 실행"""
        try:
            # 보유 중인지 확인
            if not self.position["is_holding"]:
                return False
            
            # 실제 보유 코인 수량 확인
            actual_coin_balance = self.virtual_assets[self.target_coin]
            if actual_coin_balance <= 0:
                logger.warning(f"매도 불가: 보유 코인 수량이 0입니다. ({actual_coin_balance:.8f}{self.target_coin})")
                return False
            
            sell_volume = self.position["buy_amount"] * self.config["sell_ratio"]
            
            # 실제 보유량보다 많이 팔려고 하는 경우 조정
            if sell_volume > actual_coin_balance:
                sell_volume = actual_coin_balance
                logger.warning(f"매도 수량 조정: {sell_volume:.8f}{self.target_coin} (보유량 전량)")
            
            sell_amount = sell_volume * current_price
            
            # 가상 자산 업데이트
            self.virtual_assets["KRW"] += sell_amount
            self.virtual_assets[self.target_coin] -= sell_volume
            
            # 수익 계산
            profit = (current_price - self.position["buy_price"]) * sell_volume
            profit_rate = (current_price - self.position["buy_price"]) / self.position["buy_price"]
            
            # 통계 업데이트
            self.position["total_profit"] += profit
            self.position["total_trades"] += 1
            
            if profit > 0:
                self.position["win_count"] += 1
            else:
                self.position["loss_count"] += 1
            
            # 거래 내역 기록
            trade_record = {
                "timestamp": datetime.datetime.now(),
                "type": "sell",
                "price": current_price,
                "amount": sell_volume,
                "total_krw": sell_amount,
                "profit": profit,
                "profit_rate": profit_rate,
                "reason": reason
            }
            self.trade_history.append(trade_record)
            
            logger.info(f"[테스트] 매도 주문 성공 ({reason}): 가격={current_price:,.0f}원, "
                       f"수량={sell_volume:.8f}{self.target_coin}, 수익={profit:,.0f}원 ({profit_rate:.2%})")
            
            # 포지션 정리
            remaining_amount = self.position["buy_amount"] - sell_volume
            
            # 보유량이 0이거나 매우 적으면 포지션 완전 정리
            if remaining_amount <= 0.00000001 or self.virtual_assets[self.target_coin] <= 0.00000001:
                self.position.update({
                    "is_holding": False,
                    "buy_price": 0,
                    "buy_amount": 0,
                    "buy_time": None
                })
                logger.info("포지션 완전 정리 완료")
            else:
                self.position["buy_amount"] = remaining_amount
                logger.info(f"부분 매도 완료, 남은 포지션: {remaining_amount:.8f}{self.target_coin}")
            
            return True
            
        except Exception as e:
            logger.error(f"가상 매도 주문 오류: {e}")
            return False
    
    def print_status(self):
        """현재 상태 출력"""
        try:
            current_price = self.get_current_price()
            account_info = self.get_virtual_account_info()
            
            if not current_price:
                return
            
            print("=" * 80)
            print(f"[테스트 모드] 현재 시간: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"현재 가격: {current_price:,.0f}원")
            print(f"가상 원화 잔고: {account_info['krw_balance']:,.0f}원")
            print(f"가상 {self.target_coin} 잔고: {account_info['coin_balance']:.8f}{self.target_coin}")
            print(f"총 자산 가치: {account_info['total_value']:,.0f}원")
            print(f"총 수익/손실: {account_info['profit_loss']:,.0f}원 ({account_info['profit_rate']:.2f}%)")
            
            if self.position["is_holding"]:
                profit_rate = (current_price - self.position["buy_price"]) / self.position["buy_price"]
                print(f"포지션: 보유 중 (매수가: {self.position['buy_price']:,.0f}원, "
                      f"수익률: {profit_rate:.2%})")
            else:
                print("포지션: 없음")
            
            print(f"총 거래 수: {self.position['total_trades']}")
            if self.position['total_trades'] > 0:
                win_rate = self.position['win_count'] / self.position['total_trades'] * 100
                print(f"승률: {self.position['win_count']}/{self.position['total_trades']} ({win_rate:.1f}%)")
            print(f"거래 수익: {self.position['total_profit']:,.0f}원")
            print("=" * 80)
        except Exception as e:
            logger.error(f"상태 출력 오류: {e}")
    
    def trading_loop(self):
        """메인 트레이딩 루프"""
        try:
            current_price = self.get_current_price()
            if not current_price:
                return
            
            # 손절/익절 확인
            stop_action = self.check_stop_loss_take_profit(current_price)
            if stop_action:
                self.execute_virtual_sell_order(current_price, stop_action)
                return
            
            # OHLCV 데이터 조회
            df = self.get_ohlcv_data("minute5", 100)
            if df is None or len(df) < 50:
                return
            
            # 기술적 지표 계산
            indicators = self.calculate_technical_indicators(df)
            if not indicators:
                return
            
            # 매매 신호 판단
            if not self.position["is_holding"]:
                # 매수 신호 확인
                if self.generate_buy_signal(df, indicators):
                    self.execute_virtual_buy_order(current_price)
            else:
                # 매도 신호 확인
                if self.generate_sell_signal(df, indicators):
                    self.execute_virtual_sell_order(current_price, "signal")
        
        except Exception as e:
            logger.error(f"트레이딩 루프 오류: {e}")
    
    def start_trading(self):
        """자동 매매 시작"""
        self.running = True
        logger.info("[테스트 모드] 자동 매매 시작")
        
        # 주기적 상태 출력 스케줄
        schedule.every(5).minutes.do(self.print_status)
        
        try:
            while self.running:
                # 스케줄된 작업 실행
                schedule.run_pending()
                
                # 트레이딩 루프 실행
                self.trading_loop()
                
                # 대기
                time.sleep(self.config["trading_interval"])
        
        except KeyboardInterrupt:
            self.stop_trading()
        except Exception as e:
            logger.error(f"자동 매매 실행 오류: {e}")
            self.stop_trading()
    
    def stop_trading(self):
        """자동 매매 중지"""
        self.running = False
        logger.info("[테스트 모드] 자동 매매 중지")
        self.print_final_report()
    
    def print_final_report(self):
        """최종 리포트 출력"""
        try:
            account_info = self.get_virtual_account_info()
            
            print("\n" + "=" * 80)
            print("최종 테스트 결과 리포트")
            print("=" * 80)
            print(f"시드머니: {self.seed_money:,.0f}원")
            print(f"최종 자산: {account_info['total_value']:,.0f}원")
            print(f"총 수익/손실: {account_info['profit_loss']:,.0f}원 ({account_info['profit_rate']:.2f}%)")
            print(f"총 거래 수: {self.position['total_trades']}")
            
            if self.position['total_trades'] > 0:
                win_rate = self.position['win_count'] / self.position['total_trades'] * 100
                print(f"승률: {self.position['win_count']}/{self.position['total_trades']} ({win_rate:.1f}%)")
                print(f"평균 거래당 수익: {self.position['total_profit']/self.position['total_trades']:,.0f}원")
            
            print(f"거래 수익: {self.position['total_profit']:,.0f}원")
            print("=" * 80)
            
            # 거래 내역 출력 (최근 10건)
            if self.trade_history:
                print("\n최근 거래 내역 (최대 10건):")
                for trade in self.trade_history[-10:]:
                    print(f"{trade['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} - "
                          f"{trade['type'].upper()}: {trade['price']:,.0f}원, "
                          f"{trade['amount']:.8f}{self.target_coin}")
                    if trade['type'] == 'sell':
                        print(f"  수익: {trade['profit']:,.0f}원 ({trade['profit_rate']:.2%})")
            
        except Exception as e:
            logger.error(f"최종 리포트 출력 오류: {e}")
    
    def save_test_results(self, filename: str = None):
        """테스트 결과 저장"""
        if filename is None:
            filename = f"test_results_{self.target_coin}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            account_info = self.get_virtual_account_info()
            
            results = {
                "test_info": {
                    "target_coin": self.target_coin,
                    "seed_money": self.seed_money,
                    "start_time": None,  # 실제 구현 시 추가
                    "end_time": datetime.datetime.now().isoformat(),
                    "config": self.config
                },
                "final_results": {
                    "total_value": account_info['total_value'],
                    "profit_loss": account_info['profit_loss'],
                    "profit_rate": account_info['profit_rate'],
                    "total_trades": self.position['total_trades'],
                    "win_count": self.position['win_count'],
                    "loss_count": self.position['loss_count'],
                    "trading_profit": self.position['total_profit']
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
                    } for trade in self.trade_history
                ]
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"테스트 결과 저장 완료: {filename}")
            
        except Exception as e:
            logger.error(f"테스트 결과 저장 오류: {e}")

def select_coin():
    """거래할 코인 선택"""
    supported_coins = {
        "1": ("BTC", "비트코인"),
        "2": ("ETH", "이더리움"),
        "3": ("MASK", "마스크 네트워크"),
        "4": ("SOL", "솔라나"),
        "5": ("PEPE", "페페")
    }
    
    print("\n=== 테스트할 코인을 선택하세요 ===")
    for key, (symbol, name) in supported_coins.items():
        print(f"{key}. {name} ({symbol})")
    
    while True:
        choice = input("\n번호를 선택하세요 (1-5): ").strip()
        if choice in supported_coins:
            return supported_coins[choice][0]
        else:
            print("올바른 번호를 입력하세요.")

def main():
    """메인 함수"""
    print("=" * 80)
    print("암호화폐 자동 매매 테스트 시뮬레이터")
    print("실제 거래 없이 가상 자산으로 매매 로직을 테스트합니다.")
    print("=" * 80)
    
    # 코인 선택
    selected_coin = select_coin()
    
    # 시드머니 설정
    seed_money = 1000000  # 100만원
    
    # 시뮬레이터 초기화
    simulator = TestTradingSimulator(selected_coin, seed_money)
    
    print(f"\n=== {simulator.supported_coins.get(selected_coin, {}).get('name', selected_coin)} 테스트 시뮬레이터 ===")
    print(f"시드머니: {seed_money:,.0f}원")
    
    # 사용자 입력
    while True:
        print("\n명령어:")
        print("1. start - 테스트 시작")
        print("2. stop - 테스트 중지")
        print("3. status - 현재 상태 확인")
        print("4. report - 최종 리포트")
        print("5. save - 결과 저장")
        print("6. quit - 프로그램 종료")
        
        command = input("\n명령어를 입력하세요: ").strip().lower()
        
        if command in ["1", "start"]:
            simulator.start_trading()
        elif command in ["2", "stop"]:
            simulator.stop_trading()
        elif command in ["3", "status"]:
            simulator.print_status()
        elif command in ["4", "report"]:
            simulator.print_final_report()
        elif command in ["5", "save"]:
            simulator.save_test_results()
        elif command in ["6", "quit"]:
            simulator.stop_trading()
            break
        else:
            print("올바른 명령어를 입력하세요.")

if __name__ == "__main__":
    main()