"""
수집 데이터를 텍스트 파일로 내보내기
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.korea.krx_scraper import KRXScraper
from scrapers.korea.naver_scraper import NaverFinanceScraper
from scrapers.korea.dynamic_theme_scraper import DynamicThemeScraper
from scrapers.usa.yahoo_scraper import YahooFinanceScraper
from scrapers.news.news_scraper import GoogleNewsRSS


def export_all_data():
    """모든 데이터를 수집하여 텍스트 파일로 저장"""

    output = []
    output.append("=" * 80)
    output.append(f"  RecommandAI 수집 데이터")
    output.append(f"  수집 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output.append("=" * 80)

    # 스크래퍼 초기화
    krx = KRXScraper()
    naver = NaverFinanceScraper(delay=0.3)
    yahoo = YahooFinanceScraper()
    theme_scraper = DynamicThemeScraper(delay=0.3)
    news = GoogleNewsRSS()

    # =========================================================================
    # 1. 한국 시장 지수
    # =========================================================================
    output.append("\n" + "=" * 80)
    output.append("[1] 한국 시장 지수")
    output.append("=" * 80)

    try:
        indices = naver.get_market_index()
        for name, data in indices.items():
            output.append(f"  {name}: {data.get('value', 'N/A')} ({data.get('change', 'N/A')}, {data.get('change_rate', 'N/A')}%)")
    except Exception as e:
        output.append(f"  오류: {e}")

    # =========================================================================
    # 2. 한국 주요 종목 현재가
    # =========================================================================
    output.append("\n" + "=" * 80)
    output.append("[2] 한국 주요 종목 현재가")
    output.append("=" * 80)

    korea_tickers = [
        ("005930", "삼성전자"),
        ("000660", "SK하이닉스"),
        ("035720", "카카오"),
        ("035420", "NAVER"),
        ("005380", "현대차"),
        ("051910", "LG화학"),
        ("006400", "삼성SDI"),
        ("003670", "포스코퓨처엠"),
        ("105560", "KB금융"),
        ("055550", "신한지주"),
    ]

    output.append(f"\n{'종목':<15} {'현재가':>12} {'전일대비':>12} {'등락률':>10} {'거래량':>15}")
    output.append("-" * 70)

    for ticker, name in korea_tickers:
        try:
            price = naver.get_realtime_price(ticker)
            current = price.get('current_price', 0)
            change = price.get('change', 0)
            rate = price.get('change_rate', 0)
            volume = price.get('volume', 0)
            output.append(f"{name:<15} {current:>12,}원 {change:>+12,} {rate:>+9.2f}% {volume:>15,}")
        except Exception as e:
            output.append(f"{name:<15} 오류: {e}")

    # =========================================================================
    # 3. 한국 주요 종목 펀더멘탈
    # =========================================================================
    output.append("\n" + "=" * 80)
    output.append("[3] 한국 주요 종목 펀더멘탈")
    output.append("=" * 80)

    output.append(f"\n{'종목':<15} {'PER':>10} {'PBR':>10} {'EPS':>12} {'배당률':>10}")
    output.append("-" * 60)

    for ticker, name in korea_tickers:
        try:
            fund = krx.get_fundamental(ticker)
            per = fund.get('per', 0) or 0
            pbr = fund.get('pbr', 0) or 0
            eps = fund.get('eps', 0) or 0
            div = fund.get('div_yield', 0) or 0
            output.append(f"{name:<15} {per:>10.2f} {pbr:>10.2f} {eps:>12,.0f} {div:>9.2f}%")
        except Exception as e:
            output.append(f"{name:<15} 오류: {e}")

    # =========================================================================
    # 4. 미국 시장 지수
    # =========================================================================
    output.append("\n" + "=" * 80)
    output.append("[4] 미국 시장 지수")
    output.append("=" * 80)

    try:
        us_indices = yahoo.get_market_summary()
        for name, data in us_indices.items():
            price = data.get('price', 0)
            change_pct = data.get('change_percent', 0)
            output.append(f"  {name}: {price:,.2f} ({change_pct:+.2f}%)")
    except Exception as e:
        output.append(f"  오류: {e}")

    # =========================================================================
    # 5. 미국 주요 종목 현재가
    # =========================================================================
    output.append("\n" + "=" * 80)
    output.append("[5] 미국 주요 종목 현재가")
    output.append("=" * 80)

    usa_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM", "V"]

    output.append(f"\n{'티커':<8} {'종목명':<20} {'현재가':>12} {'등락률':>10} {'52주고가':>12} {'52주저가':>12}")
    output.append("-" * 80)

    for ticker in usa_tickers:
        try:
            price = yahoo.get_current_price(ticker)
            info = yahoo.get_stock_info(ticker)
            name = info.get('name', ticker)[:18]
            current = price.get('current_price', 0)
            rate = price.get('change_rate', 0)
            high52 = price.get('fifty_two_week_high', 0)
            low52 = price.get('fifty_two_week_low', 0)
            output.append(f"{ticker:<8} {name:<20} ${current:>10.2f} {rate:>+9.2f}% ${high52:>10.2f} ${low52:>10.2f}")
        except Exception as e:
            output.append(f"{ticker:<8} 오류: {e}")

    # =========================================================================
    # 6. 미국 주요 종목 펀더멘탈
    # =========================================================================
    output.append("\n" + "=" * 80)
    output.append("[6] 미국 주요 종목 펀더멘탈")
    output.append("=" * 80)

    output.append(f"\n{'티커':<8} {'P/E':>10} {'P/B':>10} {'ROE':>10} {'배당률':>10} {'시가총액':>18}")
    output.append("-" * 70)

    for ticker in usa_tickers:
        try:
            fund = yahoo.get_fundamentals(ticker)
            pe = fund.get('pe_ratio', 0) or 0
            pb = fund.get('pb_ratio', 0) or 0
            roe = (fund.get('roe', 0) or 0) * 100
            div = (fund.get('dividend_yield', 0) or 0) * 100
            mcap = fund.get('market_cap', 0) or 0
            mcap_str = f"${mcap/1e12:.2f}T" if mcap >= 1e12 else f"${mcap/1e9:.1f}B"
            output.append(f"{ticker:<8} {pe:>10.2f} {pb:>10.2f} {roe:>9.1f}% {div:>9.2f}% {mcap_str:>18}")
        except Exception as e:
            output.append(f"{ticker:<8} 오류: {e}")

    # =========================================================================
    # 7. 네이버 금융 테마 목록 (상위 30개)
    # =========================================================================
    output.append("\n" + "=" * 80)
    output.append("[7] 네이버 금융 테마 목록 (상승률 TOP 30)")
    output.append("=" * 80)

    try:
        themes = theme_scraper.get_all_themes(pages=5)

        # 등락률 정렬
        import re
        def get_rate(t):
            try:
                numbers = re.findall(r'-?\d+\.?\d*', str(t.get("change_rate", "0")))
                return float(numbers[0]) if numbers else 0
            except:
                return 0

        sorted_themes = sorted(themes, key=get_rate, reverse=True)

        output.append(f"\n총 {len(themes)}개 테마\n")
        output.append(f"{'순위':>4} {'테마명':<25} {'등락률':>10}")
        output.append("-" * 45)

        for i, t in enumerate(sorted_themes[:30], 1):
            output.append(f"{i:>4}. {t['name']:<25} {t['change_rate']:>10}")
    except Exception as e:
        output.append(f"  오류: {e}")

    # =========================================================================
    # 8. 주요 테마별 종목 (2차전지, AI, 반도체)
    # =========================================================================
    output.append("\n" + "=" * 80)
    output.append("[8] 주요 테마별 종목")
    output.append("=" * 80)

    theme_keywords = ["2차전지", "AI", "반도체", "HBM"]

    for keyword in theme_keywords:
        output.append(f"\n--- {keyword} 테마 ---")
        try:
            matched = theme_scraper.search_theme(keyword)
            if matched:
                stocks = theme_scraper.get_theme_stocks(matched[0]["code"])
                output.append(f"테마코드: {matched[0]['code']} | 종목수: {len(stocks)}개\n")
                output.append(f"{'종목명':<12} {'현재가':>12} {'등락률':>10}")
                output.append("-" * 40)
                for stock in stocks[:10]:
                    name = stock.get('name', '')[:10]
                    price = stock.get('price', 0)
                    rate = stock.get('change_rate', '')
                    output.append(f"{name:<12} {price:>12,}원 {rate:>10}")
            else:
                output.append(f"  테마를 찾을 수 없음")
        except Exception as e:
            output.append(f"  오류: {e}")

    # =========================================================================
    # 9. 삼성전자 관련주 (1차/2차/3차)
    # =========================================================================
    output.append("\n" + "=" * 80)
    output.append("[9] 삼성전자(005930) 관련주")
    output.append("=" * 80)

    try:
        related = theme_scraper.find_related_stocks("005930", max_themes=5)

        output.append(f"\n소속 테마: {', '.join(related.get('themes', []))}")
        output.append(f"총 관련주: {related.get('total_related', 0)}개\n")

        for tier_key, tier_name in [("tier1", "1차 관련주 (핵심)"), ("tier2", "2차 관련주 (주요)"), ("tier3", "3차 관련주 (기타)")]:
            stocks = related.get(tier_key, [])
            if stocks:
                output.append(f"\n[{tier_name}] - {len(stocks)}개")
                output.append(f"{'종목명':<12} {'현재가':>12} {'등락률':>10} {'테마':<25}")
                output.append("-" * 65)
                for stock in stocks[:8]:
                    name = stock.get('name', '')[:10]
                    price = stock.get('price', 0)
                    rate = stock.get('change_rate', '')
                    themes = ', '.join(stock.get('themes', [])[:2])[:23]
                    output.append(f"{name:<12} {price:>12,}원 {rate:>10} {themes:<25}")
    except Exception as e:
        output.append(f"  오류: {e}")

    # =========================================================================
    # 10. 최신 뉴스
    # =========================================================================
    output.append("\n" + "=" * 80)
    output.append("[10] 최신 주식 뉴스")
    output.append("=" * 80)

    news_queries = [
        ("삼성전자 주식", "삼성전자"),
        ("SK하이닉스 주식", "SK하이닉스"),
        ("NVIDIA stock", "NVIDIA"),
        ("코스피 증시", "코스피"),
    ]

    for query, label in news_queries:
        output.append(f"\n--- {label} 관련 뉴스 ---")
        try:
            news_list = news.search(query, max_results=5)
            for item in news_list[:5]:
                title = item.get('title', '')[:60]
                source = item.get('source', '')
                output.append(f"  - {title}")
                output.append(f"    출처: {source}")
        except Exception as e:
            output.append(f"  오류: {e}")

    # =========================================================================
    # 파일 저장
    # =========================================================================
    output.append("\n" + "=" * 80)
    output.append("  데이터 수집 완료")
    output.append("=" * 80)

    # 파일로 저장
    filename = f"collected_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))

    print(f"\n데이터가 저장되었습니다: {filepath}")
    print('\n'.join(output))

    return filepath


if __name__ == "__main__":
    export_all_data()
