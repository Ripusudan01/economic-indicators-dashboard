"""
routers/indicators.py — Indicator data endpoints (all 6 panels)

All endpoints require JWT authentication (Bearer token).
Each endpoint reads from the DB (populated by collectors) and returns the
standard IndicatorResponse envelope with source attribution, as_of date,
and is_stale flag.

Missing values (NULL in DB) are returned as None in JSON → displayed as "—" in UI.
Stale data is flagged but still returned — never drop the last known value.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.jwt import get_current_user
from app.models.schemas import (
    IndicatorResponse, Series, DataPoint, SummaryItem
)
from app import database as db
from app.utils.freshness import is_observation_stale

router = APIRouter(prefix="/indicators", tags=["indicators"])


def _rows_to_series(
    rows: list,
    series_keys: list[dict],
    *,
    projected_after_year: int | None = None,
) -> list[Series]:
    """
    Group flat DB rows into Series objects.
    series_keys: [{"key": "india", "label": "India"}, ...]
    """
    from collections import defaultdict
    grouped = defaultdict(list)
    for row in rows:
        period = row["period_label"]
        classification = None
        if projected_after_year is not None and period.isdigit() and int(period) > projected_after_year:
            # A future calendar year cannot be an observed actual. The values endpoint
            # does not distinguish estimates from actuals for elapsed years.
            classification = "projection"
        grouped[row["series_key"]].append(DataPoint(
            period=period,
            value=row["value"],
            classification=classification,
        ))

    result = []
    for sk in series_keys:
        key = sk["key"]
        if key in grouped:
            # Sort by period label
            data = sorted(grouped[key], key=lambda dp: dp.period)
            result.append(Series(series_key=key, label=sk["label"], data=data))
    return result


def _get_staleness(rows: list) -> bool:
    """Check failure flags and observation age on each series' latest point."""
    latest_by_series = {}
    for row in rows:
        key = row["series_key"]
        if key not in latest_by_series or (row["observation_date"] or "") > (latest_by_series[key]["observation_date"] or ""):
            latest_by_series[key] = row
    return any(
        bool(row["is_stale"]) or is_observation_stale(
            row["observation_date"],
            frequency="monthly" if len(row["period_label"]) == 7 and row["period_label"][4] == "-" else "annual",
        )
        for row in latest_by_series.values()
    )


def _latest_fetched_at(rows: list) -> str:
    """Return the most recent fetched_at timestamp from DB rows."""
    if not rows:
        return datetime.now(timezone.utc).isoformat()
    return max(row["fetched_at"] for row in rows)


def _latest_observation(rows: list, *, max_period_year: int | None = None) -> str:
    """Return the most recent observation_date from DB rows."""
    if not rows:
        return "—"
    dates = [
        row["observation_date"] for row in rows
        if row["observation_date"] and (
            max_period_year is None
            or not str(row["period_label"]).isdigit()
            or int(row["period_label"]) <= max_period_year
        )
    ]
    return max(dates) if dates else "—"


def _latest_annual_period(rows: list, *, max_period_year: int) -> str:
    """Return an IMF period label, not a fabricated observation date or future projection."""
    periods = [
        str(row["period_label"]) for row in rows
        if str(row["period_label"]).isdigit() and int(row["period_label"]) <= max_period_year
    ]
    return max(periods) if periods else "—"


def _compute_yoy(series_data: list[DataPoint]) -> float | None:
    """Compute YOY change from the last two data points with values."""
    valid = [dp for dp in series_data if dp.value is not None]
    if len(valid) < 2:
        return None
    return round(valid[-1].value - valid[-2].value, 2)


# ── GDP Growth ─────────────────────────────────────────────────────────────────

@router.get("/gdp-growth", response_model=IndicatorResponse)
def get_gdp_growth(_user=Depends(get_current_user)):
    """GDP Growth — India vs World (YOY%)"""
    rows = db.fetchall(
        """
        SELECT series_key, period_label, value, source, source_url,
               observation_date, fetched_at, is_stale
        FROM indicator_snapshots
        WHERE indicator_name = 'gdp_growth'
        ORDER BY period_label ASC
        """,
    )
    rows = [dict(r) for r in rows]

    series = _rows_to_series(rows, [
        {"key": "india", "label": "India"},
        {"key": "world", "label": "World"},
    ])

    # Build summary from latest data points
    india_series = next((s for s in series if s.series_key == "india"), None)
    world_series = next((s for s in series if s.series_key == "world"), None)

    summary = []
    for s, key_prefix, label in [
        (india_series, "india", "India"),
        (world_series, "world", "World"),
    ]:
        if s and s.data:
            latest = s.data[-1].value
            yoy = _compute_yoy(s.data)
            summary.append(SummaryItem(
                key=f"{key_prefix}_latest",
                label=label,
                value=latest,
                unit="%",
                change=yoy,
                change_unit="pp",
                is_increase=(yoy >= 0) if yoy is not None else None,
            ))

    return IndicatorResponse(
        indicator="gdp_growth",
        title="GDP Growth — India vs World (YOY%)",
        source=rows[0]["source"] if rows else "World Bank API",
        source_url=rows[0]["source_url"] if rows else None,
        as_of=_latest_observation(rows),
        fetched_at=_latest_fetched_at(rows),
        is_stale=_get_staleness(rows),
        series=series,
        summary=summary,
    )


# ── Debt to GDP Ratio ─────────────────────────────────────────────────────────

@router.get("/debt-gdp", response_model=IndicatorResponse)
def get_debt_gdp(_user=Depends(get_current_user)):
    """Debt to GDP Ratio — India and India vs US"""
    rows = db.fetchall(
        """
        SELECT series_key, period_label, value, source, source_url,
               observation_date, fetched_at, is_stale
        FROM indicator_snapshots
        WHERE indicator_name = 'debt_gdp'
        ORDER BY period_label ASC
        """,
    )
    rows = [dict(r) for r in rows]

    current_year = datetime.now(timezone.utc).year
    completed_year = current_year - 1
    series = _rows_to_series(rows, [
        {"key": "india", "label": "India"},
        {"key": "us",    "label": "Ind vs US"},
    ], projected_after_year=current_year)

    summary = []
    for s, key_prefix, label in [
        (next((s for s in series if s.series_key == "india"), None), "india", "India"),
        (next((s for s in series if s.series_key == "us"),    None), "us",    "Ind vs US"),
    ]:
        if s and s.data:
            latest = s.data[-1].value
            yoy = _compute_yoy(s.data)
            summary.append(SummaryItem(
                key=f"{key_prefix}_latest",
                label=label,
                value=latest,
                unit="%",
                change=yoy,
                change_unit="pp",
                is_increase=(yoy >= 0) if yoy is not None else None,
                classification=s.data[-1].classification,
            ))

    from app.collectors.debt import LIMITATION
    return IndicatorResponse(
        indicator="debt_gdp",
        title="Debt to GDP Ratio (IND)",
        source=rows[0]["source"] if rows else "IMF WEO",
        source_url=rows[0]["source_url"] if rows else None,
        as_of=_latest_annual_period(rows, max_period_year=completed_year),
        fetched_at=_latest_fetched_at(rows),
        is_stale=_get_staleness([
            row for row in rows
            if not str(row["period_label"]).isdigit() or int(row["period_label"]) <= completed_year
        ]),
        series=series,
        summary=summary,
        note=LIMITATION,
    )


# ── Imports, Exports, Trade Balance ──────────────────────────────────────────

@router.get("/trade", response_model=IndicatorResponse)
def get_trade(_user=Depends(get_current_user)):
    """Imports, Exports, and Trade Balance for India (USD Billions)"""
    rows = db.fetchall(
        """
        SELECT series_key, period_label, value, source, source_url,
               observation_date, fetched_at, is_stale
        FROM indicator_snapshots
        WHERE indicator_name = 'trade'
        ORDER BY period_label ASC
        """,
    )
    rows = [dict(r) for r in rows]

    series = _rows_to_series(rows, [
        {"key": "exports",       "label": "Exports"},
        {"key": "imports",       "label": "Imports"},
        {"key": "trade_balance", "label": "Trade Balance"},
    ])

    summary = []
    for s, key_prefix, label in [
        (next((s for s in series if s.series_key == "exports"), None),       "exports",  "Exports"),
        (next((s for s in series if s.series_key == "imports"), None),       "imports",  "Imports"),
    ]:
        if s and s.data:
            latest = s.data[-1].value
            yoy = _compute_yoy(s.data)
            summary.append(SummaryItem(
                key=f"{key_prefix}_latest",
                label=label,
                value=latest,
                unit="USD_B",
                change=yoy,
                change_unit="B",
                is_increase=(yoy >= 0) if yoy is not None else None,
            ))

    from app.collectors.trade import LIMITATION
    return IndicatorResponse(
        indicator="trade",
        title="Imports, Exports & Trade Balance",
        source=rows[0]["source"] if rows else "World Bank API",
        source_url=rows[0]["source_url"] if rows else None,
        as_of=_latest_observation(rows),
        fetched_at=_latest_fetched_at(rows),
        is_stale=_get_staleness(rows),
        series=series,
        summary=summary,
        note=LIMITATION,
    )


# ── GST Tax Collection ────────────────────────────────────────────────────────

@router.get("/gst", response_model=IndicatorResponse)
def get_gst(_user=Depends(get_current_user)):
    """GST Tax Collection — annual totals and monthly FY25 data"""
    rows = db.fetchall(
        """
        SELECT series_key, period_label, value, source, source_url,
               observation_date, fetched_at, is_stale
        FROM indicator_snapshots
        WHERE indicator_name = 'gst'
        ORDER BY period_label ASC
        """,
    )
    rows = [dict(r) for r in rows]

    series = _rows_to_series(rows, [
        {"key": "total",   "label": "GST Collections"},
        {"key": "monthly", "label": "Monthly"},
        {"key": "yoy_pct", "label": "YOY %"},
    ])

    # Summary: latest annual total + monthly average for current FY
    total_series = next((s for s in series if s.series_key == "total"), None)
    monthly_series = next((s for s in series if s.series_key == "monthly"), None)

    summary = []
    if total_series and total_series.data:
        latest_annual = total_series.data[-1].value
        yoy_series = next((s for s in series if s.series_key == "yoy_pct"), None)
        yoy = next((dp.value for dp in reversed(yoy_series.data) if dp.value is not None), None) if yoy_series else None
        summary.append(SummaryItem(
            key="gst_collections_latest",
            label="GST Collections",
            value=latest_annual,
            unit="INR_L_CR",
            change=yoy,
            change_unit="%",
            is_increase=(yoy >= 0) if yoy is not None else None,
        ))

    if monthly_series and monthly_series.data:
        valid_monthly = [dp.value for dp in monthly_series.data if dp.value is not None]
        monthly_avg = round(sum(valid_monthly) / len(valid_monthly), 2) if valid_monthly else None
        summary.append(SummaryItem(
            key="monthly_average",
            label="Monthly Average",
            value=monthly_avg,
            unit="INR_L_CR",
            change=None,
            change_unit="",
            is_increase=None,
        ))

    from app.collectors.gst import LIMITATION
    return IndicatorResponse(
        indicator="gst",
        title="GST Tax Collection (YOY%)",
        source=rows[0]["source"] if rows else "GST Council / MoF",
        source_url=rows[0]["source_url"] if rows else None,
        as_of=_latest_observation(rows),
        fetched_at=_latest_fetched_at(rows),
        is_stale=_get_staleness(rows),
        series=series,
        summary=summary,
        note=LIMITATION,
    )


# ── Inflation ─────────────────────────────────────────────────────────────────

@router.get("/inflation", response_model=IndicatorResponse)
def get_inflation(_user=Depends(get_current_user)):
    """Inflation Rate (CPI, India) vs RBI target of 4%"""
    rows = db.fetchall(
        """
        SELECT series_key, period_label, value, source, source_url,
               observation_date, fetched_at, is_stale
        FROM indicator_snapshots
        WHERE indicator_name = 'inflation'
        ORDER BY period_label ASC
        """,
    )
    rows = [dict(r) for r in rows]

    series = _rows_to_series(rows, [
        {"key": "india",      "label": "Inflation Rate"},
        {"key": "rbi_target", "label": "RBI Target"},
    ])

    india_series = next((s for s in series if s.series_key == "india"), None)

    summary = []
    if india_series and india_series.data:
        latest = india_series.data[-1].value
        yoy = _compute_yoy(india_series.data)
        summary.append(SummaryItem(
            key="inflation_rate",
            label="Inflation Rate",
            value=latest,
            unit="%",
            change=yoy,
            change_unit="pp",
            is_increase=(yoy >= 0) if yoy is not None else None,
        ))

    # RBI target is always 4%
    summary.append(SummaryItem(
        key="rbi_target",
        label="RBI Target",
        value=4.0,
        unit="%",
        change=None,
        change_unit="",
        is_increase=None,
    ))

    from app.collectors.inflation import LIMITATION
    return IndicatorResponse(
        indicator="inflation",
        title="Inflation (IND)",
        source=rows[0]["source"] if rows else "World Bank / MOSPI",
        source_url=rows[0]["source_url"] if rows else None,
        as_of=_latest_observation(rows),
        fetched_at=_latest_fetched_at(rows),
        is_stale=_get_staleness(rows),
        series=series,
        summary=summary,
        note=LIMITATION,
    )


# ── Government Expenditure ────────────────────────────────────────────────────

@router.get("/govt-expenditure", response_model=IndicatorResponse)
def get_govt_expenditure(_user=Depends(get_current_user)):
    """Government Expenditure — Total, Revenue, and Capital (% of GDP)"""
    rows = db.fetchall(
        """
        SELECT series_key, period_label, value, source, source_url,
               observation_date, fetched_at, is_stale
        FROM indicator_snapshots
        WHERE indicator_name = 'govt_expenditure'
        ORDER BY period_label ASC
        """,
    )
    rows = [dict(r) for r in rows]

    series = _rows_to_series(rows, [
        {"key": "total",   "label": "Total Expenditure"},
        {"key": "revenue", "label": "Revenue Expenditure"},
        {"key": "capital", "label": "Capital Expenditure"},
    ])

    summary = []
    for s, key_prefix, label in [
        (next((s for s in series if s.series_key == "total"),   None), "total",   "Total Expenditure"),
        (next((s for s in series if s.series_key == "capital"), None), "capital", "Capital Expenditure"),
    ]:
        if s and s.data:
            latest = s.data[-1].value
            yoy = _compute_yoy(s.data)
            summary.append(SummaryItem(
                key=f"{key_prefix}_latest",
                label=label,
                value=latest,
                unit="% of GDP",
                change=yoy,
                change_unit="pp",
                is_increase=(yoy >= 0) if yoy is not None else None,
            ))

    from app.collectors.expenditure import LIMITATION
    return IndicatorResponse(
        indicator="govt_expenditure",
        title="Government Expenditure",
        source=rows[0]["source"] if rows else "World Bank API",
        source_url=rows[0]["source_url"] if rows else None,
        as_of=_latest_observation(rows),
        fetched_at=_latest_fetched_at(rows),
        is_stale=_get_staleness(rows),
        series=series,
        summary=summary,
        note=LIMITATION,
    )
