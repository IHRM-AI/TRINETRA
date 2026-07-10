from __future__ import annotations

from typing import Protocol, runtime_checkable

import pandas as pd

from trinetra.features.ltfs import CATEGORICAL, NUMERIC

# The feature schema the segment model consumes. A feed adapter is contracted to
# emit a frame whose columns are a subset of this set; the booster treats any
# absent column as natively missing, so an adapter only maps the fields a given
# bank feed actually carries.
FEATURE_SCHEMA: tuple[str, ...] = tuple(
    NUMERIC
    + [
        "identity_completeness",
        "overdue_ratio",
        "active_ratio",
        "primary_utilization",
        "disbursed_to_asset",
        "no_bureau_history",
    ]
    + CATEGORICAL
)


@runtime_checkable
class FeedAdapter(Protocol):
    """Maps one bank source feed onto the model feature schema.

    A bank integrates by implementing this protocol against its own Core Banking
    System, bureau pull, GST return or Account Aggregator export. The rest of the
    stack — model, calibration, reason codes, serving — is unchanged; onboarding
    a new feed is an adapter (a config change), not a rebuild.

    Implementations must:
      - name the source system via :attr:`source`;
      - accept a raw frame in the bank's native column names and return a frame
        whose columns are a subset of :data:`FEATURE_SCHEMA`;
      - be pure and row-order-preserving, so a scored row maps back to its
        source record by position.
    """

    source: str

    def to_features(self, raw: pd.DataFrame) -> pd.DataFrame:
        """Return model-ready features derived from a raw source frame."""
        ...


def validate_schema(features: pd.DataFrame) -> pd.DataFrame:
    """Reject adapter output that carries columns outside the feature schema.

    Absent columns are allowed (handled as natively missing by the booster);
    unexpected columns signal a mapping bug and are surfaced early.
    """
    unknown = sorted(set(features.columns) - set(FEATURE_SCHEMA))
    if unknown:
        raise ValueError(f"Adapter emitted unknown feature column(s): {', '.join(unknown)}")
    return features
