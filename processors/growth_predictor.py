"""
급등 예측 엔진 - 상승률이 높을 것으로 예상되는 종목 발굴

기존 추천(블루칩 안정성 위주)과 달리:
- 모멘텀 급등 후보
- 테마 수혜 종목
- 거래량 급증 종목
- 저평가 반등 후보
- AI 예측 (Gemini/Groq)
"""
import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from loguru import logger

from processors.gemini_client import GeminiClient
from processors.groq_client import GroqClient
from processors.xai_client import XAIClient


class GrowthPredictor:
    """급등 예측 엔진"""

    def __init__(self, api_key: Optional[str] = None, engine: str = "gemini"):
        self.engine_name = engine.lower()

        if self.engine_name == "xai" or self.engine_name == "grok":
            logger.info("[급등 예측] AI 엔진: xAI Grok")
            self.ai_client = XAIClient(api_key=api_key)
            self.engine_name = "xai"
        elif self.engine_name == "groq":
            logger.info("[급등 예측] AI 엔진: Groq")
            self.ai_client = GroqClient(api_key=api_key)
        else:
            logger.info("[급등 예측] AI 엔진: Gemini")
            self.ai_client = GeminiClient(api_key=api_key)

    def predict(self, data: Dict) -> Dict:
        """급등 후보 종목 예측"""
        logger.info("[급등 예측] 분석 시작")

        # 1. 규칙 기반 급등 후보 발굴
        kr_candidates = self._find_korea_candidates(data)
        us_candidates = self._find_usa_candidates(data)
        theme_plays = self._find_theme_plays(data)

        # 2. AI 예측 (가능 시)
        ai_prediction = None
        if self.ai_client.is_available():
            ai_prediction = self._ai_predict(data, kr_candidates, us_candidates, theme_plays)

        # 3. 결과 조립
        result = self._build_result(
            kr_candidates, us_candidates, theme_plays, ai_prediction, data
        )

        logger.info(f"[급등 예측] 완료: 한국 {len(result['korea_picks'])}종목, "
                     f"미국 {len(result['usa_picks'])}종목, "
                     f"테마 {len(result['theme_picks'])}개")
        return result

    # =========================================================================
    # 한국 급등 후보
    # =========================================================================
    def _find_korea_candidates(self, data: Dict) -> List[Dict]:
        """한국 급등 후보 발굴"""
        stocks = data.get("korea_stocks", [])
        candidates = []

        for s in stocks:
            score = 0
            signals = []
            price = s.get("price", {})
            fund = s.get("fundamental", {})

            current = price.get("current_price", 0)
            change_rate = self._parse_num(price.get("change_rate", 0))
            volume = price.get("volume", 0)

            per = self._parse_num(fund.get("per", 0))
            pbr = self._parse_num(fund.get("pbr", 0))
            eps = self._parse_num(fund.get("eps", 0))

            # 모멘텀 (당일 상승세)
            if change_rate >= 3.0:
                score += 25
                signals.append(f"강한 상승 모멘텀 +{change_rate:.1f}%")
            elif change_rate >= 1.0:
                score += 15
                signals.append(f"상승세 +{change_rate:.1f}%")
            elif change_rate <= -3.0:
                # 급락 반등 후보
                score += 10
                signals.append(f"급락 반등 후보 {change_rate:.1f}%")

            # 저PER 반등 (심하게 저평가)
            if 0 < per <= 8:
                score += 20
                signals.append(f"극저PER {per:.1f} 반등 기대")
            elif 0 < per <= 12:
                score += 10
                signals.append(f"저PER {per:.1f}")

            # 저PBR (자산가치 대비)
            if 0 < pbr <= 0.5:
                score += 15
                signals.append(f"극저PBR {pbr:.2f} 자산가치 반등")
            elif 0 < pbr <= 0.8:
                score += 8
                signals.append(f"저PBR {pbr:.2f}")

            # 흑자 전환 / 높은 EPS
            if eps > 0:
                if current > 0 and eps / current > 0.1:
                    score += 12
                    signals.append(f"높은 이익률 (EPS {eps:,.0f})")

            # 거래량 (높을수록 관심도 높음)
            if volume and volume > 10_000_000:
                score += 10
                signals.append(f"대량 거래 {volume:,}")
            elif volume and volume > 5_000_000:
                score += 5
                signals.append(f"활발한 거래")

            # 뉴스 감성
            news_score = self._analyze_news_sentiment(s.get("news", []), lang="ko")
            if news_score >= 0.5:
                score += 15
                signals.append("긍정적 뉴스 흐름")
            elif news_score <= -0.5:
                score -= 10
                signals.append("부정적 뉴스 주의")

            candidates.append({
                "ticker": s["ticker"],
                "name": s["name"],
                "country": "KR",
                "current_price": current,
                "change_rate": change_rate,
                "growth_score": score,
                "signals": signals,
                "volume": volume,
            })

        # 점수 순 정렬
        candidates.sort(key=lambda x: x["growth_score"], reverse=True)
        return candidates

    # =========================================================================
    # 미국 급등 후보
    # =========================================================================
    def _find_usa_candidates(self, data: Dict) -> List[Dict]:
        """미국 급등 후보 발굴"""
        stocks = data.get("usa_stocks", [])
        candidates = []

        for s in stocks:
            score = 0
            signals = []
            price = s.get("price", {})
            fund = s.get("fundamental", {})

            current = self._parse_num(price.get("current_price", 0))
            change_rate = self._parse_num(price.get("change_rate", 0))
            high52 = self._parse_num(price.get("fifty_two_week_high", 0))
            low52 = self._parse_num(price.get("fifty_two_week_low", 0))

            pe = self._parse_num(fund.get("pe_ratio", 0))
            roe = self._parse_num(fund.get("roe", 0))
            revenue_growth = self._parse_num(fund.get("revenue_growth", 0))

            # 모멘텀
            if change_rate >= 3.0:
                score += 25
                signals.append(f"강한 상승 +{change_rate:.1f}%")
            elif change_rate >= 1.0:
                score += 15
                signals.append(f"상승세 +{change_rate:.1f}%")
            elif change_rate <= -3.0:
                score += 10
                signals.append(f"급락 반등 후보 {change_rate:.1f}%")

            # 52주 위치 분석
            if high52 > 0 and low52 > 0 and current > 0:
                range_52 = high52 - low52
                if range_52 > 0:
                    position = (current - low52) / range_52
                    if position >= 0.9:
                        score += 20
                        signals.append(f"52주 신고가 근접 ({position:.0%})")
                    elif position <= 0.3:
                        score += 15
                        signals.append(f"52주 저점 반등 후보 ({position:.0%})")

            # 밸류에이션
            if 0 < pe <= 15:
                score += 15
                signals.append(f"저PE {pe:.1f}")
            elif 0 < pe <= 25:
                score += 5

            # ROE
            if roe and roe > 0.2:
                score += 12
                signals.append(f"높은 ROE {roe*100:.1f}%")
            elif roe and roe > 0.1:
                score += 6

            # 매출 성장
            if revenue_growth and revenue_growth > 0.15:
                score += 15
                signals.append(f"매출 성장 {revenue_growth*100:.1f}%")
            elif revenue_growth and revenue_growth > 0.05:
                score += 8

            # 뉴스 감성
            news_score = self._analyze_news_sentiment(s.get("news", []), lang="en")
            if news_score >= 0.5:
                score += 15
                signals.append("긍정적 뉴스")
            elif news_score <= -0.5:
                score -= 10

            candidates.append({
                "ticker": s["ticker"],
                "name": s.get("name", s["ticker"]),
                "country": "US",
                "sector": s.get("sector", ""),
                "current_price": current,
                "change_rate": change_rate,
                "growth_score": score,
                "signals": signals,
            })

        candidates.sort(key=lambda x: x["growth_score"], reverse=True)
        return candidates

    # =========================================================================
    # 테마 플레이
    # =========================================================================
    def _find_theme_plays(self, data: Dict) -> List[Dict]:
        """급등 테마 + 해당 수혜 종목 발굴"""
        themes = data.get("themes", {})
        plays = []

        # 상위 테마에서 급등 종목 추출
        top_themes = themes.get("top_themes", [])
        for theme in top_themes:
            rate = self._parse_change_rate(theme.get("change_rate", "0"))
            if rate < 1.0:
                continue

            theme_stocks = []
            for st in theme.get("stocks", [])[:10]:
                st_rate = self._parse_change_rate(st.get("change_rate", "0"))
                theme_stocks.append({
                    "name": st.get("name", ""),
                    "price": st.get("price", 0),
                    "change_rate": st_rate,
                })

            # 상승률 높은 순 정렬
            theme_stocks.sort(key=lambda x: x["change_rate"], reverse=True)

            plays.append({
                "theme_name": theme["name"],
                "theme_rate": rate,
                "momentum": "strong" if rate >= 3.0 else "moderate" if rate >= 1.0 else "weak",
                "top_stocks": theme_stocks[:5],
                "signal": f"테마 상승 +{rate:.1f}%, 수혜 종목 주목",
            })

        # 키워드 테마에서 모멘텀 체크
        kw_themes = themes.get("keyword_themes", {})
        for kw, info in kw_themes.items():
            rate = self._parse_change_rate(info.get("change_rate", "0"))
            if rate >= 1.0:
                plays.append({
                    "theme_name": f"{kw} ({info.get('theme_name', '')})",
                    "theme_rate": rate,
                    "momentum": "strong" if rate >= 3.0 else "moderate",
                    "top_stocks": [{"name": n, "price": 0, "change_rate": 0}
                                   for n in info.get("top_stocks", [])[:5]],
                    "signal": f"핵심 키워드 '{kw}' 테마 상승 중",
                })

        plays.sort(key=lambda x: x["theme_rate"], reverse=True)
        return plays

    # =========================================================================
    # AI 예측 (Gemini)
    # =========================================================================
    def _ai_predict(
        self, data: Dict, kr: List, us: List, themes: List
    ) -> Optional[Dict]:
        """Gemini AI로 급등 예측"""
        logger.info("[급등 예측] AI 분석 중...")

        prompt = self._build_growth_prompt(data, kr, us, themes)
        system = (
            "당신은 주식 급등을 예측하는 전문 트레이더입니다.\n"
            "모멘텀, 테마, 거래량, 뉴스를 종합해 단기(1-5일) 상승 가능성이 높은 종목을 선별하세요.\n"
            "반드시 한국어로, JSON 형식으로만 응답하세요.\n"
            "투자 위험 고지를 반드시 포함하세요."
        )

        result = self.ai_client.generate_json(prompt, system_instruction=system)
        if result:
            logger.info("[급등 예측] AI 분석 완료")
        else:
            logger.warning("[급등 예측] AI 분석 실패")
        return result

    def _build_growth_prompt(
        self, data: Dict, kr: List, us: List, themes: List
    ) -> str:
        lines = ["다음 데이터를 분석하여 향후 1-5일 내 상승률이 높을 종목을 예측하세요.\n"]

        # 한국 상위 후보
        lines.append("== 한국 급등 후보 (점수순) ==")
        for c in kr[:10]:
            sigs = ", ".join(c["signals"][:3]) if c["signals"] else "특이사항 없음"
            lines.append(f"  {c['name']}({c['ticker']}): "
                         f"{c['change_rate']:+.1f}%, 점수 {c['growth_score']}, "
                         f"시그널: {sigs}")

        # 미국 상위 후보
        lines.append("\n== 미국 급등 후보 (점수순) ==")
        for c in us[:10]:
            sigs = ", ".join(c["signals"][:3]) if c["signals"] else "특이사항 없음"
            lines.append(f"  {c['name']}({c['ticker']}): "
                         f"{c['change_rate']:+.1f}%, 점수 {c['growth_score']}, "
                         f"시그널: {sigs}")

        # 급등 테마
        if themes:
            lines.append("\n== 급등 테마 ==")
            for t in themes[:5]:
                stocks = ", ".join(s["name"] for s in t["top_stocks"][:3])
                lines.append(f"  {t['theme_name']}: +{t['theme_rate']:.1f}% "
                             f"({t['momentum']}) - {stocks}")

        # 뉴스
        news = data.get("market_news", [])
        if news:
            lines.append("\n== 최신 시장 뉴스 ==")
            for n in news[:5]:
                lines.append(f"  - {n.get('title', '')[:50]}")

        lines.append("""
위 데이터를 종합 분석하여 다음 JSON 형식으로 응답하세요:
{
  "prediction_summary": "전체 시장 급등 가능성 요약 (2-3문장)",
  "korea_growth_picks": [
    {
      "rank": 1,
      "ticker": "종목코드",
      "name": "종목명",
      "predicted_return": "예상 상승률 (예: +3~5%)",
      "confidence": "high | medium | low",
      "timeframe": "예상 기간 (예: 1-3일)",
      "reasoning": "예측 근거 (2-3문장)",
      "entry_point": "진입 시점/가격 조언",
      "stop_loss": "손절 기준"
    }
  ],
  "usa_growth_picks": [같은 구조],
  "theme_plays": [
    {
      "theme": "테마명",
      "momentum": "strong | moderate",
      "best_stock": "대장주",
      "reasoning": "테마 상승 근거"
    }
  ],
  "risk_warning": "투자 위험 고지"
}
한국 5개, 미국 5개, 테마 3개를 선정하세요.
상승 가능성이 높은 순서로 정렬하세요.""")

        return "\n".join(lines)

    # =========================================================================
    # 결과 조립
    # =========================================================================
    def _build_result(
        self, kr: List, us: List, themes: List,
        ai: Optional[Dict], data: Dict
    ) -> Dict:
        """최종 급등 예측 결과 조립"""
        result = {
            "generated_at": datetime.now().isoformat(),
            "type": "growth_prediction",
            "engine": "gemini" if ai else "rule_based",
        }

        if ai:
            # AI 결과 사용
            result["prediction_summary"] = ai.get("prediction_summary", "")
            result["korea_picks"] = ai.get("korea_growth_picks", [])
            result["usa_picks"] = ai.get("usa_growth_picks", [])
            result["theme_picks"] = ai.get("theme_plays", [])
            result["risk_warning"] = ai.get("risk_warning",
                "본 예측은 AI 분석 결과이며, 투자 손실의 책임은 투자자에게 있습니다.")

            # 규칙 기반 점수도 보조 정보로 추가
            result["rule_scores"] = {
                "korea": [{"ticker": c["ticker"], "name": c["name"],
                           "growth_score": c["growth_score"], "signals": c["signals"]}
                          for c in kr[:10]],
                "usa": [{"ticker": c["ticker"], "name": c["name"],
                         "growth_score": c["growth_score"], "signals": c["signals"]}
                        for c in us[:10]],
            }
        else:
            # 규칙 기반만
            result["prediction_summary"] = self._build_rule_summary(kr, us, themes, data)

            result["korea_picks"] = []
            for i, c in enumerate(kr[:7], 1):
                result["korea_picks"].append({
                    "rank": i,
                    "ticker": c["ticker"],
                    "name": c["name"],
                    "current_price": c["current_price"],
                    "change_rate": c["change_rate"],
                    "predicted_return": self._estimate_return(c["growth_score"]),
                    "confidence": self._score_to_confidence(c["growth_score"]),
                    "timeframe": "1-5일",
                    "reasoning": ", ".join(c["signals"][:4]) if c["signals"] else "종합 분석 기반",
                    "growth_score": c["growth_score"],
                })

            result["usa_picks"] = []
            for i, c in enumerate(us[:7], 1):
                result["usa_picks"].append({
                    "rank": i,
                    "ticker": c["ticker"],
                    "name": c["name"],
                    "current_price": c["current_price"],
                    "change_rate": c["change_rate"],
                    "predicted_return": self._estimate_return(c["growth_score"]),
                    "confidence": self._score_to_confidence(c["growth_score"]),
                    "timeframe": "1-5일",
                    "reasoning": ", ".join(c["signals"][:4]) if c["signals"] else "종합 분석 기반",
                    "growth_score": c["growth_score"],
                })

            result["theme_picks"] = themes[:5]
            result["risk_warning"] = (
                "본 예측은 규칙 기반 분석 결과이며, 투자 손실의 책임은 투자자에게 있습니다. "
                "단기 예측은 불확실성이 높으므로 반드시 분산 투자하세요."
            )

        return result

    def _build_rule_summary(self, kr: List, us: List, themes: List, data: Dict) -> str:
        """규칙 기반 요약 생성"""
        parts = []

        # 시장 상황
        indices = data.get("market_indices", {})
        kr_idx = indices.get("korea", {})
        if kr_idx:
            kospi = kr_idx.get("kospi", kr_idx.get("KOSPI", {}))
            if isinstance(kospi, dict):
                parts.append(f"KOSPI {kospi.get('value', 'N/A')}")

        # 한국 급등 후보
        if kr:
            top = kr[0]
            parts.append(f"한국 최유력: {top['name']}({top['growth_score']}점)")

        # 미국 급등 후보
        if us:
            top = us[0]
            parts.append(f"미국 최유력: {top['name']}({top['growth_score']}점)")

        # 테마
        if themes:
            hot = themes[0]
            parts.append(f"급등테마: {hot['theme_name']}(+{hot['theme_rate']:.1f}%)")

        return ". ".join(parts)

    # =========================================================================
    # 유틸리티
    # =========================================================================
    @staticmethod
    def _parse_num(val) -> float:
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            nums = re.findall(r'-?\d+\.?\d*', val)
            return float(nums[0]) if nums else 0
        return 0

    @staticmethod
    def _parse_change_rate(val) -> float:
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            nums = re.findall(r'[+-]?\d+\.?\d*', val)
            return float(nums[0]) if nums else 0
        return 0

    @staticmethod
    def _estimate_return(score: int) -> str:
        if score >= 60:
            return "+3~7%"
        elif score >= 45:
            return "+2~5%"
        elif score >= 30:
            return "+1~3%"
        else:
            return "+0~2%"

    @staticmethod
    def _score_to_confidence(score: int) -> str:
        if score >= 60:
            return "high"
        elif score >= 40:
            return "medium"
        return "low"

    @staticmethod
    def _analyze_news_sentiment(news: List[Dict], lang: str = "ko") -> float:
        if not news:
            return 0

        pos_ko = ["상승", "급등", "호재", "최고", "돌파", "성장", "기대", "수혜", "회복", "강세"]
        neg_ko = ["하락", "급락", "악재", "위기", "폭락", "손실", "우려", "약세", "적자", "부진"]
        pos_en = ["surge", "rally", "beat", "growth", "upgrade", "bullish", "record", "gain"]
        neg_en = ["drop", "fall", "miss", "decline", "downgrade", "bearish", "loss", "risk"]

        pos_words = pos_ko if lang == "ko" else pos_en
        neg_words = neg_ko if lang == "ko" else neg_en

        pos_count = 0
        neg_count = 0

        for n in news:
            title = (n.get("title", "") + " " + n.get("description", "")).lower()
            for w in pos_words:
                if w in title:
                    pos_count += 1
            for w in neg_words:
                if w in title:
                    neg_count += 1

        total = pos_count + neg_count
        if total == 0:
            return 0
        return (pos_count - neg_count) / total
