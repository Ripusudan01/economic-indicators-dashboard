import httpx
import json
import os

BASE_URL = "http://127.0.0.1:8000"

client = httpx.Client(base_url=BASE_URL, timeout=10.0)

print("=== 1. HEALTH CHECK ===")
res_health = client.get("/health")
print("Status:", res_health.status_code)
print(res_health.json())

print("\n=== 2. UNAUTHENTICATED ENDPOINTS ACCESS CHECK ===")
for ep in ["/ticker", "/indicators/gdp-growth", "/indicators/debt-gdp", "/indicators/trade", "/indicators/gst", "/indicators/inflation", "/indicators/govt-expenditure"]:
    r = client.get(ep)
    print(f"Unauthenticated {ep} -> Status: {r.status_code}")

print("\n=== 3. LOGIN WITH EVALUATOR ===")
evaluator_username = os.environ.get("EVALUATOR_USERNAME")
evaluator_password = os.environ.get("EVALUATOR_PASSWORD")
if not evaluator_username or not evaluator_password:
    raise SystemExit("Set EVALUATOR_USERNAME and EVALUATOR_PASSWORD in the environment before running this audit helper.")
login_res = client.post("/auth/login", json={"username": evaluator_username, "password": evaluator_password})
print("Login status:", login_res.status_code)
tokens = login_res.json()
access_token = tokens["access_token"]
headers = {"Authorization": f"Bearer {access_token}"}

print("\n=== 4. AUTHENTICATED ENDPOINTS AUDIT ===")
for ep in ["/ticker", "/indicators/gdp-growth", "/indicators/debt-gdp", "/indicators/trade", "/indicators/gst", "/indicators/inflation", "/indicators/govt-expenditure"]:
    r = client.get(ep, headers=headers)
    data = r.json()
    print(f"\n--- {ep} (Status: {r.status_code}) ---")
    if ep == "/ticker":
        print(f"Items count: {len(data['items'])}, as_of: {data['as_of']}")
        for item in data["items"]:
            print(f"  {item['symbol']}: {item['value']} (change: {item['change_pct']}%, is_stale: {item['is_stale']}, src: {item['source']})")
    else:
        print(f"Title: {data.get('title')}")
        print(f"Source: {data.get('source')} | Source URL: {data.get('source_url')}")
        print(f"As of: {data.get('as_of')} | Fetched at: {data.get('fetched_at')} | Is stale: {data.get('is_stale')}")
        print(f"Note: {data.get('note')}")
        print("Summary items:")
        for s in data.get("summary", []):
            print(f"  [{s.get('key')}]: val={s.get('value')} {s.get('unit')}, change={s.get('change')} {s.get('change_unit')}, is_increase={s.get('is_increase')}")
        print(f"Series count: {len(data.get('series', []))}")
        for ser in data.get("series", []):
            dp_count = len(ser.get("data", []))
            latest_dp = ser.get("data", [])[-1] if dp_count > 0 else None
            print(f"  Series '{ser.get('series_key')}' ({ser.get('label')}): {dp_count} points, latest: {latest_dp}")
