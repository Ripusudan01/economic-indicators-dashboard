# Economic Indicators Dashboard

React/Vite frontend and FastAPI backend for the interview assignment. The browser reads authenticated API snapshots from SQLite; the backend collects upstream data on its own schedule.

## Local setup

Requirements: Python supported by the pinned backend dependencies, Node.js/npm, and the packages in the manifests below.

Backend, from `backend/` (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:JWT_SECRET_KEY = "a-random-local-signing-key-at-least-32-bytes"
$env:EVALUATOR_USERNAME = "evaluator"
$env:EVALUATOR_PASSWORD = "set-a-private-local-password"
$env:SCHEDULER_ENABLED = "false"
python -m uvicorn app.main:app --reload
```

Frontend, from `frontend/` in another terminal:

```powershell
npm install
$env:VITE_API_BASE_URL = "http://localhost:8000"
npm run dev
```

The backend initializes its SQLite schema at startup. By default its database is `backend/db/indicators.db`; `DATABASE_URL` can point to another private SQLite path. Do not use a real local database for tests. The API-only setup above disables collectors; set `SCHEDULER_ENABLED=true` to run scheduled collection and startup collection.

## Configuration

| Variable | Purpose |
| --- | --- |
| `APP_ENV` | Use `production` to enable production validation and disable `/docs`, `/redoc`, and OpenAPI. |
| `JWT_SECRET_KEY` | Private HS256 signing key; production requires a non-placeholder key of at least 32 bytes. |
| `JWT_ALGORITHM` | Must be `HS256`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access-token lifetime; defaults to 30 minutes. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh-token lifetime; defaults to 7 days. |
| `DATABASE_URL` | SQLite URL; default is `sqlite:///./db/indicators.db` relative to `backend/`. |
| `CORS_ORIGINS` | Comma-separated exact frontend origins; production origins must use HTTPS. |
| `EVALUATOR_USERNAME` | Evaluator account name; default is `evaluator`. |
| `EVALUATOR_PASSWORD` | Local default is not suitable for deployment. Production requires a private password 16–72 UTF-8 bytes with at least three character classes. Never commit the actual value. |
| `SCHEDULER_ENABLED` | Enables scheduled and startup data collection; defaults to true. |
| `TICKER_REFRESH_SECONDS` | Backend quote collector interval; defaults to 30 seconds. |
| `APP_TITLE` / `APP_VERSION` | Optional API metadata. |
| `VITE_API_BASE_URL` | Frontend API base URL compiled into the bundle. Use the HTTPS API origin in production; do not put secrets here. |

The backend seeds the evaluator account on startup. Access tokens expire after 30 minutes and refresh tokens after 7 days; refresh tokens rotate on use. The browser stores tokens in local storage, so protect the UI from XSS and use HTTPS. Login limits five failed attempts per client IP per rolling 60 seconds in each backend process. The in-memory limit resets at restart and is not shared across workers; multi-process hosting needs a shared proxy/API-gateway limit.

## Collectors and freshness

The six indicator jobs use UTC cron schedules; India Standard Time (IST) is UTC+05:30:

| Indicator | UTC | IST |
| --- | --- | --- |
| GDP growth | 02:00 daily | 07:30 daily |
| Debt-to-GDP | 02:30 daily | 08:00 daily |
| Trade | 03:00 daily | 08:30 daily |
| GST | 03:30 daily | 09:00 daily |
| Inflation | 04:00 daily | 09:30 daily |
| Government expenditure | 04:30 daily | 10:00 daily |

These are backend collector schedules. The ticker collector is a separate backend job, every `TICKER_REFRESH_SECONDS` (30 seconds by default). The ticker component separately polls the API every 30 seconds. The dashboard **Reload data** control rereads API snapshots; it does not trigger upstream collection. The API starts a background initial collection when scheduling is enabled.

Annual indicator data is marked stale after 550 days; monthly data after 62 days. The static GST observations therefore remain stale when old even after the scheduled task runs. Yahoo daily quote bars are marked stale when the provider observation date is missing or more than three calendar days old; a recent Yahoo bar is labelled delayed, never real-time.

## Data sources and limitations

- GDP growth, trade, inflation and government finance indicators use World Bank public API series. They are annual/monthly values at source frequency and are not interpolated into higher-frequency observations.
- Debt-to-GDP uses IMF WEO `GGXWDG_NGDP`. The DataMapper values endpoint returns year/value pairs without reliable row-level actual/estimate metadata. Future calendar years are marked as projections because they cannot be observed actuals; the current and elapsed years remain unclassified and may include estimates or an in-progress projection. `as_of` is the latest completed calendar-year period, not the latest projection.
- Trade is from World Bank series; the trade-balance series is derived from imports/exports and shares a chart scale that includes negative values.
- GST is curated static data attributed to PIB/MoF, not fetched from a live source. Annual coverage ends in FY2024-25 and monthly coverage in February 2025. The annual chart's monthly line is annual total divided by 12, not actual monthly observations.
- Government expenditure uses World Bank general-government expense and net investment in nonfinancial assets (% GDP). Revenue and capital labels are proxies; their sum is not the Union Budget's direct revenue/capital expenditure split.
- Market ticker uses yfinance/Yahoo Finance as a fallback. Yahoo quotes can be delayed (commonly about 15 minutes), and the daily-bar response supplies an observation date rather than a verified intraday timestamp. It is not an official NSE/BSE feed. Direct official NSE access was not established; SENSEX is a BSE index, while NIFTY BANK and NIFTY IT are NSE indices delivered here through Yahoo Finance. The project does not claim official NSE-source compliance for these quotes.
- Collector failures retain the last valid observations and mark them stale. A successful fetch does not make old economic observations fresh.

## API routes and representative schemas

`GET /health` is public. Authentication routes are public except logout, which requires a Bearer access token. All indicator and ticker routes require `Authorization: Bearer <access_token>`.

| Route | Purpose |
| --- | --- |
| `POST /auth/login` | `{ "username": "…", "password": "…" }` → `{ "access_token": "<JWT>", "refresh_token": "<opaque token>", "token_type": "bearer", "expires_in": 1800 }` |
| `POST /auth/refresh` | `{ "refresh_token": "<opaque token>" }` → same token response; old refresh token is revoked. |
| `POST /auth/logout` | Authenticated JSON `{ "refresh_token": "<opaque token>" }` → `204` on success. |
| `GET /indicators/gdp-growth` | Indicator snapshot envelope. The same envelope is returned by `/indicators/debt-gdp`, `/indicators/trade`, `/indicators/gst`, `/indicators/inflation`, and `/indicators/govt-expenditure`. |
| `GET /ticker` | `{ "items": [{ "symbol": "NIFTY_BANK", "value": null, "change_abs": null, "change_pct": null, "source": "NSE / Yahoo Finance", "fetched_at": "<UTC fetch time>", "observation_date": "YYYY-MM-DD or null", "is_stale": true, "status": "delayed" }], "as_of": "<latest provider observation date or —>" }` |
| `GET /health` | `{ "status": "ok or degraded", "db": "ok or error", "version": "…", "timestamp": "…" }` |

Indicator response shape (values vary by indicator):

```json
{
  "indicator": "debt_gdp",
  "title": "Debt to GDP Ratio (IND)",
  "source": "IMF World Economic Outlook (WEO)",
  "source_url": "https://www.imf.org/external/datamapper/api/v1/GGXWDG_NGDP/IND/USA",
  "as_of": "<latest completed annual period label>",
  "fetched_at": "<UTC fetch timestamp>",
  "is_stale": false,
  "series": [{"series_key": "india", "label": "India", "data": [{"period": "<year>", "value": null, "classification": "projection or null"}]}],
  "summary": [],
  "note": "Annual IMF WEO data; elapsed periods may include unclassified estimates."
}
```

Optional `classification` can be `actual`, `estimate`, or `projection`, or `null` when not reliably known. API errors follow FastAPI's `{"detail": "…"}` shape: unauthenticated protected requests return `401`, invalid request bodies return `422`, invalid credentials return `401`, and exceeded login limits return `429` with a `Retry-After` header. Database health failures return HTTP `200` with `status: degraded` and `db: error`. Local `/docs` is available outside production; production disables interactive API docs.

## Tests and builds

The backend test `conftest.py` explicitly sets `APP_ENV=testing`, credentials, scheduler disabled, and a temporary SQLite database before test modules import the application. From `backend/`, run:

```powershell
python -m pytest -q -p no:cacheprovider
```

The temporary test database is removed after the test session; the local `backend/db/indicators.db` is not used. Frontend checks, from `frontend/`:

```powershell
npm run lint
npm run build
```

Dependencies are in `backend/requirements.txt`, `backend/requirements-dev.txt`, and `frontend/package.json`. There is no backend transitive lockfile.

## Deployment and submission

The repository has no deployment configuration, hosted frontend/API URLs, or configured submission links. Before deployment, configure separate HTTPS frontend/API origins, production environment variables, a private persistent database path, collector scheduling, logs/restarts, and health checks. SQLite must remain on private persistent storage accessible only to the backend. API documentation is disabled in production by default.

- Hosted demo URL: **not yet configured**
- Portfolio/project URL: **not yet configured**
- Submission or recording URL: **not yet configured**
