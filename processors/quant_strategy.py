"""
한국 주식 퀀트 전략 — 예측 · 기대수익 · BUY/HOLD/SELL · 자기진화

핵심 로직
  1. P(up) 예측 (ML 모델)
  2. Expected Return = P(up)·AvgGain − (1−P(up))·AvgLoss
  3. 규칙 기반 의사결정 (BUY / HOLD / SELL)
  4. 거래 기록 저장
  5. 자기진화
       - 정확도 기반 피처 가중치 조정
       - 가중치 < 0.3인 피처 비활성화
       - 조합 피처 활성화 시도
       - MDD 초과 시 보수적 모드로 자동 전환
"""

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
from loguru import logger

from processors.quant_data import QuantDataPipeline
from processors.quant_model import QuantModelTrainer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUANT_DIR = os.path.join(BASE_DIR, "output", "quant")
EVOLUTION_PATH = os.path.join(QUANT_DIR, "evolution_state.json")
HISTORY_PATH = os.path.join(QUANT_DIR, "trade_history.json")


# ── JSON 헬퍼 ────────────────────────────────────────────────
def _load_json(path: str, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def _save_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class QuantStrategy:
    """AI 기반 자기진화형 한국 주식 퀀트 전략 엔진"""

    # ── 의사결정 임계값 ──────────────────────────────────────
    _DEFAULT_TH = {
        "buy_p_up": 0.60,       # BUY: P(up) ≥ 0.60
        "buy_rsi_max": 70,      # BUY: RSI < 70
        "buy_sent_min": 0.0,    # BUY: sentiment ≥ 0
        "hold_p_up_min": 0.45,  # HOLD 하한
        "sell_p_up": 0.45,      # SELL: P(up) < 0.45
    }
    _CONSERVATIVE_TH = {        # MDD 초과 시 보수적 모드
        "buy_p_up": 0.65,
        "buy_rsi_max": 65,
        "buy_sent_min": 0.0,
        "hold_p_up_min": 0.50,
        "sell_p_up": 0.50,
    }

    MDD_LIMIT = 0.15           # 15% MDD → 보수적 전환
    AVG_WINDOW = 60            # 기대수익 계산 기간 (최근 거래일 수)

    def __init__(self):
        self.pipeline = QuantDataPipeline()
        self.model = QuantModelTrainer()
        self.evolution = _load_json(EVOLUTION_PATH, self._init_evolution())
        self._conservative = (
            self.evolution
            .get("mdd_tracker", {})
            .get("conservative_mode", False)
        )

    # ── 진화 상태 초기화 ─────────────────────────────────────
    @staticmethod
    def _init_evolution() -> dict:
        return {
            "generation": 0,
            "feature_weights": {f: 1.0 for f in QuantDataPipeline.ALL_FEATURES},
            "active_features": list(QuantDataPipeline.BASE_FEATURES),  # 조합 피처는 초기 비활성
            "mdd_tracker": {
                "peak": 1.0, "current": 1.0,
                "max_drawdown": 0.0, "conservative_mode": False,
            },
            "performance_history": [],
            "last_updated": datetime.now().isoformat(),
        }

    def _thresholds(self) -> dict:
        return self._CONSERVATIVE_TH if self._conservative else self._DEFAULT_TH

    # ── 메인 분석 파이프라인 ─────────────────────────────────
    def analyze(self, ticker: str, ticker_name: str = "", years: int = 3) -> dict:
        """단일 종목 전체 퀀트 분석

        Returns:
            analysis dict → format_output()로 출력 가능
            실패 시 {"error": str}
        """
        logger.info(f"\n{'=' * 60}\n  퀀트 분석: {ticker} ({ticker_name})\n{'=' * 60}")

        # 1. 데이터 파이프라인
        pipe = self.pipeline.full_pipeline(ticker, ticker_name, years)
        if "error" in pipe:
            return {"error": pipe["error"]}

        df = pipe["df"]
        fund = pipe["fundamentals"]
        sent = pipe["sentiment"]
        market = pipe["market"]

        # 활성 피처만 사용 (진화로 제거된 피처 제외)
        active_feat = [
            f for f in self.evolution.get("active_features", QuantDataPipeline.BASE_FEATURES)
            if f in df.columns
        ]
        if len(active_feat) < 3:  # 안전장치: 최소 3개 유지
            active_feat = [f for f in QuantDataPipeline.BASE_FEATURES if f in df.columns]

        # 2. 모델 학습
        logger.info("[모델] Train/Val/Test 분리 및 학습")
        try:
            (X_tr, y_tr), (X_va, y_va), (X_te, y_te) = \
                QuantModelTrainer.time_series_split(df, active_feat)
            train_res = self.model.train_and_select(X_tr, y_tr, X_va, y_va, X_te, y_te)
            if "error" in train_res:
                return {"error": f"모델: {train_res['error']}"}
        except Exception as e:
            return {"error": f"모델 학습 오류: {e}"}

        # 3. P(up) 예측 — 최근 행(오늘)의 피처 사용
        latest_feat = df[active_feat].iloc[-1].values
        p_up = self.model.predict_p_up(latest_feat)
        logger.info(f"[예측] P(up) = {p_up:.4f}")

        # 4. 기대수익 계산
        avg_gain, avg_loss, exp_ret = self._expected_return(df, p_up)
        logger.info(f"[기대수익] E[R]={exp_ret * 100:.4f}% "
                    f"(gain={avg_gain * 100:.3f}% loss={avg_loss * 100:.3f}%)")

        # 5. 의사결정
        rsi = float(df["RSI14"].iloc[-1])
        decision = self._decide(p_up, exp_ret, rsi, sent)
        logger.info(f"[결정] {decision}")

        return {
            "ticker": ticker,
            "ticker_name": ticker_name,
            "market": market,
            "data_period": (
                f"{df['Date'].iloc[0].strftime('%Y-%m-%d')} ~ "
                f"{df['Date'].iloc[-1].strftime('%Y-%m-%d')}"
            ),
            "selected_model": train_res["best_model_name"],
            "model_metrics": train_res["metrics"],
            "p_up": round(p_up, 4),
            "expected_return": round(exp_ret, 6),
            "avg_gain": round(avg_gain, 4),
            "avg_loss": round(avg_loss, 4),
            "rsi": round(rsi, 2),
            "ma20_ratio": round(float(df["MA20_ratio"].iloc[-1]), 4),
            "ma60_ratio": round(float(df["MA60_ratio"].iloc[-1]), 4),
            "fundamentals": fund,
            "sentiment": sent,
            "decision": decision,
            "conservative_mode": self._conservative,
            "evolution_gen": self.evolution.get("generation", 0),
        }

    # ── 기대수익 계산 ────────────────────────────────────────
    def _expected_return(self, df: pd.DataFrame, p_up: float) -> tuple:
        """Expected Return = P(up)·AvgGain − (1−P(up))·AvgLoss

        AvgGain / AvgLoss: 최근 AVG_WINDOW 거래일의 1일 수익률 기준
        """
        recent = df.tail(self.AVG_WINDOW).copy()
        ret = recent["Close"].pct_change().dropna()
        up = ret[ret > 0]
        down = ret[ret <= 0]

        avg_gain = float(up.mean()) if len(up) else 0.001
        avg_loss = float(abs(down.mean())) if len(down) else 0.001
        exp_ret = p_up * avg_gain - (1 - p_up) * avg_loss

        return avg_gain, avg_loss, exp_ret

    # ── 의사결정 규칙 ────────────────────────────────────────
    def _decide(self, p_up: float, exp_ret: float, rsi: float, sent: dict) -> str:
        """BUY / HOLD / SELL 결정

        SELL 리스크 조건을 먼저 확인 (negative_surge는 즉시 SELL)
        BUY는 4개 조건 모두 충족 시
        그 외는 HOLD
        """
        th = self._thresholds()

        # SELL — 리스크 우선
        if p_up < th["sell_p_up"] or sent.get("negative_surge", 0):
            return "SELL"

        # BUY — 4개 조건 모두 충족
        if (
            p_up >= th["buy_p_up"]
            and exp_ret > 0
            and rsi < th["buy_rsi_max"]
            and sent.get("sentiment_score", 0.0) >= th["buy_sent_min"]
        ):
            return "BUY"

        return "HOLD"

    # ── 거래 기록 ────────────────────────────────────────────
    def record_trade(self, analysis: dict, actual_return: float = None):
        """분석 결과를 거래 기록 파일에 추가

        actual_return: 다음 거래일 실제 수익률 (후일 업데이트 가능)
        """
        history = _load_json(HISTORY_PATH, [])
        history.append({
            "timestamp": datetime.now().isoformat(),
            "ticker": analysis.get("ticker"),
            "decision": analysis.get("decision"),
            "p_up": analysis.get("p_up"),
            "expected_return": analysis.get("expected_return"),
            "actual_return": actual_return,
        })
        _save_json(HISTORY_PATH, history)

    # ── 자기진화 ─────────────────────────────────────────────
    def self_improve(self):
        """거래 기록 분석 → 피처 가중치 조정 → MDD 모니터링

        A. MDD 계산 → 15% 초과 시 보수적 모드 전환
        B. 정확도 기반 피처 가중치 스케일링
           - 정확도 > 60% → ×1.1 (강화)
           - 정확도 < 40% → ×0.9 (약화)
        C. 가중치 < 0.3인 피처 비활성화 (최소 3개 유지)
        D. 정확도 > 55%이면 조합 피처 (MA20_sent_combo) 활성화 시도
        """
        history = _load_json(HISTORY_PATH, [])
        completed = [t for t in history if t.get("actual_return") is not None]
        if len(completed) < 5:
            logger.info("[진화] 완료 거래 < 5건 — 스킵")
            return

        # A. MDD 계산
        cum, peak, mdd = 1.0, 1.0, 0.0
        for t in completed:
            cum *= (1 + t["actual_return"])
            peak = max(peak, cum)
            mdd = max(mdd, (peak - cum) / peak)

        self._conservative = mdd >= self.MDD_LIMIT
        self.evolution["mdd_tracker"] = {
            "peak": round(peak, 6),
            "current": round(cum, 6),
            "max_drawdown": round(mdd, 4),
            "conservative_mode": self._conservative,
        }
        logger.info(f"[진화] MDD={mdd:.2%} {'→ 보수적 모드' if self._conservative else '— 정상'}")

        # B. 정확도 계산 및 피처 가중치 조정
        correct = sum(
            1 for t in completed
            if (t["decision"] == "BUY" and t["actual_return"] > 0)
            or (t["decision"] == "SELL" and t["actual_return"] < 0)
        )
        accuracy = correct / len(completed)
        logger.info(f"[진화] 정확도={accuracy:.2%} ({correct}/{len(completed)})")

        scale = 1.1 if accuracy > 0.6 else (0.9 if accuracy < 0.4 else 1.0)
        fw = self.evolution.get("feature_weights", {})
        for k in fw:
            fw[k] = round(fw[k] * scale, 3)

        # C. 비활성화 (가중치 < 0.3), 최소 3개 유지
        active = [f for f, w in fw.items() if w >= 0.3]
        if len(active) < 3:
            active = [f for f, _ in sorted(fw.items(), key=lambda x: x[1], reverse=True)[:3]]

        # D. 조합 피처 활성화 시도
        if accuracy > 0.55 and "MA20_sent_combo" not in active:
            active.append("MA20_sent_combo")
            logger.info("[진화] MA20_sent_combo 피처 활성화")

        # 저장
        self.evolution["feature_weights"] = fw
        self.evolution["active_features"] = active
        self.evolution["generation"] = self.evolution.get("generation", 0) + 1
        self.evolution.setdefault("performance_history", []).append({
            "gen": self.evolution["generation"],
            "accuracy": round(accuracy, 4),
            "mdd": round(mdd, 4),
            "n_trades": len(completed),
            "timestamp": datetime.now().isoformat(),
        })
        self.evolution["last_updated"] = datetime.now().isoformat()
        _save_json(EVOLUTION_PATH, self.evolution)
        logger.info(f"[진화] Gen {self.evolution['generation']} 완료 | 활성 피처: {active}")

    # ── 출력 포맷 ────────────────────────────────────────────
    @staticmethod
    def format_output(a: dict) -> str:
        """요구사항 형식으로 구조화된 출력 생성"""
        if "error" in a:
            return f"\n[오류] {a['error']}\n"

        # 모델 메트릭 행
        met_lines = ""
        for name, m in a.get("model_metrics", {}).items():
            star = " ★" if name == a.get("selected_model") else "  "
            met_lines += (
                f"    {star}{name:>4s}: "
                f"AUC={m.get('roc_auc', 0):.4f} | "
                f"Prec={m.get('precision', 0):.4f} | "
                f"Rec={m.get('recall', 0):.4f}\n"
            )

        # 추세 판단 (이동평균 구조)
        m20 = a.get("ma20_ratio", 1.0)
        m60 = a.get("ma60_ratio", 1.0)
        if m20 > 1.0 and m60 > 1.0:
            trend = "상승추세 (Close > MA20, Close > MA60)"
        elif m20 > 1.0:
            trend = "단기 반등 (Close > MA20, Close < MA60)"
        elif m20 < 1.0 and m60 < 1.0:
            trend = "하락추세 (Close < MA20, Close < MA60)"
        else:
            trend = "조정구간 (Close < MA20, Close > MA60)"

        # RSI 모멘텀
        rsi = a.get("rsi", 50)
        rsi_label = "과買" if rsi > 70 else ("과売" if rsi < 30 else "중립")

        # 재무
        f = a.get("fundamentals", {})
        fund_s = f"ROE={f.get('ROE', 'N/A')}"
        if f.get("PER"):
            fund_s += f" | PER={f['PER']}"
        if f.get("EPS"):
            fund_s += f" | EPS={f['EPS']}"

        # 감성
        s = a.get("sentiment", {})
        s_label = (
            "긍정" if s.get("sentiment_score", 0) > 0
            else ("부정" if s.get("sentiment_score", 0) < 0 else "중립")
        )
        neg_surge = "⚠ 부정 뉴스 급증" if s.get("negative_surge") else "없음"

        cons = " [보수적 모드]" if a.get("conservative_mode") else ""
        SEP = "=" * 64

        return (
            f"\n{SEP}\n"
            f"  한국 주식 퀀트 분석 — BUY / HOLD / SELL 추천{cons}\n"
            f"  진화 세대(Generation) : {a.get('evolution_gen', 0)}\n"
            f"{SEP}\n"
            f"  종목명            : {a.get('ticker_name', 'N/A')} ({a.get('ticker')})\n"
            f"  시장              : {a.get('market', 'KRX')}\n"
            f"  사용 데이터 기간  : {a.get('data_period', 'N/A')}\n"
            f"\n"
            f"  ── 모델 평가 ─────────────────────────────────────────\n"
            f"{met_lines}"
            f"  선택된 모델      : {a.get('selected_model', 'N/A')}\n"
            f"\n"
            f"  ── 예측 & 기대수익 ───────────────────────────────────\n"
            f"  상승 확률  P(up)       : {a.get('p_up', 0):.4f}  ({a.get('p_up', 0) * 100:.1f}%)\n"
            f"  평균 상승율 (AvgGain)  : {a.get('avg_gain', 0) * 100:.3f}%\n"
            f"  평균 하락율 (AvgLoss)  : {a.get('avg_loss', 0) * 100:.3f}%\n"
            f"  기대수익   E[R]        : {a.get('expected_return', 0) * 100:.4f}%\n"
            f"\n"
            f"  ── 핵심 근거 ─────────────────────────────────────────\n"
            f"  · 추세 (이동평균)  : {trend}\n"
            f"                       MA20 비율={m20:.4f} | MA60 비율={m60:.4f}\n"
            f"  · 모멘텀 (RSI)    : {rsi_label} (RSI={rsi})\n"
            f"  · 재무 상태       : {fund_s}\n"
            f"  · 뉴스 감성       : {s_label} "
            f"(score={s.get('sentiment_score', 0):.3f} | "
            f"양성비={s.get('positive_ratio', 0.5):.2f})\n"
            f"                       부정 급증 : {neg_surge}\n"
            f"{SEP}\n"
            f"  최종 추천 : {a.get('decision', 'HOLD')}\n"
            f"{SEP}\n"
        )


# ── 배치 분석 ────────────────────────────────────────────────
def run_quant_batch(tickers: list, years: int = 3) -> list:
    """여러 종목을 순차적으로 분석

    Args:
        tickers: [{"ticker": "005930", "name": "삼성전자"}, ...]
        years:   데이터 수집 기간 (년)
    Returns:
        analysis 결과 리스트
    """
    strategy = QuantStrategy()
    strategy.self_improve()  # 분석 전 진화 실행

    results = []
    for item in tickers:
        t, n = item.get("ticker", ""), item.get("name", "")
        if not t:
            continue
        res = strategy.analyze(t, n, years)
        results.append(res)
        if "error" not in res:
            strategy.record_trade(res)

    _save_batch_output(results)
    return results


def _save_batch_output(results: list):
    """배치 결과 → JSON + TXT 저장"""
    os.makedirs(QUANT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON (DataFrame 제외)
    _save_json(
        os.path.join(QUANT_DIR, f"quant_analysis_{ts}.json"),
        [{k: v for k, v in r.items() if k != "df"} for r in results],
    )

    # TXT 리포트
    txt_path = os.path.join(QUANT_DIR, f"quant_analysis_{ts}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(QuantStrategy.format_output(r))

    logger.info(f"배치 결과 저장: {QUANT_DIR}/quant_analysis_{ts}.*")
