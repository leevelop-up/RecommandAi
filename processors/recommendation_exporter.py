"""
추천 결과 내보내기 - 텍스트 리포트 + JSON (Spring 백엔드용)
"""
import os
import json
from datetime import datetime
from typing import Dict
from loguru import logger


class RecommendationExporter:
    """추천 결과를 텍스트/JSON 파일로 내보내기"""

    def __init__(self, output_dir: str = "."):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def export(self, result: Dict) -> Dict[str, str]:
        """텍스트 + JSON 동시 내보내기"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        txt_path = self._export_text(result, timestamp)
        json_path = self._export_json(result, timestamp)

        logger.info(f"텍스트 리포트: {txt_path}")
        logger.info(f"JSON 데이터: {json_path}")

        return {"text": txt_path, "json": json_path}

    def _export_text(self, result: Dict, timestamp: str) -> str:
        """사람용 텍스트 리포트"""
        lines = []
        engine = result.get("engine", "unknown")
        gen_at = result.get("generated_at", "")

        lines.append("=" * 80)
        lines.append("  AI 주식 추천 리포트")
        lines.append(f"  생성 시간: {gen_at}")
        lines.append(f"  분석 엔진: {engine}")
        lines.append("=" * 80)

        # 1. 시장 개요
        overview = result.get("market_overview", {})
        lines.append("\n" + "=" * 80)
        lines.append("[1] 시장 개요")
        lines.append("=" * 80)
        lines.append(f"\n{overview.get('summary', 'N/A')}")
        lines.append(f"\n시장 심리: {overview.get('sentiment', 'N/A')}")
        if overview.get("korea_summary"):
            lines.append(f"한국: {overview['korea_summary']}")
        if overview.get("usa_summary"):
            lines.append(f"미국: {overview['usa_summary']}")

        # 2. 한국 추천 종목
        kr_recs = result.get("recommendations", {}).get("korea", [])
        if kr_recs:
            lines.append("\n" + "=" * 80)
            lines.append(f"[2] 한국 추천 종목 ({len(kr_recs)}개)")
            lines.append("=" * 80)
            lines.append(f"\n{'순위':>4} {'종목명':<12} {'종목코드':<8} {'의견':<8} {'점수':>5} {'추천근거'}")
            lines.append("-" * 80)

            sorted_kr = sorted(kr_recs, key=lambda x: x.get("score", 0), reverse=True)
            for i, r in enumerate(sorted_kr, 1):
                name = r.get("name", "")[:10]
                ticker = r.get("ticker", "")
                action = r.get("action", "")
                score = r.get("score", 0)
                reason = r.get("reasoning", "")[:45]
                lines.append(f"{i:>4}. {name:<12} {ticker:<8} {action:<8} {score:>4}점  {reason}")

            # 상세 정보
            lines.append("\n--- 상세 분석 ---")
            for r in sorted_kr[:5]:
                lines.append(f"\n  [{r.get('name', '')}({r.get('ticker', '')})] - {r.get('action', '')} ({r.get('score', 0)}점)")
                lines.append(f"  근거: {r.get('reasoning', 'N/A')}")
                risks = r.get("risk_factors", [])
                if risks:
                    lines.append(f"  리스크: {', '.join(risks[:3])}")
                cats = r.get("catalysts", [])
                if cats:
                    lines.append(f"  촉매: {', '.join(cats[:3])}")
                tr = r.get("target_return", "")
                if tr:
                    lines.append(f"  예상수익: {tr}")

        # 3. 미국 추천 종목
        us_recs = result.get("recommendations", {}).get("usa", [])
        if us_recs:
            lines.append("\n" + "=" * 80)
            lines.append(f"[3] 미국 추천 종목 ({len(us_recs)}개)")
            lines.append("=" * 80)
            lines.append(f"\n{'순위':>4} {'종목명':<18} {'티커':<6} {'의견':<8} {'점수':>5} {'추천근거'}")
            lines.append("-" * 80)

            sorted_us = sorted(us_recs, key=lambda x: x.get("score", 0), reverse=True)
            for i, r in enumerate(sorted_us, 1):
                name = r.get("name", "")[:16]
                ticker = r.get("ticker", "")
                action = r.get("action", "")
                score = r.get("score", 0)
                reason = r.get("reasoning", "")[:40]
                lines.append(f"{i:>4}. {name:<18} {ticker:<6} {action:<8} {score:>4}점  {reason}")

            lines.append("\n--- 상세 분석 ---")
            for r in sorted_us[:5]:
                lines.append(f"\n  [{r.get('name', '')}({r.get('ticker', '')})] - {r.get('action', '')} ({r.get('score', 0)}점)")
                lines.append(f"  근거: {r.get('reasoning', 'N/A')}")
                risks = r.get("risk_factors", [])
                if risks:
                    lines.append(f"  리스크: {', '.join(risks[:3])}")
                cats = r.get("catalysts", [])
                if cats:
                    lines.append(f"  촉매: {', '.join(cats[:3])}")

        # 4. 섹터/테마 분석
        sectors = result.get("sector_analysis", [])
        if sectors:
            lines.append("\n" + "=" * 80)
            lines.append("[4] 섹터/테마 분석")
            lines.append("=" * 80)
            for s in sectors:
                outlook = s.get("outlook", "neutral")
                icon = {"positive": "+", "negative": "-", "neutral": "="}.get(outlook, "=")
                lines.append(f"\n  [{icon}] {s.get('sector', '')}: {outlook}")
                lines.append(f"      {s.get('reasoning', '')}")
                top = s.get("top_stocks", [])
                if top:
                    lines.append(f"      주요종목: {', '.join(top[:5])}")

        # 5. 종합 TOP 10
        top_picks = result.get("top_picks", [])
        if top_picks:
            lines.append("\n" + "=" * 80)
            lines.append("[5] 종합 TOP 10 추천")
            lines.append("=" * 80)
            lines.append(f"\n{'순위':>4} {'종목명':<15} {'코드':<8} {'국가':>4} {'의견':<8} {'점수':>5} {'한줄요약'}")
            lines.append("-" * 80)
            for p in top_picks:
                name = p.get("name", "")[:13]
                ticker = p.get("ticker", "")
                country = p.get("country", "")
                action = p.get("action", "")
                score = p.get("score", 0)
                one = p.get("one_line", "")[:35]
                lines.append(f"{p.get('rank', ''):>4}. {name:<15} {ticker:<8} {country:>4} {action:<8} {score:>4}점  {one}")

        # 6. 리스크 평가
        risk = result.get("risk_assessment", {})
        if risk:
            lines.append("\n" + "=" * 80)
            lines.append("[6] 리스크 평가")
            lines.append("=" * 80)
            lines.append(f"\n전체 리스크: {risk.get('overall_risk', 'N/A')}")
            key_risks = risk.get("key_risks", [])
            if key_risks:
                lines.append("주요 리스크:")
                for kr_item in key_risks:
                    lines.append(f"  - {kr_item}")
            opps = risk.get("opportunities", [])
            if opps:
                lines.append("기회 요인:")
                for o in opps:
                    lines.append(f"  + {o}")

        # 7. 회피 종목
        avoid = result.get("avoid_list", [])
        if avoid:
            lines.append("\n" + "=" * 80)
            lines.append("[7] 회피 추천 종목")
            lines.append("=" * 80)
            for a in avoid:
                lines.append(f"  - {a.get('name', '')}({a.get('ticker', '')}): {a.get('reason', '')}")

        # 면책 조항
        lines.append("\n" + "=" * 80)
        lines.append("  [면책 조항]")
        lines.append("  본 리포트는 AI 분석 결과이며 투자 권유가 아닙니다.")
        lines.append("  투자 결정은 본인의 판단과 책임하에 이루어져야 합니다.")
        lines.append("=" * 80)

        filepath = os.path.join(self.output_dir, f"ai_recommendation_{timestamp}.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return filepath

    def _export_json(self, result: Dict, timestamp: str) -> str:
        """Spring 백엔드용 JSON"""
        filepath = os.path.join(self.output_dir, f"ai_recommendation_{timestamp}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return filepath

    # =========================================================================
    # 급등 예측 내보내기
    # =========================================================================
    def export_growth(self, result: Dict) -> Dict[str, str]:
        """급등 예측 결과 텍스트 + JSON 내보내기"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        txt_path = self._export_growth_text(result, timestamp)
        json_path = self._export_growth_json(result, timestamp)

        logger.info(f"급등 예측 리포트: {txt_path}")
        logger.info(f"급등 예측 JSON: {json_path}")

        return {"text": txt_path, "json": json_path}

    def _export_growth_text(self, result: Dict, timestamp: str) -> str:
        """급등 예측 텍스트 리포트"""
        lines = []
        engine = result.get("engine", "unknown")

        lines.append("=" * 80)
        lines.append("  급등 예측 리포트")
        lines.append(f"  생성 시간: {result.get('generated_at', '')}")
        lines.append(f"  분석 엔진: {engine}")
        lines.append("=" * 80)

        # 요약
        summary = result.get("prediction_summary", "")
        if summary:
            lines.append(f"\n{summary}")

        # 한국 급등 후보
        kr_picks = result.get("korea_picks", [])
        if kr_picks:
            lines.append("\n" + "=" * 80)
            lines.append(f"[1] 한국 급등 예측 ({len(kr_picks)}종목)")
            lines.append("=" * 80)
            lines.append(f"\n{'순위':>4} {'종목명':<12} {'코드':<8} {'현재등락':>8} {'예상수익':>10} {'신뢰도':<8} {'근거'}")
            lines.append("-" * 80)

            for p in kr_picks:
                name = p.get("name", "")[:10]
                ticker = p.get("ticker", "")
                chg = p.get("change_rate", 0)
                ret = p.get("predicted_return", "")
                conf = p.get("confidence", "")
                reason = p.get("reasoning", "")[:35]
                rank = p.get("rank", "")
                lines.append(f"{rank:>4}. {name:<12} {ticker:<8} {chg:>+7.1f}% {ret:>10} {conf:<8} {reason}")

            # 상세
            lines.append("\n--- 상세 분석 ---")
            for p in kr_picks[:5]:
                lines.append(f"\n  [{p.get('name', '')}({p.get('ticker', '')})]")
                lines.append(f"  예상 수익: {p.get('predicted_return', 'N/A')} (신뢰도: {p.get('confidence', 'N/A')})")
                lines.append(f"  기간: {p.get('timeframe', 'N/A')}")
                lines.append(f"  근거: {p.get('reasoning', 'N/A')}")
                if p.get("entry_point"):
                    lines.append(f"  진입: {p['entry_point']}")
                if p.get("stop_loss"):
                    lines.append(f"  손절: {p['stop_loss']}")

        # 미국 급등 후보
        us_picks = result.get("usa_picks", [])
        if us_picks:
            lines.append("\n" + "=" * 80)
            lines.append(f"[2] 미국 급등 예측 ({len(us_picks)}종목)")
            lines.append("=" * 80)
            lines.append(f"\n{'순위':>4} {'종목명':<18} {'티커':<6} {'현재등락':>8} {'예상수익':>10} {'신뢰도':<8} {'근거'}")
            lines.append("-" * 80)

            for p in us_picks:
                name = p.get("name", "")[:16]
                ticker = p.get("ticker", "")
                chg = p.get("change_rate", 0)
                ret = p.get("predicted_return", "")
                conf = p.get("confidence", "")
                reason = p.get("reasoning", "")[:30]
                rank = p.get("rank", "")
                lines.append(f"{rank:>4}. {name:<18} {ticker:<6} {chg:>+7.1f}% {ret:>10} {conf:<8} {reason}")

            lines.append("\n--- 상세 분석 ---")
            for p in us_picks[:5]:
                lines.append(f"\n  [{p.get('name', '')}({p.get('ticker', '')})]")
                lines.append(f"  예상 수익: {p.get('predicted_return', 'N/A')} (신뢰도: {p.get('confidence', 'N/A')})")
                lines.append(f"  근거: {p.get('reasoning', 'N/A')}")

        # 테마 플레이
        themes = result.get("theme_picks", [])
        if themes:
            lines.append("\n" + "=" * 80)
            lines.append(f"[3] 급등 테마 ({len(themes)}개)")
            lines.append("=" * 80)

            for t in themes:
                name = t.get("theme_name", t.get("theme", ""))
                rate = t.get("theme_rate", 0)
                momentum = t.get("momentum", "")
                lines.append(f"\n  [{name}] +{rate:.1f}% ({momentum})")
                if t.get("signal"):
                    lines.append(f"  시그널: {t['signal']}")
                if t.get("reasoning"):
                    lines.append(f"  분석: {t['reasoning']}")
                top_stocks = t.get("top_stocks", [])
                if top_stocks:
                    stock_names = []
                    for st in top_stocks[:5]:
                        if isinstance(st, dict):
                            sn = st.get("name", "")
                            sr = st.get("change_rate", 0)
                            stock_names.append(f"{sn}({sr:+.1f}%)" if sr else sn)
                        else:
                            stock_names.append(str(st))
                    lines.append(f"  수혜종목: {', '.join(stock_names)}")

        # 면책
        warning = result.get("risk_warning", "")
        lines.append("\n" + "=" * 80)
        lines.append("  [투자 위험 고지]")
        lines.append(f"  {warning}" if warning else
                     "  본 예측은 참고용이며, 투자 손실의 책임은 투자자에게 있습니다.")
        lines.append("=" * 80)

        filepath = os.path.join(self.output_dir, f"growth_prediction_{timestamp}.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return filepath

    def _export_growth_json(self, result: Dict, timestamp: str) -> str:
        """급등 예측 JSON"""
        filepath = os.path.join(self.output_dir, f"growth_prediction_{timestamp}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return filepath
