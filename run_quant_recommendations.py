#!/usr/bin/env python3
"""
퀀트 ML 기반 종목 추천 배치 실행기

1. DB에서 활성 Tier-1 테마주 조회 (또는 기본 종목 리스트 사용)
2. QuantStrategy.analyze() 실행
3. output/quant/quant_recs_TIMESTAMP.json 저장

사용법:
    python run_quant_recommendations.py               # DB 종목 자동 조회
    python run_quant_recommendations.py --limit 15   # 상위 15종목만
    python run_quant_recommendations.py --tickers 005930 000660 035420
    python run_quant_recommendations.py --years 5    # 5년치 데이터 학습
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import argparse
from datetime import datetime
from loguru import logger

from processors.quant_strategy import QuantStrategy

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "quant")

# DB 조회 실패 시 fallback — 주요 KOSPI 대형주
DEFAULT_TICKERS = [
    {"ticker": "005930", "name": "삼성전자"},
    {"ticker": "000660", "name": "SK하이닉스"},
    {"ticker": "035420", "name": "NAVER"},
    {"ticker": "005380", "name": "현대차"},
    {"ticker": "051910", "name": "LG화학"},
    {"ticker": "068270", "name": "셀트리온"},
    {"ticker": "207940", "name": "삼성바이오로직스"},
    {"ticker": "035720", "name": "카카오"},
    {"ticker": "006400", "name": "삼성SDI"},
    {"ticker": "028260", "name": "삼성물산"},
    {"ticker": "105560", "name": "KB금융"},
    {"ticker": "055550", "name": "신한지주"},
    {"ticker": "003550", "name": "LG"},
    {"ticker": "012330", "name": "현대모비스"},
    {"ticker": "096770", "name": "SK이노베이션"},
    {"ticker": "034730", "name": "SK"},
    {"ticker": "015760", "name": "한국전력"},
    {"ticker": "316140", "name": "우리금융지주"},
    {"ticker": "032830", "name": "삼성생명"},
    {"ticker": "018260", "name": "삼성에스디에스"},
]


def get_tickers_from_db(limit: int = 20) -> list:
    """DB에서 활성 Tier-1 테마주 조회 (theme_score 내림차순)"""
    try:
        from api.database import get_db
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT ts.stock_code, ts.stock_name
                FROM theme_stocks ts
                INNER JOIN themes t ON ts.theme_id = t.id
                WHERE t.is_active = TRUE AND ts.tier = 1
                ORDER BY t.theme_score DESC
                LIMIT %s
            """, (limit,))
            rows = cursor.fetchall()
            cursor.close()
            if rows:
                logger.info(f"DB에서 {len(rows)}개 Tier-1 테마주 조회")
                return [{"ticker": r["stock_code"], "name": r["stock_name"]} for r in rows]
    except Exception as e:
        logger.warning(f"DB 조회 실패: {e}")
    return []


def run_quant_recommendations(tickers: list, years: int = 3) -> dict:
    """퀀트 ML 배치 분석 실행"""
    strategy = QuantStrategy()
    results = []

    for i, t in enumerate(tickers):
        ticker = t["ticker"]
        name = t.get("name", "")
        logger.info(f"[{i+1}/{len(tickers)}] 분석: {ticker} ({name})")

        try:
            analysis = strategy.analyze(ticker, name, years)
            if "error" in analysis:
                logger.warning(f"  ⚠ 실패: {analysis['error']}")
                continue
            results.append(analysis)
            logger.info(
                f"  ✓ {ticker}: {analysis['decision']} "
                f"P(up)={analysis['p_up']:.3f} E[R]={analysis['expected_return']*100:.3f}%"
            )
        except Exception as e:
            logger.error(f"  ✗ {ticker} 오류: {e}")

    buy_results = [r for r in results if r.get("decision") == "BUY"]
    hold_results = [r for r in results if r.get("decision") == "HOLD"]
    sell_results = [r for r in results if r.get("decision") == "SELL"]

    # BUY 종목: P(up) 내림차순 (오늘의 추천용)
    buy_results.sort(key=lambda x: x.get("p_up", 0), reverse=True)
    # 급등 후보: expected_return 내림차순
    growth_candidates = sorted(buy_results, key=lambda x: x.get("expected_return", 0), reverse=True)

    output = {
        "generated_at": datetime.now().isoformat(),
        "engine": "quant_ml",
        "total_analyzed": len(results),
        "buy_count": len(buy_results),
        "hold_count": len(hold_results),
        "sell_count": len(sell_results),
        "recommendations": buy_results,       # /today 용 (P(up) 기준)
        "growth_candidates": growth_candidates,  # /growth 용 (E[R] 기준)
        "all_results": results,
    }
    return output


def main():
    parser = argparse.ArgumentParser(description="퀀트 ML 종목 추천 배치 실행기")
    parser.add_argument("--years",   type=int, default=3,  help="학습 기간(년) [default: 3]")
    parser.add_argument("--limit",   type=int, default=20, help="분석 종목 수 [default: 20]")
    parser.add_argument("--tickers", nargs="*",            help="종목 코드 직접 지정 (예: 005930 000660)")
    args = parser.parse_args()

    # 종목 목록 결정
    if args.tickers:
        tickers = [{"ticker": t, "name": t} for t in args.tickers]
        logger.info(f"직접 지정 종목 {len(tickers)}개 사용")
    else:
        tickers = get_tickers_from_db(args.limit)
        if not tickers:
            logger.info("DB 종목 없음 → 기본 종목 목록 사용")
            tickers = DEFAULT_TICKERS[:args.limit]

    logger.info(f"📊 분석 대상: {len(tickers)}개 종목 / {args.years}년치 데이터")

    result = run_quant_recommendations(tickers, args.years)

    # 저장
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(OUTPUT_DIR, f"quant_recs_{timestamp}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)

    logger.info(f"✅ 저장: {out_path}")
    logger.info(
        f"   BUY {result['buy_count']}개 | "
        f"HOLD {result['hold_count']}개 | "
        f"SELL {result['sell_count']}개"
    )
    return result


if __name__ == "__main__":
    main()
