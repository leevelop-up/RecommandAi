"""
AI 추천 엔진 - Gemini AI + 규칙 기반 fallback 오케스트레이터
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Optional
from datetime import datetime
from loguru import logger

from processors.gemini_client import GeminiClient
from processors.enhanced_rules import EnhancedRuleEngine
from processors import prompt_builder


class AIRecommendationEngine:
    """AI 추천 엔진 (Gemini + Rule-based fallback)"""

    def __init__(self, api_key: Optional[str] = None, force_rule: bool = False):
        self.gemini = GeminiClient(api_key=api_key)
        self.rule_engine = EnhancedRuleEngine()
        self.force_rule = force_rule
        self.engine_used = "unknown"

    def analyze(self, data: Dict) -> Dict:
        """
        데이터 분석 및 추천 생성

        Returns:
            {
                "generated_at": str,
                "engine": "gemini" | "rule_based" | "hybrid",
                "market_overview": {...},
                "recommendations": {"korea": [...], "usa": [...]},
                "sector_analysis": [...],
                "top_picks": [...],
                "risk_assessment": {...},
                "avoid_list": [...]
            }
        """
        if self.force_rule or not self.gemini.is_available():
            if not self.force_rule:
                logger.info("Gemini API 키 미설정 → 규칙 기반 분석 모드")
            else:
                logger.info("규칙 기반 분석 모드 (강제)")
            return self._rule_based_analysis(data)

        logger.info("Gemini AI 분석 모드")
        result = self._ai_analysis(data)

        if result is None:
            logger.warning("AI 분석 실패 → 규칙 기반 fallback")
            return self._rule_based_analysis(data)

        return result

    def _ai_analysis(self, data: Dict) -> Optional[Dict]:
        """Gemini AI 4단계 분석"""
        system = prompt_builder.SYSTEM_INSTRUCTION
        results = {}

        # Step 1: 한국 종목 분석
        logger.info("[AI 1/4] 한국 종목 분석 중...")
        kr_prompt = prompt_builder.build_korea_stock_prompt(data)
        kr_result = self.gemini.generate_json(kr_prompt, system_instruction=system)

        if kr_result is None:
            logger.warning("한국 종목 AI 분석 실패")
            kr_result = self._rule_korea_fallback(data)
            results["kr_engine"] = "rule"
        else:
            results["kr_engine"] = "gemini"
        results["korea"] = kr_result

        # Step 2: 미국 종목 분석
        logger.info("[AI 2/4] 미국 종목 분석 중...")
        us_prompt = prompt_builder.build_usa_stock_prompt(data)
        us_result = self.gemini.generate_json(us_prompt, system_instruction=system)

        if us_result is None:
            logger.warning("미국 종목 AI 분석 실패")
            us_result = self._rule_usa_fallback(data)
            results["us_engine"] = "rule"
        else:
            results["us_engine"] = "gemini"
        results["usa"] = us_result

        # Step 3: 섹터/테마 분석
        logger.info("[AI 3/4] 섹터/테마 분석 중...")
        sec_prompt = prompt_builder.build_sector_theme_prompt(data)
        sec_result = self.gemini.generate_json(sec_prompt, system_instruction=system)

        if sec_result is None:
            logger.warning("섹터 분석 AI 실패, 규칙 기반 대체")
            sec_result = self._rule_sector_fallback(data)
            results["sec_engine"] = "rule"
        else:
            results["sec_engine"] = "gemini"
        results["sector"] = sec_result

        # Step 4: 종합 TOP10
        logger.info("[AI 4/4] 종합 TOP10 선정 중...")
        top_prompt = prompt_builder.build_top_picks_prompt(
            kr_result, us_result, sec_result
        )
        top_result = self.gemini.generate_json(top_prompt, system_instruction=system)

        if top_result is None:
            logger.warning("TOP10 AI 실패, 스코어 기반 대체")
            top_result = self._build_top_picks_from_scores(kr_result, us_result)
            results["top_engine"] = "rule"
        else:
            results["top_engine"] = "gemini"

        # 엔진 판별
        engines = [results.get("kr_engine"), results.get("us_engine"),
                    results.get("sec_engine"), results.get("top_engine")]
        if all(e == "gemini" for e in engines):
            self.engine_used = "gemini"
        elif all(e == "rule" for e in engines):
            self.engine_used = "rule_based"
        else:
            self.engine_used = "hybrid"

        return self._assemble_result(
            kr_result, us_result, sec_result, top_result
        )

    def _rule_based_analysis(self, data: Dict) -> Dict:
        """규칙 기반 전체 분석"""
        self.engine_used = "rule_based"
        return self.rule_engine.analyze_all(data)

    def _rule_korea_fallback(self, data: Dict) -> Dict:
        """한국 종목 규칙 기반 fallback"""
        stocks = data.get("korea_stocks", [])
        recs = []
        for s in stocks:
            result = self.rule_engine.analyze_korea_stock(s)
            recs.append(result)
        return {
            "market_summary": "AI 분석 불가, 규칙 기반 분석 결과",
            "market_sentiment": "neutral",
            "recommendations": recs,
        }

    def _rule_usa_fallback(self, data: Dict) -> Dict:
        """미국 종목 규칙 기반 fallback"""
        stocks = data.get("usa_stocks", [])
        recs = []
        for s in stocks:
            result = self.rule_engine.analyze_usa_stock(s)
            recs.append(result)
        return {
            "market_summary": "AI 분석 불가, 규칙 기반 분석 결과",
            "market_sentiment": "neutral",
            "recommendations": recs,
        }

    def _rule_sector_fallback(self, data: Dict) -> Dict:
        """섹터 분석 규칙 기반 fallback"""
        full = self.rule_engine.analyze_all(data)
        return {
            "sector_analysis": full.get("sector_analysis", []),
            "hot_themes": [],
            "risk_assessment": full.get("risk_assessment", {}),
        }

    def _build_top_picks_from_scores(self, kr: Dict, us: Dict) -> Dict:
        """스코어 기반 TOP10 생성"""
        all_recs = []

        for r in kr.get("recommendations", []):
            all_recs.append({**r, "country": "KR"})
        for r in us.get("recommendations", []):
            all_recs.append({**r, "country": "US"})

        sorted_recs = sorted(all_recs, key=lambda x: x.get("score", 0), reverse=True)

        top_picks = []
        for i, r in enumerate(sorted_recs[:10], 1):
            top_picks.append({
                "rank": i,
                "ticker": r["ticker"],
                "name": r["name"],
                "country": r.get("country", ""),
                "action": r["action"],
                "score": r["score"],
                "one_line": r.get("reasoning", "")[:60],
            })

        # 하위 종목 = avoid list
        avoid = []
        for r in sorted_recs[-3:]:
            if r.get("score", 50) < 40:
                avoid.append({
                    "ticker": r["ticker"],
                    "name": r["name"],
                    "reason": r.get("reasoning", "낮은 점수"),
                })

        return {
            "overall_summary": f"스코어 기반 분석. 최고점: {sorted_recs[0]['score'] if sorted_recs else 0}점",
            "overall_sentiment": "neutral",
            "top_picks": top_picks,
            "avoid_list": avoid,
        }

    def _assemble_result(
        self, kr: Dict, us: Dict, sector: Dict, top: Dict
    ) -> Dict:
        """최종 결과 조립"""
        # 시장 개요
        kr_summary = kr.get("market_summary", "")
        us_summary = us.get("market_summary", "")
        kr_sent = kr.get("market_sentiment", "neutral")
        us_sent = us.get("market_sentiment", "neutral")

        sentiment_map = {"bullish": 1, "neutral": 0, "bearish": -1}
        avg_sent = (sentiment_map.get(kr_sent, 0) + sentiment_map.get(us_sent, 0)) / 2
        if avg_sent > 0.3:
            overall_sent = "bullish"
        elif avg_sent < -0.3:
            overall_sent = "bearish"
        else:
            overall_sent = "neutral"

        overview_summary = top.get("overall_summary", f"{kr_summary} {us_summary}")

        # 섹터 분석
        sector_analysis = sector.get("sector_analysis", [])
        risk = sector.get("risk_assessment", {})

        return {
            "generated_at": datetime.now().isoformat(),
            "engine": self.engine_used,
            "market_overview": {
                "summary": overview_summary,
                "korea_summary": kr_summary,
                "usa_summary": us_summary,
                "trend": overall_sent,
                "sentiment": overall_sent,
            },
            "recommendations": {
                "korea": kr.get("recommendations", []),
                "usa": us.get("recommendations", []),
            },
            "sector_analysis": sector_analysis,
            "top_picks": top.get("top_picks", []),
            "risk_assessment": risk,
            "avoid_list": top.get("avoid_list", []),
        }
