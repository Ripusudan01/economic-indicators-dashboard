"""
config.py — Application settings loaded from environment variables.
All sensitive values (secrets, passwords) come from .env — never from browser code.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from functools import lru_cache


class Settings(BaseSettings):
    # ── JWT ──────────────────────────────────────────────────────────
    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ── Database ─────────────────────────────────────────────────────
    # SQLite: path relative to the backend/ directory
    database_url: str = "sqlite:///./db/indicators.db"
    # If using PostgreSQL: postgresql://user:pass@localhost:5432/indicators
    # DB must bind only to localhost / private network — never expose publicly.

    # ── CORS ─────────────────────────────────────────────────────────
    # In production, set to the exact deployed frontend origin.
    # Example: https://your-app.vercel.app
    cors_origins: str = "http://localhost:5173"
    app_env: str = "development"
    evaluator_username: str = "evaluator"
    evaluator_password: str | None = None

    # ── NSE / Market data ────────────────────────────────────────────
    # NSE session refresh (seconds)
    ticker_refresh_seconds: int = 30

    # ── Scheduler ────────────────────────────────────────────────────
    # Set to false in tests to disable background jobs
    scheduler_enabled: bool = True

    # ── App metadata ─────────────────────────────────────────────────
    app_version: str = "1.0.0"
    app_title: str = "Economic Indicators API"

    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.app_env.lower() == "production":
            origins = self.cors_origins_list()
            if self.jwt_secret_key == "CHANGE_ME_IN_PRODUCTION" or len(self.jwt_secret_key.encode("utf-8")) < 32:
                raise ValueError("JWT_SECRET_KEY must be configured with at least 32 bytes in production")
            if not origins or any(
                not origin.startswith("https://")
                or "localhost" in origin
                or "127.0.0.1" in origin
                for origin in origins
            ):
                raise ValueError("CORS_ORIGINS must contain only deployed frontend origins in production")
        if self.jwt_algorithm != "HS256":
            raise ValueError("JWT_ALGORITHM must be HS256")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — call this everywhere instead of Settings()."""
    return Settings()
