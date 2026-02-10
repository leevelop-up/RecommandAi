#!/usr/bin/env python3
"""
한국 주식 퀀트 전략 — CLI 진입점

실행 예시:
    python run_quant_strategy.py                           # 기본 종목 5개 배치 분석
    python run_quant_strategy.py --ticker 005930 --name 삼성전자   # 단일 종목
    python run_quant_strategy.py --ticker 005930 --years 5        # 5년 데이터
    python run_quant_strategy.py --evolve                          # 자기진화만 실행
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
from processors.quant_strategy import QuantStrategy, run_quant_batch

# ── 기본 분석 종목 ───────────────────────────────────────────
DEFAULT_TICKERS = [
    {"ticker": "005930", "name": "삼성전자"},
    {"ticker": "000660", "name": "SK하이닉스"},
    {"ticker": "051910", "name": "LG화학"},
    {"ticker": "017670", "name": "SK텔레콤"},
    {"ticker": "068270", "name": "AHNLAB"},
]


def setup_logger():
    logger.remove()
    logger.add(
        sys.stderr, level="INFO",
        format="{time:HH:mm:ss} | {level:<8} | {message}",
    )
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    logger.add(
        os.path.join(log_dir, "quant_{time:YYYY-MM-DD}.log"),
        level="DEBUG", rotation="1 day", retention="30 days",
    )


def main():
    setup_logger()

    parser = argparse.ArgumentParser(description="한국 주식 퀀트 전략 엔진")
    parser.add_argument("--ticker", type=str, help="단일 종목코드 (예: 005930)")
    parser.add_argument("--name", type=str, default="", help="종목명")
    parser.add_argument("--years", type=int, default=3, help="데이터 수집 기간 (년, 기본 3)")
    parser.add_argument("--evolve", action="store_true", help="자기진화만 실행")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("  한국 주식 퀀트 전략 엔진 시작")
    logger.info("=" * 60)

    if args.evolve:
        QuantStrategy().self_improve()
        logger.info("자기진화 완료")
        return

    if args.ticker:
        # 단일 종목 분석
        strategy = QuantStrategy()
        result = strategy.analyze(args.ticker, args.name, args.years)
        print(QuantStrategy.format_output(result))
        if "error" not in result:
            strategy.record_trade(result)
    else:
        # 기본 종목 배치 분석
        logger.info(f"기본 종목 {len(DEFAULT_TICKERS)}개 배치 분석")
        results = run_quant_batch(DEFAULT_TICKERS, args.years)
        for r in results:
            print(QuantStrategy.format_output(r))


if __name__ == "__main__":
    main()
