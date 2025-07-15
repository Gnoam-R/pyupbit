import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..core.market_data import MarketDataProvider
from ..core.position_manager import PositionManager
from ..core.technical_analysis import TechnicalAnalyzer
from ..utils.coin_selector import COIN_CONFIG
from .technical_strategy import TechnicalTradingStrategy

logger = logging.getLogger(__name__)


class MultiCoinTradingStrategy:
    """멀티 코인 트레이딩 전략"""
    
    def __init__(self, config: Dict, is_test_mode: bool = False):
        self.config = config
        self.is_test_mode = is_test_mode
        self.supported_coins = list(COIN_CONFIG.keys())
        
        # 각 코인별 전략 및 포지션 매니저 초기화
        self.coin_strategies = {}
        self.coin_position_managers = {}
        self.market_data_providers = {}
        
        for coin in self.supported_coins:
            self.market_data_providers[coin] = MarketDataProvider(coin)
            self.coin_strategies[coin] = TechnicalTradingStrategy(
                config, TechnicalAnalyzer(), is_test_mode
            )
            self.coin_position_managers[coin] = PositionManager()
        
        logger.info(f"멀티 코인 전략 초기화 완료 - 지원 코인: {', '.join(self.supported_coins)}")
    
    def get_market_data_for_coin(self, coin: str, interval: str = "minute5", count: int = 200) -> Optional[pd.DataFrame]:
        """특정 코인의 시장 데이터 조회"""
        if coin not in self.market_data_providers:
            logger.error(f"지원하지 않는 코인: {coin}")
            return None
        
        return self.market_data_providers[coin].get_ohlcv_data(interval, count)
    
    def get_current_price_for_coin(self, coin: str) -> Optional[float]:
        """특정 코인의 현재가 조회"""
        if coin not in self.market_data_providers:
            logger.error(f"지원하지 않는 코인: {coin}")
            return None
        
        return self.market_data_providers[coin].get_current_price()
    
    def analyze_coin_signals(self, coin: str) -> Dict:
        """특정 코인의 매매 신호 분석"""
        try:
            # 시장 데이터 조회
            df = self.get_market_data_for_coin(coin)
            if df is None or len(df) < 50:
                return {
                    "coin": coin,
                    "buy_signal": False,
                    "sell_signal": False,
                    "current_price": None,
                    "error": "시장 데이터 부족"
                }
            
            # 현재가 조회
            current_price = self.get_current_price_for_coin(coin)
            if current_price is None:
                return {
                    "coin": coin,
                    "buy_signal": False,
                    "sell_signal": False,
                    "current_price": None,
                    "error": "현재가 조회 실패"
                }
            
            # 기술적 지표 계산
            indicators = self.coin_strategies[coin].calculate_technical_indicators(df)
            if not indicators:
                return {
                    "coin": coin,
                    "buy_signal": False,
                    "sell_signal": False,
                    "current_price": current_price,
                    "error": "기술적 지표 계산 실패"
                }
            
            # 매매 신호 생성
            buy_signal = self.coin_strategies[coin].generate_buy_signal(df, indicators)
            sell_signal = self.coin_strategies[coin].generate_sell_signal(df, indicators)
            
            # 손절/익절 확인
            stop_action = self.coin_position_managers[coin].check_stop_loss_take_profit(current_price, self.config)
            
            return {
                "coin": coin,
                "buy_signal": buy_signal,
                "sell_signal": sell_signal,
                "current_price": current_price,
                "stop_action": stop_action,
                "indicators": indicators,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"{coin} 신호 분석 오류: {e}")
            return {
                "coin": coin,
                "buy_signal": False,
                "sell_signal": False,
                "current_price": None,
                "error": str(e)
            }
    
    def analyze_all_coins(self) -> Dict[str, Dict]:
        """모든 코인의 매매 신호 분석 (병렬 처리)"""
        results = {}
        
        # 병렬 처리로 모든 코인 분석
        with ThreadPoolExecutor(max_workers=len(self.supported_coins)) as executor:
            # 각 코인별로 분석 작업 제출
            future_to_coin = {
                executor.submit(self.analyze_coin_signals, coin): coin 
                for coin in self.supported_coins
            }
            
            # 결과 수집
            for future in as_completed(future_to_coin):
                coin = future_to_coin[future]
                try:
                    result = future.result()
                    results[coin] = result
                except Exception as e:
                    logger.error(f"{coin} 분석 중 오류: {e}")
                    results[coin] = {
                        "coin": coin,
                        "buy_signal": False,
                        "sell_signal": False,
                        "current_price": None,
                        "error": str(e)
                    }
        
        return results
    
    def get_trading_opportunities(self) -> Tuple[List[Dict], List[Dict]]:
        """매수/매도 기회 분석"""
        analysis_results = self.analyze_all_coins()
        
        buy_opportunities = []
        sell_opportunities = []
        
        for coin, result in analysis_results.items():
            if result["error"]:
                continue
            
            position_info = self.coin_position_managers[coin].get_position_info()
            
            # 손절/익절 우선 처리
            if result["stop_action"]:
                if position_info["is_holding"]:
                    sell_opportunities.append({
                        "coin": coin,
                        "reason": result["stop_action"],
                        "current_price": result["current_price"],
                        "priority": "high"
                    })
                continue
            
            # 매수 신호 처리
            if result["buy_signal"] and not position_info["is_holding"]:
                buy_opportunities.append({
                    "coin": coin,
                    "reason": "signal",
                    "current_price": result["current_price"],
                    "priority": "normal"
                })
            
            # 매도 신호 처리
            if result["sell_signal"] and position_info["is_holding"]:
                sell_opportunities.append({
                    "coin": coin,
                    "reason": "signal",
                    "current_price": result["current_price"],
                    "priority": "normal"
                })
        
        # 우선순위별 정렬 (high > normal)
        buy_opportunities.sort(key=lambda x: x["priority"], reverse=True)
        sell_opportunities.sort(key=lambda x: x["priority"], reverse=True)
        
        return buy_opportunities, sell_opportunities
    
    def get_position_manager_for_coin(self, coin: str) -> Optional[PositionManager]:
        """특정 코인의 포지션 매니저 반환"""
        return self.coin_position_managers.get(coin)
    
    def get_all_position_managers(self) -> Dict[str, PositionManager]:
        """모든 코인의 포지션 매니저 반환"""
        return self.coin_position_managers.copy()
    
    def get_portfolio_summary(self) -> Dict:
        """포트폴리오 요약 정보"""
        summary = {
            "total_trades": 0,
            "total_profit": 0,
            "win_count": 0,
            "loss_count": 0,
            "active_positions": 0,
            "coin_details": {}
        }
        
        for coin, position_manager in self.coin_position_managers.items():
            stats = position_manager.get_statistics()
            position_info = position_manager.get_position_info()
            
            summary["total_trades"] += stats["total_trades"]
            summary["total_profit"] += stats["total_profit"]
            summary["win_count"] += stats["win_count"]
            summary["loss_count"] += stats["loss_count"]
            
            if position_info["is_holding"]:
                summary["active_positions"] += 1
            
            summary["coin_details"][coin] = {
                "position": position_info,
                "statistics": stats,
                "current_price": self.get_current_price_for_coin(coin)
            }
        
        # 전체 승률 계산
        if summary["total_trades"] > 0:
            summary["win_rate"] = (summary["win_count"] / summary["total_trades"]) * 100
        else:
            summary["win_rate"] = 0
        
        return summary