from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

TARGET = "loan_default"
ID = "UniqueID"
DATASET_SUBDIR = Path("raw") / "ltfs"

_DURATION = re.compile(r"(?:(\d+)\s*yrs)?\s*(?:(\d+)\s*mon)?")


def _duration_to_months(value: str) -> float:
    if not isinstance(value, str):
        return np.nan
    match = _DURATION.search(value)
    if match is None:
        return np.nan
    years = int(match.group(1)) if match.group(1) else 0
    months = int(match.group(2)) if match.group(2) else 0
    return years * 12 + months


def load_raw(data_dir: Path, split: str = "train") -> pd.DataFrame:
    path = data_dir / DATASET_SUBDIR / f"{split}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"L&T dataset not found at {path}. Run scripts/download_data.sh first."
        )
    return pd.read_csv(path)


def parse(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    dob = pd.to_datetime(out["Date.of.Birth"], format="%d-%m-%y", errors="coerce")
    disbursal = pd.to_datetime(out["DisbursalDate"], format="%d-%m-%y", errors="coerce")
    out["age_years"] = ((disbursal - dob).dt.days / 365.25).clip(lower=18, upper=90)
    out["disbursal_month"] = disbursal.dt.to_period("M").astype(str)
    out["avg_acct_age_months"] = out["AVERAGE.ACCT.AGE"].map(_duration_to_months)
    out["credit_history_months"] = out["CREDIT.HISTORY.LENGTH"].map(_duration_to_months)
    return out
