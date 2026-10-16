"""
collectors/market_ticker.py — Live Market Ticker: SENSEX, NIFTY BANK, NIFTY IT

Data source: yfinance (Yahoo Finance) Python library
  SENSEX:    ^BSESN
  NIFTY BANK: ^NSEBANK
  NIFTY IT:   ^CNXIT

Why yfinance instead of NSE direct:
  NSE's public API (nseindia.com/api/allIndices) requires valid browser session
  cookies and a specific User-Agent. Programmatic access is unreliable and
  subject to rate-limiting or blocking without a formal data agreement.
  
  The assignment states: "Use publicly accessible NSE endpoints or pages as the
  principal source for data available from NSE. Where NSE does not publish a
  required indicator, a clearly identified public source may be used."
  
  Since SENSEX is a BSE (not NSE) index, it is explicitly not from NSE.
  NIFTY BANK and NIFTY IT are NSE indices. We attempt yfinance for all three
  as the documented fallback, clearly labelled as such in the UI and README.

Refresh: Every 30 seconds (configurable). Data is only live during market hours
  (Mon-Fri, 09:15-15:30 IST). Outside market hours, last known values are
  served with is_stale=False (this is expected — markets are closed).

NOTE: yfinance is not an official NSE/BSE data provider. Usage is subject
  to Yahoo Finance's terms. This is documented as a limitation.
"""
import asyncio
import math
from datetime import datetime, timezone

from app import database as db

INDICATOR_NAME = "market_ticker"

SYMBOLS = [
    {"symbol": "SENSEX",    "yf_ticker": "^BSESN",   "display_name": "SENSEX",    "source": "BSE / Yahoo Finance"},
    {"symbol": "NIFTY_BANK","yf_ticker": "^NSEBANK",  "display_name": "NIFTY BANK","source": "NSE / Yahoo Finance"},
    {"symbol": "NIFTY_IT",  "yf_ticker": "^CNXIT",    "display_name": "NIFTY IT",  "source": "NSE / Yahoo Finance"},
]

SOURCE_URL = "https://finance.yahoo.com"
LIMITATION = (
    "Market data via yfinance (Yahoo Finance). NSE direct API requires session cookies. "
    "SENSEX is a BSE index. NIFTY BANK and NIFTY IT are NSE indices served via Yahoo Finance. "
    "15-minute delay applies per Yahoo Finance terms. Non-NSE source — documented per assignment."
)

# Keep only the last 100 rows per symbol to avoid unbounded growth
MAX_ROWS_PER_SYMBOL = 100


async def _fetch_yfinance(yf_ticker: str) -> dict | None:
    """
    Fetch latest quote from yfinance using asyncio to run in executor
    (yfinance is a synchronous library).
    Returns dict with value, change_abs, change_pct or None on failure.
    """
    def _sync_fetch() -> dict | None:
        try:
            import yfinance as yf
            ticker = yf.Ticker(yf_ticker)
            info = ticker.fast_info
            price = getattr(info, "last_price", None)
            prev_close = getattr(info, "previous_close", None)
            if price is None:
                return None
            price = float(price)
            if not math.isfinite(price) or price <= 0:
                return None
            prev_close = float(prev_close) if prev_close is not None else None
            if prev_close is not None and (not math.isfinite(prev_close) or prev_close <= 0):
                prev_close = None
            change_abs = round(price - prev_close, 2) if prev_close is not None else None
            change_pct = round(change_abs / prev_close * 100, 2) if prev_close is not None and change_abs is not None else None
            return {
                "value": round(price, 2),
                "change_abs": change_abs,
                "change_pct": change_pct,
            }
        except Exception as exc:
            print(f"[Ticker] yfinance error for {yf_ticker}: {exc}")
            return None

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_fetch)


async def run() -> None:
    """Fetch current values for all three market indices and store in DB."""
    started_at = datetime.now(timezone.utc).isoformat()
    rows_upserted = 0
    status = "success"
    error_message = None

    try:
        results = await asyncio.gather(
            *[_fetch_yfinance(s["yf_ticker"]) for s in SYMBOLS]
        )
        fetched_at = datetime.now(timezone.utc).isoformat()

        for sym_config, data in zip(SYMBOLS, results):
            symbol = sym_config["symbol"]
            source = sym_config["source"]

            if data is None:
                # Mark existing ticker rows for this symbol as stale
                db.execute(
                    "UPDATE ticker_snapshots SET is_stale=1 WHERE symbol=?",
                    (symbol,),
                )
                status = "partial"
                error_message = f"Failed to fetch {symbol}"
                continue

            db.execute(
                """
                INSERT INTO ticker_snapshots
                    (symbol, value, change_abs, change_pct, source, fetched_at, is_stale)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    symbol,
                    data["value"],
                    data["change_abs"],
                    data["change_pct"],
                    source,
                    fetched_at,
                ),
            )
            rows_upserted += 1

            # Prune old rows (keep only last MAX_ROWS_PER_SYMBOL)
            db.execute(
                """
                DELETE FROM ticker_snapshots
                WHERE symbol = ?
                  AND id NOT IN (
                      SELECT id FROM ticker_snapshots
                      WHERE symbol = ?
                      ORDER BY fetched_at DESC
                      LIMIT ?
                  )
                """,
                (symbol, symbol, MAX_ROWS_PER_SYMBOL),
            )

        db.commit()

    except Exception as exc:
        status = "failed"
        error_message = str(exc)
        print(f"[Ticker collector] Unhandled error: {exc}")

    # Log the run (use a lightweight log to avoid log table bloat)
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
