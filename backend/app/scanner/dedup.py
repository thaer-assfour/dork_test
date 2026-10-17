"""Normalize URLs and persist results with per-target de-duplication."""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Result, ResultSighting
from app.engines.base import SearchHit


def normalize_url(url: str) -> str:
    try:
        p = urlparse(url.strip())
    except ValueError:
        return url.strip().lower()
    scheme = (p.scheme or "https").lower()
    netloc = p.netloc.lower()
    path = p.path.rstrip("/") or "/"
    return urlunparse((scheme, netloc, path, "", p.query, ""))


def record_hits(db: Session, target_id: int, scan_item_id: int, hits: list[SearchHit]) -> int:
    """Insert new results, update last_seen on repeats. Returns count of hits seen."""
    now = datetime.now(timezone.utc)
    for hit in hits:
        if not hit.url:
            continue
        norm = normalize_url(hit.url)
        existing = db.scalar(
            select(Result).where(Result.target_id == target_id, Result.normalized_url == norm)
        )
        if existing:
            existing.last_seen = now
            existing.seen_count += 1
            result = existing
        else:
            result = Result(
                target_id=target_id, url=hit.url, normalized_url=norm,
                title=hit.title, snippet=hit.snippet, label="new",
                first_seen=now, last_seen=now, seen_count=1,
            )
            db.add(result)
            db.flush()
        db.add(ResultSighting(result_id=result.id, scan_item_id=scan_item_id, seen_at=now))
    db.commit()
    return len(hits)
