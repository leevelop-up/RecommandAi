"""
미래 예측 분석 엔진
기술적 분석, 트렌드 예측, 산업 전망을 종합하여 미래 가치 예측
"""
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import math


class FuturePredictor:
    """미래 예측 분석기"""

    def predict_stock(self, stock: Dict, historical_data: Optional[Dict] = None) -> Dict:
        """
        종목 미래 예측 분석
        
        Returns:
            {
                "prediction_score": 0-100,
                "expected_return_3m": 예상 3개월 수익률,
                "expected_return_6m": 예상 6개월 수익률,
                "confidence": 신뢰도,
                "technical_signals": [],
                "growth_indicators": [],
                "risk_level": "low/medium/high",
                "buy_timing": "now/wait/avoid"
            }
        """
        price = stock.get("price", {})
        fund = stock.get("fundamental", {})
        
        prediction_score = 0
        signals = []
        growth_indicators = []
        
        # 1. 기술적 분석 (30점)
        tech_score, tech_signals = self._analyze_technical(price, historical_data)
        prediction_score += tech_score
        signals.extend(tech_signals)
        
        # 2. 성장성 분석 (25점)
        growth_score, growth_items = self._analyze_growth_potential(fund, price)
        prediction_score += growth_score
        growth_indicators.extend(growth_items)
        
        # 3. 트렌드 분석 (20점)
        trend_score, trend_signals = self._analyze_trend(price)
        prediction_score += trend_score
        signals.extend(trend_signals)
        
        # 4. 가치 평가 (15점)
        value_score, value_signals = self._analyze_future_value(fund, price)
        prediction_score += value_score
        signals.extend(value_signals)
        
        # 5. 산업 전망 (10점)
        sector_score, sector_signals = self._analyze_sector_outlook(stock)
        prediction_score += sector_score
        signals.extend(sector_signals)
        
        # 예상 수익률 계산
        expected_3m = self._calculate_expected_return(prediction_score, 3)
        expected_6m = self._calculate_expected_return(prediction_score, 6)
        
        # 신뢰도 계산
        confidence = self._calculate_confidence(stock, historical_data)
        
        # 리스크 레벨
        risk_level = self._assess_risk_level(prediction_score, fund, price)
        
        # 매수 타이밍
        buy_timing = self._suggest_buy_timing(prediction_score, price, trend_score)
        
        return {
            "prediction_score": round(prediction_score, 1),
            "expected_return_3m": round(expected_3m, 2),
            "expected_return_6m": round(expected_6m, 2),
            "confidence": round(confidence, 1),
            "technical_signals": signals,
            "growth_indicators": growth_indicators,
            "risk_level": risk_level,
            "buy_timing": buy_timing,
        }

    def _analyze_technical(self, price: Dict, historical: Optional[Dict]) -> Tuple[float, List[str]]:
        """기술적 분석 (30점)"""
        score = 0
        signals = []
        
        current = price.get("current_price", 0)
        if not current:
            return 0, ["데이터 부족"]
        
        # 1. 52주 고저점 대비 위치 (10점)
        high_52 = price.get("fifty_two_week_high", 0)
        low_52 = price.get("fifty_two_week_low", 0)
        
        if high_52 and low_52:
            position = (current - low_52) / (high_52 - low_52) * 100
            if position < 30:
                score += 10
                signals.append(f"🟢 52주 저점 근처 ({position:.1f}%) - 반등 가능성")
            elif position < 50:
                score += 7
                signals.append(f"🟡 52주 중간 하단 ({position:.1f}%) - 상승 여력")
            elif position > 80:
                score += 3
                signals.append(f"🔴 52주 고점 근처 ({position:.1f}%) - 조정 가능")
            else:
                score += 5
                signals.append(f"🟡 52주 중간 ({position:.1f}%)")
        
        # 2. 거래량 분석 (10점)
        volume = price.get("volume", 0)
        avg_volume = price.get("avg_volume", 0) or volume
        
        if volume and avg_volume:
            volume_ratio = volume / avg_volume
            if volume_ratio > 2.0:
                score += 10
                signals.append(f"🔥 거래량 급증 ({volume_ratio:.1f}배) - 강한 관심")
            elif volume_ratio > 1.5:
                score += 7
                signals.append(f"📈 거래량 증가 ({volume_ratio:.1f}배)")
            elif volume_ratio < 0.5:
                score += 2
                signals.append(f"😴 거래량 저조 ({volume_ratio:.1f}배)")
            else:
                score += 5
                signals.append(f"📊 거래량 평균 수준")
        
        # 3. 변동성 분석 (10점)
        change_rate = abs(price.get("change_rate", 0))
        if change_rate > 5:
            score += 3
            signals.append("⚡ 변동성 높음 - 리스크 주의")
        elif change_rate > 3:
            score += 7
            signals.append("📊 적정 변동성")
        else:
            score += 5
            signals.append("😌 변동성 낮음")
        
        return score, signals

    def _analyze_growth_potential(self, fund: Dict, price: Dict) -> Tuple[float, List[str]]:
        """성장성 분석 (25점)"""
        score = 0
        indicators = []
        
        # 1. 수익성 성장 (10점)
        eps = fund.get("eps", 0)
        roe = fund.get("roe", 0)
        
        if roe and roe > 0.20:
            score += 10
            indicators.append(f"⭐ ROE {roe*100:.1f}% - 초고수익")
        elif roe and roe > 0.15:
            score += 7
            indicators.append(f"✅ ROE {roe*100:.1f}% - 고수익")
        elif roe and roe > 0.10:
            score += 5
            indicators.append(f"📊 ROE {roe*100:.1f}% - 양호")
        
        # 2. 부채 건전성 (8점)
        debt_ratio = fund.get("debt_ratio", 0)
        if debt_ratio:
            if debt_ratio < 50:
                score += 8
                indicators.append(f"💪 부채비율 {debt_ratio:.0f}% - 매우 건전")
            elif debt_ratio < 100:
                score += 5
                indicators.append(f"✅ 부채비율 {debt_ratio:.0f}% - 건전")
            elif debt_ratio < 200:
                score += 2
                indicators.append(f"⚠️ 부채비율 {debt_ratio:.0f}% - 주의")
            else:
                score += 0
                indicators.append(f"❌ 부채비율 {debt_ratio:.0f}% - 위험")
        
        # 3. 현금 창출력 (7점)
        operating_margin = fund.get("operating_margin", 0)
        if operating_margin and operating_margin > 0.20:
            score += 7
            indicators.append(f"💰 영업이익률 {operating_margin*100:.1f}% - 우수")
        elif operating_margin and operating_margin > 0.10:
            score += 5
            indicators.append(f"📈 영업이익률 {operating_margin*100:.1f}% - 양호")
        elif operating_margin and operating_margin > 0:
            score += 3
            indicators.append(f"📊 영업이익률 {operating_margin*100:.1f}%")
        
        return score, indicators

    def _analyze_trend(self, price: Dict) -> Tuple[float, List[str]]:
        """트렌드 분석 (20점)"""
        score = 0
        signals = []
        
        change_rate = price.get("change_rate", 0)
        
        # 1. 단기 추세 (10점)
        if change_rate > 5:
            score += 10
            signals.append("🚀 강한 상승 추세")
        elif change_rate > 2:
            score += 8
            signals.append("📈 상승 추세")
        elif change_rate > 0:
            score += 6
            signals.append("🟢 완만한 상승")
        elif change_rate > -2:
            score += 4
            signals.append("🟡 보합")
        elif change_rate > -5:
            score += 2
            signals.append("📉 약한 하락")
        else:
            score += 0
            signals.append("🔴 강한 하락")
        
        # 2. 모멘텀 지속성 (10점)
        # 간단한 모멘텀 판단
        if change_rate > 0:
            score += 7
            signals.append("✅ 긍정적 모멘텀")
        elif change_rate < -3:
            score += 2
            signals.append("⚠️ 부정적 모멘텀")
        else:
            score += 5
            signals.append("🟡 중립적 모멘텀")
        
        return score, signals

    def _analyze_future_value(self, fund: Dict, price: Dict) -> Tuple[float, List[str]]:
        """미래 가치 평가 (15점)"""
        score = 0
        signals = []
        
        per = fund.get("per", 0) or fund.get("pe_ratio", 0)
        pbr = fund.get("pbr", 0) or fund.get("pb_ratio", 0)
        
        # 1. 저평가 기회 (10점)
        if per and 0 < per < 10:
            score += 10
            signals.append(f"💎 PER {per:.1f} - 심각한 저평가 (매수 기회)")
        elif per and per < 15:
            score += 7
            signals.append(f"✅ PER {per:.1f} - 저평가")
        elif per and per < 20:
            score += 5
            signals.append(f"📊 PER {per:.1f} - 적정")
        
        # 2. 자산가치 (5점)
        if pbr and pbr < 0.8:
            score += 5
            signals.append(f"💎 PBR {pbr:.2f} - 청산가치 이하")
        elif pbr and pbr < 1.5:
            score += 3
            signals.append(f"✅ PBR {pbr:.2f} - 합리적")
        
        return score, signals

    def _analyze_sector_outlook(self, stock: Dict) -> Tuple[float, List[str]]:
        """산업 전망 분석 (10점)"""
        score = 5  # 기본 점수
        signals = []
        
        # 핫 섹터 키워드
        hot_sectors = {
            "AI": 10, "반도체": 9, "2차전지": 9, "바이오": 8,
            "헬스케어": 7, "로봇": 8, "우주항공": 7, "친환경": 8,
            "전기차": 9, "자율주행": 8, "메타버스": 6, "5G": 7
        }
        
        name = stock.get("name", "")
        sector = stock.get("sector", "")
        themes = stock.get("themes", [])
        
        # 테마/섹터 매칭
        for keyword, bonus in hot_sectors.items():
            if keyword in name or keyword in sector or keyword in str(themes):
                score = bonus
                signals.append(f"🔥 {keyword} 섹터 - 성장 산업")
                break
        else:
            signals.append("📊 일반 산업")
        
        return score, signals

    def _calculate_expected_return(self, score: float, months: int) -> float:
        """예상 수익률 계산"""
        # 점수를 기반으로 예상 수익률 계산
        # 점수 70 이상 -> 월 3-5% 수익 예상
        # 점수 50-70 -> 월 1-3% 수익 예상
        # 점수 30-50 -> 월 0-1% 수익 예상
        
        if score >= 80:
            monthly_return = 0.05  # 5%
        elif score >= 70:
            monthly_return = 0.04  # 4%
        elif score >= 60:
            monthly_return = 0.03  # 3%
        elif score >= 50:
            monthly_return = 0.02  # 2%
        elif score >= 40:
            monthly_return = 0.01  # 1%
        else:
            monthly_return = 0.0  # 0%
        
        # 복리 계산
        total_return = (pow(1 + monthly_return, months) - 1) * 100
        return total_return

    def _calculate_confidence(self, stock: Dict, historical: Optional[Dict]) -> float:
        """신뢰도 계산 (0-100)"""
        confidence = 50  # 기본 신뢰도
        
        # 데이터 완전성
        fund = stock.get("fundamental", {})
        price = stock.get("price", {})
        
        if fund.get("per") or fund.get("pe_ratio"):
            confidence += 10
        if fund.get("pbr") or fund.get("pb_ratio"):
            confidence += 10
        if fund.get("roe"):
            confidence += 10
        if price.get("fifty_two_week_high") and price.get("fifty_two_week_low"):
            confidence += 10
        if stock.get("news"):
            confidence += 10
        
        return min(100, confidence)

    def _assess_risk_level(self, score: float, fund: Dict, price: Dict) -> str:
        """리스크 레벨 평가"""
        risk_points = 0
        
        # 변동성
        change_rate = abs(price.get("change_rate", 0))
        if change_rate > 5:
            risk_points += 2
        
        # 부채
        debt_ratio = fund.get("debt_ratio", 0)
        if debt_ratio > 200:
            risk_points += 2
        elif debt_ratio > 100:
            risk_points += 1
        
        # 밸류에이션
        per = fund.get("per", 0) or fund.get("pe_ratio", 0)
        if per > 50:
            risk_points += 1
        
        # 점수
        if score < 40:
            risk_points += 2
        
        if risk_points >= 4:
            return "high"
        elif risk_points >= 2:
            return "medium"
        else:
            return "low"

    def _suggest_buy_timing(self, score: float, price: Dict, trend_score: float) -> str:
        """매수 타이밍 제안"""
        current = price.get("current_price", 0)
        low_52 = price.get("fifty_two_week_low", 0)
        high_52 = price.get("fifty_two_week_high", 0)
        
        if score >= 70:
            if low_52 and current and current < low_52 * 1.2:
                return "🟢 지금 매수 (저점 + 고점수)"
            elif trend_score >= 15:
                return "🟢 지금 매수 (상승 추세)"
            else:
                return "🟡 매수 고려 (조정 기다림)"
        elif score >= 50:
            return "🟡 관망 후 매수 (더 확인 필요)"
        else:
            return "🔴 매수 보류 (리스크 높음)"


def print_prediction_report(stock: Dict, prediction: Dict):
    """예측 리포트 출력"""
    print("\n" + "="*70)
    print(f"  🔮 미래 예측 분석: {stock.get('name', '')} ({stock.get('ticker', '')})")
    print("="*70)
    
    print(f"\n📊 예측 점수: {prediction['prediction_score']:.1f}/100")
    print(f"🎯 신뢰도: {prediction['confidence']:.1f}%")
    print(f"⚠️  리스크: {prediction['risk_level'].upper()}")
    print(f"💡 매수 타이밍: {prediction['buy_timing']}")
    
    print(f"\n💰 예상 수익률:")
    print(f"   3개월: {prediction['expected_return_3m']:+.1f}%")
    print(f"   6개월: {prediction['expected_return_6m']:+.1f}%")
    
    print(f"\n🔍 기술적 시그널:")
    for signal in prediction['technical_signals']:
        print(f"   • {signal}")
    
    print(f"\n📈 성장 지표:")
    for indicator in prediction['growth_indicators']:
        print(f"   • {indicator}")
