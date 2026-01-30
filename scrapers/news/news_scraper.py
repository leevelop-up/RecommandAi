"""
뉴스 스크래퍼
주식 관련 뉴스 수집 (네이버 뉴스 API, 구글 뉴스 RSS, 웹 스크래핑)
"""
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from loguru import logger
import time
import re
import urllib.parse


class GoogleNewsRSS:
    """구글 뉴스 RSS 스크래퍼 (API 키 불필요)"""

    BASE_URL = "https://news.google.com/rss/search"

    def __init__(self, lang: str = "ko", country: str = "KR"):
        self.lang = lang
        self.country = country

    def search(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        구글 뉴스 RSS 검색

        Args:
            query: 검색어
            max_results: 최대 결과 개수

        Returns:
            뉴스 리스트
        """
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"{self.BASE_URL}?q={encoded_query}&hl={self.lang}&gl={self.country}&ceid={self.country}:{self.lang}"

            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "lxml-xml")
            items = soup.find_all("item")

            results = []
            for item in items[:max_results]:
                title = item.find("title")
                link = item.find("link")
                pub_date = item.find("pubDate")
                source = item.find("source")

                results.append({
                    "title": title.text if title else "",
                    "link": link.text if link else "",
                    "published": pub_date.text if pub_date else "",
                    "source": source.text if source else "",
                })

            logger.info(f"구글 뉴스 검색 완료: '{query}' - {len(results)}개")
            return results

        except Exception as e:
            logger.error(f"구글 뉴스 검색 실패: {e}")
            return []


class NaverNewsAPI:
    """네이버 뉴스 검색 API"""

    BASE_URL = "https://openapi.naver.com/v1/search/news.json"

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret

    def search(
        self,
        query: str,
        display: int = 20,
        start: int = 1,
        sort: str = "date",
    ) -> List[Dict]:
        """
        뉴스 검색

        Args:
            query: 검색어
            display: 결과 개수 (최대 100)
            start: 시작 위치
            sort: 정렬 (date: 날짜순, sim: 관련도순)

        Returns:
            뉴스 리스트
        """
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }

        params = {
            "query": query,
            "display": display,
            "start": start,
            "sort": sort,
        }

        try:
            response = requests.get(self.BASE_URL, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("items", []):
                # HTML 태그 제거
                title = re.sub(r"<[^>]+>", "", item.get("title", ""))
                description = re.sub(r"<[^>]+>", "", item.get("description", ""))

                results.append({
                    "title": title,
                    "description": description,
                    "link": item.get("originallink", item.get("link", "")),
                    "pub_date": item.get("pubDate", ""),
                    "source": self._extract_source(item.get("originallink", "")),
                })

            logger.info(f"네이버 뉴스 검색 완료: '{query}' - {len(results)}개")
            return results

        except Exception as e:
            logger.error(f"네이버 뉴스 검색 실패: {e}")
            return []

    def _extract_source(self, url: str) -> str:
        """URL에서 뉴스 소스 추출"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            return domain
        except Exception:
            return ""


class NaverFinanceNewsScraper:
    """네이버 금융 뉴스 스크래퍼"""

    BASE_URL = "https://finance.naver.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def _get_soup(self, url: str) -> Optional[BeautifulSoup]:
        """URL에서 BeautifulSoup 객체 반환"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            time.sleep(self.delay)
            return BeautifulSoup(response.text, "html.parser")
        except Exception as e:
            logger.error(f"페이지 요청 실패: {url}, {e}")
            return None

    def get_stock_news(self, ticker: str, page: int = 1) -> List[Dict]:
        """
        종목 관련 뉴스 조회

        Args:
            ticker: 종목 코드
            page: 페이지 번호

        Returns:
            뉴스 리스트
        """
        url = f"{self.BASE_URL}/item/news_news.naver?code={ticker}&page={page}"
        soup = self._get_soup(url)

        if not soup:
            return []

        try:
            results = []
            table = soup.select_one(".type5 tbody")
            if table:
                rows = table.select("tr")
                for row in rows:
                    title_tag = row.select_one(".title a")
                    info_tag = row.select_one(".info")
                    date_tag = row.select_one(".date")

                    if title_tag:
                        # 뉴스 상세 링크에서 article_id 추출
                        href = title_tag.get("href", "")
                        article_match = re.search(r"article_id=(\d+)", href)

                        results.append({
                            "title": title_tag.text.strip(),
                            "link": f"{self.BASE_URL}{href}" if href.startswith("/") else href,
                            "source": info_tag.text.strip() if info_tag else "",
                            "date": date_tag.text.strip() if date_tag else "",
                            "article_id": article_match.group(1) if article_match else "",
                        })

            logger.info(f"{ticker} 종목 뉴스 조회 완료: {len(results)}개")
            return results

        except Exception as e:
            logger.error(f"{ticker} 종목 뉴스 파싱 실패: {e}")
            return []

    def get_market_news(self, category: str = "main") -> List[Dict]:
        """
        시장 뉴스 조회

        Args:
            category: "main" (메인), "stock" (증권), "economy" (경제)

        Returns:
            뉴스 리스트
        """
        if category == "main":
            url = f"{self.BASE_URL}/news/mainnews.naver"
        elif category == "stock":
            url = f"{self.BASE_URL}/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258"
        else:
            url = f"{self.BASE_URL}/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=259"

        soup = self._get_soup(url)
        if not soup:
            return []

        try:
            results = []
            articles = soup.select(".newsList li") or soup.select(".mainNewsList li")

            for article in articles[:20]:
                title_tag = article.select_one("a")
                if title_tag:
                    results.append({
                        "title": title_tag.text.strip(),
                        "link": title_tag.get("href", ""),
                    })

            logger.info(f"시장 뉴스 조회 완료: {len(results)}개")
            return results

        except Exception as e:
            logger.error(f"시장 뉴스 파싱 실패: {e}")
            return []

    def get_disclosure(self, ticker: str) -> List[Dict]:
        """
        공시 정보 조회

        Args:
            ticker: 종목 코드

        Returns:
            공시 리스트
        """
        url = f"{self.BASE_URL}/item/news.naver?code={ticker}"
        soup = self._get_soup(url)

        if not soup:
            return []

        try:
            results = []
            # 공시 탭의 내용
            disclosure_table = soup.select_one(".tb_cont tbody")
            if disclosure_table:
                rows = disclosure_table.select("tr")
                for row in rows[:10]:
                    cols = row.select("td")
                    if len(cols) >= 3:
                        title_tag = cols[0].select_one("a")
                        if title_tag:
                            results.append({
                                "title": title_tag.text.strip(),
                                "link": title_tag.get("href", ""),
                                "date": cols[1].text.strip() if len(cols) > 1 else "",
                                "source": cols[2].text.strip() if len(cols) > 2 else "",
                            })

            logger.info(f"{ticker} 공시 조회 완료: {len(results)}개")
            return results

        except Exception as e:
            logger.error(f"{ticker} 공시 파싱 실패: {e}")
            return []


class StockNewsScraper:
    """통합 주식 뉴스 스크래퍼"""

    def __init__(
        self,
        naver_client_id: Optional[str] = None,
        naver_client_secret: Optional[str] = None,
        delay: float = 1.0,
    ):
        self.finance_scraper = NaverFinanceNewsScraper(delay=delay)
        self.naver_api = None

        if naver_client_id and naver_client_secret:
            self.naver_api = NaverNewsAPI(naver_client_id, naver_client_secret)

    def get_stock_news(self, ticker: str, stock_name: str = "") -> Dict:
        """
        종목 관련 모든 뉴스 수집

        Args:
            ticker: 종목 코드
            stock_name: 종목명 (API 검색용)

        Returns:
            뉴스 데이터 딕셔너리
        """
        result = {
            "ticker": ticker,
            "finance_news": self.finance_scraper.get_stock_news(ticker),
            "api_news": [],
            "updated_at": datetime.now().isoformat(),
        }

        # 네이버 API 검색 (종목명이 있는 경우)
        if self.naver_api and stock_name:
            result["api_news"] = self.naver_api.search(f"{stock_name} 주식")

        return result

    def get_market_summary_news(self) -> Dict:
        """
        시장 전체 뉴스 요약

        Returns:
            시장 뉴스 딕셔너리
        """
        result = {
            "main_news": self.finance_scraper.get_market_news("main"),
            "stock_news": self.finance_scraper.get_market_news("stock"),
            "economy_news": self.finance_scraper.get_market_news("economy"),
            "updated_at": datetime.now().isoformat(),
        }

        # API로 추가 검색
        if self.naver_api:
            result["kospi_news"] = self.naver_api.search("코스피", display=10)
            result["kosdaq_news"] = self.naver_api.search("코스닥", display=10)

        return result

    def search_news(self, keyword: str, count: int = 20) -> List[Dict]:
        """
        키워드로 뉴스 검색

        Args:
            keyword: 검색 키워드
            count: 결과 개수

        Returns:
            뉴스 리스트
        """
        if self.naver_api:
            return self.naver_api.search(keyword, display=count)
        return []
