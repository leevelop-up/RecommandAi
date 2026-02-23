"""
RecommandAi FastAPI 서버
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime
from loguru import logger

from api.database import get_db, test_connection
from api.models import (
    Theme, ThemeDetail, ThemesResponse,
    NewsItem, NewsResponse,
    Stock, ThemeStock
)

# FastAPI 앱 생성
app = FastAPI(
    title="RecommandAi API",
    description="주식 테마 및 종목 추천 API",
    version="1.0.0"
)

# CORS 설정 (프론트엔드 연동을 위해)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 specific origins만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """서버 시작시 DB 연결 테스트"""
    logger.info("🚀 RecommandAi API 서버 시작")
    test_connection()


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "RecommandAi API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """헬스 체크"""
    db_ok = test_connection()
    return {
        "status": "healthy" if db_ok else "unhealthy",
        "database": "connected" if db_ok else "disconnected",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/recommendations/today")
async def get_today_recommendations(limit: int = 10):
    """
    오늘의 AI 추천 종목
    - 높은 점수의 테마에 속한 종목들을 추천
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # 상위 테마의 Tier 1 종목들을 추천
            sql = """
            SELECT DISTINCT
                ts.stock_code,
                COALESCE(s.kr_name, ts.stock_name) as stock_name,
                ts.stock_price,
                ts.stock_change_rate,
                t.theme_name,
                t.theme_score,
                ts.tier
            FROM theme_stocks ts
            INNER JOIN themes t ON ts.theme_id = t.id
            LEFT JOIN stocks s ON ts.stock_code = s.ticker
            WHERE t.is_active = TRUE AND ts.tier = 1
            ORDER BY t.theme_score DESC, ts.stock_price DESC
            LIMIT %s
            """
            cursor.execute(sql, (limit,))
            recommendations = cursor.fetchall()
            cursor.close()

            return {
                "recommendations": recommendations,
                "total": len(recommendations),
                "generated_at": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"추천 종목 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/recommendations/growth")
async def get_growth_predictions(limit: int = 10):
    """
    급등 예측 종목
    - daily_change가 높은 테마의 종목들
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            sql = """
            SELECT DISTINCT
                ts.stock_code,
                COALESCE(s.kr_name, ts.stock_name) as stock_name,
                ts.stock_price,
                ts.stock_change_rate,
                t.theme_name,
                t.theme_score,
                t.daily_change,
                ts.tier
            FROM theme_stocks ts
            INNER JOIN themes t ON ts.theme_id = t.id
            LEFT JOIN stocks s ON ts.stock_code = s.ticker
            WHERE t.is_active = TRUE AND t.daily_change > 0
            ORDER BY t.daily_change DESC, t.theme_score DESC
            LIMIT %s
            """
            cursor.execute(sql, (limit,))
            predictions = cursor.fetchall()
            cursor.close()

            return {
                "predictions": predictions,
                "total": len(predictions),
                "generated_at": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"급등 예측 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/recommendations/summary")
async def get_market_summary():
    """
    시장 요약 정보
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # 전체 테마 통계
            cursor.execute("""
                SELECT
                    COUNT(*) as total_themes,
                    SUM(CASE WHEN daily_change > 0 THEN 1 ELSE 0 END) as rising_themes,
                    SUM(CASE WHEN daily_change < 0 THEN 1 ELSE 0 END) as falling_themes,
                    AVG(theme_score) as avg_score
                FROM themes
                WHERE is_active = TRUE
            """)
            theme_stats = cursor.fetchone()

            # 전체 종목 수
            cursor.execute("SELECT COUNT(DISTINCT stock_code) as total_stocks FROM theme_stocks")
            stock_stats = cursor.fetchone()

            # 전체 뉴스 수
            cursor.execute("SELECT COUNT(*) as total_news FROM news")
            news_stats = cursor.fetchone()

            cursor.close()

            return {
                "themes": {
                    "total": theme_stats['total_themes'],
                    "rising": theme_stats['rising_themes'],
                    "falling": theme_stats['falling_themes'],
                    "average_score": round(theme_stats['avg_score'], 2) if theme_stats['avg_score'] else 0
                },
                "stocks": {
                    "total": stock_stats['total_stocks']
                },
                "news": {
                    "total": news_stats['total_news']
                },
                "updated_at": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"시장 요약 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/themes", response_model=ThemesResponse)
async def get_themes(
    limit: int = 100,
    offset: int = 0,
    sort_by: str = "theme_score",
    order: str = "desc"
):
    """
    테마 목록 조회

    Args:
        limit: 조회 개수 (기본 100)
        offset: 시작 위치 (기본 0)
        sort_by: 정렬 기준 (theme_score, rank, created_at)
        order: 정렬 순서 (asc, desc)
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # 정렬 옵션 검증
            valid_sorts = ['theme_score', 'rank', 'created_at', 'stock_count']
            if sort_by not in valid_sorts:
                sort_by = 'theme_score'

            order = 'DESC' if order.lower() == 'desc' else 'ASC'

            # 테마 목록 조회
            sql = f"""
            SELECT * FROM themes
            WHERE is_active = TRUE
            ORDER BY {sort_by} {order}
            LIMIT %s OFFSET %s
            """
            cursor.execute(sql, (limit, offset))
            themes_data = cursor.fetchall()

            # 전체 개수 조회
            cursor.execute("SELECT COUNT(*) as total FROM themes WHERE is_active = TRUE")
            total = cursor.fetchone()['total']

            cursor.close()

            themes = [Theme(**theme) for theme in themes_data]

            return ThemesResponse(themes=themes, total=total)

    except Exception as e:
        logger.error(f"테마 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/themes/hot")
async def get_hot_themes(limit: int = 20):
    """
    급등 테마 조회 (theme_score 기준)
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            sql = """
            SELECT * FROM themes
            WHERE is_active = TRUE
            ORDER BY theme_score DESC, daily_change DESC
            LIMIT %s
            """
            cursor.execute(sql, (limit,))
            themes_data = cursor.fetchall()
            cursor.close()

            themes = [Theme(**theme) for theme in themes_data]

            return {"themes": themes, "total": len(themes)}

    except Exception as e:
        logger.error(f"급등 테마 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/themes/{theme_id}", response_model=ThemeDetail)
async def get_theme_detail(theme_id: int):
    """
    테마 상세 조회 (관련주 포함)

    Args:
        theme_id: 테마 ID
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # 테마 정보 조회
            cursor.execute("SELECT * FROM themes WHERE id = %s", (theme_id,))
            theme_data = cursor.fetchone()

            if not theme_data:
                raise HTTPException(status_code=404, detail="테마를 찾을 수 없습니다")

            # 관련주 조회 (tier별로)
            cursor.execute("""
                SELECT ts.*, COALESCE(s.kr_name, ts.stock_name) as stock_name
                FROM theme_stocks ts
                LEFT JOIN stocks s ON ts.stock_code = s.ticker
                WHERE ts.theme_id = %s AND ts.tier = 1
                ORDER BY ts.stock_price DESC
            """, (theme_id,))
            tier1_stocks = [ThemeStock(**row) for row in cursor.fetchall()]

            cursor.execute("""
                SELECT ts.*, COALESCE(s.kr_name, ts.stock_name) as stock_name
                FROM theme_stocks ts
                LEFT JOIN stocks s ON ts.stock_code = s.ticker
                WHERE ts.theme_id = %s AND ts.tier = 2
                ORDER BY ts.stock_price DESC
            """, (theme_id,))
            tier2_stocks = [ThemeStock(**row) for row in cursor.fetchall()]

            cursor.execute("""
                SELECT ts.*, COALESCE(s.kr_name, ts.stock_name) as stock_name
                FROM theme_stocks ts
                LEFT JOIN stocks s ON ts.stock_code = s.ticker
                WHERE ts.theme_id = %s AND ts.tier = 3
                ORDER BY ts.stock_price DESC
            """, (theme_id,))
            tier3_stocks = [ThemeStock(**row) for row in cursor.fetchall()]

            # 관련 뉴스 조회 (종목 연결 + 테마명 키워드 검색)
            theme_name = theme_data.get("theme_name", "")
            cursor.execute("""
                SELECT DISTINCT n.* FROM news n
                WHERE n.ticker IN (
                    SELECT stock_code FROM theme_stocks WHERE theme_id = %s
                )
                OR n.title LIKE %s
                ORDER BY n.created_at DESC
                LIMIT 10
            """, (theme_id, f"%{theme_name}%"))
            news = [NewsItem(**row) for row in cursor.fetchall()]

            cursor.close()

            theme = ThemeDetail(
                **theme_data,
                tier1_stocks=tier1_stocks,
                tier2_stocks=tier2_stocks,
                tier3_stocks=tier3_stocks,
                news=news
            )

            return theme

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"테마 상세 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/news/market", response_model=NewsResponse)
async def get_market_news(limit: int = 20):
    """
    시장 뉴스 조회

    Args:
        limit: 조회 개수
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM news
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            news_data = cursor.fetchall()
            cursor.close()

            news = [NewsItem(**item) for item in news_data]

            return NewsResponse(
                news=news,
                total_count=len(news),
                collected_at=datetime.now().isoformat()
            )

    except Exception as e:
        logger.error(f"뉴스 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/news/stock/{ticker}", response_model=NewsResponse)
async def get_stock_news(ticker: str, limit: int = 10):
    """
    종목별 뉴스 조회

    Args:
        ticker: 종목 코드
        limit: 조회 개수
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM news
                WHERE ticker = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (ticker, limit))
            news_data = cursor.fetchall()
            cursor.close()

            news = [NewsItem(**item) for item in news_data]

            return NewsResponse(
                news=news,
                total_count=len(news),
                collected_at=datetime.now().isoformat(),
                ticker=ticker
            )

    except Exception as e:
        logger.error(f"종목 뉴스 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stocks/{ticker}")
async def get_stock_detail(ticker: str):
    """
    종목 상세 조회

    Args:
        ticker: 종목 코드
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # 종목 정보
            cursor.execute("SELECT * FROM stocks WHERE ticker = %s", (ticker,))
            stock_data = cursor.fetchone()

            if not stock_data:
                raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다")

            # 소속 테마 조회
            cursor.execute("""
                SELECT t.*, ts.tier, ts.stock_price, ts.stock_change_rate
                FROM themes t
                INNER JOIN theme_stocks ts ON t.id = ts.theme_id
                WHERE ts.stock_code = %s
                ORDER BY t.theme_score DESC
                LIMIT 10
            """, (ticker,))
            themes = cursor.fetchall()

            cursor.close()

            return {
                "stock": Stock(**stock_data),
                "themes": themes
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"종목 상세 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
