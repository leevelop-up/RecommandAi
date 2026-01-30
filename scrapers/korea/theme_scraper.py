"""
테마주/관련주 스크래퍼
네이버 금융에서 테마별, 업종별 관련주 수집
"""
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from loguru import logger
import time
import re


class ThemeScraper:
    """테마주/관련주 스크래퍼"""

    BASE_URL = "https://finance.naver.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    # 주요 테마 코드 (네이버 금융 기준)
    THEME_CODES = {
        "2차전지": "467",
        "반도체": "311",
        "AI": "496",
        "자율주행": "305",
        "전기차": "288",
        "바이오": "227",
        "메타버스": "486",
        "로봇": "269",
        "수소": "479",
        "태양광": "234",
        "풍력": "417",
        "반도체장비": "312",
        "디스플레이": "163",
        "5G": "470",
        "클라우드": "482",
        "게임": "146",
        "엔터": "186",
        "화장품": "199",
        "제약": "229",
        "건설": "155",
        "조선": "258",
        "철강": "172",
        "정유": "173",
        "은행": "152",
        "증권": "153",
        "보험": "154",
    }

    def __init__(self, delay: float = 0.5):
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

    def get_theme_list(self) -> List[Dict]:
        """전체 테마 목록 조회"""
        url = f"{self.BASE_URL}/sise/theme.naver"
        soup = self._get_soup(url)

        if not soup:
            return []

        results = []
        try:
            rows = soup.select("table.type_1 tr")
            for row in rows:
                cols = row.select("td")
                if len(cols) >= 4:
                    link = cols[0].select_one("a")
                    if link:
                        href = link.get("href", "")
                        code_match = re.search(r"no=(\d+)", href)
                        if code_match:
                            results.append({
                                "name": link.text.strip(),
                                "code": code_match.group(1),
                                "change_rate": cols[2].text.strip() if len(cols) > 2 else "",
                            })

            logger.info(f"테마 목록 조회 완료: {len(results)}개")
            return results

        except Exception as e:
            logger.error(f"테마 목록 파싱 실패: {e}")
            return []

    def get_theme_stocks(self, theme_code: str) -> List[Dict]:
        """특정 테마의 관련주 조회"""
        url = f"{self.BASE_URL}/sise/sise_group_detail.naver?type=theme&no={theme_code}"
        soup = self._get_soup(url)

        if not soup:
            return []

        results = []
        try:
            rows = soup.select("table.type_5 tr")
            for row in rows:
                cols = row.select("td")
                if len(cols) >= 6:
                    link = cols[0].select_one("a")
                    if link:
                        href = link.get("href", "")
                        ticker_match = re.search(r"code=(\d+)", href)
                        if ticker_match:
                            # 현재가
                            price_text = cols[1].text.strip().replace(",", "")
                            # 등락률
                            change_text = cols[3].text.strip()

                            results.append({
                                "ticker": ticker_match.group(1),
                                "name": link.text.strip(),
                                "price": int(price_text) if price_text.isdigit() else 0,
                                "change_rate": change_text,
                            })

            logger.info(f"테마 관련주 조회 완료: {len(results)}개")
            return results

        except Exception as e:
            logger.error(f"테마 관련주 파싱 실패: {e}")
            return []

    def get_theme_stocks_by_name(self, theme_name: str) -> List[Dict]:
        """테마명으로 관련주 조회"""
        code = self.THEME_CODES.get(theme_name)
        if code:
            return self.get_theme_stocks(code)

        # 코드가 없으면 테마 목록에서 검색
        themes = self.get_theme_list()
        for theme in themes:
            if theme_name in theme["name"]:
                return self.get_theme_stocks(theme["code"])

        logger.warning(f"테마를 찾을 수 없음: {theme_name}")
        return []

    def get_sector_stocks(self, sector: str) -> List[Dict]:
        """업종별 종목 조회"""
        # 업종 코드 매핑
        sector_codes = {
            "반도체": "266",
            "IT": "267",
            "자동차": "261",
            "화학": "260",
            "철강금속": "263",
            "건설": "265",
            "운송": "268",
            "유통": "269",
            "금융": "270",
            "의약품": "271",
            "전기전자": "272",
            "음식료": "273",
            "섬유의복": "274",
            "종이목재": "275",
            "기계": "276",
        }

        code = sector_codes.get(sector)
        if not code:
            logger.warning(f"업종을 찾을 수 없음: {sector}")
            return []

        url = f"{self.BASE_URL}/sise/sise_group_detail.naver?type=upjong&no={code}"
        soup = self._get_soup(url)

        if not soup:
            return []

        results = []
        try:
            rows = soup.select("table.type_5 tr")
            for row in rows:
                cols = row.select("td")
                if len(cols) >= 6:
                    link = cols[0].select_one("a")
                    if link:
                        href = link.get("href", "")
                        ticker_match = re.search(r"code=(\d+)", href)
                        if ticker_match:
                            price_text = cols[1].text.strip().replace(",", "")
                            change_text = cols[3].text.strip()

                            results.append({
                                "ticker": ticker_match.group(1),
                                "name": link.text.strip(),
                                "price": int(price_text) if price_text.isdigit() else 0,
                                "change_rate": change_text,
                            })

            logger.info(f"{sector} 업종 종목 조회 완료: {len(results)}개")
            return results

        except Exception as e:
            logger.error(f"업종 종목 파싱 실패: {e}")
            return []


class RelatedStockFinder:
    """관련주 찾기 - 1차, 2차, 3차 관련주"""

    # 주요 종목별 공급망/관련주 매핑
    SUPPLY_CHAIN = {
        # 삼성전자 공급망
        "005930": {  # 삼성전자
            "name": "삼성전자",
            "tier1": [  # 1차 협력사 (직접 납품)
                ("000660", "SK하이닉스", "반도체 경쟁사"),
                ("006400", "삼성SDI", "배터리"),
                ("009150", "삼성전기", "MLCC/부품"),
                ("028260", "삼성물산", "건설/무역"),
                ("018260", "삼성에스디에스", "IT서비스"),
            ],
            "tier2": [  # 2차 협력사
                ("058470", "리노공업", "반도체 검사장비"),
                ("036930", "주성엔지니어링", "반도체 장비"),
                ("403870", "HPSP", "반도체 소재"),
                ("005290", "동진쎄미켐", "반도체 소재"),
                ("357780", "솔브레인", "반도체 소재"),
            ],
            "tier3": [  # 3차 관련주
                ("950160", "코오롱티슈진", "소재"),
                ("178920", "PI첨단소재", "전자소재"),
                ("025320", "시노펙스", "FPCB"),
            ],
        },
        # SK하이닉스 공급망
        "000660": {  # SK하이닉스
            "name": "SK하이닉스",
            "tier1": [
                ("005930", "삼성전자", "반도체 경쟁사"),
                ("402340", "SK스퀘어", "지주사"),
                ("034730", "SK", "모회사"),
            ],
            "tier2": [
                ("058470", "리노공업", "반도체 검사"),
                ("240810", "원익IPS", "반도체 장비"),
                ("412350", "레이크머티리얼즈", "반도체 소재"),
            ],
            "tier3": [
                ("222670", "한국SGI", "가스공급"),
                ("950170", "JTC", "반도체장비부품"),
            ],
        },
        # 테슬라 관련주 (한국)
        "TSLA": {
            "name": "테슬라",
            "tier1": [
                ("373220", "LG에너지솔루션", "배터리"),
                ("006400", "삼성SDI", "배터리"),
                ("051910", "LG화학", "배터리소재"),
            ],
            "tier2": [
                ("003670", "포스코퓨처엠", "양극재"),
                ("247540", "에코프로비엠", "양극재"),
                ("086520", "에코프로", "양극재"),
            ],
            "tier3": [
                ("298040", "효성첨단소재", "탄소섬유"),
                ("024850", "HLB이노베이션", "전장부품"),
            ],
        },
        # 엔비디아 관련주 (한국)
        "NVDA": {
            "name": "엔비디아",
            "tier1": [
                ("000660", "SK하이닉스", "HBM 공급"),
                ("005930", "삼성전자", "HBM 공급"),
            ],
            "tier2": [
                ("058470", "리노공업", "반도체 검사"),
                ("036930", "주성엔지니어링", "반도체 장비"),
                ("357780", "솔브레인", "반도체 소재"),
            ],
            "tier3": [
                ("240810", "원익IPS", "반도체 장비"),
                ("403870", "HPSP", "반도체 소재"),
            ],
        },
    }

    # 테마별 관련주 계층
    THEME_TIERS = {
        "2차전지": {
            "tier1": [  # 배터리 셀 제조사 (핵심)
                ("373220", "LG에너지솔루션", "배터리 셀"),
                ("006400", "삼성SDI", "배터리 셀"),
                ("096770", "SK이노베이션", "배터리 셀"),
            ],
            "tier2": [  # 소재/부품사
                ("051910", "LG화학", "양극재/분리막"),
                ("003670", "포스코퓨처엠", "양극재"),
                ("247540", "에코프로비엠", "양극재"),
                ("086520", "에코프로", "양극재 지주"),
                ("012450", "한화에어로스페이스", "항공/방산"),
            ],
            "tier3": [  # 장비/기타
                ("064350", "현대로템", "배터리 장비"),
                ("298040", "효성첨단소재", "탄소섬유"),
                ("108320", "LX세미콘", "BMS칩"),
            ],
        },
        "AI": {
            "tier1": [
                ("000660", "SK하이닉스", "HBM 메모리"),
                ("005930", "삼성전자", "AI 반도체"),
            ],
            "tier2": [
                ("035420", "NAVER", "AI 서비스"),
                ("035720", "카카오", "AI 서비스"),
                ("402340", "SK스퀘어", "AI 투자"),
            ],
            "tier3": [
                ("078340", "컴투스", "AI 게임"),
                ("263750", "펄어비스", "AI 게임"),
                ("417780", "테이팩스", "AI 솔루션"),
            ],
        },
        "반도체": {
            "tier1": [
                ("005930", "삼성전자", "메모리/파운드리"),
                ("000660", "SK하이닉스", "메모리"),
            ],
            "tier2": [
                ("058470", "리노공업", "반도체 검사"),
                ("036930", "주성엔지니어링", "반도체 장비"),
                ("240810", "원익IPS", "반도체 장비"),
                ("357780", "솔브레인", "반도체 소재"),
            ],
            "tier3": [
                ("005290", "동진쎄미켐", "포토레지스트"),
                ("403870", "HPSP", "전구체"),
                ("950160", "코오롱티슈진", "소재"),
            ],
        },
        "자율주행": {
            "tier1": [
                ("005380", "현대차", "완성차"),
                ("000270", "기아", "완성차"),
            ],
            "tier2": [
                ("012330", "현대모비스", "부품/센서"),
                ("161390", "한국타이어앤테크놀로지", "타이어"),
                ("018880", "한온시스템", "열관리"),
            ],
            "tier3": [
                ("204320", "만도", "조향/제동"),
                ("298040", "효성첨단소재", "탄소섬유"),
            ],
        },
        "전기차": {
            "tier1": [
                ("005380", "현대차", "전기차"),
                ("000270", "기아", "전기차"),
                ("373220", "LG에너지솔루션", "배터리"),
            ],
            "tier2": [
                ("006400", "삼성SDI", "배터리"),
                ("012330", "현대모비스", "전장부품"),
                ("003670", "포스코퓨처엠", "양극재"),
            ],
            "tier3": [
                ("018880", "한온시스템", "열관리"),
                ("204320", "만도", "조향장치"),
            ],
        },
    }

    def __init__(self):
        self.theme_scraper = ThemeScraper()

    def find_related_stocks(self, ticker: str) -> Dict:
        """
        종목의 1차, 2차, 3차 관련주 찾기

        Args:
            ticker: 종목코드 또는 티커

        Returns:
            관련주 정보 딕셔너리
        """
        # 공급망 데이터에서 찾기
        if ticker in self.SUPPLY_CHAIN:
            data = self.SUPPLY_CHAIN[ticker]
            return {
                "ticker": ticker,
                "name": data["name"],
                "tier1": data.get("tier1", []),
                "tier2": data.get("tier2", []),
                "tier3": data.get("tier3", []),
                "source": "supply_chain",
            }

        logger.info(f"{ticker} 관련주 데이터 없음")
        return {"ticker": ticker, "tier1": [], "tier2": [], "tier3": []}

    def find_theme_related_stocks(self, theme: str) -> Dict:
        """
        테마별 1차, 2차, 3차 관련주 찾기

        Args:
            theme: 테마명 (예: "2차전지", "AI", "반도체")

        Returns:
            관련주 정보 딕셔너리
        """
        # 사전 정의된 테마 계층에서 찾기
        if theme in self.THEME_TIERS:
            data = self.THEME_TIERS[theme]
            return {
                "theme": theme,
                "tier1": data.get("tier1", []),
                "tier2": data.get("tier2", []),
                "tier3": data.get("tier3", []),
                "source": "predefined",
            }

        # 네이버 금융에서 테마주 조회
        stocks = self.theme_scraper.get_theme_stocks_by_name(theme)
        if stocks:
            # 시가총액/거래량 기준으로 tier 분류 (상위 30% → 1차, 중간 40% → 2차, 나머지 → 3차)
            n = len(stocks)
            tier1_end = max(1, n // 3)
            tier2_end = max(2, 2 * n // 3)

            return {
                "theme": theme,
                "tier1": [(s["ticker"], s["name"], "핵심 관련주") for s in stocks[:tier1_end]],
                "tier2": [(s["ticker"], s["name"], "주요 관련주") for s in stocks[tier1_end:tier2_end]],
                "tier3": [(s["ticker"], s["name"], "기타 관련주") for s in stocks[tier2_end:]],
                "source": "naver_finance",
            }

        return {"theme": theme, "tier1": [], "tier2": [], "tier3": []}

    def get_all_related_with_analysis(self, ticker_or_theme: str, is_theme: bool = False) -> Dict:
        """
        관련주 찾기 + 현재가 정보 포함

        Args:
            ticker_or_theme: 종목코드 또는 테마명
            is_theme: True면 테마로 검색

        Returns:
            상세 관련주 정보
        """
        from scrapers.korea.naver_scraper import NaverFinanceScraper
        naver = NaverFinanceScraper(delay=0.3)

        if is_theme:
            related = self.find_theme_related_stocks(ticker_or_theme)
        else:
            related = self.find_related_stocks(ticker_or_theme)

        # 각 tier의 현재가 정보 추가
        for tier in ["tier1", "tier2", "tier3"]:
            enriched = []
            for item in related.get(tier, []):
                ticker = item[0]
                name = item[1]
                desc = item[2] if len(item) > 2 else ""

                try:
                    price_info = naver.get_realtime_price(ticker)
                    enriched.append({
                        "ticker": ticker,
                        "name": name,
                        "description": desc,
                        "price": price_info.get("current_price", 0),
                        "change": price_info.get("change", 0),
                        "change_rate": price_info.get("change_rate", 0),
                    })
                except Exception:
                    enriched.append({
                        "ticker": ticker,
                        "name": name,
                        "description": desc,
                    })

            related[tier] = enriched

        return related


def print_related_stocks(related: Dict):
    """관련주 출력"""
    title = related.get("theme") or related.get("name") or related.get("ticker")
    print(f"\n{'='*60}")
    print(f"  📊 {title} 관련주 분석")
    print("="*60)

    for tier_name, tier_label in [("tier1", "🥇 1차 관련주 (핵심)"),
                                   ("tier2", "🥈 2차 관련주 (주요)"),
                                   ("tier3", "🥉 3차 관련주 (기타)")]:
        stocks = related.get(tier_name, [])
        if stocks:
            print(f"\n{tier_label}")
            print("-"*60)
            for stock in stocks:
                if isinstance(stock, dict):
                    price = stock.get("price", 0)
                    change = stock.get("change", 0)
                    desc = stock.get("description", "")
                    if price:
                        print(f"  {stock['name']:<12} ({stock['ticker']}) | {price:>10,}원 ({change:+,}) | {desc}")
                    else:
                        print(f"  {stock['name']:<12} ({stock['ticker']}) | {desc}")
                else:
                    print(f"  {stock[1]:<12} ({stock[0]}) | {stock[2] if len(stock) > 2 else ''}")


if __name__ == "__main__":
    # 테스트
    finder = RelatedStockFinder()

    # 삼성전자 관련주
    print("\n" + "="*60)
    print("  삼성전자 관련주 찾기")
    print("="*60)
    samsung_related = finder.find_related_stocks("005930")
    print_related_stocks(samsung_related)

    # AI 테마 관련주
    print("\n" + "="*60)
    print("  AI 테마 관련주 찾기")
    print("="*60)
    ai_related = finder.find_theme_related_stocks("AI")
    print_related_stocks(ai_related)

    # 2차전지 테마 관련주
    print("\n" + "="*60)
    print("  2차전지 테마 관련주 찾기")
    print("="*60)
    battery_related = finder.find_theme_related_stocks("2차전지")
    print_related_stocks(battery_related)
