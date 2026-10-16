"""
routers/ticker.py — Live market ticker endpoint

GET /ticker — Returns latest quotes for SENSEX, NIFTY BANK, NIFTY IT.
Requires JWT authentication.
"""
from fastapi import APIRouter, Depends

from app.auth.jwt import get_current_user
from app.models.schemas import TickerResponse, TickerItem
from app import database as db
from app.utils.freshness import is_ticker_observation_stale

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
    latest_observation = None

    for symbol in ["SENSEX", "NIFTY_BANK", "NIFTY_IT"]:
        row = db.fetchone(
            """
            SELECT symbol, value, change_abs, change_pct, source, fetched_at, observation_date, is_stale
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
            observed = row["observation_date"]
            if observed:
                latest_observation = max(latest_observation, observed) if latest_observation else observed
            is_up = (chg_pct >= 0) if chg_pct is not None else None
            stale = bool(row["is_stale"]) or is_ticker_observation_stale(observed)

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
                    observation_date=observed,
                    is_stale=stale,
                    status="stale" if stale else "delayed",
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
                    fetched_at="—",
                    observation_date=None,
                    is_stale=True,
                    status="unavailable",
                )
            )

    return TickerResponse(items=items, as_of=latest_observation or "—")
