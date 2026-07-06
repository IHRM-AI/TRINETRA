from __future__ import annotations

from dataclasses import dataclass, field

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

DEFAULT_PARAMS: dict[str, object] = {
    "objective": "binary",
    "metric": "auc",
    "learning_rate": 0.03,
    "num_leaves": 63,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 1,
    "min_child_samples": 200,
    "verbosity": -1,
}


@dataclass
class SegmentModel:
    """A calibrated probability-of-default model for one loan segment."""

    params: dict[str, object] = field(default_factory=lambda: dict(DEFAULT_PARAMS))
    num_boost_round: int = 1500
    early_stopping_rounds: int = 100
    booster: lgb.Booster | None = None
    calibrator: IsotonicRegression | None = None
    feature_names: list[str] = field(default_factory=list)

    def fit(
        self,
        x_train: pd.DataFrame,
        y_train: np.ndarray,
        x_valid: pd.DataFrame,
        y_valid: np.ndarray,
    ) -> "SegmentModel":
        self.feature_names = list(x_train.columns)
        train_set = lgb.Dataset(x_train, label=y_train)
        valid_set = lgb.Dataset(x_valid, label=y_valid, reference=train_set)
        self.booster = lgb.train(
            self.params,
            train_set,
            num_boost_round=self.num_boost_round,
            valid_sets=[valid_set],
            callbacks=[lgb.early_stopping(self.early_stopping_rounds, verbose=False)],
        )
        raw_valid = self._raw_score(x_valid)
        self.calibrator = IsotonicRegression(out_of_bounds="clip").fit(raw_valid, y_valid)
        return self

    def _raw_score(self, x: pd.DataFrame) -> np.ndarray:
        if self.booster is None:
            raise RuntimeError("Model is not trained.")
        return self.booster.predict(x, num_iteration=self.booster.best_iteration)

    def predict_pd(self, x: pd.DataFrame) -> np.ndarray:
        raw = self._raw_score(x)
        if self.calibrator is None:
            return raw
        return self.calibrator.predict(raw)

    def importance(self) -> pd.Series:
        if self.booster is None:
            raise RuntimeError("Model is not trained.")
        gains = self.booster.feature_importance(importance_type="gain")
        return pd.Series(gains, index=self.feature_names).sort_values(ascending=False)
