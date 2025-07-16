import json
import os
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BalancePersistence:
    """잔고 지속성 관리 클래스"""
    
    def __init__(self, coin_symbol: str, data_dir: str = "balance_data"):
        self.coin_symbol = coin_symbol
        self.data_dir = data_dir
        self.balance_file = os.path.join(data_dir, f"{coin_symbol}_balance.json")
        self.history_file = os.path.join(data_dir, f"{coin_symbol}_history.json")
        
        # 디렉토리 생성
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
    
    def _serialize_datetime_objects(self, data):
        """datetime 객체를 ISO 형식 문자열로 변환"""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                elif isinstance(value, dict):
                    result[key] = self._serialize_datetime_objects(value)
                elif isinstance(value, list):
                    result[key] = [self._serialize_datetime_objects(item) if isinstance(item, (dict, datetime)) 
                                  else item.isoformat() if isinstance(item, datetime) else item 
                                  for item in value]
                else:
                    result[key] = value
            return result
        elif isinstance(data, datetime):
            return data.isoformat()
        else:
            return data
    
    def save_balance(self, krw_balance: float, coin_balance: float, 
                    total_value: float, profit_loss: float, profit_rate: float,
                    position_info: Dict, trading_stats: Dict):
        """잔고 정보 저장"""
        try:
            # datetime 객체를 ISO 형식 문자열로 변환
            position_serializable = self._serialize_datetime_objects(position_info.copy())
            trading_stats_serializable = self._serialize_datetime_objects(trading_stats.copy())
            
            balance_data = {
                "coin_symbol": self.coin_symbol,
                "last_updated": datetime.now().isoformat(),
                "balances": {
                    "KRW": krw_balance,
                    self.coin_symbol: coin_balance
                },
                "performance": {
                    "total_value": total_value,
                    "profit_loss": profit_loss,
                    "profit_rate": profit_rate
                },
                "position": position_serializable,
                "trading_stats": trading_stats_serializable
            }
            
            with open(self.balance_file, 'w', encoding='utf-8') as f:
                json.dump(balance_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 잔고 정보 저장 완료: {self.balance_file}")
            
        except Exception as e:
            logger.error(f"잔고 정보 저장 오류: {e}")
    
    def load_balance(self) -> Optional[Dict]:
        """잔고 정보 로드"""
        try:
            if os.path.exists(self.balance_file):
                with open(self.balance_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"💾 잔고 정보 로드 완료: {self.balance_file}")
                    return data
            else:
                logger.info("기존 잔고 정보 없음, 새로 시작")
                return None
        except Exception as e:
            logger.error(f"잔고 정보 로드 오류: {e}")
            return None
    
    def save_trade_history(self, trade_record: Dict):
        """거래 내역 저장"""
        try:
            history = []
            
            # 기존 히스토리 로드
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            
            # datetime 객체 직렬화
            trade_record_serializable = self._serialize_datetime_objects(trade_record.copy())
            if "timestamp" not in trade_record_serializable:
                trade_record_serializable["timestamp"] = datetime.now().isoformat()
            
            # 새 거래 추가
            history.append(trade_record_serializable)
            
            # 최근 1000개만 유지
            if len(history) > 1000:
                history = history[-1000:]
            
            # 저장
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"거래 내역 저장: {trade_record_serializable['type']}")
            
        except Exception as e:
            logger.error(f"거래 내역 저장 오류: {e}")
    
    def load_trade_history(self) -> list:
        """거래 내역 로드"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return []
        except Exception as e:
            logger.error(f"거래 내역 로드 오류: {e}")
            return []
    
    def get_balance_summary(self) -> str:
        """잔고 요약 정보 반환"""
        data = self.load_balance()
        if not data:
            return "저장된 잔고 정보가 없습니다."
        
        summary = f"""
=== {self.coin_symbol} 잔고 정보 ===
최종 업데이트: {data['last_updated']}
원화 잔고: {data['balances']['KRW']:,.0f}원
{self.coin_symbol} 잔고: {data['balances'][self.coin_symbol]:.8f}
총 자산 가치: {data['performance']['total_value']:,.0f}원
총 수익/손실: {data['performance']['profit_loss']:,.0f}원 ({data['performance']['profit_rate']:.2f}%)

거래 통계:
- 총 거래 수: {data['trading_stats']['total_trades']}
- 승률: {data['trading_stats']['win_rate']:.1f}% ({data['trading_stats']['win_count']}/{data['trading_stats']['total_trades']})
- 총 거래 수익: {data['trading_stats']['total_profit']:,.0f}원
- 평균 거래당 수익: {data['trading_stats']['avg_profit_per_trade']:,.0f}원

포지션 상태: {'보유 중' if data['position']['is_holding'] else '없음'}
"""
        
        if data['position']['is_holding']:
            summary += f"""- 매수가: {data['position']['buy_price']:,.0f}원
- 매수량: {data['position']['buy_amount']:.8f}
- 매수 시간: {data['position']['buy_time']}
"""
        
        return summary
    
    def reset_balance(self, initial_krw: float = 10000000):
        """잔고 초기화"""
        try:
            # 백업 파일 생성
            if os.path.exists(self.balance_file):
                backup_file = f"{self.balance_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(self.balance_file, backup_file)
                logger.info(f"기존 잔고 파일 백업: {backup_file}")
            
            # 초기 잔고 설정
            initial_data = {
                "coin_symbol": self.coin_symbol,
                "last_updated": datetime.now().isoformat(),
                "balances": {
                    "KRW": initial_krw,
                    self.coin_symbol: 0.0
                },
                "performance": {
                    "total_value": initial_krw,
                    "profit_loss": 0.0,
                    "profit_rate": 0.0
                },
                "position": {
                    "is_holding": False,
                    "buy_price": 0,
                    "buy_amount": 0,
                    "buy_time": None,
                    "total_profit": 0,
                    "win_count": 0,
                    "loss_count": 0,
                    "total_trades": 0
                },
                "trading_stats": {
                    "total_trades": 0,
                    "win_count": 0,
                    "loss_count": 0,
                    "win_rate": 0.0,
                    "total_profit": 0.0,
                    "avg_profit_per_trade": 0.0
                }
            }
            
            with open(self.balance_file, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 잔고 초기화 완료: {initial_krw:,.0f}원")
            
        except Exception as e:
            logger.error(f"잔고 초기화 오류: {e}")