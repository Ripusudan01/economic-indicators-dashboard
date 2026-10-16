"""Store a curated, static GST series taken from PIB/MoF publications.

The implementation does not query PIB, GST Council, or RBI. Its monthly data
ends in February 2025; annual data ends in FY2024-25. The linked PIB explainer
confirms annual totals, while the monthly values are retained from the cited
release series and have not been independently refreshed here.
"""
import calendar
from datetime import datetime, timezone

from app import database as db
from app.utils.freshness import is_observation_stale

INDICATOR_NAME = "gst"
SOURCE = "GST Council / Ministry of Finance (Press Releases)"
SOURCE_URL = "https://www.pib.gov.in/PressNoteDetails.aspx?ModuleId=3&NoteId=154789&id=154789&lang=2&reg=3"

LIMITATION = (
    "Curated static figures from PIB/MoF publications; this collector does not fetch live GST data. "
    "The monthly series ends in February 2025 and annual series in FY2024-25. "
    "Annual chart line values show annual total divided by 12, not actual monthly observations. "
    "Non-NSE source."
)

# ── Real GST collection data from GST Council press releases ──────────────────
# Source: PIB press releases / GST Council official communications
# Values in INR Lakh Crore (₹ Lakh Crore = ₹ 100,000 Crore)
# Annual totals (FY = April–March)
GST_ANNUAL_DATA = {
    "FY21": 11.37,   # FY 2020-21: ₹11.37 Lakh Crore
    "FY22": 14.83,   # FY 2021-22: ₹14.83 Lakh Crore
    "FY23": 18.08,   # FY 2022-23: ₹18.08 Lakh Crore
    "FY24": 20.18,   # FY 2023-24: ₹20.18 Lakh Crore
    "FY25": 22.08,   # FY 2024-25: ₹22.08 Lakh Crore
}

# Monthly data for FY25 (April 2024 – latest available)
# Source: GST Council official press releases (PIB)
GST_MONTHLY_FY25 = {
    "2024-04": 2.10,   # April 2024: ₹2.10 Lakh Crore
    "2024-05": 1.73,   # May 2024
    "2024-06": 1.74,   # June 2024
    "2024-07": 1.82,   # July 2024
    "2024-08": 1.75,   # August 2024
    "2024-09": 1.73,   # September 2024
    "2024-10": 1.87,   # October 2024
    "2024-11": 1.82,   # November 2024
    "2024-12": 1.77,   # December 2024
    "2025-01": 1.96,   # January 2025
    "2025-02": 1.83,   # February 2025
}


def _compute_yoy(current: float | None, previous: float | None) -> float | None:
    """Compute year-over-year percentage change."""
    if current is None or previous is None or previous == 0:
        return None
    return round((current - previous) / previous * 100, 2)


async def run() -> None:
    """Store GST annual and monthly data with YOY calculation."""
    started_at = datetime.now(timezone.utc).isoformat()
    rows_upserted = 0
    status = "success"
    error_message = None

    try:
        fetched_at = datetime.now(timezone.utc).isoformat()

        # Store annual totals
        annual_keys = sorted(GST_ANNUAL_DATA.keys())
        for i, fy in enumerate(annual_keys):
            value = GST_ANNUAL_DATA[fy]
            prev_fy = annual_keys[i - 1] if i > 0 else None
            yoy = _compute_yoy(value, GST_ANNUAL_DATA.get(prev_fy) if prev_fy else None)

            # Extract fiscal year for observation_date
            # FY25 = April 2024 – March 2025, observation = 2025-03-31
            fy_num = int(fy[2:]) + 2000
            observation_date = f"{fy_num}-03-31"
            stale = int(is_observation_stale(observation_date))

            for sk, val in [("total", value), ("yoy_pct", yoy)]:
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
                        sk,
                        fy,
                        val,
                        "INR_L_CR" if sk == "total" else "%",
                        SOURCE,
                        SOURCE_URL,
                        observation_date,
                        fetched_at,
                        stale,
                    ),
                )
                rows_upserted += 1

        # Store monthly data for FY25
        monthly_keys = sorted(GST_MONTHLY_FY25.keys())
        for i, month in enumerate(monthly_keys):
            value = GST_MONTHLY_FY25[month]
            observed = f"{month}-{calendar.monthrange(int(month[:4]), int(month[5:7]))[1]:02d}"
            stale = int(is_observation_stale(observed, frequency="monthly"))
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
                    "monthly",
                    month,
                    value,
                    "INR_L_CR",
                    SOURCE,
                    SOURCE_URL,
                    observed,
                    fetched_at,
                    stale,
                ),
            )
            rows_upserted += 1

        db.commit()

    except Exception as exc:
        status = "failed"
        error_message = str(exc)
        print(f"[GST collector] Unhandled error: {exc}")

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
    print(f"[GST collector] Done — status={status}, rows={rows_upserted}")
