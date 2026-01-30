"""
KRX (한국거래소) 데이터 스크래퍼
pykrx 라이브러리를 사용하여 KOSPI/KOSDAQ 데이터 수집
"""
import pandas as pd
from pykrx import stock
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from loguru import logger


class KRXScraper:
    """KRX 데이터 스크래퍼"""

    def __init__(self):
        self.today = datetime.now().strftime("%Y%m%d")

    def get_stock_list(self, market: str = "ALL") -> pd.DataFrame:
        """
        종목 리스트 조회

        Args:
            market: "KOSPI", "KOSDAQ", "ALL"

        Returns:
            종목 코드와 이름이 담긴 DataFrame
        """
        try:
            if market == "ALL":
                kospi = stock.get_market_ticker_list(self.today, market="KOSPI")
                kosdaq = stock.get_market_ticker_list(self.today, market="KOSDAQ")
                tickers = kospi + kosdaq
            else:
                tickers = stock.get_market_ticker_list(self.today, market=market)

            data = []
            for ticker in tickers:
                name = stock.get_market_ticker_name(ticker)
                data.append({"ticker": ticker, "name": name, "market": market})

            logger.info(f"종목 리스트 조회 완료: {len(data)}개")
            return pd.DataFrame(data)

        except Exception as e:
            logger.error(f"종목 리스트 조회 실패: {e}")
            return pd.DataFrame()

    def get_stock_price(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        주가 데이터 조회

        Args:
            ticker: 종목 코드
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)

        Returns:
            OHLCV 데이터가 담긴 DataFrame
        """
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
            if not end_date:
                end_date = self.today

            df = stock.get_market_ohlcv(start_date, end_date, ticker)
            df = df.reset_index()
            df["ticker"] = ticker
            df.columns = ["date", "open", "high", "low", "close", "volume", "ticker"]

            logger.info(f"{ticker} 주가 데이터 조회 완료: {len(df)}일")
            return df

        except Exception as e:
            logger.error(f"{ticker} 주가 데이터 조회 실패: {e}")
            return pd.DataFrame()

    def get_current_price(self, ticker: str) -> Dict:
        """
        현재가 조회

        Args:
            ticker: 종목 코드

        Returns:
            현재가 정보 딕셔너리
        """
        try:
            df = stock.get_market_ohlcv(self.today, self.today, ticker)
            if df.empty:
                # 오늘 데이터가 없으면 최근 거래일 조회
                df = stock.get_market_ohlcv(
                    (datetime.now() - timedelta(days=7)).strftime("%Y%m%d"),
                    self.today,
                    ticker,
                )
                df = df.tail(1)

            if not df.empty:
                row = df.iloc[-1]
                return {
                    "ticker": ticker,
                    "name": stock.get_market_ticker_name(ticker),
                    "date": df.index[-1].strftime("%Y-%m-%d"),
                    "open": int(row["시가"]),
                    "high": int(row["고가"]),
                    "low": int(row["저가"]),
                    "close": int(row["종가"]),
                    "volume": int(row["거래량"]),
                    "change_rate": float(row.get("등락률", 0)),
                }
            return {}

        except Exception as e:
            logger.error(f"{ticker} 현재가 조회 실패: {e}")
            return {}

    def get_market_cap(self, ticker: str, date: Optional[str] = None) -> Dict:
        """
        시가총액 조회

        Args:
            ticker: 종목 코드
            date: 조회일 (YYYYMMDD)

        Returns:
            시가총액 정보 딕셔너리
        """
        try:
            if not date:
                date = self.today

            df = stock.get_market_cap(date, date, ticker)
            if not df.empty:
                row = df.iloc[-1]
                return {
                    "ticker": ticker,
                    "date": date,
                    "market_cap": int(row["시가총액"]),
                    "shares": int(row["상장주식수"]),
                }
            return {}

        except Exception as e:
            logger.error(f"{ticker} 시가총액 조회 실패: {e}")
            return {}

    def get_fundamental(self, ticker: str, date: Optional[str] = None) -> Dict:
        """
        펀더멘탈 데이터 조회 (PER, PBR, EPS, BPS, DIV)

        Args:
            ticker: 종목 코드
            date: 조회일 (YYYYMMDD)

        Returns:
            펀더멘탈 정보 딕셔너리
        """
        try:
            if not date:
                date = self.today

            df = stock.get_market_fundamental(date, date, ticker)
            if not df.empty:
                row = df.iloc[-1]
                return {
                    "ticker": ticker,
                    "date": date,
                    "bps": float(row.get("BPS", 0)),
                    "per": float(row.get("PER", 0)),
                    "pbr": float(row.get("PBR", 0)),
                    "eps": float(row.get("EPS", 0)),
                    "div": float(row.get("DIV", 0)),
                    "dps": float(row.get("DPS", 0)),
                }
            return {}

        except Exception as e:
            logger.error(f"{ticker} 펀더멘탈 조회 실패: {e}")
            return {}

    def get_all_stock_data(self, ticker: str) -> Dict:
        """
        종목의 모든 데이터를 한번에 조회

        Args:
            ticker: 종목 코드

        Returns:
            종합 데이터 딕셔너리
        """
        result = {
            "ticker": ticker,
            "name": stock.get_market_ticker_name(ticker),
            "price": self.get_current_price(ticker),
            "market_cap": self.get_market_cap(ticker),
            "fundamental": self.get_fundamental(ticker),
            "updated_at": datetime.now().isoformat(),
        }
        return result
