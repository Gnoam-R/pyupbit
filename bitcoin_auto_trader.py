#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
암호화폐 자동 매매 프로그램

이 프로그램은 pyupbit 라이브러리를 활용하여 다음 기능들을 구현합니다:
1. 실시간 시세 모니터링
2. 기술적 분석 기반 자동 매매
3. 리스크 관리 및 손절/익절
4. 포트폴리오 관리
5. 실시간 로그 및 알림

주요 전략:
- 이동평균선 기반 매매 신호
- RSI 과매수/과매도 지표
- 볼린저 밴드 브레이크아웃
- 스토캐스틱 오실레이터
- MACD 다이버전스
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
        logging.FileHandler('bitcoin_trader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 기술적 지표 계산을 위한 간단한 함수들
def calculate_rsi(prices, period=14):
    """RSI 계산"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """볼린저 밴드 계산"""
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    return upper_band, sma, lower_band

def calculate_stochastic(high, low, close, k_period=14, d_period=3):
    """스토캐스틱 계산"""
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
    d_percent = k_percent.rolling(window=d_period).mean()
    return k_percent, d_percent

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """MACD 계산"""
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal).mean()
    macd_histogram = macd - macd_signal
    return macd, macd_signal, macd_histogram

class CryptoAutoTrader:
    def __init__(self, access_key: str, secret_key: str, target_coin: str = "BTC"):
        """
        암호화폐 자동 매매 클래스 초기화
        
        Args:
            access_key: 업비트 API 액세스 키
            secret_key: 업비트 API 시크릿 키
            target_coin: 대상 코인 (BTC, ETH, MASK, SOL, PEPE 등)
        """
        self.upbit = pyupbit.Upbit(access_key, secret_key)
        self.target_coin = target_coin
        self.target_ticker = f"KRW-{target_coin}"
        self.running = False
        
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
        
        # 지원 코인 목록
        self.supported_coins = {
            "BTC": {"name": "비트코인", "min_order": 5000},
            "ETH": {"name": "이더리움", "min_order": 5000},
            "MASK": {"name": "마스크 네트워크", "min_order": 5000},
            "SOL": {"name": "솔라나", "min_order": 5000},
            "PEPE": {"name": "페페", "min_order": 5000}
        }
        
        # 웹소켓 매니저
        self.websocket_manager = None
        
        logger.info(f"CryptoAutoTrader 초기화 완료 - 대상 코인: {self.supported_coins.get(target_coin, {}).get('name', target_coin)}")
        
    def get_account_info(self) -> Dict:
        """계정 정보 조회"""
        try:
            balances = self.upbit.get_balances()
            krw_balance = self.upbit.get_balance("KRW")
            coin_balance = self.upbit.get_balance(self.target_coin)
            
            return {
                "krw_balance": krw_balance,
                "coin_balance": coin_balance,
                "balances": balances
            }
        except Exception as e:
            logger.error(f"계정 정보 조회 오류: {e}")
            return None
    
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
    
    def get_orderbook(self) -> Dict:
        """호가 정보 조회"""
        try:
            return pyupbit.get_orderbook(self.target_ticker)
        except Exception as e:
            logger.error(f"호가 정보 조회 오류: {e}")
            return None
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> Dict:
        """기술적 지표 계산"""
        try:
            indicators = {}
            
            # 이동평균선
            indicators['ma_short'] = df['close'].rolling(window=self.config['ma_short']).mean()
            indicators['ma_long'] = df['close'].rolling(window=self.config['ma_long']).mean()
            
            # RSI
            indicators['rsi'] = calculate_rsi(df['close'], self.config['rsi_period'])
            
            # 볼린저 밴드
            indicators['bb_upper'], indicators['bb_middle'], indicators['bb_lower'] = calculate_bollinger_bands(
                df['close'], self.config['bb_period'], self.config['bb_std']
            )
            
            # 스토캐스틱
            indicators['stoch_k'], indicators['stoch_d'] = calculate_stochastic(
                df['high'], df['low'], df['close'], 
                self.config['stoch_k'], self.config['stoch_d']
            )
            
            # MACD
            indicators['macd'], indicators['macd_signal'], indicators['macd_histogram'] = calculate_macd(
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
            
            # 신호 종합 (2개 이상 신호 발생 시 매수)
            signals = [ma_signal, rsi_signal, bb_signal, stoch_signal, macd_signal, price_trend]
            buy_signal = sum(signals) >= 2
            
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
            
            # 신호 종합 (2개 이상 신호 발생 시 매도)
            signals = [ma_signal, rsi_signal, bb_signal, stoch_signal, macd_signal, price_trend]
            sell_signal = sum(signals) >= 2
            
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
    
    def execute_buy_order(self, current_price: float) -> bool:
        """매수 주문 실행"""
        try:
            account_info = self.get_account_info()
            if not account_info:
                return False
            
            krw_balance = account_info["krw_balance"]
            buy_amount = krw_balance * self.config["buy_ratio"]
            
            if buy_amount < self.config["min_order_amount"]:
                logger.warning(f"매수 가능 금액 부족: {buy_amount:,.0f}원")
                return False
            
            # 가격 단위 조정
            adjusted_price = pyupbit.get_tick_size(current_price * 0.999)  # 약간 낮은 가격으로 설정
            buy_volume = buy_amount / adjusted_price
            
            # 매수 주문
            result = self.upbit.buy_limit_order(self.target_ticker, adjusted_price, buy_volume)
            
            if result:
                self.position.update({
                    "is_holding": True,
                    "buy_price": adjusted_price,
                    "buy_amount": buy_volume,
                    "buy_time": datetime.datetime.now()
                })
                
                logger.info(f"매수 주문 성공: 가격={adjusted_price:,.0f}원, 수량={buy_volume:.8f}{self.target_coin}, "
                           f"총액={buy_amount:,.0f}원")
                return True
            else:
                logger.error("매수 주문 실패")
                return False
        except Exception as e:
            logger.error(f"매수 주문 오류: {e}")
            return False
    
    def execute_sell_order(self, current_price: float, reason: str = "signal") -> bool:
        """매도 주문 실행"""
        try:
            if not self.position["is_holding"]:
                return False
            
            sell_volume = self.position["buy_amount"] * self.config["sell_ratio"]
            
            # 가격 단위 조정
            adjusted_price = pyupbit.get_tick_size(current_price * 1.001)  # 약간 높은 가격으로 설정
            
            # 매도 주문
            result = self.upbit.sell_limit_order(self.target_ticker, adjusted_price, sell_volume)
            
            if result:
                # 수익 계산
                profit = (adjusted_price - self.position["buy_price"]) * sell_volume
                profit_rate = (adjusted_price - self.position["buy_price"]) / self.position["buy_price"]
                
                # 통계 업데이트
                self.position["total_profit"] += profit
                self.position["total_trades"] += 1
                
                if profit > 0:
                    self.position["win_count"] += 1
                else:
                    self.position["loss_count"] += 1
                
                logger.info(f"매도 주문 성공 ({reason}): 가격={adjusted_price:,.0f}원, "
                           f"수량={sell_volume:.8f}{self.target_coin}, 수익={profit:,.0f}원 ({profit_rate:.2%})")
                
                # 포지션 정리 (부분 매도인 경우)
                if self.config["sell_ratio"] == 1.0:
                    self.position.update({
                        "is_holding": False,
                        "buy_price": 0,
                        "buy_amount": 0,
                        "buy_time": None
                    })
                else:
                    self.position["buy_amount"] *= (1 - self.config["sell_ratio"])
                
                return True
            else:
                logger.error("매도 주문 실패")
                return False
        except Exception as e:
            logger.error(f"매도 주문 오류: {e}")
            return False
    
    def print_status(self):
        """현재 상태 출력"""
        try:
            current_price = self.get_current_price()
            account_info = self.get_account_info()
            
            if not current_price or not account_info:
                return
            
            print("=" * 80)
            print(f"현재 시간: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"현재 가격: {current_price:,.0f}원")
            print(f"원화 잔고: {account_info['krw_balance']:,.0f}원")
            print(f"{self.target_coin} 잔고: {account_info['coin_balance']:.8f}{self.target_coin}")
            
            if self.position["is_holding"]:
                profit_rate = (current_price - self.position["buy_price"]) / self.position["buy_price"]
                print(f"포지션: 보유 중 (매수가: {self.position['buy_price']:,.0f}원, "
                      f"수익률: {profit_rate:.2%}, 코인: {self.target_coin})")
            else:
                print("포지션: 없음")
            
            print(f"총 거래 수: {self.position['total_trades']}")
            print(f"승률: {self.position['win_count']}/{self.position['total_trades']} "
                  f"({self.position['win_count']/max(1, self.position['total_trades'])*100:.1f}%)")
            print(f"총 수익: {self.position['total_profit']:,.0f}원")
            print("=" * 80)
        except Exception as e:
            logger.error(f"상태 출력 오류: {e}")
    
    def start_websocket_monitoring(self):
        """웹소켓 실시간 모니터링 시작"""
        try:
            from pyupbit import WebSocketManager
            
            def websocket_handler():
                self.websocket_manager = WebSocketManager("ticker", [self.target_ticker])
                while self.running:
                    try:
                        data = self.websocket_manager.get()
                        if data != 'ConnectionClosedError':
                            # 실시간 데이터 처리
                            current_price = data.get('trade_price', 0)
                            change_rate = data.get('signed_change_rate', 0) * 100
                            
                            # 급격한 가격 변동 알림
                            if abs(change_rate) > 2:  # 2% 이상 변동
                                logger.warning(f"급격한 가격 변동 감지: {change_rate:.2f}%")
                    except Exception as e:
                        logger.error(f"웹소켓 데이터 처리 오류: {e}")
                        time.sleep(1)
            
            websocket_thread = Thread(target=websocket_handler, daemon=True)
            websocket_thread.start()
            logger.info("웹소켓 모니터링 시작")
        except Exception as e:
            logger.error(f"웹소켓 모니터링 시작 오류: {e}")
    
    def trading_loop(self):
        """메인 트레이딩 루프"""
        try:
            current_price = self.get_current_price()
            if not current_price:
                return
            
            # 손절/익절 확인
            stop_action = self.check_stop_loss_take_profit(current_price)
            if stop_action:
                self.execute_sell_order(current_price, stop_action)
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
                    self.execute_buy_order(current_price)
            else:
                # 매도 신호 확인
                if self.generate_sell_signal(df, indicators):
                    self.execute_sell_order(current_price, "signal")
        
        except Exception as e:
            logger.error(f"트레이딩 루프 오류: {e}")
    
    def start_trading(self):
        """자동 매매 시작"""
        self.running = True
        logger.info("자동 매매 시작")
        
        # 웹소켓 모니터링 시작
        self.start_websocket_monitoring()
        
        # 주기적 상태 출력 스케줄
        schedule.every(10).minutes.do(self.print_status)
        
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
        if self.websocket_manager:
            self.websocket_manager.terminate()
        logger.info("자동 매매 중지")
    
    def save_config(self, filename: str = "trading_config.json"):
        """설정 저장"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            logger.info(f"설정 저장 완료: {filename}")
        except Exception as e:
            logger.error(f"설정 저장 오류: {e}")
    
    def load_config(self, filename: str = "trading_config.json"):
        """설정 로드"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    self.config.update(json.load(f))
                logger.info(f"설정 로드 완료: {filename}")
            else:
                logger.info("설정 파일이 없어 기본 설정 사용")
        except Exception as e:
            logger.error(f"설정 로드 오류: {e}")

def select_coin():
    """거래할 코인 선택"""
    # 환경 변수에서 선택된 코인 확인
    selected_coin = os.environ.get('SELECTED_COIN')
    if selected_coin:
        return selected_coin
    
    supported_coins = {
        "1": ("BTC", "비트코인"),
        "2": ("ETH", "이더리움"),
        "3": ("MASK", "마스크 네트워크"),
        "4": ("SOL", "솔라나"),
        "5": ("PEPE", "페페")
    }
    
    print("\n=== 거래할 코인을 선택하세요 ===")
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
    # API 키 설정 (실제 사용 시 환경변수나 별도 파일에서 로드)
    ACCESS_KEY = "YOUR_ACCESS_KEY"
    SECRET_KEY = "YOUR_SECRET_KEY"
    
    # 파일에서 API 키 로드 시도
    try:
        with open("upbit_keys.txt", "r") as f:
            lines = f.readlines()
            ACCESS_KEY = lines[0].strip()
            SECRET_KEY = lines[1].strip()
    except FileNotFoundError:
        print("upbit_keys.txt 파일이 없습니다. API 키를 직접 설정하세요.")
        return
    except Exception as e:
        print(f"API 키 로드 오류: {e}")
        return
    
    # 코인 선택
    selected_coin = select_coin()
    
    # 트레이더 초기화
    trader = CryptoAutoTrader(ACCESS_KEY, SECRET_KEY, selected_coin)
    
    # 설정 로드
    trader.load_config()
    
    # 계정 정보 확인
    account_info = trader.get_account_info()
    if not account_info:
        print("계정 정보 조회 실패. API 키를 확인하세요.")
        return
    
    print(f"=== {trader.supported_coins.get(selected_coin, {}).get('name', selected_coin)} 자동 매매 프로그램 ===")
    print(f"원화 잔고: {account_info['krw_balance']:,.0f}원")
    print(f"{selected_coin} 잔고: {account_info['coin_balance']:.8f}{selected_coin}")
    
    # 사용자 입력
    while True:
        command = input("\n명령어를 입력하세요 (start/stop/status/config/quit): ").strip().lower()
        
        if command == "start":
            trader.start_trading()
        elif command == "stop":
            trader.stop_trading()
        elif command == "status":
            trader.print_status()
        elif command == "config":
            print("현재 설정:")
            for key, value in trader.config.items():
                print(f"  {key}: {value}")
        elif command == "quit":
            trader.stop_trading()
            break
        else:
            print("올바른 명령어를 입력하세요.")


if __name__ == "__main__":
    main()