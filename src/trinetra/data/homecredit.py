from __future__ import annotations

from pathlib import Path

import pandas as pd

TARGET = "TARGET"
ID = "SK_ID_CURR"
DATASET = Path("raw") / "homecredit" / "application_train.csv"


def load_raw(data_dir: Path) -> pd.DataFrame:
    path = data_dir / DATASET
    if not path.exists():
        raise FileNotFoundError(
            f"Home Credit application table not found at {path}. Run scripts/download_data.sh."
        )
    return pd.read_csv(path)
