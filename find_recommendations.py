"""
추천 종목 찾기
여러 종목을 분석하여 투자 추천 종목을 찾습니다.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from processors.analyzer import StockAnalyzer, print_analysis_report


def find_best_stocks():
    """관심 종목 중 추천 종목 찾기"""

    analyzer = StockAnalyzer()

    # 분석할 종목 리스트
    korea_stocks = [
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

    usa_stocks = [
        "AAPL",   # Apple
        "MSFT",   # Microsoft
        "GOOGL",  # Alphabet
        "AMZN",   # Amazon
        "TSLA",   # Tesla
        "NVDA",   # NVIDIA
        "META",   # Meta
        "JPM",    # JPMorgan
        "V",      # Visa
    ]

    print("="*70)
    print("  🔍 주식 추천 시스템 - 종목 분석 중...")
    print("="*70)

    # 분석 실행
    results = analyzer.find_recommendations(
        korea_tickers=korea_stocks,
        usa_tickers=usa_stocks,
        min_score=55,  # 55점 이상만 추천
    )

    # 한국 주식 결과
    print("\n" + "="*70)
    print("  🇰🇷 한국 주식 분석 결과")
    print("="*70)
    print(f"\n{'종목':<15} {'현재가':>12} {'변동':>10} {'점수':>6} {'등급':>4} {'추천':>10}")
    print("-"*70)

    for stock in sorted(results["korea_stocks"], key=lambda x: x["score"], reverse=True):
        price = stock["price"]
        rec = stock["recommendation"]
        current = price.get("current_price", 0)
        change = price.get("change", 0)

        print(f"{stock['name']:<15} {current:>12,}원 {change:>+10,} {stock['score']:>6} {rec['grade']:>4} {rec['action']:>10}")

    # 미국 주식 결과
    print("\n" + "="*70)
    print("  🇺🇸 미국 주식 분석 결과")
    print("="*70)
    print(f"\n{'종목':<15} {'현재가':>12} {'변동률':>10} {'점수':>6} {'등급':>4} {'추천':>10}")
    print("-"*70)

    for stock in sorted(results["usa_stocks"], key=lambda x: x["score"], reverse=True):
        price = stock["price"]
        rec = stock["recommendation"]
        current = price.get("current_price", 0)
        change_rate = price.get("change_rate", 0)

        name = stock.get("name", stock["ticker"])[:12]
        print(f"{name:<15} ${current:>11.2f} {change_rate:>+9.2f}% {stock['score']:>6} {rec['grade']:>4} {rec['action']:>10}")

    # 추천 종목
    print("\n" + "="*70)
    print("  ⭐ 추천 종목 TOP 5")
    print("="*70)

    for i, stock in enumerate(results["recommendations"][:5], 1):
        rec = stock["recommendation"]
        country = "🇰🇷" if stock["country"] == "KR" else "🇺🇸"

        print(f"\n{i}. {country} {stock['name']} ({stock['ticker']})")
        print(f"   점수: {stock['score']}/100 | 등급: {rec['grade']} | {rec['action']}")
        print(f"   분석:")
        for a in stock["analysis"][:3]:
            print(f"   {a}")

    # 상세 리포트 (1위 종목)
    if results["recommendations"]:
        print("\n" + "="*70)
        print("  📋 1위 종목 상세 리포트")
        print_analysis_report(results["recommendations"][0])

    return results


if __name__ == "__main__":
    find_best_stocks()
