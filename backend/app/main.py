"""
main.py — FastAPI Application Entry Point for Economic Indicators Dashboard.

Features:
- Parameterized SQLite DB initialization on startup
- Evaluation user seeding (admin & evaluator accounts)
- APScheduler background collection integration
- Secure CORS middleware restricting browser origin
- Health-check endpoint (/health)
- JWT Authentication routes (/auth)
- 6 Indicator endpoints (/indicators/...)
- Live Market Ticker endpoint (/ticker)
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app import database as db
from app.auth.routes import router as auth_router, get_password_hash, verify_password
from app.routers.health import router as health_router
from app.routers.indicators import router as indicators_router
from app.routers.ticker import router as ticker_router
from app.collectors.scheduler import lifespan as scheduler_lifespan

logger = logging.getLogger("economic_indicators")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def _seed_initial_users():
    """Ensure the evaluator user account exists in the database."""
    username = settings.evaluator_username
    plain_pw = settings.evaluator_password
    if not plain_pw:
        logger.warning("Evaluator account was not seeded; configure EVALUATOR_PASSWORD to enable it.")
        return
    existing = db.fetchone(
        "SELECT id, password_hash FROM users WHERE username = ?",
        (username,),
    )
    if not existing:
        hashed = get_password_hash(plain_pw)
        db.execute(
            """
            INSERT INTO users (username, password_hash, role)
            VALUES (?, ?, 'evaluator')
            """,
            (username, hashed),
        )
        db.commit()
        logger.info("Evaluation account seeded from configured credentials.")
    elif not verify_password(plain_pw, existing["password_hash"]):
        new_hash = get_password_hash(plain_pw)
        db.execute("UPDATE users SET password_hash=? WHERE id=?", (new_hash, existing["id"]))
        db.execute("UPDATE refresh_tokens SET revoked=1 WHERE user_id=?", (existing["id"],))
        db.commit()
        logger.info("Configured evaluator credentials applied; existing refresh sessions revoked.")


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """Application lifecycle wrapper ensuring user seeding before scheduler starts."""
    # First seed users after database tables are verified
    db.init_db()
    _seed_initial_users()

    # Delegate to scheduler lifespan for background tasks and cleanup
    async with scheduler_lifespan(app):
        yield


settings = get_settings()

app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description="Economic Indicators Dashboard API with real data, caching, and JWT authentication.",
    lifespan=app_lifespan,
    docs_url=None if settings.app_env.lower() == "production" else "/docs",
    redoc_url=None if settings.app_env.lower() == "production" else "/redoc",
    openapi_url=None if settings.app_env.lower() == "production" else "/openapi.json",
)

# ── CORS Middleware ─────────────────────────────────────────────────────────────
allowed_origins = settings.cors_origins_list()
for dev_origin in ([] if settings.app_env.lower() == "production" else [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]):
    if dev_origin not in allowed_origins:
        allowed_origins.append(dev_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Route Mounts ────────────────────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(indicators_router)
app.include_router(ticker_router)


@app.get("/", tags=["root"])
def root():
    return JSONResponse(
        {
            "name": settings.app_title,
            "version": settings.app_version,
            "status": "online",
            "docs_url": "/docs",
            "health_check": "/health",
            "auth_endpoint": "/auth/login",
            "ticker_endpoint": "/ticker",
            "indicators_prefix": "/indicators",
        }
    )
