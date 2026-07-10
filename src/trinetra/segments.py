from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from trinetra.data import freddie, homecredit, ltfs
from trinetra.features import freddie as freddie_features
from trinetra.features import homecredit as homecredit_features
from trinetra.features import ltfs as ltfs_features


@dataclass(frozen=True)
class PreparedSegment:
    """Feature matrix, labels and the split strategy for one segment.

    order_key holds a per-row date used for an out-of-time split. It is None
    for segments that carry no absolute vintage field, in which case a
    fixed-seed stratified random split is used and split_kind records that.
    """

    x: pd.DataFrame
    y: np.ndarray
    order_key: pd.Series | None
    split_kind: str


def _prepare_ltfs(data_dir: Path) -> PreparedSegment:
    raw = ltfs.parse(ltfs.load_raw(data_dir))
    disbursal = pd.to_datetime(raw["DisbursalDate"], format="%d-%m-%y", errors="coerce")
    return PreparedSegment(
        x=ltfs_features.build(raw),
        y=raw[ltfs.TARGET].to_numpy(),
        order_key=disbursal,
        split_kind="out-of-time",
    )


def _prepare_homecredit(data_dir: Path) -> PreparedSegment:
    raw = homecredit.load_raw(data_dir)
    return PreparedSegment(
        x=homecredit_features.build(raw),
        y=raw[homecredit.TARGET].to_numpy(),
        order_key=None,
        split_kind="random-no-vintage",
    )


def _prepare_freddie(data_dir: Path) -> PreparedSegment:
    raw = freddie.load_raw(data_dir)
    return PreparedSegment(
        x=freddie_features.build(raw),
        y=raw[freddie.TARGET].to_numpy(),
        order_key=raw[freddie.ORIGINATION_DATE],
        split_kind="out-of-time",
    )


SEGMENTS: dict[str, tuple[str, Callable[[Path], PreparedSegment]]] = {
    "ltfs": ("India vehicle finance", _prepare_ltfs),
    "homecredit": ("Retail unsecured", _prepare_homecredit),
    "freddie": ("US mortgage", _prepare_freddie),
}
