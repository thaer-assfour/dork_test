"""Settings + AI endpoints (the optional AI layer, configured from the UI)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai.providers import AIError
from app.ai.service import MODEL_CATALOG, summarize_policy, test_connection, triage_result
from app.db.base import get_db
from app.db.models import Program, Result
from app.security import AuthDep
from app.settings_store import get_ai_config, save_ai_config

router = APIRouter(prefix="/api", dependencies=[AuthDep])


class AISettingsIn(BaseModel):
    enabled: bool | None = None
    provider: str | None = None          # openai_compatible | anthropic
    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None           # "" leaves unchanged, "__CLEAR__" clears
    max_tokens: int | None = None


@router.get("/settings")
def read_settings(db: Session = Depends(get_db)):
    return {"ai": get_ai_config(db).public_dict(), "model_catalog": MODEL_CATALOG}


@router.put("/settings/ai")
def update_ai_settings(body: AISettingsIn, db: Session = Depends(get_db)):
    if body.provider and body.provider not in ("openai_compatible", "anthropic"):
        raise HTTPException(status_code=400, detail="unknown provider")
    save_ai_config(
        db, enabled=body.enabled, provider=body.provider, base_url=body.base_url,
        model=body.model, api_key=body.api_key, max_tokens=body.max_tokens,
    )
    return get_ai_config(db).public_dict()


@router.post("/ai/test")
def ai_test(db: Session = Depends(get_db)):
    try:
        return test_connection(db)
    except AIError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/ai/triage/{result_id}")
def ai_triage(result_id: int, apply: bool = False, db: Session = Depends(get_db)):
    r = db.get(Result, result_id)
    if not r:
        raise HTTPException(status_code=404, detail="result not found")
    try:
        out = triage_result(db, r.title, r.snippet, r.url)
    except AIError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    note = f"[AI {out['score']}/100] {out['reason']}"
    r.notes = (note + ("\n" + r.notes if r.notes else ""))[:2000]
    if apply and out.get("suggested_label") in ("interesting", "reviewing", "false_positive"):
        r.label = out["suggested_label"]
    db.commit()
    return out


class SummarizeIn(BaseModel):
    program_id: int | None = None
    text: str | None = None


@router.post("/ai/summarize-policy")
def ai_summarize(body: SummarizeIn, db: Session = Depends(get_db)):
    text = body.text or ""
    if body.program_id and not text:
        prog = db.get(Program, body.program_id)
        if not prog:
            raise HTTPException(status_code=404, detail="program not found")
        text = prog.scope_text or prog.policy_url or ""
    if not text.strip():
        raise HTTPException(status_code=400, detail="no policy text to summarize")
    try:
        return summarize_policy(db, text)
    except AIError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
