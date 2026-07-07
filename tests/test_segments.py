import numpy as np
import pandas as pd

from trinetra.data.freddie import _is_default
from trinetra.features import freddie as freddie_features


def test_default_label_from_payment_history():
    assert _is_default("000000000000") == 0
    assert _is_default("000012000") == 0  # 30 and 60 day are not 90-plus
    assert _is_default("0000300000") == 1
    assert _is_default("XX0X0X") == 0


def test_freddie_sentinels_become_missing():
    raw = pd.DataFrame(
        {
            "loan_term": ["360"],
            "interest_rate": ["5.5"],
            "original_upb": ["300000"],
            "num_units": ["1"],
            "credit_score": ["9999"],
            "ltv": ["95"],
            "cltv": ["95"],
            "dti": ["999"],
            "num_borrowers": ["2"],
        }
    )
    features = freddie_features.build(raw)
    assert np.isnan(features["credit_score"].iloc[0])
    assert np.isnan(features["dti"].iloc[0])
    assert features["ltv"].iloc[0] == 95
