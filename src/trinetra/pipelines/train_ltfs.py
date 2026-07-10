from __future__ import annotations

import argparse
import json
import logging

import joblib
import pandas as pd

from trinetra.config import settings
from trinetra.data import ltfs
from trinetra.eval.metrics import evaluate
from trinetra.features import ltfs as ltfs_features
from trinetra.models.gbm import SegmentModel
from trinetra.pipelines.splits import FourWaySplit, out_of_time_split

logger = logging.getLogger("trinetra.train")


def ltfs_split(raw: pd.DataFrame) -> FourWaySplit:
    """Out-of-time split on DisbursalDate: earlier vintages train, tune and
    calibrate; the most recent vintages form the untouched test block.
    """
    disbursal = pd.to_datetime(raw["DisbursalDate"], format="%d-%m-%y", errors="coerce")
    return out_of_time_split(disbursal)


def run() -> dict[str, float]:
    raw = ltfs.parse(ltfs.load_raw(settings.data_dir))
    features = ltfs_features.build(raw)
    target = raw[ltfs.TARGET].to_numpy()

    split = ltfs_split(raw)
    logger.info(
        "train=%d valid=%d calibrate=%d test=%d (%s split)",
        len(split.train),
        len(split.valid),
        len(split.calibrate),
        len(split.test),
        split.kind,
    )

    model = SegmentModel().fit(
        features.iloc[split.train],
        target[split.train],
        features.iloc[split.valid],
        target[split.valid],
    )
    model.calibrate(features.iloc[split.calibrate], target[split.calibrate])

    report = evaluate(target[split.test], model.predict_pd(features.iloc[split.test]))
    logger.info(
        "TEST AUC=%.4f Gini=%.4f KS=%.4f Brier=%.4f (n=%d, default_rate=%.3f)",
        report.auc,
        report.gini,
        report.ks,
        report.brier,
        report.n,
        report.default_rate,
    )

    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, settings.artifacts_dir / "ltfs_segment.joblib")
    payload = {"split": split.kind, **report.as_dict()}
    (settings.artifacts_dir / "ltfs_metrics.json").write_text(json.dumps(payload, indent=2))
    logger.info("top drivers:\n%s", model.importance().head(10).to_string())
    return payload


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    argparse.ArgumentParser(description="Train the L&T vehicle-finance PD segment.").parse_args()
    run()


if __name__ == "__main__":
    main()
