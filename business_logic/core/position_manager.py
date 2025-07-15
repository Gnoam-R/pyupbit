import datetime
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class PositionManager:
    """포지션 관리 클래스"""
    
    def __init__(self):
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
    
    def open_position(self, price: float, amount: float):
        """포지션 열기"""
        self.position.update({
            "is_holding": True,
            "buy_price": price,
            "buy_amount": amount,
            "buy_time": datetime.datetime.now()
        })
        logger.info(f"포지션 열기: 가격={price:,.0f}, 수량={amount:.8f}")
    
    def close_position(self, sell_price: float, sell_amount: float, reason: str = "signal"):
        """포지션 닫기"""
        if not self.position["is_holding"]:
            return
        
        profit = (sell_price - self.position["buy_price"]) * sell_amount
        profit_rate = (sell_price - self.position["buy_price"]) / self.position["buy_price"]
        
        # 통계 업데이트
        self.position["total_profit"] += profit
        self.position["total_trades"] += 1
        
        if profit > 0:
            self.position["win_count"] += 1
        else:
            self.position["loss_count"] += 1
        
        # 포지션 정리
        remaining_amount = self.position["buy_amount"] - sell_amount
        
        if remaining_amount <= 0.00000001:
            self.position.update({
                "is_holding": False,
                "buy_price": 0,
                "buy_amount": 0,
                "buy_time": None
            })
            logger.info(f"포지션 완전 정리 ({reason}): 수익={profit:,.0f}원 ({profit_rate:.2%})")
        else:
            self.position["buy_amount"] = remaining_amount
            logger.info(f"부분 매도 완료 ({reason}): 수익={profit:,.0f}원, 남은 수량={remaining_amount:.8f}")
    
    def check_stop_loss_take_profit(self, current_price: float, config: Dict) -> Optional[str]:
        """손절/익절 확인"""
        if not self.position["is_holding"]:
            return None
        
        buy_price = self.position["buy_price"]
        profit_rate = (current_price - buy_price) / buy_price
        
        if profit_rate <= -config["stop_loss"]:
            logger.info(f"손절 조건 충족: 수익률 {profit_rate:.2%}")
            return "stop_loss"
        elif profit_rate >= config["take_profit"]:
            logger.info(f"익절 조건 충족: 수익률 {profit_rate:.2%}")
            return "take_profit"
        
        return None
    
    def get_position_info(self) -> Dict:
        """포지션 정보 반환"""
        return self.position.copy()
    
    def get_statistics(self) -> Dict:
        """거래 통계 반환"""
        total_trades = self.position["total_trades"]
        win_rate = (self.position["win_count"] / max(1, total_trades)) * 100
        
        return {
            "total_trades": total_trades,
            "win_count": self.position["win_count"],
            "loss_count": self.position["loss_count"],
            "win_rate": win_rate,
            "total_profit": self.position["total_profit"],
            "avg_profit_per_trade": self.position["total_profit"] / max(1, total_trades)
        }