"""
주식 추천 스케줄러 — scrapers → Aidata 듀얼 파이프라인

실행 방법:
    python scheduler.py                         # 기본 스케줄 (금주추천 모드)
    python scheduler.py --mode weekly --once    # 즉시 1회 실행 (스크랩 + AI)
    python scheduler.py --mode legacy --once    # 즉시 1회 실행 (기존 방식)
    python scheduler.py --times 08:00 09:00     # 커스텀 실행 시간

개별 단계 실행 (로컬 테스트):
    python scrapers/run_scrapers.py             # Step 1: 스크랩만 → output/scrap/
    python Aidata/run_aidata.py                 # Step 2: AI만  → output/ai/

금주 추천 모드 (기본) — Step 1 → 2 순차 실행:
    Step 1 (스크랩)  : 뉴스·상승주가·테마·회사정보 → output/scrap/
    Step 2 (AI 분석) : scrap 데이터 → Gemini + Groq → output/ai/
"""
import sys
import os
import time
import argparse
import signal
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger


def setup_logger():
    logger.remove()
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)

    logger.add(sys.stderr, level="INFO",
               format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {message}")
    logger.add(os.path.join(log_dir, "scheduler_{time:YYYYMMDD}.log"),
               level="DEBUG", rotation="1 day", retention="30 days")


def run_news_collection():
    """뉴스 수집 실행"""
    try:
        logger.info("[스케줄러] 뉴스 수집 시작")
        from collect_comprehensive_news import NewsCollector

        collector = NewsCollector()

        # 시장 뉴스 수집
        market_result = collector.collect_and_save_market_news()
        logger.info(f"[스케줄러] 시장 뉴스: {market_result['total_collected']}개 수집, {market_result['saved_to_db']}개 DB 저장")

        return True

    except Exception as e:
        logger.error(f"[스케줄러] 뉴스 수집 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def run_weekly_recommendation():
    """금주 추천 실행 (스크랩 → Gemini + Groq 듀얼 AI)"""
    try:
        # ── Step 1/2: 스크랩 → output/scrap/ ──
        logger.info("[스케줄러] ── Step 1/2: 스크랩 실행 시작 ──")
        from scrapers.run_scrapers import ScrapeRunner
        ScrapeRunner().run_all()
        logger.info("[스케줄러] ── Step 1/2: 스크랩 완료 ──\n")

        # ── Step 2/3: AI 분석 → output/ai/ ──
        logger.info("[스케줄러] ── Step 2/3: AI 분석 실행 시작 ──")
        from Aidata.run_aidata import load_scrap_data, run_ai_analysis, save_ai_result
        data   = load_scrap_data()
        result = run_ai_analysis(data)
        save_ai_result(result)
        logger.info("[스케줄러] ── Step 2/3: AI 분석 완료 ──\n")

        # ── Step 3/3: DB 저장 ──
        logger.info("[스케줄러] ── Step 3/3: DB 저장 시작 ──")
        from save_to_db import save_to_database
        save_to_database(result)
        logger.info("[스케줄러] ── Step 3/3: DB 저장 완료 ──")

        return True

    except Exception as e:
        logger.error(f"[스케줄러] 금주 추천 실행 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def run_quant_analysis():
    """퀀트 전략 분석 실행 (ML 모델 기반 BUY/HOLD/SELL)"""
    try:
        logger.info("[스케줄러] ── 퀀트 전략 분석 시작 ──")
        from processors.quant_strategy import run_quant_batch

        DEFAULT_TICKERS = [
            {"ticker": "005930", "name": "삼성전자"},
            {"ticker": "000660", "name": "SK하이닉스"},
            {"ticker": "051910", "name": "LG화학"},
            {"ticker": "017670", "name": "SK텔레콤"},
            {"ticker": "068270", "name": "AHNLAB"},
        ]
        results = run_quant_batch(DEFAULT_TICKERS)

        success = sum(1 for r in results if "error" not in r)
        logger.info(f"[스케줄러] ── 퀀트 분석 완료: {success}/{len(results)}개 성공 ──")
        return True

    except Exception as e:
        logger.error(f"[스케줄러] 퀀트 분석 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def run_recommendation():
    """추천 + 급등 예측 실행 (기존 방식)"""
    from config.settings import get_settings
    from processors.data_aggregator import DataAggregator
    from processors.ai_engine import AIRecommendationEngine
    from processors.growth_predictor import GrowthPredictor
    from processors.recommendation_exporter import RecommendationExporter

    settings = get_settings()
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)

    try:
        # 0. 뉴스 수집 (먼저 실행)
        logger.info("[스케줄러] 뉴스 수집 시작")
        run_news_collection()

        # 1. 데이터 수집
        logger.info("[스케줄러] 데이터 수집 시작")
        aggregator = DataAggregator()
        data = aggregator.collect_all()

        # 2. 추천 분석
        logger.info("[스케줄러] 추천 분석")
        ai_engine_type = settings.AI_ENGINE.lower()

        if ai_engine_type == "xai" or ai_engine_type == "grok":
            api_key = settings.XAI_API_KEY
            logger.info("[스케줄러] AI 엔진: xAI Grok 2")
        elif ai_engine_type == "groq":
            api_key = settings.GROQ_API_KEY
            logger.info("[스케줄러] AI 엔진: Groq (llama-3.3-70b)")
        else:
            api_key = settings.GEMINI_API_KEY
            logger.info("[스케줄러] AI 엔진: Gemini 2.0 Flash")

        engine = AIRecommendationEngine(api_key=api_key, engine=ai_engine_type)
        rec_result = engine.analyze(data)

        # 3. 급등 예측
        logger.info("[스케줄러] 급등 예측")
        predictor = GrowthPredictor(api_key=api_key, engine=ai_engine_type)
        growth_result = predictor.predict(data)

        # 4. 내보내기
        exporter = RecommendationExporter(output_dir=output_dir)
        rec_paths = exporter.export(rec_result)
        growth_paths = exporter.export_growth(growth_result)

        logger.info(f"[스케줄러] 파일 저장 완료")
        logger.info(f"  추천 리포트: {rec_paths['text']}")
        logger.info(f"  추천 JSON:  {rec_paths['json']}")
        logger.info(f"  급등 예측:   {growth_paths['text']}")
        logger.info(f"  급등 JSON:  {growth_paths['json']}")

        # 5. DB 저장
        try:
            from db.save_to_db import RecommendationDB
            db = RecommendationDB()
            rec_id = db.save_recommendation(rec_paths['json'], rec_paths['text'])
            growth_id = db.save_growth_prediction(growth_paths['json'], growth_paths['text'])
            db.close()
            logger.info(f"[스케줄러] DB 저장 완료: 추천 ID={rec_id}, 급등 ID={growth_id}")
        except Exception as e:
            logger.warning(f"[스케줄러] DB 저장 실패 (파일은 저장됨): {e}")

        return True

    except Exception as e:
        logger.error(f"[스케줄러] 실행 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def get_next_run(schedule_times: list) -> datetime:
    """다음 실행 시간 계산"""
    now = datetime.now()

    for t_str in sorted(schedule_times):
        h, m = map(int, t_str.split(":"))
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if target > now:
            return target

    # 오늘 모든 시간 지남 → 내일 첫 번째 시간
    h, m = map(int, sorted(schedule_times)[0].split(":"))
    tomorrow = now + timedelta(days=1)
    return tomorrow.replace(hour=h, minute=m, second=0, microsecond=0)


def main():
    parser = argparse.ArgumentParser(description="주식 추천 스케줄러")
    parser.add_argument("--times", nargs="+", default=["08:00", "09:00"],
                        help="실행 시간 (기본: 08:00 09:00 - 08시 데이터수집, 09시 추천생성)")
    parser.add_argument("--once", action="store_true", help="즉시 1회만 실행")
    parser.add_argument("--mode", choices=["weekly", "legacy", "quant"], default="weekly",
                        help="실행 모드: weekly(금주추천-듀얼AI) / legacy(기존방식) / quant(퀀트 ML 전략)")
    args = parser.parse_args()

    setup_logger()

    if args.once:
        logger.info("[스케줄러] 1회 실행 모드")
        if args.mode == "weekly":
            logger.info("[스케줄러] 모드: 금주 추천 (Gemini + Groq 듀얼 AI)")
            run_weekly_recommendation()
        elif args.mode == "quant":
            logger.info("[스케줄러] 모드: 퀀트 ML 전략 (BUY/HOLD/SELL)")
            run_quant_analysis()
        else:
            logger.info("[스케줄러] 모드: 기존 추천")
            run_recommendation()
        return

    # 종료 시그널 처리
    running = True
    def handle_signal(sig, frame):
        nonlocal running
        logger.info(f"[스케줄러] 종료 신호 수신 ({sig})")
        running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    logger.info("=" * 60)
    logger.info("  주식 추천 스케줄러 시작")
    logger.info(f"  실행 시간: {', '.join(args.times)}")
    logger.info(f"  실행 모드: {args.mode}")
    logger.info("=" * 60)

    while running:
        next_run = get_next_run(args.times)
        wait_seconds = (next_run - datetime.now()).total_seconds()

        if wait_seconds > 0:
            logger.info(f"[스케줄러] 다음 실행: {next_run.strftime('%Y-%m-%d %H:%M')} "
                        f"({wait_seconds/60:.0f}분 후)")

            # 1분 단위로 체크하며 대기
            while wait_seconds > 0 and running:
                sleep_time = min(wait_seconds, 60)
                time.sleep(sleep_time)
                wait_seconds = (next_run - datetime.now()).total_seconds()

        if running:
            logger.info(f"[스케줄러] === 실행 시작 ({datetime.now().strftime('%H:%M')}) ===")
            if args.mode == "weekly":
                run_weekly_recommendation()
            elif args.mode == "quant":
                run_quant_analysis()
            else:
                run_recommendation()
            # 중복 실행 방지 - 1분 대기
            time.sleep(61)

    logger.info("[스케줄러] 종료")


if __name__ == "__main__":
    main()
