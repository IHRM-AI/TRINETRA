from __future__ import annotations

import pandas as pd

from trinetra.adapters.base import validate_schema
from trinetra.data import ltfs as ltfs_data
from trinetra.features import ltfs as ltfs_features


class LtfsFeedAdapter:
    """Reference adapter for the L&T vehicle-finance feed (public data path).

    Maps the raw L&T disbursal-and-bureau schema onto the model feature schema by
    reusing the same parse and feature-build steps the training pipeline runs, so
    a row scored through the adapter is identical to a row scored in training.
    A bank writes one adapter of this shape against its own CBS or bureau export.
    """

    source = "L&T / LTFS vehicle finance"

    def to_features(self, raw: pd.DataFrame) -> pd.DataFrame:
        parsed = ltfs_data.parse(raw)
        features = ltfs_features.build(parsed).reset_index(drop=True)
        return validate_schema(features)
