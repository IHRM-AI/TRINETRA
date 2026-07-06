import numpy as np
import pandas as pd

from trinetra.interpret.reason_codes import SegmentExplainer
from trinetra.interpret.taxonomy import grade_for
from trinetra.models.gbm import SegmentModel


def test_grade_bands():
    assert grade_for(0.01) == ("A", "Standard")
    assert grade_for(0.12) == ("D", "Watchlist")
    assert grade_for(0.40)[0] == "E"


def _toy_frame(n: int, rng: np.random.Generator) -> pd.DataFrame:
    ltv = rng.uniform(50, 95, n)
    return pd.DataFrame(
        {
            "ltv": ltv,
            "PERFORM_CNS.SCORE": rng.integers(300, 850, n),
            "NO.OF_INQUIRIES": rng.integers(0, 10, n),
            "primary_utilization": rng.uniform(0, 1.5, n),
        }
    )


def test_explainer_emits_reason_codes():
    rng = np.random.default_rng(0)
    x = _toy_frame(600, rng)
    y = (x["ltv"] + x["NO.OF_INQUIRIES"] * 3 > 80).astype(int).to_numpy()
    model = SegmentModel(num_boost_round=80, early_stopping_rounds=20)
    model.fit(x.iloc[:400], y[:400], x.iloc[400:], y[400:])

    explanations = SegmentExplainer(model).explain(x.iloc[400:410], top_k=3)
    assert len(explanations) == 10
    for exp in explanations:
        assert 0.0 <= exp.pd_value <= 1.0
        assert exp.grade in {"A", "B", "C", "D", "E"}
        assert all(code.code.startswith("EWS-") for code in exp.reason_codes)
