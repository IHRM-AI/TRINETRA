from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import shap

from trinetra.interpret.taxonomy import TRIGGERS, grade_for
from trinetra.models.gbm import SegmentModel


@dataclass(frozen=True)
class ReasonCode:
    code: str
    label: str
    contribution_logodds: float
    direction: str


@dataclass(frozen=True)
class Explanation:
    pd_value: float
    grade: str
    watch_tier: str
    reason_codes: list[ReasonCode]


class SegmentExplainer:
    def __init__(self, model: SegmentModel):
        if model.booster is None:
            raise RuntimeError("Model is not trained.")
        self._model = model
        self._explainer = shap.TreeExplainer(model.booster)

    def explain(self, x: pd.DataFrame, top_k: int = 5) -> list[Explanation]:
        shap_values = self._positive_class_shap(self._explainer.shap_values(x))
        pd_values = self._model.predict_pd(x)
        return [
            self._one(x.iloc[i], shap_values[i], float(pd_values[i]), top_k)
            for i in range(len(x))
        ]

    @staticmethod
    def _positive_class_shap(shap_values: object) -> np.ndarray:
        """Return the (n_samples, n_features) positive-class margin matrix.

        Older SHAP returns a list [class0, class1] for a binary LightGBM
        booster; newer SHAP returns a single array shaped either
        (n_samples, n_features) or (n_samples, n_features, n_classes).
        """
        if isinstance(shap_values, list):
            return np.asarray(shap_values[-1])
        values = np.asarray(shap_values)
        if values.ndim == 3:
            return values[:, :, -1]
        return values

    def _one(
        self, row: pd.Series, contributions: np.ndarray, pd_value: float, top_k: int
    ) -> Explanation:
        grade, tier = grade_for(pd_value)
        ranked = sorted(
            zip(row.index, contributions), key=lambda kv: abs(kv[1]), reverse=True
        )
        codes: list[ReasonCode] = []
        for feature, value in ranked:
            trigger = TRIGGERS.get(feature)
            if trigger is None or abs(value) < 1e-6:
                continue
            codes.append(
                ReasonCode(
                    code=trigger.code,
                    label=trigger.label,
                    contribution_logodds=round(float(value), 4),
                    direction="increases risk" if value > 0 else "reduces risk",
                )
            )
            if len(codes) >= top_k:
                break
        return Explanation(round(pd_value, 4), grade, tier, codes)
