"""
강화된 데이터 수집기 - 금주 추천을 위한 종합 데이터 수집
- Hot 테마 10개 (점수, 등락률, 1차/2차/3차 관련주)
- 금주 추천 종목 30개 (상세 데이터)
- 뉴스 분석 기반 동적 데이터 생성
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from loguru import logger
import re

from scrapers.korea.krx_scraper import KRXScraper
from scrapers.korea.naver_scraper import NaverFinanceScraper
from scrapers.korea.dynamic_theme_scraper import DynamicThemeScraper
from scrapers.usa.yahoo_scraper import YahooFinanceScraper
from scrapers.news.comprehensive_news_scraper import ComprehensiveNewsScraper
from config.settings import get_settings


def _safe(func, default=None):
    """안전 실행 래퍼"""
    try:
        return func()
    except Exception as e:
        logger.warning(f"데이터 수집 실패: {e}")
        return default


class EnhancedDataCollector:
    """강화된 데이터 수집기 - 금주 추천용"""

    def __init__(self):
        self.settings = get_settings()
        self.krx = KRXScraper()
        self.naver = NaverFinanceScraper(delay=0.2)
        self.yahoo = YahooFinanceScraper()
        self.theme_scraper = DynamicThemeScraper(delay=0.2)
        self.news_scraper = ComprehensiveNewsScraper(
            naver_client_id=self.settings.NAVER_CLIENT_ID,
            naver_client_secret=self.settings.NAVER_CLIENT_SECRET,
        )

    def collect_weekly_data(self) -> Dict:
        """
        금주 추천용 데이터 수집

        Returns:
            {
                "collected_at": str,
                "hot_themes": List[Dict],  # 10개
                "weekly_recommendations": List[Dict],  # 30개
                "market_overview": Dict,
                "market_news": Dict,
            }
        """
        logger.info("=" * 80)
        logger.info("  금주 추천용 데이터 수집 시작")
        logger.info("=" * 80)

        data = {
            "collected_at": datetime.now().isoformat(),
            "hot_themes": self.collect_hot_themes(count=10),
            "weekly_recommendations": self.collect_weekly_stocks(count=30),
            "market_overview": self.collect_market_overview(),
            "market_news": self.collect_comprehensive_news(),
        }

        logger.info(f"✅ 데이터 수집 완료:")
        logger.info(f"  - Hot 테마: {len(data['hot_themes'])}개")
        logger.info(f"  - 금주 추천 종목: {len(data['weekly_recommendations'])}개")
        logger.info(f"  - 시장 뉴스: {sum(len(v) for v in data['market_news']['sources'].values())}개")

        return data

    def collect_hot_themes(self, count: int = 10) -> List[Dict]:
        """
        Hot 테마 수집 (등락률 상위 + 뉴스 빈도 기반)

        Returns:
            [
                {
                    "rank": int,
                    "name": str,
                    "code": str,
                    "score": float,  # 0-100
                    "change_rate": str,
                    "daily_change": str,
                    "tier1_stocks": List[Dict],
                    "tier2_stocks": List[Dict],
                    "tier3_stocks": List[Dict],
                    "news": List[Dict],
                }
            ]
        """
        logger.info(f"Hot 테마 {count}개 수집 중...")

        # 1. 전체 테마 수집 (등락률 기준 정렬)
        all_themes = _safe(lambda: self.theme_scraper.get_all_themes(pages=10), [])

        # 2. 등락률 파싱 및 정렬
        def parse_rate(theme):
            try:
                rate_str = theme.get("change_rate", "0")
                nums = re.findall(r'-?\d+\.?\d*', rate_str)
                return float(nums[0]) if nums else 0
            except:
                return 0

        sorted_themes = sorted(all_themes, key=parse_rate, reverse=True)

        # 3. 상위 테마 상세 수집
        hot_themes = []
        for i, theme in enumerate(sorted_themes[:count * 2], 1):  # 여유있게 수집
            logger.debug(f"  테마 {i}/{count*2}: {theme['name']}")

            # 테마 종목 수집
            stocks = _safe(
                lambda c=theme["code"]: self.theme_scraper.get_theme_stocks(c), []
            )

            if len(stocks) < 3:  # 종목이 너무 적으면 스킵
                continue

            # 계층별 분류 (상위 30% = 1차, 중간 40% = 2차, 나머지 = 3차)
            n = len(stocks)
            tier1_end = max(1, n // 3)
            tier2_end = max(2, 2 * n // 3)

            tier1 = stocks[:tier1_end]
            tier2 = stocks[tier1_end:tier2_end]
            tier3 = stocks[tier2_end:]

            # 뉴스 수집
            theme_news = _safe(
                lambda: self.news_scraper.google.search(theme['name'], max_results=10), []
            )

            # 점수 계산 (등락률 + 뉴스 빈도)
            rate = parse_rate(theme)
            news_score = min(len(theme_news) * 2, 30)  # 뉴스 개수 기반 (최대 30점)
            total_score = min(100, max(0, rate * 5 + news_score + 50))  # 0-100

            hot_themes.append({
                "rank": len(hot_themes) + 1,
                "name": theme["name"],
                "code": theme["code"],
                "score": round(total_score, 1),
                "change_rate": theme["change_rate"],
                "daily_change": rate,
                "stock_count": n,
                "tier1_stocks": tier1[:10],
                "tier2_stocks": tier2[:15],
                "tier3_stocks": tier3[:20],
                "news": theme_news[:5],
            })

            if len(hot_themes) >= count:
                break

        # 점수 순으로 재정렬
        hot_themes = sorted(hot_themes, key=lambda x: x["score"], reverse=True)
        for i, theme in enumerate(hot_themes, 1):
            theme["rank"] = i

        logger.info(f"✅ Hot 테마 {len(hot_themes)}개 수집 완료")
        return hot_themes

    def collect_weekly_stocks(self, count: int = 30) -> List[Dict]:
        """
        금주 추천 종목 수집 (한국 + 미국 통합)

        Returns:
            [
                {
                    "ticker": str,
                    "name": str,
                    "country": "KR" | "US",
                    "current_price": float,
                    "daily_change": float,
                    "daily_change_rate": str,
                    "market_cap": str,
                    "per": str,
                    "pbr": str,
                    "dividend_yield": str,
                    "analyst_rating": Dict,  # 애널리스트 평가
                    "chart_6m": Dict,  # 6개월 차트 데이터
                    "news": List[Dict],
                    "investment_points": List[str],
                    "sector": str,
                }
            ]
        """
        logger.info(f"금주 추천 종목 {count}개 수집 중...")

        all_stocks = []

        # 1. 한국 종목 수집 (거래량 + 상승률 상위)
        korea_stocks = self._collect_korea_candidates()
        logger.info(f"  한국 후보: {len(korea_stocks)}개")

        for stock in korea_stocks:
            data = self._enrich_korea_stock(stock)
            if data:
                all_stocks.append(data)

        # 2. 미국 종목 수집
        usa_stocks = self._collect_usa_candidates()
        logger.info(f"  미국 후보: {len(usa_stocks)}개")

        for ticker in usa_stocks:
            data = self._enrich_usa_stock(ticker)
            if data:
                all_stocks.append(data)

        # 3. 점수 기반 정렬 및 상위 30개 선택
        scored_stocks = []
        for stock in all_stocks:
            score = self._calculate_stock_score(stock)
            stock["score"] = score
            scored_stocks.append(stock)

        scored_stocks.sort(key=lambda x: x["score"], reverse=True)
        weekly_stocks = scored_stocks[:count]

        logger.info(f"✅ 금주 추천 종목 {len(weekly_stocks)}개 선정 완료")
        return weekly_stocks

    def _collect_korea_candidates(self) -> List[Dict]:
        """한국 종목 후보 수집"""
        candidates = []

        # 거래량 상위
        kospi_volume = _safe(lambda: self.naver.get_top_stocks("KOSPI", "volume"), [])
        kosdaq_volume = _safe(lambda: self.naver.get_top_stocks("KOSDAQ", "volume"), [])
        candidates.extend(kospi_volume[:15])
        candidates.extend(kosdaq_volume[:10])

        # 상승률 상위
        kospi_rise = _safe(lambda: self.naver.get_top_stocks("KOSPI", "rise"), [])
        kosdaq_rise = _safe(lambda: self.naver.get_top_stocks("KOSDAQ", "rise"), [])
        candidates.extend(kospi_rise[:15])
        candidates.extend(kosdaq_rise[:10])

        # 중복 제거
        unique = {}
        for stock in candidates:
            ticker = stock.get("ticker")
            if ticker and ticker not in unique:
                unique[ticker] = stock

        return list(unique.values())

    def _collect_usa_candidates(self) -> List[str]:
        """미국 종목 후보 수집"""
        # 주요 종목 + 섹터별 대표주
        return [
            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
            "NVDA", "META", "JPM", "V", "JNJ",
            "UNH", "XOM", "PG", "MA", "HD",
            "COST", "ABBV", "CRM", "AMD", "NFLX",
        ]

    def _enrich_korea_stock(self, stock: Dict) -> Optional[Dict]:
        """한국 종목 상세 데이터 수집"""
        ticker = stock.get("ticker")
        name = stock.get("name", ticker)

        try:
            # 실시간 가격
            price_data = self.naver.get_realtime_price(ticker)

            # 펀더멘털
            fundamental = self.krx.get_fundamental(ticker)

            # 뉴스
            news = _safe(
                lambda: self.news_scraper.google.search(f"{name} 주식", max_results=8), []
            )

            # 6개월 차트 (일봉 데이터)
            chart_6m = self._get_korea_chart_6m(ticker)

            # 투자 포인트 생성 (뉴스 기반)
            investment_points = self._extract_investment_points(news[:5])

            return {
                "ticker": ticker,
                "name": name,
                "country": "KR",
                "current_price": price_data.get("current_price", 0),
                "daily_change": price_data.get("change", 0),
                "daily_change_rate": price_data.get("change_rate", "0%"),
                "market_cap": self._format_market_cap(fundamental.get("market_cap", 0)),
                "per": fundamental.get("per", "N/A"),
                "pbr": fundamental.get("pbr", "N/A"),
                "dividend_yield": fundamental.get("div_yield", "N/A"),
                "analyst_rating": self._get_naver_consensus(ticker),
                "chart_6m": chart_6m,
                "news": news[:5],
                "investment_points": investment_points,
                "sector": fundamental.get("sector", ""),
                "volume": price_data.get("volume", 0),
            }
        except Exception as e:
            logger.warning(f"한국 종목 데이터 수집 실패 {name}({ticker}): {e}")
            return None

    def _enrich_usa_stock(self, ticker: str) -> Optional[Dict]:
        """미국 종목 상세 데이터 수집"""
        try:
            # 가격 데이터
            price_data = self.yahoo.get_current_price(ticker)

            # 펀더멘털
            fundamental = self.yahoo.get_fundamentals(ticker)

            # 종목 정보
            info = self.yahoo.get_stock_info(ticker)

            # 뉴스
            news = self.yahoo.get_news(ticker)

            # 6개월 차트
            chart_6m = self._get_usa_chart_6m(ticker)

            # 투자 포인트
            investment_points = self._extract_investment_points(news[:5])

            return {
                "ticker": ticker,
                "name": info.get("name", ticker),
                "country": "US",
                "current_price": price_data.get("current_price", 0),
                "daily_change": price_data.get("change", 0),
                "daily_change_rate": price_data.get("change_rate", "0%"),
                "market_cap": self._format_market_cap(fundamental.get("market_cap", 0)),
                "per": fundamental.get("pe_ratio", "N/A"),
                "pbr": fundamental.get("pb_ratio", "N/A"),
                "dividend_yield": fundamental.get("dividend_yield", "N/A"),
                "analyst_rating": self._get_yahoo_analyst_rating(ticker),
                "chart_6m": chart_6m,
                "news": news[:5],
                "investment_points": investment_points,
                "sector": info.get("sector", ""),
                "volume": price_data.get("volume", 0),
            }
        except Exception as e:
            logger.warning(f"미국 종목 데이터 수집 실패 {ticker}: {e}")
            return None

    def _get_korea_chart_6m(self, ticker: str) -> Dict:
        """한국 종목 6개월 차트 데이터"""
        # 네이버에서 일봉 데이터 수집
        try:
            # 간단한 요약 정보 반환 (실제 차트는 프론트엔드에서 API 호출)
            price_data = self.naver.get_realtime_price(ticker)

            return {
                "available": True,
                "period": "6M",
                "current": price_data.get("current_price", 0),
                "high_6m": price_data.get("high", 0),
                "low_6m": price_data.get("low", 0),
                "chart_url": f"https://finance.naver.com/item/fchart.naver?code={ticker}",
            }
        except:
            return {"available": False}

    def _get_usa_chart_6m(self, ticker: str) -> Dict:
        """미국 종목 6개월 차트 데이터"""
        try:
            price_data = self.yahoo.get_current_price(ticker)

            return {
                "available": True,
                "period": "6M",
                "current": price_data.get("current_price", 0),
                "high_52w": price_data.get("fifty_two_week_high", 0),
                "low_52w": price_data.get("fifty_two_week_low", 0),
                "chart_url": f"https://finance.yahoo.com/quote/{ticker}/chart",
            }
        except:
            return {"available": False}

    def _get_naver_consensus(self, ticker: str) -> Dict:
        """네이버 증권 컨센서스 (애널리스트 의견)"""
        # 실제로는 네이버 증권 페이지 스크래핑 필요
        # 현재는 기본값 반환
        return {
            "rating": "보통",
            "target_price": "N/A",
            "analysts_count": 0,
            "source": "네이버증권",
        }

    def _get_yahoo_analyst_rating(self, ticker: str) -> Dict:
        """야후 파이낸스 애널리스트 평가"""
        # Yahoo Finance API에서 수집 가능
        return {
            "rating": "Hold",
            "target_price": "N/A",
            "analysts_count": 0,
            "source": "Yahoo Finance",
        }

    def _extract_investment_points(self, news: List[Dict]) -> List[str]:
        """뉴스에서 투자 포인트 추출"""
        points = []

        for article in news[:3]:
            title = article.get("title", "")
            desc = article.get("description", "")

            # 긍정적 키워드 추출
            positive_keywords = ["실적", "성장", "상승", "호재", "기대", "신고가", "증가"]
            text = (title + " " + desc).lower()

            for keyword in positive_keywords:
                if keyword in text:
                    points.append(f"{keyword.upper()} 관련: {title[:50]}")
                    break

        return points[:3] if points else ["최근 뉴스 기반 분석 필요"]

    def _calculate_stock_score(self, stock: Dict) -> float:
        """종목 점수 계산 (0-100)"""
        score = 50  # 기본 점수

        # 등락률 (최대 30점)
        try:
            rate_str = stock.get("daily_change_rate", "0%")
            rate = float(rate_str.replace("%", "").replace("+", ""))
            score += min(rate * 3, 30)
        except:
            pass

        # 거래량 (최대 10점)
        volume = stock.get("volume", 0)
        if volume > 1000000:
            score += 10
        elif volume > 500000:
            score += 5

        # 뉴스 빈도 (최대 10점)
        news_count = len(stock.get("news", []))
        score += min(news_count * 2, 10)

        return min(100, max(0, score))

    def _format_market_cap(self, value: float) -> str:
        """시가총액 포맷"""
        if value >= 1e12:
            return f"{value/1e12:.2f}조"
        elif value >= 1e8:
            return f"{value/1e8:.0f}억"
        else:
            return "N/A"

    def collect_market_overview(self) -> Dict:
        """시장 개요 수집"""
        korea = _safe(lambda: self.naver.get_market_index(), {})
        usa = _safe(lambda: self.yahoo.get_market_summary(), {})

        return {
            "korea": korea,
            "usa": usa,
        }

    def collect_comprehensive_news(self) -> Dict:
        """종합 시장 뉴스 수집"""
        logger.info("종합 시장 뉴스 수집 중...")
        news_data = self.news_scraper.collect_market_news()
        logger.info(f"✅ 시장 뉴스 수집 완료: {sum(len(v) for v in news_data['sources'].values())}개")
        return news_data
