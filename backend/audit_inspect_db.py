import sqlite3
import json

conn = sqlite3.connect("db/indicators.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=== TABLES ===")
for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    print(" -", row[0])

print("\n=== COLLECTOR RUNS ===")
for row in cursor.execute("SELECT collector_name, started_at, finished_at, status, rows_upserted, error_message FROM collector_runs ORDER BY id DESC LIMIT 15"):
    print(dict(row))

print("\n=== INDICATOR SNAPSHOTS SUMMARY ===")
for row in cursor.execute("""
    SELECT indicator_name, COUNT(*) as count, 
           MIN(observation_date) as min_obs, MAX(observation_date) as max_obs, 
           MAX(fetched_at) as latest_fetch, SUM(is_stale) as stale_count,
           source
    FROM indicator_snapshots 
    GROUP BY indicator_name
"""):
    print(dict(row))

print("\n=== SAMPLE DATA PER INDICATOR (LATEST 2 ROWS) ===")
for ind in ["gdp_growth", "debt_gdp", "trade", "gst", "inflation", "govt_expenditure"]:
    print(f"\n--- Indicator: {ind} ---")
    for row in cursor.execute("SELECT series_key, period_label, value, source, observation_date, is_stale FROM indicator_snapshots WHERE indicator_name = ? ORDER BY period_label DESC LIMIT 3", (ind,)):
        print("  ", dict(row))

print("\n=== TICKER SNAPSHOTS ===")
for row in cursor.execute("SELECT symbol, value, change_abs, change_pct, source, fetched_at FROM ticker_snapshots ORDER BY id DESC LIMIT 6"):
    print(dict(row))

print("\n=== USERS (PW HASH TRUNCATED) ===")
for row in cursor.execute("SELECT id, username, role, substr(password_hash, 1, 10) as pw_prefix, created_at FROM users"):
    print(dict(row))

print("\n=== REFRESH TOKENS ===")
for row in cursor.execute("SELECT id, user_id, substr(token_hash, 1, 10) as hash_prefix, expires_at, revoked, created_at FROM refresh_tokens"):
    print(dict(row))
