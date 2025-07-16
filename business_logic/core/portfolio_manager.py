import logging
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CoinInfo:
    """코인 정보"""
    symbol: str
    name: str
    current_price: float
    volume_24h: float
    change_24h: float
    market_cap: float
    min_order_amount: float = 5000


@dataclass
class PortfolioPosition:
    """포트폴리오 포지션"""
    coin_symbol: str
    amount: float
    avg_buy_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    last_updated: datetime


class PortfolioManager:
    """멀티 코인 포트폴리오 관리자"""
    
    def __init__(self, initial_balance: float = 1000000):
        self.initial_balance = initial_balance
        self.cash_balance = initial_balance
        self.positions: Dict[str, PortfolioPosition] = {}
        self.total_trades = 0
        self.total_realized_pnl = 0
        self.lock = threading.Lock()
        
        # 거래 가능한 코인 목록 (상위 10개)
        self.available_coins = [
            "BTC", "ETH", "BNB", "SOL", "ADA", 
            "DOGE", "MATIC", "DOT", "AVAX", "SHIB"
        ]
        
        # 포트폴리오 설정
        self.max_positions = 5  # 최대 5개 코인 동시 보유
        self.max_position_size = 0.3  # 단일 코인 최대 30% 비중
        self.min_position_size = 0.05  # 단일 코인 최소 5% 비중
        
        logger.info(f"포트폴리오 매니저 초기화: 초기 잔고 {initial_balance:,.0f}원")
    
    def get_available_coins(self) -> List[str]:
        """거래 가능한 코인 목록 반환"""
        return self.available_coins.copy()
    
    def get_cash_balance(self) -> float:
        """현금 잔고 반환"""
        with self.lock:
            return self.cash_balance
    
    def get_total_portfolio_value(self, coin_prices: Dict[str, float]) -> float:
        """총 포트폴리오 가치 계산"""
        with self.lock:
            total_value = self.cash_balance
            
            for symbol, position in self.positions.items():
                if symbol in coin_prices:
                    position_value = position.amount * coin_prices[symbol]
                    total_value += position_value
                    
            return total_value
    
    def get_position_weights(self, coin_prices: Dict[str, float]) -> Dict[str, float]:
        """각 코인의 포트폴리오 비중 계산"""
        total_value = self.get_total_portfolio_value(coin_prices)
        weights = {}
        
        with self.lock:
            for symbol, position in self.positions.items():
                if symbol in coin_prices:
                    position_value = position.amount * coin_prices[symbol]
                    weights[symbol] = position_value / total_value if total_value > 0 else 0
                    
        return weights
    
    def can_buy_coin(self, coin_symbol: str, buy_amount: float, current_price: float) -> bool:
        """코인 매수 가능 여부 확인"""
        with self.lock:
            # 현금 잔고 확인
            if self.cash_balance < buy_amount:
                logger.warning(f"현금 잔고 부족: 필요 {buy_amount:,.0f}원, 보유 {self.cash_balance:,.0f}원")
                return False
            
            # 최대 포지션 수 확인
            if coin_symbol not in self.positions and len(self.positions) >= self.max_positions:
                logger.warning(f"최대 포지션 수 초과: 현재 {len(self.positions)}/{self.max_positions}")
                return False
            
            # 포지션 크기 제한 확인
            coin_amount = buy_amount / current_price
            if coin_symbol in self.positions:
                total_amount = self.positions[coin_symbol].amount + coin_amount
            else:
                total_amount = coin_amount
            
            total_portfolio_value = self.get_total_portfolio_value({coin_symbol: current_price})
            position_value = total_amount * current_price
            position_weight = position_value / total_portfolio_value if total_portfolio_value > 0 else 0
            
            if position_weight > self.max_position_size:
                logger.warning(f"포지션 크기 초과: {coin_symbol} {position_weight:.1%} > {self.max_position_size:.1%}")
                return False
            
            return True
    
    def buy_coin(self, coin_symbol: str, amount: float, price: float) -> bool:
        """코인 매수"""
        buy_value = amount * price
        
        if not self.can_buy_coin(coin_symbol, buy_value, price):
            return False
        
        with self.lock:
            self.cash_balance -= buy_value
            
            if coin_symbol in self.positions:
                # 기존 포지션 평균 단가 계산
                existing_position = self.positions[coin_symbol]
                total_amount = existing_position.amount + amount
                total_value = (existing_position.amount * existing_position.avg_buy_price) + buy_value
                avg_price = total_value / total_amount
                
                self.positions[coin_symbol] = PortfolioPosition(
                    coin_symbol=coin_symbol,
                    amount=total_amount,
                    avg_buy_price=avg_price,
                    current_price=price,
                    unrealized_pnl=0,
                    realized_pnl=existing_position.realized_pnl,
                    last_updated=datetime.now()
                )
            else:
                # 새 포지션 생성
                self.positions[coin_symbol] = PortfolioPosition(
                    coin_symbol=coin_symbol,
                    amount=amount,
                    avg_buy_price=price,
                    current_price=price,
                    unrealized_pnl=0,
                    realized_pnl=0,
                    last_updated=datetime.now()
                )
            
            self.total_trades += 1
            logger.info(f"매수 완료: {coin_symbol} {amount:.8f}개 @ {price:,.0f}원 (총 {buy_value:,.0f}원)")
            return True
    
    def sell_coin(self, coin_symbol: str, amount: float, price: float) -> bool:
        """코인 매도"""
        if coin_symbol not in self.positions:
            logger.warning(f"매도 불가: {coin_symbol} 포지션 없음")
            return False
        
        with self.lock:
            position = self.positions[coin_symbol]
            
            if position.amount < amount:
                logger.warning(f"매도 불가: 보유량 부족 {position.amount:.8f} < {amount:.8f}")
                return False
            
            sell_value = amount * price
            self.cash_balance += sell_value
            
            # 실현 손익 계산
            realized_pnl = (price - position.avg_buy_price) * amount
            
            # 포지션 업데이트
            remaining_amount = position.amount - amount
            if remaining_amount > 0.00000001:  # 소량 남은 경우
                self.positions[coin_symbol] = PortfolioPosition(
                    coin_symbol=coin_symbol,
                    amount=remaining_amount,
                    avg_buy_price=position.avg_buy_price,
                    current_price=price,
                    unrealized_pnl=0,
                    realized_pnl=position.realized_pnl + realized_pnl,
                    last_updated=datetime.now()
                )
            else:
                # 포지션 완전 정리
                self.total_realized_pnl += position.realized_pnl + realized_pnl
                del self.positions[coin_symbol]
            
            self.total_trades += 1
            logger.info(f"매도 완료: {coin_symbol} {amount:.8f}개 @ {price:,.0f}원 (총 {sell_value:,.0f}원, 손익 {realized_pnl:,.0f}원)")
            return True
    
    def update_positions(self, coin_prices: Dict[str, float]):
        """포지션 정보 업데이트"""
        with self.lock:
            for symbol, position in self.positions.items():
                if symbol in coin_prices:
                    current_price = coin_prices[symbol]
                    position.current_price = current_price
                    position.unrealized_pnl = (current_price - position.avg_buy_price) * position.amount
                    position.last_updated = datetime.now()
    
    def get_portfolio_summary(self, coin_prices: Dict[str, float]) -> Dict:
        """포트폴리오 요약 정보"""
        total_value = self.get_total_portfolio_value(coin_prices)
        total_pnl = self.total_realized_pnl
        
        # 미실현 손익 합계
        unrealized_pnl = 0
        for position in self.positions.values():
            unrealized_pnl += position.unrealized_pnl
        
        total_pnl += unrealized_pnl
        
        return {
            "initial_balance": self.initial_balance,
            "cash_balance": self.cash_balance,
            "total_value": total_value,
            "total_pnl": total_pnl,
            "total_return": (total_pnl / self.initial_balance) * 100,
            "realized_pnl": self.total_realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "total_trades": self.total_trades,
            "positions_count": len(self.positions),
            "positions": {symbol: {
                "amount": pos.amount,
                "avg_buy_price": pos.avg_buy_price,
                "current_price": pos.current_price,
                "unrealized_pnl": pos.unrealized_pnl,
                "weight": (pos.amount * pos.current_price) / total_value * 100 if total_value > 0 else 0
            } for symbol, pos in self.positions.items()}
        }
    
    def get_diversification_score(self, coin_prices: Dict[str, float]) -> float:
        """포트폴리오 다양성 점수 (0-1, 1이 가장 다양함)"""
        weights = self.get_position_weights(coin_prices)
        if not weights:
            return 0
        
        # 허핀달 지수 계산 (집중도)
        herfindahl_index = sum(w ** 2 for w in weights.values())
        
        # 다양성 점수 (1 - 허핀달 지수)
        diversification_score = 1 - herfindahl_index
        return diversification_score
    
    def should_rebalance(self, coin_prices: Dict[str, float]) -> bool:
        """리밸런싱 필요 여부 판단"""
        weights = self.get_position_weights(coin_prices)
        
        for symbol, weight in weights.items():
            if weight > self.max_position_size * 1.2:  # 20% 초과 시 리밸런싱
                return True
            if weight < self.min_position_size * 0.8:  # 20% 미만 시 리밸런싱
                return True
        
        return False