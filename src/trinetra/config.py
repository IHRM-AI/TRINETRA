from __future__ import annotations

from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

PACKAGE_ROOT = Path(__file__).resolve().parents[2]

# Origins the browser cockpit is served from. Defaults cover local development
# and the live ALB deployment so the running demo works with no configuration.
# Override with the CORS_ORIGINS env var (comma-separated) to tighten in other
# environments.
DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:4173",
    "http://localhost:8091",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:4173",
    "http://127.0.0.1:8091",
    "http://ihrm-idbi-innovate-1525602521.us-east-1.elb.amazonaws.com",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    data_dir: Path = PACKAGE_ROOT / "data"
    artifacts_dir: Path = PACKAGE_ROOT / "artifacts"

    random_seed: int = 42
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: list(DEFAULT_CORS_ORIGINS),
        validation_alias="CORS_ORIGINS",
    )
    api_key: str = Field(default="", validation_alias="API_KEY")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    llm_base_url: str = Field(default="", validation_alias="VLLM_URL")
    llm_model: str = Field(default="gemma-4-31b-it", validation_alias="VLLM_MODEL_NAME")
    ocr_service_url: str = Field(default="", validation_alias="OCR_SERVICE_URL")
    firecrawl_base_url: str = Field(default="", validation_alias="FIRECRAWL_BASE_URL")
    llm_timeout_seconds: int = 120

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"


settings = Settings()
