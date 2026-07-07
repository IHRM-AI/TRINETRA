from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

from trinetra.features.ltfs import CATEGORICAL
from trinetra.genai.memo import CreditMemo, CreditMemoService
from trinetra.interpret.reason_codes import Explanation, SegmentExplainer
from trinetra.models.gbm import SegmentModel
from trinetra.survival.term_structure import TermStructure
from trinetra.survival.term_structure import build as build_term_structure


class ScoringService:
    def __init__(self, model: SegmentModel, memo_service: CreditMemoService | None = None):
        self._model = model
        self._explainer = SegmentExplainer(model)
        self._memo = memo_service or CreditMemoService()

    @classmethod
    def from_artifacts(cls, path: Path) -> "ScoringService":
        return cls(joblib.load(path))

    @property
    def feature_names(self) -> list[str]:
        return self._model.feature_names

    def _frame(self, features: dict[str, object]) -> pd.DataFrame:
        frame = pd.DataFrame([features]).reindex(columns=self._model.feature_names)
        for column in CATEGORICAL:
            if column in frame.columns:
                frame[column] = frame[column].astype("category")
        return frame

    def score(self, features: dict[str, object]) -> Explanation:
        return self._explainer.explain(self._frame(features), top_k=5)[0]

    def term_structure(self, features: dict[str, object]) -> TermStructure:
        return build_term_structure(self.score(features).pd_value, features)

    def memo(self, borrower: str, exposure: str, features: dict[str, object]) -> CreditMemo:
        return self._memo.draft(borrower, exposure, self.score(features))
