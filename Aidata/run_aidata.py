"""
AI 답변 전용 실행 스크립트
----------------------------------------------
입력:  output/scrap/  (스크랩 결과 4파일)
출력:  output/ai/     (AI 분석 결과)

실행:
    python Aidata/run_aidata.py

스크랩을 먼저 실행해야 함:
    python scrapers/run_scrapers.py   ← Step 1
    python Aidata/run_aidata.py       ← Step 2
"""
import sys
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from loguru import logger

from config.settings import get_settings
from processors.gemini_client import GeminiClient
from processors.groq_client   import GroqClient

SCRAP_DIR  = Path(ROOT_DIR) / "output" / "scrap"
AI_OUT_DIR = Path(ROOT_DIR) / "output" / "ai"

# ── 스크랩 파일 매핑 ─────────────────────────────────────────────────
_SCRAP_FILES = {
    "news":            "news_summary.json",
    "stocks":          "rising_stocks.json",
    "themes":          "rising_themes.json",
    "company_details": "company_details.json",
}


# ──────────────────────────────────────────────────────────────────────
# 데이터 로드
# ──────────────────────────────────────────────────────────────────────
def load_scrap_data() -> Dict:
    """output/scrap/ 4파일 로드"""
    data: Dict[str, dict] = {}
    for key, filename in _SCRAP_FILES.items():
        path = SCRAP_DIR / filename
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data[key] = json.load(f)
            logger.info(f"  ✅ {filename} 로드")
        else:
            logger.warning(f"  ⚠️  {filename} 없음 — 스크랩을 먼저 실행하세요")
            data[key] = {}
    return data


# ──────────────────────────────────────────────────────────────────────
# 프롬프트 빌드
# ──────────────────────────────────────────────────────────────────────
def build_prompt(data: Dict, engine_name: str) -> str:
    """스크랩 결과 4파일 → AI 프롬프트"""
    lines = [
        f"# {engine_name} AI — 금주 주식 추천 분석\n",
        "아래 수집된 데이터를 종합하여 금주 투자 전략을 제시하세요.\n",
    ]

    stocks_data  = data.get("stocks",          {})
    themes_data  = data.get("themes",          {})
    news_data    = data.get("news",            {})
    details_data = data.get("company_details", {})

    # ── 1. 시장 현황 ──────────────────────────────────────────────
    market = stocks_data.get("market_overview", {})
    lines.append("## 1. 시장 현황")

    lines.append("\n### 한국 시장")
    korea_market = market.get("korea", {})
    if korea_market:
        for name, info in korea_market.items():
            if isinstance(info, dict):
                lines.append(f"- {name}: {info.get('value', 'N/A')} ({info.get('change_rate', 'N/A')}%)")
            else:
                lines.append(f"- {name}: {info}")
    else:
        lines.append("- 데이터 없음")

    lines.append("\n### 미국 시장")
    usa_market = market.get("usa", {})
    if usa_market:
        for name, info in usa_market.items():
            if isinstance(info, dict):
                lines.append(f"- {name}: {info.get('price', 'N/A')} ({info.get('change_percent', 'N/A')}%)")
            else:
                lines.append(f"- {name}: {info}")
    else:
        lines.append("- 데이터 없음")

    # ── 2. Hot 테마 ───────────────────────────────────────────────
    themes = themes_data.get("themes", [])
    if themes:
        lines.append("\n## 2. Hot 테마")
        for theme in themes[:10]:
            lines.append(
                f"\n### {theme['rank']}. {theme['name']}  "
                f"(점수 {theme['score']}/100, 등락률 {theme['change_rate']})"
            )
            # 1차·2차·3차 관련주
            for tier_key, label in [("tier1_stocks", "1차"), ("tier2_stocks", "2차"), ("tier3_stocks", "3차")]:
                tier_stocks = theme.get(tier_key, [])
                if tier_stocks:
                    names = [
                        f"{s.get('name', '')}({s.get('change_rate', '')})"
                        for s in tier_stocks[:5]
                    ]
                    lines.append(f"- {label} 관련주: {', '.join(names)}")

            # 테마 관련 뉴스
            for n in theme.get("news", [])[:3]:
                lines.append(f"  · {n.get('title', '')[:60]}")

    # ── 3. 상승 종목 ──────────────────────────────────────────────
    kr_stocks = stocks_data.get("korea_stocks", [])
    us_stocks = stocks_data.get("usa_stocks",   [])
    all_stocks = kr_stocks + us_stocks

    if all_stocks:
        lines.append(f"\n## 3. 상승 종목 ({len(all_stocks)}개 중 상위 15)")
        for s in all_stocks[:15]:
            country = s.get("country", "KR")
            cur     = "원" if country == "KR" else "USD"
            price   = s.get("current_price", 0)
            try:
                price_fmt = f"{price:,}"
            except (TypeError, ValueError):
                price_fmt = str(price)

            lines.append(f"\n### {s.get('name', '')} ({s.get('ticker', '')}) [{country}]")
            lines.append(f"- 현재가: {price_fmt}{cur}, 등락률: {s.get('change_rate', '0%')}")
            lines.append(
                f"- PER: {s.get('per', 'N/A')}, "
                f"PBR: {s.get('pbr', 'N/A')}, "
                f"시가총액: {s.get('market_cap', 'N/A')}"
            )
            if s.get("sector"):
                lines.append(f"- 섹터: {s['sector']}")
            for n in s.get("news", [])[:2]:
                lines.append(f"  · {n.get('title', '')[:50]}")

    # ── 4. 테마별 관련주 세부 정보 (상위 5테마만) ─────────────────
    companies = details_data.get("companies", {})
    # 테마별로 그룹화
    theme_map: Dict[str, list] = {}
    for ticker, info in companies.items():
        for tn in info.get("themes", []):
            theme_map.setdefault(tn, []).append(info)

    if theme_map:
        lines.append("\n## 4. 테마별 관련주 세부 정보 (상위 5테마)")
        for tn, t_stocks in list(theme_map.items())[:5]:
            lines.append(f"\n### {tn}")
            for s in t_stocks[:5]:
                lines.append(
                    f"- {s.get('name', '')}({s.get('ticker', '')}): "
                    f"가격 {s.get('current_price', 0)}, "
                    f"PER {s.get('per', 'N/A')}, "
                    f"섹터 {s.get('sector', 'N/A')}"
                )

    # ── 5. 시장 뉴스 ──────────────────────────────────────────────
    articles = news_data.get("articles", [])
    if articles:
        lines.append(f"\n## 5. 주요 시장 뉴스 (총 {len(articles)}개 중 상위 10)")
        for i, a in enumerate(articles[:10], 1):
            src = a.get("_source", "")
            lines.append(f"{i}. [{src}] {a.get('title', '')[:60]}")

    # ── 응답 형식 ─────────────────────────────────────────────────
    lines.append("""
## 응답 형식 (반드시 이 JSON 구조를 따르세요)

```json
{
  "market_analysis": {
    "overall_sentiment": "매우 긍정적 | 긍정적 | 중립 | 부정적 | 매우 부정적",
    "korea_outlook": "한국 시장 전망 (1-2문장)",
    "usa_outlook": "미국 시장 전망 (1-2문장)",
    "key_trends": ["트렌드1", "트렌드2", "트렌드3"],
    "risks": ["리스크1", "리스크2"]
  },
  "top_themes_analysis": [
    {
      "theme": "테마명",
      "rating": "매우 강세 | 강세 | 보통 | 약세",
      "reasoning": "분석 근거 (1문장)",
      "recommended_stocks": ["종목명1", "종목명2", "종목명3"]
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
      "reasoning": "추천 근거 (1-2문장)",
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
      "reasoning": "근거 (1문장)"
    }
  ],
  "risk_warning": "전체 시장 위험 요소 (1-2문장)",
  "investment_strategy": "이번 주 투자 전략 요약 (2-3문장)"
}
```

중요:
1. 모든 분석은 제공된 실제 데이터와 뉴스를 기반으로 하세요
2. reasoning은 반드시 1-2문장으로 간결하게 작성하세요 (토큰 절약)
3. top_themes_analysis는 반드시 5개 이상 선정하세요
4. top_10_picks는 반드시 10개를 선정하세요
5. recommended_stocks에는 종목명(한글)만 기재하세요
""")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────
# AI 분석 (Gemini + Groq 듀얼)
# ──────────────────────────────────────────────────────────────────────
_SYSTEM_INSTRUCTION = """당신은 20년 경력의 전문 주식 애널리스트입니다.
- 한국어로 응답하세요.
- 데이터와 뉴스를 기반으로 객관적으로 분석하세요.
- 투자 위험과 기회를 균형있게 제시하세요.
- JSON 형식으로만 응답하세요."""


def run_ai_analysis(data: Dict) -> Dict:
    """Gemini + Groq 듀얼 분석"""
    settings = get_settings()
    result: Dict = {
        "generated_at":       datetime.now().isoformat(),
        "ai_recommendations": {},
    }

    # ── Gemini ──
    gemini_key = settings.GEMINI_API_KEY
    if gemini_key and gemini_key != "your-gemini-api-key":
        logger.info("[1/2] Gemini AI 분석 중...")
        try:
            gemini = GeminiClient(api_key=gemini_key)
            prompt = build_prompt(data, "Gemini")
            gemini_result = gemini.generate_json(
                prompt,
                system_instruction=_SYSTEM_INSTRUCTION,
                temperature=0.3,
                max_tokens=8192,
            )
            if gemini_result:
                gemini_result["engine"]      = "gemini"
                gemini_result["analyzed_at"] = datetime.now().isoformat()
                result["ai_recommendations"]["gemini"] = gemini_result
                logger.info("  ✅ Gemini 분석 완료")
            else:
                logger.warning("  ❌ Gemini 응답 비어있음")
        except Exception as e:
            logger.error(f"  ❌ Gemini 오류: {e}")
    else:
        logger.warning("[1/2] Gemini API 키 미설정 — 건너뜀")

    # ── Groq ──
    groq_key = settings.GROQ_API_KEY
    if groq_key and groq_key != "your-groq-api-key":
        logger.info("[2/2] Groq AI 분석 중...")
        try:
            groq = GroqClient(api_key=groq_key)
            if groq.is_available():
                prompt = build_prompt(data, "Groq")
                groq_result = groq.generate_json(
                    prompt,
                    system_instruction=_SYSTEM_INSTRUCTION,
                    temperature=0.3,
                    max_tokens=8192,
                )
                if groq_result:
                    groq_result["engine"]      = "groq"
                    groq_result["analyzed_at"] = datetime.now().isoformat()
                    result["ai_recommendations"]["groq"] = groq_result
                    logger.info("  ✅ Groq 분석 완료")
                else:
                    logger.warning("  ❌ Groq 응답 비어있음")
            else:
                logger.warning("  ❌ Groq 클라이언트 초기화 실패 (패키지 or 키 문제)")
        except Exception as e:
            logger.error(f"  ❌ Groq 오류: {e}")
    else:
        logger.warning("[2/2] Groq API 키 미설정 — 건너뜀")

    if not result["ai_recommendations"]:
        logger.error("❌ 모든 AI 분석 실패 — API 키를 확인하세요")

    return result


# ──────────────────────────────────────────────────────────────────────
# 결과 저장
# ──────────────────────────────────────────────────────────────────────
def save_ai_result(result: Dict) -> Path:
    """output/ai/ 저장"""
    AI_OUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path      = AI_OUT_DIR / f"weekly_recommendation_{timestamp}.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    logger.info(f"  ✅ {path} 저장")
    return path


# ──────────────────────────────────────────────────────────────────────
# 로거 설정 + main
# ──────────────────────────────────────────────────────────────────────
def setup_logger():
    logger.remove()
    log_dir = Path(ROOT_DIR) / "logs"
    log_dir.mkdir(exist_ok=True)
    logger.add(
        sys.stderr, level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {message}",
    )
    logger.add(
        str(log_dir / "aidata_{time:YYYYMMDD}.log"),
        level="DEBUG", rotation="1 day", retention="30 days",
    )


if __name__ == "__main__":
    setup_logger()

    logger.info("=" * 70)
    logger.info("  AI 분석 시작  →  output/ai/")
    logger.info("=" * 70)

    logger.info("\n📂 스크랩 데이터 로드...")
    data = load_scrap_data()

    logger.info("\n🤖 AI 분석...")
    result = run_ai_analysis(data)

    logger.info("\n💾 결과 저장...")
    save_ai_result(result)

    logger.info("\n" + "=" * 70)
    logger.info("  AI 분석 완료")
    logger.info("=" * 70)
