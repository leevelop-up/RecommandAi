"""
AI 기반 주식 분석기
종목 데이터 + 뉴스를 분석하여 투자 인사이트 제공
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger

from scrapers.korea.krx_scraper import KRXScraper
from scrapers.korea.naver_scraper import NaverFinanceScraper
from scrapers.usa.yahoo_scraper import YahooFinanceScraper
from scrapers.news.news_scraper import GoogleNewsRSS


class StockAnalyzer:
    """주식 분석기 - 데이터 수집 및 분석"""

    def __init__(self):
        self.krx = KRXScraper()
        self.naver = NaverFinanceScraper(delay=0.3)
        self.yahoo = YahooFinanceScraper()
        self.news = GoogleNewsRSS()

    def analyze_korea_stock(self, ticker: str, name: str = "") -> Dict:
        """
        한국 종목 종합 분석

        Args:
            ticker: 종목 코드
            name: 종목명 (뉴스 검색용)

        Returns:
            종합 분석 결과
        """
        logger.info(f"[분석 시작] {name}({ticker})")

        # 1. 기본 정보 수집
        price_data = self.naver.get_realtime_price(ticker)
        stock_info = self.naver.get_stock_info(ticker)
        fundamental = self.krx.get_fundamental(ticker)

        # 2. 뉴스 수집
        search_query = name if name else ticker
        news_list = self.news.search(f"{search_query} 주식", max_results=5)

        # 3. 분석 점수 계산
        score, analysis = self._calculate_score_korea(price_data, stock_info, fundamental, news_list)

        result = {
            "ticker": ticker,
            "name": name or price_data.get("name", ""),
            "country": "KR",
            "price": price_data,
            "fundamental": fundamental,
            "news": news_list,
            "score": score,
            "analysis": analysis,
            "recommendation": self._get_recommendation(score),
            "analyzed_at": datetime.now().isoformat(),
        }

        logger.info(f"[분석 완료] {name}({ticker}) - 점수: {score}/100")
        return result

    def analyze_usa_stock(self, ticker: str) -> Dict:
        """
        미국 종목 종합 분석

        Args:
            ticker: 종목 티커

        Returns:
            종합 분석 결과
        """
        logger.info(f"[분석 시작] {ticker}")

        # 1. 기본 정보 수집
        price_data = self.yahoo.get_current_price(ticker)
        fundamental = self.yahoo.get_fundamentals(ticker)
        stock_info = self.yahoo.get_stock_info(ticker)

        # 2. 뉴스 수집
        news_list = self.yahoo.get_news(ticker)

        # 3. 분석 점수 계산
        score, analysis = self._calculate_score_usa(price_data, fundamental, news_list)

        result = {
            "ticker": ticker,
            "name": stock_info.get("name", ""),
            "country": "US",
            "sector": stock_info.get("sector", ""),
            "price": price_data,
            "fundamental": fundamental,
            "news": news_list[:5],
            "score": score,
            "analysis": analysis,
            "recommendation": self._get_recommendation(score),
            "analyzed_at": datetime.now().isoformat(),
        }

        logger.info(f"[분석 완료] {ticker} - 점수: {score}/100")
        return result

    def _calculate_score_korea(
        self,
        price: Dict,
        info: Dict,
        fundamental: Dict,
        news: List[Dict],
    ) -> tuple:
        """한국 종목 점수 계산"""
        score = 50  # 기본 점수
        analysis = []

        # 1. PER 분석 (0~20점)
        per = fundamental.get("per", 0)
        if per:
            if 0 < per < 10:
                score += 20
                analysis.append(f"✅ PER {per:.1f} - 저평가 (매력적)")
            elif 10 <= per < 15:
                score += 15
                analysis.append(f"✅ PER {per:.1f} - 적정 수준")
            elif 15 <= per < 25:
                score += 5
                analysis.append(f"⚠️ PER {per:.1f} - 다소 높음")
            else:
                score -= 5
                analysis.append(f"❌ PER {per:.1f} - 고평가 주의")

        # 2. PBR 분석 (0~15점)
        pbr = fundamental.get("pbr", 0)
        if pbr:
            if 0 < pbr < 1:
                score += 15
                analysis.append(f"✅ PBR {pbr:.2f} - 자산가치 대비 저평가")
            elif 1 <= pbr < 2:
                score += 10
                analysis.append(f"✅ PBR {pbr:.2f} - 적정 수준")
            elif 2 <= pbr < 5:
                score += 0
                analysis.append(f"⚠️ PBR {pbr:.2f} - 다소 높음")
            else:
                score -= 5
                analysis.append(f"❌ PBR {pbr:.2f} - 고평가 주의")

        # 3. 주가 변동 분석 (0~15점)
        change = price.get("change", 0)
        change_rate = price.get("change_rate", 0)
        if change > 0:
            if change_rate and change_rate > 3:
                score += 10
                analysis.append(f"📈 금일 +{change_rate:.1f}% 상승 (강한 상승세)")
            else:
                score += 5
                analysis.append(f"📈 금일 상승 중")
        elif change < 0:
            if change_rate and abs(change_rate) > 3:
                score -= 5
                analysis.append(f"📉 금일 {change_rate:.1f}% 하락 (매수 기회?)")
            else:
                analysis.append(f"📉 금일 소폭 하락")

        # 4. 뉴스 분석 (간단한 키워드 기반)
        positive_keywords = ["상승", "호재", "성장", "실적", "흑자", "증가", "신고가", "돌파"]
        negative_keywords = ["하락", "악재", "감소", "적자", "위기", "우려", "급락", "손실"]

        pos_count = 0
        neg_count = 0
        for n in news:
            title = n.get("title", "")
            for kw in positive_keywords:
                if kw in title:
                    pos_count += 1
            for kw in negative_keywords:
                if kw in title:
                    neg_count += 1

        if pos_count > neg_count:
            score += 10
            analysis.append(f"📰 뉴스 긍정적 ({pos_count}개 호재 키워드)")
        elif neg_count > pos_count:
            score -= 10
            analysis.append(f"📰 뉴스 부정적 ({neg_count}개 악재 키워드)")
        else:
            analysis.append(f"📰 뉴스 중립적")

        # 점수 범위 제한
        score = max(0, min(100, score))
        return score, analysis

    def _calculate_score_usa(
        self,
        price: Dict,
        fundamental: Dict,
        news: List[Dict],
    ) -> tuple:
        """미국 종목 점수 계산"""
        score = 50
        analysis = []

        # 1. PER 분석
        per = fundamental.get("pe_ratio", 0)
        if per:
            if 0 < per < 15:
                score += 20
                analysis.append(f"✅ P/E {per:.1f} - 저평가")
            elif 15 <= per < 25:
                score += 10
                analysis.append(f"✅ P/E {per:.1f} - 적정")
            elif 25 <= per < 40:
                score += 0
                analysis.append(f"⚠️ P/E {per:.1f} - 성장주 수준")
            else:
                score -= 10
                analysis.append(f"❌ P/E {per:.1f} - 고평가")

        # 2. 배당 분석
        div_yield = fundamental.get("dividend_yield", 0)
        if div_yield and div_yield > 0.02:
            score += 10
            analysis.append(f"💰 배당수익률 {div_yield*100:.1f}%")

        # 3. 수익성 분석
        roe = fundamental.get("roe", 0)
        if roe and roe > 0.15:
            score += 10
            analysis.append(f"✅ ROE {roe*100:.1f}% - 높은 수익성")
        elif roe and roe > 0.10:
            score += 5
            analysis.append(f"✅ ROE {roe*100:.1f}% - 양호")

        # 4. 주가 변동
        change_rate = price.get("change_rate", 0)
        if change_rate:
            if change_rate > 3:
                score += 5
                analysis.append(f"📈 금일 +{change_rate:.1f}% 상승")
            elif change_rate < -3:
                score -= 5
                analysis.append(f"📉 금일 {change_rate:.1f}% 하락")

        # 5. 52주 고/저 대비
        current = price.get("current_price", 0)
        high_52 = price.get("fifty_two_week_high", 0)
        low_52 = price.get("fifty_two_week_low", 0)
        if current and high_52 and low_52:
            position = (current - low_52) / (high_52 - low_52) * 100 if high_52 != low_52 else 50
            if position < 30:
                score += 10
                analysis.append(f"📊 52주 저점 근처 (저가 매수 기회)")
            elif position > 90:
                score -= 5
                analysis.append(f"📊 52주 고점 근처 (신중 필요)")

        score = max(0, min(100, score))
        return score, analysis

    def _get_recommendation(self, score: int) -> Dict:
        """점수 기반 추천"""
        if score >= 80:
            return {"grade": "A", "action": "적극 매수", "color": "green"}
        elif score >= 65:
            return {"grade": "B", "action": "매수 고려", "color": "lightgreen"}
        elif score >= 50:
            return {"grade": "C", "action": "중립/관망", "color": "yellow"}
        elif score >= 35:
            return {"grade": "D", "action": "매수 보류", "color": "orange"}
        else:
            return {"grade": "F", "action": "매도 고려", "color": "red"}

    def find_recommendations(
        self,
        korea_tickers: List[tuple] = None,
        usa_tickers: List[str] = None,
        min_score: int = 60,
    ) -> Dict:
        """
        여러 종목 분석 후 추천 종목 찾기

        Args:
            korea_tickers: [(ticker, name), ...] 한국 종목 리스트
            usa_tickers: [ticker, ...] 미국 종목 리스트
            min_score: 추천 최소 점수

        Returns:
            분석 결과 및 추천 종목
        """
        results = {
            "analyzed_at": datetime.now().isoformat(),
            "korea_stocks": [],
            "usa_stocks": [],
            "recommendations": [],
        }

        # 한국 종목 분석
        if korea_tickers:
            for ticker, name in korea_tickers:
                try:
                    analysis = self.analyze_korea_stock(ticker, name)
                    results["korea_stocks"].append(analysis)
                    if analysis["score"] >= min_score:
                        results["recommendations"].append(analysis)
                except Exception as e:
                    logger.error(f"{ticker} 분석 실패: {e}")

        # 미국 종목 분석
        if usa_tickers:
            for ticker in usa_tickers:
                try:
                    analysis = self.analyze_usa_stock(ticker)
                    results["usa_stocks"].append(analysis)
                    if analysis["score"] >= min_score:
                        results["recommendations"].append(analysis)
                except Exception as e:
                    logger.error(f"{ticker} 분석 실패: {e}")

        # 점수 순으로 정렬
        results["recommendations"].sort(key=lambda x: x["score"], reverse=True)

        return results


def print_analysis_report(result: Dict):
    """분석 결과 출력"""
    print("\n" + "="*60)
    print(f"  📊 {result['name']} ({result['ticker']}) 분석 리포트")
    print("="*60)

    # 가격 정보
    price = result.get("price", {})
    current = price.get("current_price", 0)
    change = price.get("change", 0)
    change_rate = price.get("change_rate", 0)

    if result["country"] == "KR":
        print(f"\n💹 현재가: {current:,}원 ({change:+,}원, {change_rate:+.2f}%)")
    else:
        print(f"\n💹 현재가: ${current} ({change:+.2f}, {change_rate:+.2f}%)")

    # 펀더멘탈
    fund = result.get("fundamental", {})
    print("\n📈 펀더멘탈:")
    if result["country"] == "KR":
        print(f"  PER: {fund.get('per', 'N/A')} | PBR: {fund.get('pbr', 'N/A')} | EPS: {fund.get('eps', 'N/A')}")
    else:
        print(f"  P/E: {fund.get('pe_ratio', 'N/A')} | P/B: {fund.get('pb_ratio', 'N/A')} | ROE: {fund.get('roe', 'N/A')}")

    # 분석 내용
    print("\n🔍 분석:")
    for item in result.get("analysis", []):
        print(f"  {item}")

    # 뉴스
    print("\n📰 최신 뉴스:")
    for news in result.get("news", [])[:3]:
        print(f"  - {news.get('title', '')[:50]}...")

    # 추천
    rec = result.get("recommendation", {})
    score = result.get("score", 0)
    print(f"\n{'='*60}")
    print(f"  🎯 투자 점수: {score}/100 (등급: {rec.get('grade', 'N/A')})")
    print(f"  💡 추천: {rec.get('action', 'N/A')}")
    print("="*60)


if __name__ == "__main__":
    # 테스트 실행
    analyzer = StockAnalyzer()

    # 한국 종목 분석
    print("\n" + "🇰🇷 한국 주식 분석 ".center(60, "="))
    korea_result = analyzer.analyze_korea_stock("005930", "삼성전자")
    print_analysis_report(korea_result)

    # 미국 종목 분석
    print("\n" + "🇺🇸 미국 주식 분석 ".center(60, "="))
    usa_result = analyzer.analyze_usa_stock("AAPL")
    print_analysis_report(usa_result)
