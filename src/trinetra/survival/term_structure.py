"""Heuristic PD term-structure allocator.

This is not a fitted survival model. The available loan-level datasets carry a
single binary 12-month default label with no month-of-default or time-to-event
field, so a genuine discrete-time hazard model cannot be estimated from them.
Instead, the 12-month PD produced by the segment model is spread across months
by a fixed Gaussian-hazard weight profile whose peak shifts earlier as stress
signals rise; the monthly marginals integrate back to the 12-month PD. A fitted
discrete-time hazard model is tracked as roadmap work in the README.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

HORIZON = 12


@dataclass(frozen=True)
class TermStructure:
    months: list[int]
    marginal_pd: list[float]
    cumulative_pd: list[float]
    peak_month: int


def _hazard_weights(peak_month: float, n: int = HORIZON) -> np.ndarray:
    months = np.arange(1, n + 1)
    shape = np.exp(-0.5 * ((months - peak_month) / 2.2) ** 2)
    return shape / shape.sum()


def peak_month(features: dict[str, float]) -> int:
    """Earlier stress peak when utilisation and delinquency signals are high."""
    utilisation = float(features.get("primary_utilization", 0.5))
    overdue = float(features.get("overdue_ratio", 0.0))
    enquiries = float(features.get("NO.OF_INQUIRIES", 0.0))
    stress = np.clip(0.5 * utilisation + 0.3 * overdue + 0.02 * enquiries, 0.0, 1.0)
    return int(round(np.interp(stress, [0.0, 1.0], [9, 4])))


def build(pd_12m: float, features: dict[str, float]) -> TermStructure:
    """Heuristically decompose a 12-month PD into a monthly marginal-default curve.

    The total cumulative hazard implied by the 12-month PD is distributed across
    months by a fixed peaked weight profile, then converted to per-month marginal
    default probabilities. The curve integrates back to the 12-month PD. The
    weights are hand-set, not estimated; see the module docstring.
    """
    pd_12m = float(np.clip(pd_12m, 1e-4, 0.999))
    peak = peak_month(features)
    total_hazard = -np.log(1 - pd_12m)
    monthly_hazard = total_hazard * _hazard_weights(peak)

    survival = np.concatenate([[1.0], np.cumprod(np.exp(-monthly_hazard))])[:-1]
    marginal = survival * (1 - np.exp(-monthly_hazard))
    cumulative = np.cumsum(marginal)
    return TermStructure(
        months=list(range(1, HORIZON + 1)),
        marginal_pd=[round(float(v), 5) for v in marginal],
        cumulative_pd=[round(float(v), 5) for v in cumulative],
        peak_month=peak,
    )
