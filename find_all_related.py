"""
관련주 찾기 (동적 스크래핑)
네이버 금융에서 실시간으로 테마/관련주를 찾습니다.
하드코딩 없이 모든 데이터를 동적으로 수집합니다.
"""
import sys
import os
import argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.korea.dynamic_theme_scraper import DynamicThemeScraper, print_dynamic_related
from scrapers.korea.naver_scraper import NaverFinanceScraper
from scrapers.korea.krx_scraper import KRXScraper


def find_stock_related(ticker: str):
    """종목의 관련주 찾기"""
    print(f"\n{'='*70}")
    print(f"  🔍 종목 관련주 찾기: {ticker}")
    print("="*70)

    scraper = DynamicThemeScraper()
    naver = NaverFinanceScraper(delay=0.2)
    krx = KRXScraper()

    # 종목 정보
    info = naver.get_realtime_price(ticker)
    if info:
        print(f"\n📌 {info.get('name', ticker)} ({ticker})")
        print(f"   현재가: {info.get('current_price', 0):,}원 ({info.get('change', 0):+,})")

    # 관련주 찾기
    related = scraper.find_related_stocks(ticker, max_themes=5)
    print_dynamic_related(related)

    # 추천 종목 (1차+2차 중 상승률 높은 순)
    print(f"\n{'='*70}")
    print("  ⭐ 추천 관련주 (상승률 순)")
    print("="*70)

    all_related = related.get("tier1", []) + related.get("tier2", [])
    # 등락률에서 숫자 추출
    def get_change_rate(stock):
        rate_str = stock.get("change_rate", "0")
        try:
            # 숫자만 추출
            import re
            numbers = re.findall(r'-?\d+\.?\d*', str(rate_str))
            return float(numbers[0]) if numbers else 0
        except:
            return 0

    sorted_stocks = sorted(all_related, key=get_change_rate, reverse=True)

    print(f"\n{'종목':<12} {'현재가':>12} {'등락률':>10} {'테마':<25}")
    print("-"*70)
    for stock in sorted_stocks[:10]:
        name = stock.get("name", "")[:10]
        price = stock.get("price", 0)
        rate = stock.get("change_rate", "")
        themes = ", ".join(stock.get("themes", [])[:2])[:23]
        print(f"{name:<12} {price:>12,}원 {rate:>10} {themes:<25}")


def find_theme_related(theme: str):
    """테마의 관련주 찾기"""
    print(f"\n{'='*70}")
    print(f"  🔍 테마 관련주 찾기: {theme}")
    print("="*70)

    scraper = DynamicThemeScraper()
    related = scraper.find_theme_stocks_tiered(theme)
    print_dynamic_related(related)

    # 추천 종목
    print(f"\n{'='*70}")
    print("  ⭐ 추천 테마주 (상승률 순)")
    print("="*70)

    all_related = related.get("tier1", []) + related.get("tier2", [])

    def get_change_rate(stock):
        rate_str = stock.get("change_rate", "0")
        try:
            import re
            numbers = re.findall(r'-?\d+\.?\d*', str(rate_str))
            return float(numbers[0]) if numbers else 0
        except:
            return 0

    sorted_stocks = sorted(all_related, key=get_change_rate, reverse=True)

    print(f"\n{'종목':<12} {'현재가':>12} {'등락률':>10} {'테마':<25}")
    print("-"*70)
    for stock in sorted_stocks[:15]:
        name = stock.get("name", "")[:10]
        price = stock.get("price", 0)
        rate = stock.get("change_rate", "")
        themes = ", ".join(stock.get("themes", [])[:2])[:23]
        print(f"{name:<12} {price:>12,}원 {rate:>10} {themes:<25}")


def list_all_themes():
    """전체 테마 목록"""
    print(f"\n{'='*70}")
    print("  📋 네이버 금융 전체 테마 목록")
    print("="*70)

    scraper = DynamicThemeScraper()
    themes = scraper.get_all_themes(pages=10)

    # 등락률 순 정렬
    def get_rate(theme):
        rate_str = theme.get("change_rate", "0")
        try:
            import re
            numbers = re.findall(r'-?\d+\.?\d*', str(rate_str))
            return float(numbers[0]) if numbers else 0
        except:
            return 0

    sorted_themes = sorted(themes, key=get_rate, reverse=True)

    print(f"\n총 {len(themes)}개 테마\n")
    print("📈 상승률 TOP 20:")
    print("-"*50)
    for i, t in enumerate(sorted_themes[:20], 1):
        print(f"  {i:2}. {t['name']:<25} {t['change_rate']:>10}")

    print("\n📉 하락률 TOP 10:")
    print("-"*50)
    for i, t in enumerate(sorted_themes[-10:][::-1], 1):
        print(f"  {i:2}. {t['name']:<25} {t['change_rate']:>10}")


def main():
    parser = argparse.ArgumentParser(
        description="관련주 찾기 (동적 스크래핑)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python find_all_related.py --ticker 005930        # 삼성전자 관련주
  python find_all_related.py --ticker 000660        # SK하이닉스 관련주
  python find_all_related.py --theme 2차전지        # 2차전지 테마
  python find_all_related.py --theme AI             # AI 테마
  python find_all_related.py --theme HBM            # HBM 테마
  python find_all_related.py --list                 # 전체 테마 목록
        """
    )
    parser.add_argument("--ticker", type=str, help="종목코드 (예: 005930)")
    parser.add_argument("--theme", type=str, help="테마명 (예: 2차전지, AI, HBM)")
    parser.add_argument("--list", action="store_true", help="전체 테마 목록 조회")

    args = parser.parse_args()

    if args.ticker:
        find_stock_related(args.ticker)
    elif args.theme:
        find_theme_related(args.theme)
    elif args.list:
        list_all_themes()
    else:
        # 기본: 인기 테마 및 종목 분석
        print("="*70)
        print("  🔍 관련주 찾기 시스템 (동적 스크래핑)")
        print("="*70)
        print("\n사용법:")
        print("  python find_all_related.py --ticker 005930  # 삼성전자 관련주")
        print("  python find_all_related.py --theme AI       # AI 테마 관련주")
        print("  python find_all_related.py --list           # 전체 테마 목록")

        print("\n\n" + "="*70)
        print("  📊 인기 테마 분석")
        print("="*70)

        # 상위 테마 조회
        scraper = DynamicThemeScraper()
        themes = scraper.get_all_themes(pages=3)

        def get_rate(t):
            try:
                import re
                numbers = re.findall(r'-?\d+\.?\d*', str(t.get("change_rate", "0")))
                return float(numbers[0]) if numbers else 0
            except:
                return 0

        top_themes = sorted(themes, key=get_rate, reverse=True)[:5]

        print("\n🔥 오늘의 HOT 테마:")
        for i, t in enumerate(top_themes, 1):
            print(f"  {i}. {t['name']} ({t['change_rate']})")

        # 첫번째 HOT 테마 분석
        if top_themes:
            print(f"\n\n🔍 [{top_themes[0]['name']}] 테마 상세 분석...")
            find_theme_related(top_themes[0]["name"])


if __name__ == "__main__":
    main()
