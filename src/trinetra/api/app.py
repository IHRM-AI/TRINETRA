from __future__ import annotations

import json

import joblib
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from trinetra.api.portfolio import PortfolioService
from trinetra.api.service import ScoringService
from trinetra.config import settings
from trinetra.genai.llm import GemmaClient

app = FastAPI(title="TRINETRA", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

_ARTIFACT = settings.artifacts_dir / "ltfs_segment.joblib"
_service: ScoringService | None = None
_portfolio: PortfolioService | None = None


class ScoreRequest(BaseModel):
    features: dict[str, float | int | str | None]


class MemoRequest(BaseModel):
    borrower: str
    exposure: str
    features: dict[str, float | int | str | None]


@app.on_event("startup")
def _load() -> None:
    global _service
    if _ARTIFACT.exists():
        _service = ScoringService.from_artifacts(_ARTIFACT)


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


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "model_loaded": _service is not None,
        "genai_available": GemmaClient().available,
    }


@app.post("/score")
def score(request: ScoreRequest) -> dict[str, object]:
    explanation = _require_service().score(request.features)
    return {
        "pd": explanation.pd_value,
        "grade": explanation.grade,
        "watch_tier": explanation.watch_tier,
        "reason_codes": [code.__dict__ for code in explanation.reason_codes],
    }


@app.post("/term-structure")
def term_structure(request: ScoreRequest) -> dict[str, object]:
    return _require_service().term_structure(request.features).__dict__


@app.post("/memo")
def memo(request: MemoRequest) -> dict[str, object]:
    draft = _require_service().memo(request.borrower, request.exposure, request.features)
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
