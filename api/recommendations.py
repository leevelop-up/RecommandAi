"""
추천 종목 API 엔드포인트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import glob
from fastapi import APIRouter, HTTPException
from typing import Dict
from loguru import logger

from processors.price_enricher import PriceEnricher
from utils.data_transformer import (
    transform_recommendations_response,
    transform_growth_response
)

router = APIRouter()
price_enricher = PriceEnricher()


def get_latest_file(pattern: str) -> str:
    """최신 파일 경로 가져오기"""
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "output"
    )
    files = glob.glob(os.path.join(output_dir, pattern))
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


@router.get("/today")
def get_today_recommendations():
    """
    오늘의 AI 추천 종목

    Returns:
        추천 종목 목록 (Stock 인터페이스 형식)
    """
    logger.info("[API] 오늘의 추천 종목 요청")

    # 최신 추천 파일 찾기
    latest_file = get_latest_file("ai_recommendation_*.json")

    if not latest_file:
        raise HTTPException(
            status_code=404,
            detail="추천 데이터가 없습니다. 먼저 AI 분석을 실행해주세요."
        )

    # 파일 로드
    ai_result = load_json_file(latest_file)

    # 실시간 가격 정보 추가
    try:
        ai_result = price_enricher.enrich_recommendations(ai_result)
    except Exception as e:
        logger.warning(f"가격 정보 추가 실패: {e}")

    # Frontend 형식으로 변환
    response = transform_recommendations_response(ai_result)

    logger.info(f"[API] 추천 종목 반환: {len(response.get('recommendedStocks', []))}개")
    return response


@router.get("/growth")
def get_growth_predictions():
    """
    급등 예측 종목

    Returns:
        급등 예측 종목 목록
    """
    logger.info("[API] 급등 예측 종목 요청")

    # 최신 급등 예측 파일 찾기
    latest_file = get_latest_file("growth_prediction_*.json")

    if not latest_file:
        raise HTTPException(
            status_code=404,
            detail="급등 예측 데이터가 없습니다. 먼저 AI 분석을 실행해주세요."
        )

    # 파일 로드
    growth_result = load_json_file(latest_file)

    # 실시간 가격 정보 추가
    try:
        growth_result = price_enricher.enrich_growth_predictions(growth_result)
    except Exception as e:
        logger.warning(f"가격 정보 추가 실패: {e}")

    # Frontend 형식으로 변환
    response = transform_growth_response(growth_result)

    logger.info(f"[API] 급등 예측 반환: {len(response.get('growthStocks', []))}개")
    return response


@router.get("/summary")
def get_market_summary():
    """
    시장 요약 정보

    Returns:
        시장 개요 및 리스크 평가
    """
    logger.info("[API] 시장 요약 정보 요청")

    # 최신 추천 파일에서 시장 정보 추출
    latest_file = get_latest_file("ai_recommendation_*.json")

    if not latest_file:
        raise HTTPException(
            status_code=404,
            detail="시장 데이터가 없습니다."
        )

    ai_result = load_json_file(latest_file)

    return {
        "marketOverview": ai_result.get("market_overview", {}),
        "riskAssessment": ai_result.get("risk_assessment", {}),
        "generatedAt": ai_result.get("generated_at", ""),
        "engine": ai_result.get("engine", "unknown"),
    }
