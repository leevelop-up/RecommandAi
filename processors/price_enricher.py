"""
실시간 가격 정보 보강 모듈
AI 추천 결과에 실시간 주가 데이터를 추가
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List
from loguru import logger
from scrapers.korea.naver_scraper import NaverFinanceScraper
from scrapers.usa.yahoo_scraper import YahooFinanceScraper


class PriceEnricher:
    """AI 추천 결과에 실시간 가격 정보 추가"""

    def __init__(self):
        self.naver = NaverFinanceScraper()
        self.yahoo = YahooFinanceScraper()

    def enrich_recommendations(self, ai_result: Dict) -> Dict:
        """
        AI 추천 결과에 실시간 가격 정보 추가

        Args:
            ai_result: AI 엔진이 생성한 추천 결과

        Returns:
            가격 정보가 추가된 추천 결과
        """
        logger.info("실시간 가격 정보 추가 중...")

        # 한국 종목 가격 추가
        korea_recs = ai_result.get("recommendations", {}).get("korea", [])
        enriched_korea = self._enrich_korea_stocks(korea_recs)

        # 미국 종목 가격 추가
        usa_recs = ai_result.get("recommendations", {}).get("usa", [])
        enriched_usa = self._enrich_usa_stocks(usa_recs)

        # 결과 업데이트
        ai_result["recommendations"]["korea"] = enriched_korea
        ai_result["recommendations"]["usa"] = enriched_usa

        # Top picks도 업데이트
        if "top_picks" in ai_result:
            ai_result["top_picks"] = self._enrich_top_picks(
                ai_result["top_picks"],
                enriched_korea,
                enriched_usa
            )

        logger.info(f"가격 정보 추가 완료: 한국 {len(enriched_korea)}개, 미국 {len(enriched_usa)}개")
        return ai_result

    def _enrich_korea_stocks(self, stocks: List[Dict]) -> List[Dict]:
        """한국 종목에 실시간 가격 추가"""
        enriched = []

        for stock in stocks:
            ticker = stock.get("ticker", "")
            if not ticker:
                enriched.append(stock)
                continue

            try:
                # Naver Finance에서 실시간 가격 가져오기
                price_data = self.naver.get_realtime_price(ticker)

                if price_data:
                    stock["price"] = price_data.get("current_price", 0)
                    stock["change"] = price_data.get("change", 0)
                    stock["changePercent"] = price_data.get("change_rate", 0)
                    stock["marketCap"] = price_data.get("market_cap", "N/A")
                    stock["volume"] = price_data.get("volume", 0)

                    # 추가 정보
                    if "high" in price_data:
                        stock["high"] = price_data["high"]
                    if "low" in price_data:
                        stock["low"] = price_data["low"]
                    if "prev_close" in price_data:
                        stock["prevClose"] = price_data["prev_close"]
                else:
                    logger.warning(f"가격 정보 없음: {stock.get('name', ticker)}")
                    stock["price"] = 0
                    stock["change"] = 0
                    stock["changePercent"] = 0

            except Exception as e:
                logger.error(f"가격 정보 가져오기 실패 ({ticker}): {e}")
                stock["price"] = 0
                stock["change"] = 0
                stock["changePercent"] = 0

            enriched.append(stock)

        return enriched

    def _enrich_usa_stocks(self, stocks: List[Dict]) -> List[Dict]:
        """미국 종목에 실시간 가격 추가"""
        enriched = []

        for stock in stocks:
            ticker = stock.get("ticker", "")
            if not ticker:
                enriched.append(stock)
                continue

            try:
                # Yahoo Finance에서 실시간 가격 가져오기
                price_data = self.yahoo.get_current_price(ticker)

                if price_data:
                    stock["price"] = price_data.get("current_price", 0)
                    stock["change"] = price_data.get("change", 0)
                    stock["changePercent"] = price_data.get("change_percent", 0)
                    stock["marketCap"] = price_data.get("market_cap", "N/A")
                    stock["volume"] = price_data.get("volume", 0)

                    # 펀더멘탈 데이터 추가
                    if price_data.get("pe_ratio"):
                        stock["per"] = round(price_data["pe_ratio"], 1)
                    if price_data.get("dividend_yield") is not None:
                        # yfinance dividendYield is already in percentage (0.85 = 0.85%)
                        stock["dividend_yield"] = round(price_data["dividend_yield"], 2)
                    if price_data.get("sector"):
                        stock["sector"] = price_data["sector"]
                    if price_data.get("industry"):
                        stock["industry"] = price_data["industry"]
                else:
                    logger.warning(f"가격 정보 없음: {stock.get('name', ticker)}")
                    stock["price"] = 0
                    stock["change"] = 0
                    stock["changePercent"] = 0

            except Exception as e:
                logger.error(f"가격 정보 가져오기 실패 ({ticker}): {e}")
                stock["price"] = 0
                stock["change"] = 0
                stock["changePercent"] = 0

            enriched.append(stock)

        return enriched

    def _enrich_top_picks(self, top_picks: List[Dict], korea_stocks: List[Dict], usa_stocks: List[Dict]) -> List[Dict]:
        """Top picks에 가격 정보 추가"""
        # 가격 정보를 ticker 기준으로 매핑
        price_map = {}

        for stock in korea_stocks + usa_stocks:
            ticker = stock.get("ticker")
            if ticker:
                price_map[ticker] = {
                    "price": stock.get("price", 0),
                    "change": stock.get("change", 0),
                    "changePercent": stock.get("changePercent", 0),
                    "marketCap": stock.get("marketCap", "N/A"),
                }

        # Top picks 업데이트
        enriched = []
        for pick in top_picks:
            ticker = pick.get("ticker")
            if ticker in price_map:
                pick.update(price_map[ticker])
            enriched.append(pick)

        return enriched

    def enrich_growth_predictions(self, growth_result: Dict) -> Dict:
        """급등 예측 결과에 실시간 가격 추가"""
        logger.info("급등 예측 종목에 가격 정보 추가 중...")

        # 한국 급등 예측
        korea_picks = growth_result.get("korea_picks", [])
        enriched_korea = self._enrich_korea_stocks(korea_picks)
        growth_result["korea_picks"] = enriched_korea

        # 미국 급등 예측
        usa_picks = growth_result.get("usa_picks", [])
        enriched_usa = self._enrich_usa_stocks(usa_picks)
        growth_result["usa_picks"] = enriched_usa

        # 테마 종목들
        theme_picks = growth_result.get("theme_picks", [])
        for theme in theme_picks:
            if "top_stocks" in theme and isinstance(theme["top_stocks"], list):
                enriched_theme_stocks = []
                for stock in theme["top_stocks"]:
                    if isinstance(stock, dict) and "ticker" in stock:
                        # 종목 정보가 있는 경우
                        country = stock.get("country", "KR")
                        if country == "KR":
                            enriched = self._enrich_korea_stocks([stock])
                        else:
                            enriched = self._enrich_usa_stocks([stock])
                        enriched_theme_stocks.extend(enriched)
                    else:
                        # 단순 문자열인 경우
                        enriched_theme_stocks.append(stock)
                theme["top_stocks"] = enriched_theme_stocks

        logger.info("급등 예측 가격 정보 추가 완료")
        return growth_result
