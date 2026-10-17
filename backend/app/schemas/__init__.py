"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- auth ----
class LoginIn(BaseModel):
    password: str


# ---- discovery ----
class DiscoverIn(BaseModel):
    source: str  # disclose_io | projectdiscovery
    only_self_hosted: bool = True


class ManualProgramIn(BaseModel):
    name: str
    policy_url: str
    contact_url: str | None = None
    homepage: str | None = None
    scope_text: str | None = None


class ProgramOut(ORMModel):
    id: int
    name: str
    homepage: str | None
    policy_url: str | None
    contact_url: str | None
    source: str
    offers_bounty: bool | None
    bounty_confidence: float
    status: str
    notes: str | None
    discovered_at: datetime


class ProgramStatusIn(BaseModel):
    status: str  # approved | rejected | candidate


# ---- targets ----
class TargetIn(BaseModel):
    value: str
    kind: str = "domain"
    program_id: int | None = None
    in_scope: bool = True
    approved: bool = False


class TargetOut(ORMModel):
    id: int
    program_id: int | None
    value: str
    kind: str
    in_scope: bool
    approved: bool
    notes: str | None
    added_at: datetime


class ApproveIn(BaseModel):
    approved: bool


# ---- dorks ----
class DorkOut(ORMModel):
    id: int
    category: str
    name: str
    template: str
    priority: int
    enabled: bool
    mergeable: bool
    merge_group: str | None
    description: str | None


class DorkToggleIn(BaseModel):
    enabled: bool


# ---- scans ----
class EstimateIn(BaseModel):
    target_ids: list[int]
    dork_ids: list[int]
    engine: str


class EstimateOut(BaseModel):
    engine: str
    raw_count: int
    merged_count: int
    billable_count: int
    cached_count: int
    estimated_cost: float
    warn: bool


class ScanRunIn(EstimateIn):
    pass


class ScanOut(ORMModel):
    id: int
    created_at: datetime
    engine_name: str
    status: str
    estimated_queries: int
    estimated_cost: float
    actual_queries: int
    actual_cost: float


class ResultOut(ORMModel):
    id: int
    target_id: int
    url: str
    title: str | None
    snippet: str | None
    label: str
    notes: str | None
    seen_count: int
    first_seen: datetime
    last_seen: datetime


class ResultLabelIn(BaseModel):
    label: str
    notes: str | None = None
