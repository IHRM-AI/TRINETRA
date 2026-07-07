from __future__ import annotations

from dataclasses import dataclass, field

from trinetra.genai.llm import GemmaClient
from trinetra.genai.news import NewsItem
from trinetra.genai.text import plain_text
from trinetra.interpret.reason_codes import Explanation

SYSTEM_PROMPT = (
    "You are a credit risk analyst at an Indian bank. Draft a concise, factual "
    "early-warning memo for a credit officer. Use only the supplied figures. Do "
    "not invent numbers. End with a recommended action. The officer approves or "
    "edits before any account action is taken. Write in plain prose with simple "
    "headings and hyphen bullets; do not use Markdown symbols such as asterisks or hashes."
)


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
            f"- {code.label} ({code.code}): {code.contribution_pp:+.1f}pp, {code.direction}"
            for code in explanation.reason_codes
        )

    def _prompt(self, borrower: str, exposure: str, explanation: Explanation, news: list[NewsItem]) -> str:
        lines = [
            f"Borrower: {borrower}",
            f"Exposure: {exposure}",
            f"Predicted 12-month PD: {explanation.pd_value:.1%}",
            f"Risk grade: {explanation.grade} ({explanation.watch_tier})",
            "Triggers fired:",
            self._reasons(explanation),
        ]
        if news:
            lines.append("Adverse-media signals:")
            lines.extend(f"- {item.title} ({item.url})" for item in news)
        return "\n".join(lines)

    def _template(self, borrower: str, exposure: str, explanation: Explanation, news: list[NewsItem]) -> str:
        parts = [
            f"Early-warning review: {borrower}",
            f"Exposure: {exposure}",
            f"Predicted 12-month probability of default: {explanation.pd_value:.1%} "
            f"(grade {explanation.grade}, {explanation.watch_tier}).",
            "Triggers fired:",
            self._reasons(explanation),
        ]
        if news:
            parts.append("Adverse-media signals:")
            parts.extend(f"- {item.title} ({item.url})" for item in news)
        parts.append(
            f"Recommended action: place on {explanation.watch_tier.lower()} and review "
            "within 15 days; obtain latest financials before any limit action."
        )
        return "\n".join(parts)
