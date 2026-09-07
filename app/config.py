"""Settings: the only place the process reads its environment.

Every configuration value the app uses is a field here, read once from the
environment (and ``.env`` in dev), validated at startup. Nothing else calls
``os.getenv`` for application config -- ``tests/unit/test_settings_documented.py``
asserts every field is documented in ``.env.example`` and every credential-shaped
field is in the log scrubbing list.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Process configuration, validated once at import."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["dev", "stage", "prod"] = Field(
        default="dev", validation_alias=AliasChoices("APP_ENV", "ENV")
    )
    debug: bool = False
    log_level: str = "INFO"
    # One JSON object per line outside dev; console format in dev. ``None``
    # means "decide from env"; set LOG_JSON explicitly to force either.
    log_json: bool | None = None
    secret_key: str = "change-me"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5439/app"
    # Per worker process. Ceiling on Postgres connections is
    # (pool_size + max_overflow) * workers * replicas.
    db_pool_size: int = 10
    db_max_overflow: int = 10
    # A request that cannot get a connection fails after this many seconds
    # instead of holding a worker: saturation should look like an error, not a
    # stall. Must stay above READINESS_TIMEOUT_SECONDS in app/utils/db.py.
    db_pool_timeout: int = 10

    # LLM roles resolve to (provider, model) here; nothing else names a model.
    anthropic_api_key: str | None = None
    ai_default_provider: str = "anthropic"
    ai_default_model: str = "claude-opus-5"

    # Injected by the image build; reported by /health for drift detection.
    release_sha: str | None = None

    @property
    def is_dev(self) -> bool:
        """True in local development."""
        return self.env == "dev"

    @property
    def is_prod(self) -> bool:
        """True in production, where runtime guards warn instead of raise."""
        return self.env == "prod"

    @property
    def json_logs(self) -> bool:
        """JSON logs are on outside dev unless LOG_JSON overrides."""
        return (not self.is_dev) if self.log_json is None else self.log_json


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings (cached)."""
    return Settings()


settings = get_settings()
