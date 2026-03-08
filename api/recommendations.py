"""
추천 종목 API 엔드포인트

우선순위:
  1. 퀀트 ML 예측 결과 (output/quant/quant_recs_*.json)
  2. AI 추천 결과 fallback (output/ai_recommendation_*.json)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import glob
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from typing import Dict
from loguru import logger

from processors.price_enricher import PriceEnricher
from utils.data_transformer import (
    transform_recommendations_response,
    transform_growth_response,
    transform_quant_recommendations_response,
    transform_quant_growth_response,
)

router = APIRouter()
price_enricher = PriceEnricher()

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "output"
)
QUANT_DIR = os.path.join(OUTPUT_DIR, "quant")

# 퀀트 결과가 이 시간(시간) 이내면 유효한 것으로 판단
QUANT_FRESHNESS_HOURS = 24


def get_latest_file(pattern: str, base_dir: str = None) -> str | None:
    """최신 파일 경로 반환"""
    search_dir = base_dir or OUTPUT_DIR
    files = glob.glob(os.path.join(search_dir, pattern))
    return max(files, key=os.path.getmtime) if files else None


def load_json_file(filepath: str) -> Dict:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"JSON 로드 실패 ({filepath}): {e}")
        raise HTTPException(status_code=500, detail=f"데이터 로드 실패: {str(e)}")


def _is_fresh(filepath: str, hours: int = QUANT_FRESHNESS_HOURS) -> bool:
    """파일이 지정 시간 이내 생성됐으면 True"""
    try:
        mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
        return datetime.now() - mtime < timedelta(hours=hours)
    except Exception:
        return False


def _load_quant_result() -> Dict | None:
    """최신 퀀트 추천 파일 로드. 없거나 오래됐으면 None 반환."""
    latest = get_latest_file("quant_recs_*.json", QUANT_DIR)
    if not latest:
        return None
    if not _is_fresh(latest):
        logger.info(f"퀀트 결과가 {QUANT_FRESHNESS_HOURS}시간 초과 → AI fallback 사용")
        return None
    logger.info(f"퀀트 결과 사용: {os.path.basename(latest)}")
    return load_json_file(latest)


def _enrich_quant_stocks(response: dict) -> dict:
    """퀀트 추천 종목에 실시간 가격 정보 주입"""
    try:
        # 중복 없이 모든 종목 수집
        all_stocks: dict = {}
        for key in ("recommendedStocks", "themeStocks", "topPicks", "growthStocks"):
            for s in response.get(key, []):
                all_stocks[s["id"]] = s

        if not all_stocks:
            return response

        stock_list = [
            {"ticker": sid, "name": s.get("symbol", "")}
            for sid, s in all_stocks.items()
        ]
        enriched_list = price_enricher._enrich_korea_stocks(stock_list)
        price_map = {e.get("ticker", ""): e for e in enriched_list}

        for key in ("recommendedStocks", "themeStocks", "topPicks", "growthStocks"):
            for s in response.get(key, []):
                e = price_map.get(s["id"])
                if e:
                    s["price"] = e.get("price", 0)
                    s["change"] = e.get("change", 0)
                    s["changePercent"] = e.get("changePercent", 0)
                    s["marketCap"] = e.get("marketCap", "N/A")
    except Exception as ex:
        logger.warning(f"퀀트 가격 enrichment 실패 (무시): {ex}")
    return response


@router.get("/today")
def get_today_recommendations():
    """
    오늘의 추천 종목

    퀀트 ML 결과(BUY, P(up) 내림차순)를 우선 반환.
    퀀트 데이터가 없거나 24시간 초과 시 AI 추천 fallback.
    """
    logger.info("[API] 오늘의 추천 종목 요청")

    # ── 퀀트 ML 우선 ──────────────────────────────────────────
    quant = _load_quant_result()
    if quant:
        response = transform_quant_recommendations_response(quant)
        response = _enrich_quant_stocks(response)
        logger.info(f"[API] 퀀트 추천 반환: {len(response.get('recommendedStocks', []))}개")
        return response

    # ── AI fallback ───────────────────────────────────────────
    logger.info("[API] 퀀트 데이터 없음 → AI 추천 fallback")
    latest_file = get_latest_file("ai_recommendation_*.json")
    if not latest_file:
        raise HTTPException(
            status_code=404,
            detail="추천 데이터가 없습니다. run_quant_recommendations.py 또는 AI 분석을 실행해주세요."
        )

    ai_result = load_json_file(latest_file)
    try:
        ai_result = price_enricher.enrich_recommendations(ai_result)
    except Exception as e:
        logger.warning(f"AI 가격 정보 추가 실패: {e}")

    response = transform_recommendations_response(ai_result)
    logger.info(f"[API] AI 추천 반환: {len(response.get('recommendedStocks', []))}개")
    return response


@router.get("/growth")
def get_growth_predictions():
    """
    급등 예측 종목

    퀀트 ML 결과(BUY, E[R] 내림차순)를 우선 반환.
    퀀트 데이터가 없거나 24시간 초과 시 AI 급등 예측 fallback.
    """
    logger.info("[API] 급등 예측 종목 요청")

    # ── 퀀트 ML 우선 ──────────────────────────────────────────
    quant = _load_quant_result()
    if quant:
        response = transform_quant_growth_response(quant)
        response = _enrich_quant_stocks(response)
        logger.info(f"[API] 퀀트 급등 반환: {len(response.get('growthStocks', []))}개")
        return response

    # ── AI fallback ───────────────────────────────────────────
    logger.info("[API] 퀀트 데이터 없음 → AI 급등 예측 fallback")
    latest_file = get_latest_file("growth_prediction_*.json")
    if not latest_file:
        raise HTTPException(
            status_code=404,
            detail="급등 예측 데이터가 없습니다. run_quant_recommendations.py 또는 AI 분석을 실행해주세요."
        )

    growth_result = load_json_file(latest_file)
    try:
        growth_result = price_enricher.enrich_growth_predictions(growth_result)
    except Exception as e:
        logger.warning(f"AI 가격 정보 추가 실패: {e}")

    response = transform_growth_response(growth_result)
    logger.info(f"[API] AI 급등 반환: {len(response.get('growthStocks', []))}개")
    return response


@router.get("/summary")
def get_market_summary():
    """시장 요약 정보"""
    logger.info("[API] 시장 요약 요청")

    # 퀀트 결과로 요약 제공
    quant = _load_quant_result()
    if quant:
        return {
            "marketOverview": {
                "summary": (
                    f"퀀트 ML 분석 결과: {quant.get('total_analyzed', 0)}개 종목 분석 완료. "
                    f"BUY {quant.get('buy_count', 0)}개 / "
                    f"HOLD {quant.get('hold_count', 0)}개 / "
                    f"SELL {quant.get('sell_count', 0)}개"
                )
            },
            "riskAssessment": {},
            "generatedAt": quant.get("generated_at", ""),
            "engine": "quant_ml",
        }

    latest_file = get_latest_file("ai_recommendation_*.json")
    if not latest_file:
        raise HTTPException(status_code=404, detail="시장 데이터가 없습니다.")

    ai_result = load_json_file(latest_file)
    return {
        "marketOverview": ai_result.get("market_overview", {}),
        "riskAssessment": ai_result.get("risk_assessment", {}),
        "generatedAt": ai_result.get("generated_at", ""),
        "engine": ai_result.get("engine", "unknown"),
    }
