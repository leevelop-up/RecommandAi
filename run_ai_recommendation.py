"""
AI 주식 추천 실행 스크립트

사용법:
    python run_ai_recommendation.py                 # AI 추천 (Gemini)
    python run_ai_recommendation.py --rule-only     # 규칙 기반만
    python run_ai_recommendation.py --predict       # 급등 예측 모드
    python run_ai_recommendation.py --all           # 추천 + 급등 예측 모두
    python run_ai_recommendation.py --output-dir .  # 출력 경로 지정
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
from config.settings import get_settings
from processors.data_aggregator import DataAggregator
from processors.ai_engine import AIRecommendationEngine
from processors.growth_predictor import GrowthPredictor
from processors.recommendation_exporter import RecommendationExporter


def setup_logger(log_level: str = "INFO"):
    logger.remove()
    logger.add(sys.stderr, level=log_level, format="{time:HH:mm:ss} | {level:<7} | {message}")


def main():
    parser = argparse.ArgumentParser(description="AI 주식 추천 시스템")
    parser.add_argument("--rule-only", action="store_true", help="규칙 기반 분석만 사용")
    parser.add_argument("--predict", action="store_true", help="급등 예측 모드")
    parser.add_argument("--all", action="store_true", help="추천 + 급등 예측 모두 실행")
    parser.add_argument("--output-dir", default=None, help="출력 디렉토리 (기본: recommandai/)")
    parser.add_argument("--log-level", default="INFO", help="로그 레벨")
    args = parser.parse_args()

    setup_logger(args.log_level)
    settings = get_settings()

    output_dir = args.output_dir or os.path.dirname(os.path.abspath(__file__))
    api_key = settings.GEMINI_API_KEY if not args.rule_only else None

    logger.info("=" * 60)
    mode = "급등 예측" if args.predict else "추천 + 급등 예측" if args.all else "AI 추천"
    logger.info(f"  {mode} 시스템 시작")
    logger.info("=" * 60)

    # 1. 데이터 수집
    logger.info("[Step 1] 데이터 수집 시작")
    aggregator = DataAggregator()
    data = aggregator.collect_all()

    kr_count = len(data.get("korea_stocks", []))
    us_count = len(data.get("usa_stocks", []))
    logger.info(f"수집 완료: 한국 {kr_count}종목, 미국 {us_count}종목")

    exporter = RecommendationExporter(output_dir=output_dir)
    all_paths = {}

    # 2. 추천 분석
    if not args.predict or args.all:
        logger.info("[Step 2] AI 추천 분석")
        engine = AIRecommendationEngine(api_key=api_key, force_rule=args.rule_only)
        rec_result = engine.analyze(data)
        rec_paths = exporter.export(rec_result)
        all_paths["recommendation"] = rec_paths

        logger.info(f"  추천 엔진: {rec_result.get('engine', 'unknown')}")
        logger.info(f"  텍스트: {rec_paths['text']}")
        logger.info(f"  JSON:  {rec_paths['json']}")

        top = rec_result.get("top_picks", [])
        if top:
            logger.info("  TOP 5 추천:")
            for p in top[:5]:
                logger.info(f"    {p.get('rank', '')}. {p.get('name', '')}({p.get('ticker', '')}) "
                            f"- {p.get('action', '')} ({p.get('score', 0)}점)")

    # 3. 급등 예측
    if args.predict or args.all:
        logger.info("[Step 3] 급등 예측 분석")
        predictor = GrowthPredictor(api_key=api_key)
        growth_result = predictor.predict(data)
        growth_paths = exporter.export_growth(growth_result)
        all_paths["growth"] = growth_paths

        logger.info(f"  예측 엔진: {growth_result.get('engine', 'unknown')}")
        logger.info(f"  텍스트: {growth_paths['text']}")
        logger.info(f"  JSON:  {growth_paths['json']}")

        kr_picks = growth_result.get("korea_picks", [])
        us_picks = growth_result.get("usa_picks", [])
        if kr_picks:
            logger.info("  한국 급등 후보 TOP 3:")
            for p in kr_picks[:3]:
                logger.info(f"    {p.get('rank', '')}. {p.get('name', '')}({p.get('ticker', '')}) "
                            f"- 예상 {p.get('predicted_return', '')} ({p.get('confidence', '')})")
        if us_picks:
            logger.info("  미국 급등 후보 TOP 3:")
            for p in us_picks[:3]:
                logger.info(f"    {p.get('rank', '')}. {p.get('name', '')}({p.get('ticker', '')}) "
                            f"- 예상 {p.get('predicted_return', '')} ({p.get('confidence', '')})")

    logger.info("=" * 60)
    logger.info("  완료!")
    logger.info("=" * 60)

    return all_paths


if __name__ == "__main__":
    main()
