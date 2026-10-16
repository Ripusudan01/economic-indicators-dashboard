-- schema.sql
-- Economic Indicators Dashboard — SQLite database schema
-- All queries against this schema must use parameterized placeholders (?).
-- This file is executed once at startup via init_db().

-- ── Users (for JWT authentication) ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    UNIQUE NOT NULL,
    password_hash TEXT    NOT NULL,          -- bcrypt hash; never store plaintext
    role          TEXT    NOT NULL DEFAULT 'viewer',  -- 'viewer' | 'admin'
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Seed a default viewer account (password set at startup from env var).
-- This seed row is inserted by the application startup, not here,
-- so the password hash can be generated fresh from the env var.

-- ── Indicator snapshots ──────────────────────────────────────────────────────
-- One row per (indicator, series, period). UNIQUE constraint prevents duplicates;
-- use INSERT OR REPLACE to update stale rows.
CREATE TABLE IF NOT EXISTS indicator_snapshots (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_name   TEXT    NOT NULL,   -- 'gdp_growth' | 'debt_gdp' | 'trade' | 'gst' | 'inflation' | 'govt_expenditure'
    series_key       TEXT    NOT NULL,   -- 'india' | 'world' | 'us' | 'exports' | 'imports' | etc.
    period_label     TEXT    NOT NULL,   -- '2021' | 'FY25' | '2024-08' | '2024-Q1'
    value            REAL,              -- NULL means data unavailable (show '—' in UI)
    unit             TEXT,              -- '%' | 'USD_B' | 'INR_L_CR' | 'INR_CR'
    source           TEXT    NOT NULL,  -- human-readable source name
    source_url       TEXT,              -- canonical URL for attribution
    observation_date TEXT    NOT NULL,  -- ISO date of the actual data point
    fetched_at       TEXT    NOT NULL DEFAULT (datetime('now')),
    is_stale         INTEGER NOT NULL DEFAULT 0,  -- 1 if last fetch failed
    UNIQUE(indicator_name, series_key, period_label)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_indicator
    ON indicator_snapshots(indicator_name, series_key);

-- ── Market ticker snapshots ──────────────────────────────────────────────────
-- Keeps only the last N rows per symbol (pruned by the collector).
CREATE TABLE IF NOT EXISTS ticker_snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol      TEXT    NOT NULL,   -- 'SENSEX' | 'NIFTY_BANK' | 'NIFTY_IT'
    value       REAL,
    change_abs  REAL,
    change_pct  REAL,
    source      TEXT    NOT NULL DEFAULT 'yfinance',
    fetched_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    observation_date TEXT,
    is_stale    INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_ticker_symbol_time
    ON ticker_snapshots(symbol, fetched_at DESC);

-- ── Collector run log ────────────────────────────────────────────────────────
-- Used for staleness detection, debugging, and README documentation.
CREATE TABLE IF NOT EXISTS collector_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    collector_name  TEXT    NOT NULL,
    started_at      TEXT    NOT NULL,
    finished_at     TEXT,
    status          TEXT    NOT NULL,   -- 'success' | 'partial' | 'failed'
    error_message   TEXT,
    rows_upserted   INTEGER NOT NULL DEFAULT 0
);

-- ── Refresh tokens ───────────────────────────────────────────────────────────
-- Token rotation: each refresh creates a new row; old tokens are revoked.
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT    NOT NULL UNIQUE,  -- SHA-256 of the raw token
    expires_at  TEXT    NOT NULL,
    revoked     INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash
    ON refresh_tokens(token_hash);
