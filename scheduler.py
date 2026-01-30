"""
하루 3번 자동 실행 스케줄러

실행 방법:
    python scheduler.py                     # 기본 (08:30, 12:30, 15:30 KST)
    python scheduler.py --times 09:00 13:00 16:00  # 커스텀 시간
    python scheduler.py --once              # 즉시 1회 실행

서버에서 계속 실행:
    nohup python scheduler.py > scheduler.log 2>&1 &

또는 crontab 사용 (서버에 등록):
    crontab -e
    30 8,12,15 * * 1-5 cd /path/to/recommandai && python run_ai_recommendation.py --predict
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


def run_recommendation():
    """추천 + 급등 예측 실행"""
    from config.settings import get_settings
    from processors.data_aggregator import DataAggregator
    from processors.ai_engine import AIRecommendationEngine
    from processors.growth_predictor import GrowthPredictor
    from processors.recommendation_exporter import RecommendationExporter

    settings = get_settings()
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)

    try:
        # 1. 데이터 수집
        logger.info("[스케줄러] 데이터 수집 시작")
        aggregator = DataAggregator()
        data = aggregator.collect_all()

        # 2. 추천 분석
        logger.info("[스케줄러] 추천 분석")
        api_key = settings.GEMINI_API_KEY
        engine = AIRecommendationEngine(api_key=api_key)
        rec_result = engine.analyze(data)

        # 3. 급등 예측
        logger.info("[스케줄러] 급등 예측")
        predictor = GrowthPredictor(api_key=api_key)
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
    parser.add_argument("--times", nargs="+", default=["08:30", "12:30", "15:30"],
                        help="실행 시간 (기본: 08:30 12:30 15:30)")
    parser.add_argument("--once", action="store_true", help="즉시 1회만 실행")
    args = parser.parse_args()

    setup_logger()

    if args.once:
        logger.info("[스케줄러] 1회 실행 모드")
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
            run_recommendation()
            # 중복 실행 방지 - 1분 대기
            time.sleep(61)

    logger.info("[스케줄러] 종료")


if __name__ == "__main__":
    main()
