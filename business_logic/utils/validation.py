import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def validate_coin_ticker(ticker: str) -> bool:
    """코인 티커 유효성 검사"""
    if not ticker:
        return False
    
    # KRW-{COIN} 형태인지 확인
    if not ticker.startswith("KRW-"):
        return False
    
    coin_symbol = ticker[4:]  # KRW- 제거
    
    # 코인 심볼이 유효한지 확인 (영문 대문자, 2-10자)
    if not coin_symbol.isalpha() or not coin_symbol.isupper():
        return False
    
    if len(coin_symbol) < 2 or len(coin_symbol) > 10:
        return False
    
    return True


def validate_trading_config(config: Dict[str, Any]) -> bool:
    """트레이딩 설정 유효성 검사"""
    required_fields = [
        'buy_ratio', 'sell_ratio', 'stop_loss', 'take_profit',
        'min_order_amount', 'trading_interval'
    ]
    
    for field in required_fields:
        if field not in config:
            logger.error(f"필수 설정 필드 누락: {field}")
            return False
    
    # 비율 검사 (0-1 사이)
    ratio_fields = ['buy_ratio', 'sell_ratio', 'stop_loss', 'take_profit']
    for field in ratio_fields:
        value = config[field]
        if not isinstance(value, (int, float)) or value <= 0 or value > 1:
            logger.error(f"잘못된 비율 값: {field} = {value}")
            return False
    
    # 양수 검사
    positive_fields = ['min_order_amount', 'trading_interval']
    for field in positive_fields:
        value = config[field]
        if not isinstance(value, (int, float)) or value <= 0:
            logger.error(f"잘못된 양수 값: {field} = {value}")
            return False
    
    return True


def validate_price_amount(price: float, amount: float) -> bool:
    """가격과 수량 유효성 검사"""
    if not isinstance(price, (int, float)) or price <= 0:
        logger.error(f"잘못된 가격: {price}")
        return False
    
    if not isinstance(amount, (int, float)) or amount <= 0:
        logger.error(f"잘못된 수량: {amount}")
        return False
    
    return True


def ensure_directory_exists(directory: str) -> bool:
    """디렉터리가 존재하지 않으면 생성"""
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"디렉터리 생성: {directory}")
        return True
    except Exception as e:
        logger.error(f"디렉터리 생성 실패: {directory}, 오류: {e}")
        return False


def validate_api_keys(access_key: str, secret_key: str) -> bool:
    """API 키 유효성 검사"""
    if not access_key or not secret_key:
        logger.error("API 키가 비어있습니다.")
        return False
    
    # 기본적인 형태 검사
    if len(access_key) < 10 or len(secret_key) < 10:
        logger.error("API 키가 너무 짧습니다.")
        return False
    
    return True