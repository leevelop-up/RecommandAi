"""
FastAPI 메인 서버 - RecommandStock 프론트엔드용 API
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
from loguru import logger

from api.recommendations import router as recommendations_router
from api.themes import router as themes_router
from api.news import router as news_router
from api.data_files import router as data_files_router

app = FastAPI(
    title="RecommandStock API",
    description="AI 주식 추천 API for React Frontend",
    version="1.0.0"
)

# CORS 설정 - 프론트엔드에서 접근 가능하도록
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite, React 기본 포트
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(recommendations_router, prefix="/api/recommendations", tags=["Recommendations"])
app.include_router(themes_router, prefix="/api/themes", tags=["Themes"])
app.include_router(news_router, prefix="/api/news", tags=["News"])
app.include_router(data_files_router, prefix="/api", tags=["DataFiles"])


@app.get("/")
def root():
    """API 루트"""
    return {
        "service": "RecommandStock API",
        "version": "1.0.0",
        "endpoints": {
            "recommendations": "/api/recommendations/today",
            "growth": "/api/recommendations/growth",
            "themes": "/api/themes",
            "news": "/api/news/market"
        }
    }


@app.get("/health")
def health_check():
    """헬스 체크"""
    return {"status": "healthy", "service": "RecommandStock API"}


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting RecommandStock API Server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
