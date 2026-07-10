from __future__ import annotations

import json
import logging
import math
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import AsyncIterator

import joblib
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from trinetra.api.portfolio import PortfolioService
from trinetra.api.service import ScoringService
from trinetra.config import settings
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


@app.get("/portfolio")
def portfolio(n: int = 200, seed: int = 7) -> dict[str, object]:
    return _require_portfolio().sample(n=n, seed=seed)


@app.get("/benchmark")
def benchmark() -> dict[str, object]:
    path = settings.artifacts_dir / "benchmark.json"
    if not path.exists():
        raise HTTPException(status_code=503, detail="Benchmark not computed. Run the benchmark pipeline.")
    return json.loads(path.read_text())
