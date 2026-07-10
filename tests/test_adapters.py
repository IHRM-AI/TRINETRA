import pandas as pd
import pytest

from trinetra.adapters import FEATURE_SCHEMA, FeedAdapter, LtfsFeedAdapter
from trinetra.adapters.base import validate_schema


def _raw_ltfs_row() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "disbursed_amount": 84000000,
                "asset_cost": 64000000,
                "ltv": 0.91,
                "PERFORM_CNS.SCORE": 604,
                "PRI.NO.OF.ACCTS": 11,
                "PRI.ACTIVE.ACCTS": 9,
                "PRI.OVERDUE.ACCTS": 4,
                "PRI.CURRENT.BALANCE": 58000000,
                "PRI.SANCTIONED.AMOUNT": 62000000,
                "PRI.DISBURSED.AMOUNT": 62000000,
                "SEC.NO.OF.ACCTS": 0,
                "SEC.ACTIVE.ACCTS": 0,
                "SEC.OVERDUE.ACCTS": 0,
                "PRIMARY.INSTAL.AMT": 120000,
                "NEW.ACCTS.IN.LAST.SIX.MONTHS": 3,
                "DELINQUENT.ACCTS.IN.LAST.SIX.MONTHS": 2,
                "NO.OF_INQUIRIES": 4,
                "Aadhar_flag": 1,
                "PAN_flag": 1,
                "VoterID_flag": 0,
                "Driving_flag": 0,
                "Passport_flag": 0,
                "Employment.Type": "Self employed",
                "State_ID": 4,
                "manufacturer_id": 45,
                "Date.of.Birth": "01-01-77",
                "DisbursalDate": "01-06-18",
                "AVERAGE.ACCT.AGE": "3yrs 4mon",
                "CREDIT.HISTORY.LENGTH": "9yrs 4mon",
            }
        ]
    )


def test_reference_adapter_satisfies_the_protocol():
    adapter = LtfsFeedAdapter()
    assert isinstance(adapter, FeedAdapter)
    assert adapter.source


def test_reference_adapter_emits_schema_subset():
    features = LtfsFeedAdapter().to_features(_raw_ltfs_row())
    assert len(features) == 1
    assert set(features.columns).issubset(set(FEATURE_SCHEMA))
    assert features.at[0, "ltv"] == pytest.approx(0.91)
    assert features.at[0, "overdue_ratio"] == pytest.approx(4 / 11)


def test_validate_schema_rejects_unknown_columns():
    bad = pd.DataFrame({"ltv": [0.9], "not_a_feature": [1]})
    with pytest.raises(ValueError, match="unknown feature column"):
        validate_schema(bad)


def test_validate_schema_allows_subset():
    ok = pd.DataFrame({"ltv": [0.9], "overdue_ratio": [0.3]})
    assert validate_schema(ok) is ok
