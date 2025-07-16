import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

logger = logging.getLogger(__name__)


@dataclass
class CoinMetrics:
    """코인 분석 지표"""
    symbol: str
    current_price: float
    volume_24h: float
    change_24h: float
    rsi: float
    macd_signal: str  # 'bullish', 'bearish', 'neutral'
    bb_position: str  # 'oversold', 'overbought', 'neutral'
    momentum_score: float
    volatility_score: float
    volume_score: float
    technical_score: float
    overall_score: float


class CoinAnalyzer:
    """멀티 코인 분석기"""
    
    def __init__(self, market_data_provider, technical_analyzer):
        self.market_data_provider = market_data_provider
        self.technical_analyzer = technical_analyzer
        self.lock = threading.Lock()
        
        # 분석 가중치
        self.weights = {
            'technical': 0.4,
            'momentum': 0.3,
            'volume': 0.2,
            'volatility': 0.1
        }
        
        logger.info("코인 분석기 초기화 완료")
    
    def analyze_single_coin(self, coin_symbol: str) -> Optional[CoinMetrics]:
        """단일 코인 분석"""
        try:
            # 시장 데이터 조회
            current_price = self.market_data_provider.get_current_price_for_coin(coin_symbol)
            if not current_price:
                logger.warning(f"가격 정보 없음: {coin_symbol}")
                return None
            
            # OHLCV 데이터 조회
            df = self.market_data_provider.get_ohlcv_data_for_coin(coin_symbol, "minute5", 100)
            if df is None or len(df) < 50:
                logger.warning(f"OHLCV 데이터 부족: {coin_symbol}")
                return None
            
            # 기술적 지표 계산
            rsi = self.technical_analyzer.calculate_rsi(df['close']).iloc[-1]
            
            # MACD 계산
            macd, macd_signal, macd_histogram = self.technical_analyzer.calculate_macd(df['close'])
            macd_latest = macd.iloc[-1]
            macd_signal_latest = macd_signal.iloc[-1]
            
            # MACD 신호 판단
            if macd_latest > macd_signal_latest:
                macd_signal_str = 'bullish'
            elif macd_latest < macd_signal_latest:
                macd_signal_str = 'bearish'
            else:
                macd_signal_str = 'neutral'
            
            # 볼린저 밴드 계산
            bb_upper, bb_middle, bb_lower = self.technical_analyzer.calculate_bollinger_bands(df['close'])
            bb_upper_latest = bb_upper.iloc[-1]
            bb_lower_latest = bb_lower.iloc[-1]
            
            # 볼린저 밴드 포지션 판단
            if current_price <= bb_lower_latest:
                bb_position = 'oversold'
            elif current_price >= bb_upper_latest:
                bb_position = 'overbought'
            else:
                bb_position = 'neutral'
            
            # 24시간 변동률 계산
            change_24h = ((df['close'].iloc[-1] - df['close'].iloc[-288]) / df['close'].iloc[-288]) * 100 if len(df) > 288 else 0
            
            # 24시간 거래량 계산
            volume_24h = df['volume'].tail(288).sum() if len(df) > 288 else df['volume'].sum()
            
            # 각종 점수 계산
            momentum_score = self._calculate_momentum_score(df, rsi, macd_signal_str)
            volatility_score = self._calculate_volatility_score(df)
            volume_score = self._calculate_volume_score(df)
            technical_score = self._calculate_technical_score(rsi, macd_signal_str, bb_position)
            
            # 종합 점수 계산
            overall_score = (
                technical_score * self.weights['technical'] +
                momentum_score * self.weights['momentum'] +
                volume_score * self.weights['volume'] +
                volatility_score * self.weights['volatility']
            )
            
            return CoinMetrics(
                symbol=coin_symbol,
                current_price=current_price,
                volume_24h=volume_24h,
                change_24h=change_24h,
                rsi=rsi,
                macd_signal=macd_signal_str,
                bb_position=bb_position,
                momentum_score=momentum_score,
                volatility_score=volatility_score,
                volume_score=volume_score,
                technical_score=technical_score,
                overall_score=overall_score
            )
            
        except Exception as e:
            logger.error(f"코인 분석 오류 {coin_symbol}: {e}")
            return None
    
    def analyze_multiple_coins(self, coin_symbols: List[str]) -> List[CoinMetrics]:
        """멀티 코인 동시 분석"""
        results = []
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_coin = {
                executor.submit(self.analyze_single_coin, coin): coin 
                for coin in coin_symbols
            }
            
            for future in as_completed(future_to_coin):
                coin = future_to_coin[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.error(f"코인 분석 실패 {coin}: {e}")
        
        return results
    
    def _calculate_momentum_score(self, df: pd.DataFrame, rsi: float, macd_signal: str) -> float:
        """모멘텀 점수 계산 (0-100)"""
        score = 50  # 기본 점수
        
        # RSI 기반 점수
        if 30 < rsi < 70:
            score += 20  # 적정 범위
        elif rsi < 30:
            score += 30  # 과매도 (매수 기회)
        elif rsi > 70:
            score -= 20  # 과매수
        
        # MACD 신호 기반 점수
        if macd_signal == 'bullish':
            score += 20
        elif macd_signal == 'bearish':
            score -= 20
        
        # 가격 추세 점수
        if len(df) >= 10:
            recent_trend = (df['close'].iloc[-1] - df['close'].iloc[-10]) / df['close'].iloc[-10]
            if recent_trend > 0.02:  # 2% 이상 상승
                score += 10
            elif recent_trend < -0.02:  # 2% 이상 하락
                score -= 10
        
        return max(0, min(100, score))
    
    def _calculate_volatility_score(self, df: pd.DataFrame) -> float:
        """변동성 점수 계산 (0-100)"""
        if len(df) < 20:
            return 50
        
        # 변동성 계산 (20일 표준편차)
        returns = df['close'].pct_change().dropna()
        volatility = returns.tail(20).std() * 100
        
        # 적정 변동성 범위: 2-8%
        if 2 <= volatility <= 8:
            score = 100 - abs(volatility - 5) * 10  # 5%가 최적
        elif volatility < 2:
            score = 30  # 변동성 너무 낮음
        else:
            score = max(0, 70 - (volatility - 8) * 5)  # 변동성 너무 높음
        
        return max(0, min(100, score))
    
    def _calculate_volume_score(self, df: pd.DataFrame) -> float:
        """거래량 점수 계산 (0-100)"""
        if len(df) < 20:
            return 50
        
        # 최근 거래량 vs 평균 거래량
        recent_volume = df['volume'].tail(5).mean()
        avg_volume = df['volume'].tail(20).mean()
        
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
        
        # 거래량 증가 시 높은 점수
        if volume_ratio > 1.5:
            score = 90
        elif volume_ratio > 1.2:
            score = 80
        elif volume_ratio > 1.0:
            score = 70
        elif volume_ratio > 0.8:
            score = 60
        else:
            score = 40
        
        return score
    
    def _calculate_technical_score(self, rsi: float, macd_signal: str, bb_position: str) -> float:
        """기술적 분석 점수 계산 (0-100)"""
        score = 50  # 기본 점수
        
        # RSI 점수
        if 30 <= rsi <= 70:
            score += 20
        elif rsi < 30:
            score += 30  # 과매도
        else:
            score -= 20  # 과매수
        
        # MACD 점수
        if macd_signal == 'bullish':
            score += 20
        elif macd_signal == 'bearish':
            score -= 20
        
        # 볼린저 밴드 점수
        if bb_position == 'oversold':
            score += 15
        elif bb_position == 'overbought':
            score -= 15
        
        return max(0, min(100, score))
    
    def rank_coins_by_score(self, coin_metrics: List[CoinMetrics]) -> List[CoinMetrics]:
        """점수 기준 코인 순위"""
        return sorted(coin_metrics, key=lambda x: x.overall_score, reverse=True)
    
    def get_best_buy_candidates(self, coin_metrics: List[CoinMetrics], 
                               current_positions: List[str], 
                               max_candidates: int = 3) -> List[CoinMetrics]:
        """최적 매수 후보 선정"""
        # 이미 보유한 코인 제외
        available_coins = [coin for coin in coin_metrics if coin.symbol not in current_positions]
        
        # 점수 기준 정렬
        ranked_coins = self.rank_coins_by_score(available_coins)
        
        # 매수 조건 필터링
        buy_candidates = []
        for coin in ranked_coins:
            if self._is_good_buy_candidate(coin):
                buy_candidates.append(coin)
            
            if len(buy_candidates) >= max_candidates:
                break
        
        return buy_candidates
    
    def get_sell_candidates(self, coin_metrics: List[CoinMetrics], 
                           current_positions: List[str]) -> List[CoinMetrics]:
        """매도 후보 선정"""
        # 보유 중인 코인만 필터링
        held_coins = [coin for coin in coin_metrics if coin.symbol in current_positions]
        
        sell_candidates = []
        for coin in held_coins:
            if self._is_good_sell_candidate(coin):
                sell_candidates.append(coin)
        
        return sell_candidates
    
    def _is_good_buy_candidate(self, coin: CoinMetrics) -> bool:
        """매수 후보 판단"""
        # 종합 점수 70 이상
        if coin.overall_score < 70:
            return False
        
        # RSI 과매수 상태 제외
        if coin.rsi > 75:
            return False
        
        # 볼린저 밴드 과매수 상태 제외
        if coin.bb_position == 'overbought':
            return False
        
        # 거래량 점수 50 이상
        if coin.volume_score < 50:
            return False
        
        return True
    
    def _is_good_sell_candidate(self, coin: CoinMetrics) -> bool:
        """매도 후보 판단"""
        # 종합 점수 40 이하
        if coin.overall_score <= 40:
            return True
        
        # RSI 과매수 상태
        if coin.rsi > 80:
            return True
        
        # 볼린저 밴드 과매수 상태
        if coin.bb_position == 'overbought':
            return True
        
        # MACD 하락 신호
        if coin.macd_signal == 'bearish' and coin.overall_score < 60:
            return True
        
        return False