"""
Machine Learning Module: Regime & Momentum Direction Classifier.
Uses Scikit-learn (RandomForest / GradientBoosting) to evaluate candle feature sets.
Features:
- Returns over last 1, 3, 5 candles
- Normalized EMA fast-to-slow spread
- RSI
- ADX and DI spreads
- ATR % of price (volatility)
- Volume ratio (current volume vs 10-period rolling average)
Status:
- NOT_TRAINED: Initial state
- INSUFFICIENT_DATA: Less than 100 historical candles available
- VALIDATING: Walk-forward validation in progress
- READY: Trained and validated on chronological split
"""

from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score
import logging

logger = logging.getLogger("riskpilot.ml")


class MLStrategyModel:
    def __init__(self, min_training_samples: int = 80):
        self.min_samples = min_training_samples
        self.model: Optional[GradientBoostingClassifier] = None
        self.status: str = "NOT_TRAINED"
        self.validation_accuracy: Optional[float] = None
        self.last_trained_sample_count: int = 0
        self.feature_columns = [
            "return_1",
            "return_3",
            "return_5",
            "ema_diff_pct",
            "rsi",
            "adx",
            "di_spread",
            "atr_pct",
            "vol_ratio"
        ]

    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extracts leakage-free chronological features from candle data."""
        feats = pd.DataFrame(index=df.index)
        close = df["close"]

        feats["return_1"] = close.pct_change(1)
        feats["return_3"] = close.pct_change(3)
        feats["return_5"] = close.pct_change(5)

        if "ema_fast" in df.columns and "ema_slow" in df.columns:
            feats["ema_diff_pct"] = (df["ema_fast"] - df["ema_slow"]) / df["close"] * 100.0
        else:
            feats["ema_diff_pct"] = 0.0

        feats["rsi"] = df.get("rsi", 50.0)
        feats["adx"] = df.get("adx", 20.0)

        plus_di = df.get("plus_di", 25.0)
        minus_di = df.get("minus_di", 25.0)
        feats["di_spread"] = plus_di - minus_di

        feats["atr_pct"] = df.get("atr_pct", 1.0)

        # Volume ratio relative to 10-period rolling average
        vol = df.get("volume", pd.Series(1.0, index=df.index))
        vol_ma = vol.rolling(10).mean().replace(0.0, np.nan)
        feats["vol_ratio"] = (vol / vol_ma).fillna(1.0)

        return feats

    def train_and_validate(self, df: pd.DataFrame, target_horizon: int = 3) -> Dict[str, Any]:
        """
        Trains model on historical candles using strictly chronological walk-forward split.
        Target: 1 if future return > 0.15%, -1 if future return < -0.15%, 0 if flat.
        """
        if len(df) < self.min_samples:
            self.status = "INSUFFICIENT_DATA"
            return {
                "status": self.status,
                "message": f"Requires at least {self.min_samples} candles. Got {len(df)}.",
                "accuracy": None
            }

        self.status = "VALIDATING"
        feats = self.extract_features(df)

        # Target: future return over target_horizon
        future_return = df["close"].pct_change(target_horizon).shift(-target_horizon)

        # Threshold for meaningful move
        threshold = 0.0015  # 15 bps
        target = pd.Series(0, index=df.index)
        target[future_return > threshold] = 1   # UP
        target[future_return < -threshold] = -1 # DOWN

        # Drop NaN rows due to lookback/lookforward
        valid_idx = ~(feats.isna().any(axis=1) | future_return.isna())
        X = feats[valid_idx][self.feature_columns]
        y = target[valid_idx]

        if len(X) < 50:
            self.status = "INSUFFICIENT_DATA"
            return {"status": self.status, "message": "Too few valid samples after lag alignment.", "accuracy": None}

        # Chronological split (80% train, 20% validation) - NO random shuffle to avoid lookahead leakage
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]

        clf = GradientBoostingClassifier(
            n_estimators=40,
            learning_rate=0.05,
            max_depth=3,
            random_state=42
        )
        clf.fit(X_train, y_train)

        val_preds = clf.predict(X_val)
        acc = float(accuracy_score(y_val, val_preds))

        self.model = clf
        self.validation_accuracy = round(acc, 4)
        self.last_trained_sample_count = len(X)
        self.status = "READY"

        return {
            "status": self.status,
            "accuracy": self.validation_accuracy,
            "training_samples": len(X_train),
            "validation_samples": len(X_val),
            "feature_importances": dict(zip(self.feature_columns, [round(float(w), 4) for w in clf.feature_importances_]))
        }

    def predict(self, latest_df: pd.DataFrame) -> Tuple[Optional[str], Optional[float]]:
        """
        Returns (predicted_direction, confidence) for the latest candle.
        Confidence is the probability of the predicted class.
        """
        if self.status != "READY" or self.model is None or len(latest_df) < 15:
            return None, None

        feats = self.extract_features(latest_df)
        curr_row = feats.iloc[[-1]][self.feature_columns]

        if curr_row.isna().any().any():
            return None, None

        probs = self.model.predict_proba(curr_row)[0]
        classes = self.model.classes_

        best_idx = int(np.argmax(probs))
        predicted_class = classes[best_idx]
        confidence = float(probs[best_idx])

        direction_map = {1: "UP", -1: "DOWN", 0: "NEUTRAL"}
        return direction_map.get(predicted_class, "NEUTRAL"), round(confidence, 3)
