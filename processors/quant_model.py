"""
한국 주식 퀀트 전략 — ML 모델 학습 · 평가 · 자동 선택

모델    : Logistic Regression / Random Forest / XGBoost
분리    : 시계열 기반 Train(60%) / Val(20%) / Test(20%) — 셔플 없음
가중치  : 최근 데이터 지수 감소 가중치 (recency bias)
스케일  : StandardScaler (train fit → val/test transform, leakage 없음)
선택 기준: ROC-AUC (최우선)
"""

import numpy as np
import pandas as pd
from loguru import logger

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, precision_score, recall_score

try:
    from xgboost import XGBClassifier
except ImportError:
    XGBClassifier = None
    logger.warning("xgboost 미설치 — LR / RF만 사용")


class QuantModelTrainer:
    """시계열 기반 모델 학습, 평가, 선택"""

    TRAIN_RATIO = 0.60
    VAL_RATIO = 0.20        # Test = 나머지 20%
    DECAY_LAMBDA = 0.005    # 최근 데이터 가중치 강화 지수
    MIN_TRAIN = 120         # 최소 학습 행 수

    def __init__(self):
        self.best_model = None
        self.best_model_name: str = ""
        self.scaler = StandardScaler()
        self.all_metrics: dict = {}

    # ── 시계열 분리 ──────────────────────────────────────────
    @staticmethod
    def time_series_split(df: pd.DataFrame, feature_cols: list):
        """시간 순서 유지하며 Train / Val / Test 분리

        label이 NaN인 행과 피처에 NaN이 있는 행은 제외 후 분리.
        Returns: (X_train, y_train), (X_val, y_val), (X_test, y_test)
        """
        valid = (
            df.dropna(subset=["label"])
            .dropna(subset=feature_cols)
            .reset_index(drop=True)
        )
        n = len(valid)
        t1 = int(n * QuantModelTrainer.TRAIN_RATIO)
        t2 = int(n * (QuantModelTrainer.TRAIN_RATIO + QuantModelTrainer.VAL_RATIO))

        def _xy(part):
            return part[feature_cols].values, part["label"].values.astype(int)

        return _xy(valid.iloc[:t1]), _xy(valid.iloc[t1:t2]), _xy(valid.iloc[t2:])

    # ── 최근 데이터 가중치 ───────────────────────────────────
    @staticmethod
    def sample_weights(n: int, lam: float = 0.005) -> np.ndarray:
        """지수 감소 가중치 — 최근 행이 더 높은 가중치

        w[i] = exp(λ·i)  (i=0이 가장 오래된 행)
        합이 n이 되도록 정규화하여 sklearn sample_weight와 호환.
        """
        w = np.exp(lam * np.arange(n))
        return w / w.sum() * n

    # ── 모델 후보 정의 ────────────────────────────────────────
    @staticmethod
    def _candidates() -> dict:
        """학습할 모델 후보 딕셔너리"""
        m = {
            "lr": LogisticRegression(
                max_iter=1000, C=1.0, solver="lbfgs", random_state=42
            ),
            "rf": RandomForestClassifier(
                n_estimators=100, max_depth=10, min_samples_leaf=10,
                random_state=42, n_jobs=-1,
            ),
        }
        if XGBClassifier is not None:
            m["xgb"] = XGBClassifier(
                n_estimators=200, max_depth=6, learning_rate=0.05,
                subsample=0.8, colsample_bytree=0.8,
                eval_metric="logloss", random_state=42,
                early_stopping_rounds=20,
            )
        return m

    # ── 학습 + 평가 + 최선 모델 선택 ─────────────────────────
    def train_and_select(self, X_train, y_train, X_val, y_val,
                         X_test=None, y_test=None) -> dict:
        """3개 모델 학습 후 ROC-AUC 기준 최선 모델 선택

        StandardScaler는 train에서만 fit하고 val/test에 transform.
        상수 컬럼(분산=0)이면 NaN이 나오므로 0으로 대체.

        Returns:
            {"best_model_name": str, "metrics": {name: {roc_auc, precision, recall}}}
            실패 시 {"error": str}
        """
        if len(X_train) < self.MIN_TRAIN:
            return {"error": f"학습 데이터 부족 ({len(X_train)} < {self.MIN_TRAIN})"}
        if len(np.unique(y_train)) < 2:
            return {"error": "단일 클래스 라벨"}

        # 스케일링 (train fit → val transform)
        X_train_s = np.nan_to_num(self.scaler.fit_transform(X_train), nan=0.0)
        X_val_s = np.nan_to_num(self.scaler.transform(X_val), nan=0.0)

        sw = self.sample_weights(len(X_train), self.DECAY_LAMBDA)
        results = {}

        for name, model in self._candidates().items():
            try:
                logger.debug(f"  모델 학습: {name}")
                if name == "xgb":
                    model.fit(
                        X_train_s, y_train,
                        sample_weight=sw,
                        eval_set=[(X_val_s, y_val)],
                        verbose=False,
                    )
                else:
                    model.fit(X_train_s, y_train, sample_weight=sw)

                val_p = model.predict_proba(X_val_s)[:, 1]
                val_pred = (val_p >= 0.5).astype(int)

                auc = (
                    roc_auc_score(y_val, val_p)
                    if len(np.unique(y_val)) > 1 else 0.5
                )
                results[name] = {
                    "model": model,
                    "roc_auc": round(float(auc), 4),
                    "precision": round(float(precision_score(y_val, val_pred, zero_division=0)), 4),
                    "recall": round(float(recall_score(y_val, val_pred, zero_division=0)), 4),
                }
                logger.info(
                    f"  {name}: AUC={auc:.4f} "
                    f"Prec={results[name]['precision']} "
                    f"Rec={results[name]['recall']}"
                )
            except Exception as e:
                logger.error(f"  {name} 학습 실패: {e}")

        if not results:
            return {"error": "모든 모델 학습 실패"}

        # ROC-AUC 기준 최선 모델
        best_name = max(results, key=lambda k: results[k]["roc_auc"])
        self.best_model = results[best_name]["model"]
        self.best_model_name = best_name
        self.all_metrics = {
            k: {m: v for m, v in r.items() if m != "model"}
            for k, r in results.items()
        }
        logger.info(f"  ★ 최선 모델: {best_name} (AUC={results[best_name]['roc_auc']})")

        return {"best_model_name": best_name, "metrics": self.all_metrics}

    # ── P(up) 예측 ───────────────────────────────────────────
    def predict_p_up(self, X: np.ndarray) -> float:
        """최선 모델로 상승 확률 P(up) 예측

        스케일러는 학습 시 fit된 상태 → 동일한 스케일 적용.
        """
        if self.best_model is None:
            raise RuntimeError("모델 학습 미완료")
        X_s = np.nan_to_num(self.scaler.transform(X.reshape(1, -1)), nan=0.0)
        return float(self.best_model.predict_proba(X_s)[0][1])
