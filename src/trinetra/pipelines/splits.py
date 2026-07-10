from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class FourWaySplit:
    """Disjoint index sets for a leakage-free evaluation.

    train      fits the booster
    valid      drives early stopping only
    calibrate  fits the isotonic calibrator only
    test       reports every metric and is never seen before scoring
    """

    train: np.ndarray
    valid: np.ndarray
    calibrate: np.ndarray
    test: np.ndarray
    kind: str


def _cut_points(n: int, valid: float, calibrate: float, test: float) -> tuple[int, int, int]:
    n_test = int(round(n * test))
    n_calibrate = int(round(n * calibrate))
    n_valid = int(round(n * valid))
    train_end = n - n_valid - n_calibrate - n_test
    valid_end = train_end + n_valid
    calibrate_end = valid_end + n_calibrate
    return train_end, valid_end, calibrate_end


def out_of_time_split(
    order_key: pd.Series,
    valid: float = 0.15,
    calibrate: float = 0.15,
    test: float = 0.2,
) -> FourWaySplit:
    """Order rows by a date-like key and cut the most recent vintages into
    the calibrate and test blocks. Earlier vintages train and tune the model.
    """
    order = order_key.fillna(order_key.max()).argsort(kind="stable").to_numpy()
    train_end, valid_end, calibrate_end = _cut_points(len(order), valid, calibrate, test)
    return FourWaySplit(
        train=order[:train_end],
        valid=order[train_end:valid_end],
        calibrate=order[valid_end:calibrate_end],
        test=order[calibrate_end:],
        kind="out-of-time",
    )


def stratified_random_split(
    y: np.ndarray,
    seed: int,
    valid: float = 0.15,
    calibrate: float = 0.15,
    test: float = 0.2,
    kind: str = "random-no-vintage",
) -> FourWaySplit:
    """Fixed-seed split that preserves the class balance in every block. Used
    only where no vintage field exists to support an out-of-time split.
    """
    y = np.asarray(y)
    rng = np.random.default_rng(seed)
    blocks: list[list[np.ndarray]] = [[], [], [], []]
    for label in np.unique(y):
        members = np.where(y == label)[0]
        rng.shuffle(members)
        train_end, valid_end, calibrate_end = _cut_points(
            len(members), valid, calibrate, test
        )
        blocks[0].append(members[:train_end])
        blocks[1].append(members[train_end:valid_end])
        blocks[2].append(members[valid_end:calibrate_end])
        blocks[3].append(members[calibrate_end:])
    train, valid_idx, calibrate_idx, test_idx = (np.concatenate(b) for b in blocks)
    return FourWaySplit(
        train=np.sort(train),
        valid=np.sort(valid_idx),
        calibrate=np.sort(calibrate_idx),
        test=np.sort(test_idx),
        kind=kind,
    )
