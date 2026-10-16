"""
models/schemas.py — Pydantic response models for all API endpoints.

These define the exact JSON shape the frontend receives.
Using strict models ensures responses are validated before leaving the server.
"""
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel


# ── Generic response envelope ──────────────────────────────────────────────────

class DataPoint(BaseModel):
    period: str           # '2021', 'FY25', '2024-08', etc.
    value: float | None   # None → displayed as '—' in UI
    classification: Literal["actual", "estimate", "projection"] | None = None


class Series(BaseModel):
    series_key: str       # 'india', 'world', 'exports', etc.
    label: str            # Human-readable label
    data: list[DataPoint]


class SummaryItem(BaseModel):
    key: str              # 'india_latest', 'rbi_target', etc.
    label: str
    value: float | None
    unit: str             # '%', 'USD_B', 'INR_L_CR'
    change: float | None  # YOY or period-over-period change
    change_unit: str      # 'pp' (percentage points), '%', 'abs'
    is_increase: bool | None  # True = green ▲, False = red ▼, None = neutral
    classification: Literal["actual", "estimate", "projection"] | None = None


class IndicatorResponse(BaseModel):
    indicator: str
    title: str
    source: str
    source_url: str | None
    as_of: str            # latest observation date or annual period label, depending on source
    fetched_at: str       # ISO datetime when backend last fetched
    is_stale: bool        # True → show stale badge in UI
    series: list[Series]
    summary: list[SummaryItem]
    note: str | None = None  # Any limitation or assumption to display


# ── Market ticker ─────────────────────────────────────────────────────────────

class TickerItem(BaseModel):
    symbol: str           # 'SENSEX', 'NIFTY_BANK', 'NIFTY_IT'
    display_name: str     # 'SENSEX', 'NIFTY BANK', 'NIFTY IT'
    value: float | None
    change_abs: float | None
    change_pct: float | None
    is_up: bool | None    # True = green, False = red
    source: str
    fetched_at: str
    observation_date: str | None = None
    is_stale: bool
    status: Literal["fresh", "delayed", "stale", "unavailable"] = "unavailable"


class TickerResponse(BaseModel):
    items: list[TickerItem]
    as_of: str


# ── Health check ──────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str           # 'ok' | 'degraded'
    db: str               # 'ok' | 'error'
    version: str
    timestamp: str
