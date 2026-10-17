"""Render dork templates against a target, with optional OR-merging.

Variables supported in a template: {domain}, {wildcard}, {org}, {url}.
Mergeable dorks that share a merge_group and a common prefix are fused into a
single query with an OR group, which cuts the number of billed queries.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class RenderedQuery:
    query: str
    dork_ids: list[int]          # dorks folded into this query
    primary_dork_id: int | None  # representative id for coverage logging


def _vars_for_target(value: str, kind: str) -> dict[str, str]:
    bare = value.lstrip("*.")
    return {
        "domain": bare,
        "wildcard": value if kind == "wildcard" else f"*.{bare}",
        "org": bare.split(".")[0],
        "url": value if kind == "url" else f"https://{bare}",
    }


def render_one(template: str, target_value: str, target_kind: str) -> str:
    vars_ = _vars_for_target(target_value, target_kind)
    out = template
    for key, val in vars_.items():
        out = out.replace("{" + key + "}", val)
    return out.strip()


# Match a trailing operator token like `ext:sql`, `inurl:admin`, `intitle:x`.
_OP_RE = re.compile(r"^(?P<prefix>.*?)(?P<op>\b\w+:)(?P<arg>\S+)\s*$")


def _split_operator(rendered: str) -> tuple[str, str, str] | None:
    m = _OP_RE.match(rendered)
    if not m:
        return None
    return m.group("prefix").strip(), m.group("op"), m.group("arg")


def render_target(dorks: list, target_value: str, target_kind: str, max_merge: int = 8) -> list[RenderedQuery]:
    """Render all dorks for one target, merging where safe.

    `dorks` are objects with .id, .template, .mergeable, .merge_group.
    """
    out: list[RenderedQuery] = []
    # group mergeable dorks by (merge_group, shared prefix, operator)
    buckets: dict[tuple, list] = {}
    singles: list = []

    for d in dorks:
        rendered = render_one(d.template, target_value, target_kind)
        if d.mergeable and d.merge_group:
            parts = _split_operator(rendered)
            if parts:
                prefix, op, arg = parts
                buckets.setdefault((d.merge_group, prefix, op), []).append((d.id, arg))
                continue
        singles.append(RenderedQuery(query=rendered, dork_ids=[d.id], primary_dork_id=d.id))

    for (group, prefix, op), items in buckets.items():
        # chunk by max_merge to respect query length / provider limits
        for i in range(0, len(items), max_merge):
            chunk = items[i:i + max_merge]
            ids = [cid for cid, _ in chunk]
            args = [a for _, a in chunk]
            if len(args) == 1:
                query = f"{prefix} {op}{args[0]}".strip()
            else:
                or_group = " OR ".join(f"{op}{a}" for a in args)
                query = f"{prefix} ({or_group})".strip()
            out.append(RenderedQuery(query=query, dork_ids=ids, primary_dork_id=ids[0]))

    return singles + out
