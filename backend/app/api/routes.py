"""All HTTP API routes for DorkHub."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.base import get_db
from app.db.models import (
    Dork,
    Program,
    Result,
    Scan,
    ScanItem,
    Target,
)
from app.discovery.sources import SOURCES, manual_candidate
from app.engines.registry import engine_catalog, get_engine
from app.schemas import (
    ApproveIn,
    DiscoverIn,
    DorkOut,
    DorkToggleIn,
    EstimateIn,
    EstimateOut,
    LoginIn,
    ManualProgramIn,
    ProgramOut,
    ProgramStatusIn,
    ResultLabelIn,
    ResultOut,
    ScanOut,
    ScanRunIn,
    TargetIn,
    TargetOut,
)
from app.scanner.planner import build_plan
from app.security import (
    COOKIE_NAME,
    AuthDep,
    make_session_token,
    verify_password,
)
from app.tasks.queue import enqueue_scan

router = APIRouter(prefix="/api")


# ----------------------------- auth -----------------------------
@router.post("/auth/login")
def login(body: LoginIn, response: Response):
    settings = get_settings()
    if settings.auth_password_hash and not verify_password(body.password, settings.auth_password_hash):
        raise HTTPException(status_code=401, detail="bad password")
    response.set_cookie(COOKIE_NAME, make_session_token(), httponly=True, samesite="lax")
    return {"ok": True}


@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.get("/auth/status")
def auth_status():
    return {"auth_required": bool(get_settings().auth_password_hash)}


# ----------------------------- engines -----------------------------
@router.get("/engines", dependencies=[AuthDep])
def list_engines():
    return engine_catalog()


# ----------------------------- discovery -----------------------------
@router.post("/discovery/run", dependencies=[AuthDep])
def run_discovery(body: DiscoverIn, db: Session = Depends(get_db)):
    if body.source not in SOURCES:
        raise HTTPException(status_code=400, detail="unknown source")
    candidates = SOURCES[body.source](only_self_hosted=body.only_self_hosted)
    added = 0
    for c in candidates:
        exists = db.scalar(select(Program).where(Program.source == c["source"], Program.name == c["name"]))
        if exists:
            continue
        db.add(Program(
            name=c["name"], homepage=c.get("homepage"), policy_url=c.get("policy_url"),
            contact_url=c.get("contact_url"), source=c["source"],
            offers_bounty=c.get("offers_bounty"), bounty_confidence=c.get("bounty_confidence", 0.0),
            scope_text=c.get("scope_text"), status="candidate",
        ))
        added += 1
    db.commit()
    return {"fetched": len(candidates), "added": added}


@router.post("/discovery/manual", dependencies=[AuthDep])
def add_manual(body: ManualProgramIn, db: Session = Depends(get_db)):
    c = manual_candidate(body.name, body.policy_url, body.contact_url, body.homepage, body.scope_text)
    prog = Program(
        name=c["name"], homepage=c.get("homepage"), policy_url=c.get("policy_url"),
        contact_url=c.get("contact_url"), source="manual",
        offers_bounty=c.get("offers_bounty"), bounty_confidence=c.get("bounty_confidence", 0.0),
        scope_text=c.get("scope_text"), status="candidate",
    )
    db.add(prog)
    db.commit()
    db.refresh(prog)
    return ProgramOut.model_validate(prog)


@router.get("/programs", response_model=list[ProgramOut], dependencies=[AuthDep])
def list_programs(status: str | None = None, q: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Program)
    if status:
        stmt = stmt.where(Program.status == status)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Program.name.ilike(like))
    stmt = stmt.order_by(Program.discovered_at.desc())
    return db.scalars(stmt).all()


@router.patch("/programs/{program_id}", response_model=ProgramOut, dependencies=[AuthDep])
def set_program_status(program_id: int, body: ProgramStatusIn, db: Session = Depends(get_db)):
    prog = db.get(Program, program_id)
    if not prog:
        raise HTTPException(status_code=404, detail="not found")
    prog.status = body.status
    db.commit()
    db.refresh(prog)
    return prog


# ----------------------------- targets -----------------------------
@router.post("/targets", response_model=TargetOut, dependencies=[AuthDep])
def create_target(body: TargetIn, db: Session = Depends(get_db)):
    existing = db.scalar(select(Target).where(Target.value == body.value))
    if existing:
        raise HTTPException(status_code=409, detail="target exists")
    t = Target(**body.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.get("/targets", response_model=list[TargetOut], dependencies=[AuthDep])
def list_targets(approved: bool | None = None, db: Session = Depends(get_db)):
    stmt = select(Target)
    if approved is not None:
        stmt = stmt.where(Target.approved == approved)
    return db.scalars(stmt.order_by(Target.added_at.desc())).all()


@router.patch("/targets/{target_id}/approve", response_model=TargetOut, dependencies=[AuthDep])
def approve_target(target_id: int, body: ApproveIn, db: Session = Depends(get_db)):
    t = db.get(Target, target_id)
    if not t:
        raise HTTPException(status_code=404, detail="not found")
    t.approved = body.approved
    db.commit()
    db.refresh(t)
    return t


@router.delete("/targets/{target_id}", dependencies=[AuthDep])
def delete_target(target_id: int, db: Session = Depends(get_db)):
    t = db.get(Target, target_id)
    if t:
        db.delete(t)
        db.commit()
    return {"ok": True}


# ----------------------------- dorks -----------------------------
@router.get("/dorks", response_model=list[DorkOut], dependencies=[AuthDep])
def list_dorks(category: str | None = None, enabled: bool | None = None, db: Session = Depends(get_db)):
    stmt = select(Dork)
    if category:
        stmt = stmt.where(Dork.category == category)
    if enabled is not None:
        stmt = stmt.where(Dork.enabled == enabled)
    return db.scalars(stmt.order_by(Dork.category, Dork.priority)).all()


@router.patch("/dorks/{dork_id}/toggle", response_model=DorkOut, dependencies=[AuthDep])
def toggle_dork(dork_id: int, body: DorkToggleIn, db: Session = Depends(get_db)):
    d = db.get(Dork, dork_id)
    if not d:
        raise HTTPException(status_code=404, detail="not found")
    d.enabled = body.enabled
    db.commit()
    db.refresh(d)
    return d


@router.post("/dorks/import", dependencies=[AuthDep])
def import_dorks(db: Session = Depends(get_db)):
    from app.dorks.importer import import_library

    return import_library(db)


# ----------------------------- scans -----------------------------
@router.post("/scans/estimate", response_model=EstimateOut, dependencies=[AuthDep])
def estimate_scan(body: EstimateIn, db: Session = Depends(get_db)):
    try:
        engine = get_engine(body.engine)
    except KeyError:
        raise HTTPException(status_code=400, detail="unknown engine")
    plan = build_plan(db, body.target_ids, body.dork_ids, body.engine, float(engine.price_per_1000))
    d = plan.as_dict()
    d["warn"] = d["estimated_cost"] >= get_settings().cost_warn_threshold_usd
    return d


@router.post("/scans/run", response_model=ScanOut, dependencies=[AuthDep])
def run_scan(body: ScanRunIn, db: Session = Depends(get_db)):
    try:
        engine = get_engine(body.engine)
    except KeyError:
        raise HTTPException(status_code=400, detail="unknown engine")
    if not engine.configured:
        raise HTTPException(status_code=400, detail=f"engine '{body.engine}' has no API credentials configured")
    plan = build_plan(db, body.target_ids, body.dork_ids, body.engine, float(engine.price_per_1000))
    if plan.merged_count == 0:
        raise HTTPException(status_code=400, detail="nothing to scan (no approved targets or enabled dorks)")

    scan = Scan(
        engine_name=body.engine, status="planned",
        estimated_queries=plan.billable_count, estimated_cost=plan.estimated_cost,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    enqueue_scan(scan.id, body.target_ids, body.dork_ids, body.engine)
    db.refresh(scan)
    return scan


@router.get("/scans", response_model=list[ScanOut], dependencies=[AuthDep])
def list_scans(db: Session = Depends(get_db)):
    return db.scalars(select(Scan).order_by(Scan.created_at.desc())).all()


@router.get("/scans/{scan_id}", response_model=ScanOut, dependencies=[AuthDep])
def get_scan(scan_id: int, db: Session = Depends(get_db)):
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="not found")
    return scan


# ----------------------------- coverage -----------------------------
@router.get("/coverage", dependencies=[AuthDep])
def coverage_matrix(db: Session = Depends(get_db)):
    """Targets x dorks grid: last scan time and result count per cell."""
    rows = db.execute(
        select(
            ScanItem.target_id,
            ScanItem.dork_id,
            func.max(ScanItem.finished_at),
            func.sum(ScanItem.result_count),
            func.count(ScanItem.id),
        ).group_by(ScanItem.target_id, ScanItem.dork_id)
    ).all()
    cells = [
        {
            "target_id": r[0], "dork_id": r[1],
            "last_scanned": r[2].isoformat() if r[2] else None,
            "result_count": int(r[3] or 0), "scan_count": int(r[4] or 0),
        }
        for r in rows
    ]
    targets = db.scalars(select(Target).where(Target.approved == True)).all()  # noqa: E712
    dorks = db.scalars(select(Dork)).all()
    return {
        "targets": [{"id": t.id, "value": t.value} for t in targets],
        "dorks": [{"id": d.id, "name": d.name, "category": d.category} for d in dorks],
        "cells": cells,
    }


# ----------------------------- results -----------------------------
@router.get("/results", response_model=list[ResultOut], dependencies=[AuthDep])
def list_results(target_id: int | None = None, label: str | None = None,
                 db: Session = Depends(get_db)):
    stmt = select(Result)
    if target_id:
        stmt = stmt.where(Result.target_id == target_id)
    if label:
        stmt = stmt.where(Result.label == label)
    return db.scalars(stmt.order_by(Result.last_seen.desc())).all()


@router.patch("/results/{result_id}", response_model=ResultOut, dependencies=[AuthDep])
def label_result(result_id: int, body: ResultLabelIn, db: Session = Depends(get_db)):
    r = db.get(Result, result_id)
    if not r:
        raise HTTPException(status_code=404, detail="not found")
    r.label = body.label
    if body.notes is not None:
        r.notes = body.notes
    db.commit()
    db.refresh(r)
    return r


@router.get("/dashboard", dependencies=[AuthDep])
def dashboard(db: Session = Depends(get_db)):
    return {
        "programs_total": db.scalar(select(func.count(Program.id))) or 0,
        "programs_approved": db.scalar(select(func.count(Program.id)).where(Program.status == "approved")) or 0,
        "targets_approved": db.scalar(select(func.count(Target.id)).where(Target.approved == True)) or 0,  # noqa: E712
        "dorks_enabled": db.scalar(select(func.count(Dork.id)).where(Dork.enabled == True)) or 0,  # noqa: E712
        "scans_total": db.scalar(select(func.count(Scan.id))) or 0,
        "results_new": db.scalar(select(func.count(Result.id)).where(Result.label == "new")) or 0,
    }
