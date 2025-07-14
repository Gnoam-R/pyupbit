# 비트코인 자동 매매 프로그램

pyupbit 라이브러리를 활용한 고급 비트코인 자동 매매 시스템입니다.

## 주요 기능

### 1. 실시간 시세 모니터링
- **현재가 조회**: `get_current_price()` - 실시간 비트코인 현재가
- **OHLCV 데이터**: `get_ohlcv_data()` - 캔들 차트 데이터 (1분, 5분, 일봉 등)
- **호가 정보**: `get_orderbook()` - 매수/매도 호가 정보
- **웹소켓 실시간 데이터**: 가격 변동 실시간 알림

### 2. 기술적 분석 지표
- **이동평균선**: 단기(5일) vs 장기(20일) 골든크로스/데드크로스
- **RSI**: 과매수(70)/과매도(30) 구간 판단
- **볼린저 밴드**: 상단/하단 터치 신호
- **스토캐스틱**: %K, %D 오실레이터
- **MACD**: 다이버전스 신호

### 3. 자동 매매 전략
- **매수 조건**: 2개 이상의 매수 신호 발생 시
  - 골든크로스 발생
  - RSI 과매도 (< 30)
  - 볼린저 밴드 하단 터치
  - 스토캐스틱 과매도 (< 20)
  - MACD 상승 전환
  - 가격 상승 추세

- **매도 조건**: 2개 이상의 매도 신호 발생 시
  - 데드크로스 발생
  - RSI 과매수 (> 70)
  - 볼린저 밴드 상단 터치
  - 스토캐스틱 과매수 (> 80)
  - MACD 하락 전환
  - 가격 하락 추세

### 4. 리스크 관리
- **손절매**: 3% 손실 시 자동 매도
- **익절매**: 5% 수익 시 자동 매도
- **포지션 관리**: 보유 원화의 10% 매수, 보유 비트코인의 50% 매도
- **최소 주문 금액**: 5,000원 이상

### 5. 계정 관리
- **잔고 조회**: `get_account_info()` - 원화/비트코인 잔고 확인
- **매수/매도 주문**: `execute_buy_order()`, `execute_sell_order()`
- **가격 단위 조정**: `get_tick_size()` - 업비트 호가 단위 자동 조정
- **수익률 계산**: 실시간 수익률 및 통계 관리

## 설치 및 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. API 키 설정
`upbit_keys.txt` 파일을 생성하고 다음과 같이 입력:
```
your_access_key
your_secret_key
```

### 3. 실행
```bash
python bitcoin_auto_trader.py
```

## 사용 방법

### 명령어
- `start`: 자동 매매 시작
- `stop`: 자동 매매 중지
- `status`: 현재 상태 확인 (잔고, 포지션, 수익률)
- `config`: 현재 설정 확인
- `quit`: 프로그램 종료

### 설정 파일
`trading_config.json` 파일을 통해 매매 설정 조정 가능:
```json
{
  "buy_ratio": 0.1,
  "sell_ratio": 0.5,
  "stop_loss": 0.03,
  "take_profit": 0.05,
  "trading_interval": 60,
  "rsi_oversold": 30,
  "rsi_overbought": 70
}
```

## 주요 pyupbit API 활용

### 시세 조회 API
```python
# 티커 목록 조회
tickers = pyupbit.get_tickers("KRW")

# 현재가 조회
current_price = pyupbit.get_current_price("KRW-BTC")

# OHLCV 데이터 조회
df = pyupbit.get_ohlcv("KRW-BTC", interval="minute5", count=200)

# 호가 정보 조회
orderbook = pyupbit.get_orderbook("KRW-BTC")
```

### 거래 API
```python
# 업비트 객체 생성
upbit = pyupbit.Upbit(access_key, secret_key)

# 잔고 조회
balance = upbit.get_balance("KRW")
balances = upbit.get_balances()

# 매수/매도 주문
buy_result = upbit.buy_limit_order("KRW-BTC", price, volume)
sell_result = upbit.sell_limit_order("KRW-BTC", price, volume)

# 시장가 주문
market_buy = upbit.buy_market_order("KRW-BTC", krw_amount)
market_sell = upbit.sell_market_order("KRW-BTC", btc_volume)

# 주문 조회/취소
orders = upbit.get_order("KRW-BTC")
cancel_result = upbit.cancel_order(uuid)
```

### 웹소켓 API
```python
from pyupbit import WebSocketManager

# 실시간 데이터 수신
wm = WebSocketManager("ticker", ["KRW-BTC"])
data = wm.get()
print(data)  # 실시간 가격 정보
wm.terminate()
```

## 로그 및 모니터링

- 모든 거래 활동은 `bitcoin_trader.log` 파일에 기록
- 실시간 가격 변동 알림 (2% 이상 변동 시)
- 매수/매도 신호 발생 시 상세 로그
- 수익률 및 승률 통계 제공

## 주의사항

1. **API 키 보안**: API 키는 절대 코드에 직접 입력하지 마세요
2. **테스트 환경**: 실제 거래 전 소액으로 테스트해보세요
3. **시장 변동성**: 암호화폐는 변동성이 크므로 신중하게 사용하세요
4. **API 제한**: 업비트 API 호출 제한을 준수하세요
5. **손실 위험**: 투자 손실 위험이 있으므로 여유 자금으로만 거래하세요

## 지원 기능

- 다양한 시간대 차트 분석 (1분, 5분, 1시간, 1일)
- 복합 기술적 지표 기반 신호 생성
- 포지션 관리 및 리스크 컨트롤
- 실시간 웹소켓 모니터링
- 설정 파일 저장/로드
- 상세한 로그 및 통계 제공

이 프로그램은 pyupbit 라이브러리의 모든 주요 기능을 활용하여 전문적인 자동 매매 시스템을 구현했습니다.