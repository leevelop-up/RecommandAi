"""
뉴스 API 엔드포인트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import glob
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional
from loguru import logger

router = APIRouter()


def get_latest_file(pattern: str) -> str:
    """최신 파일 경로 가져오기"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = glob.glob(os.path.join(base_dir, pattern))
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def load_json_file(filepath: str) -> Dict:
    """JSON 파일 로드"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"JSON 파일 로드 실패 ({filepath}): {e}")
        raise HTTPException(status_code=500, detail=f"데이터 로드 실패: {str(e)}")


@router.get("/market")
def get_market_news(limit: int = Query(default=20, le=100)):
    """
    시장 뉴스

    Args:
        limit: 반환할 뉴스 개수 (최대 100)

    Returns:
        시장 뉴스 목록
    """
    logger.info(f"[API] 시장 뉴스 요청 (limit={limit})")

    # 최신 시장 뉴스 파일 찾기
    latest_file = get_latest_file("market_news_*.json")

    if not latest_file:
        raise HTTPException(
            status_code=404,
            detail="뉴스 데이터가 없습니다. 먼저 뉴스 수집을 실행해주세요."
        )

    news_data = load_json_file(latest_file)

    # 모든 소스의 뉴스 통합
    all_news = []
    for source, news_list in news_data.get("sources", {}).items():
        for news in news_list:
            all_news.append({
                "title": news.get("title", ""),
                "description": news.get("description", ""),
                "link": news.get("link", ""),
                "source": news.get("source", source),
                "published": news.get("published", ""),
            })

    # 최신순 정렬 (발행일 기준, 없으면 그대로)
    all_news = all_news[:limit]

    logger.info(f"[API] 시장 뉴스 반환: {len(all_news)}개")
    return {
        "news": all_news,
        "totalCount": len(all_news),
        "collectedAt": news_data.get("collected_at", ""),
    }


@router.get("/stock/{ticker}")
def get_stock_news(ticker: str, limit: int = Query(default=10, le=50)):
    """
    종목별 뉴스

    Args:
        ticker: 종목 코드
        limit: 반환할 뉴스 개수 (최대 50)

    Returns:
        해당 종목 관련 뉴스
    """
    logger.info(f"[API] 종목 뉴스 요청: {ticker} (limit={limit})")

    # 종목별 뉴스 파일 찾기
    latest_file = get_latest_file(f"stock_{ticker}_news_*.json")

    if not latest_file:
        # 종목 뉴스가 없으면 빈 배열 반환
        logger.warning(f"종목 뉴스 파일 없음: {ticker}")
        return {
            "news": [],
            "totalCount": 0,
            "ticker": ticker,
        }

    news_data = load_json_file(latest_file)

    # 모든 소스의 뉴스 통합
    all_news = []
    for source, news_list in news_data.get("sources", {}).items():
        for news in news_list:
            all_news.append({
                "title": news.get("title", ""),
                "description": news.get("description", ""),
                "link": news.get("link", ""),
                "source": news.get("source", source),
                "published": news.get("published", ""),
            })

    all_news = all_news[:limit]

    logger.info(f"[API] 종목 뉴스 반환: {ticker} - {len(all_news)}개")
    return {
        "news": all_news,
        "totalCount": len(all_news),
        "ticker": ticker,
        "stockName": news_data.get("stock_name", ""),
        "collectedAt": news_data.get("collected_at", ""),
    }


@router.get("/keyword/{keyword}")
def search_news(keyword: str, limit: int = Query(default=10, le=50)):
    """
    키워드 뉴스 검색

    Args:
        keyword: 검색 키워드
        limit: 반환할 뉴스 개수 (최대 50)

    Returns:
        키워드 관련 뉴스
    """
    logger.info(f"[API] 키워드 뉴스 검색: {keyword} (limit={limit})")

    # 키워드 뉴스 파일 찾기
    latest_file = get_latest_file(f"keyword_{keyword}_news_*.json")

    if not latest_file:
        logger.warning(f"키워드 뉴스 파일 없음: {keyword}")
        return {
            "news": [],
            "totalCount": 0,
            "keyword": keyword,
        }

    news_data = load_json_file(latest_file)

    # 모든 소스의 뉴스 통합
    all_news = []
    for source, news_list in news_data.get("sources", {}).items():
        for news in news_list:
            all_news.append({
                "title": news.get("title", ""),
                "description": news.get("description", ""),
                "link": news.get("link", ""),
                "source": news.get("source", source),
                "published": news.get("published", ""),
            })

    all_news = all_news[:limit]

    logger.info(f"[API] 키워드 뉴스 반환: {keyword} - {len(all_news)}개")
    return {
        "news": all_news,
        "totalCount": len(all_news),
        "keyword": keyword,
        "collectedAt": news_data.get("collected_at", ""),
    }
