"""Engine registry: builds provider instances from settings and exposes metadata."""
from __future__ import annotations

from app.config import get_settings
from app.engines.base import SearchEngine
from app.engines.dataforseo import DataForSEOEngine
from app.engines.serper import SerperEngine


def build_engines() -> dict[str, SearchEngine]:
    s = get_settings()
    return {
        "serper": SerperEngine(api_key=s.serper_api_key),
        "dataforseo": DataForSEOEngine(login=s.dataforseo_login, password=s.dataforseo_password),
    }


def get_engine(name: str) -> SearchEngine:
    engines = build_engines()
    if name not in engines:
        raise KeyError(f"unknown engine: {name}")
    return engines[name]


def engine_catalog() -> list[dict]:
    """Metadata for the UI: price, free quota, whether credentials are present."""
    out = []
    default = get_settings().default_engine
    for name, eng in build_engines().items():
        out.append({
            "name": name,
            "price_per_1000": eng.price_per_1000,
            "free_quota": eng.free_quota,
            "configured": eng.configured,
            "is_default": name == default,
        })
    return out
