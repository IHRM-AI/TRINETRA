"""FastAPI TestClient coverage for the serving layer.

These tests inject an in-memory model so they run without the artifact or the
(git-ignored) L&T dataset present, matching the CI environment.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import trinetra.api.app as app_module
from trinetra.api.portfolio import PortfolioService
from trinetra.api.service import ScoringService
from trinetra.genai.llm import GemmaClient
from trinetra.genai.memo import CreditMemoService
from trinetra.models.gbm import SegmentModel


def _in_memory_service() -> ScoringService:
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


def _in_memory_portfolio(service: ScoringService) -> PortfolioService:
    # Exercise the real sample()/_rank_grades() code without touching disk by
    # populating the attributes those methods read.
    rng = np.random.default_rng(2)
    features = pd.DataFrame(
        {
            "ltv": rng.uniform(50, 95, 60),
            "PERFORM_CNS.SCORE": rng.integers(300, 850, 60),
            "NO.OF_INQUIRIES": rng.integers(0, 10, 60),
        }
    )
    portfolio = object.__new__(PortfolioService)
    portfolio._model = service._model
    portfolio._features = features
    portfolio._pd = service._model.predict_pd(features)
    return portfolio


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    service = _in_memory_service()
    # Point the artifact at an absent path so the lifespan handler is a no-op and
    # leaves the injected in-memory service in place, matching CI where neither
    # the artifact nor the dataset is present.
    monkeypatch.setattr(app_module, "_ARTIFACT", app_module._ARTIFACT.with_name("absent.joblib"))
    monkeypatch.setattr(app_module, "_service", service)
    monkeypatch.setattr(app_module, "_portfolio", _in_memory_portfolio(service))
    monkeypatch.setattr(app_module.settings, "api_key", "", raising=False)
    with TestClient(app_module.app) as test_client:
        yield test_client


def test_health_reports_model_loaded(client: TestClient) -> None:
    payload = client.get("/health").json()
    assert payload["status"] == "ok"
    assert payload["model_loaded"] is True
    assert "genai_available" in payload


def test_score_valid_input(client: TestClient) -> None:
    response = client.post(
        "/score",
        json={"features": {"ltv": 92.0, "PERFORM_CNS.SCORE": 320, "NO.OF_INQUIRIES": 8}},
    )
    assert response.status_code == 200
    body = response.json()
    assert 0.0 <= body["pd"] <= 1.0
    assert body["grade"] in {"A", "B", "C", "D", "E"}
    assert isinstance(body["reason_codes"], list)


def test_score_rejects_unknown_feature(client: TestClient) -> None:
    response = client.post("/score", json={"features": {"not_a_feature": 1}})
    assert response.status_code == 422
    assert "Unknown feature" in response.json()["detail"]


def test_score_rejects_empty_features(client: TestClient) -> None:
    response = client.post("/score", json={"features": {}})
    assert response.status_code == 422
    assert "No features" in response.json()["detail"]


def test_score_rejects_non_finite_value(client: TestClient) -> None:
    response = client.post(
        "/score",
        content='{"features": {"ltv": NaN}}',
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422
    assert "Non-finite" in response.json()["detail"]


def test_term_structure_valid_input(client: TestClient) -> None:
    response = client.post("/term-structure", json={"features": {"ltv": 90.0}})
    assert response.status_code == 200
    body = response.json()
    assert body["months"] == list(range(1, 13))
    assert "peak_month" in body


def test_portfolio_carries_synthetic_flag(client: TestClient) -> None:
    response = client.get("/portfolio?n=20")
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["synthetic"] is True
    assert body["summary"]["n"] == len(body["accounts"])


def test_portfolio_carries_next_action(client: TestClient) -> None:
    body = client.get("/portfolio?n=20").json()
    assert "action_counts" in body["summary"]
    for account in body["accounts"]:
        assert account["next_action"]
        assert account["action_reason"]
    graded_e = [a for a in body["accounts"] if a["grade"] == "E"]
    for account in graded_e:
        assert account["next_action"] == "Exit / RFA review"


def test_portfolio_pins_shared_lifecycle_account(client: TestClient) -> None:
    body = client.get("/portfolio?n=20").json()
    shared = [a for a in body["accounts"] if a["id"] == "sharma-kirana"]
    assert len(shared) == 1
    account = shared[0]
    assert account["name"] == "Sharma Kirana Store"
    assert account["grade"] == "D"
    assert account["pd"] > 0.15
    assert "SMA" in account["watch_tier"]
    assert "early-warning" in account["action_reason"]
    assert body["summary"]["n"] == len(body["accounts"])


def test_adverse_media_fixture_escalates(client: TestClient) -> None:
    response = client.post("/adverse-media", json={"borrower": "Shree Ganesh Textiles", "grade": "C"})
    assert response.status_code == 200
    body = response.json()
    assert body["escalate"] is True
    assert body["is_demo_fixture"] is True
    assert body["tier_escalation"] == "Watchlist"
    assert body["sources"]
    assert "separate from the PD model" in body["overlay_note"]


def test_adverse_media_degrades_when_unconfigured(client: TestClient) -> None:
    response = client.post("/adverse-media", json={"borrower": "Apex Auto Components"})
    assert response.status_code == 200
    body = response.json()
    assert body["escalate"] is False
    assert body["service_available"] is False


def test_adverse_media_rejects_empty_borrower(client: TestClient) -> None:
    response = client.post("/adverse-media", json={"borrower": "   "})
    assert response.status_code == 422


def test_extract_returns_demo_fixture_for_sample(client: TestClient) -> None:
    response = client.post(
        "/extract",
        files={"file": ("sample-acme.pdf", b"pdf-bytes", "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "demo fixture — OCR offline"
    assert body["service_available"] is False
    assert body["fields"]["name"] == "Acme Textiles Pvt Ltd"
    assert body["fields"]["PERFORM_CNS.SCORE"] == 612


def test_extract_honours_demo_flag(client: TestClient) -> None:
    response = client.post(
        "/extract",
        files={"file": ("statement.pdf", b"pdf-bytes", "application/pdf")},
        data={"demo": "true"},
    )
    assert response.status_code == 200
    assert response.json()["source"] == "demo fixture — OCR offline"


def test_extract_demo_flag_needs_no_file(client: TestClient) -> None:
    response = client.post("/extract", data={"demo": "true"})
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "demo fixture — OCR offline"
    assert body["fields"]["name"] == "Acme Textiles Pvt Ltd"


def test_extract_requires_file_without_demo(client: TestClient) -> None:
    response = client.post("/extract", data={"demo": "false"})
    assert response.status_code == 422


def test_extract_degrades_when_ocr_offline(client: TestClient) -> None:
    response = client.post(
        "/extract",
        files={"file": ("statement.pdf", b"pdf-bytes", "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["fields"] == {}
    assert body["service_available"] is False
    assert "offline" in body["message"].lower()


def test_extract_rejects_empty_file(client: TestClient) -> None:
    response = client.post(
        "/extract",
        files={"file": ("statement.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 422


def test_score_returns_503_when_model_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module, "_service", None)
    monkeypatch.setattr(app_module, "_portfolio", None)
    monkeypatch.setattr(app_module, "_ARTIFACT", app_module._ARTIFACT.with_name("absent.joblib"))
    monkeypatch.setattr(app_module.settings, "api_key", "", raising=False)
    with TestClient(app_module.app) as test_client:
        response = test_client.post("/score", json={"features": {"ltv": 90.0}})
        assert response.status_code == 503
        assert "not loaded" in response.json()["detail"]


def test_api_key_gate_enforced_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _in_memory_service()
    monkeypatch.setattr(app_module, "_ARTIFACT", app_module._ARTIFACT.with_name("absent.joblib"))
    monkeypatch.setattr(app_module, "_service", service)
    monkeypatch.setattr(app_module.settings, "api_key", "topsecret", raising=False)
    with TestClient(app_module.app) as test_client:
        rejected = test_client.post("/score", json={"features": {"ltv": 90.0}})
        assert rejected.status_code == 401
        accepted = test_client.post(
            "/score",
            json={"features": {"ltv": 90.0}},
            headers={"x-api-key": "topsecret"},
        )
        assert accepted.status_code == 200
