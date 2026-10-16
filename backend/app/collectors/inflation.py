"""
collectors/inflation.py — Inflation Rate: India (CPI) vs RBI Target

Data sources:
  Primary: World Bank API — FP.CPI.TOTL.ZG (Inflation, consumer prices, annual %)
    URL: https://api.worldbank.org/v2/country/IN/indicator/FP.CPI.TOTL.ZG
    This is the annual average CPI inflation rate for India.

  RBI Target: Fixed at 4% (median of 2%-6% band set by the Monetary Policy Committee).
    This is a fixed known value — no API needed.
    Reference: https://www.rbi.org.in/Scripts/PublicationsView.aspx?id=20737

Limitation:
  Annual CPI data from World Bank (sourced from MOSPI). Most recent year may be
  1 year behind (e.g., in 2025, 2024 data may not yet be confirmed in World Bank DB).
  Monthly CPI is published by MOSPI (mospi.gov.in) but has no stable public API.
  Non-NSE source — documented per assignment requirements.
"""
from datetime import datetime, timezone

from app import database as db
from app.utils.http_client import safe_get
from app.collectors.validation import finite_number, valid_year

INDICATOR_NAME = "inflation"
SOURCE = "World Bank API / MOSPI"
SOURCE_URL = "https://api.worldbank.org/v2/country/IN/indicator/FP.CPI.TOTL.ZG?format=json&mrv=10"
RBI_TARGET_URL = "https://rbi.org.in"
LIMITATION = (
    "Annual CPI inflation from World Bank (sourced from MOSPI). "
    "RBI target is the fixed 4% mandate of the Monetary Policy Committee. "
    "Non-NSE source — documented per assignment requirements."
)

RBI_TARGET_PCT = 4.0   # Fixed; set by MPC, unchanged since 2016 framework
WB_INDICATOR = "FP.CPI.TOTL.ZG"


async def run() -> None:
    """Fetch India CPI inflation (annual) and store alongside the fixed RBI target."""
    started_at = datetime.now(timezone.utc).isoformat()
    rows_upserted = 0
    status = "success"
    error_message = None

    try:
        url = f"https://api.worldbank.org/v2/country/IN/indicator/{WB_INDICATOR}"
        response = await safe_get(url, params={"format": "json", "mrv": 10, "per_page": 10})

        if response is None:
            db.execute(
                "UPDATE indicator_snapshots SET is_stale=1 WHERE indicator_name=?",
                (INDICATOR_NAME,),
            )
            db.commit()
            status = "failed"
            error_message = "World Bank API unavailable for CPI data"
        else:
            data = response.json()
            if isinstance(data, list) and len(data) >= 2 and data[1]:
                rows = data[1]
                fetched_at = datetime.now(timezone.utc).isoformat()

                for row in rows:
                    if not isinstance(row, dict):
                        raise ValueError("Unexpected World Bank row format")
                    year = row.get("date")
                    value = row.get("value")
                    if not year:
                        continue
                    year = valid_year(year)
                    value = finite_number(value)

                    # Actual CPI inflation
                    db.execute(
                        """
                        INSERT INTO indicator_snapshots
                            (indicator_name, series_key, period_label, value, unit,
                             source, source_url, observation_date, fetched_at, is_stale)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(indicator_name, series_key, period_label)
                        DO UPDATE SET
                            value=COALESCE(excluded.value, indicator_snapshots.value),
                            fetched_at=CASE WHEN excluded.value IS NULL THEN indicator_snapshots.fetched_at ELSE excluded.fetched_at END,
                            is_stale=CASE WHEN excluded.value IS NULL THEN 1 ELSE 0 END
                        """,
                        (
                            INDICATOR_NAME,
                            "india",
                            str(year),
                            float(value) if value is not None else None,
                            "%",
                            SOURCE,
                            SOURCE_URL,
                            f"{year}-12-31",
                            fetched_at,
                            1 if value is None else 0,
                        ),
                    )
                    rows_upserted += 1

                    # RBI target for the same year (static value, always 4%)
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
                            "rbi_target",
                            str(year),
                            RBI_TARGET_PCT,
                            "%",
                            "RBI Monetary Policy Committee (fixed mandate)",
                            RBI_TARGET_URL,
                            f"{year}-12-31",
                            fetched_at,
                        ),
                    )
                    rows_upserted += 1

                db.commit()
            else:
                status = "partial"
                error_message = "Unexpected World Bank response format"

    except Exception as exc:
        db.rollback()
        db.execute("UPDATE indicator_snapshots SET is_stale=1 WHERE indicator_name=?", (INDICATOR_NAME,))
        db.commit()
        status = "failed"
        error_message = str(exc)
        print(f"[Inflation collector] Unhandled error: {exc}")

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
    print(f"[Inflation collector] Done — status={status}, rows={rows_upserted}")
