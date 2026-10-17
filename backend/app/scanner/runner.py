"""Execute a scan: run each planned query through the engine, log coverage, store results.

Hard safety rule: a query only runs for an approved target. The planner already
filters to approved targets; the runner re-checks before every call.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import QueryCache, Scan, ScanItem, Target
from app.engines.base import EngineError, SearchEngine, SearchHit
from app.scanner.dedup import record_hits
from app.scanner.planner import ScanPlan, query_hash


def _cached_payload(db: Session, engine: str, query: str):
    row = db.scalar(
        select(QueryCache).where(
            QueryCache.engine_name == engine,
            QueryCache.query_hash == query_hash(engine, query),
        )
    )
    return row.payload if row else None


def _store_cache(db: Session, engine: str, query: str, payload: dict) -> None:
    h = query_hash(engine, query)
    row = db.scalar(select(QueryCache).where(QueryCache.engine_name == engine, QueryCache.query_hash == h))
    if row:
        row.payload = payload
        row.fetched_at = datetime.now(timezone.utc)
    else:
        db.add(QueryCache(engine_name=engine, query_hash=h, payload=payload))
    db.commit()


def execute_scan(db: Session, scan_id: int, plan: ScanPlan, engine: SearchEngine) -> None:
    settings = get_settings()
    scan = db.get(Scan, scan_id)
    if not scan:
        return
    scan.status = "running"
    db.commit()

    delay = 1.0 / settings.rate_limit_per_sec if settings.rate_limit_per_sec > 0 else 0
    actual_queries = 0
    actual_cost = 0.0

    for pq in plan.queries:
        target = db.get(Target, pq.target_id)
        if not target or not target.approved:
            continue  # safety: never scan an unapproved target

        item = ScanItem(
            scan_id=scan_id, target_id=pq.target_id, dork_id=pq.primary_dork_id,
            rendered_query=pq.query, status="running", cache_hit=pq.cached,
            started_at=datetime.now(timezone.utc),
        )
        db.add(item)
        db.commit()

        hits: list[SearchHit] = []
        try:
            cached = _cached_payload(db, plan.engine, pq.query) if pq.cached else None
            if cached is not None:
                from app.engines.base import SearchHit as _H
                hits = [_H(url=h.get("url", ""), title=h.get("title"), snippet=h.get("snippet"))
                        for h in cached.get("hits", [])]
            else:
                resp = engine.search(pq.query, num=10)
                hits = resp.hits
                actual_queries += 1
                actual_cost += engine.cost_for(resp.credits)
                _store_cache(db, plan.engine, pq.query,
                             {"hits": [h.__dict__ for h in hits]})
                if delay:
                    time.sleep(delay)

            count = record_hits(db, pq.target_id, item.id, hits)
            item.result_count = count
            item.status = "done"
        except EngineError as exc:
            item.status = "error"
            item.error = str(exc)
        finally:
            item.finished_at = datetime.now(timezone.utc)
            db.commit()

    scan.actual_queries = actual_queries
    scan.actual_cost = round(actual_cost, 4)
    scan.status = "done"
    db.commit()
