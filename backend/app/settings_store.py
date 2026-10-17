"""DB-backed key/value settings, with transparent encryption for secret values.

Used for runtime settings the user edits in the UI (the AI layer config). Search
provider keys still live in .env; only the AI config is editable here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crypto import decrypt, encrypt
from app.db.models import Setting

SECRET_KEYS = {"ai_api_key"}  # stored encrypted


def get_value(db: Session, key: str, default: str = "") -> str:
    row = db.get(Setting, key)
    if not row:
        return default
    return decrypt(row.value) if key in SECRET_KEYS else row.value


def set_value(db: Session, key: str, value: str) -> None:
    stored = encrypt(value) if key in SECRET_KEYS else value
    row = db.get(Setting, key)
    if row:
        row.value = stored
    else:
        db.add(Setting(key=key, value=stored))
    db.commit()


@dataclass
class AIConfig:
    enabled: bool = False
    provider: str = "openai_compatible"   # openai_compatible | anthropic
    base_url: str = "http://localhost:11434/v1"  # default: local Ollama
    model: str = "llama3.1"
    has_key: bool = False                  # whether a key is stored (never the key itself)
    max_tokens: int = 1024

    def public_dict(self) -> dict:
        return asdict(self)


def get_ai_config(db: Session) -> AIConfig:
    return AIConfig(
        enabled=get_value(db, "ai_enabled", "false") == "true",
        provider=get_value(db, "ai_provider", "openai_compatible"),
        base_url=get_value(db, "ai_base_url", "http://localhost:11434/v1"),
        model=get_value(db, "ai_model", "llama3.1"),
        has_key=bool(get_value(db, "ai_api_key", "")),
        max_tokens=int(get_value(db, "ai_max_tokens", "1024") or "1024"),
    )


def get_ai_key(db: Session) -> str:
    return get_value(db, "ai_api_key", "")


def save_ai_config(db: Session, *, enabled: bool | None = None, provider: str | None = None,
                   base_url: str | None = None, model: str | None = None,
                   api_key: str | None = None, max_tokens: int | None = None) -> None:
    if enabled is not None:
        set_value(db, "ai_enabled", "true" if enabled else "false")
    if provider is not None:
        set_value(db, "ai_provider", provider)
    if base_url is not None:
        set_value(db, "ai_base_url", base_url)
    if model is not None:
        set_value(db, "ai_model", model)
    if max_tokens is not None:
        set_value(db, "ai_max_tokens", str(max_tokens))
    # api_key: empty string means "leave unchanged"; a sentinel clears it.
    if api_key is not None and api_key != "":
        if api_key == "__CLEAR__":
            set_value(db, "ai_api_key", "")
        else:
            set_value(db, "ai_api_key", api_key)
