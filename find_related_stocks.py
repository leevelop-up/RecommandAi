"""
관련주 찾기 + 분석 + 미래 예측
1차, 2차, 3차 관련주를 찾고 투자 분석 및 미래 예측을 제공합니다.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.korea.theme_scraper import RelatedStockFinder
from scrapers.korea.naver_scraper import NaverFinanceScraper
from processors.analyzer import StockAnalyzer
from processors.future_predictor import FuturePredictor, print_prediction_report
from loguru import logger


def analyze_related_stocks(ticker_or_theme: str, is_theme: bool = False):
    """
    관련주 찾기 + 분석

    Args:
        ticker_or_theme: 종목코드 또는 테마명
        is_theme: True면 테마로 검색
    """
    finder = RelatedStockFinder()
    naver = NaverFinanceScraper(delay=0.3)
    analyzer = StockAnalyzer()
    predictor = FuturePredictor()

    # 관련주 찾기
    if is_theme:
        related = finder.find_theme_related_stocks(ticker_or_theme)
        title = f"📊 [{ticker_or_theme}] 테마 관련주 분석"
    else:
        related = finder.find_related_stocks(ticker_or_theme)
        name = related.get("name", ticker_or_theme)
        title = f"📊 [{name}] ({ticker_or_theme}) 관련주 분석"

    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

    all_stocks = []

    # 각 tier 분석
    for tier_name, tier_label, emoji in [
        ("tier1", "1차 관련주 (핵심)", "🥇"),
        ("tier2", "2차 관련주 (주요)", "🥈"),
        ("tier3", "3차 관련주 (기타)", "🥉"),
    ]:
        stocks = related.get(tier_name, [])
        if not stocks:
            continue

        print(f"\n{emoji} {tier_label}")
        print("-"*70)
        print(f"{'종목':<12} {'현재가':>12} {'변동':>10} {'점수':>6} {'등급':>4} {'설명':<15}")
        print("-"*70)

        for item in stocks:
            if isinstance(item, tuple):
                ticker, name, desc = item[0], item[1], item[2] if len(item) > 2 else ""
            else:
                ticker = item.get("ticker", "")
                name = item.get("name", "")
                desc = item.get("description", "")

            try:
                # 현재가 조회
                price_info = naver.get_realtime_price(ticker)
                current = price_info.get("current_price", 0)
                change = price_info.get("change", 0)

                # 간단 분석 (펀더멘탈)
                from scrapers.korea.krx_scraper import KRXScraper
                krx = KRXScraper()
                fund = krx.get_fundamental(ticker)

                # 미래 예측 분석 적용
                stock_data = {
                    "ticker": ticker,
                    "name": name,
                    "price": price_info,
                    "fundamental": fund,
                }
                
                prediction = predictor.predict_stock(stock_data)
                score = prediction["prediction_score"]

                # 등급
                if score >= 70:
                    grade = "A"
                elif score >= 55:
                    grade = "B"
                elif score >= 40:
                    grade = "C"
                else:
                    grade = "D"

                print(f"{name:<12} {current:>12,}원 {change:>+10,} {score:>6} {grade:>4} {desc:<15}")

                all_stocks.append({
                    "tier": tier_name,
                    "ticker": ticker,
                    "name": name,
                    "price": current,
                    "change": change,
                    "score": score,
                    "grade": grade,
                    "description": desc,
                    "expected_return_3m": prediction.get("expected_return_3m", 0),
                    "expected_return_6m": prediction.get("expected_return_6m", 0),
                    "buy_timing": prediction.get("buy_timing", ""),
                    "risk_level": prediction.get("risk_level", "medium"),
                })

            except Exception as e:
                print(f"{name:<12} {'조회실패':>12} {'-':>10} {'-':>6} {'-':>4} {desc:<15}")
                logger.error(f"{ticker} 분석 실패: {e}")

    # 추천 종목 (점수 상위)
    if all_stocks:
        print("\n" + "="*70)
        print("  ⭐ 추천 종목 (점수 상위)")
        print("="*70)

        sorted_stocks = sorted(all_stocks, key=lambda x: x.get("score", 0), reverse=True)
        for i, stock in enumerate(sorted_stocks[:5], 1):
            tier_emoji = {"tier1": "🥇", "tier2": "🥈", "tier3": "🥉"}.get(stock["tier"], "")
            print(f"\n{i}. {tier_emoji} {stock['name']} ({stock['ticker']})")
            print(f"   현재가: {stock['price']:,}원 ({stock['change']:+,})")
            print(f"   점수: {stock['score']:.1f}/100 | 등급: {stock['grade']}")
            print(f"   설명: {stock['description']}")
            
            # 예상 수익률 추가 표시
            if 'expected_return_3m' in stock and 'expected_return_6m' in stock:
                print(f"   📈 예상 수익률: 3개월 {stock['expected_return_3m']:+.1f}% | 6개월 {stock['expected_return_6m']:+.1f}%")
            if 'buy_timing' in stock:
                print(f"   💡 {stock['buy_timing']}")

    return all_stocks


def main():
    """30개 테마 추천 시스템"""
    print("="*70)
    print("  🔍 관련주 찾기 + 분석 시스템 (30개 테마)")
    print("="*70)
    
    # 지원 테마 목록 (30개)
    themes = [
        ("2차전지", "🔋"),
        ("AI", "🤖"),
        ("반도체", "💾"),
        ("자율주행", "🚗"),
        ("전기차", "⚡"),
        ("바이오", "🧬"),
        ("헬스케어", "💊"),
        ("로봇", "🦾"),
        ("5G", "📡"),
        ("우주항공", "🚀"),
        ("친환경", "🌱"),
        ("수소에너지", "💧"),
        ("태양광", "☀️"),
        ("풍력", "🌪️"),
        ("메타버스", "🥽"),
        ("블록체인", "⛓️"),
        ("NFT", "🎨"),
        ("게임", "🎮"),
        ("엔터테인먼트", "🎵"),
        ("콘텐츠", "📺"),
        ("방산", "🛡️"),
        ("건설", "🏗️"),
        ("부동산", "🏢"),
        ("금융", "💰"),
        ("보험", "🏦"),
        ("유통", "🛒"),
        ("패션", "👗"),
        ("식품", "🍔"),
        ("화장품", "💄"),
        ("관광", "✈️"),
    ]
    
    print("\n📋 지원 테마 목록:")
    for i, (theme, emoji) in enumerate(themes, 1):
        print(f"{i:2d}. {emoji} {theme}", end="  ")
        if i % 5 == 0:
            print()
    print("\n")
    
    print("지원 종목: 삼성전자(005930), SK하이닉스(000660), 엔비디아(NVDA), 테슬라(TSLA)")

    # 1. 삼성전자 관련주
    print("\n\n" + "🇰🇷 삼성전자 관련주 ".center(70, "="))
    analyze_related_stocks("005930", is_theme=False)

    # 2. AI 테마 관련주
    print("\n\n" + "🤖 AI 테마 관련주 ".center(70, "="))
    analyze_related_stocks("AI", is_theme=True)

    # 3. 2차전지 테마 관련주
    print("\n\n" + "🔋 2차전지 테마 관련주 ".center(70, "="))
    analyze_related_stocks("2차전지", is_theme=True)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="관련주 찾기")
    parser.add_argument("--ticker", type=str, help="종목코드 (예: 005930)")
    parser.add_argument("--theme", type=str, help="테마명 (예: AI, 2차전지)")

    args = parser.parse_args()

    if args.ticker:
        analyze_related_stocks(args.ticker, is_theme=False)
    elif args.theme:
        analyze_related_stocks(args.theme, is_theme=True)
    else:
        main()
