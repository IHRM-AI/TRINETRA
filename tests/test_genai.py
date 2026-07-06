import pytest

from trinetra.genai.llm import GemmaClient
from trinetra.genai.memo import CreditMemoService
from trinetra.interpret.reason_codes import Explanation, ReasonCode


def _explanation() -> Explanation:
    return Explanation(
        pd_value=0.229,
        grade="E",
        watch_tier="Watchlist / RFA review",
        reason_codes=[
            ReasonCode("EWS-C01", "High loan-to-value", 9.2, "increases risk"),
            ReasonCode("EWS-E01", "Frequent credit enquiries", 6.1, "increases risk"),
        ],
    )


def test_offline_client_is_unavailable():
    client = GemmaClient(base_url="")
    assert client.available is False
    with pytest.raises(RuntimeError):
        client.complete("s", "u")


def test_memo_falls_back_to_template_when_llm_offline():
    service = CreditMemoService(llm=GemmaClient(base_url=""))
    memo = service.draft("Shree Ganesh Textiles", "8.4 Cr", _explanation())
    assert memo.status == "Awaiting officer approval"
    assert "template" in memo.generated_by
    assert "22.9%" in memo.body
    assert "EWS-C01" in memo.body
