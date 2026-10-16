"""
collectors/expenditure.py — Government Expenditure: Total and Capital

Data source: World Bank API (public, free, no API key required)
  Expense: GC.XPN.TOTL.GD.ZS — central government expense (% of GDP)
  Net investment: GC.NFN.TOTL.GD.ZS — net investment in nonfinancial assets (% of GDP)

  Revenue expenditure is represented by expense. Capital expenditure is proxied by
  net investment in nonfinancial assets. Total is the sum of those two series.
  This is a GFS proxy, not a direct Union Budget capital/revenue expenditure split.

  The Ministry of Finance (indiabudget.gov.in) publishes more detailed Union Budget
  data in absolute INR terms. However, no structured JSON API is available from MoF.
  World Bank is used as the documented public fallback per assignment rules.

Limitation:
  Annual fiscal data from World Bank. Most recent year may be 1-2 years behind.
  Absolute INR values from Union Budget are not available via stable public API.
  Non-NSE source — documented per assignment requirements.
"""
from datetime import datetime, timezone

import asyncio
from app import database as db
from app.utils.http_client import safe_get
from app.collectors.validation import finite_number, valid_year
from app.utils.freshness import is_observation_stale

INDICATOR_NAME = "govt_expenditure"
SOURCE = "World Bank API (GC.XPN.TOTL.GD.ZS / GC.NFN.TOTL.GD.ZS)"
SOURCE_URL = "https://api.worldbank.org/v2/country/IN/indicator/GC.XPN.TOTL.GD.ZS?format=json&mrv=10"
LIMITATION = (
    "Annual World Bank government finance data. Revenue expenditure is proxied by expense; "
    "capital expenditure is proxied by net investment in nonfinancial assets; total is their sum. "
    "These GFS measures are not the Union Budget's direct revenue/capital expenditure split. "
    "Non-NSE source."
)

WB_EXPENSE_PCT_GDP = "GC.XPN.TOTL.GD.ZS"
WB_NET_INVESTMENT_PCT_GDP = "GC.NFN.TOTL.GD.ZS"


async def _fetch_wb(indicator_code: str) -> dict[str, float | None] | None:
    """Fetch a World Bank indicator for India. Returns {year: value} or None."""
    url = f"https://api.worldbank.org/v2/country/IN/indicator/{indicator_code}"
    response = await safe_get(url, params={"format": "json", "mrv": 10, "per_page": 10})
    if response is None:
        return None
    try:
        data = response.json()
        if not isinstance(data, list) or len(data) < 2 or not data[1]:
            return None
        result = {}
        for row in data[1]:
            if not isinstance(row, dict):
                return None
            if row.get("date"):
                result[valid_year(row["date"])] = finite_number(row.get("value"))
        return result
    except Exception as exc:
        print(f"[Expenditure collector] Parse error for {indicator_code}: {exc}")
        return None


async def run() -> None:
    """Fetch and store Total and Capital expenditure data for India."""
    started_at = datetime.now(timezone.utc).isoformat()
    rows_upserted = 0
    status = "success"
    error_message = None

    try:
        expense_data, net_investment_data = await asyncio.gather(
            _fetch_wb(WB_EXPENSE_PCT_GDP),
            _fetch_wb(WB_NET_INVESTMENT_PCT_GDP),
        )

        if expense_data is None and net_investment_data is None:
            db.execute(
                "UPDATE indicator_snapshots SET is_stale=1 WHERE indicator_name=?",
                (INDICATOR_NAME,),
            )
            db.commit()
            status = "failed"
            error_message = "World Bank API unavailable for expenditure data"
        else:
            if expense_data is None:
                db.execute(
                    "UPDATE indicator_snapshots SET is_stale=1 WHERE indicator_name=? AND series_key='total'",
                    (INDICATOR_NAME,),
                )
            if net_investment_data is None:
                db.execute(
                    "UPDATE indicator_snapshots SET is_stale=1 WHERE indicator_name=? AND series_key IN ('capital', 'revenue')",
                    (INDICATOR_NAME,),
                )
            all_years = set()
            if expense_data:
                all_years |= set(expense_data.keys())
            if net_investment_data:
                all_years |= set(net_investment_data.keys())

            fetched_at = datetime.now(timezone.utc).isoformat()

            for year in sorted(all_years):
                revenue_gdp = (expense_data or {}).get(year)
                capital_gdp = (net_investment_data or {}).get(year)
                total = (
                    round(revenue_gdp + capital_gdp, 3)
                    if revenue_gdp is not None and capital_gdp is not None
                    else None
                )

                rows_to_insert = [
                    ("total", "Total Expenditure", total),
                    ("capital", "Capital Expenditure", capital_gdp),
                    ("revenue", "Revenue Expenditure", revenue_gdp),
                ]

                for series_key, label, value in rows_to_insert:
                    observed = f"{year}-03-31"
                    if value is None:
                        db.execute(
                            "UPDATE indicator_snapshots SET is_stale=1 WHERE indicator_name=? AND series_key=? AND period_label=?",
                            (INDICATOR_NAME, series_key, year),
                        )
                        continue
                    db.execute(
                        """
                        INSERT INTO indicator_snapshots
                            (indicator_name, series_key, period_label, value, unit,
                             source, source_url, observation_date, fetched_at, is_stale)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(indicator_name, series_key, period_label)
                        DO UPDATE SET
                            value=excluded.value,
                            fetched_at=excluded.fetched_at,
                            observation_date=excluded.observation_date,
                            is_stale=excluded.is_stale
                        """,
                        (
                            INDICATOR_NAME,
                            series_key,
                            year,
                            value,
                            "% of GDP",
                            SOURCE,
                            SOURCE_URL,
                            observed,  # Indian fiscal year end
                            fetched_at,
                            int(is_observation_stale(observed)),
                        ),
                    )
                    rows_upserted += 1

            db.commit()
            if expense_data is None or net_investment_data is None:
                status = "partial"
                error_message = "One expenditure series failed"

    except Exception as exc:
        db.rollback()
        db.execute("UPDATE indicator_snapshots SET is_stale=1 WHERE indicator_name=?", (INDICATOR_NAME,))
        db.commit()
        status = "failed"
        error_message = str(exc)
        print(f"[Expenditure collector] Unhandled error: {exc}")

    db.execute(
        """
        INSERT INTO collector_runs
            (collector_name, started_at, finished_at, status, error_message, rows_upserted)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            INDICATOR_NAME,
            started_at,
            datetime.now(timezone.utc).isoformat(),
            status,
            error_message,
            rows_upserted,
        ),
    )
    db.commit()
    print(f"[Expenditure collector] Done — status={status}, rows={rows_upserted}")
