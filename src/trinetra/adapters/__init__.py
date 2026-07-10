"""Feed adapters: map a bank's raw source schema to the model feature schema.

A bank plugs its own feed in by supplying a :class:`FeedAdapter`. The adapter is
the only integration surface — the model, serving layer and interpretation layer
are untouched. See ``docs/integration.md`` for the day-1 integration path.
"""

from trinetra.adapters.base import FEATURE_SCHEMA, FeedAdapter
from trinetra.adapters.ltfs import LtfsFeedAdapter

__all__ = ["FEATURE_SCHEMA", "FeedAdapter", "LtfsFeedAdapter"]
