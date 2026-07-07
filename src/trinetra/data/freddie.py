from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd

TARGET = "default"
SUBDIR = Path("raw") / "freddie"

# Positional columns in the Freddie CRT loan-level (lld) format.
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
    frames: list[pd.DataFrame] = []
    with zipfile.ZipFile(archives[0]) as archive:
        members = [m for m in archive.namelist() if m.endswith("_lld.txt")][:max_files]
        for member in members:
            raw = pd.read_csv(
                io.BytesIO(archive.read(member)), sep="|", header=None, dtype=str, low_memory=False
            )
            subset = raw[list(FEATURE_COLUMNS) + [DQ_COLUMN]].copy()
            subset.columns = list(FEATURE_COLUMNS.values()) + ["_dq"]
            frames.append(subset)

    frame = pd.concat(frames, ignore_index=True)
    frame[TARGET] = frame["_dq"].map(_is_default)
    return frame.drop(columns=["_dq"])
