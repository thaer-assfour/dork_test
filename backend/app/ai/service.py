"""High-level AI features built on a configured provider.

Features (all optional, triggered only on demand):
- triage_result: rank a single search result as interesting / noise, with a reason
  and a suggested label.
- summarize_policy: pull scope / bounty / exclusions out of a program policy text.

Prompts ask for strict JSON so the result is machine-usable; parsing is defensive.
"""
from __future__ import annotations

import json
import re

from sqlalchemy.orm import Session

from app.ai.providers import AIError, build_provider
from app.settings_store import get_ai_config, get_ai_key

# Catalog shown in the model dropdown. Free-text entry is also allowed.
MODEL_CATALOG = {
    "anthropic": [
        "claude-opus-5-5",
        "claude-sonnet-5-5",
        "claude-haiku-5-5",
        "claude-fable-5-1",
    ],
    "openai_compatible": [
        "llama3.1",            # local via Ollama
        "qwen2.5",             # local via Ollama
        "mistral",             # local via Ollama
        "gpt-4o-mini",         # hosted gateways
        "deepseek-chat",
    ],
}

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _provider_from_db(db: Session):
    cfg = get_ai_config(db)
    if not cfg.enabled:
        raise AIError("AI is disabled in settings")
    return build_provider(cfg.provider, cfg.base_url, get_ai_key(db), cfg.model), cfg.max_tokens


def _parse_json(text: str) -> dict:
    m = _JSON_RE.search(text or "")
    if not m:
        raise AIError("AI did not return JSON")
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as exc:
        raise AIError(f"could not parse AI JSON: {exc}") from exc


def test_connection(db: Session) -> dict:
    provider, _ = _provider_from_db(db)
    out = provider.complete(
        system="You are a connectivity check. Reply with exactly: OK",
        prompt="Reply with OK.",
        max_tokens=16,
    )
    return {"ok": "ok" in out.lower(), "reply": out.strip()[:200]}


def triage_result(db: Session, title: str | None, snippet: str | None, url: str) -> dict:
    provider, max_tokens = _provider_from_db(db)
    system = (
        "You triage search results for an authorized bug bounty engagement. "
        "Given one result, judge how likely it is to be security-relevant for a "
        "researcher (exposed data, admin surface, sensitive file, misconfig). "
        "Do not suggest exploiting anything. Respond ONLY with JSON: "
        '{"interesting": true|false, "score": 0-100, "reason": "short", '
        '"suggested_label": "interesting|reviewing|false_positive"}.'
    )
    prompt = f"URL: {url}\nTitle: {title or ''}\nSnippet: {snippet or ''}"
    data = _parse_json(provider.complete(system, prompt, max_tokens=min(max_tokens, 400)))
    return {
        "interesting": bool(data.get("interesting")),
        "score": int(data.get("score", 0)),
        "reason": str(data.get("reason", ""))[:500],
        "suggested_label": data.get("suggested_label", "reviewing"),
    }


def summarize_policy(db: Session, text: str) -> dict:
    provider, max_tokens = _provider_from_db(db)
    system = (
        "You summarize a bug bounty / vulnerability disclosure policy. Respond ONLY "
        'with JSON: {"offers_bounty": true|false|null, "in_scope": "short", '
        '"out_of_scope": "short", "notes": "short"}.'
    )
    prompt = text[:12000]
    data = _parse_json(provider.complete(system, prompt, max_tokens=min(max_tokens, 800)))
    return {
        "offers_bounty": data.get("offers_bounty"),
        "in_scope": str(data.get("in_scope", ""))[:1000],
        "out_of_scope": str(data.get("out_of_scope", ""))[:1000],
        "notes": str(data.get("notes", ""))[:1000],
    }
