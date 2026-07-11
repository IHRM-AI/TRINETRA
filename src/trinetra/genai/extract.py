from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from trinetra.config import settings
from trinetra.genai.ocr import OcrClient

# Fields the "Score a new account" form accepts. Keys match the payload the
# cockpit builds in NewBorrowerForm.tsx exactly, so an extracted dict can be
# merged into the form state without any remapping. Text fields (name, sector)
# and the numeric feature fields are parsed by labelled patterns from OCR text.
NUMERIC_FIELDS: dict[str, tuple[str, ...]] = {
    "PERFORM_CNS.SCORE": (
        "bureau score",
        "cibil score",
        "cns score",
        "credit score",
    ),
    "ltv": (
        "loan to value",
        "loan-to-value",
        "ltv",
    ),
    "primary_utilization": (
        "limit utilisation",
        "limit utilization",
        "utilisation",
        "utilization",
    ),
    "PRI.OVERDUE.ACCTS": (
        "overdue accounts",
        "overdue accts",
        "accounts overdue",
    ),
    "DELINQUENT.ACCTS.IN.LAST.SIX.MONTHS": (
        "delinquencies",
        "delinquent accounts",
        "delinquent accts",
    ),
    "NO.OF_INQUIRIES": (
        "bureau enquiries",
        "bureau inquiries",
        "credit enquiries",
        "credit inquiries",
        "enquiries",
        "inquiries",
    ),
    "age_years": (
        "promoter age",
        "director age",
        "age of promoter",
    ),
    "credit_history_months": (
        "credit history",
        "vintage",
        "history length",
    ),
}

# Bounds mirror the form's stated ranges. A parsed value outside its range is
# treated as a mis-read and dropped, so the officer never sees an implausible
# pre-fill silently accepted.
NUMERIC_BOUNDS: dict[str, tuple[float, float]] = {
    "PERFORM_CNS.SCORE": (300.0, 900.0),
    "ltv": (0.0, 1.0),
    "primary_utilization": (0.0, 1.2),
    "PRI.OVERDUE.ACCTS": (0.0, 999.0),
    "DELINQUENT.ACCTS.IN.LAST.SIX.MONTHS": (0.0, 999.0),
    "NO.OF_INQUIRIES": (0.0, 999.0),
    "age_years": (18.0, 100.0),
    "credit_history_months": (0.0, 1200.0),
}

INTEGER_FIELDS = frozenset(
    {
        "PERFORM_CNS.SCORE",
        "PRI.OVERDUE.ACCTS",
        "DELINQUENT.ACCTS.IN.LAST.SIX.MONTHS",
        "NO.OF_INQUIRIES",
        "age_years",
        "credit_history_months",
    }
)

_NUMBER = r"([0-9]+(?:\.[0-9]+)?)"
_NAME_LABELS = ("borrower name", "borrower", "entity name", "account name", "name")
_SECTOR_LABELS = ("sector", "industry", "segment")
_EXPOSURE_LABELS = ("exposure", "sanctioned exposure", "limit", "facility")


@dataclass(frozen=True)
class ExtractionResult:
    """Best-effort, reviewable extraction of form fields from a document.

    ``fields`` carries only the keys the parser found; the cockpit merges them
    into the form and the officer reviews every value before scoring. ``source``
    labels the provenance ("ocr" for a live read, or a clearly-labelled demo
    fixture) so the UI never presents a canned read as a live one.
    """

    fields: dict[str, object] = field(default_factory=dict)
    source: str = "ocr"
    message: str = ""
    service_available: bool = True


# Deterministic demo fixture. The OCR GPU instance is VPN-only and currently
# stopped, so a filename that looks like the bundled sample (or an explicit
# demo flag) returns a canned extraction for a representative borrower. It is
# clearly labelled and never presented as a live OCR read.
DEMO_SOURCE = "demo fixture — OCR offline"
DEMO_FIXTURE = ExtractionResult(
    fields={
        "name": "Acme Textiles Pvt Ltd",
        "sector": "Textiles",
        "exposureCr": 7.5,
        "PERFORM_CNS.SCORE": 612,
        "ltv": 0.88,
        "primary_utilization": 0.93,
        "PRI.OVERDUE.ACCTS": 3,
        "DELINQUENT.ACCTS.IN.LAST.SIX.MONTHS": 2,
        "NO.OF_INQUIRIES": 4,
        "age_years": 46,
        "credit_history_months": 108,
    },
    source=DEMO_SOURCE,
    message="OCR offline — loaded a sample borrower for review.",
    service_available=False,
)

_DEMO_FILENAME_HINTS = ("sample", "acme")


def is_demo_request(filename: str | None, demo: bool) -> bool:
    if demo:
        return True
    if not filename:
        return False
    lowered = filename.lower()
    return any(hint in lowered for hint in _DEMO_FILENAME_HINTS)


def _coerce(field_key: str, raw: str) -> float | int | None:
    try:
        value = float(raw)
    except ValueError:
        return None
    low, high = NUMERIC_BOUNDS[field_key]
    if not (low <= value <= high):
        return None
    if field_key in INTEGER_FIELDS:
        return int(round(value))
    return round(value, 4)


def _match_number(text: str, labels: tuple[str, ...]) -> str | None:
    # Drop parenthetical qualifiers such as "(6m)" or "(90d)" so a number inside
    # a unit hint is never mistaken for the field value; the real value follows
    # the label and a separator.
    cleaned = re.sub(r"\([^)\n]*\)", " ", text)
    for label in labels:
        pattern = re.compile(
            rf"{re.escape(label)}[^0-9\n]{{0,12}}{_NUMBER}",
            re.IGNORECASE,
        )
        found = pattern.search(cleaned)
        if found:
            return found.group(1)
    return None


def _match_text(text: str, labels: tuple[str, ...]) -> str | None:
    for label in labels:
        pattern = re.compile(
            rf"{re.escape(label)}\s*[:=\-]\s*(.+)",
            re.IGNORECASE,
        )
        for line in text.splitlines():
            found = pattern.search(line.strip())
            if found:
                value = found.group(1).strip()
                if value:
                    return value
    return None


def parse_fields(text: str) -> dict[str, object]:
    """Parse labelled numbers and names out of OCR text into form fields.

    The parser is deterministic and conservative: it only emits a field when a
    recognised label is present with a parseable, in-range value. Unlabelled or
    ambiguous numbers are ignored rather than guessed.
    """
    parsed: dict[str, object] = {}
    if not text or not text.strip():
        return parsed

    name = _match_text(text, _NAME_LABELS)
    if name:
        parsed["name"] = name
    sector = _match_text(text, _SECTOR_LABELS)
    if sector:
        parsed["sector"] = sector

    exposure_raw = _match_number(text, _EXPOSURE_LABELS)
    if exposure_raw is not None:
        try:
            exposure = float(exposure_raw)
        except ValueError:
            exposure = None
        if exposure is not None and 0 < exposure <= 10000:
            parsed["exposureCr"] = round(exposure, 2)

    for field_key, labels in NUMERIC_FIELDS.items():
        raw = _match_number(text, labels)
        if raw is None:
            continue
        value = _coerce(field_key, raw)
        if value is not None:
            parsed[field_key] = value

    return parsed


class FormExtractor:
    """Turn an uploaded document into a partial NewBorrowerForm pre-fill.

    Runs OCR to get text, then a deterministic labelled-field parser. When the
    OCR service is unconfigured or unreachable the extractor degrades cleanly:
    a recognised sample document (by filename or an explicit demo flag) returns
    a clearly-labelled demo fixture, and anything else returns an empty,
    "OCR offline" result rather than raising.
    """

    def __init__(self, ocr: OcrClient | None = None):
        self._ocr = ocr or OcrClient()

    def extract(
        self, document: Path, filename: str | None = None, demo: bool = False
    ) -> ExtractionResult:
        name = filename or document.name
        if is_demo_request(name, demo):
            return DEMO_FIXTURE

        if not self._ocr.available:
            return ExtractionResult(
                fields={},
                source="ocr",
                message="OCR service offline — no fields extracted (set OCR_SERVICE_URL).",
                service_available=False,
            )

        try:
            text = self._ocr.extract(document)
        except Exception:
            return ExtractionResult(
                fields={},
                source="ocr",
                message="OCR service offline — the reader is unreachable.",
                service_available=False,
            )

        parsed = parse_fields(text)
        if not parsed:
            return ExtractionResult(
                fields={},
                source="ocr",
                message="No form fields could be read from the document.",
                service_available=True,
            )
        return ExtractionResult(
            fields=parsed,
            source="ocr",
            message="Extracted from document — best-effort, please review before scoring.",
            service_available=True,
        )


def configured_ocr_available() -> bool:
    return bool(settings.ocr_service_url)
