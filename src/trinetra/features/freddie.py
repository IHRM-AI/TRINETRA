from __future__ import annotations

import numpy as np
import pandas as pd

NUMERIC = [
    "loan_term",
    "interest_rate",
    "original_upb",
    "num_units",
    "credit_score",
    "ltv",
    "cltv",
    "dti",
    "num_borrowers",
]
SENTINELS = {"credit_score": 9999, "dti": 999, "ltv": 999, "cltv": 999}


def build(df: pd.DataFrame) -> pd.DataFrame:
    features = pd.DataFrame(index=df.index)
    for column in NUMERIC:
        features[column] = pd.to_numeric(df[column], errors="coerce")
    for column, sentinel in SENTINELS.items():
        features[column] = features[column].replace(sentinel, np.nan)
    features["payment_to_balance"] = features["interest_rate"] / 100 * features["original_upb"]
    return features
