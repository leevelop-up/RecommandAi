"""
AI 추천/급등 예측 결과를 MariaDB에 저장

테이블 구조:
- ai_recommendations: AI 추천 종목 리스트
- growth_predictions: 급등 예측 종목 리스트
- recommendation_history: 추천 이력 (메타데이터)
"""
import sys
import os
import json
from datetime import datetime
from typing import Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from loguru import logger

from config.settings import get_settings

Base = declarative_base()


# =========================================================================
# 테이블 정의
# =========================================================================
class RecommendationHistory(Base):
    """추천 이력 메타데이터"""
    __tablename__ = "recommendation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    generated_at = Column(DateTime, nullable=False, index=True)
    engine = Column(String(50), nullable=False)  # gemini, rule_based, hybrid
    recommendation_type = Column(Enum("stable", "growth", "both"), nullable=False)  # stable=추천, growth=급등예측
    market_summary = Column(Text)
    market_sentiment = Column(String(20))
    total_korea = Column(Integer, default=0)
    total_usa = Column(Integer, default=0)
    json_file_path = Column(String(255))
    txt_file_path = Column(String(255))
    created_at = Column(DateTime, default=datetime.now)


class AIRecommendation(Base):
    """AI 추천 종목 (안정성 위주)"""
    __tablename__ = "ai_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    history_id = Column(Integer, nullable=False, index=True)  # recommendation_history FK
    generated_at = Column(DateTime, nullable=False, index=True)

    ticker = Column(String(20), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    country = Column(String(5), nullable=False)  # KR, US

    current_price = Column(Float)
    change_rate = Column(Float)

    score = Column(Integer)
    grade = Column(String(5))
    action = Column(String(20))  # 적극 매수, 매수, 보유, 매도 고려, 매도

    reasoning = Column(Text)
    risk_factors = Column(JSON)  # ["리스크1", "리스크2"]
    catalysts = Column(JSON)  # ["촉매1", "촉매2"]
    target_return = Column(String(50))

    # 펀더멘탈
    per = Column(Float)
    pbr = Column(Float)
    eps = Column(Float)
    roe = Column(Float)

    # 뉴스 감성
    news_sentiment_score = Column(Float)
    news_sentiment_label = Column(String(20))

    created_at = Column(DateTime, default=datetime.now)


class GrowthPrediction(Base):
    """급등 예측 종목 (모멘텀 위주)"""
    __tablename__ = "growth_predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    history_id = Column(Integer, nullable=False, index=True)
    generated_at = Column(DateTime, nullable=False, index=True)

    rank = Column(Integer)
    ticker = Column(String(20), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    country = Column(String(5), nullable=False)

    current_price = Column(Float)
    change_rate = Column(Float)

    predicted_return = Column(String(50))  # "+3~7%"
    confidence = Column(String(20))  # high, medium, low
    timeframe = Column(String(50))  # "1-3일"

    reasoning = Column(Text)
    entry_point = Column(String(100))
    stop_loss = Column(String(100))

    growth_score = Column(Integer)  # 규칙 기반 점수
    signals = Column(JSON)  # ["시그널1", "시그널2"]

    created_at = Column(DateTime, default=datetime.now)


class ThemePrediction(Base):
    """급등 테마 예측"""
    __tablename__ = "theme_predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    history_id = Column(Integer, nullable=False, index=True)
    generated_at = Column(DateTime, nullable=False, index=True)

    theme_name = Column(String(100), nullable=False)
    theme_rate = Column(Float)
    momentum = Column(String(20))  # strong, moderate, weak

    reasoning = Column(Text)
    signal = Column(Text)
    top_stocks = Column(JSON)  # [{"name": "종목명", "change_rate": 3.5}, ...]

    created_at = Column(DateTime, default=datetime.now)


# =========================================================================
# DB 저장 로직
# =========================================================================
class RecommendationDB:
    """추천 데이터 DB 저장"""

    def __init__(self):
        settings = get_settings()
        self.engine = create_engine(settings.MARIADB_URL, echo=False)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def save_recommendation(self, json_path: str, txt_path: str) -> int:
        """AI 추천 결과 저장"""
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        generated_at = datetime.fromisoformat(data["generated_at"])
        engine = data.get("engine", "unknown")

        # 메타데이터 저장
        overview = data.get("market_overview", {})
        history = RecommendationHistory(
            generated_at=generated_at,
            engine=engine,
            recommendation_type="stable",
            market_summary=overview.get("summary", ""),
            market_sentiment=str(overview.get("sentiment", "")),
            total_korea=len(data.get("recommendations", {}).get("korea", [])),
            total_usa=len(data.get("recommendations", {}).get("usa", [])),
            json_file_path=json_path,
            txt_file_path=txt_path,
        )
        self.session.add(history)
        self.session.flush()

        # 한국 추천 종목
        for rec in data.get("recommendations", {}).get("korea", []):
            fund = rec.get("fundamentals", {})
            news = rec.get("news_sentiment", {})

            row = AIRecommendation(
                history_id=history.id,
                generated_at=generated_at,
                ticker=rec["ticker"],
                name=rec["name"],
                country=rec.get("country", "KR"),
                current_price=rec.get("current_price"),
                change_rate=rec.get("change_rate"),
                score=rec.get("score"),
                grade=rec.get("grade"),
                action=rec.get("action"),
                reasoning=rec.get("reasoning"),
                risk_factors=rec.get("risk_factors"),
                catalysts=rec.get("catalysts"),
                target_return=rec.get("target_return"),
                per=fund.get("per"),
                pbr=fund.get("pbr"),
                eps=fund.get("eps"),
                roe=fund.get("roe"),
                news_sentiment_score=news.get("score"),
                news_sentiment_label=news.get("label"),
            )
            self.session.add(row)

        # 미국 추천 종목
        for rec in data.get("recommendations", {}).get("usa", []):
            fund = rec.get("fundamentals", {})
            news = rec.get("news_sentiment", {})

            row = AIRecommendation(
                history_id=history.id,
                generated_at=generated_at,
                ticker=rec["ticker"],
                name=rec["name"],
                country=rec.get("country", "US"),
                current_price=rec.get("current_price"),
                change_rate=rec.get("change_rate"),
                score=rec.get("score"),
                grade=rec.get("grade"),
                action=rec.get("action"),
                reasoning=rec.get("reasoning"),
                risk_factors=rec.get("risk_factors"),
                catalysts=rec.get("catalysts"),
                target_return=rec.get("target_return"),
                per=fund.get("pe_ratio"),
                pbr=fund.get("pb_ratio"),
                roe=fund.get("roe"),
                news_sentiment_score=news.get("score"),
                news_sentiment_label=news.get("label"),
            )
            self.session.add(row)

        self.session.commit()
        logger.info(f"AI 추천 저장 완료: history_id={history.id}, "
                    f"한국 {len(data.get('recommendations',{}).get('korea',[]))}종목, "
                    f"미국 {len(data.get('recommendations',{}).get('usa',[]))}종목")
        return history.id

    def save_growth_prediction(self, json_path: str, txt_path: str) -> int:
        """급등 예측 결과 저장"""
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        generated_at = datetime.fromisoformat(data["generated_at"])
        engine = data.get("engine", "unknown")

        # 메타데이터
        history = RecommendationHistory(
            generated_at=generated_at,
            engine=engine,
            recommendation_type="growth",
            market_summary=data.get("prediction_summary", ""),
            market_sentiment="",
            total_korea=len(data.get("korea_picks", [])),
            total_usa=len(data.get("usa_picks", [])),
            json_file_path=json_path,
            txt_file_path=txt_path,
        )
        self.session.add(history)
        self.session.flush()

        # 한국 급등 후보
        for pick in data.get("korea_picks", []):
            row = GrowthPrediction(
                history_id=history.id,
                generated_at=generated_at,
                rank=pick.get("rank"),
                ticker=pick["ticker"],
                name=pick["name"],
                country=pick.get("country", "KR"),
                current_price=pick.get("current_price"),
                change_rate=pick.get("change_rate"),
                predicted_return=pick.get("predicted_return"),
                confidence=pick.get("confidence"),
                timeframe=pick.get("timeframe"),
                reasoning=pick.get("reasoning"),
                entry_point=pick.get("entry_point"),
                stop_loss=pick.get("stop_loss"),
                growth_score=pick.get("growth_score"),
                signals=pick.get("signals"),
            )
            self.session.add(row)

        # 미국 급등 후보
        for pick in data.get("usa_picks", []):
            row = GrowthPrediction(
                history_id=history.id,
                generated_at=generated_at,
                rank=pick.get("rank"),
                ticker=pick["ticker"],
                name=pick["name"],
                country=pick.get("country", "US"),
                current_price=pick.get("current_price"),
                change_rate=pick.get("change_rate"),
                predicted_return=pick.get("predicted_return"),
                confidence=pick.get("confidence"),
                timeframe=pick.get("timeframe"),
                reasoning=pick.get("reasoning"),
                entry_point=pick.get("entry_point"),
                stop_loss=pick.get("stop_loss"),
                growth_score=pick.get("growth_score"),
                signals=pick.get("signals"),
            )
            self.session.add(row)

        # 테마
        for theme in data.get("theme_picks", []):
            row = ThemePrediction(
                history_id=history.id,
                generated_at=generated_at,
                theme_name=theme.get("theme_name", theme.get("theme", "")),
                theme_rate=theme.get("theme_rate", 0),
                momentum=theme.get("momentum"),
                reasoning=theme.get("reasoning"),
                signal=theme.get("signal"),
                top_stocks=theme.get("top_stocks"),
            )
            self.session.add(row)

        self.session.commit()
        logger.info(f"급등 예측 저장 완료: history_id={history.id}, "
                    f"한국 {len(data.get('korea_picks',[]))}종목, "
                    f"미국 {len(data.get('usa_picks',[]))}종목, "
                    f"테마 {len(data.get('theme_picks',[]))}개")
        return history.id

    def close(self):
        self.session.close()


# =========================================================================
# 실행 스크립트
# =========================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="AI 추천/급등 예측 JSON → DB 저장")
    parser.add_argument("--recommendation", help="ai_recommendation_*.json 경로")
    parser.add_argument("--growth", help="growth_prediction_*.json 경로")
    parser.add_argument("--auto", action="store_true", help="최신 파일 자동 찾아서 저장")
    args = parser.parse_args()

    db = RecommendationDB()

    try:
        if args.auto:
            # 최신 파일 자동 찾기
            import glob
            rec_jsons = sorted(glob.glob("ai_recommendation_*.json"), reverse=True)
            growth_jsons = sorted(glob.glob("growth_prediction_*.json"), reverse=True)

            if rec_jsons:
                rec_json = rec_jsons[0]
                rec_txt = rec_json.replace(".json", ".txt")
                logger.info(f"AI 추천: {rec_json}")
                db.save_recommendation(rec_json, rec_txt)

            if growth_jsons:
                growth_json = growth_jsons[0]
                growth_txt = growth_json.replace(".json", ".txt")
                logger.info(f"급등 예측: {growth_json}")
                db.save_growth_prediction(growth_json, growth_txt)

        else:
            if args.recommendation:
                txt_path = args.recommendation.replace(".json", ".txt")
                db.save_recommendation(args.recommendation, txt_path)

            if args.growth:
                txt_path = args.growth.replace(".json", ".txt")
                db.save_growth_prediction(args.growth, txt_path)

    finally:
        db.close()

    logger.info("DB 저장 완료")


if __name__ == "__main__":
    main()
