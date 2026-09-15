from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="WANDERMIND_",
        extra="ignore",
        case_sensitive=False,
    )

    env: Literal["dev", "test", "prod"] = "dev"
    app_name: str = "WanderMind"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    database_url: str = "sqlite+aiosqlite:///./wandermind.db"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    access_username: str = Field(default="wandermind", min_length=1, max_length=100)
    access_password: SecretStr | None = None
    static_dir: str | None = None
    embedding_dimensions: int = Field(default=96, ge=8, le=4_096)
    runtime_adapter: Literal["mock", "codex", "openai"] = "mock"
    codex_executable: str = "codex"
    runtime_cwd: str | None = None
    llm_base_url: str = "https://apihub.agnes-ai.com/v1"
    llm_api_key: SecretStr | None = None
    llm_model: str = Field(default="agnes-2.5-flash", min_length=1, max_length=200)
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    llm_max_output_tokens: int = Field(default=2_000, ge=128, le=32_000)
    runtime_timeout_seconds: float = Field(default=60.0, gt=0, le=3_600)
    runtime_max_retries: int = Field(default=2, ge=0, le=10)
    wonder_threshold: float = Field(default=0.58, ge=0.0, le=1.0)
    cheap_score_threshold: float = Field(default=0.40, ge=0.0, le=1.0)
    score_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "novelty": 0.18,
            "surprise": 0.12,
            "personal_relevance": 0.18,
            "coherence": 0.12,
            "generativity": 0.14,
            "explanatory_power": 0.10,
            "evidence_potential": 0.08,
            "cross_domain_value": 0.08,
            "redundancy_penalty": 0.12,
            "arbitrariness_penalty": 0.10,
            "hallucination_risk_penalty": 0.15,
        }
    )
    enable_scheduler: bool = False
    incubation_interval_minutes: int = Field(default=360, ge=5, le=43_200)
    max_request_bytes: int = Field(default=2_100_000, ge=1_024, le=50_000_000)
    auto_create_schema: bool = True

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("invalid log level")
        return normalized

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        if isinstance(value, str) and value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        if isinstance(value, str) and value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        return value

    @field_validator("llm_base_url")
    @classmethod
    def normalize_llm_base_url(cls, value: str) -> str:
        normalized = value.rstrip("/")
        if not normalized.startswith(("https://", "http://")):
            raise ValueError("LLM base URL must use HTTP or HTTPS")
        return normalized


@lru_cache
def get_settings() -> Settings:
    return Settings()
