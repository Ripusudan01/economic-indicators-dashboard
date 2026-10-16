"""
models/schemas.py — Pydantic response models for all API endpoints.

These define the exact JSON shape the frontend receives.
Using strict models ensures responses are validated before leaving the server.
"""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel


# ── Generic response envelope ──────────────────────────────────────────────────

class DataPoint(BaseModel):
    period: str           # '2021', 'FY25', '2024-08', etc.
    value: float | None   # None → displayed as '—' in UI


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


class IndicatorResponse(BaseModel):
    indicator: str
    title: str
    source: str
    source_url: str | None
    as_of: str            # ISO date string (observation date of latest data)
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
    is_stale: bool


class TickerResponse(BaseModel):
    items: list[TickerItem]
    as_of: str


# ── Health check ──────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str           # 'ok' | 'degraded'
    db: str               # 'ok' | 'error'
    version: str
    timestamp: str
