"""
test_api.py — Test suite for Economic Indicators API

Tests cover:
- Health check endpoint (/health)
- Authentication flows (login, refresh, logout, invalid credentials)
- Protected indicator endpoints (with and without JWT)
- Live ticker endpoint
- Database parameterization and safety
"""
import pytest
import secrets
import sqlite3
from fastapi.testclient import TestClient
from app.main import app
from app import database as db

client = TestClient(app)
TEST_USERNAME = "test_evaluator"
TEST_PASSWORD = secrets.token_urlsafe(24)


def setup_module():
    """Ensure DB tables and test user exist."""
    db.init_db()
    from app.auth.routes import get_password_hash
    db.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'evaluator') "
        "ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash",
        (TEST_USERNAME, get_password_hash(TEST_PASSWORD)),
    )
    db.commit()


def test_health_check():
    """Verify /health returns 200 and db: ok."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "degraded"]
    assert data["db"] == "ok"
    assert "version" in data


def test_login_success():
    """Verify login with valid credentials returns access and refresh tokens."""
    response = client.post(
        "/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


def test_login_invalid_credentials():
    """Verify login with invalid credentials fails with 401."""
    response = client.post(
        "/auth/login",
        json={"username": "evaluator", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_passwords_longer_than_bcrypt_limit_are_not_truncated():
    from app.auth.routes import get_password_hash, verify_password

    accepted = "a" * 72
    rejected_suffix = "a" * 72 + "different"
    password_hash = get_password_hash(accepted)
    assert verify_password(accepted, password_hash)
    assert not verify_password(rejected_suffix, password_hash)
    with pytest.raises(ValueError):
        get_password_hash(rejected_suffix)


def test_malformed_and_tampered_bearer_tokens_are_rejected():
    from datetime import datetime, timedelta, timezone
    from jose import jwt
    from app.config import get_settings

    expired = jwt.encode(
        {"sub": "1", "type": "access", "iat": datetime.now(timezone.utc) - timedelta(minutes=2),
         "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        get_settings().jwt_secret_key,
        algorithm="HS256",
    )
    for token in ("not-a-jwt", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.invalid", expired):
        response = client.get(
            "/indicators/gdp-growth",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401


def test_production_settings_reject_weak_key_and_http_origins():
    from app.config import Settings

    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            app_env="production",
            jwt_secret_key="CHANGE_ME_IN_PRODUCTION",
            cors_origins="https://dashboard.example.com",
            evaluator_username="evaluator",
            evaluator_password="TestStrong_Password123",
        )
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            app_env="production",
            jwt_secret_key="x" * 32,
            cors_origins="https://dashboard.example.com",
            evaluator_username="evaluator",
            evaluator_password=None,
        )
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            app_env="production",
            jwt_secret_key="x" * 32,
            cors_origins="https://dashboard.example.com",
            evaluator_username="evaluator",
            evaluator_password="weak",
        )
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            app_env="production",
            jwt_secret_key="x" * 32,
            cors_origins="http://localhost:5173",
            evaluator_username="evaluator",
            evaluator_password="TestStrong_Password123",
        )
    Settings(
        _env_file=None,
        app_env="production",
        jwt_secret_key="x" * 32,
        cors_origins="https://dashboard.example.com",
        evaluator_username="evaluator",
        evaluator_password="LongStrong_TestPassword123",
    )


def test_ticker_stale_column_migration_preserves_existing_rows(tmp_path, monkeypatch):
    legacy_path = tmp_path / "legacy.sqlite"
    legacy = sqlite3.connect(legacy_path)
    legacy.execute(
        """CREATE TABLE ticker_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            value REAL,
            change_abs REAL,
            change_pct REAL,
            source TEXT NOT NULL DEFAULT 'yfinance',
            fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
        )"""
    )
    legacy.execute(
        "INSERT INTO ticker_snapshots (symbol, value, fetched_at) VALUES ('SENSEX', 123.45, '2025-01-01T00:00:00+00:00')"
    )
    legacy.commit()
    legacy.close()

    db.close_connection()
    previous_path = db._DB_PATH
    monkeypatch.setattr(db, "_DB_PATH", legacy_path)
    db.init_db()
    migrated = db.fetchone("SELECT symbol, value, fetched_at, is_stale FROM ticker_snapshots")
    assert migrated["symbol"] == "SENSEX"
    assert migrated["value"] == 123.45
    assert migrated["fetched_at"].startswith("2025-01-01")
    assert migrated["is_stale"] == 1

    db.close_connection()
    db._DB_PATH = previous_path


def test_upstream_numeric_and_year_validation():
    from app.collectors.validation import finite_number, valid_year

    assert finite_number("0") == 0.0
    assert finite_number(None) is None
    assert valid_year("2025") == "2025"
    with pytest.raises(ValueError):
        finite_number("NaN")
    with pytest.raises(ValueError):
        finite_number("not-a-number")
    with pytest.raises(ValueError):
        valid_year("FY25")


def test_token_refresh_and_rotation():
    """Verify refresh token rotation: old refresh token is invalidated after use."""
    # 1. Login
    login_res = client.post(
        "/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    tokens = login_res.json()
    refresh_token_1 = tokens["refresh_token"]

    # 2. Refresh
    refresh_res = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token_1},
    )
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    refresh_token_2 = new_tokens["refresh_token"]
    assert refresh_token_2 != refresh_token_1

    # 3. Old token should now be rejected (token rotation)
    replay_res = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token_1},
    )
    assert replay_res.status_code == 401


def test_logout_revokes_refresh_token():
    login_res = client.post(
        "/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    tokens = login_res.json()
    response = client.post(
        "/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 204
    replay = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401
    # Access tokens are stateless and remain valid until their expiry.
    protected = client.get(
        "/indicators/gdp-growth",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert protected.status_code == 200


def test_configured_evaluator_credentials_seed_and_rotate(monkeypatch):
    from app.main import _seed_initial_users, settings

    username = "configured_evaluator_test"
    first_password = secrets.token_urlsafe(24)
    monkeypatch.setattr(settings, "evaluator_username", username)
    monkeypatch.setattr(settings, "evaluator_password", first_password)
    _seed_initial_users()
    first_login = client.post("/auth/login", json={"username": username, "password": first_password})
    assert first_login.status_code == 200

    second_password = secrets.token_urlsafe(24)
    monkeypatch.setattr(settings, "evaluator_password", second_password)
    _seed_initial_users()
    assert client.post("/auth/login", json={"username": username, "password": first_password}).status_code == 401
    assert client.post("/auth/login", json={"username": username, "password": second_password}).status_code == 200


def test_changing_configured_evaluator_username_preserves_existing_user(monkeypatch):
    from app.main import _seed_initial_users, settings

    old_username = f"previous_evaluator_{secrets.token_hex(4)}"
    new_username = f"current_evaluator_{secrets.token_hex(4)}"
    old_password = secrets.token_urlsafe(24)
    new_password = secrets.token_urlsafe(24)

    monkeypatch.setattr(settings, "evaluator_username", old_username)
    monkeypatch.setattr(settings, "evaluator_password", old_password)
    _seed_initial_users()

    monkeypatch.setattr(settings, "evaluator_username", new_username)
    monkeypatch.setattr(settings, "evaluator_password", new_password)
    _seed_initial_users()

    assert client.post(
        "/auth/login", json={"username": new_username, "password": new_password}
    ).status_code == 200
    assert client.post(
        "/auth/login", json={"username": old_username, "password": old_password}
    ).status_code == 200


def test_protected_routes_require_auth():
    """Verify that indicator endpoints return 401/403 when no auth token is provided."""
    endpoints = [
        "/indicators/gdp-growth",
        "/indicators/debt-gdp",
        "/indicators/trade",
        "/indicators/gst",
        "/indicators/inflation",
        "/indicators/govt-expenditure",
        "/ticker",
    ]
    for ep in endpoints:
        res = client.get(ep)
        assert res.status_code in [401, 403], f"Endpoint {ep} should be protected"


def test_protected_routes_with_auth():
    """Verify that indicator endpoints succeed when a valid JWT is provided."""
    login_res = client.post(
        "/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    endpoints = [
        "/indicators/gdp-growth",
        "/indicators/debt-gdp",
        "/indicators/trade",
        "/indicators/gst",
        "/indicators/inflation",
        "/indicators/govt-expenditure",
        "/ticker",
    ]
    for ep in endpoints:
        res = client.get(ep, headers=headers)
        assert res.status_code == 200, f"Endpoint {ep} failed with {res.status_code}: {res.text}"
        data = res.json()
        if ep == "/ticker":
            assert "items" in data
            assert len(data["items"]) == 3
        else:
            assert "series" in data
            assert "summary" in data
            assert "source" in data
            assert "as_of" in data
