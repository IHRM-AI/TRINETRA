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


def test_high_risk_feature_reason_code_points_up():
    rng = np.random.default_rng(3)
    n = 1200
    x = pd.DataFrame(
        {
            "ltv": rng.uniform(50, 95, n),
            "PERFORM_CNS.SCORE": rng.integers(300, 850, n),
            "NO.OF_INQUIRIES": rng.integers(0, 12, n),
            "primary_utilization": rng.uniform(0, 1.2, n),
        }
    )
    # Inquiries are the sole driver of default so the trigger direction is
    # unambiguous: more inquiries must read as increasing risk.
    y = (x["NO.OF_INQUIRIES"] >= 6).astype(int).to_numpy()
    model = SegmentModel(num_boost_round=120, early_stopping_rounds=30)
    model.fit(x.iloc[:800], y[:800], x.iloc[800:], y[800:])

    high = pd.DataFrame(
        {
            "ltv": [70.0],
            "PERFORM_CNS.SCORE": [600],
            "NO.OF_INQUIRIES": [11],
            "primary_utilization": [0.5],
        }
    )
    explanation = SegmentExplainer(model).explain(high, top_k=4)[0]
    inquiry_codes = [c for c in explanation.reason_codes if c.code == "EWS-E01"]
    assert inquiry_codes, "expected the inquiry trigger to fire for a high-inquiry borrower"
    assert inquiry_codes[0].direction == "increases risk"
    assert inquiry_codes[0].contribution_logodds > 0
