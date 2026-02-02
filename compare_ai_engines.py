"""
AI 엔진 비교 스크립트 - Gemini vs Groq
같은 데이터로 두 AI의 추천 결과를 비교합니다.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import get_settings
from processors.data_aggregator import DataAggregator
from processors.ai_engine import AIRecommendationEngine
from loguru import logger
import json
from datetime import datetime

def compare_engines():
    """Gemini와 Groq 비교"""
    settings = get_settings()

    logger.info("=" * 80)
    logger.info("AI 엔진 비교: Gemini vs Groq")
    logger.info("=" * 80)

    # 1. 데이터 수집 (한 번만)
    logger.info("\n[1단계] 데이터 수집 중...")
    aggregator = DataAggregator()
    data = aggregator.collect_all()
    logger.info(f"✅ 데이터 수집 완료: 한국 {len(data.get('korea_stocks', []))}종목, 미국 {len(data.get('usa_stocks', []))}종목")

    results = {}

    # 2. Gemini 분석
    logger.info("\n" + "=" * 80)
    logger.info("[2단계] Gemini AI 분석 시작")
    logger.info("=" * 80)
    try:
        gemini_engine = AIRecommendationEngine(
            api_key=settings.GEMINI_API_KEY,
            engine="gemini"
        )
        gemini_result = gemini_engine.analyze(data)
        results["gemini"] = gemini_result
        logger.info("✅ Gemini 분석 완료")
    except Exception as e:
        logger.error(f"❌ Gemini 분석 실패: {e}")
        results["gemini"] = None

    # 3. Groq 분석
    logger.info("\n" + "=" * 80)
    logger.info("[3단계] Groq AI 분석 시작")
    logger.info("=" * 80)
    try:
        groq_engine = AIRecommendationEngine(
            api_key=settings.GROQ_API_KEY,
            engine="groq"
        )
        groq_result = groq_engine.analyze(data)
        results["groq"] = groq_result
        logger.info("✅ Groq 분석 완료")
    except Exception as e:
        logger.error(f"❌ Groq 분석 실패: {e}")
        results["groq"] = None

    # 4. 결과 비교
    logger.info("\n" + "=" * 80)
    logger.info("[4단계] 결과 비교")
    logger.info("=" * 80)

    print("\n" + "=" * 100)
    print("🔍 AI 엔진 비교 결과 요약")
    print("=" * 100)

    for engine_name in ["gemini", "groq"]:
        result = results.get(engine_name)
        if not result:
            print(f"\n❌ {engine_name.upper()}: 분석 실패")
            continue

        print(f"\n{'🔷' if engine_name == 'gemini' else '⚡'} {engine_name.upper()} AI")
        print("-" * 100)

        # 엔진 정보
        print(f"엔진 모드: {result.get('engine', 'unknown')}")

        # 시장 개요
        overview = result.get('market_overview', {})
        print(f"시장 심리: {overview.get('sentiment', 'N/A')}")
        print(f"시장 트렌드: {overview.get('trend', 'N/A')}")
        print(f"시장 요약: {overview.get('summary', 'N/A')[:100]}...")

        # TOP 5 추천
        top_picks = result.get('top_picks', [])
        print(f"\n📊 TOP 5 추천 종목:")
        for i, pick in enumerate(top_picks[:5], 1):
            print(f"  {i}. {pick.get('name', 'N/A')} ({pick.get('ticker', 'N/A')}) - "
                  f"점수: {pick.get('score', 0)}, 액션: {pick.get('action', 'N/A')}")

        # 한국 종목 수
        korea_recs = result.get('recommendations', {}).get('korea', [])
        print(f"\n🇰🇷 한국 추천 종목: {len(korea_recs)}개")

        # 미국 종목 수
        usa_recs = result.get('recommendations', {}).get('usa', [])
        print(f"🇺🇸 미국 추천 종목: {len(usa_recs)}개")

        # 섹터 분석
        sectors = result.get('sector_analysis', [])
        print(f"\n📈 섹터 분석: {len(sectors)}개 섹터")
        for sector in sectors[:3]:
            print(f"  - {sector.get('sector', 'N/A')}: {sector.get('outlook', 'N/A')}")

    # 5. 차이점 분석
    print("\n" + "=" * 100)
    print("🔄 주요 차이점")
    print("=" * 100)

    if results["gemini"] and results["groq"]:
        gemini_tops = [p.get('ticker') for p in results["gemini"].get('top_picks', [])[:5]]
        groq_tops = [p.get('ticker') for p in results["groq"].get('top_picks', [])[:5]]

        common = set(gemini_tops) & set(groq_tops)
        gemini_only = set(gemini_tops) - set(groq_tops)
        groq_only = set(groq_tops) - set(gemini_tops)

        print(f"\n✅ 공통 추천: {len(common)}개 - {list(common)}")
        print(f"🔷 Gemini만 추천: {len(gemini_only)}개 - {list(gemini_only)}")
        print(f"⚡ Groq만 추천: {len(groq_only)}개 - {list(groq_only)}")

        # 시장 심리 비교
        gemini_sentiment = results["gemini"].get('market_overview', {}).get('sentiment', 'N/A')
        groq_sentiment = results["groq"].get('market_overview', {}).get('sentiment', 'N/A')

        print(f"\n💭 시장 심리 분석:")
        print(f"  Gemini: {gemini_sentiment}")
        print(f"  Groq:   {groq_sentiment}")
        print(f"  {'✅ 일치' if gemini_sentiment == groq_sentiment else '❌ 불일치'}")

    # 6. JSON 저장
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    comparison_file = os.path.join(output_dir, f"ai_comparison_{timestamp}.json")

    with open(comparison_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "gemini": results.get("gemini"),
            "groq": results.get("groq")
        }, f, ensure_ascii=False, indent=2)

    print(f"\n💾 비교 결과 저장: {comparison_file}")
    print("\n" + "=" * 100)

if __name__ == "__main__":
    compare_engines()
