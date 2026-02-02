"""
데이터 변환 유틸리티
AI 추천 결과를 RecommandStock Stock 인터페이스 형식으로 변환
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from typing import Dict, List, Optional
from loguru import logger


# 종목 마스터 데이터 로드
def load_stock_master() -> Dict:
    """종목 마스터 데이터 로드"""
    try:
        master_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "stock_master.json"
        )
        if os.path.exists(master_path):
            with open(master_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            logger.warning(f"종목 마스터 파일 없음: {master_path}")
            return {}
    except Exception as e:
        logger.error(f"종목 마스터 로드 실패: {e}")
        return {}


STOCK_MASTER = load_stock_master()


def get_english_name(ticker: str, korean_name: str = "") -> str:
    """
    종목 영문명 조회

    Args:
        ticker: 종목 코드
        korean_name: 한글 종목명 (fallback용)

    Returns:
        영문명 (없으면 한글명 그대로)
    """
    if ticker in STOCK_MASTER:
        return STOCK_MASTER[ticker].get("en_name", korean_name or ticker)

    # 마스터에 없으면 한글명 그대로 반환
    return korean_name or ticker


def format_market_cap(value, country: str = "KR") -> str:
    """
    시가총액 숫자를 읽기 쉬운 형식으로 변환

    Args:
        value: 시가총액 (숫자 또는 문자열)
        country: 국가 코드 (KR 또는 US)

    Returns:
        포맷된 시가총액 문자열
    """
    if isinstance(value, str):
        # 이미 포맷된 경우 그대로 반환
        if any(c in value for c in ["조", "억", "$", "T", "B", "M"]):
            return value
        try:
            value = float(value.replace(",", ""))
        except (ValueError, AttributeError):
            return value

    if not value or value == 0:
        return "N/A"

    value = float(value)

    if country == "US" or country != "KR":
        # 미국: $T, $B, $M
        if value >= 1_000_000_000_000:
            return f"${value / 1_000_000_000_000:.2f}T"
        elif value >= 1_000_000_000:
            return f"${value / 1_000_000_000:.1f}B"
        elif value >= 1_000_000:
            return f"${value / 1_000_000:.1f}M"
        else:
            return f"${value:,.0f}"
    else:
        # 한국: 조원, 억원
        if value >= 1_000_000_000_000:
            return f"{value / 1_000_000_000_000:.1f}조원"
        elif value >= 100_000_000:
            return f"{value / 100_000_000:.0f}억원"
        else:
            return f"{value:,.0f}원"


def convert_score_to_rating(score: int) -> float:
    """
    0-100 점수를 1.0-5.0 평점으로 변환

    Args:
        score: AI 점수 (0-100)

    Returns:
        애널리스트 평점 (1.0-5.0)
    """
    if score >= 91:
        return round(4.6 + (score - 91) * 0.04, 1)
    elif score >= 76:
        return round(4.1 + (score - 76) * 0.027, 1)
    elif score >= 61:
        return round(3.1 + (score - 61) * 0.06, 1)
    elif score >= 41:
        return round(2.1 + (score - 41) * 0.045, 1)
    else:
        return round(1.0 + score * 0.025, 1)


def transform_to_stock_interface(ai_stock: Dict) -> Dict:
    """
    AI 추천 결과를 Stock 인터페이스로 변환

    Args:
        ai_stock: AI 엔진의 종목 데이터

    Returns:
        Stock 인터페이스 형식 딕셔너리
    """
    ticker = ai_stock.get("ticker", "")
    korean_name = ai_stock.get("name", "")
    score = ai_stock.get("score", 50)

    # 국가 판별: 티커가 숫자면 한국, 알파벳이면 미국
    country = ai_stock.get("country", "")
    if not country:
        country = "KR" if ticker.isdigit() else "US"

    # 시가총액 포맷팅
    raw_market_cap = ai_stock.get("marketCap", ai_stock.get("market_cap", 0))
    formatted_market_cap = format_market_cap(raw_market_cap, country)

    # PER: per 또는 peRatio 또는 fundamentals.per
    pe_ratio = ai_stock.get("peRatio", 0) or ai_stock.get("per", 0)
    if not pe_ratio and "fundamentals" in ai_stock:
        pe_ratio = ai_stock["fundamentals"].get("per", 0)

    # 배당률
    dividend_yield = ai_stock.get("dividendYield", 0) or ai_stock.get("dividend_yield", 0)

    # 섹터
    sector = ai_stock.get("sector", "")
    if not sector or sector == "기타":
        sector = ai_stock.get("industry", "기타")

    return {
        "id": ticker,
        "symbol": korean_name,  # 한글명
        "name": get_english_name(ticker, korean_name),  # 영문명
        "price": ai_stock.get("price", 0),
        "change": ai_stock.get("change", 0),
        "changePercent": ai_stock.get("changePercent", 0),
        "marketCap": formatted_market_cap,
        "peRatio": round(pe_ratio, 1) if pe_ratio else 0,
        "dividendYield": round(dividend_yield, 2) if dividend_yield else 0,
        "sector": sector,
        "recommendation": ai_stock.get("action", "Hold"),
        "analystRating": convert_score_to_rating(score),
        "country": country,
        # 추가 정보 (optional)
        "reasoning": ai_stock.get("reasoning", ""),
        "targetReturn": ai_stock.get("target_return", ""),
        "riskFactors": ai_stock.get("risk_factors", []),
        "catalysts": ai_stock.get("catalysts", []),
    }


def transform_recommendations_response(ai_result: Dict) -> Dict:
    """
    AI 추천 결과를 Frontend API 응답 형식으로 변환

    Args:
        ai_result: AI 엔진의 전체 추천 결과

    Returns:
        Frontend용 응답 딕셔너리
    """
    korea_recs = ai_result.get("recommendations", {}).get("korea", [])
    usa_recs = ai_result.get("recommendations", {}).get("usa", [])

    # 한국/미국 각각 점수순 정렬 후 변환
    korea_sorted = sorted(korea_recs, key=lambda x: x.get("score", 0), reverse=True)
    usa_sorted = sorted(usa_recs, key=lambda x: x.get("score", 0), reverse=True)

    # 한국/미국 균형있게 선택 (각각 상위 10개씩, 교차 배치)
    korea_transformed = [transform_to_stock_interface(s) for s in korea_sorted[:10]]
    usa_transformed = [transform_to_stock_interface(s) for s in usa_sorted[:10]]

    # 교차 배치: US, KR, US, KR, ...
    recommended_stocks = []
    max_len = max(len(korea_transformed), len(usa_transformed))
    for i in range(max_len):
        if i < len(usa_transformed):
            recommended_stocks.append(usa_transformed[i])
        if i < len(korea_transformed):
            recommended_stocks.append(korea_transformed[i])

    # 테마/섹터별 종목 추출
    theme_stocks = []
    sector_analysis = ai_result.get("sector_analysis", [])
    # 모든 추천 종목의 이름/심볼 매핑 (이름 기준 검색용)
    all_stocks_by_name = {}
    for stock in recommended_stocks:
        all_stocks_by_name[stock.get("symbol", "")] = stock
        all_stocks_by_name[stock.get("name", "")] = stock

    added_tickers = set()
    for sector in sector_analysis:
        top_stock_names = sector.get("top_stocks", [])

        for stock_name in top_stock_names:
            if isinstance(stock_name, str) and stock_name in all_stocks_by_name:
                stock = all_stocks_by_name[stock_name]
                if stock.get("id") not in added_tickers:
                    theme_stocks.append(stock)
                    added_tickers.add(stock.get("id"))

    # 테마주가 부족한 경우, 높은 점수의 한국 종목으로 보충
    if len(theme_stocks) < 6:
        for stock in korea_transformed:
            if stock.get("id") not in added_tickers:
                theme_stocks.append(stock)
                added_tickers.add(stock.get("id"))
                if len(theme_stocks) >= 6:
                    break

    # 그래도 부족하면 미국 높은 점수 종목으로 보충
    if len(theme_stocks) < 6:
        for stock in usa_transformed:
            if stock.get("id") not in added_tickers:
                theme_stocks.append(stock)
                added_tickers.add(stock.get("id"))
                if len(theme_stocks) >= 6:
                    break

    return {
        "generatedAt": ai_result.get("generated_at", ""),
        "engine": ai_result.get("engine", "unknown"),
        "marketOverview": ai_result.get("market_overview", {}),
        "recommendedStocks": recommended_stocks[:20],  # 상위 20개
        "themeStocks": theme_stocks[:10],  # 테마별 상위 10개
        "topPicks": [
            transform_to_stock_interface(pick)
            for pick in ai_result.get("top_picks", [])[:10]
        ],
        "sectorAnalysis": sector_analysis,
        "riskAssessment": ai_result.get("risk_assessment", {}),
    }


def transform_growth_response(growth_result: Dict) -> Dict:
    """
    급등 예측 결과를 Frontend API 응답 형식으로 변환

    Args:
        growth_result: 급등 예측 결과

    Returns:
        Frontend용 응답 딕셔너리
    """
    korea_picks = growth_result.get("korea_picks", [])
    usa_picks = growth_result.get("usa_picks", [])

    # Stock 인터페이스로 변환
    growth_stocks = []

    for pick in korea_picks + usa_picks:
        stock = transform_to_stock_interface(pick)
        # 급등 예측 추가 정보
        stock["predictedReturn"] = pick.get("predicted_return", "")
        stock["confidence"] = pick.get("confidence", "")
        stock["timeframe"] = pick.get("timeframe", "")
        stock["entryPoint"] = pick.get("entry_point", "")
        stock["stopLoss"] = pick.get("stop_loss", "")
        stock["rank"] = pick.get("rank", 0)
        growth_stocks.append(stock)

    # 테마별 급등 예측
    theme_picks = growth_result.get("theme_picks", [])
    hot_themes = []

    for theme in theme_picks:
        hot_themes.append({
            "id": theme.get("theme_name", theme.get("theme", "")),
            "name": theme.get("theme_name", theme.get("theme", "")),
            "score": theme.get("theme_rate", 0) * 10,  # 0-100 스케일로 변환
            "trend": "hot" if theme.get("momentum") == "강세" else "rising",
            "momentum": theme.get("momentum", ""),
            "signal": theme.get("signal", ""),
            "reasoning": theme.get("reasoning", ""),
            "topStocks": [
                transform_to_stock_interface(stock) if isinstance(stock, dict) else stock
                for stock in theme.get("top_stocks", [])[:5]
            ]
        })

    return {
        "generatedAt": growth_result.get("generated_at", ""),
        "engine": growth_result.get("engine", "unknown"),
        "predictionSummary": growth_result.get("prediction_summary", ""),
        "growthStocks": growth_stocks,
        "hotThemes": hot_themes,
        "riskWarning": growth_result.get("risk_warning", ""),
    }


def transform_themes_response(sector_analysis: List[Dict]) -> Dict:
    """
    섹터 분석을 Theme 형식으로 변환

    Args:
        sector_analysis: AI의 섹터 분석 결과

    Returns:
        Frontend용 테마 목록
    """
    themes = []

    for sector in sector_analysis:
        sector_name = sector.get("sector", "")
        outlook = sector.get("outlook", "neutral")

        # Outlook을 점수로 변환
        score_map = {"positive": 85, "neutral": 50, "negative": 25}
        score = score_map.get(outlook, 50)

        # Trend 결정
        trend = "hot" if outlook == "positive" else "stable" if outlook == "neutral" else "falling"

        themes.append({
            "id": sector_name,
            "name": sector_name,
            "score": score,
            "trend": trend,
            "outlook": outlook,
            "reasoning": sector.get("reasoning", ""),
            "stockCount": len(sector.get("top_stocks", [])),
            "topStocks": sector.get("top_stocks", [])[:5],
        })

    # 점수순 정렬
    themes.sort(key=lambda x: x["score"], reverse=True)

    return {"themes": themes}
