import pyupbit
import pandas as pd
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class MarketDataProvider:
    """시장 데이터 제공 클래스"""
    
    def __init__(self, target_coin: str):
        self.target_coin = target_coin
        self.target_ticker = f"KRW-{target_coin}"
    
    def get_current_price(self) -> Optional[float]:
        """현재가 조회"""
        try:
            return pyupbit.get_current_price(self.target_ticker)
        except Exception as e:
            logger.error(f"현재가 조회 오류: {e}")
            return None
    
    def get_ohlcv_data(self, interval: str = "minute5", count: int = 200) -> Optional[pd.DataFrame]:
        """OHLCV 데이터 조회"""
        try:
            df = pyupbit.get_ohlcv(self.target_ticker, interval=interval, count=count)
            return df
        except Exception as e:
            logger.error(f"OHLCV 데이터 조회 오류: {e}")
            return None
    
    def get_orderbook(self) -> Optional[Dict]:
        """호가 정보 조회"""
        try:
            return pyupbit.get_orderbook(self.target_ticker)
        except Exception as e:
            logger.error(f"호가 정보 조회 오류: {e}")
            return None