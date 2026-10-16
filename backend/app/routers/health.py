"""
routers/health.py — Health check endpoint

GET /health — No authentication required
Returns DB connectivity status, app version, and timestamp.
This endpoint is used by the assignment panel to verify the API is live.
"""
from datetime import datetime, timezone

from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.config import get_settings
from app import database as db

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check():
    """
    Health check endpoint.
    Returns:
      - status: 'ok' if everything is healthy, 'degraded' if DB has issues
      - db: 'ok' if a test query succeeds, 'error' otherwise
      - version: application version from config
      - timestamp: current UTC time
    """
    settings = get_settings()
    db_status = "ok"
    overall_status = "ok"

    try:
        # Simple query to verify DB connection is live
        db.fetchone("SELECT 1 AS alive")
    except Exception as exc:
        db_status = "error"
        overall_status = "degraded"
        print(f"[Health] DB check failed: {exc}")

    return HealthResponse(
        status=overall_status,
        db=db_status,
        version=settings.app_version,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
