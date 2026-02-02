"""
금주 추천 실행 스크립트
- 08:00 데이터 수집
- 09:00 추천 생성 (Gemini + Groq 듀얼 AI)

실행 방법:
    python run_weekly_recommendation.py
    python run_weekly_recommendation.py --output-dir custom_output
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import argparse
from datetime import datetime
from pathlib import Path
from loguru import logger

from config.settings import get_settings
from processors.enhanced_data_collector import EnhancedDataCollector
from processors.weekly_recommender import WeeklyRecommender


def setup_logger():
    """로거 설정"""
    logger.remove()
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    logger.add(sys.stderr, level="INFO",
               format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:<7}</level> | <level>{message}</level>")
    logger.add(log_dir / "weekly_recommendation_{time:YYYYMMDD}.log",
               level="DEBUG", rotation="1 day", retention="30 days",
               format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {message}")


def save_results(result: dict, output_dir: Path):
    """결과 저장"""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON 저장
    json_file = output_dir / f"weekly_recommendation_{timestamp}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f"💾 JSON 저장: {json_file}")

    # 텍스트 리포트 생성
    txt_file = output_dir / f"weekly_recommendation_{timestamp}.txt"
    with open(txt_file, "w", encoding="utf-8") as f:
        write_text_report(f, result)
    logger.info(f"📄 텍스트 리포트 저장: {txt_file}")

    return json_file, txt_file


def write_text_report(f, result: dict):
    """텍스트 리포트 작성"""
    f.write("=" * 100 + "\n")
    f.write("  📊 금주 주식 추천 리포트\n")
    f.write("=" * 100 + "\n")
    f.write(f"생성 시간: {result.get('generated_at', 'N/A')}\n")
    f.write(f"추천 시간: {result.get('schedule_time', '09:00')}\n")
    f.write("=" * 100 + "\n\n")

    # 시장 개요
    market = result.get("market_overview", {})
    if market:
        f.write("\n" + "=" * 100 + "\n")
        f.write("🌍 시장 개요\n")
        f.write("=" * 100 + "\n\n")

        korea = market.get("korea", {})
        if korea:
            f.write("📊 한국 시장\n")
            f.write("-" * 100 + "\n")
            for name, info in korea.items():
                val = info.get("value", "N/A")
                chg = info.get("change", "N/A")
                chg_rate = info.get("change_rate", "N/A")
                f.write(f"  {name}: {val} | 전일대비: {chg} ({chg_rate}%)\n")
            f.write("\n")

        usa = market.get("usa", {})
        if usa:
            f.write("📊 미국 시장\n")
            f.write("-" * 100 + "\n")
            for name, info in usa.items():
                price = info.get("price", "N/A")
                chg = info.get("change", "N/A")
                chg_pct = info.get("change_percent", "N/A")
                f.write(f"  {name}: ${price} | 전일대비: {chg} ({chg_pct}%)\n")
            f.write("\n")

    # Hot 테마
    hot_themes = result.get("hot_themes", [])
    if hot_themes:
        f.write("\n" + "=" * 100 + "\n")
        f.write("🔥 HOT 테마 TOP 10\n")
        f.write("=" * 100 + "\n\n")

        for theme in hot_themes[:10]:
            f.write(f"{theme['rank']}. {theme['name']}\n")
            f.write(f"   점수: {theme['score']}/100 | 등락률: {theme['change_rate']} | 종목 수: {theme['stock_count']}개\n")

            # 1차 관련주
            tier1 = theme.get("tier1_stocks", [])
            if tier1:
                tier1_names = [f"{s['name']}({s.get('change_rate', 'N/A')})" for s in tier1[:5]]
                f.write(f"   🥇 1차 관련주 (핵심): {', '.join(tier1_names)}\n")

            # 2차 관련주
            tier2 = theme.get("tier2_stocks", [])
            if tier2:
                tier2_names = [s['name'] for s in tier2[:5]]
                f.write(f"   🥈 2차 관련주: {', '.join(tier2_names)}\n")

            # 3차 관련주
            tier3 = theme.get("tier3_stocks", [])
            if tier3:
                tier3_names = [s['name'] for s in tier3[:5]]
                f.write(f"   🥉 3차 관련주: {', '.join(tier3_names)}\n")

            # 뉴스
            news = theme.get("news", [])
            if news:
                f.write(f"   📰 최신 뉴스:\n")
                for n in news[:3]:
                    f.write(f"     · {n.get('title', '')[:80]}\n")

            f.write("\n")

    # 금주 추천 종목 30개
    weekly = result.get("weekly_recommendations", [])
    if weekly:
        f.write("\n" + "=" * 100 + "\n")
        f.write("📈 금주 추천 종목 30개\n")
        f.write("=" * 100 + "\n\n")

        # 한국 종목과 미국 종목 분리
        korea_stocks = [s for s in weekly if s['country'] == 'KR']
        usa_stocks = [s for s in weekly if s['country'] == 'US']

        if korea_stocks:
            f.write("🇰🇷 한국 종목\n")
            f.write("-" * 100 + "\n")
            for i, stock in enumerate(korea_stocks, 1):
                f.write(f"\n{i}. {stock['name']} ({stock['ticker']})\n")
                f.write(f"   현재가: {stock['current_price']:,}원 | 전일대비: {stock['daily_change_rate']}\n")
                f.write(f"   시가총액: {stock['market_cap']} | PER: {stock['per']} | PBR: {stock.get('pbr', 'N/A')} | 배당률: {stock['dividend_yield']}\n")
                f.write(f"   섹터: {stock.get('sector', 'N/A')} | 거래량: {stock.get('volume', 0):,}\n")

                # 애널리스트 평가
                rating = stock.get("analyst_rating", {})
                if rating and rating.get("rating"):
                    f.write(f"   애널리스트: {rating.get('rating', 'N/A')}")
                    if rating.get("target_price"):
                        f.write(f" | 목표가: {rating['target_price']}")
                    f.write("\n")

                # 차트 정보
                chart = stock.get("chart_6m", {})
                if chart.get("available"):
                    f.write(f"   6개월 차트: 고가 {chart.get('high_6m', 0):,}원 | 저가 {chart.get('low_6m', 0):,}원\n")

                # 투자 포인트
                points = stock.get("investment_points", [])
                if points:
                    f.write(f"   💡 투자 포인트:\n")
                    for point in points[:3]:
                        f.write(f"     · {point[:80]}\n")

                # 뉴스
                news = stock.get("news", [])
                if news:
                    f.write(f"   📰 최근 뉴스:\n")
                    for n in news[:2]:
                        f.write(f"     · {n.get('title', '')[:70]}\n")

        if usa_stocks:
            f.write("\n\n🇺🇸 미국 종목\n")
            f.write("-" * 100 + "\n")
            for i, stock in enumerate(usa_stocks, 1):
                f.write(f"\n{i}. {stock['name']} ({stock['ticker']})\n")
                f.write(f"   현재가: ${stock['current_price']:,.2f} | 전일대비: {stock['daily_change_rate']}\n")
                f.write(f"   시가총액: {stock['market_cap']} | PER: {stock['per']} | PBR: {stock.get('pbr', 'N/A')} | 배당률: {stock['dividend_yield']}\n")
                f.write(f"   섹터: {stock.get('sector', 'N/A')} | 거래량: {stock.get('volume', 0):,}\n")

                # 애널리스트 평가
                rating = stock.get("analyst_rating", {})
                if rating and rating.get("rating"):
                    f.write(f"   애널리스트: {rating.get('rating', 'N/A')}")
                    if rating.get("target_price"):
                        f.write(f" | 목표가: {rating['target_price']}")
                    f.write("\n")

                # 차트 정보
                chart = stock.get("chart_6m", {})
                if chart.get("available"):
                    f.write(f"   52주 차트: 고가 ${chart.get('high_52w', 0):,.2f} | 저가 ${chart.get('low_52w', 0):,.2f}\n")

                # 투자 포인트
                points = stock.get("investment_points", [])
                if points:
                    f.write(f"   💡 투자 포인트:\n")
                    for point in points[:3]:
                        f.write(f"     · {point[:80]}\n")

                # 뉴스
                news = stock.get("news", [])
                if news:
                    f.write(f"   📰 최근 뉴스:\n")
                    for n in news[:2]:
                        f.write(f"     · {n.get('title', '')[:70]}\n")

    # AI 분석 (Gemini)
    ai_recs = result.get("ai_recommendations", {})

    if "gemini" in ai_recs:
        f.write("\n\n" + "=" * 100 + "\n")
        f.write("🔷 Gemini AI 분석\n")
        f.write("=" * 100 + "\n\n")
        write_ai_analysis(f, ai_recs["gemini"])

    # AI 분석 (Groq)
    if "groq" in ai_recs:
        f.write("\n\n" + "=" * 100 + "\n")
        f.write("⚡ Groq AI 분석\n")
        f.write("=" * 100 + "\n\n")
        write_ai_analysis(f, ai_recs["groq"])


def write_ai_analysis(f, ai_result: dict):
    """AI 분석 결과 작성"""
    # 시장 분석
    market = ai_result.get("market_analysis", {})
    if market:
        f.write("📊 시장 분석\n")
        f.write("-" * 100 + "\n")
        f.write(f"전체 심리: {market.get('overall_sentiment', 'N/A')}\n\n")

        korea_outlook = market.get('korea_outlook', '')
        if korea_outlook:
            f.write(f"🇰🇷 한국 시장 전망:\n")
            f.write(f"   {korea_outlook}\n\n")

        usa_outlook = market.get('usa_outlook', '')
        if usa_outlook:
            f.write(f"🇺🇸 미국 시장 전망:\n")
            f.write(f"   {usa_outlook}\n\n")

        trends = market.get("key_trends", [])
        if trends:
            f.write(f"📈 주요 트렌드:\n")
            for i, trend in enumerate(trends, 1):
                f.write(f"   {i}. {trend}\n")
            f.write("\n")

        risks = market.get("risks", [])
        if risks:
            f.write(f"⚠️ 주요 리스크:\n")
            for i, risk in enumerate(risks, 1):
                f.write(f"   {i}. {risk}\n")
            f.write("\n")

    # 테마 분석
    theme_analysis = ai_result.get("top_themes_analysis", [])
    if theme_analysis:
        f.write("\n🔥 Hot 테마 분석\n")
        f.write("-" * 100 + "\n")
        for i, theme in enumerate(theme_analysis[:5], 1):
            f.write(f"\n{i}. {theme.get('theme', 'N/A')}\n")
            f.write(f"   평가: {theme.get('rating', 'N/A')}\n")
            f.write(f"   분석: {theme.get('reasoning', 'N/A')}\n")
            rec_stocks = theme.get('recommended_stocks', [])
            if rec_stocks:
                f.write(f"   추천 종목: {', '.join(rec_stocks[:5])}\n")
        f.write("\n")

    # TOP 10 추천
    top_picks = ai_result.get("top_10_picks", [])
    if top_picks:
        f.write("\n🏆 TOP 10 추천 종목\n")
        f.write("-" * 100 + "\n\n")

        for pick in top_picks[:10]:
            rank = pick.get('rank', 0)
            name = pick.get('name', 'N/A')
            ticker = pick.get('ticker', 'N/A')
            country = pick.get('country', 'N/A')

            f.write(f"{rank}. {name} ({ticker}) - {country}\n")
            f.write(f"   📊 액션: {pick.get('action', 'N/A')} | 예상수익: {pick.get('target_return', 'N/A')} | 기간: {pick.get('investment_period', 'N/A')}\n")
            f.write(f"   💰 추천매수가: {pick.get('entry_price', 'N/A')} | 목표가: {pick.get('target_price', 'N/A')} | 손절가: {pick.get('stop_loss', 'N/A')}\n")

            reasoning = pick.get('reasoning', '')
            if reasoning:
                f.write(f"   📝 추천근거:\n")
                f.write(f"      {reasoning}\n")
            f.write("\n")

    # 섹터별 추천
    sector_recs = ai_result.get("sector_recommendations", [])
    if sector_recs:
        f.write("\n📊 섹터별 추천\n")
        f.write("-" * 100 + "\n")
        for sector in sector_recs:
            f.write(f"• {sector.get('sector', 'N/A')}: {sector.get('rating', 'N/A')}\n")
            f.write(f"  {sector.get('reasoning', 'N/A')}\n\n")

    # 투자 전략
    strategy = ai_result.get("investment_strategy", "")
    if strategy:
        f.write("\n💡 이번 주 투자 전략\n")
        f.write("-" * 100 + "\n")
        f.write(f"{strategy}\n\n")

    # 위험 경고
    warning = ai_result.get("risk_warning", "")
    if warning:
        f.write("\n⚠️ 위험 경고\n")
        f.write("-" * 100 + "\n")
        f.write(f"{warning}\n\n")


def main():
    parser = argparse.ArgumentParser(description="금주 주식 추천 생성")
    parser.add_argument("--output-dir", type=str, default="output",
                        help="출력 디렉토리 (기본: output)")
    args = parser.parse_args()

    setup_logger()

    logger.info("=" * 100)
    logger.info("  🚀 금주 주식 추천 시스템 시작")
    logger.info("=" * 100)

    try:
        settings = get_settings()

        # 1. 데이터 수집 (08:00 실행 시뮬레이션)
        logger.info("\n[1/3] 데이터 수집 시작 (08:00 예정 작업)")
        collector = EnhancedDataCollector()
        data = collector.collect_weekly_data()
        logger.info("✅ 데이터 수집 완료")

        # 2. AI 추천 생성 (09:00 실행 시뮬레이션)
        logger.info("\n[2/3] AI 추천 생성 시작 (09:00 예정 작업)")
        recommender = WeeklyRecommender(
            gemini_api_key=settings.GEMINI_API_KEY,
            groq_api_key=settings.GROQ_API_KEY,
        )
        result = recommender.generate_weekly_recommendations(data)
        logger.info("✅ AI 추천 생성 완료")

        # 3. 결과 저장
        logger.info("\n[3/3] 결과 저장")
        output_dir = Path(__file__).parent / args.output_dir
        json_file, txt_file = save_results(result, output_dir)

        # 4. DB 저장 (선택적)
        try:
            from db.save_to_db import WeeklyRecommendationDB
            db = WeeklyRecommendationDB()
            rec_id = db.save_weekly_recommendation(str(json_file), str(txt_file))
            db.close()
            logger.info(f"✅ DB 저장 완료: ID={rec_id}")
        except Exception as e:
            logger.warning(f"DB 저장 실패 (파일은 저장됨): {e}")

        logger.info("\n" + "=" * 100)
        logger.info("  ✅ 금주 주식 추천 시스템 완료")
        logger.info("=" * 100)
        logger.info(f"📄 JSON: {json_file}")
        logger.info(f"📄 TXT:  {txt_file}")

    except Exception as e:
        logger.error(f"❌ 실행 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
