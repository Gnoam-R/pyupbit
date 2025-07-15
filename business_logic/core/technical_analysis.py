import pandas as pd


class TechnicalAnalyzer:
    """기술적 분석 지표 계산 클래스"""
    
    @staticmethod
    def calculate_rsi(prices, period=14):
        """RSI 계산"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def calculate_bollinger_bands(prices, period=20, std_dev=2):
        """볼린저 밴드 계산"""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return upper_band, sma, lower_band

    @staticmethod
    def calculate_stochastic(high, low, close, k_period=14, d_period=3):
        """스토캐스틱 계산"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()
        return k_percent, d_percent

    @staticmethod
    def calculate_macd(prices, fast=12, slow=26, signal=9):
        """MACD 계산"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        macd_histogram = macd - macd_signal
        return macd, macd_signal, macd_histogram

    @classmethod
    def calculate_technical_indicators(cls, df):
        """모든 기술적 지표를 계산하여 반환"""
        close = df['close']
        high = df['high']
        low = df['low']
        
        # 이동평균선
        sma_5 = close.rolling(window=5).mean()
        sma_20 = close.rolling(window=20).mean()
        ema_5 = close.ewm(span=5).mean()
        ema_20 = close.ewm(span=20).mean()
        
        # RSI
        rsi = cls.calculate_rsi(close)
        
        # 볼린저 밴드
        bb_upper, bb_middle, bb_lower = cls.calculate_bollinger_bands(close)
        
        # 스토캐스틱
        stoch_k, stoch_d = cls.calculate_stochastic(high, low, close)
        
        # MACD
        macd, macd_signal, macd_histogram = cls.calculate_macd(close)
        
        return {
            'sma_5': sma_5.iloc[-1] if len(sma_5) > 0 else None,
            'sma_20': sma_20.iloc[-1] if len(sma_20) > 0 else None,
            'ema_5': ema_5.iloc[-1] if len(ema_5) > 0 else None,
            'ema_20': ema_20.iloc[-1] if len(ema_20) > 0 else None,
            'rsi': rsi.iloc[-1] if len(rsi) > 0 else None,
            'bb_upper': bb_upper.iloc[-1] if len(bb_upper) > 0 else None,
            'bb_middle': bb_middle.iloc[-1] if len(bb_middle) > 0 else None,
            'bb_lower': bb_lower.iloc[-1] if len(bb_lower) > 0 else None,
            'stoch_k': stoch_k.iloc[-1] if len(stoch_k) > 0 else None,
            'stoch_d': stoch_d.iloc[-1] if len(stoch_d) > 0 else None,
            'macd': macd.iloc[-1] if len(macd) > 0 else None,
            'macd_signal': macd_signal.iloc[-1] if len(macd_signal) > 0 else None,
            'macd_histogram': macd_histogram.iloc[-1] if len(macd_histogram) > 0 else None
        }