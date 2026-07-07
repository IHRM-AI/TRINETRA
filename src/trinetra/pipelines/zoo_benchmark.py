from __future__ import annotations

import json
import logging

import numpy as np

from trinetra.config import settings
from trinetra.eval.metrics import evaluate
from trinetra.models.gbm import SegmentModel
from trinetra.segments import SEGMENTS

logger = logging.getLogger("trinetra.zoo")


def _split(n: int, seed: int, valid_fraction: float) -> tuple[np.ndarray, np.ndarray]:
    order = np.random.default_rng(seed).permutation(n)
    cutoff = int(n * (1 - valid_fraction))
    return order[:cutoff], order[cutoff:]


def run() -> dict[str, object]:
    rows = []
    for name, (label, prepare) in SEGMENTS.items():
        try:
            x, y = prepare(settings.data_dir)
        except FileNotFoundError:
            logger.info("segment %s skipped (data not present)", name)
            continue
        train_idx, valid_idx = _split(len(x), settings.random_seed, settings.validation_fraction)
        model = SegmentModel().fit(x.iloc[train_idx], y[train_idx], x.iloc[valid_idx], y[valid_idx])
        report = evaluate(y[valid_idx], model.predict_pd(x.iloc[valid_idx]))
        rows.append({"segment": name, "label": label, **report.as_dict()})
        logger.info(
            "%-11s %-22s AUC=%.3f Gini=%.3f KS=%.3f (n=%d, default_rate=%.3f)",
            name, label, report.auc, report.gini, report.ks, report.n, report.default_rate,
        )

    result = {"segments": rows}
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    (settings.artifacts_dir / "zoo_benchmark.json").write_text(json.dumps(result, indent=2))
    return result


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    run()


if __name__ == "__main__":
    main()
