import pytest

from trinetra.genai.adverse_media import AdverseMediaOverlay
from trinetra.genai.news import FirecrawlClient, NewsItem


def test_unconfigured_client_degrades_without_escalating():
    overlay = AdverseMediaOverlay(FirecrawlClient(base_url=""))
    result = overlay.check("Apex Auto Components", grade="C")
    assert result.escalate is False
    assert result.service_available is False
    assert result.tier_escalation is None
    assert "unavailable" in result.summary.lower()


def test_unreachable_client_degrades_without_raising(monkeypatch):
    client = FirecrawlClient(base_url="https://firecrawl.internal")

    def _boom(*_args, **_kwargs):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(client, "search", _boom)
    result = AdverseMediaOverlay(client).check("Krishna Agro Foods", grade="D")
    assert result.escalate is False
    assert result.service_available is False


def test_demo_fixture_escalates_known_borrower():
    overlay = AdverseMediaOverlay(FirecrawlClient(base_url=""))
    result = overlay.check("Shree Ganesh Textiles", grade="C")
    assert result.is_demo_fixture is True
    assert result.escalate is True
    assert result.tier_escalation == "Watchlist"
    assert result.sources
    assert "demo" in result.summary.lower()


def test_demo_fixture_grade_d_escalates_to_rfa():
    overlay = AdverseMediaOverlay(FirecrawlClient(base_url=""))
    result = overlay.check("shree ganesh textiles", grade="D")
    assert result.tier_escalation == "RFA review"


def test_live_hits_are_filtered_to_adverse_terms(monkeypatch):
    client = FirecrawlClient(base_url="https://firecrawl.internal")
    hits = [
        NewsItem(url="https://x/1", title="Company wins export award", content="growth"),
        NewsItem(url="https://x/2", title="Firm named in loan fraud probe", content="alleged"),
    ]
    monkeypatch.setattr(client, "search", lambda *_a, **_k: hits)
    result = AdverseMediaOverlay(client).check("Some Borrower", grade="C")
    assert result.escalate is True
    assert len(result.sources) == 1
    assert result.sources[0].url == "https://x/2"


def test_no_adverse_terms_does_not_escalate(monkeypatch):
    client = FirecrawlClient(base_url="https://firecrawl.internal")
    clean = [NewsItem(url="https://x/1", title="Company opens new plant", content="expansion")]
    monkeypatch.setattr(client, "search", lambda *_a, **_k: clean)
    result = AdverseMediaOverlay(client).check("Clean Borrower", grade="C")
    assert result.escalate is False
    assert result.service_available is True
    assert "No adverse media found" in result.summary


def test_multiple_hits_are_summarised_with_a_count(monkeypatch):
    client = FirecrawlClient(base_url="https://firecrawl.internal")
    hits = [
        NewsItem(url="https://x/1", title="named in loan fraud probe", content=""),
        NewsItem(url="https://x/2", title="insolvency petition admitted", content=""),
    ]
    monkeypatch.setattr(client, "search", lambda *_a, **_k: hits)
    result = AdverseMediaOverlay(client).check("Borrower", grade="C")
    assert "+1 more" in result.summary


@pytest.mark.parametrize("grade,expected", [("A", "Watchlist"), ("E", "RFA review")])
def test_tier_escalation_by_grade(monkeypatch, grade, expected):
    client = FirecrawlClient(base_url="https://firecrawl.internal")
    hits = [NewsItem(url="https://x/2", title="named in fraud case", content="")]
    monkeypatch.setattr(client, "search", lambda *_a, **_k: hits)
    result = AdverseMediaOverlay(client).check("Borrower", grade=grade)
    assert result.tier_escalation == expected
