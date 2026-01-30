"""
화면별 데이터 수집 및 텍스트 파일 생성
recommandstock 웹 페이지에 표시할 모든 데이터를 수집합니다.
"""
import sys
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.korea.krx_scraper import KRXScraper
from scrapers.korea.naver_scraper import NaverFinanceScraper
from scrapers.korea.dynamic_theme_scraper import DynamicThemeScraper
from scrapers.usa.yahoo_scraper import YahooFinanceScraper
from scrapers.news.news_scraper import GoogleNewsRSS
from processors.analyzer import StockAnalyzer


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def safe(func, default=None):
    try:
        return func()
    except Exception as e:
        log(f"  오류: {e}")
        return default


def get_rate_num(rate_str):
    try:
        numbers = re.findall(r'-?\d+\.?\d*', str(rate_str))
        return float(numbers[0]) if numbers else 0
    except:
        return 0


def export_all():
    out = []
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 스크래퍼 초기화
    log("스크래퍼 초기화...")
    krx = KRXScraper()
    naver = NaverFinanceScraper(delay=0.2)
    yahoo = YahooFinanceScraper()
    theme_scraper = DynamicThemeScraper(delay=0.2)
    news_scraper = GoogleNewsRSS()
    analyzer = StockAnalyzer()

    # =====================================================================
    # 페이지 1: 메인 대시보드
    # =====================================================================
    log("=== 페이지 1: 메인 대시보드 ===")
    out.append("=" * 90)
    out.append(f"  [페이지 1] 메인 대시보드 - 수집시간: {timestamp}")
    out.append("=" * 90)

    # 1-1. 한국 시장 지수
    out.append("\n[1-1] 한국 시장 지수")
    out.append("-" * 50)
    indices = safe(lambda: naver.get_market_index(), {})
    for name, data in indices.items():
        out.append(f"  {name}: {data.get('value', 'N/A')} (전일대비: {data.get('change', 'N/A')})")

    # 1-2. 미국 시장 지수
    out.append("\n[1-2] 미국 시장 지수")
    out.append("-" * 50)
    us_indices = safe(lambda: yahoo.get_market_summary(), {})
    for name, data in us_indices.items():
        price = data.get('price', 0)
        chg_pct = data.get('change_percent', 0)
        out.append(f"  {name}: {price:,.2f} ({chg_pct:+.2f}%)")

    # 1-3. HOT 테마 TOP 10
    out.append("\n[1-3] HOT 테마 TOP 10 (상승률순)")
    out.append("-" * 50)
    log("  테마 목록 수집 중...")
    all_themes = safe(lambda: theme_scraper.get_all_themes(pages=5), [])
    sorted_themes = sorted(all_themes, key=lambda t: get_rate_num(t.get("change_rate", "0")), reverse=True)
    out.append(f"  총 {len(all_themes)}개 테마")
    out.append(f"\n  {'순위':>4} {'테마명':<28} {'등락률':>10}")
    out.append("  " + "-" * 46)
    for i, t in enumerate(sorted_themes[:10], 1):
        out.append(f"  {i:>4}. {t['name']:<28} {t['change_rate']:>10}")

    # 1-4. KOSPI 거래량 TOP 10
    out.append("\n[1-4] KOSPI 거래량 TOP 10")
    out.append("-" * 50)
    log("  KOSPI 거래량 상위 수집 중...")
    kospi_top = safe(lambda: naver.get_top_stocks("kospi", 10), [])
    out.append(f"\n  {'종목':<12} {'현재가':>12} {'전일대비':>12} {'거래량':>15}")
    out.append("  " + "-" * 55)
    for s in kospi_top[:10]:
        name = s.get('name', '')[:10]
        price = s.get('price', 0)
        change = s.get('change', 0)
        volume = s.get('volume', 0)
        out.append(f"  {name:<12} {price:>12,}원 {change:>+12,} {volume:>15,}")

    # 1-5. KOSDAQ 거래량 TOP 10
    out.append("\n[1-5] KOSDAQ 거래량 TOP 10")
    out.append("-" * 50)
    log("  KOSDAQ 거래량 상위 수집 중...")
    kosdaq_top = safe(lambda: naver.get_top_stocks("kosdaq", 10), [])
    out.append(f"\n  {'종목':<12} {'현재가':>12} {'전일대비':>12} {'거래량':>15}")
    out.append("  " + "-" * 55)
    for s in kosdaq_top[:10]:
        name = s.get('name', '')[:10]
        price = s.get('price', 0)
        change = s.get('change', 0)
        volume = s.get('volume', 0)
        out.append(f"  {name:<12} {price:>12,}원 {change:>+12,} {volume:>15,}")

    # 1-6. 최신 시장 뉴스 (메인)
    out.append("\n[1-6] 오늘의 시장 뉴스")
    out.append("-" * 50)
    market_news = safe(lambda: news_scraper.search("코스피 증시 오늘", max_results=10), [])
    for item in market_news[:10]:
        title = item.get('title', '')[:65]
        source = item.get('source', '')
        out.append(f"  - {title}")
        out.append(f"    [{source}] {item.get('published', '')}")

    # =====================================================================
    # 페이지 2: 한국 주요 종목 리스트
    # =====================================================================
    log("=== 페이지 2: 한국 주요 종목 리스트 ===")
    out.append("\n\n" + "=" * 90)
    out.append(f"  [페이지 2] 한국 주요 종목 리스트")
    out.append("=" * 90)

    korea_watchlist = [
        ("005930", "삼성전자"), ("000660", "SK하이닉스"), ("035720", "카카오"),
        ("035420", "NAVER"), ("005380", "현대차"), ("051910", "LG화학"),
        ("006400", "삼성SDI"), ("003670", "포스코퓨처엠"), ("105560", "KB금융"),
        ("055550", "신한지주"), ("000270", "기아"), ("068270", "셀트리온"),
        ("028260", "삼성물산"), ("207940", "삼성바이오로직스"), ("373220", "LG에너지솔루션"),
        ("005490", "POSCO홀딩스"), ("012330", "현대모비스"), ("066570", "LG전자"),
        ("003550", "LG"), ("096770", "SK이노베이션"),
    ]

    # 2-1. 현재가 + 펀더멘탈 통합
    out.append("\n[2-1] 한국 주요 종목 현재가 + 펀더멘탈")
    out.append("-" * 90)
    out.append(f"\n  {'종목':<12} {'현재가':>12} {'전일대비':>10} {'PER':>8} {'PBR':>8} {'EPS':>10}")
    out.append("  " + "-" * 65)

    korea_prices = {}
    korea_fundamentals = {}

    for ticker, name in korea_watchlist:
        log(f"  {name}({ticker}) 수집 중...")
        price = safe(lambda t=ticker: naver.get_realtime_price(t), {})
        fund = safe(lambda t=ticker: krx.get_fundamental(t), {})
        korea_prices[ticker] = price
        korea_fundamentals[ticker] = fund

        current = price.get('current_price', 0)
        change = price.get('change', 0)
        per = fund.get('per', 0) or 0
        pbr = fund.get('pbr', 0) or 0
        eps = fund.get('eps', 0) or 0
        out.append(f"  {name:<12} {current:>12,}원 {change:>+10,} {per:>8.2f} {pbr:>8.2f} {eps:>10,.0f}")

    # 2-2. 상세 정보 (시가총액, 52주 고저)
    out.append("\n[2-2] 한국 종목 상세 정보")
    out.append("-" * 90)
    out.append(f"\n  {'종목':<12} {'시가총액':>16} {'52주최고':>12} {'52주최저':>12}")
    out.append("  " + "-" * 55)

    for ticker, name in korea_watchlist:
        log(f"  {name} 상세정보 수집 중...")
        info = safe(lambda t=ticker: naver.get_stock_info(t), {})
        mcap = info.get('market_cap', 'N/A')
        high = info.get('week52_high', 'N/A')
        low = info.get('week52_low', 'N/A')
        out.append(f"  {name:<12} {str(mcap):>16} {str(high):>12} {str(low):>12}")

    # =====================================================================
    # 페이지 3: 종목 상세 (삼성전자, SK하이닉스, NAVER 예시)
    # =====================================================================
    log("=== 페이지 3: 종목 상세 페이지 ===")
    out.append("\n\n" + "=" * 90)
    out.append(f"  [페이지 3] 종목 상세 페이지")
    out.append("=" * 90)

    detail_stocks = [
        ("005930", "삼성전자"),
        ("000660", "SK하이닉스"),
        ("035420", "NAVER"),
    ]

    for ticker, name in detail_stocks:
        out.append(f"\n{'─' * 90}")
        out.append(f"  ◆ {name} ({ticker}) 상세 분석")
        out.append(f"{'─' * 90}")

        # 가격 정보
        price = korea_prices.get(ticker, {})
        fund = korea_fundamentals.get(ticker, {})
        out.append(f"\n  [가격 정보]")
        out.append(f"    현재가: {price.get('current_price', 0):,}원")
        out.append(f"    전일대비: {price.get('change', 0):+,}원")
        out.append(f"    고가: {price.get('high', 'N/A')}")
        out.append(f"    저가: {price.get('low', 'N/A')}")
        out.append(f"    거래량: {price.get('volume', 0):,}")

        # 펀더멘탈
        out.append(f"\n  [펀더멘탈]")
        out.append(f"    PER: {fund.get('per', 'N/A')}")
        out.append(f"    PBR: {fund.get('pbr', 'N/A')}")
        out.append(f"    EPS: {fund.get('eps', 'N/A')}")
        out.append(f"    BPS: {fund.get('bps', 'N/A')}")
        out.append(f"    배당수익률: {fund.get('div_yield', 'N/A')}")

        # 소속 테마
        log(f"  {name} 소속 테마 조회 중...")
        stock_themes = safe(lambda t=ticker: theme_scraper.get_stock_themes(t), [])
        out.append(f"\n  [소속 테마] ({len(stock_themes)}개)")
        for t in stock_themes[:8]:
            out.append(f"    - {t['name']} (코드: {t['code']})")

        # 관련주 (1차/2차/3차)
        log(f"  {name} 관련주 조회 중...")
        related = safe(lambda t=ticker: theme_scraper.find_related_stocks(t, max_themes=5), {})
        out.append(f"\n  [관련주] 총 {related.get('total_related', 0)}개")

        for tier_key, tier_name in [("tier1", "1차 관련주(핵심)"), ("tier2", "2차 관련주(주요)"), ("tier3", "3차 관련주(기타)")]:
            stocks = related.get(tier_key, [])
            if stocks:
                out.append(f"\n    {tier_name} - {len(stocks)}개")
                out.append(f"    {'종목명':<12} {'현재가':>10} {'등락률':>10} {'공통테마':<30}")
                out.append("    " + "-" * 65)
                for s in stocks[:8]:
                    sname = s.get('name', '')[:10]
                    sprice = s.get('price', 0)
                    srate = s.get('change_rate', '')
                    sthemes = ', '.join(s.get('themes', [])[:3])[:28]
                    out.append(f"    {sname:<12} {sprice:>10,}원 {srate:>10} {sthemes:<30}")

        # 종목 뉴스
        log(f"  {name} 뉴스 수집 중...")
        stock_news = safe(lambda n=name: news_scraper.search(f"{n} 주식", max_results=8), [])
        out.append(f"\n  [최신 뉴스] ({len(stock_news)}건)")
        for item in stock_news[:8]:
            title = item.get('title', '')[:60]
            source = item.get('source', '')
            out.append(f"    - {title}")
            out.append(f"      [{source}] {item.get('published', '')}")

    # =====================================================================
    # 페이지 4: 테마 목록 + 상세
    # =====================================================================
    log("=== 페이지 4: 테마 페이지 ===")
    out.append("\n\n" + "=" * 90)
    out.append(f"  [페이지 4] 테마 목록 및 상세")
    out.append("=" * 90)

    # 4-1. 전체 테마 목록 (전체 수집)
    log("  전체 테마 목록 수집 중...")
    full_themes = safe(lambda: theme_scraper.get_all_themes(pages=10), [])
    sorted_all = sorted(full_themes, key=lambda t: get_rate_num(t.get("change_rate", "0")), reverse=True)

    out.append(f"\n[4-1] 전체 테마 목록 ({len(full_themes)}개)")
    out.append("-" * 55)
    out.append(f"\n  {'순위':>4} {'테마명':<28} {'코드':>8} {'등락률':>10}")
    out.append("  " + "-" * 52)
    for i, t in enumerate(sorted_all, 1):
        out.append(f"  {i:>4}. {t['name']:<28} {t['code']:>8} {t['change_rate']:>10}")

    # 4-2. 하락률 TOP 20
    out.append(f"\n[4-2] 하락률 TOP 20")
    out.append("-" * 55)
    out.append(f"\n  {'순위':>4} {'테마명':<28} {'등락률':>10}")
    out.append("  " + "-" * 46)
    for i, t in enumerate(sorted_all[-20:][::-1], 1):
        out.append(f"  {i:>4}. {t['name']:<28} {t['change_rate']:>10}")

    # 4-3. 주요 테마 상세 (상위 5개 테마)
    top5_themes = sorted_all[:5]

    for theme in top5_themes:
        out.append(f"\n{'─' * 90}")
        out.append(f"  ◆ [{theme['name']}] 테마 상세 (등락률: {theme['change_rate']})")
        out.append(f"{'─' * 90}")

        log(f"  테마 '{theme['name']}' 종목 수집 중...")
        theme_stocks = safe(lambda c=theme['code']: theme_scraper.get_theme_stocks(c), [])
        out.append(f"  소속 종목: {len(theme_stocks)}개\n")
        out.append(f"  {'종목명':<12} {'종목코드':>8} {'현재가':>12} {'전일대비':>10} {'등락률':>10}")
        out.append("  " + "-" * 55)
        for s in theme_stocks:
            sname = s.get('name', '')[:10]
            sticker = s.get('ticker', '')
            sprice = s.get('price', 0)
            schange = s.get('change', '')
            srate = s.get('change_rate', '')
            out.append(f"  {sname:<12} {sticker:>8} {sprice:>12,}원 {schange:>10} {srate:>10}")

    # 4-4. 키워드 테마 상세 (2차전지, AI, HBM, 반도체, 바이오)
    keyword_themes = ["2차전지", "AI", "HBM", "반도체", "바이오시밀러", "전기차", "로봇", "양자컴퓨터"]

    for keyword in keyword_themes:
        out.append(f"\n{'─' * 90}")
        out.append(f"  ◆ [{keyword}] 테마 검색 결과")
        out.append(f"{'─' * 90}")

        log(f"  '{keyword}' 테마 검색 중...")
        matched = safe(lambda k=keyword: theme_scraper.search_theme(k), [])
        out.append(f"  매칭 테마: {len(matched)}개")

        for m in matched[:3]:
            out.append(f"\n  >> {m['name']} (코드: {m['code']}, 등락률: {m['change_rate']})")
            stocks = safe(lambda c=m['code']: theme_scraper.get_theme_stocks(c), [])
            out.append(f"     소속 종목 {len(stocks)}개:")
            for s in stocks[:10]:
                sname = s.get('name', '')[:10]
                sprice = s.get('price', 0)
                srate = s.get('change_rate', '')
                out.append(f"     - {sname:<12} {sprice:>10,}원  {srate:>10}")

    # =====================================================================
    # 페이지 5: 미국 주식
    # =====================================================================
    log("=== 페이지 5: 미국 주식 ===")
    out.append("\n\n" + "=" * 90)
    out.append(f"  [페이지 5] 미국 주식")
    out.append("=" * 90)

    usa_watchlist = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
        "NVDA", "META", "JPM", "V", "JNJ",
        "UNH", "XOM", "PG", "MA", "HD",
        "COST", "ABBV", "CRM", "AMD", "NFLX",
    ]

    # 5-1. 미국 종목 현재가
    out.append(f"\n[5-1] 미국 종목 현재가 ({len(usa_watchlist)}개)")
    out.append("-" * 90)
    out.append(f"\n  {'티커':<7} {'종목명':<22} {'현재가':>12} {'등락률':>10} {'52주고가':>12} {'52주저가':>12}")
    out.append("  " + "-" * 80)

    us_price_data = {}
    us_fund_data = {}
    us_info_data = {}

    for ticker in usa_watchlist:
        log(f"  {ticker} 수집 중...")
        price = safe(lambda t=ticker: yahoo.get_current_price(t), {})
        info = safe(lambda t=ticker: yahoo.get_stock_info(t), {})
        us_price_data[ticker] = price
        us_info_data[ticker] = info

        name = info.get('name', ticker)[:20]
        current = price.get('current_price', 0)
        rate = price.get('change_rate', 0)
        h52 = price.get('fifty_two_week_high', 0)
        l52 = price.get('fifty_two_week_low', 0)
        out.append(f"  {ticker:<7} {name:<22} ${current:>10.2f} {rate:>+9.2f}% ${h52:>10.2f} ${l52:>10.2f}")

    # 5-2. 미국 종목 펀더멘탈
    out.append(f"\n[5-2] 미국 종목 펀더멘탈")
    out.append("-" * 90)
    out.append(f"\n  {'티커':<7} {'P/E':>10} {'P/B':>10} {'ROE':>10} {'배당률':>10} {'이익률':>10} {'섹터':<20}")
    out.append("  " + "-" * 80)

    for ticker in usa_watchlist:
        log(f"  {ticker} 펀더멘탈 수집 중...")
        fund = safe(lambda t=ticker: yahoo.get_fundamentals(t), {})
        us_fund_data[ticker] = fund
        info = us_info_data.get(ticker, {})

        pe = fund.get('pe_ratio', 0) or 0
        pb = fund.get('pb_ratio', 0) or 0
        roe = (fund.get('roe', 0) or 0) * 100
        div = (fund.get('dividend_yield', 0) or 0) * 100
        margin = (fund.get('profit_margin', 0) or 0) * 100
        sector = info.get('sector', '')[:18]
        out.append(f"  {ticker:<7} {pe:>10.2f} {pb:>10.2f} {roe:>9.1f}% {div:>9.2f}% {margin:>9.1f}% {sector:<20}")

    # 5-3. 미국 종목별 상세
    us_detail = ["AAPL", "NVDA", "TSLA", "MSFT", "AMZN"]
    for ticker in us_detail:
        info = us_info_data.get(ticker, {})
        price = us_price_data.get(ticker, {})
        fund = us_fund_data.get(ticker, {})

        out.append(f"\n{'─' * 90}")
        out.append(f"  ◆ {info.get('name', ticker)} ({ticker})")
        out.append(f"{'─' * 90}")
        out.append(f"  섹터: {info.get('sector', 'N/A')}")
        out.append(f"  산업: {info.get('industry', 'N/A')}")
        out.append(f"  현재가: ${price.get('current_price', 0):.2f}")
        out.append(f"  등락률: {price.get('change_rate', 0):+.2f}%")
        out.append(f"  52주 고가: ${price.get('fifty_two_week_high', 0):.2f}")
        out.append(f"  52주 저가: ${price.get('fifty_two_week_low', 0):.2f}")
        out.append(f"  P/E: {fund.get('pe_ratio', 'N/A')}")
        out.append(f"  P/B: {fund.get('pb_ratio', 'N/A')}")
        out.append(f"  ROE: {(fund.get('roe', 0) or 0) * 100:.1f}%")
        out.append(f"  배당수익률: {(fund.get('dividend_yield', 0) or 0) * 100:.2f}%")

        # 뉴스
        log(f"  {ticker} 뉴스 수집 중...")
        us_news = safe(lambda t=ticker: yahoo.get_news(t), [])
        out.append(f"\n  [최신 뉴스]")
        for n in us_news[:5]:
            out.append(f"    - {n.get('title', '')[:60]}")
            out.append(f"      [{n.get('publisher', '')}]")

    # =====================================================================
    # 페이지 6: 추천 종목 분석
    # =====================================================================
    log("=== 페이지 6: 추천 종목 분석 ===")
    out.append("\n\n" + "=" * 90)
    out.append(f"  [페이지 6] AI 추천 종목 분석")
    out.append("=" * 90)

    # 6-1. 한국 종목 분석
    out.append("\n[6-1] 한국 종목 AI 분석")
    out.append("-" * 90)

    korea_analysis_list = [
        ("005930", "삼성전자"), ("000660", "SK하이닉스"), ("035720", "카카오"),
        ("035420", "NAVER"), ("005380", "현대차"), ("051910", "LG화학"),
        ("006400", "삼성SDI"), ("003670", "포스코퓨처엠"), ("105560", "KB금융"),
        ("055550", "신한지주"), ("000270", "기아"), ("068270", "셀트리온"),
    ]

    kr_results = []
    for ticker, name in korea_analysis_list:
        log(f"  {name} AI 분석 중...")
        result = safe(lambda t=ticker, n=name: analyzer.analyze_korea_stock(t, n), None)
        if result:
            kr_results.append(result)

    # 점수순 정렬
    kr_results.sort(key=lambda x: x.get('score', 0), reverse=True)

    out.append(f"\n  {'종목':<12} {'현재가':>12} {'전일대비':>10} {'점수':>6} {'등급':>4} {'추천':>10}")
    out.append("  " + "-" * 60)
    for r in kr_results:
        name = r.get('name', '')[:10]
        price = r.get('price', {})
        current = price.get('current_price', 0)
        change = price.get('change', 0)
        score = r.get('score', 0)
        rec = r.get('recommendation', {})
        out.append(f"  {name:<12} {current:>12,}원 {change:>+10,} {score:>6} {rec.get('grade',''):>4} {rec.get('action',''):>10}")

    # 상세 분석
    for r in kr_results[:5]:
        out.append(f"\n  ◆ {r['name']} ({r['ticker']}) 상세 분석")
        out.append(f"    점수: {r['score']}/100 | 등급: {r['recommendation']['grade']} | {r['recommendation']['action']}")
        for a in r.get('analysis', []):
            out.append(f"    {a}")

    # 6-2. 미국 종목 분석
    out.append(f"\n[6-2] 미국 종목 AI 분석")
    out.append("-" * 90)

    usa_analysis_list = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM", "V"]

    us_results = []
    for ticker in usa_analysis_list:
        log(f"  {ticker} AI 분석 중...")
        result = safe(lambda t=ticker: analyzer.analyze_usa_stock(t), None)
        if result:
            us_results.append(result)

    us_results.sort(key=lambda x: x.get('score', 0), reverse=True)

    out.append(f"\n  {'티커':<8} {'종목명':<18} {'현재가':>12} {'등락률':>10} {'점수':>6} {'등급':>4} {'추천':>10}")
    out.append("  " + "-" * 72)
    for r in us_results:
        name = r.get('name', r['ticker'])[:16]
        price = r.get('price', {})
        current = price.get('current_price', 0)
        rate = price.get('change_rate', 0)
        score = r.get('score', 0)
        rec = r.get('recommendation', {})
        out.append(f"  {r['ticker']:<8} {name:<18} ${current:>10.2f} {rate:>+9.2f}% {score:>6} {rec.get('grade',''):>4} {rec.get('action',''):>10}")

    for r in us_results[:5]:
        out.append(f"\n  ◆ {r.get('name', r['ticker'])} ({r['ticker']}) 상세 분석")
        out.append(f"    점수: {r['score']}/100 | 등급: {r['recommendation']['grade']} | {r['recommendation']['action']}")
        for a in r.get('analysis', []):
            out.append(f"    {a}")

    # 6-3. 종합 추천 TOP 10
    out.append(f"\n[6-3] 종합 추천 TOP 10 (한국+미국)")
    out.append("-" * 90)

    all_results = kr_results + us_results
    all_results.sort(key=lambda x: x.get('score', 0), reverse=True)

    for i, r in enumerate(all_results[:10], 1):
        country = "🇰🇷" if r.get('country') == 'KR' else "🇺🇸"
        rec = r.get('recommendation', {})
        out.append(f"\n  {i}위. {country} {r.get('name', '')} ({r['ticker']})")
        out.append(f"      점수: {r['score']}/100 | 등급: {rec.get('grade', '')} | {rec.get('action', '')}")
        for a in r.get('analysis', [])[:3]:
            out.append(f"      {a}")

    # =====================================================================
    # 페이지 7: 뉴스 센터
    # =====================================================================
    log("=== 페이지 7: 뉴스 센터 ===")
    out.append("\n\n" + "=" * 90)
    out.append(f"  [페이지 7] 뉴스 센터")
    out.append("=" * 90)

    news_categories = [
        ("주식 시장 전망 2026", "시장 전망"),
        ("코스피 증시", "코스피"),
        ("코스닥 바이오", "코스닥/바이오"),
        ("반도체 주식", "반도체"),
        ("2차전지 배터리 주식", "2차전지"),
        ("AI 인공지능 주식", "AI/인공지능"),
        ("미국 주식 나스닥", "미국 나스닥"),
        ("금리 환율 경제", "금리/환율"),
        ("부동산 리츠 투자", "부동산/리츠"),
        ("IPO 공모주 상장", "IPO/공모주"),
    ]

    for query, label in news_categories:
        out.append(f"\n  [{label}] 최신 뉴스")
        out.append("  " + "-" * 60)
        log(f"  '{label}' 뉴스 수집 중...")
        news_list = safe(lambda q=query: news_scraper.search(q, max_results=8), [])
        for item in news_list[:8]:
            title = item.get('title', '')[:60]
            source = item.get('source', '')
            pub = item.get('published', '')
            out.append(f"  - {title}")
            out.append(f"    [{source}] {pub}")

    # =====================================================================
    # 페이지 8: 관련주 맵
    # =====================================================================
    log("=== 페이지 8: 관련주 맵 ===")
    out.append("\n\n" + "=" * 90)
    out.append(f"  [페이지 8] 관련주 맵")
    out.append("=" * 90)

    related_targets = [
        ("000660", "SK하이닉스"),
        ("035720", "카카오"),
        ("068270", "셀트리온"),
    ]

    for ticker, name in related_targets:
        out.append(f"\n{'─' * 90}")
        out.append(f"  ◆ {name}({ticker}) 관련주")
        out.append(f"{'─' * 90}")

        log(f"  {name} 관련주 조회 중...")
        related = safe(lambda t=ticker: theme_scraper.find_related_stocks(t, max_themes=5), {})

        out.append(f"  소속 테마: {', '.join(related.get('themes', []))}")
        out.append(f"  총 관련주: {related.get('total_related', 0)}개")

        for tier_key, tier_name in [("tier1", "1차 관련주(핵심)"), ("tier2", "2차 관련주(주요)"), ("tier3", "3차 관련주(기타)")]:
            stocks = related.get(tier_key, [])
            if stocks:
                out.append(f"\n  [{tier_name}] {len(stocks)}개")
                out.append(f"  {'종목명':<12} {'코드':>8} {'현재가':>10} {'등락률':>10} {'공통테마':<30}")
                out.append("  " + "-" * 75)
                for s in stocks[:10]:
                    sn = s.get('name', '')[:10]
                    st = s.get('ticker', '')
                    sp = s.get('price', 0)
                    sr = s.get('change_rate', '')
                    sth = ', '.join(s.get('themes', [])[:3])[:28]
                    out.append(f"  {sn:<12} {st:>8} {sp:>10,}원 {sr:>10} {sth:<30}")

    # =====================================================================
    # 파일 저장
    # =====================================================================
    out.append("\n\n" + "=" * 90)
    out.append(f"  데이터 수집 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    out.append("=" * 90)

    filename = f"page_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))

    log(f"\n저장 완료: {filepath}")
    log(f"총 {len(out)} 줄")
    return filepath


if __name__ == "__main__":
    export_all()
