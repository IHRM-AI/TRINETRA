from __future__ import annotations

import numpy as np
import pandas as pd

NUMERIC = [
    "AMT_INCOME_TOTAL",
    "AMT_CREDIT",
    "AMT_ANNUITY",
    "AMT_GOODS_PRICE",
    "REGION_POPULATION_RELATIVE",
    "DAYS_BIRTH",
    "DAYS_EMPLOYED",
    "DAYS_REGISTRATION",
    "DAYS_ID_PUBLISH",
    "CNT_FAM_MEMBERS",
    "EXT_SOURCE_1",
    "EXT_SOURCE_2",
    "EXT_SOURCE_3",
    "AMT_REQ_CREDIT_BUREAU_YEAR",
    "DEF_30_CNT_SOCIAL_CIRCLE",
]

CATEGORICAL = [
    "NAME_CONTRACT_TYPE",
    "CODE_GENDER",
    "NAME_INCOME_TYPE",
    "NAME_EDUCATION_TYPE",
    "NAME_FAMILY_STATUS",
    "OCCUPATION_TYPE",
]


def build(df: pd.DataFrame) -> pd.DataFrame:
    features = pd.DataFrame(index=df.index)
    for column in NUMERIC:
        features[column] = pd.to_numeric(df[column], errors="coerce")

    income = features["AMT_INCOME_TOTAL"].replace(0, np.nan)
    features["credit_income_ratio"] = features["AMT_CREDIT"] / income
    features["annuity_income_ratio"] = features["AMT_ANNUITY"] / income
    features["employment_ratio"] = (df["DAYS_EMPLOYED"] / df["DAYS_BIRTH"]).replace(
        [np.inf, -np.inf], np.nan
    )
    features["ext_source_mean"] = df[["EXT_SOURCE_1", "EXT_SOURCE_2", "EXT_SOURCE_3"]].mean(axis=1)

    for column in CATEGORICAL:
        features[column] = df[column].astype("category")

    return features
