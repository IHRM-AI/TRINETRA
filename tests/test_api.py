import numpy as np
import pandas as pd

from trinetra.api.service import ScoringService
from trinetra.genai.llm import GemmaClient
from trinetra.genai.memo import CreditMemoService
from trinetra.models.gbm import SegmentModel


def _service() -> ScoringService:
    rng = np.random.default_rng(1)
    x = pd.DataFrame(
        {
            "ltv": rng.uniform(50, 95, 500),
            "PERFORM_CNS.SCORE": rng.integers(300, 850, 500),
            "NO.OF_INQUIRIES": rng.integers(0, 10, 500),
        }
    )
    y = (x["ltv"] + x["NO.OF_INQUIRIES"] * 3 > 80).astype(int).to_numpy()
    model = SegmentModel(num_boost_round=80, early_stopping_rounds=20)
    model.fit(x.iloc[:350], y[:350], x.iloc[350:], y[350:])
    return ScoringService(model, CreditMemoService(llm=GemmaClient(base_url="")))


def test_service_scores_and_drafts_memo():
    service = _service()
    features = {"ltv": 92.0, "PERFORM_CNS.SCORE": 320, "NO.OF_INQUIRIES": 8}
    explanation = service.score(features)
    assert 0.0 <= explanation.pd_value <= 1.0
    assert explanation.grade in {"A", "B", "C", "D", "E"}

    memo = service.memo("Test Borrower", "1.0 Cr", features)
    assert memo.status == "Awaiting officer approval"
    assert "Test Borrower" in memo.body
