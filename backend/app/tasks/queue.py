"""Task-queue abstraction.

- "sync" backend runs the job inline (no Redis needed) — good for local use.
- "rq" backend enqueues to Redis so a separate worker executes long scans.
The scan API calls `enqueue_scan` and doesn't care which backend is active.
"""
from __future__ import annotations

from app.config import get_settings


def run_scan_job(scan_id: int, target_ids: list[int], dork_ids: list[int], engine_name: str) -> None:
    """Entry point executed by whichever backend. Rebuilds its own DB session."""
    from app.db.base import SessionLocal
    from app.engines.registry import get_engine
    from app.scanner.planner import build_plan

    db = SessionLocal()
    try:
        engine = get_engine(engine_name)
        plan = build_plan(db, target_ids, dork_ids, engine_name, float(engine.price_per_1000))
        from app.scanner.runner import execute_scan
        execute_scan(db, scan_id, plan, engine)
    finally:
        db.close()


def enqueue_scan(scan_id: int, target_ids: list[int], dork_ids: list[int], engine_name: str) -> str:
    settings = get_settings()
    if settings.task_backend == "rq":
        from redis import Redis
        from rq import Queue

        q = Queue("dorkhub", connection=Redis.from_url(settings.redis_url))
        job = q.enqueue(run_scan_job, scan_id, target_ids, dork_ids, engine_name, job_timeout=3600)
        return job.id
    # sync fallback
    run_scan_job(scan_id, target_ids, dork_ids, engine_name)
    return f"sync-{scan_id}"
