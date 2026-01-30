"""
스크래퍼 기능 테스트 스크립트
DB 연결 없이 스크래핑 기능만 테스트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.korea.krx_scraper import KRXScraper
from scrapers.korea.naver_scraper import NaverFinanceScraper
from scrapers.usa.yahoo_scraper import YahooFinanceScraper
from scrapers.news.news_scraper import NaverFinanceNewsScraper, StockNewsScraper


def test_krx_scraper():
    """KRX 스크래퍼 테스트"""
    print("\n" + "="*50)
    print("KRX 스크래퍼 테스트")
    print("="*50)

    krx = KRXScraper()

    # 1. 종목 리스트 (KOSPI 상위 5개)
    print("\n[1] KOSPI 종목 리스트 (상위 5개)")
    df = krx.get_stock_list("KOSPI")
    if not df.empty:
        print(df.head())

    # 2. 삼성전자 현재가
    print("\n[2] 삼성전자(005930) 현재가")
    price = krx.get_current_price("005930")
    if price:
        for key, value in price.items():
            print(f"  {key}: {value}")

    # 3. 삼성전자 펀더멘탈
    print("\n[3] 삼성전자(005930) 펀더멘탈")
    fundamental = krx.get_fundamental("005930")
    if fundamental:
        for key, value in fundamental.items():
            print(f"  {key}: {value}")


def test_naver_scraper():
    """네이버 금융 스크래퍼 테스트"""
    print("\n" + "="*50)
    print("네이버 금융 스크래퍼 테스트")
    print("="*50)

    naver = NaverFinanceScraper(delay=0.5)

    # 1. 삼성전자 실시간 가격
    print("\n[1] 삼성전자(005930) 실시간 가격")
    price = naver.get_realtime_price("005930")
    if price:
        for key, value in price.items():
            print(f"  {key}: {value}")

    # 2. KOSPI 상승 상위 종목
    print("\n[2] KOSPI 상승 상위 5개")
    top_rise = naver.get_top_stocks("KOSPI", "rise")
    for stock in top_rise[:5]:
        print(f"  {stock['rank']}. {stock['name']} ({stock['ticker']}): {stock['change_rate']}")

    # 3. 시장 지수
    print("\n[3] 시장 지수")
    index = naver.get_market_index()
    for name, data in index.items():
        print(f"  {name}: {data}")


def test_yahoo_scraper():
    """Yahoo Finance 스크래퍼 테스트"""
    print("\n" + "="*50)
    print("Yahoo Finance 스크래퍼 테스트")
    print("="*50)

    yahoo = YahooFinanceScraper()

    # 1. AAPL 현재가
    print("\n[1] Apple(AAPL) 현재가")
    price = yahoo.get_current_price("AAPL")
    if price:
        print(f"  종목명: {price.get('name')}")
        print(f"  현재가: ${price.get('current_price')}")
        print(f"  변동: {price.get('change')} ({price.get('change_rate')}%)")
        print(f"  거래량: {price.get('volume'):,}")

    # 2. AAPL 펀더멘탈
    print("\n[2] Apple(AAPL) 펀더멘탈")
    fund = yahoo.get_fundamentals("AAPL")
    if fund:
        print(f"  PER: {fund.get('pe_ratio')}")
        print(f"  PBR: {fund.get('pb_ratio')}")
        print(f"  EPS: ${fund.get('eps')}")
        print(f"  배당수익률: {fund.get('dividend_yield')}")

    # 3. 미국 시장 지수
    print("\n[3] 미국 시장 지수")
    market = yahoo.get_market_summary()
    for name, data in market.items():
        print(f"  {name}: {data.get('price')} ({data.get('change_percent'):.2f}%)")

    # 4. AAPL 뉴스
    print("\n[4] Apple(AAPL) 최근 뉴스")
    news = yahoo.get_news("AAPL")
    for item in news[:5]:
        print(f"  - {item['title']}")
        print(f"    출처: {item['publisher']} | {item['published']}")


def test_news_scraper():
    """뉴스 스크래퍼 테스트"""
    print("\n" + "="*50)
    print("뉴스 스크래퍼 테스트")
    print("="*50)

    news_scraper = NaverFinanceNewsScraper(delay=0.5)

    # 1. 삼성전자 관련 뉴스
    print("\n[1] 삼성전자(005930) 관련 뉴스")
    news_list = news_scraper.get_stock_news("005930")
    for news in news_list[:5]:
        print(f"  - {news['title']}")
        print(f"    출처: {news['source']} | {news['date']}")

    # 2. 시장 뉴스 (메인)
    print("\n[2] 시장 메인 뉴스")
    market_news = news_scraper.get_market_news("main")
    for news in market_news[:5]:
        print(f"  - {news['title']}")

    # 3. 증권 뉴스
    print("\n[3] 증권 뉴스")
    stock_news = news_scraper.get_market_news("stock")
    for news in stock_news[:5]:
        print(f"  - {news['title']}")


def main():
    print("=" * 60)
    print("  RecommandAI 스크래퍼 기능 테스트")
    print("=" * 60)

    try:
        # 한국 주식 테스트
        test_krx_scraper()
        test_naver_scraper()

        # 미국 주식 테스트
        test_yahoo_scraper()

        # 뉴스 테스트
        test_news_scraper()

        print("\n" + "="*50)
        print("모든 테스트 완료!")
        print("="*50)

    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
