import logging
from typing import Dict, List, Optional, Tuple
import pandas as pd
import pyupbit
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import threading
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MultiMarketDataProvider:
    """멀티 코인 시장 데이터 제공자"""
    
    def __init__(self, coins: List[str]):
        self.coins = coins
        self.tickers = {coin: f"KRW-{coin}" for coin in coins}
        self.cache = {}
        self.cache_timeout = 30  # 30초 캐시
        self.lock = threading.Lock()
        
        # 요청 제한 관리
        self.request_delay = 0.1  # 요청 간 100ms 대기
        self.last_request_time = 0
        
        logger.info(f"멀티 마켓 데이터 제공자 초기화: {len(coins)}개 코인")
    
    def _rate_limit(self):
        """API 요청 제한 관리"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self.last_request_time = time.time()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """캐시 유효성 확인"""
        if cache_key not in self.cache:
            return False
        
        cache_time = self.cache[cache_key]['timestamp']
        return (datetime.now() - cache_time).seconds < self.cache_timeout
    
    def get_current_price_for_coin(self, coin: str) -> Optional[float]:
        """단일 코인 현재가 조회"""
        if coin not in self.tickers:
            return None
        
        cache_key = f"price_{coin}"
        with self.lock:
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]['data']
        
        try:
            self._rate_limit()
            price = pyupbit.get_current_price(self.tickers[coin])
            
            with self.lock:
                self.cache[cache_key] = {
                    'data': price,
                    'timestamp': datetime.now()
                }
            
            return price
        except Exception as e:
            logger.error(f"현재가 조회 오류 {coin}: {e}")
            return None
    
    def get_all_current_prices(self) -> Dict[str, float]:
        """모든 코인 현재가 동시 조회"""
        cache_key = "all_prices"
        with self.lock:
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]['data']
        
        def fetch_price(coin):
            try:
                self._rate_limit()
                price = pyupbit.get_current_price(self.tickers[coin])
                return coin, price
            except Exception as e:
                logger.error(f"가격 조회 실패 {coin}: {e}")
                return coin, None
        
        prices = {}
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_coin = {
                executor.submit(fetch_price, coin): coin 
                for coin in self.coins
            }
            
            for future in as_completed(future_to_coin):
                coin, price = future.result()
                if price is not None:
                    prices[coin] = price
        
        with self.lock:
            self.cache[cache_key] = {
                'data': prices,
                'timestamp': datetime.now()
            }
        
        return prices
    
    def get_ohlcv_data_for_coin(self, coin: str, interval: str = "minute5", count: int = 200) -> Optional[pd.DataFrame]:
        """단일 코인 OHLCV 데이터 조회"""
        if coin not in self.tickers:
            return None
        
        cache_key = f"ohlcv_{coin}_{interval}_{count}"
        with self.lock:
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]['data']
        
        try:
            self._rate_limit()
            df = pyupbit.get_ohlcv(self.tickers[coin], interval=interval, count=count)
            
            with self.lock:
                self.cache[cache_key] = {
                    'data': df,
                    'timestamp': datetime.now()
                }
            
            return df
        except Exception as e:
            logger.error(f"OHLCV 조회 오류 {coin}: {e}")
            return None
    
    def get_all_ohlcv_data(self, interval: str = "minute5", count: int = 200) -> Dict[str, pd.DataFrame]:
        """모든 코인 OHLCV 데이터 동시 조회"""
        cache_key = f"all_ohlcv_{interval}_{count}"
        with self.lock:
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]['data']
        
        def fetch_ohlcv(coin):
            try:
                self._rate_limit()
                df = pyupbit.get_ohlcv(self.tickers[coin], interval=interval, count=count)
                return coin, df
            except Exception as e:
                logger.error(f"OHLCV 조회 실패 {coin}: {e}")
                return coin, None
        
        ohlcv_data = {}
        
        with ThreadPoolExecutor(max_workers=3) as executor:  # OHLCV는 더 제한적으로
            future_to_coin = {
                executor.submit(fetch_ohlcv, coin): coin 
                for coin in self.coins
            }
            
            for future in as_completed(future_to_coin):
                coin, df = future.result()
                if df is not None and not df.empty:
                    ohlcv_data[coin] = df
        
        with self.lock:
            self.cache[cache_key] = {
                'data': ohlcv_data,
                'timestamp': datetime.now()
            }
        
        return ohlcv_data
    
    def get_market_summary(self) -> Dict[str, Dict]:
        """시장 전체 요약 정보"""
        cache_key = "market_summary"
        with self.lock:
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]['data']
        
        def fetch_coin_info(coin):
            try:
                self._rate_limit()
                ticker = self.tickers[coin]
                
                # 현재가
                current_price = pyupbit.get_current_price(ticker)
                if current_price is None:
                    return coin, None
                
                # 24시간 데이터
                df = pyupbit.get_ohlcv(ticker, interval="minute1", count=1440)  # 24시간
                if df is None or df.empty:
                    return coin, None
                
                # 24시간 변동률
                change_24h = ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]) * 100
                
                # 24시간 거래량
                volume_24h = df['volume'].sum()
                
                # 24시간 고가/저가
                high_24h = df['high'].max()
                low_24h = df['low'].min()
                
                return coin, {
                    'current_price': current_price,
                    'change_24h': change_24h,
                    'volume_24h': volume_24h,
                    'high_24h': high_24h,
                    'low_24h': low_24h,
                    'timestamp': datetime.now()
                }
            except Exception as e:
                logger.error(f"마켓 정보 조회 실패 {coin}: {e}")
                return coin, None
        
        market_data = {}
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_coin = {
                executor.submit(fetch_coin_info, coin): coin 
                for coin in self.coins
            }
            
            for future in as_completed(future_to_coin):
                coin, info = future.result()
                if info is not None:
                    market_data[coin] = info
        
        with self.lock:
            self.cache[cache_key] = {
                'data': market_data,
                'timestamp': datetime.now()
            }
        
        return market_data
    
    def get_top_gainers(self, limit: int = 5) -> List[Tuple[str, float]]:
        """상위 상승 코인"""
        market_data = self.get_market_summary()
        
        gainers = []
        for coin, info in market_data.items():
            if 'change_24h' in info:
                gainers.append((coin, info['change_24h']))
        
        gainers.sort(key=lambda x: x[1], reverse=True)
        return gainers[:limit]
    
    def get_top_losers(self, limit: int = 5) -> List[Tuple[str, float]]:
        """상위 하락 코인"""
        market_data = self.get_market_summary()
        
        losers = []
        for coin, info in market_data.items():
            if 'change_24h' in info:
                losers.append((coin, info['change_24h']))
        
        losers.sort(key=lambda x: x[1])
        return losers[:limit]
    
    def get_high_volume_coins(self, limit: int = 5) -> List[Tuple[str, float]]:
        """고거래량 코인"""
        market_data = self.get_market_summary()
        
        high_volume = []
        for coin, info in market_data.items():
            if 'volume_24h' in info:
                high_volume.append((coin, info['volume_24h']))
        
        high_volume.sort(key=lambda x: x[1], reverse=True)
        return high_volume[:limit]
    
    def clear_cache(self):
        """캐시 초기화"""
        with self.lock:
            self.cache.clear()
            logger.info("캐시 초기화 완료")
    
    def get_cache_stats(self) -> Dict:
        """캐시 통계"""
        with self.lock:
            total_entries = len(self.cache)
            valid_entries = sum(1 for key in self.cache.keys() if self._is_cache_valid(key))
            
            return {
                'total_entries': total_entries,
                'valid_entries': valid_entries,
                'cache_hit_rate': valid_entries / max(1, total_entries) * 100
            }
    
    def update_coin_list(self, new_coins: List[str]):
        """코인 목록 업데이트"""
        self.coins = new_coins
        self.tickers = {coin: f"KRW-{coin}" for coin in new_coins}
        self.clear_cache()
        logger.info(f"코인 목록 업데이트: {len(new_coins)}개 코인")
    
    def is_market_open(self) -> bool:
        """시장 개장 여부 확인 (암호화폐는 24시간이지만 거래량 확인용)"""
        try:
            current_time = datetime.now()
            # 새벽 시간대 (2-6시) 거래량 감소 시간으로 판단
            if 2 <= current_time.hour <= 6:
                return False
            return True
        except:
            return True
    
    def get_market_health_score(self) -> float:
        """시장 건강도 점수 (0-100)"""
        try:
            market_data = self.get_market_summary()
            if not market_data:
                return 50
            
            # 상승 코인 비율
            up_coins = sum(1 for info in market_data.values() 
                          if info.get('change_24h', 0) > 0)
            up_ratio = up_coins / len(market_data)
            
            # 거래량 활성도
            total_volume = sum(info.get('volume_24h', 0) for info in market_data.values())
            avg_volume = total_volume / len(market_data)
            volume_score = min(100, avg_volume / 1000000)  # 정규화
            
            # 종합 점수
            health_score = (up_ratio * 60) + (volume_score * 0.4)
            
            return min(100, max(0, health_score))
        except:
            return 50