import json
import os
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class OptimizedTradingConfig:
    """수익률 최적화된 트레이딩 설정 관리 클래스"""
    
    # 기본 설정 (보수적)
    CONSERVATIVE_CONFIG = {
        "buy_ratio": 0.1,
        "sell_ratio": 0.5,
        "stop_loss": 0.03,
        "take_profit": 0.05,
        "min_order_amount": 5000,
        "trading_interval": 60,
        "ma_short": 5,
        "ma_long": 20,
        "rsi_period": 14,
        "rsi_oversold": 30,
        "rsi_overbought": 70,
        "bb_period": 20,
        "bb_std": 2,
        "stoch_k": 14,
        "stoch_d": 3,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
    }
    
    # 공격적 설정 (수익률 향상)
    AGGRESSIVE_CONFIG = {
        "buy_ratio": 0.3,          # 30% 투자 (더 많은 자본 활용)
        "sell_ratio": 1.0,         # 100% 매도 (완전 매도로 수익 극대화)
        "stop_loss": 0.04,         # 4% 손절 (위험 관리 유지)
        "take_profit": 0.12,       # 12% 익절 (더 큰 수익 추구)
        "min_order_amount": 5000,
        "trading_interval": 30,    # 30초 간격 (더 빠른 반응)
        "ma_short": 3,             # 더 빠른 이동평균
        "ma_long": 12,             # 더 빠른 이동평균
        "rsi_period": 10,          # 더 민감한 RSI
        "rsi_oversold": 25,        # 더 민감한 과매도
        "rsi_overbought": 75,      # 더 민감한 과매수
        "bb_period": 15,           # 더 민감한 볼린저 밴드
        "bb_std": 1.8,             # 더 좁은 밴드
        "stoch_k": 10,             # 더 민감한 스토캐스틱
        "stoch_d": 3,
        "macd_fast": 8,            # 더 빠른 MACD
        "macd_slow": 18,           # 더 빠른 MACD
        "macd_signal": 6,          # 더 빠른 신호
    }
    
    # 균형 설정 (위험과 수익의 균형)
    BALANCED_CONFIG = {
        "buy_ratio": 0.2,          # 20% 투자
        "sell_ratio": 0.8,         # 80% 매도
        "stop_loss": 0.035,        # 3.5% 손절
        "take_profit": 0.08,       # 8% 익절
        "min_order_amount": 5000,
        "trading_interval": 45,    # 45초 간격
        "ma_short": 4,
        "ma_long": 16,
        "rsi_period": 12,
        "rsi_oversold": 28,
        "rsi_overbought": 72,
        "bb_period": 18,
        "bb_std": 1.9,
        "stoch_k": 12,
        "stoch_d": 3,
        "macd_fast": 10,
        "macd_slow": 22,
        "macd_signal": 7,
    }
    
    # 고수익 설정 (높은 위험, 높은 수익)
    HIGH_PROFIT_CONFIG = {
        "buy_ratio": 0.5,          # 50% 투자 (최대 자본 활용)
        "sell_ratio": 1.0,         # 100% 매도
        "stop_loss": 0.05,         # 5% 손절 (약간 더 여유)
        "take_profit": 0.15,       # 15% 익절 (높은 수익 목표)
        "min_order_amount": 5000,
        "trading_interval": 20,    # 20초 간격 (매우 빠른 반응)
        "ma_short": 2,             # 매우 빠른 이동평균
        "ma_long": 8,              # 매우 빠른 이동평균
        "rsi_period": 8,           # 매우 민감한 RSI
        "rsi_oversold": 20,        # 매우 민감한 과매도
        "rsi_overbought": 80,      # 매우 민감한 과매수
        "bb_period": 12,           # 매우 민감한 볼린저 밴드
        "bb_std": 1.5,             # 매우 좁은 밴드
        "stoch_k": 8,              # 매우 민감한 스토캐스틱
        "stoch_d": 2,
        "macd_fast": 6,            # 매우 빠른 MACD
        "macd_slow": 14,           # 매우 빠른 MACD
        "macd_signal": 4,          # 매우 빠른 신호
    }
    
    def __init__(self, config_type: str = "balanced", config_file: str = "optimized_trading_config.json"):
        self.config_file = config_file
        self.config_type = config_type
        
        # 설정 타입에 따라 기본 설정 선택
        if config_type == "conservative":
            self.config = self.CONSERVATIVE_CONFIG.copy()
        elif config_type == "aggressive":
            self.config = self.AGGRESSIVE_CONFIG.copy()
        elif config_type == "balanced":
            self.config = self.BALANCED_CONFIG.copy()
        elif config_type == "high_profit":
            self.config = self.HIGH_PROFIT_CONFIG.copy()
        else:
            self.config = self.BALANCED_CONFIG.copy()
        
        self.load_config()
    
    def load_config(self):
        """설정 로드"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
                logger.info(f"최적화 설정 로드 완료: {self.config_file}")
            else:
                logger.info(f"설정 파일이 없어 {self.config_type} 기본 설정 사용")
        except Exception as e:
            logger.error(f"설정 로드 오류: {e}")
    
    def save_config(self):
        """설정 저장"""
        try:
            config_with_meta = {
                "config_type": self.config_type,
                "config": self.config
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_with_meta, f, ensure_ascii=False, indent=2)
            logger.info(f"최적화 설정 저장 완료: {self.config_file}")
        except Exception as e:
            logger.error(f"설정 저장 오류: {e}")
    
    def get_config(self) -> Dict:
        """설정 반환"""
        return self.config.copy()
    
    def update_config(self, new_config: Dict):
        """설정 업데이트"""
        self.config.update(new_config)
    
    def get(self, key: str, default=None):
        """특정 설정 값 조회"""
        return self.config.get(key, default)
    
    def set(self, key: str, value):
        """특정 설정 값 설정"""
        self.config[key] = value
    
    def get_config_info(self) -> Dict:
        """설정 정보 반환"""
        return {
            "config_type": self.config_type,
            "description": self._get_config_description(),
            "risk_level": self._get_risk_level(),
            "expected_profit": self._get_expected_profit()
        }
    
    def _get_config_description(self) -> str:
        """설정 설명 반환"""
        descriptions = {
            "conservative": "보수적 설정 - 안전한 투자, 낮은 수익",
            "balanced": "균형 설정 - 위험과 수익의 균형",
            "aggressive": "공격적 설정 - 중간 위험, 중간 수익",
            "high_profit": "고수익 설정 - 높은 위험, 높은 수익"
        }
        return descriptions.get(self.config_type, "알 수 없는 설정")
    
    def _get_risk_level(self) -> str:
        """위험 수준 반환"""
        risk_levels = {
            "conservative": "낮음",
            "balanced": "중간",
            "aggressive": "중간-높음",
            "high_profit": "높음"
        }
        return risk_levels.get(self.config_type, "알 수 없음")
    
    def _get_expected_profit(self) -> str:
        """예상 수익 반환"""
        expected_profits = {
            "conservative": "1-3%",
            "balanced": "3-6%",
            "aggressive": "6-10%",
            "high_profit": "10-20%"
        }
        return expected_profits.get(self.config_type, "알 수 없음")


def select_config_type():
    """설정 타입 선택"""
    print("\n=== 트레이딩 설정 타입을 선택하세요 ===")
    print("1. 보수적 설정 (안전한 투자, 낮은 수익)")
    print("2. 균형 설정 (위험과 수익의 균형)")
    print("3. 공격적 설정 (중간 위험, 중간 수익)")
    print("4. 고수익 설정 (높은 위험, 높은 수익)")
    
    config_map = {
        "1": "conservative",
        "2": "balanced",
        "3": "aggressive",
        "4": "high_profit"
    }
    
    while True:
        choice = input("\n번호를 선택하세요 (1-4): ").strip()
        if choice in config_map:
            return config_map[choice]
        else:
            print("올바른 번호를 입력하세요.")