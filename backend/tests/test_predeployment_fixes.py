"""Regression coverage for data freshness, failure recovery, and ticker status."""
import asyncio
from datetime import datetime, timedelta, timezone

from app import database as db
from app.collectors import expenditure, gst, market_ticker
from app.routers.indicators import get_debt_gdp, get_gst
from app.routers.ticker import get_ticker
from app.utils.freshness import is_observation_stale, is_ticker_observation_stale


def test_observation_age_policy_is_frequency_aware():
    now = datetime(2026, 10, 16, tzinfo=timezone.utc)
    assert is_observation_stale("2025-03-31", now=now)
    assert not is_observation_stale("2026-01-01", now=now)
    assert is_observation_stale("2026-08-01", frequency="monthly", now=now)
    assert not is_observation_stale("2026-09-01", frequency="monthly", now=now)
    assert is_observation_stale("not-a-date", now=now)


def test_ticker_provider_observation_age_policy_is_conservative():
    now = datetime(2026, 10, 16, tzinfo=timezone.utc)
    assert not is_ticker_observation_stale("2026-10-16", now=now)
    assert is_ticker_observation_stale("2026-10-12", now=now)
    assert is_ticker_observation_stale(None, now=now)
    assert is_ticker_observation_stale("not-a-date", now=now)
    assert is_ticker_observation_stale("2026-10-17", now=now)


def test_gst_summary_reports_percent_and_static_observation_stays_stale():
    db.init_db()
    asyncio.run(gst.run())
    response = get_gst(_user=None)
    collection = next(item for item in response.summary if item.key == "gst_collections_latest")
    assert collection.change_unit == "%"
    assert collection.change == 9.42
    latest = db.fetchone(
        "SELECT is_stale, observation_date, fetched_at FROM indicator_snapshots "
        "WHERE indicator_name='gst' AND series_key='total' AND period_label='FY25'"
    )
    assert latest["is_stale"] == 1
    assert latest["observation_date"] == "2025-03-31"


def test_expenditure_old_observation_is_stale_and_failed_refresh_preserves_value(monkeypatch):
    db.init_db()
    db.execute(
        "INSERT INTO indicator_snapshots (indicator_name, series_key, period_label, value, unit, source, "
        "observation_date, fetched_at, is_stale) VALUES ('govt_expenditure','total','2022',12.5,'% of GDP',"
        "'World Bank','2022-03-31','2026-10-16T00:00:00+00:00',0) "
        "ON CONFLICT(indicator_name,series_key,period_label) DO UPDATE SET value=12.5,is_stale=0"
    )

    async def fetch_partial(code):
        return {"2022": 3.0} if code == expenditure.WB_NET_INVESTMENT_PCT_GDP else None

    monkeypatch.setattr(expenditure, "_fetch_wb", fetch_partial)
    asyncio.run(expenditure.run())
    row = db.fetchone(
        "SELECT value,is_stale FROM indicator_snapshots WHERE indicator_name='govt_expenditure' "
        "AND series_key='total' AND period_label='2022'"
    )
    assert row["value"] == 12.5
    assert row["is_stale"] == 1


def test_ticker_refresh_failure_preserves_last_quote_and_endpoint_reports_stale(monkeypatch):
    db.init_db()
    fetched = datetime.now(timezone.utc).isoformat()
    db.execute(
        "INSERT INTO ticker_snapshots (symbol,value,change_abs,change_pct,source,fetched_at,observation_date,is_stale) "
        "VALUES ('NIFTY_BANK',123.0,1.0,0.8,'NSE / Yahoo Finance',?,'2026-10-16',0)",
        (fetched,),
    )
    db.commit()

    async def fail_fetch(_symbol):
        return None

    monkeypatch.setattr(market_ticker, "_fetch_yfinance", fail_fetch)
    asyncio.run(market_ticker.run())
    quote = db.fetchone(
        "SELECT value,is_stale,observation_date FROM ticker_snapshots WHERE symbol='NIFTY_BANK' ORDER BY fetched_at DESC LIMIT 1"
    )
    assert quote["value"] == 123.0
    assert quote["is_stale"] == 1
    assert quote["observation_date"] == "2026-10-16"
    ticker = get_ticker(_user=None)
    item = next(item for item in ticker.items if item.symbol == "NIFTY_BANK")
    assert item.status == "stale"
    assert item.is_stale


def test_ticker_status_is_never_live_without_a_successful_snapshot():
    db.init_db()
    response = get_ticker(_user=None)
    assert all(item.status in {"unavailable", "stale", "delayed", "fresh"} for item in response.items)
    assert all(item.status != "live" for item in response.items)
    assert any(item.status == "unavailable" for item in response.items)


def test_successful_yahoo_snapshot_is_reported_as_delayed():
    db.init_db()
    db.execute(
        "INSERT INTO ticker_snapshots (symbol,value,change_abs,change_pct,source,fetched_at,observation_date,is_stale) "
        "VALUES ('NIFTY_IT',456.0,2.0,0.4,'NSE / Yahoo Finance',?,?,0)",
        (datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).date().isoformat()),
    )
    db.commit()
    response = get_ticker(_user=None)
    item = next(item for item in response.items if item.symbol == "NIFTY_IT")
    assert item.status == "delayed"
    assert not item.is_stale
    assert item.observation_date == datetime.now(timezone.utc).date().isoformat()


def test_missing_or_repeated_old_ticker_observation_never_looks_fresh():
    db.init_db()
    fetched = datetime.now(timezone.utc).isoformat()
    earlier_fetch = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
    old_date = (datetime.now(timezone.utc).date() - timedelta(days=4)).isoformat()
    db.execute(
        "INSERT INTO ticker_snapshots (symbol,value,change_abs,change_pct,source,fetched_at,observation_date,is_stale) "
        "VALUES ('SENSEX',100.0,1.0,1.0,'BSE / Yahoo Finance',?,?,0)",
        (earlier_fetch, old_date),
    )
    db.execute(
        "INSERT INTO ticker_snapshots (symbol,value,change_abs,change_pct,source,fetched_at,observation_date,is_stale) "
        "VALUES ('SENSEX',100.0,1.0,1.0,'BSE / Yahoo Finance',?,?,0)",
        (fetched, old_date),
    )
    db.execute(
        "INSERT INTO ticker_snapshots (symbol,value,change_abs,change_pct,source,fetched_at,observation_date,is_stale) "
        "VALUES ('NIFTY_BANK',200.0,1.0,0.5,'NSE / Yahoo Finance',?,NULL,0)",
        (fetched,),
    )
    db.commit()
    items = {item.symbol: item for item in get_ticker(_user=None).items}
    assert items["SENSEX"].status == "stale"
    assert items["SENSEX"].observation_date == old_date
    assert items["SENSEX"].fetched_at == fetched
    assert items["NIFTY_BANK"].status == "stale"
    assert items["NIFTY_BANK"].observation_date is None


def test_debt_future_year_is_projection_and_as_of_excludes_future_years():
    db.init_db()
    current_year = datetime.now(timezone.utc).year
    previous_year = current_year - 1
    future_year = current_year + 2
    for year, value in ((previous_year, 80.0), (current_year, 78.0), (future_year, 75.0)):
        db.execute(
            "INSERT INTO indicator_snapshots (indicator_name,series_key,period_label,value,unit,source,observation_date,fetched_at,is_stale) "
            "VALUES ('debt_gdp','india',? ,?,'%','IMF WEO',?,?,0)",
            (str(year), value, f"{year}-03-31", datetime.now(timezone.utc).isoformat()),
        )
    db.commit()
    response = get_debt_gdp(_user=None)
    india = next(series for series in response.series if series.series_key == "india")
    assert india.data[0].classification is None
    assert india.data[1].classification is None
    assert india.data[-1].classification == "projection"
    assert response.as_of == str(previous_year)
    summary = next(item for item in response.summary if item.key == "india_latest")
    assert summary.classification == "projection"


def test_login_ip_limit_returns_429_and_success_clears_failures():
    from app.auth.routes import _check_login_limit, _clear_login_failures, _record_login_failure, get_password_hash
    from fastapi.testclient import TestClient
    from app.main import app

    _clear_login_failures("testclient")
    for _ in range(5):
        _record_login_failure("testclient")
    client = TestClient(app)
    response = client.post("/auth/login", json={"username": "missing", "password": "wrong"})
    assert response.status_code == 429
    assert "Retry-After" in response.headers
    username = "rate_limit_test_user"
    password = "Temporary_TestPassword123"
    db.execute(
        "INSERT INTO users (username,password_hash,role) VALUES (?,?, 'evaluator') "
        "ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash",
        (username, get_password_hash(password)),
    )
    db.commit()
    _clear_login_failures("testclient")
    _record_login_failure("testclient")
    success = client.post("/auth/login", json={"username": username, "password": password})
    assert success.status_code == 200
    assert _check_login_limit("testclient") == 0
