"""
collectors/debt.py — Debt to GDP Ratio: India (FY25) and India vs US

Data sources:
  Primary: IMF World Economic Outlook (WEO) API — GGXWDG_NGDP
    URL: https://www.imf.org/external/datamapper/api/v1/GGXWDG_NGDP/IND/USA
    This is the General Government Gross Debt as % of GDP (annual).
  
  Fallback / supplementary: World Bank — GC.DOD.TOTL.GD.ZS
    (Central Government debt, % of GDP — less comprehensive than IMF)

Design note: The Figma dashboard shows a date-labeled area chart (Jul 25 → Aug 22).
  This resembles a HIGH-FREQUENCY chart (daily or weekly). However, both IMF WEO
  and World Bank provide only ANNUAL fiscal-year data. We use annual data and label
  the x-axis accordingly. The chart shape will match the design reference as a
  multi-year trend. This design decision is documented in the README.

Countries: IND (India), USA (US for comparison)
NSE does NOT publish this data. IMF WEO is the legitimate alternate source.
"""
from datetime import datetime, timezone

from app import database as db
from app.utils.http_client import safe_get
from app.collectors.validation import finite_number, valid_year

INDICATOR_NAME = "debt_gdp"
SOURCE = "IMF World Economic Outlook (WEO)"
SOURCE_URL = "https://www.imf.org/external/datamapper/api/v1/GGXWDG_NGDP/IND/USA"
IMF_INDICATOR = "GGXWDG_NGDP"

LIMITATION = (
    "Annual IMF WEO general government gross debt (% of GDP); recent periods may be estimates or projections. "
    "The design reference shows a date-labeled chart; we render annual data points. "
    "Non-NSE source."
)


async def _fetch_imf_debt() -> dict | None:
    """
    Fetch Debt/GDP from the IMF DataMapper API.
    Returns dict with 'IND' and 'USA' lists, or None on failure.
    """
    response = await safe_get(SOURCE_URL)
    if response is None:
        return None

    try:
        data = response.json()
        # IMF DataMapper returns: {"values": {"GGXWDG_NGDP": {"IND": {year: value, ...}, "USA": {...}}}}
        values = data.get("values", {}).get(IMF_INDICATOR, {})
        if not isinstance(values, dict):
            return None
        return values  # dict: {"IND": {"2020": 89.0, ...}, "USA": {...}}
    except Exception as exc:
        print(f"[Debt collector] Parse error: {exc}")
        return None


async def run() -> None:
    """Fetch and store Debt/GDP data for India and USA."""
    started_at = datetime.now(timezone.utc).isoformat()
    rows_upserted = 0
    status = "success"
    error_message = None

    try:
        imf_data = await _fetch_imf_debt()

        if imf_data is None:
            # Mark all existing rows as stale
            db.execute(
                "UPDATE indicator_snapshots SET is_stale=1 WHERE indicator_name=?",
                (INDICATOR_NAME,),
            )
            db.commit()
            status = "failed"
            error_message = "IMF API unavailable"
        else:
            series_map = {
                "india": ("IND", "India"),
                "us": ("USA", "Ind vs US"),
            }

            for series_key, (country_code, label) in series_map.items():
                country_data = imf_data.get(country_code, {})
                if not isinstance(country_data, dict) or not country_data:
                    db.execute(
                        "UPDATE indicator_snapshots SET is_stale=1 WHERE indicator_name=? AND series_key=?",
                        (INDICATOR_NAME, series_key),
                    )
                    db.commit()
                    status = "partial"
                    error_message = f"No data for {country_code}"
                    continue

                for year_str, value in country_data.items():
                    year_str = valid_year(year_str)
                    value = finite_number(value)
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
                            year_str,
                            value,
                            "%",
                            SOURCE,
                            SOURCE_URL,
                            f"{year_str}-03-31",  # Indian fiscal year end
                            datetime.now(timezone.utc).isoformat(),
                            1 if value is None else 0,
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
        print(f"[Debt collector] Unhandled error: {exc}")

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
    print(f"[Debt collector] Done — status={status}, rows={rows_upserted}")
