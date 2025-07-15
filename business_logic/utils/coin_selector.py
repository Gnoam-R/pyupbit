import os
from typing import Dict, Tuple


SUPPORTED_COINS = {
    "1": ("BTC", "비트코인"),
    "2": ("ETH", "이더리움"),
    "3": ("MASK", "마스크 네트워크"),
    "4": ("SOL", "솔라나"),
    "5": ("PEPE", "페페")
}

COIN_CONFIG = {
    "BTC": {"name": "비트코인", "min_order": 5000},
    "ETH": {"name": "이더리움", "min_order": 5000},
    "MASK": {"name": "마스크 네트워크", "min_order": 5000},
    "SOL": {"name": "솔라나", "min_order": 5000},
    "PEPE": {"name": "페페", "min_order": 5000}
}


def select_coin() -> str:
    """거래할 코인 선택"""
    # 환경 변수에서 선택된 코인 확인
    selected_coin = os.environ.get('SELECTED_COIN')
    if selected_coin and selected_coin in COIN_CONFIG:
        return selected_coin
    
    print("\n=== 거래할 코인을 선택하세요 ===")
    for key, (symbol, name) in SUPPORTED_COINS.items():
        print(f"{key}. {name} ({symbol})")
    
    while True:
        choice = input("\n번호를 선택하세요 (1-5): ").strip()
        if choice in SUPPORTED_COINS:
            return SUPPORTED_COINS[choice][0]
        else:
            print("올바른 번호를 입력하세요.")


def get_coin_info(coin_symbol: str) -> Dict:
    """코인 정보 조회"""
    return COIN_CONFIG.get(coin_symbol, {"name": coin_symbol, "min_order": 5000})


def get_coin_name(coin_symbol: str) -> str:
    """코인명 조회"""
    return get_coin_info(coin_symbol).get("name", coin_symbol)