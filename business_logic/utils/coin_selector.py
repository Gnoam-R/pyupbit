import os
from typing import Dict, Tuple, List


SUPPORTED_COINS = {
    "1": ("BTC", "비트코인"),
    "2": ("ETH", "이더리움"),
    "3": ("XRP", "리플"),
    "4": ("ADA", "에이다"),
    "5": ("SOL", "솔라나"),
    "6": ("DOGE", "도지코인"),
    "7": ("MATIC", "폴리곤"),
    "8": ("AVAX", "아발란체"),
    "9": ("SHIB", "시바이누"),
    "10": ("DOT", "폴카닷")
}

COIN_CONFIG = {
    "BTC": {"name": "비트코인", "min_order": 5000, "min_amount": 0.00001},
    "ETH": {"name": "이더리움", "min_order": 5000, "min_amount": 0.001},
    "XRP": {"name": "리플", "min_order": 5000, "min_amount": 1},
    "ADA": {"name": "에이다", "min_order": 5000, "min_amount": 1},
    "SOL": {"name": "솔라나", "min_order": 5000, "min_amount": 0.01},
    "DOGE": {"name": "도지코인", "min_order": 5000, "min_amount": 1},
    "MATIC": {"name": "폴리곤", "min_order": 5000, "min_amount": 1},
    "AVAX": {"name": "아발란체", "min_order": 5000, "min_amount": 0.1},
    "SHIB": {"name": "시바이누", "min_order": 5000, "min_amount": 100000},
    "DOT": {"name": "폴카닷", "min_order": 5000, "min_amount": 0.1}
}


def select_coin() -> str:
    """단일 코인 선택 (기존 호환성 유지)"""
    coins = select_coins(multi=False)
    return coins[0] if coins else "BTC"


def select_coins(multi: bool = True) -> List[str]:
    """
    거래할 코인 선택
    
    Args:
        multi: True면 다중 선택 가능, False면 단일 선택
    
    Returns:
        선택된 코인 심볼 리스트
    """
    # 환경 변수에서 선택된 코인 확인
    selected_coin = os.environ.get('SELECTED_COIN')
    if selected_coin and selected_coin in COIN_CONFIG:
        return [selected_coin]
    
    if multi:
        print("\n=== 거래할 코인을 선택하세요 (다중 선택 가능) ===")
        for key, (symbol, name) in SUPPORTED_COINS.items():
            print(f"{key}. {name} ({symbol})")
        print("예시: '1,2,3' 또는 '1 2 3' 또는 '1-3' (1번부터 3번까지)")
        
        while True:
            choice = input("\n번호를 선택하세요 (쉼표, 공백, 또는 하이픈으로 구분): ").strip()
            
            try:
                selected_coins = parse_coin_selection(choice)
                if selected_coins:
                    coin_names = [f"{SUPPORTED_COINS[str(i)][1]}({SUPPORTED_COINS[str(i)][0]})" for i in selected_coins]
                    print(f"선택된 코인: {', '.join(coin_names)}")
                    
                    confirm = input("이 코인들로 거래하시겠습니까? (y/n): ").strip().lower()
                    if confirm in ['y', 'yes', '예']:
                        return [SUPPORTED_COINS[str(i)][0] for i in selected_coins]
                    else:
                        continue
                else:
                    print("올바른 번호를 입력하세요.")
            except Exception as e:
                print(f"입력 오류: {e}")
    else:
        # 단일 선택
        print("\n=== 거래할 코인을 선택하세요 ===")
        for key, (symbol, name) in SUPPORTED_COINS.items():
            print(f"{key}. {name} ({symbol})")
        
        while True:
            choice = input("\n번호를 선택하세요 (1-10): ").strip()
            if choice in SUPPORTED_COINS:
                return [SUPPORTED_COINS[choice][0]]
            else:
                print("올바른 번호를 입력하세요.")


def parse_coin_selection(choice: str) -> List[int]:
    """코인 선택 문자열 파싱"""
    selected = []
    
    # 쉼표 또는 공백으로 분리
    if ',' in choice:
        parts = choice.split(',')
    else:
        parts = choice.split()
    
    for part in parts:
        part = part.strip()
        if '-' in part:
            # 범위 선택 (예: 1-3)
            try:
                start, end = map(int, part.split('-'))
                for i in range(start, end + 1):
                    if str(i) in SUPPORTED_COINS:
                        selected.append(i)
            except ValueError:
                raise ValueError(f"잘못된 범위 형식: {part}")
        else:
            # 단일 선택
            if part in SUPPORTED_COINS:
                selected.append(int(part))
            else:
                raise ValueError(f"잘못된 번호: {part}")
    
    return list(set(selected))  # 중복 제거


def get_coin_info(coin_symbol: str) -> Dict:
    """코인 정보 조회"""
    return COIN_CONFIG.get(coin_symbol, {"name": coin_symbol, "min_order": 5000, "min_amount": 0.01})


def get_coin_name(coin_symbol: str) -> str:
    """코인명 조회"""
    return get_coin_info(coin_symbol).get("name", coin_symbol)


def get_all_coin_names(coin_symbols: List[str]) -> str:
    """여러 코인명을 하나의 문자열로 결합"""
    names = [get_coin_name(symbol) for symbol in coin_symbols]
    return ", ".join(names)