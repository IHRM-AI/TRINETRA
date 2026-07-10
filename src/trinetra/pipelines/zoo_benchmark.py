from __future__ import annotations

import json
import logging

from trinetra.config import settings
from trinetra.eval.metrics import evaluate
from trinetra.models.gbm import SegmentModel
from trinetra.pipelines.splits import out_of_time_split, stratified_random_split
from trinetra.segments import SEGMENTS, PreparedSegment

logger = logging.getLogger("trinetra.zoo")


def _split(prepared: PreparedSegment, seed: int):
    if prepared.order_key is not None:
        return out_of_time_split(prepared.order_key)
    return stratified_random_split(prepared.y, seed, kind=prepared.split_kind)


def run() -> dict[str, object]:
    rows = []
    for name, (label, prepare) in SEGMENTS.items():
        try:
            prepared = prepare(settings.data_dir)
        except FileNotFoundError:
            logger.info("segment %s skipped (data not present)", name)
            continue

        split = _split(prepared, settings.random_seed)
        x, y = prepared.x, prepared.y
        model = SegmentModel().fit(
            x.iloc[split.train], y[split.train], x.iloc[split.valid], y[split.valid]
        )
        model.calibrate(x.iloc[split.calibrate], y[split.calibrate])

        report = evaluate(y[split.test], model.predict_pd(x.iloc[split.test]))
        rows.append(
            {"segment": name, "label": label, "split": split.kind, **report.as_dict()}
        )
        logger.info(
            "%-11s %-22s [%s] AUC=%.3f Gini=%.3f KS=%.3f (n=%d, default_rate=%.3f)",
            name, label, split.kind, report.auc, report.gini, report.ks,
            report.n, report.default_rate,
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
