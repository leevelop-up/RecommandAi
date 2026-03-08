"""
테마/섹터 API 엔드포인트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import glob
from fastapi import APIRouter, HTTPException
from typing import Dict, List
from loguru import logger

from utils.data_transformer import transform_themes_response

router = APIRouter()


def get_latest_files(pattern: str, count: int = 1) -> list:
    """최신 파일 경로 목록 반환 (count개)"""
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "output"
    )
    files = glob.glob(os.path.join(output_dir, pattern))
    if not files:
        return []
    return sorted(files, key=os.path.getmtime, reverse=True)[:count]


def get_latest_file(pattern: str) -> str:
    """최신 파일 경로 가져오기"""
    files = get_latest_files(pattern, 1)
    return files[0] if files else None


def extract_sector_scores(ai_result: dict) -> dict:
    """ai_result에서 {sector_name: score} 딕셔너리 추출"""
    score_map = {"positive": 85, "긍정적": 85, "neutral": 50,
                 "중립(소폭 상승)": 55, "중립(소폭 하락)": 45,
                 "negative": 25, "부정적": 25}
    result = {}
    for s in ai_result.get("sector_analysis", []):
        name = s.get("sector", "")
        outlook = s.get("outlook", "neutral")
        result[name] = score_map.get(outlook, 50)
    return result


def load_json_file(filepath: str) -> Dict:
    """JSON 파일 로드"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"JSON 파일 로드 실패 ({filepath}): {e}")
        raise HTTPException(status_code=500, detail=f"데이터 로드 실패: {str(e)}")


@router.get("")
def get_themes():
    """
    테마/섹터 목록

    Returns:
        테마 목록 (점수 포함)
    """
    logger.info("[API] 테마 목록 요청")

    # 최신 추천 파일 찾기
    latest_file = get_latest_file("ai_recommendation_*.json")

    if not latest_file:
        raise HTTPException(
            status_code=404,
            detail="테마 데이터가 없습니다. 먼저 AI 분석을 실행해주세요."
        )

    # 파일 로드 (최신 + 이전)
    recent_files = get_latest_files("ai_recommendation_*.json", 2)
    ai_result = load_json_file(recent_files[0])
    sector_analysis = ai_result.get("sector_analysis", [])

    # 이전 파일에서 previousScore 추출
    previous_scores = {}
    if len(recent_files) >= 2:
        try:
            prev_result = load_json_file(recent_files[1])
            previous_scores = extract_sector_scores(prev_result)
        except Exception:
            pass

    response = transform_themes_response(sector_analysis, previous_scores)

    logger.info(f"[API] 테마 목록 반환: {len(response.get('themes', []))}개")
    return response


@router.get("/hot")
def get_hot_themes():
    """
    급등 테마 (Hot Themes)

    Returns:
        급등 중인 테마 목록
    """
    logger.info("[API] 급등 테마 요청")

    # 급등 예측 파일에서 테마 정보 가져오기
    latest_file = get_latest_file("growth_prediction_*.json")

    if not latest_file:
        raise HTTPException(
            status_code=404,
            detail="급등 테마 데이터가 없습니다."
        )

    growth_result = load_json_file(latest_file)

    # 테마 픽 추출
    theme_picks = growth_result.get("theme_picks", [])

    hot_themes = []
    for theme in theme_picks:
        hot_themes.append({
            "id": theme.get("theme_name", theme.get("theme", "")),
            "name": theme.get("theme_name", theme.get("theme", "")),
            "score": theme.get("theme_rate", 0) * 10,  # 0-100 스케일로
            "trend": "hot",
            "momentum": theme.get("momentum", ""),
            "signal": theme.get("signal", ""),
            "reasoning": theme.get("reasoning", ""),
            "topStocks": theme.get("top_stocks", [])[:5]
        })

    logger.info(f"[API] 급등 테마 반환: {len(hot_themes)}개")
    return {"hotThemes": hot_themes}


@router.get("/{theme_id}")
def get_theme_detail(theme_id: str):
    """
    테마 상세 정보

    Args:
        theme_id: 테마 ID (섹터명)

    Returns:
        테마 상세 정보 및 관련 종목
    """
    logger.info(f"[API] 테마 상세 요청: {theme_id}")

    # 최신 추천 파일 찾기
    latest_file = get_latest_file("ai_recommendation_*.json")

    if not latest_file:
        raise HTTPException(
            status_code=404,
            detail="테마 데이터가 없습니다."
        )

    ai_result = load_json_file(latest_file)

    # 해당 섹터 찾기
    sector_analysis = ai_result.get("sector_analysis", [])
    theme_info = next((s for s in sector_analysis if s.get("sector") == theme_id), None)

    if not theme_info:
        raise HTTPException(
            status_code=404,
            detail=f"테마를 찾을 수 없습니다: {theme_id}"
        )

    # 해당 섹터의 종목들 찾기
    korea_recs = ai_result.get("recommendations", {}).get("korea", [])
    usa_recs = ai_result.get("recommendations", {}).get("usa", [])
    all_stocks = korea_recs + usa_recs

    related_stocks = [
        stock for stock in all_stocks
        if stock.get("sector") == theme_id
    ]

    # 점수순 정렬
    related_stocks.sort(key=lambda x: x.get("score", 0), reverse=True)

    response = {
        "id": theme_id,
        "name": theme_id,
        "outlook": theme_info.get("outlook", "neutral"),
        "reasoning": theme_info.get("reasoning", ""),
        "topStocks": theme_info.get("top_stocks", []),
        "tier1Stocks": theme_info.get("tier1_stocks", []),
        "tier2Stocks": theme_info.get("tier2_stocks", []),
        "tier3Stocks": theme_info.get("tier3_stocks", []),
        "relatedStocks": related_stocks[:10],
        "stockCount": len(related_stocks),
    }

    logger.info(f"[API] 테마 상세 반환: {theme_id} ({len(related_stocks)}개 종목)")
    return response
