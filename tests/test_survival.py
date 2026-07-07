import numpy as np

from trinetra.survival.term_structure import HORIZON, build, peak_month


def test_curve_integrates_to_pd():
    ts = build(0.24, {"primary_utilization": 0.9, "overdue_ratio": 0.3, "NO.OF_INQUIRIES": 4})
    assert len(ts.marginal_pd) == HORIZON
    assert abs(ts.cumulative_pd[-1] - 0.24) < 0.01
    assert ts.cumulative_pd == sorted(ts.cumulative_pd)


def test_stress_pulls_peak_earlier():
    calm = peak_month({"primary_utilization": 0.1, "overdue_ratio": 0.0, "NO.OF_INQUIRIES": 0})
    stressed = peak_month({"primary_utilization": 1.0, "overdue_ratio": 0.6, "NO.OF_INQUIRIES": 8})
    assert stressed < calm
    assert 4 <= stressed <= 9 and 4 <= calm <= 9


def test_marginal_curve_is_non_negative():
    ts = build(0.5, {"primary_utilization": 0.5})
    assert all(value >= 0 for value in ts.marginal_pd)
    # Survival decay shifts the marginal peak up to one month before the hazard peak.
    assert abs((int(np.argmax(ts.marginal_pd)) + 1) - ts.peak_month) <= 1
