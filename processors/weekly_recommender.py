"""
금주 추천 엔진 - Gemini + Groq 듀얼 AI 분석
뉴스 기반 동적 분석으로 하드코딩 없는 추천 생성
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger

from processors.gemini_client import GeminiClient
from processors.groq_client import GroqClient
from config.settings import get_settings


class WeeklyRecommender:
    """금주 추천 생성기 (Gemini + Groq 듀얼 AI)"""

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        groq_api_key: Optional[str] = None,
    ):
        settings = get_settings()
        self.gemini_key = gemini_api_key or settings.GEMINI_API_KEY
        self.groq_key = groq_api_key or settings.GROQ_API_KEY

        self.gemini_client = None
        self.groq_client = None

        if self.gemini_key:
            self.gemini_client = GeminiClient(api_key=self.gemini_key)
            logger.info("✅ Gemini AI 엔진 활성화")

        if self.groq_key:
            self.groq_client = GroqClient(api_key=self.groq_key)
            logger.info("✅ Groq AI 엔진 활성화")

    def generate_weekly_recommendations(self, data: Dict) -> Dict:
        """
        금주 추천 생성

        Args:
            data: enhanced_data_collector에서 수집한 데이터

        Returns:
            {
                "generated_at": str,
                "schedule_time": "09:00",
                "hot_themes": List[Dict],  # 10개
                "weekly_recommendations": List[Dict],  # 30개
                "ai_recommendations": {
                    "gemini": Dict,
                    "groq": Dict,
                },
                "market_overview": Dict,
            }
        """
        logger.info("=" * 80)
        logger.info("  금주 추천 생성 시작 (Gemini + Groq 듀얼 AI)")
        logger.info("=" * 80)

        result = {
            "generated_at": datetime.now().isoformat(),
            "schedule_time": "09:00",
            "hot_themes": data.get("hot_themes", []),
            "weekly_recommendations": data.get("weekly_recommendations", []),
            "market_overview": data.get("market_overview", {}),
            "ai_recommendations": {},
        }

        # Gemini 분석
        if self.gemini_client and self.gemini_client.is_available():
            logger.info("\n[1/2] Gemini AI 분석 중...")
            gemini_result = self._analyze_with_gemini(data)
            if gemini_result:
                result["ai_recommendations"]["gemini"] = gemini_result
                logger.info("✅ Gemini 분석 완료")
            else:
                logger.warning("❌ Gemini 분석 실패")

        # Groq 분석
        if self.groq_client and self.groq_client.is_available():
            logger.info("\n[2/2] Groq AI 분석 중...")
            groq_result = self._analyze_with_groq(data)
            if groq_result:
                result["ai_recommendations"]["groq"] = groq_result
                logger.info("✅ Groq 분석 완료")
            else:
                logger.warning("❌ Groq 분석 실패")

        # AI 분석이 하나도 없으면 경고
        if not result["ai_recommendations"]:
            logger.error("❌ 모든 AI 분석 실패 - API 키를 확인하세요")

        logger.info("=" * 80)
        logger.info("  금주 추천 생성 완료")
        logger.info("=" * 80)

        return result

    def _analyze_with_gemini(self, data: Dict) -> Optional[Dict]:
        """Gemini AI로 종합 분석"""
        try:
            prompt = self._build_comprehensive_prompt(data, "Gemini")

            system_instruction = """당신은 20년 경력의 전문 주식 애널리스트입니다.
- 한국어로 응답하세요.
- 데이터와 뉴스를 기반으로 객관적으로 분석하세요.
- 투자 위험과 기회를 균형있게 제시하세요.
- JSON 형식으로만 응답하세요."""

            result = self.gemini_client.generate_json(
                prompt,
                system_instruction=system_instruction,
                temperature=0.3
            )

            if result:
                result["engine"] = "gemini"
                result["analyzed_at"] = datetime.now().isoformat()

            return result

        except Exception as e:
            logger.error(f"Gemini 분석 실패: {e}")
            return None

    def _analyze_with_groq(self, data: Dict) -> Optional[Dict]:
        """Groq AI로 종합 분석"""
        try:
            prompt = self._build_comprehensive_prompt(data, "Groq")

            system_instruction = """당신은 20년 경력의 전문 주식 애널리스트입니다.
- 한국어로 응답하세요.
- 데이터와 뉴스를 기반으로 객관적으로 분석하세요.
- 투자 위험과 기회를 균형있게 제시하세요.
- JSON 형식으로만 응답하세요."""

            result = self.groq_client.generate_json(
                prompt,
                system_instruction=system_instruction,
                temperature=0.3
            )

            if result:
                result["engine"] = "groq"
                result["analyzed_at"] = datetime.now().isoformat()

            return result

        except Exception as e:
            logger.error(f"Groq 분석 실패: {e}")
            return None

    def _build_comprehensive_prompt(self, data: Dict, engine_name: str) -> str:
        """종합 분석 프롬프트 생성"""
        lines = [
            f"# {engine_name} AI - 금주 주식 추천 분석\n",
            "다음 데이터를 분석하여 금주 투자 전략을 제시하세요.\n",
        ]

        # 시장 개요
        market = data.get("market_overview", {})
        korea = market.get("korea", {})
        usa = market.get("usa", {})

        lines.append("## 1. 시장 현황")
        lines.append("\n### 한국 시장")
        for name, info in korea.items():
            val = info.get("value", "N/A")
            chg = info.get("change_rate", "N/A")
            lines.append(f"- {name}: {val} ({chg}%)")

        lines.append("\n### 미국 시장")
        for name, info in usa.items():
            price = info.get("price", "N/A")
            chg = info.get("change_percent", "N/A")
            lines.append(f"- {name}: {price} ({chg}%)")

        # Hot 테마
        hot_themes = data.get("hot_themes", [])
        if hot_themes:
            lines.append("\n## 2. Hot 테마 (상위 10개)")
            for theme in hot_themes[:10]:
                lines.append(f"\n### {theme['rank']}. {theme['name']}")
                lines.append(f"- 점수: {theme['score']}/100")
                lines.append(f"- 등락률: {theme['change_rate']}")
                lines.append(f"- 종목 수: {theme['stock_count']}개")

                # 1차 관련주
                tier1 = theme.get("tier1_stocks", [])
                if tier1:
                    tier1_names = [f"{s['name']}({s['change_rate']})" for s in tier1[:5]]
                    lines.append(f"- 핵심 종목: {', '.join(tier1_names)}")

                # 뉴스
                news = theme.get("news", [])
                if news:
                    lines.append("- 최근 뉴스:")
                    for n in news[:3]:
                        lines.append(f"  · {n.get('title', '')[:60]}")

        # 금주 추천 후보 종목
        weekly = data.get("weekly_recommendations", [])
        if weekly:
            lines.append("\n## 3. 금주 추천 후보 종목 (30개)")
            for stock in weekly[:30]:
                lines.append(f"\n### {stock['name']} ({stock['ticker']}) - {stock['country']}")
                lines.append(f"- 현재가: {stock['current_price']:,}{'원' if stock['country']=='KR' else 'USD'}")
                lines.append(f"- 전일대비: {stock['daily_change_rate']}")
                lines.append(f"- 시가총액: {stock['market_cap']}")
                lines.append(f"- PER: {stock['per']}, PBR: {stock.get('pbr', 'N/A')}")
                lines.append(f"- 배당률: {stock['dividend_yield']}")
                lines.append(f"- 섹터: {stock.get('sector', 'N/A')}")

                # 뉴스
                news = stock.get("news", [])
                if news:
                    lines.append("- 최근 뉴스:")
                    for n in news[:2]:
                        lines.append(f"  · {n.get('title', '')[:50]}")

                # 투자 포인트
                points = stock.get("investment_points", [])
                if points:
                    lines.append(f"- 투자 포인트: {', '.join(points[:2])}")

        # 시장 뉴스
        market_news = data.get("market_news", {})
        if market_news:
            all_news = []
            for source, news_list in market_news.get("sources", {}).items():
                all_news.extend(news_list[:5])

            if all_news:
                lines.append("\n## 4. 주요 시장 뉴스")
                for i, news in enumerate(all_news[:20], 1):
                    lines.append(f"{i}. {news.get('title', '')[:80]}")

        # 응답 형식
        lines.append("""

## 응답 형식 (반드시 이 JSON 구조를 따르세요)

```json
{
  "market_analysis": {
    "overall_sentiment": "매우 긍정적 | 긍정적 | 중립 | 부정적 | 매우 부정적",
    "korea_outlook": "시장 전망 (2-3문장)",
    "usa_outlook": "시장 전망 (2-3문장)",
    "key_trends": ["트렌드1", "트렌드2", "트렌드3"],
    "risks": ["리스크1", "리스크2"]
  },
  "top_themes_analysis": [
    {
      "theme": "테마명",
      "rating": "매우 강세 | 강세 | 보통 | 약세",
      "reasoning": "분석 근거 (2-3문장)",
      "recommended_stocks": ["종목1", "종목2", "종목3"]
    }
  ],
  "top_10_picks": [
    {
      "rank": 1,
      "ticker": "종목코드",
      "name": "종목명",
      "country": "KR | US",
      "action": "적극매수 | 매수 | 보유",
      "target_return": "10-15%",
      "reasoning": "추천 근거 (3-4문장, 구체적인 재무지표와 뉴스 기반)",
      "entry_price": "추천 매수가",
      "target_price": "목표가",
      "stop_loss": "손절가",
      "investment_period": "단기(1개월) | 중기(3개월) | 장기(6개월+)"
    }
  ],
  "sector_recommendations": [
    {
      "sector": "섹터명",
      "rating": "비중확대 | 중립 | 비중축소",
      "reasoning": "근거 (2문장)"
    }
  ],
  "risk_warning": "전체 시장 위험 요소 (3-4문장)",
  "investment_strategy": "이번 주 투자 전략 요약 (4-5문장)"
}
```

**중요:**
1. 모든 분석은 제공된 실제 데이터와 뉴스를 기반으로 하세요
2. 구체적인 숫자와 근거를 제시하세요
3. 긍정적/부정적 측면을 균형있게 다루세요
4. 투자 위험을 명확히 언급하세요
5. top_10_picks는 반드시 10개를 선정하세요
""")

        return "\n".join(lines)
