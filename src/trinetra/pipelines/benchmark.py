from __future__ import annotations

import json
import logging

import joblib

from trinetra.config import settings
from trinetra.data import ltfs
from trinetra.eval.benchmark import capture_at, capture_curve, rule_score
from trinetra.eval.metrics import evaluate
from trinetra.features import ltfs as ltfs_features
from trinetra.pipelines.train_ltfs import ltfs_split

logger = logging.getLogger("trinetra.benchmark")
RATES = [0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5]
FLAG_BUDGET = 0.2


def run() -> dict[str, object]:
    model = joblib.load(settings.artifacts_dir / "ltfs_segment.joblib")
    raw = ltfs.parse(ltfs.load_raw(settings.data_dir))
    features = ltfs_features.build(raw)
    target = raw[ltfs.TARGET].to_numpy()
    split = ltfs_split(raw)

    x_test, y_test = features.iloc[split.test], target[split.test]
    model_pd = model.predict_pd(x_test)
    rules = rule_score(x_test)

    report = {
        "split": split.kind,
        "n_test": int(len(split.test)),
        "default_rate": round(float(y_test.mean()), 4),
        "metrics": evaluate(y_test, model_pd).as_dict(),
        "capture_at_20pct": {
            "model": round(capture_at(y_test, model_pd, FLAG_BUDGET), 4),
            "rule_baseline": round(capture_at(y_test, rules, FLAG_BUDGET), 4),
        },
        "capture_curve_model": capture_curve(y_test, model_pd, RATES),
        "capture_curve_rule": capture_curve(y_test, rules, RATES),
    }
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    (settings.artifacts_dir / "benchmark.json").write_text(json.dumps(report, indent=2))
    logger.info(
        "capture@20%%: model %.1f%% vs rule baseline %.1f%% (lift %.1fx)",
        report["capture_at_20pct"]["model"] * 100,
        report["capture_at_20pct"]["rule_baseline"] * 100,
        report["capture_at_20pct"]["model"] / max(report["capture_at_20pct"]["rule_baseline"], 1e-6),
    )
    return report


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    run()


if __name__ == "__main__":
    main()
