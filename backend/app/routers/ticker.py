"""
routers/ticker.py — Live market ticker endpoint

GET /ticker — Returns latest quotes for SENSEX, NIFTY BANK, NIFTY IT.
Requires JWT authentication.
"""
from fastapi import APIRouter, Depends

from app.auth.jwt import get_current_user
from app.models.schemas import TickerResponse, TickerItem
from app import database as db

router = APIRouter(prefix="/ticker", tags=["ticker"])

DISPLAY_NAMES = {
    "SENSEX": "SENSEX",
    "NIFTY_BANK": "NIFTY BANK",
    "NIFTY_IT": "NIFTY IT",
}

DEFAULT_SOURCES = {
    "SENSEX": "BSE / Yahoo Finance",
    "NIFTY_BANK": "NSE / Yahoo Finance",
    "NIFTY_IT": "NSE / Yahoo Finance",
}


@router.get("", response_model=TickerResponse)
def get_ticker(_user=Depends(get_current_user)):
    """
    Returns the latest ticker snapshot for SENSEX, NIFTY BANK, and NIFTY IT.
    """
    items = []
    latest_ts = None

    for symbol in ["SENSEX", "NIFTY_BANK", "NIFTY_IT"]:
        row = db.fetchone(
            """
            SELECT symbol, value, change_abs, change_pct, source, fetched_at, is_stale
            FROM ticker_snapshots
            WHERE symbol = ?
            ORDER BY fetched_at DESC
            LIMIT 1
            """,
            (symbol,),
        )

        if row:
            row = dict(row)
            val = row["value"]
            chg_abs = row["change_abs"]
            chg_pct = row["change_pct"]
            src = row["source"] or DEFAULT_SOURCES.get(symbol, "Yahoo Finance")
            fetched_at = row["fetched_at"]
            latest_ts = max(latest_ts, fetched_at) if latest_ts else fetched_at
            is_up = (chg_pct >= 0) if chg_pct is not None else None

            items.append(
                TickerItem(
                    symbol=symbol,
                    display_name=DISPLAY_NAMES.get(symbol, symbol),
                    value=val,
                    change_abs=chg_abs,
                    change_pct=chg_pct,
                    is_up=is_up,
                    source=src,
                    fetched_at=fetched_at,
                    is_stale=bool(row["is_stale"]),
                )
            )
        else:
            items.append(
                TickerItem(
                    symbol=symbol,
                    display_name=DISPLAY_NAMES.get(symbol, symbol),
                    value=None,
                    change_abs=None,
                    change_pct=None,
                    is_up=None,
                    source=DEFAULT_SOURCES.get(symbol, "Yahoo Finance"),
                    fetched_at=latest_ts or "—",
                    is_stale=True,
                )
            )

    return TickerResponse(items=items, as_of=latest_ts or "—")
