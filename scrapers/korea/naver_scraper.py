"""
네이버 금융 스크래퍼
실시간 주가, 종목 정보, 투자자별 매매동향 등 수집
"""
import requests
from bs4 import BeautifulSoup
import pandas as pd
from typing import Dict, List, Optional
from loguru import logger
import time
import re


class NaverFinanceScraper:
    """네이버 금융 스크래퍼"""

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

    def get_realtime_price(self, ticker: str) -> Dict:
        """
        실시간 주가 정보 조회

        Args:
            ticker: 종목 코드

        Returns:
            실시간 가격 정보 딕셔너리
        """
        url = f"{self.BASE_URL}/item/main.naver?code={ticker}"
        soup = self._get_soup(url)

        if not soup:
            return {}

        try:
            result = {"ticker": ticker}

            # 종목명
            name_tag = soup.select_one(".wrap_company h2 a")
            result["name"] = name_tag.text.strip() if name_tag else ""

            # 현재가
            price_tag = soup.select_one(".no_today .blind")
            if price_tag:
                result["current_price"] = int(price_tag.text.replace(",", ""))

            # 전일 대비
            change_tag = soup.select_one(".no_exday .blind")
            if change_tag:
                change_text = change_tag.text.replace(",", "")
                # 상승/하락 확인
                is_up = soup.select_one(".no_exday .ico.up") is not None
                change_val = int(change_text) if change_text.isdigit() else 0
                result["change"] = change_val if is_up else -change_val

            # 등락률
            rate_tag = soup.select_one(".no_exday em span.blind")
            if rate_tag:
                rate_text = rate_tag.text.replace("%", "").strip()
                try:
                    result["change_rate"] = float(rate_text)
                except ValueError:
                    result["change_rate"] = 0.0

            # 거래량
            volume_items = soup.select(".no_info tr td")
            for item in volume_items:
                text = item.get_text(strip=True)
                if "거래량" in str(item.find_previous("th")):
                    result["volume"] = int(text.replace(",", ""))
                    break

            # 시가, 고가, 저가, 상한가, 하한가
            table = soup.select_one(".tab_con1 table")
            if table:
                rows = table.select("tr")
                for row in rows:
                    th = row.select_one("th")
                    td = row.select_one("td .blind")
                    if th and td:
                        label = th.text.strip()
                        value = td.text.replace(",", "")
                        if label == "시가":
                            result["open"] = int(value)
                        elif label == "고가":
                            result["high"] = int(value)
                        elif label == "저가":
                            result["low"] = int(value)

            logger.info(f"{ticker} 실시간 가격 조회 완료")
            return result

        except Exception as e:
            logger.error(f"{ticker} 실시간 가격 파싱 실패: {e}")
            return {}

    def get_stock_info(self, ticker: str) -> Dict:
        """
        종목 기본 정보 조회 (시가총액, 상장주식수, PER, EPS 등)

        Args:
            ticker: 종목 코드

        Returns:
            종목 정보 딕셔너리
        """
        url = f"{self.BASE_URL}/item/main.naver?code={ticker}"
        soup = self._get_soup(url)

        if not soup:
            return {}

        try:
            result = {"ticker": ticker}

            # 종목 개요 테이블
            tables = soup.select(".aside_invest_info table")
            for table in tables:
                rows = table.select("tr")
                for row in rows:
                    ths = row.select("th")
                    tds = row.select("td")
                    for th, td in zip(ths, tds):
                        label = th.text.strip()
                        value = td.text.strip().replace(",", "").replace("원", "")

                        if "시가총액" in label:
                            # 억 단위로 저장
                            result["market_cap"] = value
                        elif "상장주식수" in label:
                            result["shares"] = value
                        elif "PER" in label:
                            try:
                                result["per"] = float(value.replace("배", ""))
                            except ValueError:
                                result["per"] = None
                        elif "EPS" in label:
                            try:
                                result["eps"] = int(value)
                            except ValueError:
                                result["eps"] = None
                        elif "PBR" in label:
                            try:
                                result["pbr"] = float(value.replace("배", ""))
                            except ValueError:
                                result["pbr"] = None
                        elif "BPS" in label:
                            try:
                                result["bps"] = int(value)
                            except ValueError:
                                result["bps"] = None

            logger.info(f"{ticker} 종목 정보 조회 완료")
            return result

        except Exception as e:
            logger.error(f"{ticker} 종목 정보 파싱 실패: {e}")
            return {}

    def get_investor_trading(self, ticker: str) -> Dict:
        """
        투자자별 매매동향 조회

        Args:
            ticker: 종목 코드

        Returns:
            투자자별 매매동향 딕셔너리
        """
        url = f"{self.BASE_URL}/item/frgn.naver?code={ticker}"
        soup = self._get_soup(url)

        if not soup:
            return {}

        try:
            result = {"ticker": ticker, "investors": []}

            table = soup.select_one(".type2 table")
            if table:
                rows = table.select("tbody tr")
                for row in rows[:5]:  # 최근 5일
                    cols = row.select("td")
                    if len(cols) >= 6:
                        date = cols[0].text.strip()
                        foreign_buy = cols[4].text.strip().replace(",", "")
                        inst_buy = cols[5].text.strip().replace(",", "")

                        result["investors"].append(
                            {
                                "date": date,
                                "foreign_net": int(foreign_buy) if foreign_buy else 0,
                                "institution_net": int(inst_buy) if inst_buy else 0,
                            }
                        )

            logger.info(f"{ticker} 투자자별 매매동향 조회 완료")
            return result

        except Exception as e:
            logger.error(f"{ticker} 투자자별 매매동향 파싱 실패: {e}")
            return {}

    def get_top_stocks(self, market: str = "KOSPI", category: str = "rise") -> List[Dict]:
        """
        상승/하락/거래량 상위 종목 조회

        Args:
            market: "KOSPI" or "KOSDAQ"
            category: "rise" (상승), "fall" (하락), "volume" (거래량)

        Returns:
            상위 종목 리스트
        """
        sosok = "0" if market == "KOSPI" else "1"

        if category == "rise":
            url = f"{self.BASE_URL}/sise/sise_rise.naver?sosok={sosok}"
        elif category == "fall":
            url = f"{self.BASE_URL}/sise/sise_fall.naver?sosok={sosok}"
        else:
            url = f"{self.BASE_URL}/sise/sise_quant.naver?sosok={sosok}"

        soup = self._get_soup(url)
        if not soup:
            return []

        try:
            results = []
            table = soup.select_one(".type_2 table")
            if table:
                rows = table.select("tbody tr")
                for row in rows[:20]:  # 상위 20개
                    cols = row.select("td")
                    if len(cols) >= 10:
                        link = cols[1].select_one("a")
                        if link:
                            href = link.get("href", "")
                            ticker_match = re.search(r"code=(\d+)", href)
                            if ticker_match:
                                results.append(
                                    {
                                        "rank": len(results) + 1,
                                        "ticker": ticker_match.group(1),
                                        "name": link.text.strip(),
                                        "current_price": cols[2].text.strip().replace(",", ""),
                                        "change": cols[3].text.strip().replace(",", ""),
                                        "change_rate": cols[4].text.strip(),
                                        "volume": cols[5].text.strip().replace(",", ""),
                                    }
                                )

            logger.info(f"{market} {category} 상위 종목 조회 완료: {len(results)}개")
            return results

        except Exception as e:
            logger.error(f"상위 종목 파싱 실패: {e}")
            return []

    def get_market_index(self) -> Dict:
        """
        KOSPI/KOSDAQ 지수 조회

        Returns:
            시장 지수 딕셔너리
        """
        url = f"{self.BASE_URL}/sise/sise_index.naver?code=KOSPI"
        soup = self._get_soup(url)

        result = {}

        if soup:
            try:
                # KOSPI
                kospi_price = soup.select_one("#now_value")
                if kospi_price:
                    result["kospi"] = {
                        "value": float(kospi_price.text.replace(",", "")),
                        "change": soup.select_one("#change_value_and_rate").text.strip()
                        if soup.select_one("#change_value_and_rate")
                        else "",
                    }
            except Exception as e:
                logger.error(f"KOSPI 지수 파싱 실패: {e}")

        # KOSDAQ
        url = f"{self.BASE_URL}/sise/sise_index.naver?code=KOSDAQ"
        soup = self._get_soup(url)

        if soup:
            try:
                kosdaq_price = soup.select_one("#now_value")
                if kosdaq_price:
                    result["kosdaq"] = {
                        "value": float(kosdaq_price.text.replace(",", "")),
                        "change": soup.select_one("#change_value_and_rate").text.strip()
                        if soup.select_one("#change_value_and_rate")
                        else "",
                    }
            except Exception as e:
                logger.error(f"KOSDAQ 지수 파싱 실패: {e}")

        return result
