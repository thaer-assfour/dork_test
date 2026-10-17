"""Serper.dev provider (Google results via official API)."""
from __future__ import annotations

import httpx

from app.engines.base import EngineError, SearchEngine, SearchHit, SearchResponse

API_URL = "https://google.serper.dev/search"


class SerperEngine(SearchEngine):
    name = "serper"
    price_per_1000 = 1.0  # approx; confirm current pack rate on serper.dev
    free_quota = 2500

    @property
    def configured(self) -> bool:
        return bool(self._config.get("api_key"))

    def search(self, query: str, num: int = 10) -> SearchResponse:
        api_key = self._config.get("api_key")
        if not api_key:
            raise EngineError("serper: missing api key")
        # num > 10 costs 2 credits on serper; keep this explicit for the estimator.
        credits = 2 if num > 10 else 1
        payload = {"q": query, "num": min(num, 100)}
        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
        try:
            resp = httpx.post(API_URL, json=payload, headers=headers, timeout=30.0)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise EngineError(f"serper request failed: {exc}") from exc
        data = resp.json()
        hits = [
            SearchHit(url=o.get("link", ""), title=o.get("title"), snippet=o.get("snippet"))
            for o in data.get("organic", [])
            if o.get("link")
        ]
        return SearchResponse(hits=hits, raw=data, credits=credits)
