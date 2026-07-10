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


def test_metrics_against_hand_computed_fixture():
    # Six borrowers, three defaults. Positives score {0.35, 0.70, 0.90},
    # negatives score {0.10, 0.40, 0.80}. Of the nine positive-negative pairs
    # six are correctly ordered, so AUC = 6 / 9 and Gini = 2 * AUC - 1.
    y_true = np.array([0, 0, 1, 0, 1, 1])
    y_score = np.array([0.10, 0.40, 0.35, 0.80, 0.70, 0.90])
    report = evaluate(y_true, y_score)

    assert report.n == 6
    assert abs(report.default_rate - 0.5) < 1e-12
    assert abs(report.auc - 6 / 9) < 1e-12
    assert abs(report.gini - (2 * 6 / 9 - 1)) < 1e-12
    # Squared-error Brier over the six points.
    expected_brier = (0.10**2 + 0.40**2 + 0.65**2 + 0.80**2 + 0.30**2 + 0.10**2) / 6
    assert abs(report.brier - expected_brier) < 1e-12


def test_ks_matches_hand_computed_cdf_gap():
    # Scores are monotone in the label here, so at the split between negatives
    # and positives the positive CDF reaches 0 while the negative CDF reaches 1,
    # giving a maximum gap of 1.0.
    y_true = np.array([0, 0, 1, 1])
    y_score = np.array([0.2, 0.3, 0.6, 0.9])
    assert abs(ks_statistic(y_true, y_score) - 1.0) < 1e-12


def test_ks_bounded_when_score_carries_no_ranking():
    # Identical scores carry no ranking signal, so the statistic stays well
    # inside the unit interval rather than saturating at 1.0.
    y_true = np.array([0, 1, 0, 1])
    y_score = np.array([0.5, 0.5, 0.5, 0.5])
    ks = ks_statistic(y_true, y_score)
    assert 0.0 <= ks < 1.0
