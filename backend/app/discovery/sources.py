"""Program discovery sources.

Each source yields candidate dicts with a common shape:
  {name, homepage, policy_url, contact_url, scope_text, source}
Only self-hosted candidates (not on a known platform) are kept. The user later
approves which candidates become real programs/targets.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import httpx

from app.discovery.classifier import classify_bounty, is_self_hosted

DISCLOSE_IO_URL = "https://raw.githubusercontent.com/disclose/diodb/master/program-list.json"
PROJECTDISCOVERY_URL = (
    "https://raw.githubusercontent.com/projectdiscovery/public-bugbounty-programs/main/chaos-bugbounty-list.json"
)


@dataclass
class Candidate:
    name: str
    source: str
    homepage: str | None = None
    policy_url: str | None = None
    contact_url: str | None = None
    scope_text: str | None = None
    offers_bounty: bool | None = None
    bounty_confidence: float = 0.0
    domains: list[str] | None = None

    def finalize(self) -> "Candidate":
        self.offers_bounty, self.bounty_confidence = classify_bounty(self.scope_text)
        return self


def _get_json(url: str, timeout: float = 30.0):
    resp = httpx.get(url, timeout=timeout, follow_redirects=True)
    resp.raise_for_status()
    return resp.json()


def fetch_disclose_io(only_self_hosted: bool = True) -> list[dict]:
    data = _get_json(DISCLOSE_IO_URL)
    rows = data if isinstance(data, list) else data.get("programs", [])
    out: list[Candidate] = []
    for r in rows:
        policy = r.get("policy_url")
        contact = r.get("contact_url")
        home = r.get("launch_date") and None or r.get("url") or policy
        if only_self_hosted and not is_self_hosted(policy, contact, home):
            continue
        out.append(Candidate(
            name=r.get("program_name") or r.get("name") or "unknown",
            source="disclose_io",
            homepage=home,
            policy_url=policy,
            contact_url=contact,
            scope_text=r.get("preferred_languages") and None or (policy or ""),
            offers_bounty=r.get("offers_bounty"),
        ).finalize())
    return [asdict(c) for c in out]


def fetch_projectdiscovery(only_self_hosted: bool = True) -> list[dict]:
    data = _get_json(PROJECTDISCOVERY_URL)
    programs = data.get("programs", []) if isinstance(data, dict) else data
    out: list[Candidate] = []
    for p in programs:
        url = p.get("url")
        if only_self_hosted and not is_self_hosted(url, None, url):
            continue
        out.append(Candidate(
            name=p.get("name", "unknown"),
            source="projectdiscovery",
            homepage=url,
            policy_url=url,
            offers_bounty=p.get("bounty"),
            domains=p.get("domains") or [],
        ))
    return [asdict(c) for c in out]


def manual_candidate(name: str, policy_url: str, contact_url: str | None = None,
                     homepage: str | None = None, scope_text: str | None = None) -> dict:
    c = Candidate(
        name=name, source="manual", policy_url=policy_url,
        contact_url=contact_url, homepage=homepage or policy_url, scope_text=scope_text,
    ).finalize()
    return asdict(c)


SOURCES = {
    "disclose_io": fetch_disclose_io,
    "projectdiscovery": fetch_projectdiscovery,
}
