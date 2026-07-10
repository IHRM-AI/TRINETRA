from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd

TARGET = "default"
ORIGINATION_DATE = "origination_date"
SUBDIR = Path("raw") / "freddie"

# The Freddie Mac CRT loan-level ("lld") file is a headerless, pipe-delimited
# text file with 90 positional fields per row. The mapping below records the
# zero-based column index of each field this pipeline consumes; the indices are
# fixed by the published CRT file layout and must be kept in sync with it.
#
# Origination-time underwriting fields (known at loan cut, safe as features):
#   10 loan_term, 11 interest_rate, 12 original_upb, 17 num_units,
#   22 credit_score, 23 ltv, 24 cltv, 25 dti, 29 num_borrowers.
# Column 8 is the loan origination date (YYYYMM) and drives the out-of-time
# split. Column 37 is the 48-character monthly delinquency-status history over
# the loan's performance window; it is a post-origination outcome and is used
# only to derive the label, never as a feature.
EXPECTED_FIELD_COUNT = 90
ORIGINATION_DATE_COLUMN = 8
FEATURE_COLUMNS = {
    10: "loan_term",
    11: "interest_rate",
    12: "original_upb",
    17: "num_units",
    22: "credit_score",
    23: "ltv",
    24: "cltv",
    25: "dti",
    29: "num_borrowers",
}
DQ_COLUMN = 37

# A loan is labelled default if its monthly delinquency history ever reaches
# 90 days past due or worse (status codes 3-9 in the performance-window string).
SEVERE_CODES = set("3456789")


def _is_default(payment_history: str) -> int:
    return int(any(code in SEVERE_CODES for code in str(payment_history)))


def load_raw(data_dir: Path, max_files: int = 20) -> pd.DataFrame:
    archives = list((data_dir / SUBDIR).glob("*.zip"))
    if not archives:
        raise FileNotFoundError(
            f"Freddie CRT archive not found in {data_dir / SUBDIR}. Download the sample from "
            "freddiemac.com/research and place the zip there."
        )
    used = list(FEATURE_COLUMNS) + [ORIGINATION_DATE_COLUMN, DQ_COLUMN]
    frames: list[pd.DataFrame] = []
    with zipfile.ZipFile(archives[0]) as archive:
        members = [m for m in archive.namelist() if m.endswith("_lld.txt")][:max_files]
        for member in members:
            raw = pd.read_csv(
                io.BytesIO(archive.read(member)), sep="|", header=None, dtype=str, low_memory=False
            )
            if raw.shape[1] != EXPECTED_FIELD_COUNT:
                raise ValueError(
                    f"Freddie CRT member {member} has {raw.shape[1]} columns, expected "
                    f"{EXPECTED_FIELD_COUNT}. The file layout has changed; the positional "
                    "column indices in FEATURE_COLUMNS must be revalidated."
                )
            subset = raw[used].copy()
            subset.columns = (
                list(FEATURE_COLUMNS.values()) + [ORIGINATION_DATE, "_dq"]
            )
            frames.append(subset)

    frame = pd.concat(frames, ignore_index=True)
    origination = pd.to_datetime(frame[ORIGINATION_DATE], format="%Y%m", errors="coerce")
    if origination.notna().mean() < 0.99:
        raise ValueError(
            "Freddie origination-date column is not in the expected YYYYMM format; "
            "the positional layout may have changed."
        )
    frame[ORIGINATION_DATE] = origination
    frame[TARGET] = frame["_dq"].map(_is_default)
    return frame.drop(columns=["_dq"])
