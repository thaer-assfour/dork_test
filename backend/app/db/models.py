"""Database models for DorkHub.

Core tables map 1:1 to the data model in PLAN.md:
  programs -> targets -> scans -> scan_items (the coverage table) -> results
  dorks, engines, query_cache, settings are supporting tables.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(300))
    homepage: Mapped[str | None] = mapped_column(String(500), nullable=True)
    policy_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contact_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source: Mapped[str] = mapped_column(String(50))  # disclose_io | projectdiscovery | securitytxt | search | manual
    offers_bounty: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    bounty_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    scope_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="candidate")  # candidate | approved | rejected
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    targets: Mapped[list["Target"]] = relationship(back_populates="program", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("source", "name", name="uq_program_source_name"),)


class Target(Base):
    __tablename__ = "targets"

    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int | None] = mapped_column(ForeignKey("programs.id"), nullable=True)
    value: Mapped[str] = mapped_column(String(300))
    kind: Mapped[str] = mapped_column(String(20), default="domain")  # domain | wildcard | url | ip_range
    in_scope: Mapped[bool] = mapped_column(Boolean, default=True)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    program: Mapped["Program | None"] = relationship(back_populates="targets")

    __table_args__ = (UniqueConstraint("value", name="uq_target_value"),)


class Dork(Base):
    __tablename__ = "dorks"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(120))
    template: Mapped[str] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=2)  # 1 high .. 3 low
    engine_hint: Mapped[str | None] = mapped_column(String(40), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    mergeable: Mapped[bool] = mapped_column(Boolean, default=False)
    merge_group: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (UniqueConstraint("category", "name", name="uq_dork_cat_name"),)


class Engine(Base):
    __tablename__ = "engines"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)
    price_per_1000: Mapped[float] = mapped_column(Numeric(10, 4), default=0)
    free_quota: Mapped[int] = mapped_column(Integer, default=0)
    daily_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    engine_name: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="planned")  # planned|running|paused|done|failed
    estimated_queries: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Numeric(10, 4), default=0)
    actual_queries: Mapped[int] = mapped_column(Integer, default=0)
    actual_cost: Mapped[float] = mapped_column(Numeric(10, 4), default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list["ScanItem"]] = relationship(back_populates="scan", cascade="all, delete-orphan")


class ScanItem(Base):
    """The coverage table: one row per (target, dork) executed in a scan."""

    __tablename__ = "scan_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("scans.id"))
    target_id: Mapped[int] = mapped_column(ForeignKey("targets.id"))
    dork_id: Mapped[int | None] = mapped_column(ForeignKey("dorks.id"), nullable=True)
    rendered_query: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|running|done|error|skipped
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    scan: Mapped["Scan"] = relationship(back_populates="items")


class Result(Base):
    __tablename__ = "results"

    id: Mapped[int] = mapped_column(primary_key=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("targets.id"))
    url: Mapped[str] = mapped_column(String(1000))
    normalized_url: Mapped[str] = mapped_column(String(1000))
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    label: Mapped[str] = mapped_column(String(20), default="new")  # new|reviewing|interesting|false_positive|reported
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    seen_count: Mapped[int] = mapped_column(Integer, default=1)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (UniqueConstraint("target_id", "normalized_url", name="uq_result_target_url"),)


class ResultSighting(Base):
    __tablename__ = "result_sightings"

    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"))
    scan_item_id: Mapped[int] = mapped_column(ForeignKey("scan_items.id"))
    seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class QueryCache(Base):
    __tablename__ = "query_cache"

    id: Mapped[int] = mapped_column(primary_key=True)
    engine_name: Mapped[str] = mapped_column(String(40))
    query_hash: Mapped[str] = mapped_column(String(64))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    payload: Mapped[dict] = mapped_column(JSON)

    __table_args__ = (UniqueConstraint("engine_name", "query_hash", name="uq_cache_engine_hash"),)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
