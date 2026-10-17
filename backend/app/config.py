"""Application configuration, read from environment / .env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Look for .env at the repo root (one level above backend/) and in backend/,
# so it is found whether you run from the repo root or from backend/.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = Path(__file__).resolve().parents[1]
_ENV_FILES = (str(_REPO_ROOT / ".env"), str(_BACKEND / ".env"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILES, env_prefix="DORKHUB_", extra="ignore")

    # Core
    app_name: str = "DorkHub"
    secret_key: str = "change-me-in-env"
    # Single-user auth. Hash is generated with `dorkhub set-password`.
    auth_password_hash: str = ""

    # Database. SQLite by default for easy local run; Postgres in compose.
    database_url: str = "sqlite:///./dorkhub.db"

    # Task queue backend: "sync" runs inline (no Redis), "rq" uses Redis.
    task_backend: str = "sync"
    redis_url: str = "redis://localhost:6379/0"

    # Search providers (keys stay in env, never in the DB).
    serper_api_key: str = ""
    dataforseo_login: str = ""
    dataforseo_password: str = ""
    google_cse_key: str = ""
    google_cse_cx: str = ""
    brave_api_key: str = ""

    # Default engine shown in the UI.
    default_engine: str = "serper"

    # Scan safety / cost controls.
    cache_ttl_hours: int = 72
    max_merge_terms: int = 8          # max OR terms fused into one query
    cost_warn_threshold_usd: float = 20.0
    rate_limit_per_sec: float = 2.0

    # Discovery: platform domains excluded from "self-hosted" candidates.
    excluded_platforms: list[str] = [
        "hackerone.com",
        "bugcrowd.com",
        "intigriti.com",
        "yeswehack.com",
        "hackenproof.com",
        "immunefi.com",
        "federacy.com",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
