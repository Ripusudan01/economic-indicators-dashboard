"""
collectors/scheduler.py — APScheduler job definitions and FastAPI lifespan integration.

All upstream data collection happens server-side on a schedule.
The browser never makes direct calls to NSE, World Bank, IMF, or any other upstream.

Schedule:
  - market_ticker: every 30 seconds
  - All indicator collectors: once daily (staggered to avoid simultaneous requests)

The scheduler is disabled in tests by setting SCHEDULER_ENABLED=false in .env.
"""
import asyncio
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.collectors import (
    gdp,
    debt,
    trade,
    gst,
    inflation,
    expenditure,
    market_ticker,
)

scheduler = AsyncIOScheduler(timezone="UTC")


def _setup_jobs() -> None:
    """Register all collection jobs with their schedules."""
    settings = get_settings()

    # ── Market ticker: every 30 seconds ──────────────────────────────
    scheduler.add_job(
        market_ticker.run,
        trigger=IntervalTrigger(seconds=settings.ticker_refresh_seconds),
        id="market_ticker",
        name="Market Ticker (SENSEX, NIFTY BANK, NIFTY IT)",
        replace_existing=True,
        misfire_grace_time=10,
    )

    # ── Daily indicator collectors (staggered by 30 minutes) ─────────
    # Stagger prevents thundering-herd against upstream APIs.
    daily_jobs = [
        ("gdp_growth",       gdp.run,         "02:00"),
        ("debt_gdp",         debt.run,         "02:30"),
        ("trade",            trade.run,        "03:00"),
        ("gst",              gst.run,          "03:30"),
        ("inflation",        inflation.run,    "04:00"),
        ("govt_expenditure", expenditure.run,  "04:30"),
    ]

    for job_id, func, utc_time in daily_jobs:
        hour, minute = utc_time.split(":")
        scheduler.add_job(
            func,
            trigger=CronTrigger(hour=int(hour), minute=int(minute), timezone="UTC"),
            id=job_id,
            name=f"Daily collector: {job_id}",
            replace_existing=True,
            misfire_grace_time=300,  # 5 min grace for temporary outages
        )


async def _run_initial_collection() -> None:
    """
    Run all collectors once at startup to populate the DB immediately.
    This ensures the dashboard has data on first request without waiting
    for the daily schedule.
    Runs concurrently but with a small delay between indicator collectors
    to be polite to upstream APIs.
    """
    print("[Scheduler] Running initial data collection...")

    # Ticker first (fast)
    await market_ticker.run()

    # Indicator collectors staggered by 2 seconds
    collectors = [gdp.run, debt.run, trade.run, gst.run, inflation.run, expenditure.run]
    for collector in collectors:
        try:
            await collector()
            await asyncio.sleep(2)  # 2-second courtesy delay between requests
        except Exception as exc:
            print(f"[Scheduler] Initial collection error: {exc}")

    print("[Scheduler] Initial data collection complete.")


@asynccontextmanager
async def lifespan(app):
    """
    FastAPI lifespan context manager.
    Starts the scheduler and runs initial collection on startup.
    Shuts down cleanly on exit.
    """
    from app.database import init_db, close_connection
    from app.utils.http_client import close_client

    # Initialize database schema
    init_db()

    settings = get_settings()
    if settings.scheduler_enabled:
        _setup_jobs()
        scheduler.start()
        print(f"[Scheduler] Started with {len(scheduler.get_jobs())} jobs.")

        # Run initial collection in background (don't block startup)
        asyncio.create_task(_run_initial_collection())

    yield  # Application runs here

    # Shutdown
    if settings.scheduler_enabled and scheduler.running:
        scheduler.shutdown(wait=False)
        print("[Scheduler] Shutdown complete.")

    await close_client()
    close_connection()
    print("[App] Shutdown complete.")
