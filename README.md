# Economic Indicators Dashboard

React/Vite frontend and FastAPI backend for the interview assignment. Dashboard API responses are served from SQLite snapshots collected by the backend scheduler.

## Local setup

Backend (run from `backend/`):

```powershell
python -m pip install -r requirements.txt
$env:JWT_SECRET_KEY = "a-random-local-signing-key-at-least-32-bytes"
$env:EVALUATOR_PASSWORD = "set-a-private-local-password"
$env:SCHEDULER_ENABLED = "false" # optional for API-only development
python -m uvicorn app.main:app --reload
```

Frontend (run from `frontend/`):

```powershell
npm install
$env:VITE_API_BASE_URL = "http://localhost:8000"
npm run dev
```

The database defaults to `backend/db/indicators.db`. Set `DATABASE_URL` to change it. Do not use a production database for tests.

## Configuration

| Variable | Purpose |
| --- | --- |
| `APP_ENV` | Set to `production` to enforce production checks and disable API docs. |
| `JWT_SECRET_KEY` | HS256 signing key; production requires at least 32 bytes and rejects the placeholder. |
| `JWT_ALGORITHM` | Must be `HS256`. |
| `DATABASE_URL` | SQLite URL, default `sqlite:///./db/indicators.db`. |
| `CORS_ORIGINS` | Comma-separated exact frontend origins. Set only the deployed HTTPS frontend origin in production. |
| `EVALUATOR_USERNAME` | Evaluator account name, default `evaluator`. |
| `EVALUATOR_PASSWORD` | Optional evaluator password. When configured, startup seeds or updates that account and revokes its refresh sessions after a password change. Share the credential separately from source. |
| `SCHEDULER_ENABLED` | Enables the collectors; defaults to true. |
| `TICKER_REFRESH_SECONDS` | Market quote refresh interval; defaults to 30 seconds. |
| `VITE_API_BASE_URL` | Public API base URL compiled into the frontend. Never put secrets here. |

## API routes

- `GET /health` — unauthenticated health check.
- `POST /auth/login` — JSON `{ "username", "password" }`; returns access and refresh tokens.
- `POST /auth/refresh` — JSON `{ "refresh_token" }`; rotates the one-use refresh token.
- `POST /auth/logout` — authenticated request with JSON `{ "refresh_token" }`; revokes refresh token.
- `GET /indicators/gdp-growth`, `/debt-gdp`, `/trade`, `/gst`, `/inflation`, `/govt-expenditure` — Bearer access token required.
- `GET /ticker` — Bearer access token required.

Access tokens expire after 30 minutes; refresh tokens after 7 days. The browser stores both tokens in local storage, so an XSS flaw could expose them. Avoid rendering untrusted HTML and use HTTPS in deployment.

## Data notes

Collectors fetch public data server-side. GDP, trade, inflation and expenditure use World Bank data; debt uses IMF WEO; ticker quotes use Yahoo Finance/yfinance as a documented fallback. Expenditure is a GFS proxy: expense and net investment in nonfinancial assets, not the Union Budget's direct capital/revenue split. IMF debt values may include estimates or projections. GST data is a static, curated series through FY2024-25 and monthly values through February 2025; it is not fetched live. The GST chart line is annual totals divided by 12, not actual month-by-month data. Each panel provides source, observation date, and limitations where applicable. Annual sources remain annual; they are not interpolated into higher frequency values. Upstream failures retain stored observations and should mark them stale.

Backend runtime dependencies are pinned in `backend/requirements.txt`; test tooling is in `backend/requirements-dev.txt`. There is no backend transitive lockfile.

## Deployment and submission checklist

- Deploy the frontend and API on separate hosting environments with HTTPS.
- Set `APP_ENV=production`, a unique random `JWT_SECRET_KEY`, the exact frontend HTTPS origin in `CORS_ORIGINS`, a private persistent database path, and a private evaluator password.
- Configure network controls so only the API host can reach the database. SQLite should remain on the API host's private persistent storage.
- Share the evaluator account details separately from this repository.
- Provide live frontend, API/docs (docs are disabled in production by default), and health URLs, plus portfolio/project links and the required screen recording.

The repository currently has no deployment configuration or hosted URLs. Confirm the Figma reference at the required 1214 × 2159 viewport before submission.
