# 🚀 PyUpbit 자동 매매 시스템

깔끔하고 모듈화된 암호화폐 자동 매매 시스템입니다. 실제 거래와 테스트 모드를 명확히 분리하여 안전하게 전략을 테스트할 수 있습니다.

## 📁 프로젝트 구조

```
pyupbit/
├── bitcoin_auto_trader.py          # 실제 거래 프로그램
├── test_trading_simulator.py       # 가상 거래 테스트 프로그램
├── business_logic/                 # 비즈니스 로직 모듈
│   ├── core/                       # 핵심 기능
│   │   ├── trading_engine.py       # 통합 트레이딩 엔진
│   │   ├── market_data.py          # 시장 데이터 조회
│   │   ├── asset_manager.py        # 자산 관리 (실제/가상)
│   │   ├── position_manager.py     # 포지션 관리
│   │   └── technical_analysis.py   # 기술적 분석
│   ├── strategies/                 # 트레이딩 전략
│   │   └── technical_strategy.py   # 기술적 분석 전략
│   ├── executors/                  # 거래 실행
│   │   └── trading_executor.py     # 실제/가상 거래 실행
│   └── utils/                      # 유틸리티
│       ├── config.py               # 설정 관리
│       ├── logger.py               # 로깅 설정
│       └── coin_selector.py        # 코인 선택
└── logs/                           # 로그 파일
```

## 🔧 설치 및 설정

### 1. 필수 라이브러리 설치

```bash
pip install pyupbit pandas numpy schedule
```

### 2. API 키 설정 (실제 거래용)

**방법 1: 환경 변수 설정**
```bash
export UPBIT_ACCESS_KEY='your_access_key'
export UPBIT_SECRET_KEY='your_secret_key'
```

**방법 2: 파일 생성**
```bash
# upbit_keys.txt 파일 생성
echo "your_access_key" > upbit_keys.txt
echo "your_secret_key" >> upbit_keys.txt
```

## 🎯 사용 방법

### 실제 거래 모드

```bash
python3 bitcoin_auto_trader.py
```

- **⚠️ 주의**: 실제 자산으로 거래를 수행합니다
- API 키가 필요합니다
- 웹소켓 실시간 모니터링 지원
- 안전한 거래 실행 및 리스크 관리

### 테스트 모드 (시뮬레이션)

```bash
python3 test_trading_simulator.py
```

- **✅ 안전**: 가상 자산으로만 거래 테스트
- API 키 불필요 (시장 데이터만 조회)
- 100만원 시드머니로 시작
- 상세한 테스트 결과 리포트
- 결과를 JSON 파일로 저장

## 📊 주요 기능

### 공통 기능
- **다중 코인 지원**: BTC, ETH, MASK, SOL, PEPE
- **기술적 분석**: RSI, 볼린저 밴드, 이동평균선, 스토캐스틱, MACD
- **리스크 관리**: 손절/익절 자동 실행
- **상세한 로깅**: 모든 거래 내역 기록
- **실시간 모니터링**: 현재 상태 및 포지션 확인

### 실제 거래 전용
- **실시간 웹소켓**: 급격한 가격 변동 감지
- **API 키 검증**: 안전한 거래 실행
- **실제 자산 관리**: 업비트 계정 연동

### 테스트 전용
- **시뮬레이션 모드**: 위험 없는 전략 테스트
- **상세한 리포트**: 승률, 수익률, 거래 내역
- **결과 저장**: JSON 형태로 테스트 결과 보관
- **빠른 테스트**: 더 민감한 매매 신호로 빠른 결과 확인

## 🎮 명령어

### 실제 거래 모드
- `start` - 자동 매매 시작
- `stop` - 자동 매매 중지
- `status` - 현재 상태 확인
- `config` - 현재 설정 보기
- `quit` - 프로그램 종료

### 테스트 모드
- `start` - 테스트 시작
- `stop` - 테스트 중지
- `status` - 현재 상태 확인
- `report` - 최종 리포트 보기
- `save` - 결과 저장
- `config` - 현재 설정 보기
- `quit` - 프로그램 종료

## ⚙️ 설정 파일

`trading_config.json` 파일에서 매매 설정을 수정할 수 있습니다:

```json
{
  "buy_ratio": 0.1,          // 매수 비율 (10%)
  "sell_ratio": 0.5,         // 매도 비율 (50%)
  "stop_loss": 0.03,         // 손절 비율 (3%)
  "take_profit": 0.05,       // 익절 비율 (5%)
  "min_order_amount": 5000,  // 최소 주문 금액
  "trading_interval": 60,    // 매매 판단 주기 (초)
  "rsi_oversold": 30,        // RSI 과매도 기준
  "rsi_overbought": 70       // RSI 과매수 기준
}
```

## 🔐 보안 주의사항

1. **API 키 보안**: API 키를 코드에 직접 입력하지 마세요
2. **권한 설정**: 업비트에서 필요한 최소 권한만 설정하세요
3. **테스트 먼저**: 실제 거래 전에 반드시 테스트 모드로 전략을 검증하세요
4. **소액 테스트**: 처음에는 소액으로 테스트해보세요

## 🚨 면책 조항

이 프로그램은 교육 목적으로 제작되었습니다. 암호화폐 투자는 높은 리스크를 수반하며, 사용자의 모든 투자 결과에 대한 책임은 사용자에게 있습니다.

## 🤝 기여하기

버그 리포트나 기능 제안은 언제든지 환영합니다!

## 📜 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.