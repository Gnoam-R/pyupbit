import json
import os
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class TradingConfig:
    """트레이딩 설정 관리 클래스"""
    
    DEFAULT_CONFIG = {
        # 매매 비율 설정 (균형있는 포지션 관리)
        "buy_ratio": 0.2,           # 보유 원화의 20% 매수 (더 적극적)
        "sell_ratio": 0.3,          # 보유 코인의 30% 매도 (분할 매도)
        
        # 리스크 관리 (위험 대비 수익 개선)
        "stop_loss": 0.05,          # 5% 손절 (변동성 고려)
        "take_profit": 0.08,        # 8% 익절 (1:1.6 비율)
        
        # 주문 설정
        "min_order_amount": 5000,
        "trading_interval": 60,
        
        # 이동평균선 (신호 개선)
        "ma_short": 7,              # 단기 MA (노이즈 감소)
        "ma_long": 21,              # 장기 MA (3주 평균)
        
        # RSI 설정 (과매수/과매도 개선)
        "rsi_period": 14,
        "rsi_oversold": 25,         # 과매도 기준 강화
        "rsi_overbought": 75,       # 과매수 기준 강화
        
        # 볼린저 밴드
        "bb_period": 20,
        "bb_std": 2,
        
        # 스토캐스틱 (더 민감한 설정)
        "stoch_k": 14,
        "stoch_d": 3,
        "stoch_oversold": 20,       # 스토캐스틱 과매도 기준
        "stoch_overbought": 80,     # 스토캐스틱 과매수 기준
        
        # MACD
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
    }
    
    def __init__(self, config_file: str = "trading_config.json"):
        self.config_file = config_file
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()
    
    def load_config(self):
        """설정 로드"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
                logger.info(f"설정 로드 완료: {self.config_file}")
            else:
                logger.info("설정 파일이 없어 기본 설정 사용")
        except Exception as e:
            logger.error(f"설정 로드 오류: {e}")
    
    def save_config(self):
        """설정 저장"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            logger.info(f"설정 저장 완료: {self.config_file}")
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