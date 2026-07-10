from __future__ import annotations

from dataclasses import dataclass, field

from trinetra.genai.news import FirecrawlClient, NewsItem

# Keywords that qualify a search hit as adverse. The overlay is a rules-based
# screen, not a model: a borrower is escalated only when a hit contains one of
# these terms, and the escalation is a deterministic tier bump applied on top of
# the PD grade.
ADVERSE_TERMS = (
    "fraud",
    "default",
    "insolvency",
    "bankruptcy",
    "wilful defaulter",
    "wilful default",
    "loan fraud",
    "money laundering",
    "ed raid",
    "cbi",
    "scam",
    "diversion of funds",
    "shell company",
    "gst evasion",
    "auditor resignation",
    "sfio",
    "nclt",
)

# Tier escalations applied when adverse media is confirmed. Keyed on the PD
# grade; the overlay never lowers a tier, it only raises the watch stance.
TIER_ESCALATION = {
    "A": "Watchlist",
    "B": "Watchlist",
    "C": "Watchlist",
    "D": "RFA review",
    "E": "RFA review",
}


@dataclass(frozen=True)
class AdverseMediaResult:
    borrower: str
    escalate: bool
    summary: str
    tier_escalation: str | None = None
    is_demo_fixture: bool = False
    service_available: bool = True
    sources: list[NewsItem] = field(default_factory=list)


# Deterministic demo fixture. Firecrawl runs on a VPN-only instance that is not
# reachable from every demo environment, so one known borrower returns a canned,
# clearly labelled adverse-media hit. This keeps the overlay demonstrable when
# the live service is unreachable and is never presented as a live result. The
# portfolio pins its highest-risk account to this name so the overlay is one
# click away in the cockpit.
DEMO_BORROWER = "Shree Ganesh Textiles"

DEMO_FIXTURE: dict[str, list[NewsItem]] = {
    DEMO_BORROWER.lower(): [
        NewsItem(
            url="https://demo.trinetra.local/adverse/shree-ganesh-textiles",
            title="Shree Ganesh Textiles named in loan-fraud probe (labelled demo fixture)",
            content=(
                "Demo fixture. Lenders flag alleged diversion of working-capital "
                "funds and a pending wilful-defaulter classification."
            ),
        ),
    ],
}


def _is_adverse(item: NewsItem) -> bool:
    haystack = f"{item.title} {item.content}".lower()
    return any(term in haystack for term in ADVERSE_TERMS)


def _summarise(borrower: str, hits: list[NewsItem]) -> str:
    lead = hits[0].title.strip()
    if len(hits) == 1:
        return f"Adverse media for {borrower}: {lead}"
    return f"Adverse media for {borrower}: {lead} (+{len(hits) - 1} more)"


class AdverseMediaOverlay:
    """Rules-based adverse-media screen, separate from the PD model.

    A confirmed hit escalates the borrower's watch tier and raises an alert; it
    does not enter the PD model or alter the score. When Firecrawl is unreachable
    or unconfigured the overlay degrades to a clean "no adverse media / service
    unavailable" result rather than raising.
    """

    def __init__(self, client: FirecrawlClient | None = None):
        self._client = client or FirecrawlClient()

    def check(self, borrower: str, grade: str = "C", limit: int = 5) -> AdverseMediaResult:
        fixture = DEMO_FIXTURE.get(borrower.strip().lower())
        if fixture is not None:
            adverse = [item for item in fixture if _is_adverse(item)]
            return AdverseMediaResult(
                borrower=borrower,
                escalate=bool(adverse),
                summary=_summarise(borrower, adverse),
                tier_escalation=TIER_ESCALATION.get(grade, "Watchlist") if adverse else None,
                is_demo_fixture=True,
                service_available=True,
                sources=adverse,
            )

        if not self._client.available:
            return AdverseMediaResult(
                borrower=borrower,
                escalate=False,
                summary="No adverse media (screen unavailable — Firecrawl not configured).",
                service_available=False,
            )

        try:
            hits = self._client.search(f"{borrower} fraud default insolvency", limit=limit)
        except Exception:
            return AdverseMediaResult(
                borrower=borrower,
                escalate=False,
                summary="No adverse media (screen unavailable — Firecrawl unreachable).",
                service_available=False,
            )

        adverse = [item for item in hits if _is_adverse(item)]
        if not adverse:
            return AdverseMediaResult(
                borrower=borrower,
                escalate=False,
                summary=f"No adverse media found for {borrower}.",
                service_available=True,
            )

        return AdverseMediaResult(
            borrower=borrower,
            escalate=True,
            summary=_summarise(borrower, adverse),
            tier_escalation=TIER_ESCALATION.get(grade, "Watchlist"),
            service_available=True,
            sources=adverse,
        )
