"""
강화된 규칙 기반 분석 엔진 (AI fallback)
"""
import re
from typing import Dict, List, Tuple
from datetime import datetime
from loguru import logger


# 뉴스 감성 키워드 (확장)
KR_POSITIVE = [
    "상승", "호재", "성장", "실적", "흑자", "증가", "신고가", "돌파",
    "호실적", "사상최고", "매출증가", "영업이익", "수주", "계약",
    "배당", "자사주", "소각", "수요증가", "수출호조", "강세",
    "반등", "급등", "수혜", "목표상향", "투자확대", "성과",
]
KR_NEGATIVE = [
    "하락", "악재", "감소", "적자", "위기", "우려", "급락", "손실",
    "실적부진", "매출감소", "영업손실", "부채", "리콜", "소송",
    "제재", "규제", "감원", "구조조정", "하향", "매도",
    "폭락", "약세", "경고", "위험", "파산", "부실",
]
EN_POSITIVE = [
    "surge", "beat", "upgrade", "growth", "profit", "record",
    "bullish", "rally", "strong", "gain", "outperform", "buy",
    "dividend", "buyback", "expansion", "positive", "rises",
]
EN_NEGATIVE = [
    "drop", "miss", "downgrade", "decline", "loss", "layoff",
    "bearish", "sell", "weak", "warning", "risk", "crash",
    "bankruptcy", "debt", "lawsuit", "regulation", "falls",
]


class EnhancedRuleEngine:
    """강화된 규칙 기반 주식 분석 엔진"""

    def analyze_all(self, data: Dict) -> Dict:
        """전체 데이터 규칙 기반 분석"""
        logger.info("[규칙 기반] 분석 시작")

        market_ctx = self._build_market_context(data.get("market_indices", {}))

        # 한국 종목 분석
        kr_recs = []
        for stock in data.get("korea_stocks", []):
            result = self.analyze_korea_stock(stock, market_ctx)
            kr_recs.append(result)
        kr_recs.sort(key=lambda x: x["score"], reverse=True)

        # 미국 종목 분석
        us_recs = []
        for stock in data.get("usa_stocks", []):
            result = self.analyze_usa_stock(stock, market_ctx)
            us_recs.append(result)
        us_recs.sort(key=lambda x: x["score"], reverse=True)

        # 섹터/테마 분석
        sector_analysis = self._analyze_sectors(data.get("themes", {}))

        # 리스크 평가
        risk = self._assess_risk(data)

        # 종합 TOP 10
        all_recs = kr_recs + us_recs
        all_recs.sort(key=lambda x: x["score"], reverse=True)
        top_picks = []
        for i, r in enumerate(all_recs[:10], 1):
            top_picks.append({
                "rank": i,
                "ticker": r["ticker"],
                "name": r["name"],
                "country": r["country"],
                "action": r["action"],
                "score": r["score"],
                "one_line": r["reasoning"][:60] if r["reasoning"] else "",
            })

        result = {
            "generated_at": datetime.now().isoformat(),
            "engine": "rule_based",
            "market_overview": market_ctx,
            "recommendations": {
                "korea": kr_recs,
                "usa": us_recs,
            },
            "sector_analysis": sector_analysis,
            "risk_assessment": risk,
            "top_picks": top_picks,
        }

        logger.info(f"[규칙 기반] 분석 완료: 한국 {len(kr_recs)}종목, 미국 {len(us_recs)}종목")
        return result

    def analyze_korea_stock(self, stock: Dict, market_ctx: Dict) -> Dict:
        """한국 종목 분석"""
        price = stock.get("price", {})
        fund = stock.get("fundamental", {})
        news = stock.get("news", [])

        score = 0
        reasons = []

        # 1. 밸류에이션 (0-30점)
        val_score, val_reason = self._score_valuation(
            fund.get("per", 0), fund.get("pbr", 0), "KR"
        )
        score += val_score
        reasons.extend(val_reason)

        # 2. 모멘텀 (0-20점)
        change = price.get("change", 0)
        change_rate = price.get("change_rate", 0)
        mkt_change = market_ctx.get("korea_change", 0)
        mom_score, mom_reason = self._score_momentum(change, change_rate, mkt_change)
        score += mom_score
        reasons.extend(mom_reason)

        # 3. 펀더멘탈 품질 (0-25점)
        fund_score, fund_reason = self._score_fundamentals_kr(fund)
        score += fund_score
        reasons.extend(fund_reason)

        # 4. 뉴스 감성 (0-15점)
        sentiment = self._analyze_news_sentiment(news, "KR")
        news_score, news_reason = self._score_news(sentiment)
        score += news_score
        reasons.extend(news_reason)

        # 5. 테마 모멘텀 (0-10점)
        theme_score, theme_reason = self._score_theme(stock)
        score += theme_score
        reasons.extend(theme_reason)

        score = max(0, min(100, score))
        action, grade = self._get_action(score)

        return {
            "ticker": stock["ticker"],
            "name": stock["name"],
            "country": "KR",
            "current_price": price.get("current_price", 0),
            "change_rate": change_rate,
            "score": score,
            "grade": grade,
            "action": action,
            "reasoning": " / ".join(reasons[:5]),
            "risk_factors": self._get_risk_factors_kr(fund, price),
            "catalysts": self._get_catalysts_kr(fund, price, sentiment),
            "fundamentals": {
                "per": fund.get("per", 0),
                "pbr": fund.get("pbr", 0),
                "eps": fund.get("eps", 0),
            },
            "news_sentiment": sentiment,
        }

    def analyze_usa_stock(self, stock: Dict, market_ctx: Dict) -> Dict:
        """미국 종목 분석"""
        price = stock.get("price", {})
        fund = stock.get("fundamental", {})
        news = stock.get("news", [])

        score = 0
        reasons = []

        # 1. 밸류에이션 (0-30점)
        pe = fund.get("pe_ratio", 0) or 0
        pb = fund.get("pb_ratio", 0) or 0
        val_score, val_reason = self._score_valuation(pe, pb, "US")
        score += val_score
        reasons.extend(val_reason)

        # 2. 모멘텀 (0-20점)
        change_rate = price.get("change_rate", 0)
        mkt_change = market_ctx.get("usa_change", 0)
        mom_score, mom_reason = self._score_momentum(0, change_rate, mkt_change)
        score += mom_score
        reasons.extend(mom_reason)

        # 3. 펀더멘탈 품질 (0-25점)
        fund_score, fund_reason = self._score_fundamentals_us(fund, price)
        score += fund_score
        reasons.extend(fund_reason)

        # 4. 뉴스 감성 (0-15점)
        sentiment = self._analyze_news_sentiment(news, "US")
        news_score, news_reason = self._score_news(sentiment)
        score += news_score
        reasons.extend(news_reason)

        # 5. 섹터 보너스 (0-10점)
        sector_score, sector_reason = self._score_sector(stock)
        score += sector_score
        reasons.extend(sector_reason)

        score = max(0, min(100, score))
        action, grade = self._get_action(score)

        return {
            "ticker": stock["ticker"],
            "name": stock.get("name", stock["ticker"]),
            "country": "US",
            "sector": stock.get("sector", ""),
            "current_price": price.get("current_price", 0),
            "change_rate": change_rate,
            "score": score,
            "grade": grade,
            "action": action,
            "reasoning": " / ".join(reasons[:5]),
            "risk_factors": self._get_risk_factors_us(fund, price),
            "catalysts": self._get_catalysts_us(fund, price, sentiment),
            "fundamentals": {
                "pe_ratio": pe,
                "pb_ratio": pb,
                "roe": fund.get("roe", 0),
                "dividend_yield": fund.get("dividend_yield", 0),
            },
            "news_sentiment": sentiment,
        }

    # ── 스코어링 ──

    def _score_valuation(self, per: float, pbr: float, country: str) -> Tuple[int, List[str]]:
        """밸류에이션 점수 (0-30)"""
        score = 0
        reasons = []
        per = per or 0
        pbr = pbr or 0

        if country == "KR":
            if 0 < per < 10:
                score += 18
                reasons.append(f"PER {per:.1f} 저평가")
            elif 10 <= per < 15:
                score += 14
                reasons.append(f"PER {per:.1f} 적정")
            elif 15 <= per < 25:
                score += 6
                reasons.append(f"PER {per:.1f} 다소 높음")
            elif per >= 25:
                score += 0
                reasons.append(f"PER {per:.1f} 고평가")

            if 0 < pbr < 1:
                score += 12
                reasons.append(f"PBR {pbr:.2f} 자산가치 저평가")
            elif 1 <= pbr < 2:
                score += 8
            elif 2 <= pbr < 5:
                score += 2
            # pbr >= 5: +0
        else:
            if 0 < per < 15:
                score += 18
                reasons.append(f"P/E {per:.1f} 저평가")
            elif 15 <= per < 25:
                score += 12
                reasons.append(f"P/E {per:.1f} 적정")
            elif 25 <= per < 40:
                score += 4
                reasons.append(f"P/E {per:.1f} 성장주 수준")
            elif per >= 40:
                score += 0
                reasons.append(f"P/E {per:.1f} 고평가")

            if 0 < pbr < 3:
                score += 12
            elif 3 <= pbr < 10:
                score += 6
            elif pbr >= 10:
                score += 0

        return min(score, 30), reasons

    def _score_momentum(self, change: float, change_rate: float, mkt_change: float) -> Tuple[int, List[str]]:
        """모멘텀 점수 (0-20)"""
        score = 0
        reasons = []

        if change_rate > 5:
            score += 12
            reasons.append(f"강한 상승 {change_rate:+.1f}%")
        elif change_rate > 2:
            score += 8
            reasons.append(f"상승세 {change_rate:+.1f}%")
        elif change_rate > 0:
            score += 5
        elif change_rate > -2:
            score += 3
        elif change_rate > -5:
            score += 1
            reasons.append(f"하락 {change_rate:.1f}%")
        else:
            score += 0
            reasons.append(f"급락 {change_rate:.1f}%")

        # 시장 대비 상대강도
        relative = change_rate - mkt_change
        if relative > 3:
            score += 8
            reasons.append("시장 대비 강세")
        elif relative > 0:
            score += 4
        elif relative < -3:
            score += 0
            reasons.append("시장 대비 약세")
        else:
            score += 2

        return min(score, 20), reasons

    def _score_fundamentals_kr(self, fund: Dict) -> Tuple[int, List[str]]:
        """한국 펀더멘탈 품질 (0-25)"""
        score = 0
        reasons = []
        eps = fund.get("eps", 0) or 0
        bps = fund.get("bps", 0) or 0
        div = fund.get("div_yield", 0) or 0

        if eps > 0:
            score += 10
            reasons.append(f"EPS {eps:,.0f} 흑자")
        else:
            reasons.append("적자 기업 주의")

        if bps > 0:
            score += 5

        if div > 3:
            score += 10
            reasons.append(f"고배당 {div:.1f}%")
        elif div > 1:
            score += 5
            reasons.append(f"배당 {div:.1f}%")

        return min(score, 25), reasons

    def _score_fundamentals_us(self, fund: Dict, price: Dict) -> Tuple[int, List[str]]:
        """미국 펀더멘탈 품질 (0-25)"""
        score = 0
        reasons = []

        roe = (fund.get("roe", 0) or 0)
        if isinstance(roe, float) and roe < 1:
            roe *= 100
        div = (fund.get("dividend_yield", 0) or 0)
        if isinstance(div, float) and div < 1:
            div *= 100
        margin = (fund.get("profit_margin", 0) or 0)
        if isinstance(margin, float) and margin < 1:
            margin *= 100

        if roe > 20:
            score += 10
            reasons.append(f"ROE {roe:.1f}% 우수")
        elif roe > 10:
            score += 6
            reasons.append(f"ROE {roe:.1f}% 양호")
        elif roe > 0:
            score += 3

        if div > 2:
            score += 8
            reasons.append(f"배당 {div:.1f}%")
        elif div > 0.5:
            score += 4

        # 52주 저점 대비 위치
        current = price.get("current_price", 0)
        high52 = price.get("fifty_two_week_high", 0)
        low52 = price.get("fifty_two_week_low", 0)
        if current and high52 and low52 and high52 != low52:
            position = (current - low52) / (high52 - low52) * 100
            if position < 30:
                score += 7
                reasons.append("52주 저점 근처 (매수 기회)")
            elif position < 60:
                score += 4
            elif position > 90:
                score += 0
                reasons.append("52주 고점 근처 (신중)")
            else:
                score += 2

        return min(score, 25), reasons

    def _score_news(self, sentiment: Dict) -> Tuple[int, List[str]]:
        """뉴스 감성 점수 (0-15)"""
        score_val = sentiment.get("score", 0)
        reasons = []

        if score_val > 0.5:
            reasons.append(f"뉴스 매우 긍정적 (감성 {score_val:.1f})")
            return 15, reasons
        elif score_val > 0.2:
            reasons.append("뉴스 긍정적")
            return 10, reasons
        elif score_val > -0.2:
            reasons.append("뉴스 중립")
            return 7, reasons
        elif score_val > -0.5:
            reasons.append("뉴스 부정적")
            return 3, reasons
        else:
            reasons.append("뉴스 매우 부정적")
            return 0, reasons

    def _score_theme(self, stock: Dict) -> Tuple[int, List[str]]:
        """테마 모멘텀 점수 (0-10)"""
        # 기본 5점 (테마 정보 없으면 중립)
        return 5, []

    def _score_sector(self, stock: Dict) -> Tuple[int, List[str]]:
        """섹터 보너스 (0-10)"""
        sector = stock.get("sector", "").lower()
        reasons = []

        # 성장 섹터 가산
        growth_sectors = ["technology", "healthcare", "communication"]
        value_sectors = ["financial", "energy", "utilities"]

        if any(s in sector for s in growth_sectors):
            reasons.append(f"성장 섹터: {stock.get('sector', '')}")
            return 7, reasons
        elif any(s in sector for s in value_sectors):
            reasons.append(f"가치 섹터: {stock.get('sector', '')}")
            return 5, reasons

        return 5, reasons

    # ── 뉴스 감성 분석 ──

    def _analyze_news_sentiment(self, news_list: List[Dict], country: str) -> Dict:
        """뉴스 감성 분석 (키워드 기반)"""
        pos = KR_POSITIVE if country == "KR" else EN_POSITIVE
        neg = KR_NEGATIVE if country == "KR" else EN_NEGATIVE

        pos_count = 0
        neg_count = 0
        key_headlines = []

        for n in news_list:
            title = n.get("title", "")
            for kw in pos:
                if kw in title.lower():
                    pos_count += 1
            for kw in neg:
                if kw in title.lower():
                    neg_count += 1
            if title:
                key_headlines.append(title[:60])

        total = pos_count + neg_count
        if total > 0:
            score = (pos_count - neg_count) / total
        else:
            score = 0

        return {
            "score": round(score, 2),
            "positive_count": pos_count,
            "negative_count": neg_count,
            "key_headlines": key_headlines[:3],
        }

    # ── 추천 등급 ──

    def _get_action(self, score: int) -> Tuple[str, str]:
        """점수 → 추천 액션 + 등급"""
        if score >= 80:
            return "적극 매수", "A"
        elif score >= 65:
            return "매수", "B"
        elif score >= 50:
            return "보유", "C"
        elif score >= 35:
            return "매도 고려", "D"
        else:
            return "매도", "F"

    # ── 리스크/촉매 ──

    def _get_risk_factors_kr(self, fund: Dict, price: Dict) -> List[str]:
        risks = []
        per = fund.get("per", 0) or 0
        pbr = fund.get("pbr", 0) or 0
        eps = fund.get("eps", 0) or 0
        if per > 30:
            risks.append(f"높은 PER ({per:.1f}배)")
        if pbr > 5:
            risks.append(f"높은 PBR ({pbr:.2f}배)")
        if eps <= 0:
            risks.append("적자 기업")
        if price.get("change", 0) < 0:
            risks.append("당일 하락세")
        return risks if risks else ["특이 리스크 없음"]

    def _get_catalysts_kr(self, fund: Dict, price: Dict, sentiment: Dict) -> List[str]:
        catalysts = []
        per = fund.get("per", 0) or 0
        pbr = fund.get("pbr", 0) or 0
        if 0 < per < 12:
            catalysts.append("저평가 매력")
        if 0 < pbr < 1:
            catalysts.append("자산가치 대비 저평가")
        if sentiment.get("score", 0) > 0.3:
            catalysts.append("긍정적 뉴스 흐름")
        if price.get("change", 0) > 0:
            catalysts.append("상승 모멘텀")
        return catalysts if catalysts else ["해당 없음"]

    def _get_risk_factors_us(self, fund: Dict, price: Dict) -> List[str]:
        risks = []
        pe = fund.get("pe_ratio", 0) or 0
        if pe > 40:
            risks.append(f"높은 P/E ({pe:.1f}배)")
        roe = (fund.get("roe", 0) or 0)
        if roe < 0:
            risks.append("음수 ROE")
        change = price.get("change_rate", 0)
        if change < -3:
            risks.append(f"당일 급락 ({change:.1f}%)")
        h52 = price.get("fifty_two_week_high", 0)
        cur = price.get("current_price", 0)
        if h52 and cur and cur > h52 * 0.95:
            risks.append("52주 고점 근접")
        return risks if risks else ["특이 리스크 없음"]

    def _get_catalysts_us(self, fund: Dict, price: Dict, sentiment: Dict) -> List[str]:
        catalysts = []
        pe = fund.get("pe_ratio", 0) or 0
        div = (fund.get("dividend_yield", 0) or 0)
        if isinstance(div, float) and div < 1:
            div *= 100
        if 0 < pe < 20:
            catalysts.append("밸류에이션 매력")
        if div > 2:
            catalysts.append(f"배당 매력 ({div:.1f}%)")
        if sentiment.get("score", 0) > 0.3:
            catalysts.append("긍정적 뉴스 흐름")
        l52 = price.get("fifty_two_week_low", 0)
        cur = price.get("current_price", 0)
        if l52 and cur and cur < l52 * 1.2:
            catalysts.append("52주 저점 근처 매수 기회")
        return catalysts if catalysts else ["해당 없음"]

    # ── 섹터/테마 분석 ──

    def _analyze_sectors(self, themes: Dict) -> List[Dict]:
        """테마/섹터 분석"""
        results = []
        for kw, info in themes.get("keyword_themes", {}).items():
            rate_str = info.get("change_rate", "0")
            try:
                nums = re.findall(r'-?\d+\.?\d*', str(rate_str))
                rate = float(nums[0]) if nums else 0
            except:
                rate = 0

            if rate > 2:
                outlook = "긍정적"
            elif rate > 0:
                outlook = "중립(소폭 상승)"
            elif rate > -2:
                outlook = "중립(소폭 하락)"
            else:
                outlook = "부정적"

            results.append({
                "sector": kw,
                "theme_name": info.get("theme_name", kw),
                "change_rate": rate_str,
                "outlook": outlook,
                "stock_count": info.get("stock_count", 0),
                "top_stocks": info.get("top_stocks", []),
                "reasoning": f"{kw} 테마 등락률 {rate_str}, {info.get('stock_count', 0)}개 종목 포함",
            })

        return results

    def _assess_risk(self, data: Dict) -> Dict:
        """전체 리스크 평가"""
        indices = data.get("market_indices", {})
        usa = indices.get("usa", {})

        vix = 0
        for name, info in usa.items():
            if "VIX" in name.upper():
                vix = info.get("price", 0)

        if vix > 30:
            overall = "높음"
        elif vix > 20:
            overall = "보통"
        else:
            overall = "낮음"

        risks = []
        opportunities = []

        if vix > 20:
            risks.append(f"VIX {vix:.1f} - 시장 변동성 확대")
        else:
            opportunities.append(f"VIX {vix:.1f} - 안정적 시장")

        # 뉴스 기반 리스크
        for news in data.get("market_news", [])[:5]:
            title = news.get("title", "")
            for kw in ["우려", "위기", "하락", "급락", "전쟁", "관세"]:
                if kw in title:
                    risks.append(f"시장 뉴스: {title[:40]}")
                    break
            for kw in ["상승", "돌파", "신고가", "호재"]:
                if kw in title:
                    opportunities.append(f"시장 뉴스: {title[:40]}")
                    break

        return {
            "overall_risk": overall,
            "vix": vix,
            "key_risks": risks[:5] if risks else ["특이 리스크 없음"],
            "opportunities": opportunities[:5] if opportunities else ["특이 기회 없음"],
        }

    def _build_market_context(self, indices: Dict) -> Dict:
        """시장 컨텍스트 구성"""
        korea = indices.get("korea", {})
        usa = indices.get("usa", {})

        # 한국 지수
        kospi_data = korea.get("kospi", {})
        kospi_val = kospi_data.get("value", 0) if isinstance(kospi_data, dict) else 0
        kospi_change_str = str(kospi_data.get("change", "0")) if isinstance(kospi_data, dict) else "0"
        try:
            nums = re.findall(r'-?\d+\.?\d*', kospi_change_str)
            korea_change = float(nums[0]) if nums else 0
        except:
            korea_change = 0

        # 미국 지수
        sp500 = {}
        for name, info in usa.items():
            if "S&P" in name or "SP500" in name.upper():
                sp500 = info
                break
        usa_change = sp500.get("change_percent", 0)

        # 트렌드 판단
        if korea_change > 1:
            trend = "상승"
            sentiment = 0.6
        elif korea_change > 0:
            trend = "소폭 상승"
            sentiment = 0.3
        elif korea_change > -1:
            trend = "소폭 하락"
            sentiment = -0.2
        else:
            trend = "하락"
            sentiment = -0.5

        summary_parts = []
        if kospi_val:
            summary_parts.append(f"KOSPI {kospi_val}")
        summary_parts.append(f"한국 시장 {trend}")
        if sp500:
            summary_parts.append(f"S&P500 {sp500.get('price', 'N/A')} ({usa_change:+.2f}%)")

        return {
            "summary": ", ".join(summary_parts),
            "trend": trend,
            "sentiment": sentiment,
            "korea_change": korea_change,
            "usa_change": usa_change,
            "korea_indices": korea,
            "usa_indices": usa,
        }
