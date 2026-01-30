"""
RecommandAI - 주식 데이터 수집 및 처리 시스템
메인 실행 파일
"""
import sys
import os
from datetime import datetime
from typing import List, Optional

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
from apscheduler.schedulers.blocking import BlockingScheduler

from config import get_settings
from scrapers import KRXScraper, NaverFinanceScraper, YahooFinanceScraper, StockNewsScraper
from utils import get_mariadb, get_redis
from models import Stock, StockPrice, StockRealtime, StockNews, MarketIndex


# 로깅 설정
settings = get_settings()
logger.add(
    settings.LOG_FILE,
    rotation="1 day",
    retention="7 days",
    level=settings.LOG_LEVEL,
)


class StockDataCollector:
    """주식 데이터 수집기"""

    def __init__(self):
        self.krx = KRXScraper()
        self.naver = NaverFinanceScraper()
        self.yahoo = YahooFinanceScraper()
        self.news = StockNewsScraper(
            naver_client_id=settings.NAVER_CLIENT_ID,
            naver_client_secret=settings.NAVER_CLIENT_SECRET,
        )
        self.db = get_mariadb()
        self.redis = get_redis()

    def collect_korea_stock_list(self):
        """한국 종목 리스트 수집 및 저장"""
        logger.info("한국 종목 리스트 수집 시작")

        df = self.krx.get_stock_list("ALL")
        if df.empty:
            logger.warning("종목 리스트가 비어있습니다")
            return

        with self.db.get_session() as session:
            for _, row in df.iterrows():
                existing = session.query(Stock).filter_by(ticker=row["ticker"]).first()
                if existing:
                    existing.name = row["name"]
                    existing.updated_at = datetime.utcnow()
                else:
                    stock = Stock(
                        ticker=row["ticker"],
                        name=row["name"],
                        market=row["market"],
                        country="KR",
                    )
                    session.add(stock)

        logger.info(f"한국 종목 리스트 저장 완료: {len(df)}개")

    def collect_korea_realtime_prices(self, tickers: Optional[List[str]] = None):
        """한국 주식 실시간 가격 수집"""
        logger.info("한국 실시간 가격 수집 시작")

        if not tickers:
            # DB에서 활성 종목 조회
            with self.db.get_session() as session:
                stocks = session.query(Stock).filter_by(country="KR", is_active=1).all()
                tickers = [s.ticker for s in stocks]

        for ticker in tickers:
            try:
                price_data = self.naver.get_realtime_price(ticker)
                if price_data:
                    # Redis에 캐시
                    self.redis.set_realtime_price(ticker, price_data)
                    logger.debug(f"{ticker} 실시간 가격 저장")
            except Exception as e:
                logger.error(f"{ticker} 실시간 가격 수집 실패: {e}")

        logger.info(f"한국 실시간 가격 수집 완료: {len(tickers)}개")

    def collect_usa_stock_prices(self, tickers: Optional[List[str]] = None):
        """미국 주식 가격 수집"""
        logger.info("미국 주식 가격 수집 시작")

        if not tickers:
            tickers = self.yahoo.POPULAR_TICKERS

        for ticker in tickers:
            try:
                price_data = self.yahoo.get_current_price(ticker)
                if price_data:
                    self.redis.set_realtime_price(ticker, price_data)
                    logger.debug(f"{ticker} 가격 저장")
            except Exception as e:
                logger.error(f"{ticker} 가격 수집 실패: {e}")

        logger.info(f"미국 주식 가격 수집 완료: {len(tickers)}개")

    def collect_korea_historical_prices(self, ticker: str, days: int = 365):
        """한국 주식 과거 가격 수집"""
        logger.info(f"{ticker} 과거 가격 수집 시작")

        df = self.krx.get_stock_price(ticker)
        if df.empty:
            return

        with self.db.get_session() as session:
            for _, row in df.iterrows():
                existing = session.query(StockPrice).filter_by(
                    ticker=ticker, date=row["date"].date()
                ).first()

                if not existing:
                    price = StockPrice(
                        ticker=ticker,
                        date=row["date"].date(),
                        open=row["open"],
                        high=row["high"],
                        low=row["low"],
                        close=row["close"],
                        volume=row["volume"],
                    )
                    session.add(price)

        logger.info(f"{ticker} 과거 가격 저장 완료")

    def collect_news(self, ticker: str, stock_name: str = ""):
        """종목 뉴스 수집"""
        logger.info(f"{ticker} 뉴스 수집 시작")

        news_data = self.news.get_stock_news(ticker, stock_name)

        # Redis 캐시
        all_news = news_data.get("finance_news", []) + news_data.get("api_news", [])
        self.redis.set_news_cache(ticker, all_news[:20])

        # DB 저장
        with self.db.get_session() as session:
            for item in all_news[:20]:
                existing = session.query(StockNews).filter_by(
                    ticker=ticker, title=item.get("title", "")
                ).first()

                if not existing:
                    news = StockNews(
                        ticker=ticker,
                        title=item.get("title", ""),
                        description=item.get("description", ""),
                        link=item.get("link", ""),
                        source=item.get("source", ""),
                    )
                    session.add(news)

        logger.info(f"{ticker} 뉴스 저장 완료")

    def collect_market_index(self):
        """시장 지수 수집"""
        logger.info("시장 지수 수집 시작")

        # 한국 지수
        kr_index = self.naver.get_market_index()
        for name, data in kr_index.items():
            self.redis.set_market_index(name, data)

        # 미국 지수
        us_index = self.yahoo.get_market_summary()
        for name, data in us_index.items():
            self.redis.set_market_index(name, data)

        logger.info("시장 지수 수집 완료")

    def collect_top_stocks(self):
        """상위 종목 수집"""
        logger.info("상위 종목 수집 시작")

        for market in ["KOSPI", "KOSDAQ"]:
            for category in ["rise", "fall", "volume"]:
                stocks = self.naver.get_top_stocks(market, category)
                key = f"{market.lower()}_{category}"
                self.redis.set_top_stocks(key, stocks)

        logger.info("상위 종목 수집 완료")


def init_database():
    """데이터베이스 초기화"""
    logger.info("데이터베이스 초기화 시작")
    db = get_mariadb()
    db.create_tables()
    logger.info("데이터베이스 초기화 완료")


def run_once():
    """한 번 실행"""
    collector = StockDataCollector()

    # 종목 리스트 수집
    collector.collect_korea_stock_list()

    # 시장 지수 수집
    collector.collect_market_index()

    # 상위 종목 수집
    collector.collect_top_stocks()

    # 주요 종목 실시간 가격 (상위 20개만)
    with collector.db.get_session() as session:
        stocks = session.query(Stock).filter_by(country="KR", is_active=1).limit(20).all()
        tickers = [s.ticker for s in stocks]
    collector.collect_korea_realtime_prices(tickers)

    # 미국 주식
    collector.collect_usa_stock_prices()

    logger.info("데이터 수집 완료")


def run_scheduler():
    """스케줄러 실행"""
    scheduler = BlockingScheduler()
    collector = StockDataCollector()

    # 실시간 가격: 1분마다 (장중)
    scheduler.add_job(
        collector.collect_korea_realtime_prices,
        "cron",
        day_of_week="mon-fri",
        hour="9-15",
        minute="*",
        id="korea_realtime",
    )

    # 시장 지수: 5분마다
    scheduler.add_job(
        collector.collect_market_index,
        "interval",
        minutes=5,
        id="market_index",
    )

    # 상위 종목: 5분마다 (장중)
    scheduler.add_job(
        collector.collect_top_stocks,
        "cron",
        day_of_week="mon-fri",
        hour="9-15",
        minute="*/5",
        id="top_stocks",
    )

    # 종목 리스트: 매일 오전 8시
    scheduler.add_job(
        collector.collect_korea_stock_list,
        "cron",
        hour=8,
        minute=0,
        id="stock_list",
    )

    # 미국 주식: 30분마다 (미국 장중 시간 고려)
    scheduler.add_job(
        collector.collect_usa_stock_prices,
        "interval",
        minutes=30,
        id="usa_prices",
    )

    logger.info("스케줄러 시작")
    scheduler.start()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RecommandAI - 주식 데이터 수집기")
    parser.add_argument("--init", action="store_true", help="데이터베이스 초기화")
    parser.add_argument("--once", action="store_true", help="한 번 실행")
    parser.add_argument("--scheduler", action="store_true", help="스케줄러 실행")

    args = parser.parse_args()

    if args.init:
        init_database()
    elif args.once:
        run_once()
    elif args.scheduler:
        run_scheduler()
    else:
        # 기본: 한 번 실행
        run_once()
