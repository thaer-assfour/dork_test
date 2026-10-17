"""DorkHub FastAPI application entrypoint."""
from __future__ import annotations

import csv
import io
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.ai_routes import router as ai_router
from app.api.routes import router as api_router
from app.config import get_settings
from app.db.base import get_db, init_db
from app.db.models import Result
from app.security import AuthDep

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}


@app.get("/api/results/export", dependencies=[AuthDep])
def export_results(fmt: str = "csv", db: Session = Depends(get_db)):
    results = db.scalars(select(Result).order_by(Result.last_seen.desc())).all()
    if fmt == "json":
        from fastapi.responses import JSONResponse
        return JSONResponse([
            {"url": r.url, "title": r.title, "label": r.label, "target_id": r.target_id,
             "first_seen": r.first_seen.isoformat(), "last_seen": r.last_seen.isoformat()}
            for r in results
        ])
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["url", "title", "snippet", "label", "target_id", "seen_count", "first_seen", "last_seen"])
    for r in results:
        writer.writerow([r.url, r.title or "", r.snippet or "", r.label, r.target_id,
                         r.seen_count, r.first_seen.isoformat(), r.last_seen.isoformat()])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=dorkhub-results.csv"},
    )


app.include_router(api_router)
app.include_router(ai_router)

# Serve the built frontend if present (production). In dev, Vite serves it.
_static = Path(__file__).parent.parent / "static"
if _static.exists():
    app.mount("/", StaticFiles(directory=str(_static), html=True), name="static")
