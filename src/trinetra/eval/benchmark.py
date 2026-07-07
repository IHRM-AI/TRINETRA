from __future__ import annotations

import numpy as np
import pandas as pd


def rule_score(features: pd.DataFrame) -> np.ndarray:
    """A rule-based EWS proxy: a count of fired risk triggers per account."""
    triggers = (
        (features["PERFORM_CNS.SCORE"] < 500).astype(int)
        + (features["PRI.OVERDUE.ACCTS"] > 0).astype(int)
        + (features["DELINQUENT.ACCTS.IN.LAST.SIX.MONTHS"] > 0).astype(int)
        + (features["NO.OF_INQUIRIES"] >= 3).astype(int)
        + (features["primary_utilization"] > 0.9).astype(int)
    )
    return triggers.to_numpy()


def capture_at(y_true: np.ndarray, score: np.ndarray, flag_rate: float) -> float:
    """Fraction of defaulters captured within the top flag_rate by score."""
    y_true = np.asarray(y_true)
    order = np.argsort(-np.asarray(score), kind="stable")
    cutoff = max(1, int(len(order) * flag_rate))
    flagged = order[:cutoff]
    total_defaults = y_true.sum()
    if total_defaults == 0:
        return 0.0
    return float(y_true[flagged].sum() / total_defaults)


def capture_curve(
    y_true: np.ndarray, score: np.ndarray, rates: list[float]
) -> list[dict[str, float]]:
    return [
        {"flag_rate": rate, "capture": round(capture_at(y_true, score, rate), 4)}
        for rate in rates
    ]
