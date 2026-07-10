from __future__ import annotations

import numpy as np

from trinetra.config import settings
from trinetra.data import ltfs
from trinetra.features import ltfs as ltfs_features
from trinetra.models.gbm import SegmentModel

# Risk-rank the monitored book into grades. Proportions reflect a managed MSME
# portfolio: mostly standard, a small watchlist tail.
GRADE_MIX = [
    (0.40, "A", "Standard"),
    (0.30, "B", "Standard"),
    (0.17, "C", "Monitor"),
    (0.09, "D", "Watchlist"),
    (0.04, "E", "Watchlist / RFA review"),
]

SECTORS = [
    "Textiles", "Auto components", "Pharma", "Agro processing", "Steel fabrication",
    "Logistics", "Light engineering", "Gems & jewellery", "Food processing",
    "Chemicals", "Plastics", "Electronics",
]
ZONES = [
    "Mumbai", "Pune", "Ahmedabad", "Nashik", "Nagpur", "Hyderabad", "Coimbatore",
    "Kochi", "Surat", "Ludhiana", "Indore", "Jaipur",
]
PREFIX = [
    "Shree", "Sri", "National", "Apex", "Prime", "United", "Bharat", "Royal", "Star",
    "Ganesh", "Krishna", "Laxmi", "Deccan", "Rathod", "Vasant", "Meenakshi", "Sagar",
    "Gupta", "Verma", "Patel", "Reddy", "Nair",
]
SUFFIX = [
    "Textiles", "Auto Components", "Industries", "Enterprises", "Trading Co", "Exports",
    "Fabricators", "Agro Foods", "Engineering", "Steels", "Logistics", "Traders",
    "Mills", "Products", "Pvt Ltd",
]


def _clean(value: object) -> object:
    if isinstance(value, float) and np.isnan(value):
        return None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    return value if isinstance(value, (int, float, str)) else str(value)


class PortfolioService:
    def __init__(self, model: SegmentModel):
        self._model = model
        raw = ltfs.parse(ltfs.load_raw(settings.data_dir))
        self._features = ltfs_features.build(raw).reset_index(drop=True)
        self._pd = model.predict_pd(self._features)

    def _rank_grades(self, pd_values: np.ndarray) -> tuple[list[str], list[str]]:
        order = np.argsort(pd_values)
        grades = [""] * len(pd_values)
        tiers = [""] * len(pd_values)
        start = 0
        cumulative = 0.0
        for fraction, grade, tier in GRADE_MIX:
            cumulative += fraction
            stop = int(round(cumulative * len(pd_values)))
            for position in order[start:stop]:
                grades[position], tiers[position] = grade, tier
            start = stop
        for position in order[start:]:
            grades[position], tiers[position] = GRADE_MIX[-1][1], GRADE_MIX[-1][2]
        return grades, tiers

    def sample(self, n: int = 200, seed: int = 7) -> dict[str, object]:
        rng = np.random.default_rng(seed)
        size = min(n, len(self._features))
        picked = rng.choice(len(self._features), size=size, replace=False)
        frame = self._features.iloc[picked].reset_index(drop=True)
        pd_values = self._pd[picked]
        grades, tiers = self._rank_grades(pd_values)

        accounts: list[dict[str, object]] = []
        for position in range(size):
            grade, tier = grades[position], tiers[position]
            exposure_cr = round(float(np.clip(rng.lognormal(0.9, 0.7), 0.4, 30)), 1)
            accounts.append(
                {
                    "id": f"acc-{int(picked[position])}",
                    "name": f"{PREFIX[rng.integers(len(PREFIX))]} {SUFFIX[rng.integers(len(SUFFIX))]}",
                    "sector": SECTORS[rng.integers(len(SECTORS))],
                    "region": f"{ZONES[rng.integers(len(ZONES))]} Zonal",
                    "account": f"A/c {100000 + int(picked[position])}",
                    "exposure_cr": exposure_cr,
                    "pd": round(float(pd_values[position]), 4),
                    "grade": grade,
                    "watch_tier": tier,
                    "features": {key: _clean(frame.at[position, key]) for key in frame.columns},
                }
            )

        accounts.sort(key=lambda account: -account["pd"])
        high_risk = [a for a in accounts if a["grade"] in {"D", "E"}]
        summary = {
            "n": len(accounts),
            "total_exposure_cr": round(sum(a["exposure_cr"] for a in accounts), 1),
            "high_risk": len(high_risk),
            "exposure_at_risk_cr": round(sum(a["exposure_cr"] for a in high_risk), 1),
            "synthetic": True,
            "note": (
                "Names, sectors, regions and exposures are illustrative demo data. "
                "Only the probability of default is model-derived, scored on the "
                "public L&T vehicle-finance dataset."
            ),
        }
        return {"accounts": accounts, "summary": summary}
