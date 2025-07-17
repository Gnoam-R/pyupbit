import pandas as pd
import logging
from typing import Dict, Optional, Tuple
from ..core.technical_analysis import TechnicalAnalyzer
from ..core.position_manager import PositionManager
from ..utils.format_helper import format_profit_rate

logger = logging.getLogger(__name__)


class PriorityTradingStrategy:
    """우선순위 기반 트레이딩 전략 클래스"""
    
    def __init__(self, config: Dict, technical_analyzer: TechnicalAnalyzer, is_test_mode: bool = False):
        self.config = config
        self.analyzer = technical_analyzer
        self.is_test_mode = is_test_mode
        self.position_manager = PositionManager()
        
        # 전략 우선순위 설정
        self.strategy_priority = [
            "trend_following",    # 1순위: 추세 추종 (이동평균선 교차)
            "momentum_indicators", # 2순위: 보조 지표 (RSI, MACD)
            "advanced_strategies"  # 3순위: 고급 전략 (향후 LLM 연동)
        ]
        
        # 전략 이름 매핑
        self.strategy_names = {
            "trend_following": "추세 추종 전략",
            "momentum_indicators": "보조 지표 전략",
            "advanced_strategies": "고급 전략"
        }
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> Dict:
        """기술적 지표 계산"""
        try:
            indicators = {}
            
            # 이동평균선
            indicators['ma_short'] = df['close'].rolling(window=self.config['ma_short']).mean()
            indicators['ma_long'] = df['close'].rolling(window=self.config['ma_long']).mean()
            
            # RSI
            indicators['rsi'] = self.analyzer.calculate_rsi(df['close'], self.config['rsi_period'])
            
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
    
    def _check_trend_following_strategy(self, df: pd.DataFrame, indicators: Dict) -> Tuple[str, float, str]:
        """
        제1순위: 추세 추종 전략 (이동평균선 교차)
        
        Returns:
            (signal_type, strength, reason)
        """
        try:
            # 이동평균선 교차 확인
            ma_short_current = indicators['ma_short'].iloc[-1]
            ma_long_current = indicators['ma_long'].iloc[-1]
            ma_short_prev = indicators['ma_short'].iloc[-2]
            ma_long_prev = indicators['ma_long'].iloc[-2]
            
            # 골든크로스 (상승 추세 시작)
            if (ma_short_current > ma_long_current and ma_short_prev <= ma_long_prev):
                strength = 1.0  # 최고 강도
                reason = f"골든크로스 발생 (단기MA: {ma_short_current:.0f} > 장기MA: {ma_long_current:.0f})"
                return "buy", strength, reason
            
            # 데드크로스 (하락 추세 시작)
            elif (ma_short_current < ma_long_current and ma_short_prev >= ma_long_prev):
                strength = 1.0  # 최고 강도
                reason = f"데드크로스 발생 (단기MA: {ma_short_current:.0f} < 장기MA: {ma_long_current:.0f})"
                return "sell", strength, reason
            
            # 추세 지속 확인
            elif ma_short_current > ma_long_current:
                # 상승 추세 지속
                trend_strength = (ma_short_current - ma_long_current) / ma_long_current
                if trend_strength > 0.02:  # 2% 이상 차이
                    strength = 0.6
                    reason = f"상승 추세 지속 (추세 강도: {trend_strength:.1%})"
                    return "buy", strength, reason
                    
            elif ma_short_current < ma_long_current:
                # 하락 추세 지속
                trend_strength = (ma_long_current - ma_short_current) / ma_long_current
                if trend_strength > 0.02:  # 2% 이상 차이
                    strength = 0.6
                    reason = f"하락 추세 지속 (추세 강도: {trend_strength:.1%})"
                    return "sell", strength, reason
            
            return "hold", 0.0, "추세 신호 없음"
            
        except Exception as e:
            logger.error(f"추세 추종 전략 오류: {e}")
            return "hold", 0.0, "전략 오류"
    
    def _check_momentum_indicators(self, df: pd.DataFrame, indicators: Dict) -> Tuple[str, float, str]:
        """
        제2순위: 보조 지표 활용 전략 (RSI, MACD)
        """
        try:
            signals = []
            reasons = []
            
            # RSI 신호
            rsi_current = indicators['rsi'].iloc[-1]
            if rsi_current < self.config['rsi_oversold']:
                signals.append(("buy", 0.8, f"RSI 과매도 ({rsi_current:.1f})"))
            elif rsi_current > self.config['rsi_overbought']:
                signals.append(("sell", 0.8, f"RSI 과매수 ({rsi_current:.1f})"))
            
            # MACD 신호
            macd_current = indicators['macd'].iloc[-1]
            macd_signal_current = indicators['macd_signal'].iloc[-1]
            macd_prev = indicators['macd'].iloc[-2]
            macd_signal_prev = indicators['macd_signal'].iloc[-2]
            
            # MACD 상승 돌파
            if (macd_current > macd_signal_current and macd_prev <= macd_signal_prev):
                signals.append(("buy", 0.7, f"MACD 상승 돌파 ({macd_current:.2f} > {macd_signal_current:.2f})"))
            # MACD 하락 돌파
            elif (macd_current < macd_signal_current and macd_prev >= macd_signal_prev):
                signals.append(("sell", 0.7, f"MACD 하락 돌파 ({macd_current:.2f} < {macd_signal_current:.2f})"))
            
            # 가장 강한 신호 선택
            if signals:
                strongest_signal = max(signals, key=lambda x: x[1])
                return strongest_signal[0], strongest_signal[1], strongest_signal[2]
            
            return "hold", 0.0, "보조 지표 신호 없음"
            
        except Exception as e:
            logger.error(f"보조 지표 전략 오류: {e}")
            return "hold", 0.0, "전략 오류"
    
    def _check_advanced_strategies(self, df: pd.DataFrame, indicators: Dict) -> Tuple[str, float, str]:
        """
        제3순위: 고급 전략 (향후 LLM 연동 예정)
        현재는 기본 구현만 제공
        """
        try:
            # 향후 LLM 연동 시 이 부분에 고급 전략 추가
            # 현재는 변동성 기반 간단한 전략만 구현
            
            current_price = df['close'].iloc[-1]
            price_change = (current_price - df['close'].iloc[-10]) / df['close'].iloc[-10]
            
            if abs(price_change) > 0.05:  # 5% 이상 변동
                if price_change > 0:
                    return "buy", 0.3, f"고변동성 상승 ({price_change:.1%})"
                else:
                    return "sell", 0.3, f"고변동성 하락 ({price_change:.1%})"
            
            return "hold", 0.0, "고급 전략 신호 없음"
            
        except Exception as e:
            logger.error(f"고급 전략 오류: {e}")
            return "hold", 0.0, "전략 오류"
    
    def generate_trading_signal(self, df: pd.DataFrame, indicators: Dict) -> Tuple[str, Dict]:
        """
        우선순위에 따라 매매 신호 생성
        
        Returns:
            (signal, strategy_info)
        """
        try:
            strategy_results = {}
            
            # 1순위: 추세 추종 전략
            trend_signal, trend_strength, trend_reason = self._check_trend_following_strategy(df, indicators)
            strategy_results['trend_following'] = {
                'signal': trend_signal,
                'strength': trend_strength,
                'reason': trend_reason,
                'priority': 1
            }
            
            # 2순위: 보조 지표 전략
            momentum_signal, momentum_strength, momentum_reason = self._check_momentum_indicators(df, indicators)
            strategy_results['momentum_indicators'] = {
                'signal': momentum_signal,
                'strength': momentum_strength,
                'reason': momentum_reason,
                'priority': 2
            }
            
            # 3순위: 고급 전략
            advanced_signal, advanced_strength, advanced_reason = self._check_advanced_strategies(df, indicators)
            strategy_results['advanced_strategies'] = {
                'signal': advanced_signal,
                'strength': advanced_strength,
                'reason': advanced_reason,
                'priority': 3
            }
            
            # 우선순위에 따라 최종 신호 결정
            final_signal = "hold"
            selected_strategy = None
            
            # 1순위 전략이 강한 신호를 보내면 우선 채택
            if trend_strength >= 1.0:
                final_signal = trend_signal
                selected_strategy = 'trend_following'
            # 1순위가 약한 신호이고 2순위가 강한 신호를 보내면 2순위 채택
            elif trend_strength < 0.8 and momentum_strength >= 0.7:
                final_signal = momentum_signal
                selected_strategy = 'momentum_indicators'
            # 1순위가 중간 강도 신호를 보내면 채택
            elif trend_strength >= 0.6:
                final_signal = trend_signal
                selected_strategy = 'trend_following'
            # 2순위 신호만 있으면 채택
            elif momentum_strength >= 0.5:
                final_signal = momentum_signal
                selected_strategy = 'momentum_indicators'
            # 마지막으로 3순위 신호 확인
            elif advanced_strength >= 0.3:
                final_signal = advanced_signal
                selected_strategy = 'advanced_strategies'
            
            # 최종 결과 정리
            result_info = {
                'final_signal': final_signal,
                'selected_strategy': selected_strategy,
                'all_strategies': strategy_results,
                'decision_log': self._generate_decision_log(strategy_results, selected_strategy)
            }
            
            return final_signal, result_info
            
        except Exception as e:
            logger.error(f"매매 신호 생성 오류: {e}")
            return "hold", {'error': str(e)}
    
    def _generate_decision_log(self, strategy_results: Dict, selected_strategy: str) -> str:
        """의사결정 로그 생성"""
        try:
            log_lines = []
            log_lines.append("📊 전략별 분석 결과:")
            
            for strategy_name, result in strategy_results.items():
                priority = result['priority']
                signal = result['signal']
                strength = result['strength']
                reason = result['reason']
                
                status = "✅ 선택됨" if strategy_name == selected_strategy else "⚪ 참고"
                log_lines.append(f"   {priority}순위 [{strategy_name}] {status}")
                log_lines.append(f"     신호: {signal.upper()}, 강도: {strength:.1f}, 이유: {reason}")
            
            if selected_strategy:
                selected_info = strategy_results[selected_strategy]
                strategy_name = self.strategy_names.get(selected_strategy, selected_strategy)
                log_lines.append(f"🎯 최종 선택: {strategy_name} ({selected_info['signal'].upper()})")
                log_lines.append(f"   이유: {selected_info['reason']}")
            else:
                log_lines.append("🎯 최종 선택: 매매 보류 (충분한 신호 없음)")
            
            return "\n".join(log_lines)
            
        except Exception as e:
            return f"로그 생성 오류: {e}"
    
    def generate_buy_signal(self, df: pd.DataFrame, indicators: Dict) -> Tuple[bool, Dict]:
        """매수 신호 생성"""
        signal, info = self.generate_trading_signal(df, indicators)
        should_buy = signal == "buy"
        
        if should_buy:
            logger.info(f"🟢 매수 신호 발생!")
            logger.info(info['decision_log'])
        
        return should_buy, info
    
    def generate_sell_signal(self, df: pd.DataFrame, indicators: Dict) -> Tuple[bool, Dict]:
        """매도 신호 생성"""
        signal, info = self.generate_trading_signal(df, indicators)
        should_sell = signal == "sell"
        
        if should_sell:
            logger.info(f"🔴 매도 신호 발생!")
            logger.info(info['decision_log'])
        
        return should_sell, info
    
    def check_stop_loss_take_profit(self, current_price: float) -> Optional[str]:
        """손절/익절 확인"""
        return self.position_manager.check_stop_loss_take_profit(current_price, self.config)
    
    def get_position_manager(self) -> PositionManager:
        """포지션 매니저 반환"""
        return self.position_manager
    
    def get_statistics(self) -> Dict:
        """거래 통계 반환"""
        return self.position_manager.get_statistics()
    
    def get_position_info(self) -> Dict:
        """포지션 정보 반환"""
        return self.position_manager.get_position_info()