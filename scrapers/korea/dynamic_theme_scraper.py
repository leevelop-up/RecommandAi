"""
동적 테마/관련주 스크래퍼
네이버 금융에서 실시간으로 테마 및 관련주를 수집 (하드코딩 없음)
"""
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple
from loguru import logger
import time
import re
from collections import defaultdict


class DynamicThemeScraper:
    """동적 테마/관련주 스크래퍼 - 하드코딩 없이 실시간 데이터 수집"""

    BASE_URL = "https://finance.naver.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    def __init__(self, delay: float = 0.3):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self._theme_cache = {}  # 테마 목록 캐시
        self._stock_themes = defaultdict(list)  # 종목별 소속 테마

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

    def get_all_themes(self, pages: int = None, max_pages: int = 50) -> List[Dict]:
        """
        전체 테마 목록 조회 (여러 페이지)

        Args:
            pages: 조회할 페이지 수 (None이면 자동으로 모든 페이지 크롤링)
            max_pages: 최대 페이지 수 제한 (무한 루프 방지)

        Returns:
            테마 목록
        """
        all_themes = []
        seen_codes = set()
        page = 1

        # pages가 지정되지 않으면 자동으로 모든 페이지 크롤링
        if pages is None:
            logger.info("모든 테마 페이지 자동 크롤링 시작...")
            while page <= max_pages:
                url = f"{self.BASE_URL}/sise/theme.naver?&page={page}"
                soup = self._get_soup(url)

                if not soup:
                    break

                try:
                    links = soup.select('td a[href*="type=theme"]')

                    # 더 이상 테마가 없으면 종료
                    if not links:
                        logger.info(f"페이지 {page}에서 테마 없음 - 크롤링 종료")
                        break

                    page_themes = []
                    new_count = 0
                    for link in links:
                        href = link.get("href", "")
                        code_match = re.search(r"no=(\d+)", href)
                        if code_match:
                            theme_name = link.text.strip()
                            theme_code = code_match.group(1)

                            # 등락률 찾기
                            parent_td = link.find_parent("td")
                            if parent_td:
                                next_tds = parent_td.find_next_siblings("td")
                                change_rate = next_tds[1].text.strip() if len(next_tds) > 1 else ""
                            else:
                                change_rate = ""

                            page_themes.append({
                                "name": theme_name,
                                "code": theme_code,
                                "change_rate": change_rate,
                            })
                            if theme_code not in seen_codes:
                                new_count += 1

                    # 이 페이지의 모든 테마가 이미 수집됐으면 루프 종료 (페이지 반복 감지)
                    if page_themes and new_count == 0:
                        logger.info(f"페이지 {page}: 새 테마 없음 - 크롤링 종료 (중복 페이지)")
                        break

                    if page_themes:
                        for t in page_themes:
                            if t["code"] not in seen_codes:
                                seen_codes.add(t["code"])
                                all_themes.append(t)
                        logger.info(f"페이지 {page}: {new_count}개 신규 테마 수집 (누적: {len(all_themes)}개)")
                    else:
                        break

                    page += 1

                except Exception as e:
                    logger.error(f"테마 목록 파싱 실패 (page {page}): {e}")
                    break
        else:
            # 지정된 페이지 수만큼만 크롤링
            for page in range(1, pages + 1):
                url = f"{self.BASE_URL}/sise/theme.naver?&page={page}"
                soup = self._get_soup(url)

                if not soup:
                    continue

                try:
                    links = soup.select('td a[href*="type=theme"]')
                    new_count = 0
                    for link in links:
                        href = link.get("href", "")
                        code_match = re.search(r"no=(\d+)", href)
                        if code_match:
                            theme_name = link.text.strip()
                            theme_code = code_match.group(1)

                            if theme_code in seen_codes:
                                continue
                            seen_codes.add(theme_code)
                            new_count += 1

                            # 등락률 찾기
                            parent_td = link.find_parent("td")
                            if parent_td:
                                next_tds = parent_td.find_next_siblings("td")
                                change_rate = next_tds[1].text.strip() if len(next_tds) > 1 else ""
                            else:
                                change_rate = ""

                            all_themes.append({
                                "name": theme_name,
                                "code": theme_code,
                                "change_rate": change_rate,
                            })

                    if new_count == 0:
                        logger.info(f"페이지 {page}: 새 테마 없음 - 크롤링 종료")
                        break

                except Exception as e:
                    logger.error(f"테마 목록 파싱 실패 (page {page}): {e}")

        # 캐시에 저장
        for theme in all_themes:
            self._theme_cache[theme["name"]] = theme["code"]
            self._theme_cache[theme["code"]] = theme["name"]

        logger.info(f"전체 테마 조회 완료: {len(all_themes)}개")
        return all_themes

    def get_theme_stocks(self, theme_code: str) -> List[Dict]:
        """
        특정 테마의 종목 조회

        Args:
            theme_code: 테마 코드

        Returns:
            종목 리스트
        """
        url = f"{self.BASE_URL}/sise/sise_group_detail.naver?type=theme&no={theme_code}"
        soup = self._get_soup(url)

        if not soup:
            return []

        stocks = []
        try:
            # 테마명 추출
            theme_name = ""
            title = soup.select_one(".sub_tlt")
            if title:
                theme_name = title.text.strip()

            # 종목 테이블
            rows = soup.select("table.type_5 tbody tr")
            for row in rows:
                cols = row.select("td")
                if len(cols) >= 6:
                    link = cols[0].select_one("a")
                    if link:
                        href = link.get("href", "")
                        ticker_match = re.search(r"code=(\d+)", href)
                        if ticker_match:
                            # KRX 종목코드는 6자리 — 짧으면 zero-pad
                            ticker = ticker_match.group(1).zfill(6)
                            name = link.text.strip()

                            # 현재가
                            price_text = re.sub(r"[^\d]", "", cols[1].text)
                            price = int(price_text) if price_text else 0

                            # 전일비 — "상승\n3,650" / "하락\n650" → 숫자만 추출
                            change_raw = cols[2].text.strip()
                            change_nums = re.findall(r"[\d,]+", change_raw)
                            change_text = change_nums[0].replace(",", "") if change_nums else "0"
                            # 부호 판별 (하락이면 음수)
                            if "하락" in change_raw or "▼" in change_raw:
                                change_text = "-" + change_text

                            # 등락률 — 공백/개행 제거 후 숫자+부호+% 만 남김
                            rate_raw = cols[3].text.strip()
                            rate_match = re.search(r"[-+]?\d+\.?\d*", rate_raw)
                            rate_text = (rate_match.group(0) + "%") if rate_match else "0%"
                            if ("하락" in rate_raw or "▼" in rate_raw) and not rate_text.startswith("-"):
                                rate_text = "-" + rate_text

                            stocks.append({
                                "ticker": ticker,
                                "name": name,
                                "price": price,
                                "change": change_text,
                                "change_rate": rate_text,
                                "theme": theme_name,
                            })

                            # 종목별 테마 매핑
                            self._stock_themes[ticker].append({
                                "code": theme_code,
                                "name": theme_name,
                            })

            logger.info(f"테마 '{theme_name}' 종목 조회 완료: {len(stocks)}개")
            return stocks

        except Exception as e:
            logger.error(f"테마 종목 파싱 실패: {e}")
            return []

    def search_theme(self, keyword: str) -> List[Dict]:
        """
        키워드로 테마 검색

        Args:
            keyword: 검색 키워드

        Returns:
            매칭되는 테마 리스트
        """
        # 캐시가 비어있으면 전체 테마 조회
        if not self._theme_cache:
            self.get_all_themes()

        matched = []
        themes = self.get_all_themes(pages=10)

        for theme in themes:
            if keyword.lower() in theme["name"].lower():
                matched.append(theme)

        logger.info(f"테마 검색 '{keyword}': {len(matched)}개 매칭")
        return matched

    def get_stock_themes(self, ticker: str) -> List[Dict]:
        """
        특정 종목이 속한 테마 조회

        Args:
            ticker: 종목 코드

        Returns:
            테마 리스트
        """
        url = f"{self.BASE_URL}/item/main.naver?code={ticker}"
        soup = self._get_soup(url)

        if not soup:
            return []

        themes = []
        try:
            # 테마 정보 찾기 (종목 페이지에서)
            theme_area = soup.select_one(".theme")
            if theme_area:
                theme_links = theme_area.select("a")
                for link in theme_links:
                    href = link.get("href", "")
                    code_match = re.search(r"no=(\d+)", href)
                    if code_match:
                        themes.append({
                            "name": link.text.strip(),
                            "code": code_match.group(1),
                        })

            # 테마를 찾지 못하면 전체 테마에서 검색
            if not themes:
                all_themes = self.get_all_themes(pages=3)
                for theme in all_themes[:30]:  # 상위 30개 테마만 검색
                    stocks = self.get_theme_stocks(theme["code"])
                    for stock in stocks:
                        if stock["ticker"] == ticker:
                            themes.append({
                                "name": theme["name"],
                                "code": theme["code"],
                            })
                            break

            logger.info(f"{ticker} 소속 테마: {len(themes)}개")
            return themes

        except Exception as e:
            logger.error(f"종목 테마 조회 실패: {e}")
            return []

    def find_related_stocks(self, ticker: str, max_themes: int = 5) -> Dict:
        """
        종목의 관련주 찾기 (동적)
        해당 종목이 속한 테마의 다른 종목들 = 관련주

        Args:
            ticker: 종목 코드
            max_themes: 조회할 최대 테마 수

        Returns:
            관련주 정보
        """
        # 종목 이름 조회
        from scrapers.korea.naver_scraper import NaverFinanceScraper
        naver = NaverFinanceScraper(delay=0.2)
        stock_info = naver.get_realtime_price(ticker)
        stock_name = stock_info.get("name", ticker)

        # 종목이 속한 테마 찾기
        themes = self.get_stock_themes(ticker)

        if not themes:
            # 테마를 찾지 못하면 종목명으로 테마 검색
            matched_themes = self.search_theme(stock_name[:2])  # 첫 2글자로 검색
            themes = matched_themes[:max_themes]

        all_related = {}
        tier1 = []  # 같은 테마에 여러번 등장하는 종목
        tier2 = []  # 같은 테마에 한번 등장하는 종목
        tier3 = []  # 연관 테마 종목

        stock_count = defaultdict(int)

        # 각 테마의 종목 조회
        for i, theme in enumerate(themes[:max_themes]):
            stocks = self.get_theme_stocks(theme["code"])

            for stock in stocks:
                if stock["ticker"] != ticker:  # 자기 자신 제외
                    stock_count[stock["ticker"]] += 1
                    all_related[stock["ticker"]] = {
                        **stock,
                        "themes": all_related.get(stock["ticker"], {}).get("themes", []) + [theme["name"]],
                    }

        # 티어 분류 (등장 횟수 기준)
        for t, count in sorted(stock_count.items(), key=lambda x: -x[1]):
            stock_data = all_related[t]
            if count >= 3:
                tier1.append(stock_data)
            elif count >= 2:
                tier2.append(stock_data)
            else:
                tier3.append(stock_data)

        result = {
            "ticker": ticker,
            "name": stock_name,
            "themes": [t["name"] for t in themes],
            "tier1": tier1[:10],  # 1차 관련주 (핵심) - 최대 10개
            "tier2": tier2[:15],  # 2차 관련주 (주요) - 최대 15개
            "tier3": tier3[:20],  # 3차 관련주 (기타) - 최대 20개
            "total_related": len(all_related),
        }

        logger.info(f"{stock_name}({ticker}) 관련주 찾기 완료: 1차 {len(tier1)}, 2차 {len(tier2)}, 3차 {len(tier3)}")
        return result

    def find_theme_stocks_tiered(self, theme_keyword: str) -> Dict:
        """
        테마 관련주 찾기 (계층별)

        Args:
            theme_keyword: 테마 키워드

        Returns:
            계층별 관련주
        """
        # 테마 검색
        matched_themes = self.search_theme(theme_keyword)

        if not matched_themes:
            logger.warning(f"테마를 찾을 수 없음: {theme_keyword}")
            return {"theme": theme_keyword, "tier1": [], "tier2": [], "tier3": []}

        all_stocks = {}
        stock_count = defaultdict(int)

        # 매칭된 모든 테마의 종목 수집
        for theme in matched_themes[:5]:  # 최대 5개 테마
            stocks = self.get_theme_stocks(theme["code"])
            for stock in stocks:
                stock_count[stock["ticker"]] += 1
                if stock["ticker"] not in all_stocks:
                    all_stocks[stock["ticker"]] = stock
                all_stocks[stock["ticker"]]["themes"] = all_stocks[stock["ticker"]].get("themes", []) + [theme["name"]]

        # 등장 횟수 기준 정렬
        sorted_tickers = sorted(stock_count.keys(), key=lambda x: -stock_count[x])

        # 상위 30% = 1차, 중간 40% = 2차, 나머지 = 3차
        n = len(sorted_tickers)
        tier1_end = max(1, n // 3)
        tier2_end = max(2, 2 * n // 3)

        tier1 = [all_stocks[t] for t in sorted_tickers[:tier1_end]]
        tier2 = [all_stocks[t] for t in sorted_tickers[tier1_end:tier2_end]]
        tier3 = [all_stocks[t] for t in sorted_tickers[tier2_end:]]

        result = {
            "theme": theme_keyword,
            "matched_themes": [t["name"] for t in matched_themes],
            "tier1": tier1,
            "tier2": tier2,
            "tier3": tier3,
            "total": n,
        }

        logger.info(f"테마 '{theme_keyword}' 관련주: 1차 {len(tier1)}, 2차 {len(tier2)}, 3차 {len(tier3)}")
        return result


def print_dynamic_related(data: Dict):
    """동적 관련주 출력"""
    title = data.get("theme") or data.get("name") or data.get("ticker")
    print(f"\n{'='*70}")
    print(f"  📊 [{title}] 관련주 분석 (실시간)")
    print("="*70)

    if data.get("themes"):
        print(f"\n소속 테마: {', '.join(data['themes'][:5])}")

    if data.get("matched_themes"):
        print(f"\n매칭 테마: {', '.join(data['matched_themes'][:5])}")

    for tier_key, tier_label in [
        ("tier1", "🥇 1차 관련주 (핵심)"),
        ("tier2", "🥈 2차 관련주 (주요)"),
        ("tier3", "🥉 3차 관련주 (기타)"),
    ]:
        stocks = data.get(tier_key, [])
        if stocks:
            print(f"\n{tier_label} ({len(stocks)}개)")
            print("-"*70)
            print(f"{'종목':<12} {'현재가':>12} {'등락률':>10} {'테마':>20}")
            print("-"*70)

            for stock in stocks[:10]:  # 각 tier 최대 10개 출력
                name = stock.get("name", "")[:10]
                price = stock.get("price", 0)
                rate = stock.get("change_rate", "")
                themes = ", ".join(stock.get("themes", [])[:2])[:18]

                print(f"{name:<12} {price:>12,}원 {rate:>10} {themes:>20}")


if __name__ == "__main__":
    scraper = DynamicThemeScraper()

    # 1. 전체 테마 목록
    print("="*70)
    print("  📋 전체 테마 목록 (상위 20개)")
    print("="*70)
    themes = scraper.get_all_themes(pages=2)
    for i, theme in enumerate(themes[:20], 1):
        print(f"  {i:2}. {theme['name']:<20} (코드: {theme['code']}) {theme['change_rate']}")

    # 2. 특정 테마 종목
    print("\n" + "="*70)
    print("  🔋 2차전지 테마 종목")
    print("="*70)
    battery_themes = scraper.search_theme("2차전지")
    if battery_themes:
        stocks = scraper.get_theme_stocks(battery_themes[0]["code"])
        for stock in stocks[:10]:
            print(f"  {stock['name']:<12} ({stock['ticker']}) | {stock['price']:>10,}원 | {stock['change_rate']}")

    # 3. 종목 관련주 (삼성전자)
    print("\n" + "="*70)
    print("  🔍 삼성전자(005930) 관련주 찾기")
    print("="*70)
    related = scraper.find_related_stocks("005930", max_themes=3)
    print_dynamic_related(related)
