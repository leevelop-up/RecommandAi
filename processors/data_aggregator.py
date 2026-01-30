"""
데이터 수집기 - 모든 스크래퍼로부터 분석용 데이터 통합 수집
"""
import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Tuple
from datetime import datetime
from loguru import logger

from scrapers.korea.krx_scraper import KRXScraper
from scrapers.korea.naver_scraper import NaverFinanceScraper
from scrapers.korea.dynamic_theme_scraper import DynamicThemeScraper
from scrapers.usa.yahoo_scraper import YahooFinanceScraper
from scrapers.news.news_scraper import GoogleNewsRSS


def _safe(func, default=None):
    try:
        return func()
    except Exception as e:
        logger.warning(f"데이터 수집 실패: {e}")
        return default


class DataAggregator:
    """분석용 데이터 통합 수집기"""

    KOREA_WATCHLIST: List[Tuple[str, str]] = [
        ("005930", "삼성전자"), ("000660", "SK하이닉스"), ("035720", "카카오"),
        ("035420", "NAVER"), ("005380", "현대차"), ("051910", "LG화학"),
        ("006400", "삼성SDI"), ("003670", "포스코퓨처엠"), ("105560", "KB금융"),
        ("055550", "신한지주"), ("000270", "기아"), ("068270", "셀트리온"),
        ("028260", "삼성물산"), ("207940", "삼성바이오로직스"), ("373220", "LG에너지솔루션"),
        ("005490", "POSCO홀딩스"), ("012330", "현대모비스"), ("066570", "LG전자"),
        ("003550", "LG"), ("096770", "SK이노베이션"),
    ]

    USA_WATCHLIST: List[str] = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
        "NVDA", "META", "JPM", "V", "JNJ",
        "UNH", "XOM", "PG", "MA", "HD",
        "COST", "ABBV", "CRM", "AMD", "NFLX",
    ]

    THEME_KEYWORDS = ["2차전지", "AI", "HBM", "반도체", "바이오", "전기차", "로봇"]

    def __init__(self):
        self.krx = KRXScraper()
        self.naver = NaverFinanceScraper(delay=0.2)
        self.yahoo = YahooFinanceScraper()
        self.theme_scraper = DynamicThemeScraper(delay=0.2)
        self.news_scraper = GoogleNewsRSS()

    def collect_all(self) -> Dict:
        """모든 데이터 수집 및 구조화"""
        logger.info("=== 전체 데이터 수집 시작 ===")

        data = {
            "collected_at": datetime.now().isoformat(),
            "market_indices": self.collect_market_indices(),
            "korea_stocks": self.collect_korea_stocks(),
            "usa_stocks": self.collect_usa_stocks(),
            "themes": self.collect_themes(),
            "market_news": self.collect_market_news(),
        }

        kr_count = len(data["korea_stocks"])
        us_count = len(data["usa_stocks"])
        logger.info(f"=== 데이터 수집 완료: 한국 {kr_count}종목, 미국 {us_count}종목 ===")
        return data

    def collect_market_indices(self) -> Dict:
        """시장 지수 수집"""
        logger.info("시장 지수 수집 중...")
        korea = _safe(lambda: self.naver.get_market_index(), {})
        usa = _safe(lambda: self.yahoo.get_market_summary(), {})
        return {"korea": korea, "usa": usa}

    def collect_korea_stocks(self) -> List[Dict]:
        """한국 종목 데이터 수집"""
        logger.info(f"한국 종목 수집 중 ({len(self.KOREA_WATCHLIST)}개)...")
        stocks = []

        for ticker, name in self.KOREA_WATCHLIST:
            logger.debug(f"  {name}({ticker}) 수집")
            price = _safe(lambda t=ticker: self.naver.get_realtime_price(t), {})
            fund = _safe(lambda t=ticker: self.krx.get_fundamental(t), {})
            news = _safe(lambda n=name: self.news_scraper.search(f"{n} 주식", max_results=5), [])

            stocks.append({
                "ticker": ticker,
                "name": name,
                "country": "KR",
                "price": price,
                "fundamental": fund,
                "news": news,
            })

        return stocks

    def collect_usa_stocks(self) -> List[Dict]:
        """미국 종목 데이터 수집"""
        logger.info(f"미국 종목 수집 중 ({len(self.USA_WATCHLIST)}개)...")
        stocks = []

        for ticker in self.USA_WATCHLIST:
            logger.debug(f"  {ticker} 수집")
            price = _safe(lambda t=ticker: self.yahoo.get_current_price(t), {})
            fund = _safe(lambda t=ticker: self.yahoo.get_fundamentals(t), {})
            info = _safe(lambda t=ticker: self.yahoo.get_stock_info(t), {})
            news = _safe(lambda t=ticker: self.yahoo.get_news(t), [])

            stocks.append({
                "ticker": ticker,
                "name": info.get("name", ticker),
                "country": "US",
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "price": price,
                "fundamental": fund,
                "news": news[:5],
            })

        return stocks

    def collect_themes(self) -> Dict:
        """테마 데이터 수집"""
        logger.info("테마 데이터 수집 중...")

        all_themes = _safe(lambda: self.theme_scraper.get_all_themes(pages=5), [])

        # 등락률 기준 정렬
        def _rate(t):
            try:
                nums = re.findall(r'-?\d+\.?\d*', str(t.get("change_rate", "0")))
                return float(nums[0]) if nums else 0
            except:
                return 0

        sorted_themes = sorted(all_themes, key=_rate, reverse=True)

        # 상위 테마 종목 수집
        top_themes_detail = []
        for theme in sorted_themes[:5]:
            stocks = _safe(
                lambda c=theme["code"]: self.theme_scraper.get_theme_stocks(c), []
            )
            top_themes_detail.append({
                "name": theme["name"],
                "code": theme["code"],
                "change_rate": theme["change_rate"],
                "stocks": stocks[:10],
            })

        # 키워드 테마
        keyword_themes = {}
        for kw in self.THEME_KEYWORDS:
            matched = _safe(lambda k=kw: self.theme_scraper.search_theme(k), [])
            if matched:
                stocks = _safe(
                    lambda c=matched[0]["code"]: self.theme_scraper.get_theme_stocks(c), []
                )
                keyword_themes[kw] = {
                    "theme_name": matched[0]["name"],
                    "change_rate": matched[0].get("change_rate", ""),
                    "stock_count": len(stocks),
                    "top_stocks": [s["name"] for s in stocks[:5]],
                }

        return {
            "all_themes": sorted_themes[:30],
            "top_themes": top_themes_detail,
            "keyword_themes": keyword_themes,
        }

    def collect_market_news(self) -> List[Dict]:
        """시장 뉴스 수집"""
        logger.info("시장 뉴스 수집 중...")
        return _safe(
            lambda: self.news_scraper.search("코스피 증시 주식", max_results=10), []
        )
