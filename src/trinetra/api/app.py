from __future__ import annotations

import json
import logging
import math
import tempfile
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import joblib
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from trinetra.api.portfolio import PortfolioService
from trinetra.api.service import ScoringService
from trinetra.config import settings
from trinetra.genai.adverse_media import AdverseMediaOverlay
from trinetra.genai.extract import DEMO_FIXTURE, ExtractionResult, FormExtractor
from trinetra.genai.llm import GemmaClient

logger = logging.getLogger("trinetra.api")

_ARTIFACT = settings.artifacts_dir / "ltfs_segment.joblib"
_service: ScoringService | None = None
_portfolio: PortfolioService | None = None


class ScoreRequest(BaseModel):
    features: dict[str, float | int | str | None]


class MemoRequest(BaseModel):
    borrower: str
    exposure: str
    features: dict[str, float | int | str | None]


class AdverseMediaRequest(BaseModel):
    borrower: str
    grade: str = "C"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global _service
    if _ARTIFACT.exists():
        _service = ScoringService.from_artifacts(_ARTIFACT)
    yield


app = FastAPI(title="TRINETRA", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    start = time.perf_counter()
    response = await call_next(request)
    latency_ms = round((time.perf_counter() - start) * 1000, 1)
    logger.info(
        "request",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "latency_ms": latency_ms,
        },
    )
    return response


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Optional API-key gate. Enforced only when API_KEY is configured.

    With no API_KEY set (the default) the check is a no-op, so the same-origin
    cockpit keeps working with no header. When API_KEY is set, callers must send
    a matching x-api-key header.
    """
    if not settings.api_key:
        return
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


def _require_service() -> ScoringService:
    if _service is None:
        raise HTTPException(status_code=503, detail="Model artifact not loaded. Train a segment first.")
    return _service


def _require_portfolio() -> PortfolioService:
    global _portfolio
    if _portfolio is None:
        if not _ARTIFACT.exists():
            raise HTTPException(status_code=503, detail="Model artifact not loaded. Train a segment first.")
        _portfolio = PortfolioService(joblib.load(_ARTIFACT))
    return _portfolio


def _validate_features(
    features: dict[str, object], known: list[str]
) -> dict[str, object]:
    """Reject malformed feature payloads before scoring.

    Unknown keys and explicit NaN/inf values are rejected with HTTP 422 so a
    client error surfaces clearly instead of being silently reindexed to a
    missing value. Absent features are permitted: the booster handles them as
    natively missing, which the cockpit relies on when it sends a partial form.
    """
    if not features:
        raise HTTPException(status_code=422, detail="No features provided.")

    known_set = set(known)
    unknown = sorted(key for key in features if key not in known_set)
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown feature(s): {', '.join(unknown)}.",
        )

    non_finite = sorted(
        key
        for key, value in features.items()
        if isinstance(value, float) and not math.isfinite(value)
    )
    if non_finite:
        raise HTTPException(
            status_code=422,
            detail=f"Non-finite value(s) for: {', '.join(non_finite)}.",
        )
    return features


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "model_loaded": _service is not None,
        "genai_available": GemmaClient().available,
    }


@app.post("/score")
def score(request: ScoreRequest, _: None = Depends(require_api_key)) -> dict[str, object]:
    service = _require_service()
    features = _validate_features(request.features, service.feature_names)
    explanation = service.score(features)
    return {
        "pd": explanation.pd_value,
        "grade": explanation.grade,
        "watch_tier": explanation.watch_tier,
        "reason_codes": [code.__dict__ for code in explanation.reason_codes],
    }


@app.post("/term-structure")
def term_structure(request: ScoreRequest, _: None = Depends(require_api_key)) -> dict[str, object]:
    service = _require_service()
    features = _validate_features(request.features, service.feature_names)
    return service.term_structure(features).__dict__


@app.post("/memo")
def memo(request: MemoRequest, _: None = Depends(require_api_key)) -> dict[str, object]:
    service = _require_service()
    features = _validate_features(request.features, service.feature_names)
    draft = service.memo(request.borrower, request.exposure, features)
    return draft.__dict__


@app.post("/adverse-media")
def adverse_media(
    request: AdverseMediaRequest, _: None = Depends(require_api_key)
) -> dict[str, object]:
    if not request.borrower.strip():
        raise HTTPException(status_code=422, detail="Borrower name is required.")
    result = AdverseMediaOverlay().check(request.borrower, grade=request.grade)
    return {
        "borrower": result.borrower,
        "escalate": result.escalate,
        "summary": result.summary,
        "tier_escalation": result.tier_escalation,
        "is_demo_fixture": result.is_demo_fixture,
        "service_available": result.service_available,
        "sources": [{"url": item.url, "title": item.title} for item in result.sources],
        "overlay_note": "adverse-media overlay — rules-based, separate from the PD model",
    }


_MAX_UPLOAD_BYTES = 15 * 1024 * 1024


def _extract_response(result: ExtractionResult) -> dict[str, object]:
    return {
        "fields": result.fields,
        "source": result.source,
        "message": result.message,
        "service_available": result.service_available,
    }


@app.post("/extract")
async def extract(
    file: UploadFile | None = File(default=None),
    demo: bool = Form(default=False),
    _: None = Depends(require_api_key),
) -> dict[str, object]:
    """Extract NewBorrowerForm fields from an uploaded PDF or image.

    Runs OCR to get text, then a deterministic labelled-field parser, and
    returns only the fields it found for the officer to review before scoring.
    Degrades gracefully: an unconfigured or unreachable OCR service does not
    500. A recognised sample document (or demo=true) returns a clearly-labelled
    demo fixture so the feature is always demonstrable offline, and the demo
    path needs no uploaded bytes.
    """
    if demo:
        return _extract_response(DEMO_FIXTURE)

    if file is None:
        raise HTTPException(status_code=422, detail="No file uploaded.")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")
    if len(payload) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded file exceeds the 15 MB limit.")

    suffix = Path(file.filename or "upload").suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as handle:
        handle.write(payload)
        handle.flush()
        result = FormExtractor().extract(
            Path(handle.name), filename=file.filename, demo=False
        )
    return _extract_response(result)


@app.get("/portfolio")
def portfolio(n: int = 200, seed: int = 7) -> dict[str, object]:
    return _require_portfolio().sample(n=n, seed=seed)


@app.get("/benchmark")
def benchmark() -> dict[str, object]:
    path = settings.artifacts_dir / "benchmark.json"
    if not path.exists():
        raise HTTPException(status_code=503, detail="Benchmark not computed. Run the benchmark pipeline.")
    return json.loads(path.read_text())
