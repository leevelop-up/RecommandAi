# RecommandStock ↔ RecommandAi 데이터 매핑 분석

생성일: 2026-02-01

## 1. RecommandStock이 요구하는 데이터 구조

### 1.1 Stock 인터페이스 (기본 종목 데이터)
```typescript
interface Stock {
  id: string;
  symbol: string;          // 종목명 (예: "삼성전자")
  name: string;            // 영문명 (예: "Samsung Electronics")
  price: number;           // 현재가
  change: number;          // 전일대비 변화액
  changePercent: number;   // 등락률 (%)
  marketCap: string;       // 시가총액 (예: "427조원")
  peRatio: number;         // PER
  dividendYield: number;   // 배당수익률
  sector: string;          // 섹터/업종
  recommendation: string;  // 추천의견 (Strong Buy, Buy, Hold 등)
  analystRating: number;   // 애널리스트 평점 (1-5)
}
```

### 1.2 HomePage가 보여주는 데이터
- **추천 종목** (`recommendedStocks`): AI가 추천하는 종목 목록
- **테마 종목** (`themeStocks`): 특정 테마/섹터 관련 종목
- **급등 종목**: 단기 급등 예측 종목
- **시장 지수**: KOSPI, KOSDAQ, S&P 500 등
- **테마 트렌드**: 인기 테마별 점수/순위

### 1.3 ThemeListPage가 요구하는 데이터
```typescript
interface Theme {
  id: string;
  name: string;            // 테마명 (예: "AI 반도체")
  score: number;           // 테마 점수 (0-100)
  trend: string;           // 트렌드 (rising, hot, stable)
  stockCount: number;      // 관련 종목 수
  topStocks: Stock[];      // 대표 종목들
  news?: NewsItem[];       // 관련 뉴스
}
```

### 1.4 MyPage가 보여주는 데이터
- **사용자 정보**: 이름, 이메일, 가입일
- **포트폴리오**: 보유 종목, 수익률, 평가액
- **관심 종목**: 즐겨찾기한 종목 목록
- **최근 본 종목**: 조회 이력

---

## 2. RecommandAi가 생성하는 데이터 구조

### 2.1 AI 추천 결과 (`ai_recommendation_*.json`)
```python
{
  "generated_at": "2026-02-01T10:30:00",
  "engine": "gemini",  # or "rule_based", "hybrid"
  "market_overview": {
    "summary": "...",
    "sentiment": "positive|neutral|negative",
    "korea_summary": "...",
    "usa_summary": "..."
  },
  "recommendations": {
    "korea": [
      {
        "ticker": "005930",
        "name": "삼성전자",
        "action": "Strong Buy",
        "score": 85,
        "reasoning": "...",
        "target_return": "+15~20%",
        "risk_factors": ["..."],
        "catalysts": ["..."]
      }
    ],
    "usa": [...]
  },
  "sector_analysis": [
    {
      "sector": "반도체",
      "outlook": "positive",
      "reasoning": "...",
      "top_stocks": ["삼성전자", "SK하이닉스"]
    }
  ],
  "top_picks": [
    {
      "rank": 1,
      "ticker": "005930",
      "name": "삼성전자",
      "country": "KR",
      "action": "Strong Buy",
      "score": 85,
      "one_line": "..."
    }
  ],
  "risk_assessment": {...},
  "avoid_list": [...]
}
```

### 2.2 급등 예측 결과 (`growth_prediction_*.json`)
```python
{
  "generated_at": "...",
  "engine": "gemini",
  "prediction_summary": "...",
  "korea_picks": [
    {
      "rank": 1,
      "ticker": "...",
      "name": "...",
      "change_rate": 2.5,  # 현재 등락률
      "predicted_return": "+5~7%",
      "confidence": "High",
      "timeframe": "1-3일",
      "reasoning": "...",
      "entry_point": "...",
      "stop_loss": "..."
    }
  ],
  "usa_picks": [...],
  "theme_picks": [
    {
      "theme_name": "AI 반도체",
      "theme_rate": 3.2,
      "momentum": "강세",
      "signal": "매수",
      "reasoning": "...",
      "top_stocks": [...]
    }
  ],
  "risk_warning": "..."
}
```

### 2.3 뉴스 데이터 (`market_news_*.json`)
```python
{
  "collected_at": "...",
  "sources": {
    "google": [
      {
        "title": "...",
        "description": "...",
        "link": "...",
        "source": "Google News",
        "published": "2024-01-01 10:00:00"
      }
    ],
    "naver_finance": [...],
    "daum": [...],
    ...
  }
}
```

---

## 3. 데이터 매핑 GAP 분석

### 3.1 ❌ 누락된 데이터 (RecommandAi에서 생성 안됨)

1. **실시간 주가 데이터**
   - `price`, `change`, `changePercent` - 현재 하드코딩됨
   - **해결방안**: Naver Finance API로 실시간 가격 가져와서 JSON에 포함

2. **기본 재무 데이터**
   - `marketCap`, `peRatio`, `dividendYield` - 현재 없음
   - **해결방안**: KRX/Yahoo Finance API로 수집해서 JSON에 포함

3. **애널리스트 평점**
   - `analystRating` (1-5점) - 현재 없음
   - **해결방안**: AI 스코어(0-100)를 1-5점으로 변환

4. **테마/섹터 상세 데이터**
   - Theme 객체 (id, score, trend, stockCount) - 부분적으로만 존재
   - **해결방안**: sector_analysis를 확장하여 테마 점수 계산

5. **종목별 영문명**
   - `name` (영문) - 현재 한글명만 존재
   - **해결방안**: 종목 마스터 데이터에 영문명 추가

### 3.2 ✅ 이미 존재하는 데이터

1. **추천 의견**: `action` (Strong Buy, Buy 등) ✓
2. **추천 근거**: `reasoning` ✓
3. **종목 코드**: `ticker` ✓
4. **종목명**: `name` (한글) ✓
5. **섹터 분석**: `sector_analysis` ✓
6. **급등 예측**: `korea_picks`, `usa_picks` ✓
7. **테마 분석**: `theme_picks` ✓
8. **뉴스 데이터**: 종합 뉴스 수집 ✓

### 3.3 ⚠️  형식 변환 필요

| RecommandStock 요구 | RecommandAi 제공 | 변환 필요 |
|-------------------|----------------|---------|
| `recommendation: "Strong Buy"` | `action: "Strong Buy"` | 필드명만 다름 |
| `analystRating: 4.7` | `score: 85` | 0-100 → 1-5 변환 |
| `marketCap: "427조원"` | 없음 | 추가 수집 필요 |
| `price: 71500` | 없음 | 실시간 가격 추가 |
| `changePercent: 1.71` | `change_rate: 1.71` | 필드명 통일 |

---

## 4. 구현 필요 기능

### 4.1 🔴 우선순위 높음 - 즉시 구현 필요

#### A. API 엔드포인트 생성 (`api/recommendations.py`)
```python
@app.get("/api/recommendations/today")
def get_today_recommendations():
    """오늘의 AI 추천 종목 (최신 JSON 파일 읽기)"""
    # output/ 디렉토리에서 최신 ai_recommendation_*.json 읽기
    # 실시간 가격 정보 추가
    # Stock 인터페이스 형식으로 변환
    return {
        "recommendedStocks": [...],
        "themeStocks": [...],
        "marketIndices": {...}
    }

@app.get("/api/growth/today")
def get_growth_predictions():
    """급등 예측 종목"""
    # growth_prediction_*.json 읽기
    return {"growthStocks": [...]}

@app.get("/api/themes")
def get_themes():
    """테마 목록 + 점수"""
    # sector_analysis를 Theme 형식으로 변환
    return {"themes": [...]}

@app.get("/api/news/market")
def get_market_news():
    """시장 뉴스"""
    # market_news_*.json 읽기
    return {"news": [...]}
```

#### B. 실시간 가격 보강 모듈 (`processors/price_enricher.py`)
```python
class PriceEnricher:
    def enrich_recommendations(self, ai_result: Dict) -> Dict:
        """AI 추천 결과에 실시간 가격 정보 추가"""
        for stock in ai_result["recommendations"]["korea"]:
            ticker = stock["ticker"]
            # Naver Finance에서 실시간 가격 가져오기
            price_data = self.naver.get_realtime_price(ticker)
            stock["price"] = price_data.get("current_price")
            stock["change"] = price_data.get("change")
            stock["changePercent"] = price_data.get("change_rate")
            stock["marketCap"] = price_data.get("market_cap")
        return ai_result
```

#### C. 데이터 변환 유틸 (`utils/data_transformer.py`)
```python
def transform_to_stock_interface(ai_stock: Dict) -> Dict:
    """AI 결과를 Stock 인터페이스로 변환"""
    return {
        "id": ai_stock["ticker"],
        "symbol": ai_stock["name"],
        "name": get_english_name(ai_stock["ticker"]),  # 영문명
        "price": ai_stock.get("price", 0),
        "change": ai_stock.get("change", 0),
        "changePercent": ai_stock.get("changePercent", 0),
        "marketCap": ai_stock.get("marketCap", "N/A"),
        "peRatio": ai_stock.get("peRatio", 0),
        "dividendYield": ai_stock.get("dividendYield", 0),
        "sector": ai_stock.get("sector", "기타"),
        "recommendation": ai_stock["action"],
        "analystRating": convert_score_to_rating(ai_stock["score"])
    }

def convert_score_to_rating(score: int) -> float:
    """0-100 점수를 1-5 평점으로 변환"""
    # 0-40: 1.0-2.0
    # 41-60: 2.1-3.0
    # 61-75: 3.1-4.0
    # 76-90: 4.1-4.5
    # 91-100: 4.6-5.0
    if score >= 91: return 4.6 + (score - 91) * 0.04
    elif score >= 76: return 4.1 + (score - 76) * 0.027
    elif score >= 61: return 3.1 + (score - 61) * 0.06
    elif score >= 41: return 2.1 + (score - 41) * 0.045
    else: return 1.0 + score * 0.025
```

### 4.2 🟡 우선순위 중간 - 다음 단계

#### D. 종목 마스터 데이터 (`data/stock_master.json`)
```json
{
  "005930": {
    "ticker": "005930",
    "kr_name": "삼성전자",
    "en_name": "Samsung Electronics",
    "sector": "반도체",
    "market": "KOSPI"
  },
  ...
}
```

#### E. 테마 점수 계산 모듈 (`processors/theme_scorer.py`)
```python
class ThemeScorer:
    def calculate_theme_scores(self, data: Dict) -> List[Dict]:
        """섹터 분석 + 뉴스 + 급등예측을 종합해서 테마 점수 계산"""
        themes = []
        for sector in data["sector_analysis"]:
            score = self._calculate_score(sector, data)
            themes.append({
                "id": sector["sector"],
                "name": sector["sector"],
                "score": score,  # 0-100
                "trend": self._determine_trend(sector),
                "stockCount": len(sector.get("top_stocks", [])),
                "topStocks": sector.get("top_stocks", [])
            })
        return sorted(themes, key=lambda x: x["score"], reverse=True)
```

### 4.3 🟢 우선순위 낮음 - 선택사항

#### F. 사용자 포트폴리오 관리 (DB 필요)
- 보유 종목, 매수가, 수익률 추적
- 관심 종목 저장
- 조회 이력 저장

#### G. 실시간 알림 시스템
- 급등 알림
- 추천 종목 업데이트 알림
- 테마 점수 변화 알림

---

## 5. 즉시 실행 계획

### Step 1: API 서버 구축 (FastAPI)
```bash
cd /Users/lee/Documents/GitHub/RecommandAi
mkdir -p api
touch api/main.py api/recommendations.py api/themes.py
```

### Step 2: 데이터 변환 모듈 구현
```bash
mkdir -p utils
touch utils/data_transformer.py
touch processors/price_enricher.py
```

### Step 3: 종목 마스터 데이터 생성
```bash
mkdir -p data
touch data/stock_master.json
# 주요 종목 100개 정도 수동으로 추가
```

### Step 4: RecommandStock에서 API 연동
```typescript
// src/services/api.ts
export const getRecommendations = async () => {
  const response = await fetch('http://localhost:8000/api/recommendations/today');
  return response.json();
};
```

---

## 6. 예상 API 응답 형식

### `/api/recommendations/today`
```json
{
  "generatedAt": "2026-02-01T10:30:00",
  "recommendedStocks": [
    {
      "id": "005930",
      "symbol": "삼성전자",
      "name": "Samsung Electronics",
      "price": 71500,
      "change": 1200,
      "changePercent": 1.71,
      "marketCap": "427조원",
      "peRatio": 15.2,
      "dividendYield": 2.8,
      "sector": "반도체",
      "recommendation": "Strong Buy",
      "analystRating": 4.7
    }
  ],
  "themeStocks": [...],
  "hotThemes": [...]
}
```

---

## 결론

**부족한 데이터:**
1. ❌ 실시간 주가 정보 (price, change, changePercent)
2. ❌ 재무 데이터 (marketCap, peRatio, dividendYield)
3. ❌ 종목 영문명
4. ❌ 테마 점수 시스템
5. ❌ API 엔드포인트

**필요한 작업:**
1. FastAPI 서버 구축
2. 실시간 가격 수집 모듈
3. 데이터 변환 레이어
4. 종목 마스터 데이터 생성
5. RecommandStock ↔ API 연동
