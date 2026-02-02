# 🚀 금주 추천 시스템 빠른 시작

## ✅ 완료된 구현

### 새로 추가된 기능

1. **Hot 테마 분석 (10개)**
   - 등락률 + 뉴스 빈도 기반 점수 계산
   - 1차/2차/3차 관련주 자동 분류
   - 각 테마별 최신 뉴스 수집

2. **금주 추천 종목 (30개)**
   - 한국 + 미국 통합 추천
   - 거래량/상승률 상위 종목 동적 수집
   - 상세 재무 데이터 (시가총액, PER, PBR, 배당률)
   - 6개월 차트 데이터
   - 종목별 뉴스 및 투자 포인트

3. **듀얼 AI 분석**
   - Gemini AI 분석
   - Groq AI 분석
   - 각 AI별 Top 10 추천, 시장 전망, 투자 전략

4. **스케줄러 개선**
   - 08:00 데이터 수집
   - 09:00 AI 분석 및 추천 생성
   - Weekly/Legacy 모드 선택 가능

## 🎯 즉시 실행 (1분 만에)

### Step 1: API 키 확인

```bash
cat .env | grep -E "GEMINI_API_KEY|GROQ_API_KEY"
```

**설정 방법:**
- `.env` 파일에 API 키 추가
- 예시: [.env.example](.env.example) 참고

### Step 2: 테스트 실행

```bash
# 금주 추천 1회 실행 (2-3분 소요)
python run_weekly_recommendation.py
```

또는 스케줄러로:

```bash
# 즉시 1회 실행
python scheduler.py --mode weekly --once
```

### Step 3: 결과 확인

```bash
# 최신 결과 파일 확인
ls -lht output/weekly_recommendation_* | head -5

# JSON 내용 확인
cat output/weekly_recommendation_*.json | jq '.hot_themes[] | {rank, name, score}'

# 텍스트 리포트 확인
cat output/weekly_recommendation_*.txt | head -50
```

## 📊 출력 예시

### Hot 테마
```
1. AI반도체
   점수: 87.5/100 | 등락률: +3.2% | 종목 수: 45개
   핵심 종목: 삼성전자(+2.1%), SK하이닉스(+3.5%)...

2. 2차전지
   점수: 82.3/100 | 등락률: +2.8% | 종목 수: 38개
   ...
```

### 금주 추천 종목
```
1. 삼성전자 (005930) - KR
   현재가: 75,000원 | 전일대비: +1.5%
   시가총액: 450조 | PER: 15.2 | 배당률: 2.3%
   투자 포인트: HBM3 수주 확대...
```

### AI 분석 (Gemini)
```
Top 10 추천:
1. NVDA (US) - 적극매수
   예상수익: 15-20%
   추천매수가: $880
   목표가: $1,050
   ...
```

## 🤖 Gemini vs Groq 비교

두 AI의 분석을 비교하여 더 객관적인 투자 판단 가능:

```bash
# 두 AI의 Top 10 비교
cat output/weekly_recommendation_*.json | jq '{
  gemini: .ai_recommendations.gemini.top_10_picks[0:3],
  groq: .ai_recommendations.groq.top_10_picks[0:3]
}'
```

## 🔄 자동화 설정

### 매일 자동 실행

```bash
# 백그라운드로 스케줄러 시작
nohup python scheduler.py > scheduler.log 2>&1 &

# 프로세스 확인
ps aux | grep scheduler.py

# 로그 확인
tail -f scheduler.log
```

### Cron 설정 (서버)

```bash
crontab -e

# 평일 매일 08:00에 실행
0 8 * * 1-5 cd /Users/lee/Documents/GitHub/RecommandAi && /usr/bin/python3 run_weekly_recommendation.py >> /tmp/weekly_rec.log 2>&1
```

## 📁 새로 추가된 파일

```
processors/
├── enhanced_data_collector.py    # 강화된 데이터 수집기
└── weekly_recommender.py         # AI 기반 추천 생성기

run_weekly_recommendation.py       # 메인 실행 스크립트
scheduler.py                       # 업데이트됨 (Weekly 모드 추가)

WEEKLY_RECOMMENDATION_README.md    # 상세 문서
QUICK_START.md                     # 이 파일
```

## 🎨 프론트엔드 통합 (다음 단계)

새로운 데이터 구조를 프론트엔드에 통합하려면:

1. API 엔드포인트 추가:
```python
# api/weekly_recommendations.py
@router.get("/weekly/latest")
def get_latest_weekly():
    # output/weekly_recommendation_*.json 최신 파일 반환
```

2. 프론트엔드 페이지 생성:
```typescript
// src/app/pages/WeeklyRecommendationPage.tsx
// Hot 테마 10개 + 추천 종목 30개 + 듀얼 AI 분석 표시
```

## ⚠️ 주의사항

1. **API 사용량**: Gemini + Groq 동시 호출로 API 사용량 2배
   - Gemini Free tier: 15 RPM (분당 요청)
   - Groq Free tier: 30 RPM

2. **실행 시간**: 전체 실행에 2-5분 소요
   - 뉴스 수집: ~30초
   - 데이터 수집: ~1분
   - AI 분석: ~1-2분 (Gemini + Groq)

3. **메모리**: 최대 ~500MB 사용

## 🐛 문제 해결

### "No module named 'processors.enhanced_data_collector'"

```bash
# 경로 확인
ls -l processors/enhanced_data_collector.py

# Python 경로 문제면 현재 디렉토리에서 실행
cd /Users/lee/Documents/GitHub/RecommandAi
python run_weekly_recommendation.py
```

### API 키 오류

```bash
# .env 파일 위치 확인
ls -la .env

# API 키 테스트
python -c "from config.settings import get_settings; print(get_settings().GEMINI_API_KEY[:20])"
```

### 스크래핑 실패

- 딜레이 증가: `DynamicThemeScraper(delay=0.5)` → `delay=1.0`
- 네트워크 확인: `ping finance.naver.com`

## 💡 다음 개선 사항

1. 애널리스트 평가 실제 스크래핑 (현재 placeholder)
2. 6개월 차트 상세 데이터 (OHLCV)
3. DB 자동 저장 (`WeeklyRecommendationDB` 구현)
4. 프론트엔드 대시보드
5. 알림 기능 (이메일/텔레그램)

## ✨ 완성!

이제 매일 08:00에 자동으로 데이터를 수집하고, 09:00에 Gemini + Groq 듀얼 AI가 분석한 금주 추천을 받을 수 있습니다!

```bash
# 지금 바로 실행해보세요!
python run_weekly_recommendation.py
```
