import pandas as pd
import logging
from typing import Dict, Optional
from ..core.position_manager import PositionManager

logger = logging.getLogger(__name__)


class TechnicalTradingStrategy:
    """기술적 분석 기반 트레이딩 전략"""
    
    def __init__(self, config: Dict, technical_analyzer, is_test_mode: bool = False):
        self.config = config
        self.analyzer = technical_analyzer
        self.is_test_mode = is_test_mode
        self.position_manager = PositionManager()
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> Dict:
        """기술적 지표 계산"""
        try:
            indicators = {}
            
            # 이동평균선
            indicators['ma_short'] = df['close'].rolling(window=self.config['ma_short']).mean()
            indicators['ma_long'] = df['close'].rolling(window=self.config['ma_long']).mean()
            
            # RSI
            indicators['rsi'] = self.analyzer.calculate_rsi(df['close'], self.config['rsi_period'])
            
            # 볼린저 밴드
            indicators['bb_upper'], indicators['bb_middle'], indicators['bb_lower'] = \
                self.analyzer.calculate_bollinger_bands(
                    df['close'], self.config['bb_period'], self.config['bb_std']
                )
            
            # 스토캐스틱
            indicators['stoch_k'], indicators['stoch_d'] = \
                self.analyzer.calculate_stochastic(
                    df['high'], df['low'], df['close'], 
                    self.config['stoch_k'], self.config['stoch_d']
                )
            
            # MACD
            indicators['macd'], indicators['macd_signal'], indicators['macd_histogram'] = \
                self.analyzer.calculate_macd(
                    df['close'], self.config['macd_fast'], 
                    self.config['macd_slow'], self.config['macd_signal']
                )
            
            return indicators
        except Exception as e:
            logger.error(f"기술적 지표 계산 오류: {e}")
            return {}
    
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
            
            # 신호 종합 (테스트 모드: 2개 이상, 실제 모드: 3개 이상)
            signals = [ma_signal, rsi_signal, bb_signal, stoch_signal, macd_signal, price_trend]
            threshold = 2 if self.is_test_mode else 3
            buy_signal = sum(signals) >= threshold
            
            if buy_signal:
                logger.info(f"매수 신호 발생 (임계값: {threshold}): MA={ma_signal}, RSI={rsi_signal}, BB={bb_signal}, "
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
            
            # 신호 종합 (테스트 모드: 2개 이상, 실제 모드: 3개 이상)
            signals = [ma_signal, rsi_signal, bb_signal, stoch_signal, macd_signal, price_trend]
            threshold = 2 if self.is_test_mode else 3
            sell_signal = sum(signals) >= threshold
            
            if sell_signal:
                logger.info(f"매도 신호 발생 (임계값: {threshold}): MA={ma_signal}, RSI={rsi_signal}, BB={bb_signal}, "
                           f"STOCH={stoch_signal}, MACD={macd_signal}, TREND={price_trend}")
            
            return sell_signal
        except Exception as e:
            logger.error(f"매도 신호 생성 오류: {e}")
            return False
    
    def check_stop_loss_take_profit(self, current_price: float) -> Optional[str]:
        """손절/익절 확인"""
        return self.position_manager.check_stop_loss_take_profit(current_price, self.config)
    
    def get_position_manager(self) -> PositionManager:
        """포지션 매니저 반환"""
        return self.position_manager