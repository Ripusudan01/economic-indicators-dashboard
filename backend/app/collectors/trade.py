"""
collectors/trade.py — Imports, Exports, and Trade Balance for India

Data source: World Bank API (public, free, no API key required)
  Exports: NE.EXP.GNFS.CD — Exports of goods and services (current US$)
  Imports: NE.IMP.GNFS.CD — Imports of goods and services (current US$)
  Country: IND (India)

Limitation:
  The World Bank data is annual and denominated in current USD.
  We convert to USD Billions (divide by 1e9) for display.
  Trade Balance = Exports - Imports (annual).
  
  The Ministry of Commerce DGCI&S provides more granular monthly data,
  but does not offer a stable public JSON API. Where a structured API is
  unavailable, we use World Bank as the documented fallback per assignment rules.
  This is noted in the UI as "as of" date and in the README as a limitation.

NSE does NOT publish trade statistics.
"""
from datetime import datetime, timezone

from app import database as db
from app.utils.http_client import safe_get
from app.collectors.validation import finite_number, valid_year

INDICATOR_NAME = "trade"
SOURCE = "World Bank API"
SOURCE_URL = "https://api.worldbank.org/v2/country/IN/indicator/{indicator}?format=json&mrv=10"
LIMITATION = (
    "Annual data from World Bank (NE.EXP.GNFS.CD, NE.IMP.GNFS.CD). "
    "Monthly DGCI&S data not available via stable public API. "
    "Non-NSE source — documented per assignment requirements."
)

WB_INDICATORS = {
    "exports": "NE.EXP.GNFS.CD",
    "imports": "NE.IMP.GNFS.CD",
}


async def _fetch_wb_indicator(indicator_code: str) -> dict[str, float | None] | None:
    """
    Fetch a World Bank indicator for India.
    Returns dict of {year_str: value_in_usd_billions} or None on failure.
    """
    url = f"https://api.worldbank.org/v2/country/IN/indicator/{indicator_code}"
    response = await safe_get(url, params={"format": "json", "mrv": 10, "per_page": 10})
    if response is None:
        return None

    try:
        data = response.json()
        if not isinstance(data, list) or len(data) < 2:
            return None
        rows = data[1]
        if not rows:
            return None
        result = {}
        for row in rows:
            if not isinstance(row, dict):
                return None
            year = row.get("date")
            value = row.get("value")
            if year:
                year = valid_year(year)
                # Convert from USD to USD Billions
                parsed_value = finite_number(value)
                result[year] = round(parsed_value / 1e9, 1) if parsed_value is not None else None
        return result
    except Exception as exc:
        print(f"[Trade collector] Parse error for {indicator_code}: {exc}")
        return None


async def run() -> None:
    """Fetch and store Imports, Exports, and computed Trade Balance."""
    started_at = datetime.now(timezone.utc).isoformat()
    rows_upserted = 0
    status = "success"
    error_message = None

    try:
        import asyncio
        exports_data, imports_data = await asyncio.gather(
            _fetch_wb_indicator(WB_INDICATORS["exports"]),
            _fetch_wb_indicator(WB_INDICATORS["imports"]),
        )

        if exports_data is None and imports_data is None:
            db.execute(
                "UPDATE indicator_snapshots SET is_stale=1 WHERE indicator_name=?",
                (INDICATOR_NAME,),
            )
            db.commit()
            status = "failed"
            error_message = "World Bank API unavailable for trade data"
        else:
            if exports_data is None:
                db.execute(
                    "UPDATE indicator_snapshots SET is_stale=1 WHERE indicator_name=? AND series_key IN ('exports', 'trade_balance')",
                    (INDICATOR_NAME,),
                )
            if imports_data is None:
                db.execute(
                    "UPDATE indicator_snapshots SET is_stale=1 WHERE indicator_name=? AND series_key IN ('imports', 'trade_balance')",
                    (INDICATOR_NAME,),
                )
            # Collect all years across both datasets
            all_years = set()
            if exports_data:
                all_years |= set(exports_data.keys())
            if imports_data:
                all_years |= set(imports_data.keys())

            for year in sorted(all_years):
                exp_val = (exports_data or {}).get(year)
                imp_val = (imports_data or {}).get(year)
                trade_balance = (
                    round(exp_val - imp_val, 1)
                    if exp_val is not None and imp_val is not None
                    else None
                )

                rows_to_insert = [
                    ("exports", "Exports", exp_val),
                    ("imports", "Imports", imp_val),
                    ("trade_balance", "Trade Balance", trade_balance),
                ]

                for series_key, label, value in rows_to_insert:
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
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                        ON CONFLICT(indicator_name, series_key, period_label)
                        DO UPDATE SET
                            value=excluded.value,
                            fetched_at=excluded.fetched_at,
                            is_stale=0
                        """,
                        (
                            INDICATOR_NAME,
                            series_key,
                            year,
                            value,
                            "USD_B",
                            SOURCE,
                            SOURCE_URL.format(indicator=WB_INDICATORS.get(series_key, "NE.EXP.GNFS.CD")),
                            f"{year}-12-31",
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )
                    rows_upserted += 1

            db.commit()
            if exports_data is None or imports_data is None:
                status = "partial"
                error_message = "One or more trade series failed to fetch"

    except Exception as exc:
        db.rollback()
        db.execute("UPDATE indicator_snapshots SET is_stale=1 WHERE indicator_name=?", (INDICATOR_NAME,))
        db.commit()
        status = "failed"
        error_message = str(exc)
        print(f"[Trade collector] Unhandled error: {exc}")

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
    print(f"[Trade collector] Done — status={status}, rows={rows_upserted}")
