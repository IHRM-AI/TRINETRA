from __future__ import annotations

import numpy as np
import pandas as pd

NUMERIC = [
    "disbursed_amount",
    "asset_cost",
    "ltv",
    "PERFORM_CNS.SCORE",
    "PRI.NO.OF.ACCTS",
    "PRI.ACTIVE.ACCTS",
    "PRI.OVERDUE.ACCTS",
    "PRI.CURRENT.BALANCE",
    "PRI.SANCTIONED.AMOUNT",
    "PRI.DISBURSED.AMOUNT",
    "SEC.NO.OF.ACCTS",
    "SEC.ACTIVE.ACCTS",
    "SEC.OVERDUE.ACCTS",
    "PRIMARY.INSTAL.AMT",
    "NEW.ACCTS.IN.LAST.SIX.MONTHS",
    "DELINQUENT.ACCTS.IN.LAST.SIX.MONTHS",
    "NO.OF_INQUIRIES",
    "age_years",
    "avg_acct_age_months",
    "credit_history_months",
]

CATEGORICAL = ["Employment.Type", "State_ID", "manufacturer_id"]

IDENTITY_FLAGS = [
    "Aadhar_flag",
    "PAN_flag",
    "VoterID_flag",
    "Driving_flag",
    "Passport_flag",
]


def build(df: pd.DataFrame) -> pd.DataFrame:
    features = pd.DataFrame(index=df.index)

    for column in NUMERIC:
        features[column] = pd.to_numeric(df[column], errors="coerce")

    features["identity_completeness"] = df[IDENTITY_FLAGS].sum(axis=1)
    features["overdue_ratio"] = _safe_ratio(
        df["PRI.OVERDUE.ACCTS"], df["PRI.NO.OF.ACCTS"]
    )
    features["active_ratio"] = _safe_ratio(
        df["PRI.ACTIVE.ACCTS"], df["PRI.NO.OF.ACCTS"]
    )
    features["primary_utilization"] = _safe_ratio(
        df["PRI.CURRENT.BALANCE"], df["PRI.SANCTIONED.AMOUNT"]
    )
    features["disbursed_to_asset"] = _safe_ratio(
        df["disbursed_amount"], df["asset_cost"]
    )
    features["no_bureau_history"] = (df["PERFORM_CNS.SCORE"] == 0).astype("int8")

    for column in CATEGORICAL:
        features[column] = df[column].astype("category")

    return features


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denom = denominator.replace(0, np.nan)
    return (numerator / denom).replace([np.inf, -np.inf], np.nan).fillna(0.0)
