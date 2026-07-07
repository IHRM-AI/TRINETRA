import numpy as np

from trinetra.eval.benchmark import capture_at, capture_curve


def test_perfect_ranking_captures_all_defaulters():
    y = np.array([0, 0, 0, 1, 1])
    score = np.array([0.1, 0.2, 0.3, 0.9, 0.95])
    assert capture_at(y, score, 0.4) == 1.0


def test_capture_is_monotone_in_flag_rate():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, size=400)
    score = rng.random(400)
    curve = [point["capture"] for point in capture_curve(y, score, [0.1, 0.2, 0.4, 0.8])]
    assert curve == sorted(curve)


def test_no_defaults_returns_zero():
    assert capture_at(np.zeros(10), np.random.default_rng(0).random(10), 0.2) == 0.0
