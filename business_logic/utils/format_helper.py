"""포맷팅 헬퍼 함수들"""

def format_percentage(value: float, precision: int = 2) -> str:
    """
    퍼센트 값을 올바르게 포맷팅
    -0.00% 같은 이상한 표시를 방지
    """
    if abs(value) < 0.01:  # 0.01% 미만은 0.00%로 표시
        return "0.00%"
    
    return f"{value:.{precision}f}%"


def format_profit_rate(profit_rate: float, precision: int = 2) -> str:
    """
    수익률을 올바르게 포맷팅
    """
    percentage = profit_rate * 100
    return format_percentage(percentage, precision)


def format_currency(amount: float, currency: str = "원") -> str:
    """
    통화 값을 포맷팅
    """
    if abs(amount) < 1:
        return f"{amount:.2f}{currency}"
    else:
        return f"{amount:,.0f}{currency}"


def format_coin_amount(amount: float, precision: int = 8) -> str:
    """
    코인 수량을 포맷팅
    """
    if amount == 0:
        return "0"
    
    # 소수점 이하 0이 아닌 첫 번째 자리까지 표시
    if amount < 0.00000001:
        return f"{amount:.12f}"
    elif amount < 0.0001:
        return f"{amount:.8f}"
    elif amount < 1:
        return f"{amount:.6f}"
    else:
        return f"{amount:.4f}"


def format_statistics_log(stats: dict, current_profit_rate: float = None) -> str:
    """
    통계 정보를 로그용으로 포맷팅
    """
    lines = []
    lines.append(f"📊 거래 통계")
    lines.append(f"   총 거래: {stats['total_trades']}회")
    
    if stats['total_trades'] > 0:
        lines.append(f"   승률: {format_percentage(stats['win_rate'])} ({stats['win_count']}/{stats['total_trades']})")
        lines.append(f"   누적 수익: {format_currency(stats['total_profit'])}")
        lines.append(f"   평균 거래당 수익: {format_currency(stats['avg_profit_per_trade'])}")
    
    if current_profit_rate is not None:
        lines.append(f"   현재 포지션 수익률: {format_profit_rate(current_profit_rate)}")
    
    return "\n".join(lines)


def safe_percentage(numerator: float, denominator: float) -> float:
    """
    안전한 퍼센트 계산 (0으로 나누기 방지)
    """
    if denominator == 0:
        return 0.0
    return (numerator / denominator) * 100