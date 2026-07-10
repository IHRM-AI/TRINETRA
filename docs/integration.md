# Day-1 integration

TRINETRA is designed to sit beside a bank's existing systems, not replace them.
A bank plugs its own data in through a **feed adapter** — a small mapping class —
and the rest of the stack (model, calibration, reason codes, serving) is
untouched. Onboarding a new source is a config change, not a rebuild.

## The one integration surface

Every raw feed is mapped onto a single, stable feature schema that the segment
model consumes. That mapping is the only code a bank writes. The contract lives
in [`src/trinetra/adapters/base.py`](../src/trinetra/adapters/base.py):

```python
@runtime_checkable
class FeedAdapter(Protocol):
    source: str

    def to_features(self, raw: pd.DataFrame) -> pd.DataFrame:
        ...
```

An adapter takes a raw frame in the bank's native column names and returns a
frame whose columns are a subset of `FEATURE_SCHEMA`. Fields the feed does not
carry are simply left out — the gradient booster treats absent columns as
natively missing, so a partial feed still scores. Emitting a column outside the
schema is rejected early by `validate_schema`, so mapping bugs surface at
onboarding rather than in production.

## Reference adapter

[`src/trinetra/adapters/ltfs.py`](../src/trinetra/adapters/ltfs.py) is a working
adapter for the public L&T vehicle-finance feed. It reuses the same parse and
feature-build steps the training pipeline runs, so a row scored through the
adapter is identical to a row scored in training. A bank writes one adapter of
this shape against its own export.

## Where each bank feed maps in

| Bank source | System | What the adapter maps |
|---|---|---|
| Core Banking System (CBS) | Finacle / Flexcube / BaNCS | Limits, balances, utilisation, disbursal and instalment fields |
| Credit bureau | CIBIL / Experian / CRIF | Score, enquiries, overdue and delinquent account counts, history length |
| GST returns | GSTN | Turnover trend and filing regularity as derived ratios |
| Account Aggregator | Sahamati AA | Bank-statement-derived cashflow and balance features |
| Existing EWS | In-house rule engine (~80 triggers) | Trigger states carried in as features and shared reason-code vocabulary |

The existing EWS is ingested as features and shared vocabulary, so TRINETRA
extends the current early-warning process rather than bypassing it.

## Steps to onboard a feed

1. Write a class implementing `FeedAdapter` for the source, mapping raw columns
   to schema columns and deriving any ratios (see `LtfsFeedAdapter`).
2. Run the adapter output through `validate_schema` (called for you in the
   reference adapter) to confirm the mapping stays within the feature schema.
3. Retrain the segment on the bank's own book in the sandbox — the model,
   calibration and reason-code layers are unchanged.
4. Serve as usual; the FastAPI layer and cockpit need no changes.

## What does not change

The model, isotonic calibration, SHAP-to-RBI-EWS reason codes, PD term
structure, serving API and cockpit are all source-agnostic. Adding a bank feed
touches the adapter layer only.
