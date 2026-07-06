from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from trinetra.api.service import ScoringService
from trinetra.config import settings
from trinetra.genai.llm import GemmaClient

app = FastAPI(title="TRINETRA", version="0.1.0")

_ARTIFACT = settings.artifacts_dir / "ltfs_segment.joblib"
_service: ScoringService | None = None


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


@app.post("/memo")
def memo(request: MemoRequest) -> dict[str, object]:
    draft = _require_service().memo(request.borrower, request.exposure, request.features)
    return draft.__dict__
