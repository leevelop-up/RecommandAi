"""
Yahoo Finance 스크래퍼
미국 주식 데이터 수집 (yfinance 라이브러리 사용)
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from loguru import logger


class YahooFinanceScraper:
    """Yahoo Finance 데이터 스크래퍼"""

    # 인기 미국 주식 티커
    POPULAR_TICKERS = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META",
        "TSLA", "NVDA", "JPM", "V", "JNJ",
        "WMT", "PG", "MA", "UNH", "HD",
        "DIS", "PYPL", "ADBE", "NFLX", "CRM",
    ]

    def __init__(self):
        pass

    def get_stock_info(self, ticker: str) -> Dict:
        """
        종목 기본 정보 조회

        Args:
            ticker: 종목 티커 (예: AAPL, MSFT)

        Returns:
            종목 정보 딕셔너리
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            result = {
                "ticker": ticker,
                "name": info.get("longName", ""),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "country": info.get("country", ""),
                "website": info.get("website", ""),
                "description": info.get("longBusinessSummary", ""),
                "market_cap": info.get("marketCap", 0),
                "enterprise_value": info.get("enterpriseValue", 0),
                "employees": info.get("fullTimeEmployees", 0),
            }

            logger.info(f"{ticker} 종목 정보 조회 완료")
            return result

        except Exception as e:
            logger.error(f"{ticker} 종목 정보 조회 실패: {e}")
            return {}

    def get_current_price(self, ticker: str) -> Dict:
        """
        현재가 정보 조회

        Args:
            ticker: 종목 티커

        Returns:
            현재가 정보 딕셔너리
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            result = {
                "ticker": ticker,
                "name": info.get("longName", ""),
                "current_price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
                "previous_close": info.get("previousClose", 0),
                "open": info.get("open", info.get("regularMarketOpen", 0)),
                "high": info.get("dayHigh", info.get("regularMarketDayHigh", 0)),
                "low": info.get("dayLow", info.get("regularMarketDayLow", 0)),
                "volume": info.get("volume", info.get("regularMarketVolume", 0)),
                "avg_volume": info.get("averageVolume", 0),
                "market_cap": info.get("marketCap", 0),
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh", 0),
                "fifty_two_week_low": info.get("fiftyTwoWeekLow", 0),
                # 펀더멘탈 데이터 추가
                "pe_ratio": info.get("trailingPE", 0),
                "forward_pe": info.get("forwardPE", 0),
                "dividend_yield": info.get("dividendYield", 0),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
            }

            # 변동률 계산
            if result["previous_close"] and result["current_price"]:
                change = result["current_price"] - result["previous_close"]
                change_percent = (change / result["previous_close"]) * 100
                result["change"] = round(change, 2)
                result["change_percent"] = round(change_percent, 2)

            logger.info(f"{ticker} 현재가 조회 완료")
            return result

        except Exception as e:
            logger.error(f"{ticker} 현재가 조회 실패: {e}")
            return {}

    def get_historical_data(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        과거 주가 데이터 조회

        Args:
            ticker: 종목 티커
            period: 기간 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: 간격 (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

        Returns:
            OHLCV DataFrame
        """
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval)

            if not df.empty:
                df = df.reset_index()
                df["ticker"] = ticker
                df.columns = [col.lower().replace(" ", "_") for col in df.columns]

            logger.info(f"{ticker} 과거 데이터 조회 완료: {len(df)}개")
            return df

        except Exception as e:
            logger.error(f"{ticker} 과거 데이터 조회 실패: {e}")
            return pd.DataFrame()

    def get_fundamentals(self, ticker: str) -> Dict:
        """
        펀더멘탈 데이터 조회

        Args:
            ticker: 종목 티커

        Returns:
            펀더멘탈 정보 딕셔너리
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            result = {
                "ticker": ticker,
                "pe_ratio": info.get("trailingPE", 0),
                "forward_pe": info.get("forwardPE", 0),
                "peg_ratio": info.get("pegRatio", 0),
                "pb_ratio": info.get("priceToBook", 0),
                "ps_ratio": info.get("priceToSalesTrailing12Months", 0),
                "eps": info.get("trailingEps", 0),
                "forward_eps": info.get("forwardEps", 0),
                "dividend_yield": info.get("dividendYield", 0),
                "dividend_rate": info.get("dividendRate", 0),
                "payout_ratio": info.get("payoutRatio", 0),
                "profit_margin": info.get("profitMargins", 0),
                "operating_margin": info.get("operatingMargins", 0),
                "roe": info.get("returnOnEquity", 0),
                "roa": info.get("returnOnAssets", 0),
                "revenue": info.get("totalRevenue", 0),
                "revenue_growth": info.get("revenueGrowth", 0),
                "gross_profit": info.get("grossProfits", 0),
                "ebitda": info.get("ebitda", 0),
                "net_income": info.get("netIncomeToCommon", 0),
                "debt_to_equity": info.get("debtToEquity", 0),
                "current_ratio": info.get("currentRatio", 0),
                "quick_ratio": info.get("quickRatio", 0),
                "free_cash_flow": info.get("freeCashflow", 0),
                "beta": info.get("beta", 0),
            }

            logger.info(f"{ticker} 펀더멘탈 조회 완료")
            return result

        except Exception as e:
            logger.error(f"{ticker} 펀더멘탈 조회 실패: {e}")
            return {}

    def get_financials(self, ticker: str) -> Dict:
        """
        재무제표 데이터 조회

        Args:
            ticker: 종목 티커

        Returns:
            재무제표 딕셔너리 (income_statement, balance_sheet, cash_flow)
        """
        try:
            stock = yf.Ticker(ticker)

            result = {
                "ticker": ticker,
                "income_statement": stock.income_stmt.to_dict() if not stock.income_stmt.empty else {},
                "balance_sheet": stock.balance_sheet.to_dict() if not stock.balance_sheet.empty else {},
                "cash_flow": stock.cashflow.to_dict() if not stock.cashflow.empty else {},
            }

            logger.info(f"{ticker} 재무제표 조회 완료")
            return result

        except Exception as e:
            logger.error(f"{ticker} 재무제표 조회 실패: {e}")
            return {}

    def get_analyst_recommendations(self, ticker: str) -> List[Dict]:
        """
        애널리스트 추천 조회

        Args:
            ticker: 종목 티커

        Returns:
            추천 리스트
        """
        try:
            stock = yf.Ticker(ticker)
            recommendations = stock.recommendations

            if recommendations is not None and not recommendations.empty:
                df = recommendations.tail(10).reset_index()
                result = df.to_dict("records")
                logger.info(f"{ticker} 애널리스트 추천 조회 완료")
                return result

            return []

        except Exception as e:
            logger.error(f"{ticker} 애널리스트 추천 조회 실패: {e}")
            return []

    def get_news(self, ticker: str) -> List[Dict]:
        """
        종목 관련 뉴스 조회

        Args:
            ticker: 종목 티커

        Returns:
            뉴스 리스트
        """
        try:
            stock = yf.Ticker(ticker)
            news = stock.news

            result = []
            for item in news[:10]:  # 최근 10개
                # 새로운 yfinance 구조: content 안에 데이터가 있음
                content = item.get("content", item)  # content가 없으면 item 자체 사용

                # provider 정보 추출
                provider = content.get("provider", {})
                publisher = provider.get("displayName", "") if isinstance(provider, dict) else ""

                # thumbnail 추출
                thumbnail = content.get("thumbnail", {})
                thumb_url = ""
                if thumbnail and isinstance(thumbnail, dict):
                    resolutions = thumbnail.get("resolutions", [])
                    if resolutions and len(resolutions) > 0:
                        thumb_url = resolutions[0].get("url", "")

                result.append({
                    "title": content.get("title", ""),
                    "publisher": publisher,
                    "link": content.get("canonicalUrl", {}).get("url", "") or content.get("clickThroughUrl", {}).get("url", ""),
                    "published": content.get("pubDate", ""),
                    "summary": content.get("summary", ""),
                    "thumbnail": thumb_url,
                })

            logger.info(f"{ticker} 뉴스 조회 완료: {len(result)}개")
            return result

        except Exception as e:
            logger.error(f"{ticker} 뉴스 조회 실패: {e}")
            return []

    def get_multiple_prices(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        여러 종목의 현재가 한번에 조회

        Args:
            tickers: 종목 티커 리스트

        Returns:
            {ticker: price_info} 딕셔너리
        """
        result = {}
        for ticker in tickers:
            result[ticker] = self.get_current_price(ticker)
        return result

    def get_market_summary(self) -> Dict:
        """
        주요 지수 및 시장 요약 조회

        Returns:
            시장 요약 딕셔너리
        """
        indices = {
            "^GSPC": "S&P 500",
            "^DJI": "Dow Jones",
            "^IXIC": "NASDAQ",
            "^RUT": "Russell 2000",
            "^VIX": "VIX",
        }

        result = {}
        for ticker, name in indices.items():
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                result[name] = {
                    "ticker": ticker,
                    "price": info.get("regularMarketPrice", 0),
                    "change": info.get("regularMarketChange", 0),
                    "change_percent": info.get("regularMarketChangePercent", 0),
                }
            except Exception as e:
                logger.error(f"{ticker} 지수 조회 실패: {e}")

        return result

    def get_all_stock_data(self, ticker: str) -> Dict:
        """
        종목의 모든 데이터를 한번에 조회

        Args:
            ticker: 종목 티커

        Returns:
            종합 데이터 딕셔너리
        """
        return {
            "ticker": ticker,
            "info": self.get_stock_info(ticker),
            "price": self.get_current_price(ticker),
            "fundamentals": self.get_fundamentals(ticker),
            "news": self.get_news(ticker),
            "recommendations": self.get_analyst_recommendations(ticker),
            "updated_at": datetime.now().isoformat(),
        }
