"""Heuristic classifier: does a program likely pay a bounty, and is it self-hosted?"""
from __future__ import annotations

from urllib.parse import urlparse

from app.config import get_settings

_BOUNTY_WORDS = ["bounty", "reward", "monetary", "payout", "we pay", "compensation", "swag"]
_NO_BOUNTY_WORDS = ["no monetary", "unable to offer", "do not offer", "no reward", "recognition only", "hall of fame"]


def classify_bounty(text: str | None) -> tuple[bool | None, float]:
    """Return (offers_bounty, confidence 0..1) from policy text."""
    if not text:
        return None, 0.0
    low = text.lower()
    neg = sum(1 for w in _NO_BOUNTY_WORDS if w in low)
    pos = sum(1 for w in _BOUNTY_WORDS if w in low)
    if neg and neg >= pos:
        return False, min(1.0, 0.4 + 0.2 * neg)
    if pos:
        return True, min(1.0, 0.4 + 0.2 * pos)
    return None, 0.1


def _host(url: str | None) -> str:
    if not url:
        return ""
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def is_self_hosted(policy_url: str | None, contact_url: str | None, homepage: str | None = None) -> bool:
    """True when the program is not hosted on a known platform domain."""
    excluded = get_settings().excluded_platforms
    hosts = [_host(policy_url), _host(contact_url)]
    for h in hosts:
        if not h:
            continue
        if any(h == p or h.endswith("." + p) for p in excluded):
            return False
    # If we have no policy/contact host at all, fall back to homepage presence.
    if not any(hosts):
        return bool(_host(homepage))
    return True
