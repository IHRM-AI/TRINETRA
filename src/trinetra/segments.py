from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

from trinetra.data import freddie, homecredit, ltfs
from trinetra.features import freddie as freddie_features
from trinetra.features import homecredit as homecredit_features
from trinetra.features import ltfs as ltfs_features

Prepared = tuple[pd.DataFrame, np.ndarray]


def _prepare_ltfs(data_dir: Path) -> Prepared:
    raw = ltfs.parse(ltfs.load_raw(data_dir))
    return ltfs_features.build(raw), raw[ltfs.TARGET].to_numpy()


def _prepare_homecredit(data_dir: Path) -> Prepared:
    raw = homecredit.load_raw(data_dir)
    return homecredit_features.build(raw), raw[homecredit.TARGET].to_numpy()


def _prepare_freddie(data_dir: Path) -> Prepared:
    raw = freddie.load_raw(data_dir)
    return freddie_features.build(raw), raw[freddie.TARGET].to_numpy()


SEGMENTS: dict[str, tuple[str, Callable[[Path], Prepared]]] = {
    "ltfs": ("India vehicle finance", _prepare_ltfs),
    "homecredit": ("Retail unsecured", _prepare_homecredit),
    "freddie": ("US mortgage", _prepare_freddie),
}
