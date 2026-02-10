"""
스크랩전용 실행 스크립트 — 순수 데이터 수집
----------------------------------------------
출력 (output/scrap/):
    news_summary.json      — 뉴스 총정리 (구글·다음·연합·경제신문 등, 중복 제거)
    rising_stocks.json     — 상승 주가 (한국 거래량/상승률 상위 + 미국 주요주)
    rising_themes.json     — 상승 테마 10개 + 각 테마별 1차·2차·3차 관련주
    company_details.json   — 위 모든 종목의 세부 정보 통합

실행:
    python scrapers/run_scrapers.py
"""
import sys
import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from loguru import logger

from scrapers.korea.krx_scraper import KRXScraper
from scrapers.korea.naver_scraper import NaverFinanceScraper
from scrapers.korea.dynamic_theme_scraper import DynamicThemeScraper
from scrapers.usa.yahoo_scraper import YahooFinanceScraper
from scrapers.news.comprehensive_news_scraper import ComprehensiveNewsScraper
from config.settings import get_settings

OUTPUT_DIR = Path(ROOT_DIR) / "output" / "scrap"

US_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
    "NVDA", "META", "JPM",   "V",    "JNJ",
    "UNH",  "XOM",  "PG",    "MA",   "HD",
    "COST", "ABBV", "CRM",   "AMD",  "NFLX",
]


def _safe(func, default=None):
    """안전 실행 래퍼"""
    try:
        return func()
    except Exception as e:
        logger.warning(f"수집 실패: {e}")
        return default


def _parse_rate(rate_str: str) -> float:
    """등락률 문자열 → float"""
    try:
        nums = re.findall(r'-?\d+\.?\d*', str(rate_str))
        return float(nums[0]) if nums else 0.0
    except Exception:
        return 0.0


def _save_json(path: Path, data: Dict):
    """JSON 파일 저장"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────────────────────────
class ScrapeRunner:
    """스크랩 실행기"""

    def __init__(self):
        self.settings = get_settings()
        self.krx           = KRXScraper()
        self.naver         = NaverFinanceScraper(delay=0.2)
        self.yahoo         = YahooFinanceScraper()
        self.theme_scraper = DynamicThemeScraper(delay=0.2)
        self.news_scraper  = ComprehensiveNewsScraper(
            naver_client_id=self.settings.NAVER_CLIENT_ID,
            naver_client_secret=self.settings.NAVER_CLIENT_SECRET,
        )

    # ── 메인 실행 ─────────────────────────────────────────────────
    def run_all(self):
        """4단계 스크랩 순차 실행 → output/scrap/ 저장"""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        logger.info("=" * 70)
        logger.info("  스크랩 시작  →  output/scrap/")
        logger.info("=" * 70)

        # 1) 뉴스 총정리
        logger.info("\n[1/4] 뉴스 수집 중...")
        news = self.collect_news()
        _save_json(OUTPUT_DIR / "news_summary.json", news)
        logger.info(f"  ✅ news_summary.json  (기사 {news['total_count']}개)")

        # 2) 상승 주가
        logger.info("\n[2/4] 상승 주가 수집 중...")
        stocks = self.collect_rising_stocks()
        _save_json(OUTPUT_DIR / "rising_stocks.json", stocks)
        logger.info(f"  ✅ rising_stocks.json  (한국 {len(stocks.get('korea_stocks', []))}개, "
                    f"미국 {len(stocks.get('usa_stocks', []))}개)")

        # 3) 상승 테마
        logger.info("\n[3/4] 상승 테마 수집 중...")
        themes = self.collect_rising_themes(count=200)  # 상위 200개 테마만 수집
        _save_json(OUTPUT_DIR / "rising_themes.json", themes)
        logger.info(f"  ✅ rising_themes.json  (테마 {len(themes.get('themes', []))}개)")

        # 4) 회사 세부 정보 통합
        logger.info("\n[4/4] 회사 세부 정보 수집 중...")
        details = self.collect_company_details(stocks, themes)
        _save_json(OUTPUT_DIR / "company_details.json", details)
        logger.info(f"  ✅ company_details.json  (회사 {details['total_companies']}개)")

        logger.info("\n" + "=" * 70)
        logger.info("  스크랩 완료")
        logger.info("=" * 70)

    # ── 1) 뉴스 총정리 ────────────────────────────────────────────
    def collect_news(self) -> Dict:
        """여러 소스의 뉴스 수집·중복 제거"""
        market_news = _safe(
            lambda: self.news_scraper.collect_market_news(),
            {"sources": {}},
        )

        all_articles: List[Dict] = []
        sources_summary: Dict[str, int] = {}

        for source, articles in market_news.get("sources", {}).items():
            sources_summary[source] = len(articles)
            for a in articles:
                a["_source"] = source
                all_articles.append(a)

        # 제목 앞 50자 기준 중복 제거
        seen: set = set()
        unique: List[Dict] = []
        for a in all_articles:
            key = a.get("title", "").strip()[:50]
            if key and key not in seen:
                seen.add(key)
                unique.append(a)

        return {
            "collected_at":    datetime.now().isoformat(),
            "total_count":     len(unique),
            "sources_summary": sources_summary,
            "articles":        unique,
        }

    # ── 2) 상승 주가 ──────────────────────────────────────────────
    def collect_rising_stocks(self) -> Dict:
        """한국 거래량·상승률 상위 + 미국 주요주"""
        logger.info("  한국 종목 수집 중...")
        kospi_vol   = _safe(lambda: self.naver.get_top_stocks("KOSPI",  "volume"), [])
        kosdaq_vol  = _safe(lambda: self.naver.get_top_stocks("KOSDAQ", "volume"), [])
        kospi_rise  = _safe(lambda: self.naver.get_top_stocks("KOSPI",  "rise"),   [])
        kosdaq_rise = _safe(lambda: self.naver.get_top_stocks("KOSDAQ", "rise"),   [])

        # ticker 기준 중복 제거
        kr_map: Dict[str, Dict] = {}
        for stock in kospi_vol + kosdaq_vol + kospi_rise + kosdaq_rise:
            t = stock.get("ticker")
            if t and t not in kr_map:
                stock["country"] = "KR"
                kr_map[t] = stock
        kr_stocks = list(kr_map.values())
        logger.info(f"    한국 종목: {len(kr_stocks)}개")

        # 미국 종목
        logger.info("  미국 종목 수집 중...")
        us_stocks: List[Dict] = []
        for ticker in US_TICKERS:
            data = _safe(lambda t=ticker: self._fetch_us_stock(t))
            if data:
                us_stocks.append(data)
        logger.info(f"    미국 종목: {len(us_stocks)}개")

        # 시장 개요
        market_overview = {
            "korea": _safe(lambda: self.naver.get_market_index(), {}),
            "usa":   _safe(lambda: self.yahoo.get_market_summary(), {}),
        }

        return {
            "collected_at":    datetime.now().isoformat(),
            "market_overview": market_overview,
            "korea_stocks":    kr_stocks,
            "usa_stocks":      us_stocks,
        }

    def _fetch_us_stock(self, ticker: str) -> Optional[Dict]:
        """미국 종목 기본 데이터"""
        price       = self.yahoo.get_current_price(ticker)
        info        = self.yahoo.get_stock_info(ticker)
        fundamental = self.yahoo.get_fundamentals(ticker)
        news        = self.yahoo.get_news(ticker)

        return {
            "ticker":         ticker,
            "name":           info.get("name", ticker),
            "country":        "US",
            "current_price":  price.get("current_price", 0),
            "change":         price.get("change", 0),
            "change_rate":    price.get("change_rate", "0%"),
            "volume":         price.get("volume", 0),
            "sector":         info.get("sector", ""),
            "per":            fundamental.get("pe_ratio", "N/A"),
            "pbr":            fundamental.get("pb_ratio", "N/A"),
            "market_cap":     fundamental.get("market_cap", 0),
            "dividend_yield": fundamental.get("dividend_yield", "N/A"),
            "news":           news[:5],
        }

    # ── 3) 상승 테마 ──────────────────────────────────────────────
    def collect_rising_themes(self, count: int = None) -> Dict:
        """등락률 상위 테마 + 1차·2차·3차 관련주"""
        logger.info("  전체 테마 크롤링 중 (모든 페이지)...")
        all_themes = _safe(lambda: self.theme_scraper.get_all_themes(pages=None), [])  # 모든 페이지

        # 등락률 내림차순
        sorted_themes = sorted(
            all_themes,
            key=lambda t: _parse_rate(t.get("change_rate", "0")),
            reverse=True,
        )

        themes: List[Dict] = []
        total_themes = len(sorted_themes) if count is None else count

        logger.info(f"  수집할 테마 개수: {len(sorted_themes)}개")

        for idx, theme in enumerate(sorted_themes, 1):
            # count가 None이면 모든 테마, 아니면 count 개수만큼
            if count is not None and len(themes) >= count:
                break

            logger.info(f"  [{idx}/{len(sorted_themes)}] {theme['name']} 수집 중...")

            stocks = _safe(
                lambda c=theme["code"]: self.theme_scraper.get_theme_stocks(c), []
            )

            # 종목이 너무 적으면 스킵
            if len(stocks) < 3:
                logger.info(f"    종목 수 부족 ({len(stocks)}개) - 스킵")
                continue

            n      = len(stocks)
            t1_end = max(1, n // 3)
            t2_end = max(2, 2 * n // 3)

            rate       = _parse_rate(theme.get("change_rate", "0"))
            theme_news = _safe(
                lambda name=theme["name"]: self.news_scraper.google.search(name, max_results=10),
                [],
            )
            news_score = min(len(theme_news) * 2, 30)
            score      = round(min(100, max(0, rate * 5 + news_score + 50)), 1)

            themes.append({
                "rank":         0,  # 아래에서 재정렬
                "name":         theme["name"],
                "code":         theme["code"],
                "score":        score,
                "change_rate":  theme["change_rate"],
                "daily_change": rate,
                "stock_count":  n,
                "tier1_stocks": stocks[:t1_end],  # 제한 제거 - 모든 1차 관련주
                "tier2_stocks": stocks[t1_end:t2_end],  # 제한 제거 - 모든 2차 관련주
                "tier3_stocks": stocks[t2_end:],  # 제한 제거 - 모든 3차 관련주
                "news":         theme_news[:5],
            })

        # 점수 정렬 + rank 부여
        themes.sort(key=lambda x: x["score"], reverse=True)
        for i, t in enumerate(themes, 1):
            t["rank"] = i

        logger.info(f"    테마 수집 완료: {len(themes)}개")
        return {
            "collected_at": datetime.now().isoformat(),
            "themes":       themes,
        }

    # ── 4) 회사 세부 정보 통합 ────────────────────────────────────
    def collect_company_details(self, stocks_data: Dict, themes_data: Dict) -> Dict:
        """모든 종목의 세부 정보를 한 파일로 통합"""
        companies: Dict[str, Dict] = {}

        # ① rising_stocks — 한국 종목 세부 정보 수집
        for stock in stocks_data.get("korea_stocks", []):
            ticker = stock.get("ticker")
            if ticker and ticker not in companies:
                detail = self._fetch_kr_detail(ticker, stock.get("name", ticker))
                if detail:
                    companies[ticker] = detail

        # ② rising_stocks — 미국 종목 (이미 수집됨 → 재사용)
        for stock in stocks_data.get("usa_stocks", []):
            ticker = stock.get("ticker")
            if ticker and ticker not in companies:
                companies[ticker] = {
                    "ticker":         ticker,
                    "name":           stock.get("name", ticker),
                    "country":        "US",
                    "current_price":  stock.get("current_price", 0),
                    "change_rate":    stock.get("change_rate", "0%"),
                    "sector":         stock.get("sector", ""),
                    "per":            stock.get("per", "N/A"),
                    "pbr":            stock.get("pbr", "N/A"),
                    "market_cap":     stock.get("market_cap", 0),
                    "dividend_yield": stock.get("dividend_yield", "N/A"),
                    "news":           stock.get("news", []),
                    "themes":         [],
                }

        # ③ rising_themes — 1·2·3차 관련주 세부 정보
        for theme in themes_data.get("themes", []):
            theme_name = theme["name"]
            for tier_key in ("tier1_stocks", "tier2_stocks", "tier3_stocks"):
                for stock in theme.get(tier_key, []):
                    ticker = stock.get("ticker") or stock.get("code")
                    name   = stock.get("name", str(ticker) if ticker else "")
                    if not ticker:
                        continue

                    if ticker in companies:
                        # 이미 존재하면 테마 정보만 추가
                        companies[ticker].setdefault("themes", [])
                        if theme_name not in companies[ticker]["themes"]:
                            companies[ticker]["themes"].append(theme_name)
                        continue

                    # 새 종목 → 세부 정보 수집
                    detail = self._fetch_kr_detail(ticker, name)
                    if detail:
                        detail["themes"] = [theme_name]
                        companies[ticker] = detail

        logger.info(f"    회사 세부 정보 통합 완료: {len(companies)}개")
        return {
            "collected_at":    datetime.now().isoformat(),
            "total_companies": len(companies),
            "companies":       companies,
        }

    def _fetch_kr_detail(self, ticker: str, name: str) -> Optional[Dict]:
        """한국 종목 세부 정보 수집"""
        try:
            price       = _safe(lambda: self.naver.get_realtime_price(ticker), {})
            fundamental = _safe(lambda: self.krx.get_fundamental(ticker), {})
            news        = _safe(
                lambda: self.news_scraper.google.search(f"{name} 주식", max_results=5), []
            )
            return {
                "ticker":        ticker,
                "name":          name,
                "country":       "KR",
                "current_price": price.get("current_price", 0),
                "change":        price.get("change", 0),
                "change_rate":   price.get("change_rate", "0%"),
                "volume":        price.get("volume", 0),
                "market_cap":    fundamental.get("market_cap", 0),
                "per":           fundamental.get("per", "N/A"),
                "pbr":           fundamental.get("pbr", "N/A"),
                "eps":           fundamental.get("eps", "N/A"),
                "div_yield":     fundamental.get("div_yield", "N/A"),
                "sector":        fundamental.get("sector", ""),
                "news":          news,
                "themes":        [],
            }
        except Exception as e:
            logger.warning(f"    세부 정보 수집 실패 {name}({ticker}): {e}")
            return None


# ── 로거 설정 + main ──────────────────────────────────────────────────
def setup_logger():
    logger.remove()
    log_dir = Path(ROOT_DIR) / "logs"
    log_dir.mkdir(exist_ok=True)
    logger.add(
        sys.stderr, level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {message}",
    )
    logger.add(
        str(log_dir / "scraper_{time:YYYYMMDD}.log"),
        level="DEBUG", rotation="1 day", retention="30 days",
    )


if __name__ == "__main__":
    setup_logger()
    ScrapeRunner().run_all()
