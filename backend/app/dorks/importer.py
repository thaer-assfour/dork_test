"""Import YAML dork library files into the database (idempotent upsert)."""
from __future__ import annotations

from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Dork

LIBRARY_DIR = Path(__file__).parent / "library"


def import_library(db: Session, directory: Path | None = None) -> dict[str, int]:
    directory = directory or LIBRARY_DIR
    added = updated = 0
    for path in sorted(directory.glob("*.yaml")):
        items = yaml.safe_load(path.read_text()) or []
        for item in items:
            existing = db.scalar(
                select(Dork).where(Dork.category == item["category"], Dork.name == item["name"])
            )
            if existing:
                existing.template = item["template"]
                existing.priority = item.get("priority", 2)
                existing.mergeable = item.get("mergeable", False)
                existing.merge_group = item.get("merge_group")
                existing.engine_hint = item.get("engine_hint")
                existing.description = item.get("description")
                updated += 1
            else:
                db.add(Dork(
                    category=item["category"],
                    name=item["name"],
                    template=item["template"],
                    priority=item.get("priority", 2),
                    mergeable=item.get("mergeable", False),
                    merge_group=item.get("merge_group"),
                    engine_hint=item.get("engine_hint"),
                    description=item.get("description"),
                    enabled=True,
                ))
                added += 1
    db.commit()
    return {"added": added, "updated": updated}
