from __future__ import annotations

import argparse
import json
import logging

import joblib
import numpy as np
import pandas as pd

from trinetra.config import settings
from trinetra.data import ltfs
from trinetra.eval.metrics import evaluate
from trinetra.features import ltfs as ltfs_features
from trinetra.models.gbm import SegmentModel

logger = logging.getLogger("trinetra.train")


def temporal_split(
    frame: pd.DataFrame, order_key: str, valid_fraction: float
) -> tuple[np.ndarray, np.ndarray]:
    order = frame[order_key].fillna(frame[order_key].max()).argsort(kind="stable")
    cutoff = int(len(order) * (1 - valid_fraction))
    return order[:cutoff].to_numpy(), order[cutoff:].to_numpy()


def run(valid_fraction: float | None = None) -> dict[str, float]:
    valid_fraction = valid_fraction or settings.validation_fraction
    raw = ltfs.parse(ltfs.load_raw(settings.data_dir))
    features = ltfs_features.build(raw)
    target = raw[ltfs.TARGET].to_numpy()
    disbursal = pd.to_datetime(raw["DisbursalDate"], format="%d-%m-%y", errors="coerce")

    train_idx, valid_idx = temporal_split(
        pd.DataFrame({"d": disbursal}), "d", valid_fraction
    )
    logger.info("train=%d valid=%d (out-of-time split)", len(train_idx), len(valid_idx))

    model = SegmentModel().fit(
        features.iloc[train_idx],
        target[train_idx],
        features.iloc[valid_idx],
        target[valid_idx],
    )

    report = evaluate(target[valid_idx], model.predict_pd(features.iloc[valid_idx]))
    logger.info(
        "AUC=%.4f Gini=%.4f KS=%.4f Brier=%.4f (n=%d, default_rate=%.3f)",
        report.auc,
        report.gini,
        report.ks,
        report.brier,
        report.n,
        report.default_rate,
    )

    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, settings.artifacts_dir / "ltfs_segment.joblib")
    (settings.artifacts_dir / "ltfs_metrics.json").write_text(
        json.dumps(report.as_dict(), indent=2)
    )
    logger.info("top drivers:\n%s", model.importance().head(10).to_string())
    return report.as_dict()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(description="Train the L&T vehicle-finance PD segment.")
    parser.add_argument("--valid-fraction", type=float, default=None)
    args = parser.parse_args()
    run(args.valid_fraction)


if __name__ == "__main__":
    main()
