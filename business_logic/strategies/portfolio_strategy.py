import logging
from typing import Dict, List, Optional, Tuple
import pandas as pd
from datetime import datetime
from ..core.portfolio_manager import PortfolioManager
from ..core.coin_analyzer import CoinAnalyzer, CoinMetrics
from ..core.multi_market_data import MultiMarketDataProvider
from ..core.technical_analysis import TechnicalAnalyzer

logger = logging.getLogger(__name__)


class PortfolioTradingStrategy:
    """포트폴리오 기반 멀티 코인 트레이딩 전략"""
    
    def __init__(self, config: Dict, initial_balance: float = 1000000):
        self.config = config
        self.portfolio_manager = PortfolioManager(initial_balance)
        self.technical_analyzer = TechnicalAnalyzer()
        
        # 지원 코인 목록
        self.supported_coins = self.portfolio_manager.get_available_coins()
        
        # 멀티 마켓 데이터 제공자 초기화
        self.market_data = MultiMarketDataProvider(self.supported_coins)
        
        # 코인 분석기 초기화
        self.coin_analyzer = CoinAnalyzer(self.market_data, self.technical_analyzer)
        
        # 전략 설정
        self.max_positions = config.get('max_positions', 5)
        self.position_size = config.get('position_size', 0.2)  # 포지션당 20%
        self.min_score_for_buy = config.get('min_score_for_buy', 70)
        self.min_score_for_sell = config.get('min_score_for_sell', 40)
        
        # 리스크 관리
        self.stop_loss = config.get('stop_loss', 0.05)  # 5% 손절
        self.take_profit = config.get('take_profit', 0.15)  # 15% 익절
        self.max_daily_loss = config.get('max_daily_loss', 0.03)  # 일일 최대 손실 3%
        
        # 분석 간격
        self.analysis_interval = config.get('analysis_interval', 300)  # 5분
        self.last_analysis_time = datetime.now()
        
        logger.info(f"포트폴리오 전략 초기화 완료 - 지원 코인: {len(self.supported_coins)}개")
    
    def should_analyze_market(self) -> bool:
        """시장 분석 실행 여부 판단"""
        now = datetime.now()
        elapsed = (now - self.last_analysis_time).total_seconds()
        return elapsed >= self.analysis_interval
    
    def analyze_market_opportunities(self) -> Dict:
        """시장 기회 분석"""
        if not self.should_analyze_market():
            return {"action": "wait", "reason": "분석 간격 대기 중"}
        
        try:
            # 모든 코인 분석
            coin_metrics = self.coin_analyzer.analyze_multiple_coins(self.supported_coins)
            
            if not coin_metrics:
                return {"action": "wait", "reason": "분석 데이터 없음"}
            
            # 현재 포지션 확인
            current_positions = list(self.portfolio_manager.positions.keys())
            
            # 현재 가격 정보
            current_prices = self.market_data.get_all_current_prices()
            
            # 포트폴리오 업데이트
            self.portfolio_manager.update_positions(current_prices)
            
            # 매수/매도 후보 선정
            buy_candidates = self.coin_analyzer.get_best_buy_candidates(
                coin_metrics, current_positions, max_candidates=3
            )
            sell_candidates = self.coin_analyzer.get_sell_candidates(
                coin_metrics, current_positions
            )
            
            # 포트폴리오 요약
            portfolio_summary = self.portfolio_manager.get_portfolio_summary(current_prices)
            
            # 리스크 체크
            risk_analysis = self._analyze_risk(portfolio_summary)
            
            # 시장 요약
            market_summary = self._get_market_summary(coin_metrics, current_prices)
            
            self.last_analysis_time = datetime.now()
            
            return {
                "action": "analyzed",
                "coin_metrics": coin_metrics,
                "buy_candidates": buy_candidates,
                "sell_candidates": sell_candidates,
                "portfolio_summary": portfolio_summary,
                "risk_analysis": risk_analysis,
                "current_prices": current_prices,
                "market_summary": market_summary
            }
            
        except Exception as e:
            logger.error(f"시장 분석 오류: {e}")
            return {"action": "error", "reason": str(e)}
    
    def generate_trading_signals(self, analysis_result: Dict) -> List[Dict]:
        """거래 신호 생성"""
        if analysis_result["action"] != "analyzed":
            return []
        
        signals = []
        
        # 리스크 체크
        risk_analysis = analysis_result["risk_analysis"]
        if risk_analysis["emergency_stop"]:
            return [{"action": "emergency_stop", "reason": risk_analysis["reason"]}]
        
        # 매도 신호 우선 처리
        sell_candidates = analysis_result["sell_candidates"]
        for coin in sell_candidates:
            if self._should_sell_coin(coin, analysis_result):
                signals.append({
                    "action": "sell",
                    "coin": coin.symbol,
                    "reason": f"기술적 신호 (점수: {coin.overall_score:.1f})",
                    "urgency": "high" if coin.overall_score < 30 else "medium",
                    "price": coin.current_price
                })
        
        # 매수 신호 처리
        if not risk_analysis["stop_buying"]:
            buy_candidates = analysis_result["buy_candidates"]
            for coin in buy_candidates:
                if self._should_buy_coin(coin, analysis_result):
                    signals.append({
                        "action": "buy",
                        "coin": coin.symbol,
                        "reason": f"기술적 신호 (점수: {coin.overall_score:.1f})",
                        "urgency": "high" if coin.overall_score > 85 else "medium",
                        "price": coin.current_price
                    })
        
        # 리밸런싱 신호
        if self._should_rebalance(analysis_result):
            signals.append({
                "action": "rebalance",
                "reason": "포트폴리오 불균형",
                "urgency": "low"
            })
        
        return signals
    
    def execute_trading_signal(self, signal: Dict) -> Dict:
        """거래 신호 실행"""
        try:
            if signal["action"] == "buy":
                return self._execute_buy_signal(signal)
            elif signal["action"] == "sell":
                return self._execute_sell_signal(signal)
            elif signal["action"] == "rebalance":
                return self._execute_rebalance_signal()
            elif signal["action"] == "emergency_stop":
                return self._execute_emergency_stop()
            else:
                return {"success": False, "reason": "알 수 없는 신호"}
        except Exception as e:
            logger.error(f"거래 신호 실행 오류: {e}")
            return {"success": False, "reason": str(e)}
    
    def _should_buy_coin(self, coin: CoinMetrics, analysis_result: Dict) -> bool:
        """매수 조건 확인"""
        # 기본 점수 체크
        if coin.overall_score < self.min_score_for_buy:
            return False
        
        # 현재 포지션 수 체크
        current_positions = len(self.portfolio_manager.positions)
        if current_positions >= self.max_positions:
            return False
        
        # 시장 건강도 체크
        market_health = analysis_result["market_summary"]["health_score"]
        if market_health < 40:
            return False
        
        # 중복 매수 방지
        if coin.symbol in self.portfolio_manager.positions:
            return False
        
        return True
    
    def _should_sell_coin(self, coin: CoinMetrics, analysis_result: Dict) -> bool:
        """매도 조건 확인"""
        # 기본 점수 체크
        if coin.overall_score <= self.min_score_for_sell:
            return True
        
        # 기술적 매도 신호
        if coin.rsi > 80 and coin.bb_position == 'overbought':
            return True
        
        # 손절/익절 체크
        if coin.symbol in self.portfolio_manager.positions:
            position = self.portfolio_manager.positions[coin.symbol]
            pnl_rate = (coin.current_price - position.avg_buy_price) / position.avg_buy_price
            
            if pnl_rate <= -self.stop_loss:  # 손절
                return True
            if pnl_rate >= self.take_profit:  # 익절
                return True
        
        return False
    
    def _should_rebalance(self, analysis_result: Dict) -> bool:
        """리밸런싱 필요 여부"""
        portfolio_summary = analysis_result["portfolio_summary"]
        
        # 포지션 비중 체크
        for position_info in portfolio_summary["positions"].values():
            if position_info["weight"] > 40:  # 40% 초과 시 리밸런싱
                return True
        
        return False
    
    def _execute_buy_signal(self, signal: Dict) -> Dict:
        """매수 신호 실행"""
        coin_symbol = signal["coin"]
        current_price = signal["price"]
        
        # 매수 금액 계산
        cash_balance = self.portfolio_manager.get_cash_balance()
        buy_amount = min(cash_balance * self.position_size, cash_balance * 0.95)
        
        if buy_amount < 5000:  # 최소 주문 금액
            return {"success": False, "reason": "매수 금액 부족"}
        
        # 매수 수량 계산
        buy_quantity = buy_amount / current_price
        
        # 매수 실행
        success = self.portfolio_manager.buy_coin(coin_symbol, buy_quantity, current_price)
        
        if success:
            return {
                "success": True,
                "action": "buy",
                "coin": coin_symbol,
                "quantity": buy_quantity,
                "price": current_price,
                "amount": buy_amount
            }
        else:
            return {"success": False, "reason": "매수 실행 실패"}
    
    def _execute_sell_signal(self, signal: Dict) -> Dict:
        """매도 신호 실행"""
        coin_symbol = signal["coin"]
        current_price = signal["price"]
        
        if coin_symbol not in self.portfolio_manager.positions:
            return {"success": False, "reason": "보유 포지션 없음"}
        
        position = self.portfolio_manager.positions[coin_symbol]
        
        # 매도 수량 결정
        sell_quantity = position.amount
        if signal["urgency"] == "medium":
            sell_quantity = position.amount * 0.5  # 부분 매도
        
        # 매도 실행
        success = self.portfolio_manager.sell_coin(coin_symbol, sell_quantity, current_price)
        
        if success:
            sell_amount = sell_quantity * current_price
            return {
                "success": True,
                "action": "sell",
                "coin": coin_symbol,
                "quantity": sell_quantity,
                "price": current_price,
                "amount": sell_amount
            }
        else:
            return {"success": False, "reason": "매도 실행 실패"}
    
    def _execute_rebalance_signal(self) -> Dict:
        """리밸런싱 신호 실행"""
        current_prices = self.market_data.get_all_current_prices()
        portfolio_summary = self.portfolio_manager.get_portfolio_summary(current_prices)
        
        rebalance_actions = []
        
        # 비중이 높은 포지션 부분 매도
        for coin_symbol, position_info in portfolio_summary["positions"].items():
            if position_info["weight"] > 35:  # 35% 초과 시 부분 매도
                if coin_symbol in current_prices:
                    position = self.portfolio_manager.positions[coin_symbol]
                    sell_quantity = position.amount * 0.3  # 30% 매도
                    current_price = current_prices[coin_symbol]
                    
                    success = self.portfolio_manager.sell_coin(coin_symbol, sell_quantity, current_price)
                    if success:
                        rebalance_actions.append({
                            "action": "sell",
                            "coin": coin_symbol,
                            "quantity": sell_quantity,
                            "reason": "리밸런싱"
                        })
        
        return {
            "success": True,
            "action": "rebalance",
            "actions": rebalance_actions
        }
    
    def _execute_emergency_stop(self) -> Dict:
        """비상 정지 실행"""
        logger.warning("비상 정지 실행: 모든 포지션 매도")
        
        current_prices = self.market_data.get_all_current_prices()
        emergency_actions = []
        
        # 모든 포지션 매도
        for coin_symbol, position in list(self.portfolio_manager.positions.items()):
            if coin_symbol in current_prices:
                current_price = current_prices[coin_symbol]
                success = self.portfolio_manager.sell_coin(coin_symbol, position.amount, current_price)
                if success:
                    emergency_actions.append({
                        "action": "sell",
                        "coin": coin_symbol,
                        "quantity": position.amount,
                        "reason": "비상 정지"
                    })
        
        return {
            "success": True,
            "action": "emergency_stop",
            "actions": emergency_actions
        }
    
    def _analyze_risk(self, portfolio_summary: Dict) -> Dict:
        """리스크 분석"""
        total_return = portfolio_summary["total_return"]
        unrealized_pnl = portfolio_summary["unrealized_pnl"]
        
        # 일일 최대 손실 체크
        emergency_stop = total_return <= -self.max_daily_loss * 100
        
        # 매수 중단 조건
        stop_buying = (
            total_return <= -2 or  # 2% 이상 손실
            unrealized_pnl <= -portfolio_summary["initial_balance"] * 0.02
        )
        
        return {
            "emergency_stop": emergency_stop,
            "stop_buying": stop_buying,
            "total_return": total_return,
            "risk_level": "high" if emergency_stop else "medium" if stop_buying else "low",
            "reason": "일일 최대 손실 초과" if emergency_stop else "손실 확대 방지" if stop_buying else "정상"
        }
    
    def _get_market_summary(self, coin_metrics: List[CoinMetrics], current_prices: Dict[str, float]) -> Dict:
        """시장 요약 정보"""
        if not coin_metrics:
            return {"health_score": 50, "top_coins": [], "market_trend": "neutral"}
        
        # 상위 코인 (점수 기준)
        top_coins = sorted(coin_metrics, key=lambda x: x.overall_score, reverse=True)[:3]
        
        # 시장 건강도 계산
        avg_score = sum(coin.overall_score for coin in coin_metrics) / len(coin_metrics)
        health_score = min(100, max(0, avg_score))
        
        # 시장 트렌드
        bullish_count = sum(1 for coin in coin_metrics if coin.overall_score > 70)
        bearish_count = sum(1 for coin in coin_metrics if coin.overall_score < 40)
        
        if bullish_count > bearish_count:
            market_trend = "bullish"
        elif bearish_count > bullish_count:
            market_trend = "bearish"
        else:
            market_trend = "neutral"
        
        return {
            "health_score": health_score,
            "top_coins": [{"symbol": coin.symbol, "score": coin.overall_score} for coin in top_coins],
            "market_trend": market_trend,
            "bullish_count": bullish_count,
            "bearish_count": bearish_count
        }
    
    def get_portfolio_status(self) -> Dict:
        """포트폴리오 상태 정보"""
        current_prices = self.market_data.get_all_current_prices()
        portfolio_summary = self.portfolio_manager.get_portfolio_summary(current_prices)
        
        return {
            "portfolio_summary": portfolio_summary,
            "current_prices": current_prices,
            "supported_coins": self.supported_coins,
            "strategy_config": {
                "max_positions": self.max_positions,
                "position_size": self.position_size,
                "stop_loss": self.stop_loss,
                "take_profit": self.take_profit
            }
        }
    
    def print_portfolio_status(self):
        """포트폴리오 상태 출력"""
        try:
            status = self.get_portfolio_status()
            portfolio = status["portfolio_summary"]
            
            print("\n" + "=" * 80)
            print("포트폴리오 상태")
            print("=" * 80)
            print(f"초기 잔고: {portfolio['initial_balance']:,.0f}원")
            print(f"현금 잔고: {portfolio['cash_balance']:,.0f}원")
            print(f"총 자산: {portfolio['total_value']:,.0f}원")
            print(f"총 수익: {portfolio['total_pnl']:,.0f}원 ({portfolio['total_return']:.2f}%)")
            print(f"실현 수익: {portfolio['realized_pnl']:,.0f}원")
            print(f"미실현 수익: {portfolio['unrealized_pnl']:,.0f}원")
            print(f"총 거래 수: {portfolio['total_trades']}")
            print(f"보유 포지션: {portfolio['positions_count']}/{self.max_positions}")
            
            if portfolio['positions']:
                print("\n보유 포지션:")
                for symbol, pos in portfolio['positions'].items():
                    print(f"  {symbol}: {pos['amount']:.8f}개 @ {pos['avg_buy_price']:,.0f}원 "
                          f"(현재가: {pos['current_price']:,.0f}원, 수익: {pos['unrealized_pnl']:,.0f}원, "
                          f"비중: {pos['weight']:.1f}%)")
            
            print("=" * 80)
            
        except Exception as e:
            logger.error(f"포트폴리오 상태 출력 오류: {e}")
    
    def get_trading_opportunities_summary(self) -> str:
        """거래 기회 요약"""
        analysis_result = self.analyze_market_opportunities()
        
        if analysis_result["action"] != "analyzed":
            return f"분석 불가: {analysis_result.get('reason', '알 수 없음')}"
        
        buy_candidates = analysis_result["buy_candidates"]
        sell_candidates = analysis_result["sell_candidates"]
        market_summary = analysis_result["market_summary"]
        
        summary = f"""
시장 상황: {market_summary['market_trend']} (건강도: {market_summary['health_score']:.1f})
상위 코인: {', '.join([f"{coin['symbol']}({coin['score']:.1f})" for coin in market_summary['top_coins']])}
매수 후보: {len(buy_candidates)}개 ({', '.join([coin.symbol for coin in buy_candidates])})
매도 후보: {len(sell_candidates)}개 ({', '.join([coin.symbol for coin in sell_candidates])})
"""
        return summary.strip()