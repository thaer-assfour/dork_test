"""DataForSEO provider (Google Organic, Live Advanced endpoint)."""
from __future__ import annotations

import base64

import httpx

from app.engines.base import EngineError, SearchEngine, SearchHit, SearchResponse

API_URL = "https://api.dataforseo.com/v3/serp/google/organic/live/advanced"


class DataForSEOEngine(SearchEngine):
    name = "dataforseo"
    price_per_1000 = 2.0  # live mode; standard queue is cheaper. Confirm on dataforseo.com
    free_quota = 0

    @property
    def configured(self) -> bool:
        return bool(self._config.get("login") and self._config.get("password"))

    def _auth_header(self) -> str:
        login = self._config.get("login", "")
        password = self._config.get("password", "")
        token = base64.b64encode(f"{login}:{password}".encode()).decode()
        return f"Basic {token}"

    def search(self, query: str, num: int = 10) -> SearchResponse:
        if not self.configured:
            raise EngineError("dataforseo: missing login/password")
        body = [{
            "keyword": query,
            "language_code": "en",
            "location_code": 2840,  # United States
            "depth": min(num, 100),
        }]
        headers = {"Authorization": self._auth_header(), "Content-Type": "application/json"}
        try:
            resp = httpx.post(API_URL, json=body, headers=headers, timeout=60.0)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise EngineError(f"dataforseo request failed: {exc}") from exc
        data = resp.json()
        hits: list[SearchHit] = []
        for task in data.get("tasks", []) or []:
            for result in task.get("result", []) or []:
                for item in result.get("items", []) or []:
                    if item.get("type") == "organic" and item.get("url"):
                        hits.append(SearchHit(
                            url=item["url"],
                            title=item.get("title"),
                            snippet=item.get("description"),
                        ))
        return SearchResponse(hits=hits, raw=data, credits=1)
