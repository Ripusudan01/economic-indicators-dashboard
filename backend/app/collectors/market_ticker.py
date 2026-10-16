"""
collectors/market_ticker.py — Live Market Ticker: SENSEX, NIFTY BANK, NIFTY IT

Data source: yfinance (Yahoo Finance) Python library
  SENSEX:    ^BSESN
  NIFTY BANK: ^NSEBANK
  NIFTY IT:   ^CNXIT

Why yfinance instead of NSE direct:
  A direct request to NSE's allIndices endpoint could not be verified from the
  development environment, and no stable supported unauthenticated interface
  was established. This collector keeps the documented fallback rather than
  scraping an unsupported endpoint.
  
  The assignment states: "Use publicly accessible NSE endpoints or pages as the
  principal source for data available from NSE. Where NSE does not publish a
  required indicator, a clearly identified public source may be used."
  
  Since SENSEX is a BSE (not NSE) index, it is explicitly not from NSE.
  NIFTY BANK and NIFTY IT are NSE indices. We attempt yfinance for all three
  as the documented fallback, clearly labelled as such in the UI and README.

Refresh: Every 30 seconds (configurable). Yahoo Finance may return delayed
  quotes; these are never represented as real-time. Failed refreshes preserve
  the last quote and mark it stale.

NOTE: yfinance is not an official NSE/BSE data provider. Usage is subject
  to Yahoo Finance's terms. This is documented as a limitation.
"""
import asyncio
import math
from datetime import date, datetime, timezone

from app import database as db

INDICATOR_NAME = "market_ticker"

SYMBOLS = [
    {"symbol": "SENSEX",    "yf_ticker": "^BSESN",   "display_name": "SENSEX",    "source": "BSE / Yahoo Finance"},
    {"symbol": "NIFTY_BANK","yf_ticker": "^NSEBANK",  "display_name": "NIFTY BANK","source": "NSE / Yahoo Finance"},
    {"symbol": "NIFTY_IT",  "yf_ticker": "^CNXIT",    "display_name": "NIFTY IT",  "source": "NSE / Yahoo Finance"},
]

SOURCE_URL = "https://finance.yahoo.com"
LIMITATION = (
    "Market data via yfinance (Yahoo Finance). Direct NSE API access was not established in the development environment. "
    "SENSEX is a BSE index. NIFTY BANK and NIFTY IT are NSE indices served via Yahoo Finance. "
    "Yahoo Finance quotes can be delayed (commonly about 15 minutes); they are not real-time. "
    "Non-NSE source — documented per assignment."
)

# Keep only the last 100 rows per symbol to avoid unbounded growth
MAX_ROWS_PER_SYMBOL = 100


async def _fetch_yfinance(yf_ticker: str) -> dict | None:
    """
    Fetch latest quote from yfinance using asyncio to run in executor
    (yfinance is a synchronous library).
    Returns value, change, and the daily bar's observation date when available.
    """
    def _sync_fetch() -> dict | None:
        try:
            import yfinance as yf
            frame = yf.download(
                yf_ticker, period="5d", interval="1d", progress=False,
                threads=False, timeout=8, multi_level_index=False,
            )
            if frame is None or frame.empty or "Close" not in frame:
                return None
            closes = frame["Close"].dropna()
            if len(closes) < 2:
                return None
            price = float(closes.iloc[-1])
            if not math.isfinite(price) or price <= 0:
                return None
            prev_close = float(closes.iloc[-2])
            if prev_close is not None and (not math.isfinite(prev_close) or prev_close <= 0):
                prev_close = None
            change_abs = round(price - prev_close, 2) if prev_close is not None else None
            change_pct = round(change_abs / prev_close * 100, 2) if prev_close is not None and change_abs is not None else None
            observation_date = None
            try:
                index_value = closes.index[-1]
                candidate_date = index_value.date().isoformat() if hasattr(index_value, "date") else str(index_value)[:10]
                observation_date = date.fromisoformat(candidate_date).isoformat()
            except (TypeError, ValueError, AttributeError):
                # Do not substitute the backend fetch time for missing provider metadata.
                pass
            return {
                "value": round(price, 2),
                "change_abs": change_abs,
                "change_pct": change_pct,
                "observation_date": observation_date,
            }
        except Exception as exc:
            print(f"[Ticker] yfinance error for {yf_ticker}: {exc}")
            return None

    loop = asyncio.get_running_loop()
    try:
        return await asyncio.wait_for(loop.run_in_executor(None, _sync_fetch), timeout=12)
    except asyncio.TimeoutError:
        print(f"[Ticker] yfinance request timed out for {yf_ticker}")
        return None


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
                    (symbol, value, change_abs, change_pct, source, fetched_at, observation_date, is_stale)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    symbol,
                    data["value"],
                    data["change_abs"],
                    data["change_pct"],
                    source,
                    fetched_at,
                    data["observation_date"],
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
