"""
종합 뉴스 스크래퍼 - 모든 뉴스 소스 통합
최대한 많은 뉴스를 수집하여 AI 분석용 데이터 생성
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from loguru import logger
import time
import re
import urllib.parse


class DaumNewsScraper:
    """다음 뉴스 스크래퍼"""

    BASE_URL = "https://search.daum.net/search"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    def __init__(self, delay: float = 0.5):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def search(self, query: str, max_results: int = 20) -> List[Dict]:
        """다음 뉴스 검색"""
        try:
            params = {
                "w": "news",
                "q": query,
                "period": "a",  # 전체 기간
            }

            response = self.session.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            time.sleep(self.delay)

            soup = BeautifulSoup(response.text, "html.parser")
            articles = soup.select(".c-list-basic li")

            results = []
            for article in articles[:max_results]:
                title_tag = article.select_one(".tit-g")
                desc_tag = article.select_one(".desc")
                source_tag = article.select_one(".txt-info")
                date_tag = article.select_one(".gem-subinfo")

                if title_tag:
                    link = title_tag.get("href", "")
                    results.append({
                        "title": title_tag.text.strip(),
                        "description": desc_tag.text.strip() if desc_tag else "",
                        "link": link,
                        "source": "다음 - " + source_tag.text.strip() if source_tag else "다음",
                        "published": date_tag.text.strip() if date_tag else "",
                    })

            logger.info(f"다음 뉴스 검색 완료: '{query}' - {len(results)}개")
            return results

        except Exception as e:
            logger.error(f"다음 뉴스 검색 실패: {e}")
            return []


class EconomyNewsScraper:
    """경제 신문 스크래퍼 (매일경제, 한국경제, 서울경제)"""

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def get_maeil_news(self, keyword: str = "증시") -> List[Dict]:
        """매일경제 뉴스"""
        try:
            url = f"https://www.mk.co.kr/news/search/?keyword={urllib.parse.quote(keyword)}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            time.sleep(self.delay)

            soup = BeautifulSoup(response.text, "html.parser")
            articles = soup.select(".news_list li")

            results = []
            for article in articles[:20]:
                title_tag = article.select_one(".news_ttl a")
                desc_tag = article.select_one(".news_txt")
                date_tag = article.select_one(".news_date")

                if title_tag:
                    results.append({
                        "title": title_tag.text.strip(),
                        "description": desc_tag.text.strip() if desc_tag else "",
                        "link": title_tag.get("href", ""),
                        "source": "매일경제",
                        "published": date_tag.text.strip() if date_tag else "",
                    })

            logger.info(f"매일경제 뉴스 수집 완료: {len(results)}개")
            return results

        except Exception as e:
            logger.error(f"매일경제 뉴스 수집 실패: {e}")
            return []

    def get_hankyung_news(self, keyword: str = "증시") -> List[Dict]:
        """한국경제 뉴스"""
        try:
            url = f"https://www.hankyung.com/search?query={urllib.parse.quote(keyword)}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            time.sleep(self.delay)

            soup = BeautifulSoup(response.text, "html.parser")
            articles = soup.select(".news-list article")

            results = []
            for article in articles[:20]:
                title_tag = article.select_one("h3 a")
                desc_tag = article.select_one(".txt")
                date_tag = article.select_one(".date")

                if title_tag:
                    results.append({
                        "title": title_tag.text.strip(),
                        "description": desc_tag.text.strip() if desc_tag else "",
                        "link": "https://www.hankyung.com" + title_tag.get("href", ""),
                        "source": "한국경제",
                        "published": date_tag.text.strip() if date_tag else "",
                    })

            logger.info(f"한국경제 뉴스 수집 완료: {len(results)}개")
            return results

        except Exception as e:
            logger.error(f"한국경제 뉴스 수집 실패: {e}")
            return []

    def get_sedaily_news(self, keyword: str = "증시") -> List[Dict]:
        """서울경제 뉴스"""
        try:
            url = f"https://www.sedaily.com/Search?searchWord={urllib.parse.quote(keyword)}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            time.sleep(self.delay)

            soup = BeautifulSoup(response.text, "html.parser")
            articles = soup.select(".article_list li")

            results = []
            for article in articles[:20]:
                title_tag = article.select_one(".tit a")
                desc_tag = article.select_one(".subtit")
                date_tag = article.select_one(".date")

                if title_tag:
                    results.append({
                        "title": title_tag.text.strip(),
                        "description": desc_tag.text.strip() if desc_tag else "",
                        "link": "https://www.sedaily.com" + title_tag.get("href", ""),
                        "source": "서울경제",
                        "published": date_tag.text.strip() if date_tag else "",
                    })

            logger.info(f"서울경제 뉴스 수집 완료: {len(results)}개")
            return results

        except Exception as e:
            logger.error(f"서울경제 뉴스 수집 실패: {e}")
            return []


class YonhapNewsScraper:
    """연합뉴스 스크래퍼"""

    BASE_URL = "https://www.yna.co.kr"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def get_economy_news(self) -> List[Dict]:
        """연합뉴스 경제 섹션"""
        try:
            url = f"{self.BASE_URL}/economy/all"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            time.sleep(self.delay)

            soup = BeautifulSoup(response.text, "html.parser")
            articles = soup.select(".list-type038 li")

            results = []
            for article in articles[:30]:
                title_tag = article.select_one(".tit-wrap a")
                desc_tag = article.select_one(".lead")
                date_tag = article.select_one(".txt-time")

                if title_tag:
                    href = title_tag.get("href", "")
                    full_link = href if href.startswith("http") else f"{self.BASE_URL}{href}"

                    results.append({
                        "title": title_tag.text.strip(),
                        "description": desc_tag.text.strip() if desc_tag else "",
                        "link": full_link,
                        "source": "연합뉴스",
                        "published": date_tag.text.strip() if date_tag else "",
                    })

            logger.info(f"연합뉴스 경제 뉴스 수집 완료: {len(results)}개")
            return results

        except Exception as e:
            logger.error(f"연합뉴스 수집 실패: {e}")
            return []

    def search(self, query: str, max_results: int = 20) -> List[Dict]:
        """연합뉴스 검색"""
        try:
            url = f"{self.BASE_URL}/search?query={urllib.parse.quote(query)}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            time.sleep(self.delay)

            soup = BeautifulSoup(response.text, "html.parser")
            articles = soup.select(".list li")

            results = []
            for article in articles[:max_results]:
                title_tag = article.select_one("a")

                if title_tag:
                    results.append({
                        "title": title_tag.text.strip(),
                        "link": title_tag.get("href", ""),
                        "source": "연합뉴스",
                    })

            logger.info(f"연합뉴스 검색 완료: '{query}' - {len(results)}개")
            return results

        except Exception as e:
            logger.error(f"연합뉴스 검색 실패: {e}")
            return []


class ComprehensiveNewsScraper:
    """모든 뉴스 소스 통합 스크래퍼"""

    def __init__(
        self,
        naver_client_id: Optional[str] = None,
        naver_client_secret: Optional[str] = None,
    ):
        from .news_scraper import GoogleNewsRSS, NaverNewsAPI, NaverFinanceNewsScraper

        self.google = GoogleNewsRSS(lang="ko", country="KR")
        self.daum = DaumNewsScraper()
        self.economy = EconomyNewsScraper()
        self.yonhap = YonhapNewsScraper()
        self.naver_finance = NaverFinanceNewsScraper()

        self.naver_api = None
        if naver_client_id and naver_client_secret:
            self.naver_api = NaverNewsAPI(naver_client_id, naver_client_secret)

    def collect_all_news(self, keyword: str) -> Dict[str, List[Dict]]:
        """모든 소스에서 뉴스 수집"""
        logger.info(f"=== 전체 뉴스 수집 시작: '{keyword}' ===")

        results = {
            "keyword": keyword,
            "collected_at": datetime.now().isoformat(),
            "sources": {}
        }

        # 1. 구글 뉴스
        results["sources"]["google"] = self.google.search(keyword, max_results=30)

        # 2. 다음 뉴스
        results["sources"]["daum"] = self.daum.search(keyword, max_results=30)

        # 3. 네이버 API (있는 경우)
        if self.naver_api:
            results["sources"]["naver_api"] = self.naver_api.search(keyword, display=30)

        # 4. 네이버 금융
        results["sources"]["naver_finance"] = self.naver_finance.get_market_news("stock")

        # 5. 연합뉴스
        results["sources"]["yonhap"] = self.yonhap.search(keyword, max_results=30)

        # 6. 경제 신문들
        results["sources"]["maeil"] = self.economy.get_maeil_news(keyword)
        results["sources"]["hankyung"] = self.economy.get_hankyung_news(keyword)
        results["sources"]["sedaily"] = self.economy.get_sedaily_news(keyword)

        # 통계
        total_count = sum(len(news) for news in results["sources"].values())
        logger.info(f"=== 전체 뉴스 수집 완료: 총 {total_count}개 ===")

        for source, news_list in results["sources"].items():
            logger.info(f"  {source}: {len(news_list)}개")

        return results

    def collect_stock_news(self, ticker: str, stock_name: str) -> Dict[str, List[Dict]]:
        """특정 종목 뉴스 수집"""
        logger.info(f"=== 종목 뉴스 수집: {stock_name}({ticker}) ===")

        results = {
            "ticker": ticker,
            "stock_name": stock_name,
            "collected_at": datetime.now().isoformat(),
            "sources": {}
        }

        # 종목명으로 검색
        query = f"{stock_name} 주식"

        results["sources"]["google"] = self.google.search(query, max_results=20)
        results["sources"]["daum"] = self.daum.search(query, max_results=20)

        if self.naver_api:
            results["sources"]["naver_api"] = self.naver_api.search(query, display=20)

        # 네이버 금융 종목 뉴스
        results["sources"]["naver_finance"] = self.naver_finance.get_stock_news(ticker)

        results["sources"]["yonhap"] = self.yonhap.search(stock_name, max_results=20)

        total_count = sum(len(news) for news in results["sources"].values())
        logger.info(f"=== 종목 뉴스 수집 완료: 총 {total_count}개 ===")

        return results

    def collect_market_news(self) -> Dict[str, List[Dict]]:
        """시장 전체 뉴스 수집"""
        logger.info("=== 시장 뉴스 수집 시작 ===")

        results = {
            "collected_at": datetime.now().isoformat(),
            "sources": {}
        }

        # 주요 키워드
        keywords = ["코스피", "코스닥", "증시", "주식시장"]

        for keyword in keywords:
            results["sources"][f"google_{keyword}"] = self.google.search(keyword, max_results=15)
            results["sources"][f"daum_{keyword}"] = self.daum.search(keyword, max_results=15)

        # 연합뉴스 경제
        results["sources"]["yonhap_economy"] = self.yonhap.get_economy_news()

        # 경제 신문
        results["sources"]["maeil"] = self.economy.get_maeil_news("증시")
        results["sources"]["hankyung"] = self.economy.get_hankyung_news("증시")
        results["sources"]["sedaily"] = self.economy.get_sedaily_news("증시")

        # 네이버 금융
        results["sources"]["naver_main"] = self.naver_finance.get_market_news("main")
        results["sources"]["naver_stock"] = self.naver_finance.get_market_news("stock")
        results["sources"]["naver_economy"] = self.naver_finance.get_market_news("economy")

        total_count = sum(len(news) for news in results["sources"].values())
        logger.info(f"=== 시장 뉴스 수집 완료: 총 {total_count}개 ===")

        return results
