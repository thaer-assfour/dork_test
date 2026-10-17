"""Unified search-provider interface.

Every provider implements `search(query, num) -> SearchResponse`. The rest of
the app never talks to a provider directly; it goes through the registry so the
engine can be swapped from a single setting.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SearchHit:
    url: str
    title: str | None = None
    snippet: str | None = None


@dataclass
class SearchResponse:
    hits: list[SearchHit] = field(default_factory=list)
    raw: dict | None = None
    # billable units this call cost on the provider (usually 1 per query).
    credits: int = 1


class SearchEngine:
    """Base class. Subclasses set `name`, `price_per_1000`, and implement `search`."""

    name: str = "base"
    price_per_1000: float = 0.0
    free_quota: int = 0
    daily_cap: int | None = None

    def __init__(self, **kwargs) -> None:
        self._config = kwargs

    @property
    def configured(self) -> bool:
        """Whether the engine has the credentials it needs to run."""
        return True

    def search(self, query: str, num: int = 10) -> SearchResponse:  # pragma: no cover - interface
        raise NotImplementedError

    def cost_for(self, num_queries: int) -> float:
        return round(num_queries * self.price_per_1000 / 1000.0, 4)


class EngineError(RuntimeError):
    pass
