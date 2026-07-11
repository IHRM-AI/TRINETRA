from __future__ import annotations

from dataclasses import dataclass, field

from trinetra.genai.llm import GemmaClient
from trinetra.genai.news import NewsItem
from trinetra.genai.text import plain_text
from trinetra.interpret.reason_codes import Explanation

SYSTEM_PROMPT = (
    "You are a senior credit-risk analyst at an Indian bank drafting a formal "
    "early-warning credit memo for the credit officer's file. Use only the supplied "
    "figures; never invent numbers. Produce a structured memo with these numbered "
    "sections: 1. Facility summary; 2. Risk assessment; 3. Key risk drivers; "
    "4. Adverse media (omit if none supplied); 5. Recommended action; 6. Conditions "
    "and next review. Write in professional prose, two to four sentences per section, "
    "with hyphen bullets for lists. Interpret the probability of default and the "
    "RBI-EWS triggers for the officer rather than merely restating them. Close by "
    "noting the memo is model-assisted and requires officer approval. Do not use "
    "Markdown symbols such as asterisks or hashes."
)

_WATCH_REVIEW_DAYS = ((("rfa", "watchlist"), 15), (("watchlist",), 30), (("monitor",), 90))


def _pd_narrative(pd_value: float) -> str:
    if pd_value >= 0.35:
        return (
            "This is a materially elevated default risk that sits well above the "
            "performing-book norm and calls for prompt intervention"
        )
    if pd_value >= 0.15:
        return "This is an elevated default risk that warrants active, near-term monitoring"
    return "This is within the standard range, though the drivers below merit attention"


def _review_days(watch_tier: str) -> int:
    tier = watch_tier.lower()
    for keys, days in _WATCH_REVIEW_DAYS:
        if any(k in tier for k in keys):
            return days
    return 365


def _action_narrative(watch_tier: str) -> list[str]:
    tier = watch_tier.lower()
    if "rfa" in tier:
        return [
            "- Place the account on the RFA (red-flagged account) register and escalate to the early-warning committee.",
            "- Restrict any enhancement or fresh disbursement pending a fresh appraisal.",
            "- Assess collateral cover and explore restructuring, additional security, or a phased exit.",
        ]
    if "watchlist" in tier:
        return [
            "- Move the account to the active watchlist and increase the review cadence.",
            "- Run a covenant and end-use check, and confirm the security position is current.",
            "- Hold facility limits at the existing level until the next review clears the flags.",
        ]
    if "monitor" in tier:
        return [
            "- Apply enhanced monitoring and re-confirm the borrower's cash-flow position.",
            "- Review at the next scheduled cycle unless a trigger deteriorates further.",
        ]
    return ["- Continue standard annual review; no immediate action indicated by the current signals."]


@dataclass(frozen=True)
class CreditMemo:
    borrower: str
    body: str
    status: str
    generated_by: str
    sources: list[str] = field(default_factory=list)


class CreditMemoService:
    def __init__(self, llm: GemmaClient | None = None):
        self._llm = llm or GemmaClient()

    def draft(
        self,
        borrower: str,
        exposure: str,
        explanation: Explanation,
        news: list[NewsItem] | None = None,
    ) -> CreditMemo:
        news = news or []
        body = self._template(borrower, exposure, explanation, news)
        generated_by = "deterministic template (LLM offline)"
        if self._llm.available:
            try:
                body = plain_text(
                    self._llm.complete(
                        SYSTEM_PROMPT, self._prompt(borrower, exposure, explanation, news)
                    )
                )
                generated_by = f"Gemma-4 ({self._llm.model})"
            except Exception:
                generated_by = "deterministic template (LLM unreachable)"
        return CreditMemo(
            borrower=borrower,
            body=body,
            status="Awaiting officer approval",
            generated_by=generated_by,
            sources=[item.url for item in news if item.url],
        )

    @staticmethod
    def _reasons(explanation: Explanation) -> str:
        return "\n".join(
            f"- {code.label} ({code.code}): {code.direction} "
            f"(SHAP log-odds margin {code.contribution_logodds:+.3f})"
            for code in explanation.reason_codes
        )

    def _prompt(self, borrower: str, exposure: str, explanation: Explanation, news: list[NewsItem]) -> str:
        lines = [
            f"Borrower: {borrower}",
            f"Current exposure: {exposure}",
            f"Predicted 12-month probability of default: {explanation.pd_value:.1%}",
            f"Risk grade: {explanation.grade}; monitoring status: {explanation.watch_tier}",
            f"Suggested next review window: {_review_days(explanation.watch_tier)} days",
            "RBI-EWS triggers fired (SHAP log-odds margin; sign gives direction):",
            self._reasons(explanation),
        ]
        if news:
            lines.append("Adverse-media signals (rules-based overlay, separate from the PD model):")
            lines.extend(f"- {item.title} ({item.url})" for item in news)
        return "\n".join(lines)

    def _template(self, borrower: str, exposure: str, explanation: Explanation, news: list[NewsItem]) -> str:
        top = explanation.reason_codes[0].label.lower() if explanation.reason_codes else None
        review_days = _review_days(explanation.watch_tier)
        parts = [
            "EARLY-WARNING CREDIT MEMO",
            "",
            "1. Facility summary",
            f"Borrower: {borrower}",
            f"Current exposure: {exposure}",
            f"Risk grade: {explanation.grade}  |  Monitoring status: {explanation.watch_tier}",
            "",
            "2. Risk assessment",
            f"The segment model places the 12-month probability of default at "
            f"{explanation.pd_value:.1%}. {_pd_narrative(explanation.pd_value)}. On the internal "
            f"scale this maps to grade {explanation.grade}, monitored under the "
            f"{explanation.watch_tier} track.",
            "",
            "3. Key risk drivers",
            "Ranked by contribution to the score, mapped to the RBI early-warning trigger "
            "taxonomy. Sign gives direction; magnitude ranks the driver (SHAP log-odds margin):",
            self._reasons(explanation),
        ]
        if top:
            parts.append(
                f"The score is led by {top}, alongside the further triggers listed above."
            )
        parts += ["", "4. Adverse media"]
        if news:
            parts += [
                *(f"- {item.title}" for item in news),
                "An adverse-media overlay has flagged the borrower. This signal is rules-based "
                "and sits outside the PD model; on its own it warrants tighter monitoring.",
            ]
        else:
            parts.append(
                "No adverse media flagged by the overlay at the time of this review."
            )
        parts += [
            "",
            "5. Recommended action",
            *_action_narrative(explanation.watch_tier),
            "",
            "6. Conditions and next review",
            "- Obtain the latest audited or provisional financials and recent GST returns "
            "before any limit or facility decision.",
            "- Confirm the security position and end-use of existing facilities.",
            f"- Next early-warning review: within {review_days} days.",
            "",
            "This memo is model-assisted and requires credit-officer approval. TRINETRA "
            "augments the existing early-warning system; it does not take account action "
            "autonomously.",
        ]
        return "\n".join(parts)
