import numpy as np

from trinetra.eval.metrics import evaluate, ks_statistic


def test_perfect_separation():
    y_true = np.array([0, 0, 1, 1])
    y_score = np.array([0.1, 0.2, 0.8, 0.9])
    report = evaluate(y_true, y_score)
    assert report.auc == 1.0
    assert report.gini == 1.0
    assert report.ks == 1.0


def test_ks_within_bounds():
    rng = np.random.default_rng(0)
    y_true = rng.integers(0, 2, size=500)
    y_score = rng.random(500)
    assert 0.0 <= ks_statistic(y_true, y_score) <= 1.0


def test_report_reports_class_balance():
    y_true = np.array([0, 1, 1, 1])
    report = evaluate(y_true, np.array([0.2, 0.6, 0.7, 0.9]))
    assert report.n == 4
    assert abs(report.default_rate - 0.75) < 1e-9
