"""
한국 주식 퀀트 전략 — 데이터 수집 · 전처리 · 피처 엔지니어링

소스  : pykrx (가격 · 기본지표), 키워드 기반 뉴스 감성 분석
규칙  : Data Leakage 절대 금지
        - 라벨은 t+1 Close로 생성 (shift)
        - 모든 기술 지표는 t 시점 이전 데이터만 사용
        - 학습 시 마지막 행(라벨 NaN)은 제외
"""

import os
import json
import time

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger

try:
    from pykrx import stock as pykrx_stock
except ImportError:
    pykrx_stock = None
    logger.warning("pykrx 패키지 미설치 — pip install pykrx")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── 감성 키워드 사전 (한국 주식 시장) ────────────────────────
_POS_KW = [
    "상승", "반등", "강세", "폭등", "호실적", "실적개선", "성장", "수주",
    "매출증가", "영업이익증가", "저평가", "배당", "신사업", "수출증가",
    "기대", "호조", "회복", "우세", "안정", "실적호조", "흑자",
    "혁신", "확장", "신규수주", "배당증가", "목표상향", "실적상향",
]
_NEG_KW = [
    "하락", "폭락", "약세", "실적악화", "손실", "적자", "부채증가",
    "실적감소", "수주취소", "불안", "하락세", "급락", "매출감소",
    "영업이익감소", "위기", "침체", "실적부진", "급등후조정",
    "과대평가", "목표하향", "실적하향", "매입자제", "리스크", "부정", "제재",
]


class SentimentScorer:
    """키워드 매칭 기반 뉴스 감성 스코어링"""

    @staticmethod
    def score_text(text: str) -> float:
        """단일 텍스트 → 감성 점수 (-1 ~ +1)"""
        if not text:
            return 0.0
        pos = sum(1 for kw in _POS_KW if kw in text)
        neg = sum(1 for kw in _NEG_KW if kw in text)
        total = pos + neg
        return round((pos - neg) / total, 3) if total else 0.0

    @staticmethod
    def score_articles(articles: list) -> dict:
        """기사 리스트 → {sentiment_score, positive_ratio, negative_surge}"""
        if not articles:
            return {"sentiment_score": 0.0, "positive_ratio": 0.5, "negative_surge": 0}
        scores = [
            SentimentScorer.score_text(
                f"{a.get('title', '')} {a.get('summary', a.get('description', ''))}"
            )
            for a in articles
        ]
        neg_strong = sum(1 for s in scores if s < -0.3)
        return {
            "sentiment_score": round(float(np.mean(scores)), 3),
            "positive_ratio": round(sum(1 for s in scores if s > 0) / len(scores), 3),
            "negative_surge": 1 if neg_strong >= max(2, len(scores) * 0.4) else 0,
        }


class QuantDataPipeline:
    """퀀트 전략 전체 데이터 파이프라인

    BASE_FEATURES : 기본 피처 (항상 활성)
    COMBO_FEATURES: 진화로 활성화될 조합 피처
    ALL_FEATURES  : 전체 가능한 피처 목록
    """

    BASE_FEATURES = [
        "return_1d", "return_5d",
        "MA20_ratio", "MA60_ratio", "RSI14", "volume_ratio",
        "revenue_growth_z", "op_income_growth_z", "ROE_z", "debt_ratio_z",
        "sentiment_score", "positive_ratio", "negative_surge",
    ]
    COMBO_FEATURES = ["MA20_sent_combo"]
    ALL_FEATURES = BASE_FEATURES + COMBO_FEATURES

    def __init__(self):
        if pykrx_stock is None:
            raise ImportError("pykrx 패키지가 필요합니다")

    # ── 1. OHLCV 수집 ────────────────────────────────────────
    def fetch_ohlcv(self, ticker: str, years: int = 3) -> pd.DataFrame:
        """pykrx로 일봉 OHLCV 수집 (최소 3년간)

        Returns:
            Date, Open, High, Low, Close, Volume 컬럼의 DataFrame
        """
        end_str = datetime.now().strftime("%Y%m%d")
        start_str = (datetime.now() - timedelta(days=365 * years + 30)).strftime("%Y%m%d")
        try:
            df = pykrx_stock.get_market_ohlcv(start_str, end_str, ticker)
            if df is None or df.empty:
                logger.warning(f"{ticker}: OHLCV 데이터 없음")
                return pd.DataFrame()

            # 컬럼 매핑 (krx_scraper.py와 동일 패턴: 시가→Open 등)
            rename = {"시가": "Open", "고가": "High", "저가": "Low", "종가": "Close", "거래량": "Volume"}
            df = df.rename(columns=rename)
            df = df[["Open", "High", "Low", "Close", "Volume"]]
            df.index = pd.to_datetime(df.index)
            df = df[df["Volume"] > 0].sort_index()
            df = df.reset_index().rename(columns={"날짜": "Date"})

            logger.info(f"{ticker}: {len(df)}일간 OHLCV "
                        f"({df['Date'].iloc[0].date()} ~ {df['Date'].iloc[-1].date()})")
            time.sleep(0.3)  # pykrx rate-limit 방지
            return df
        except Exception as e:
            logger.error(f"{ticker} OHLCV 수집 실패: {e}")
            return pd.DataFrame()

    # ── 2. 기본지표 (재무) 수집 ──────────────────────────────
    def fetch_fundamentals(self, ticker: str) -> dict:
        """PER, PBR, EPS, BPS → ROE 도출

        pykrx get_market_fundamental은 단일 시점만 제공하므로
        YoY 성장률은 프록시(PER)로 대체.
        """
        for days_back in range(7):  # 최근 거래일까지 역추적
            check_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")
            try:
                df = pykrx_stock.get_market_fundamental(check_date, check_date, ticker)
                if df is not None and not df.empty:
                    row = df.iloc[-1]
                    eps = float(row.get("EPS", 0) or 0)
                    bps = float(row.get("BPS", 0) or 0)
                    roe = round(eps / bps * 100, 2) if bps != 0 else 0.0
                    time.sleep(0.3)
                    return {
                        "PER": float(row.get("PER", 0) or 0),
                        "PBR": float(row.get("PBR", 0) or 0),
                        "EPS": eps,
                        "ROE": roe,
                        "revenue_growth": None,   # 단일 시점 API 제한
                        "op_income_growth": None,
                        "debt_ratio": None,
                    }
            except Exception:
                continue
        logger.warning(f"{ticker}: 기본지표 수집 실패")
        return {}

    # ── 3. 뉴스 감성 수집 ────────────────────────────────────
    def fetch_news_sentiment(self, ticker: str, ticker_name: str = "") -> dict:
        """스크레이프 결과 파일에서 종목 관련 기사 추출 → 감성 스코어링

        output/scrap/news_summary.json이 존재하면 활용,
        관련 기사 없으면 중립(0.0) 반환.
        """
        scrap_path = os.path.join(BASE_DIR, "output", "scrap", "news_summary.json")
        articles = []
        if os.path.exists(scrap_path):
            try:
                with open(scrap_path, "r", encoding="utf-8") as f:
                    news_data = json.load(f)
                all_arts: list = []
                if isinstance(news_data, dict):
                    for v in news_data.values():
                        if isinstance(v, list):
                            all_arts.extend(v)
                elif isinstance(news_data, list):
                    all_arts = news_data

                terms = [t for t in [ticker, ticker_name] if t]
                articles = [a for a in all_arts if any(t in a.get("title", "") for t in terms)]
            except Exception as e:
                logger.debug(f"스크레이프 뉴스 로드 오류: {e}")

        if not articles:
            logger.debug(f"{ticker}: 관련 뉴스 없음 → 중립")
            return {"sentiment_score": 0.0, "positive_ratio": 0.5, "negative_surge": 0}
        return SentimentScorer.score_articles(articles)

    # ── 4. 시장 감지 (KOSPI / KOSDAQ) ────────────────────────
    @staticmethod
    def detect_market(ticker: str) -> str:
        """pykrx ticker list로 KOSPI/KOSDAQ 판별"""
        try:
            today = datetime.now().strftime("%Y%m%d")
            kospi = pykrx_stock.get_market_ticker_list(today, market="KOSPI")
            return "KOSPI" if ticker in kospi else "KOSDAQ"
        except Exception:
            return "KRX"

    # ── 5. 전처리 (결측치 + IQR 이상치) ──────────────────────
    @staticmethod
    def preprocess(df: pd.DataFrame) -> pd.DataFrame:
        """결측치 제거 + Close 기준 IQR(1%~99%) 이상치 제거"""
        df = df.dropna().reset_index(drop=True)
        Q1 = df["Close"].quantile(0.01)
        Q3 = df["Close"].quantile(0.99)
        IQR = Q3 - Q1
        mask = (df["Close"] >= Q1 - 1.5 * IQR) & (df["Close"] <= Q3 + 1.5 * IQR)
        return df[mask].reset_index(drop=True)

    # ── 6. 기술 지표 계산 ────────────────────────────────────
    @staticmethod
    def compute_technicals(df: pd.DataFrame) -> pd.DataFrame:
        """수익률, 이동평균, RSI(14), 거래량 비율

        ⚠ 모든 rolling은 현재 시점(t) 기준 과거만 사용 — leakage 없음
        """
        df = df.copy()

        # 수익률
        df["return_1d"] = df["Close"].pct_change(1)   # (Close[t] - Close[t-1]) / Close[t-1]
        df["return_5d"] = df["Close"].pct_change(5)   # (Close[t] - Close[t-5]) / Close[t-5]

        # 이동평균 및 비율
        df["MA20"] = df["Close"].rolling(20).mean()
        df["MA60"] = df["Close"].rolling(60).mean()
        df["MA20_ratio"] = df["Close"] / df["MA20"]
        df["MA60_ratio"] = df["Close"] / df["MA60"]

        # RSI(14) — Wilder EMA (com=13 → span=14)
        delta = df["Close"].diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.ewm(com=13, adjust=False).mean()
        avg_loss = loss.ewm(com=13, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df["RSI14"] = (100 - 100 / (1 + rs)).fillna(50)

        # 거래량 비율
        df["volume_ratio"] = df["Volume"] / df["Volume"].rolling(20).mean()

        return df

    # ── 7. 재무 피처 (정규화) ────────────────────────────────
    @staticmethod
    def add_fundamental_features(df: pd.DataFrame, fund: dict) -> pd.DataFrame:
        """재무 변수를 [0, 1] 범위로 매핑

        ROE   : 0~30%  → 0~1
        PER   : op_income_growth_z 프록시로 사용 (낮을수록 수익성 대비 저평가)
        revenue_growth / debt_ratio : 현재 API 제한상 중립(0.5)
        """
        df = df.copy()
        roe = fund.get("ROE") or 0.0
        df["ROE_z"] = min(max(roe, 0), 30) / 30.0

        per = fund.get("PER") or 0.0
        df["op_income_growth_z"] = min(per, 50) / 50.0 if per > 0 else 0.5

        df["revenue_growth_z"] = 0.5   # N/A → 중립
        df["debt_ratio_z"] = 0.5       # N/A → 중립
        return df

    # ── 8. 감성 피처 ─────────────────────────────────────────
    @staticmethod
    def add_sentiment_features(df: pd.DataFrame, sent: dict) -> pd.DataFrame:
        """최근 뉴스 감성 피처 추가 (행 전체에 동일 값)"""
        df = df.copy()
        df["sentiment_score"] = sent.get("sentiment_score", 0.0)
        df["positive_ratio"] = sent.get("positive_ratio", 0.5)
        df["negative_surge"] = sent.get("negative_surge", 0)
        return df

    # ── 9. 조합 피처 ─────────────────────────────────────────
    @staticmethod
    def add_combo_features(df: pd.DataFrame) -> pd.DataFrame:
        """진화로 활성화될 수 있는 조합 피처 — 항상 계산하여 준비"""
        df = df.copy()
        df["MA20_sent_combo"] = df["MA20_ratio"] * df["sentiment_score"]
        return df

    # ── 10. 라벨 생성 ────────────────────────────────────────
    @staticmethod
    def create_labels(df: pd.DataFrame) -> pd.DataFrame:
        """정답 라벨: Y[t] = 1 if Close[t+1] > Close[t] else 0

        next_return[t] = (Close[t+1] - Close[t]) / Close[t]
        ⚠ 마지막 행은 Close[t+1]이 없으므로 label = NaN → 학습에서 제거
        """
        df = df.copy()
        df["next_return"] = df["Close"].shift(-1) / df["Close"] - 1  # t+1 수익률
        df["label"] = (df["next_return"] > 0).astype(float)
        # 마지막 행: next_return = NaN → label도 NaN으로 명시
        df.loc[df["next_return"].isna(), "label"] = np.nan
        return df

    # ── 전체 파이프라인 ──────────────────────────────────────
    def full_pipeline(self, ticker: str, ticker_name: str = "", years: int = 3) -> dict:
        """수집 → 전처리 → 피처 엔지니어링 → 라벨까지 전체 실행

        Returns:
            {ticker, ticker_name, market, df, fundamentals, sentiment}
            df는 피처 + 라벨이 완성된 DataFrame
            "error" 키가 있으면 실패
        """
        logger.info(f"[{ticker}] 퀀트 파이프라인 시작")

        df = self.fetch_ohlcv(ticker, years)
        if df.empty:
            return {"error": f"{ticker}: OHLCV 수집 실패"}

        fund = self.fetch_fundamentals(ticker)
        sent = self.fetch_news_sentiment(ticker, ticker_name)
        market = self.detect_market(ticker)

        df = self.preprocess(df)
        df = self.compute_technicals(df)
        df = self.add_fundamental_features(df, fund)
        df = self.add_sentiment_features(df, sent)
        df = self.add_combo_features(df)
        df = self.create_labels(df)

        logger.info(f"[{ticker}] 파이프라인 완료: {len(df)}행 | 시장={market}")
        return {
            "ticker": ticker,
            "ticker_name": ticker_name,
            "market": market,
            "df": df,
            "fundamentals": fund,
            "sentiment": sent,
        }
