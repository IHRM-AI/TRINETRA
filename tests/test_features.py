import numpy as np
import pandas as pd

from trinetra.data.ltfs import _duration_to_months
from trinetra.features import ltfs
from trinetra.features.ltfs import CATEGORICAL, IDENTITY_FLAGS, NUMERIC, _safe_ratio


def _raw_frame() -> pd.DataFrame:
    columns = (
        set(NUMERIC)
        | set(CATEGORICAL)
        | set(IDENTITY_FLAGS)
        | {"PRI.CURRENT.BALANCE", "PRI.SANCTIONED.AMOUNT"}
    )
    row = {name: 1 for name in columns}
    for name in CATEGORICAL:
        row[name] = "x"
    return pd.DataFrame([row, row])


def test_build_produces_derived_features():
    features = ltfs.build(_raw_frame())
    for derived in [
        "identity_completeness",
        "overdue_ratio",
        "active_ratio",
        "primary_utilization",
        "disbursed_to_asset",
        "no_bureau_history",
    ]:
        assert derived in features.columns
    for name in CATEGORICAL:
        assert str(features[name].dtype) == "category"


def test_no_bureau_history_flags_zero_score():
    frame = _raw_frame()
    frame.loc[0, "PERFORM_CNS.SCORE"] = 0
    features = ltfs.build(frame)
    assert features["no_bureau_history"].iloc[0] == 1
    assert features["no_bureau_history"].iloc[1] == 0


def test_safe_ratio_handles_zero_denominator():
    numerator = pd.Series([5.0, 3.0])
    denominator = pd.Series([0.0, 6.0])
    result = _safe_ratio(numerator, denominator)
    assert result.iloc[0] == 0.0
    assert abs(result.iloc[1] - 0.5) < 1e-12


def test_duration_to_months_parses_years_and_months():
    assert _duration_to_months("2yrs 6mon") == 30
    assert _duration_to_months("0yrs 0mon") == 0
    assert np.isnan(_duration_to_months(None))
