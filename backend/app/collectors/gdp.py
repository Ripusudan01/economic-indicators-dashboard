"""
collectors/gdp.py — GDP Growth: India vs World (Year-on-Year %)

Data source: World Bank API (public, free, no API key required)
  Indicator: NY.GDP.MKTP.KD.ZG — GDP growth (annual %)
  Countries: IND (India), WLD (World aggregate)
  URL: https://api.worldbank.org/v2/country/{code}/indicator/NY.GDP.MKTP.KD.ZG

NSE does NOT publish GDP data. World Bank is the legitimate alternate source.
This is documented in the README and displayed in the UI as "as of" date.

Observation: Annual data. Latest available year is typically 1-2 years behind
             (e.g., in 2025, the latest confirmed data is often 2023 or 2024).
             We store the observation_date as the last year for which data exists.
"""
import asyncio
from datetime import datetime, timezone

from app import database as db
from app.utils.http_client import safe_get
from app.collectors.validation import finite_number, valid_year

INDICATOR_NAME = "gdp_growth"
SOURCE = "World Bank API"
SOURCE_URL = "https://api.worldbank.org/v2/country/{code}/indicator/NY.GDP.MKTP.KD.ZG?format=json&mrv=10"
WB_INDICATOR = "NY.GDP.MKTP.KD.ZG"

SERIES_CONFIG = [
    {"series_key": "india", "label": "India", "country_code": "IN"},
    {"series_key": "world", "label": "World", "country_code": "WLD"},
]

# Fetch last 10 years of data from World Bank
YEARS_TO_FETCH = 10


async def _fetch_country_gdp(country_code: str) -> list[dict] | None:
    """
    Fetch GDP growth data for one country from the World Bank API.
    Returns a list of {period_label, value, observation_date} dicts, or None on failure.
    """
    url = f"https://api.worldbank.org/v2/country/{country_code}/indicator/{WB_INDICATOR}"
    response = await safe_get(
        url,
        params={"format": "json", "mrv": YEARS_TO_FETCH, "per_page": YEARS_TO_FETCH},
    )
    if response is None:
        return None

    try:
        data = response.json()
        # World Bank returns [metadata, [data_rows]]
        if not isinstance(data, list) or len(data) < 2:
            return None
        rows = data[1]
        if not rows:
            return None

        results = []
        for row in rows:
            if not isinstance(row, dict):
                return None
            year = row.get("date")
            value = row.get("value")  # can be None if data not yet released
            if year:
                year = valid_year(year)
                results.append({
                    "period_label": year,
                    "value": finite_number(value),
                    "observation_date": f"{year}-12-31",  # annual data, end of year
                })
        return results
    except Exception as exc:
        print(f"[GDP collector] Parse error for {country_code}: {exc}")
        return None


async def run() -> None:
    """
    Main collector entry point. Fetches GDP data for India and World,
    upserts to DB, and logs the run. Sets is_stale=1 on failure.
    """
    started_at = datetime.now(timezone.utc).isoformat()
    rows_upserted = 0
    status = "success"
    error_message = None

    try:
        # Fetch both series concurrently
        india_data, world_data = await asyncio.gather(
            _fetch_country_gdp("IN"),
            _fetch_country_gdp("WLD"),
        )

        series_results = [
            ("india", "India", india_data),
            ("world", "World", world_data),
        ]

        for series_key, label, data in series_results:
            if data is None:
                # Mark existing rows for this series as stale
                db.execute(
                    "UPDATE indicator_snapshots SET is_stale=1 WHERE indicator_name=? AND series_key=?",
                    (INDICATOR_NAME, series_key),
                )
                db.commit()
                status = "partial"
                error_message = f"Failed to fetch {series_key} data"
                continue

            for row in data:
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
                        series_key,
                        row["period_label"],
                        row["value"],
                        "%",
                        SOURCE,
                        SOURCE_URL.format(code="IN" if series_key == "india" else "WLD"),
                        row["observation_date"],
                        datetime.now(timezone.utc).isoformat(),
                        1 if row["value"] is None else 0,
                    ),
                )
                rows_upserted += 1

        db.commit()

    except Exception as exc:
        db.rollback()
        db.execute("UPDATE indicator_snapshots SET is_stale=1 WHERE indicator_name=?", (INDICATOR_NAME,))
        db.commit()
        status = "failed"
        error_message = str(exc)
        print(f"[GDP collector] Unhandled error: {exc}")

    # Log the run
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
    print(f"[GDP collector] Done — status={status}, rows={rows_upserted}")
