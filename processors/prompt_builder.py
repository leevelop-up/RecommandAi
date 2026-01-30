"""
프롬프트 빌더 - 수집 데이터를 Gemini 프롬프트로 변환
4단계 분할 호출: 한국종목 → 미국종목 → 섹터/테마 → 종합TOP10
"""
from typing import Dict, List


SYSTEM_INSTRUCTION = """당신은 전문 주식 애널리스트입니다.
- 반드시 한국어로 응답하세요.
- 객관적이고 데이터 기반으로 분석하세요.
- 투자 위험도 반드시 언급하세요.
- JSON 형식으로만 응답하세요."""


def build_korea_stock_prompt(data: Dict) -> str:
    """한국 종목 분석 프롬프트"""
    lines = ["다음 한국 주식 데이터를 분석하고 추천 의견을 JSON으로 제공하세요.\n"]

    # 시장 지수
    indices = data.get("market_indices", {}).get("korea", {})
    if indices:
        lines.append("== 시장 지수 ==")
        for name, info in indices.items():
            val = info.get("value", "N/A")
            chg = info.get("change_rate", "N/A")
            lines.append(f"  {name}: {val} ({chg}%)")
        lines.append("")

    # 개별 종목
    stocks = data.get("korea_stocks", [])
    if stocks:
        lines.append("== 종목 데이터 ==")
        for s in stocks:
            p = s.get("price", {})
            f = s.get("fundamental", {})
            lines.append(f"\n[{s['name']}({s['ticker']})]")
            lines.append(f"  현재가: {p.get('current_price', 'N/A')}원")
            lines.append(f"  등락률: {p.get('change_rate', 'N/A')}%")
            lines.append(f"  거래량: {p.get('volume', 'N/A')}")
            lines.append(f"  PER: {f.get('per', 'N/A')}, PBR: {f.get('pbr', 'N/A')}")
            lines.append(f"  EPS: {f.get('eps', 'N/A')}, 배당률: {f.get('div_yield', 'N/A')}%")

            news = s.get("news", [])
            if news:
                titles = [n.get("title", "")[:40] for n in news[:3]]
                lines.append(f"  최근뉴스: {' | '.join(titles)}")

    # 테마 정보
    themes = data.get("themes", {})
    top_themes = themes.get("top_themes", [])
    if top_themes:
        lines.append("\n== 주요 상승 테마 ==")
        for t in top_themes[:5]:
            lines.append(f"  {t['name']}: {t['change_rate']}")
            top_stocks = [st.get("name", "") for st in t.get("stocks", [])[:5]]
            if top_stocks:
                lines.append(f"    주요종목: {', '.join(top_stocks)}")

    lines.append("""
응답 JSON 형식:
{
  "market_summary": "한국 시장 현황 요약 (2-3문장)",
  "market_sentiment": "bullish | neutral | bearish",
  "recommendations": [
    {
      "ticker": "종목코드",
      "name": "종목명",
      "action": "적극매수 | 매수 | 보유 | 매도고려 | 매도",
      "score": 0-100,
      "reasoning": "추천 근거 (2-3문장)",
      "risk_factors": ["리스크1", "리스크2"],
      "catalysts": ["촉매1", "촉매2"],
      "target_return": "예상 수익률 범위"
    }
  ]
}
모든 종목에 대해 분석하세요.""")

    return "\n".join(lines)


def build_usa_stock_prompt(data: Dict) -> str:
    """미국 종목 분석 프롬프트"""
    lines = ["다음 미국 주식 데이터를 분석하고 추천 의견을 JSON으로 제공하세요.\n"]

    # 시장 지수
    indices = data.get("market_indices", {}).get("usa", {})
    if indices:
        lines.append("== 미국 시장 지수 ==")
        for name, info in indices.items():
            price = info.get("price", "N/A")
            chg = info.get("change_percent", "N/A")
            lines.append(f"  {name}: {price} ({chg}%)")
        lines.append("")

    # 개별 종목
    stocks = data.get("usa_stocks", [])
    if stocks:
        lines.append("== 종목 데이터 ==")
        for s in stocks:
            p = s.get("price", {})
            f = s.get("fundamental", {})
            lines.append(f"\n[{s['name']}({s['ticker']})]")
            lines.append(f"  섹터: {s.get('sector', 'N/A')}")
            lines.append(f"  현재가: ${p.get('current_price', 'N/A')}")
            lines.append(f"  등락률: {p.get('change_rate', 'N/A')}%")
            lines.append(f"  52주 고가: ${p.get('fifty_two_week_high', 'N/A')}")
            lines.append(f"  52주 저가: ${p.get('fifty_two_week_low', 'N/A')}")
            lines.append(f"  P/E: {f.get('pe_ratio', 'N/A')}, P/B: {f.get('pb_ratio', 'N/A')}")
            lines.append(f"  ROE: {f.get('roe', 'N/A')}, 배당률: {f.get('dividend_yield', 'N/A')}")
            mcap = f.get("market_cap", 0)
            if mcap:
                mcap_str = f"${mcap/1e12:.2f}T" if mcap >= 1e12 else f"${mcap/1e9:.1f}B"
                lines.append(f"  시가총액: {mcap_str}")

            news = s.get("news", [])
            if news:
                titles = [n.get("title", "")[:40] for n in news[:3]]
                lines.append(f"  최근뉴스: {' | '.join(titles)}")

    lines.append("""
응답 JSON 형식:
{
  "market_summary": "미국 시장 현황 요약 (2-3문장)",
  "market_sentiment": "bullish | neutral | bearish",
  "recommendations": [
    {
      "ticker": "티커",
      "name": "종목명",
      "action": "적극매수 | 매수 | 보유 | 매도고려 | 매도",
      "score": 0-100,
      "reasoning": "추천 근거 (2-3문장)",
      "risk_factors": ["리스크1", "리스크2"],
      "catalysts": ["촉매1", "촉매2"],
      "target_return": "예상 수익률 범위"
    }
  ]
}
모든 종목에 대해 분석하세요.""")

    return "\n".join(lines)


def build_sector_theme_prompt(data: Dict) -> str:
    """섹터/테마 분석 프롬프트"""
    lines = ["다음 테마 및 섹터 데이터를 분석하세요.\n"]

    themes = data.get("themes", {})

    # 상위 테마
    top_themes = themes.get("top_themes", [])
    if top_themes:
        lines.append("== 상승률 상위 테마 ==")
        for t in top_themes:
            lines.append(f"\n[{t['name']}] 등락률: {t['change_rate']}")
            stocks = t.get("stocks", [])
            for st in stocks[:5]:
                lines.append(f"  - {st.get('name', '')}: {st.get('price', 0):,}원 ({st.get('change_rate', '')})")

    # 키워드 테마
    kw_themes = themes.get("keyword_themes", {})
    if kw_themes:
        lines.append("\n== 주요 키워드 테마 ==")
        for kw, info in kw_themes.items():
            lines.append(f"  {kw}: {info.get('theme_name', '')} ({info.get('change_rate', '')})")
            top = info.get("top_stocks", [])
            if top:
                lines.append(f"    주요종목: {', '.join(top)}")

    # 미국 섹터
    usa_stocks = data.get("usa_stocks", [])
    if usa_stocks:
        sectors: Dict[str, List] = {}
        for s in usa_stocks:
            sec = s.get("sector", "기타")
            if sec:
                sectors.setdefault(sec, []).append(s)

        if sectors:
            lines.append("\n== 미국 섹터별 종목 ==")
            for sec, stocks in sectors.items():
                names = [f"{s['ticker']}({s.get('price',{}).get('change_rate','N/A')}%)" for s in stocks]
                lines.append(f"  {sec}: {', '.join(names)}")

    # 뉴스
    news = data.get("market_news", [])
    if news:
        lines.append("\n== 최신 시장 뉴스 ==")
        for n in news[:8]:
            lines.append(f"  - {n.get('title', '')[:60]}")

    lines.append("""
응답 JSON 형식:
{
  "sector_analysis": [
    {
      "sector": "섹터/테마명",
      "outlook": "positive | neutral | negative",
      "reasoning": "분석 근거 (2-3문장)",
      "top_stocks": ["종목1", "종목2"]
    }
  ],
  "hot_themes": [
    {
      "name": "테마명",
      "momentum": "strong | moderate | weak",
      "reasoning": "분석 (1-2문장)"
    }
  ],
  "risk_assessment": {
    "overall_risk": "low | moderate | high",
    "key_risks": ["리스크1", "리스크2", "리스크3"],
    "opportunities": ["기회1", "기회2"]
  }
}""")

    return "\n".join(lines)


def build_top_picks_prompt(
    korea_result: Dict, usa_result: Dict, sector_result: Dict
) -> str:
    """종합 TOP10 선정 프롬프트"""
    lines = ["이전 분석 결과를 종합하여 한국+미국 통합 TOP 10 추천 종목을 선정하세요.\n"]

    # 한국 분석 요약
    if korea_result:
        lines.append("== 한국 종목 분석 결과 ==")
        lines.append(f"시장: {korea_result.get('market_summary', 'N/A')}")
        for r in korea_result.get("recommendations", []):
            lines.append(f"  {r['name']}({r['ticker']}): {r['action']} (점수:{r['score']})")

    # 미국 분석 요약
    if usa_result:
        lines.append("\n== 미국 종목 분석 결과 ==")
        lines.append(f"시장: {usa_result.get('market_summary', 'N/A')}")
        for r in usa_result.get("recommendations", []):
            lines.append(f"  {r['name']}({r['ticker']}): {r['action']} (점수:{r['score']})")

    # 섹터 분석 요약
    if sector_result:
        lines.append("\n== 섹터/테마 분석 ==")
        for s in sector_result.get("sector_analysis", []):
            lines.append(f"  {s['sector']}: {s['outlook']}")
        risk = sector_result.get("risk_assessment", {})
        if risk:
            lines.append(f"  전체 리스크: {risk.get('overall_risk', 'N/A')}")

    lines.append("""
한국과 미국 종목을 통합하여 가장 유망한 TOP 10을 선정하세요.

응답 JSON 형식:
{
  "overall_summary": "종합 시장 분석 (3-5문장)",
  "overall_sentiment": "bullish | neutral | bearish",
  "top_picks": [
    {
      "rank": 1,
      "ticker": "종목코드",
      "name": "종목명",
      "country": "KR | US",
      "action": "적극매수 | 매수 | 보유",
      "score": 0-100,
      "one_line": "한줄 추천 사유"
    }
  ],
  "avoid_list": [
    {
      "ticker": "종목코드",
      "name": "종목명",
      "reason": "회피 사유"
    }
  ]
}
반드시 10개 종목을 rank 순서대로 제공하세요.""")

    return "\n".join(lines)
