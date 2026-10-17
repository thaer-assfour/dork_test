"""Build the concrete query plan for a scan and estimate its cost.

The plan drives both the pre-run estimate (shown live in the UI) and the actual
execution, so the number the user approves is the number that runs.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Dork, QueryCache, Target
from app.dorks.renderer import render_target


@dataclass
class PlannedQuery:
    target_id: int
    query: str
    dork_ids: list[int]
    primary_dork_id: int | None
    cached: bool = False


@dataclass
class ScanPlan:
    engine: str
    queries: list[PlannedQuery]
    raw_count: int           # before merge
    merged_count: int        # after merge
    billable_count: int      # after cache
    estimated_cost: float

    def as_dict(self) -> dict:
        return {
            "engine": self.engine,
            "raw_count": self.raw_count,
            "merged_count": self.merged_count,
            "billable_count": self.billable_count,
            "cached_count": self.merged_count - self.billable_count,
            "estimated_cost": self.estimated_cost,
        }


def query_hash(engine: str, query: str) -> str:
    return hashlib.sha256(f"{engine}::{query}".encode()).hexdigest()


def _is_cached(db: Session, engine: str, query: str, ttl_hours: int) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=ttl_hours)
    row = db.scalar(
        select(QueryCache).where(
            QueryCache.engine_name == engine,
            QueryCache.query_hash == query_hash(engine, query),
            QueryCache.fetched_at >= cutoff,
        )
    )
    return row is not None


def build_plan(db: Session, target_ids: list[int], dork_ids: list[int], engine: str,
               price_per_1000: float) -> ScanPlan:
    settings = get_settings()
    targets = db.scalars(select(Target).where(Target.id.in_(target_ids), Target.approved == True)).all()  # noqa: E712
    dorks = db.scalars(select(Dork).where(Dork.id.in_(dork_ids), Dork.enabled == True)).all()  # noqa: E712

    raw_count = len(targets) * len(dorks)
    planned: list[PlannedQuery] = []
    for t in targets:
        rendered = render_target(dorks, t.value, t.kind, max_merge=settings.max_merge_terms)
        for rq in rendered:
            cached = _is_cached(db, engine, rq.query, settings.cache_ttl_hours)
            planned.append(PlannedQuery(
                target_id=t.id, query=rq.query, dork_ids=rq.dork_ids,
                primary_dork_id=rq.primary_dork_id, cached=cached,
            ))

    merged_count = len(planned)
    billable = [p for p in planned if not p.cached]
    billable_count = len(billable)
    cost = round(billable_count * price_per_1000 / 1000.0, 4)
    return ScanPlan(
        engine=engine, queries=planned, raw_count=raw_count,
        merged_count=merged_count, billable_count=billable_count, estimated_cost=cost,
    )
