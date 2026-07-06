from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Trigger:
    code: str
    label: str
    higher_is_worse: bool


# Feature-to-trigger mapping aligned to RBI Early-Warning-Signal vocabulary.
# One shared vocabulary is applied across every segment model so that reason
# codes read identically regardless of which model produced the score.
TRIGGERS: dict[str, Trigger] = {
    "PERFORM_CNS.SCORE": Trigger("EWS-B01", "Bureau score deterioration", higher_is_worse=False),
    "no_bureau_history": Trigger("EWS-B02", "New-to-credit / no bureau record", higher_is_worse=True),
    "overdue_ratio": Trigger("EWS-B03", "Overdue accounts on bureau", higher_is_worse=True),
    "PRI.OVERDUE.ACCTS": Trigger("EWS-B03", "Overdue accounts on bureau", higher_is_worse=True),
    "DELINQUENT.ACCTS.IN.LAST.SIX.MONTHS": Trigger("EWS-B04", "Recent delinquencies (6 months)", higher_is_worse=True),
    "primary_utilization": Trigger("EWS-U01", "High utilisation of sanctioned limits", higher_is_worse=True),
    "NO.OF_INQUIRIES": Trigger("EWS-E01", "Frequent credit enquiries", higher_is_worse=True),
    "NEW.ACCTS.IN.LAST.SIX.MONTHS": Trigger("EWS-E02", "Rapid new-account opening", higher_is_worse=True),
    "credit_history_months": Trigger("EWS-H01", "Thin credit history", higher_is_worse=False),
    "ltv": Trigger("EWS-C01", "High loan-to-value", higher_is_worse=True),
    "disbursed_to_asset": Trigger("EWS-C02", "High financing ratio", higher_is_worse=True),
    "identity_completeness": Trigger("EWS-K01", "Incomplete KYC identity set", higher_is_worse=False),
    "active_ratio": Trigger("EWS-B05", "Share of active credit lines", higher_is_worse=True),
}


# Predicted 12-month PD bands. Grades mirror the portfolio heatmap and map to a
# watch tier; true SMA-0/1/2 staging is driven by days-past-due in production.
GRADE_BANDS: list[tuple[float, str, str]] = [
    (0.02, "A", "Standard"),
    (0.05, "B", "Standard"),
    (0.10, "C", "Monitor"),
    (0.15, "D", "Watchlist"),
    (1.01, "E", "Watchlist / RFA review"),
]


def grade_for(pd_value: float) -> tuple[str, str]:
    for upper, grade, tier in GRADE_BANDS:
        if pd_value < upper:
            return grade, tier
    return GRADE_BANDS[-1][1], GRADE_BANDS[-1][2]
