# RecommandStock API 서버

RecommandAi 백엔드와 RecommandStock 프론트엔드를 연결하는 FastAPI 서버

## 📋 기능

- ✅ AI 추천 종목 API
- ✅ 급등 예측 API
- ✅ 테마/섹터 분석 API
- ✅ 시장/종목 뉴스 API
- ✅ 실시간 가격 정보 자동 추가
- ✅ CORS 설정 (React 개발 서버 허용)

## 🚀 빠른 시작

### 1. API 서버 시작

```bash
# 간단한 방법
./start_api.sh

# 또는 직접 실행
python api/main.py
```

서버 주소: `http://localhost:8000`
API 문서: `http://localhost:8000/docs`

### 2. AI 추천 데이터 생성

API를 사용하기 전에 먼저 AI 분석을 실행하여 데이터를 생성해야 합니다:

```bash
# 추천 + 급등 예측 실행
python run_ai_recommendation.py --predict

# 뉴스 수집
python collect_comprehensive_news.py --market
```

## 📡 API 엔드포인트

### 추천 종목

#### `GET /api/recommendations/today`
오늘의 AI 추천 종목 (실시간 가격 포함)

**응답 예시:**
```json
{
  "generatedAt": "2026-02-01T10:30:00",
  "engine": "gemini",
  "marketOverview": {
    "summary": "...",
    "sentiment": "positive"
  },
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
      "analystRating": 4.7,
      "reasoning": "...",
      "targetReturn": "+15~20%"
    }
  ],
  "themeStocks": [...],
  "topPicks": [...]
}
```

#### `GET /api/recommendations/growth`
급등 예측 종목

**응답 예시:**
```json
{
  "generatedAt": "2026-02-01T10:30:00",
  "growthStocks": [
    {
      "id": "247540",
      "symbol": "에코프로비엠",
      "name": "EcoPro BM",
      "price": 285000,
      "predictedReturn": "+5~7%",
      "confidence": "High",
      "timeframe": "1-3일",
      "entryPoint": "280,000원",
      "stopLoss": "270,000원",
      "rank": 1
    }
  ],
  "hotThemes": [...]
}
```

#### `GET /api/recommendations/summary`
시장 요약 정보

### 테마/섹터

#### `GET /api/themes`
전체 테마 목록 (점수 포함)

**응답 예시:**
```json
{
  "themes": [
    {
      "id": "반도체",
      "name": "반도체",
      "score": 85,
      "trend": "hot",
      "outlook": "positive",
      "reasoning": "...",
      "stockCount": 5,
      "topStocks": ["삼성전자", "SK하이닉스", ...]
    }
  ]
}
```

#### `GET /api/themes/hot`
급등 중인 테마

#### `GET /api/themes/{theme_id}`
테마 상세 정보 및 관련 종목

### 뉴스

#### `GET /api/news/market?limit=20`
시장 뉴스

**파라미터:**
- `limit`: 반환할 뉴스 개수 (기본: 20, 최대: 100)

#### `GET /api/news/stock/{ticker}?limit=10`
종목별 뉴스

**예시:** `/api/news/stock/005930?limit=10`

#### `GET /api/news/keyword/{keyword}?limit=10`
키워드 뉴스 검색

**예시:** `/api/news/keyword/AI반도체?limit=10`

## 🏗️ 아키텍처

```
RecommandAi/
├── api/                    # API 서버
│   ├── main.py            # FastAPI 메인 서버
│   ├── recommendations.py # 추천 종목 라우터
│   ├── themes.py          # 테마 라우터
│   └── news.py            # 뉴스 라우터
├── processors/
│   └── price_enricher.py  # 실시간 가격 추가
├── utils/
│   └── data_transformer.py # 데이터 형식 변환
├── data/
│   └── stock_master.json  # 종목 마스터 (한글/영문명)
└── output/                # AI 생성 데이터 (JSON)
    ├── ai_recommendation_*.json
    ├── growth_prediction_*.json
    └── market_news_*.json
```

## 🔄 데이터 플로우

1. **AI 분석 실행** → `output/` 폴더에 JSON 생성
2. **API 요청** → 최신 JSON 파일 로드
3. **실시간 가격 추가** → Naver/Yahoo Finance에서 현재가 조회
4. **형식 변환** → RecommandStock Stock 인터페이스로 변환
5. **응답 반환** → Frontend로 JSON 응답

## 📝 Frontend 연동

### React에서 API 사용하기

```typescript
// src/services/api.ts
const API_BASE_URL = 'http://localhost:8000/api';

export const getRecommendations = async () => {
  const response = await fetch(`${API_BASE_URL}/recommendations/today`);
  return response.json();
};

export const getGrowthPredictions = async () => {
  const response = await fetch(`${API_BASE_URL}/recommendations/growth`);
  return response.json();
};

export const getThemes = async () => {
  const response = await fetch(`${API_BASE_URL}/themes`);
  return response.json();
};

export const getMarketNews = async (limit = 20) => {
  const response = await fetch(`${API_BASE_URL}/news/market?limit=${limit}`);
  return response.json();
};
```

### 컴포넌트에서 사용

```typescript
import { useEffect, useState } from 'react';
import { getRecommendations } from '@/services/api';

function HomePage() {
  const [stocks, setStocks] = useState([]);

  useEffect(() => {
    getRecommendations()
      .then(data => setStocks(data.recommendedStocks))
      .catch(error => console.error('API Error:', error));
  }, []);

  return (
    <div>
      {stocks.map(stock => (
        <StockCard key={stock.id} stock={stock} />
      ))}
    </div>
  );
}
```

## ⚙️ 설정

### CORS 설정 변경

`api/main.py`에서 CORS 허용 도메인 수정:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite
        "http://localhost:3000",  # React
        "https://your-domain.com"  # 프로덕션
    ],
    ...
)
```

### 포트 변경

`api/main.py` 마지막 부분:

```python
uvicorn.run(app, host="0.0.0.0", port=8000)  # 포트 번호 변경
```

## 🔧 트러블슈팅

### 1. "추천 데이터가 없습니다" 오류

**원인:** AI 분석이 실행되지 않음
**해결:** `python run_ai_recommendation.py --predict` 실행

### 2. 가격 정보가 0원

**원인:** Naver/Yahoo Finance 스크래핑 실패
**해결:** 인터넷 연결 확인, API 제한 확인

### 3. CORS 오류

**원인:** Frontend 도메인이 허용되지 않음
**해결:** `api/main.py`의 `allow_origins`에 도메인 추가

### 4. 종목 영문명이 한글로 나옴

**원인:** `data/stock_master.json`에 종목 정보 없음
**해결:** 해당 종목을 `stock_master.json`에 추가

## 📊 성능 최적화

- **캐싱**: 동일한 파일을 반복해서 읽지 않도록 메모리 캐싱 추가 가능
- **비동기 처리**: 가격 조회를 async로 병렬 처리
- **Redis**: 실시간 가격 정보를 Redis에 캐싱
- **DB 연동**: JSON 파일 대신 PostgreSQL/MariaDB 사용

## 🚀 배포

### Docker로 배포

```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt requirements_api.txt ./
RUN pip install -r requirements.txt -r requirements_api.txt
COPY . .
CMD ["python", "api/main.py"]
```

### 시스템 서비스로 등록 (systemd)

```bash
sudo nano /etc/systemd/system/recommandstock-api.service
```

```ini
[Unit]
Description=RecommandStock API Server
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/path/to/RecommandAi
ExecStart=/usr/bin/python3 /path/to/RecommandAi/api/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable recommandstock-api
sudo systemctl start recommandstock-api
```

## 📚 추가 자료

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [RecommandAi 메인 README](./README.md)
- [데이터 매핑 분석](./DATA_MAPPING_ANALYSIS.md)
