"""Keep test imports isolated from developer .env files and the local database."""
import os
import tempfile
from pathlib import Path

_test_root = Path(tempfile.mkdtemp(prefix="economic-dashboard-tests-"))
os.environ.update({
    "APP_ENV": "testing",
    "DATABASE_URL": f"sqlite:///{(_test_root / 'tests.sqlite').as_posix()}",
    "JWT_SECRET_KEY": "test-only-signing-key-with-more-than-32-bytes",
    "JWT_ALGORITHM": "HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
    "REFRESH_TOKEN_EXPIRE_DAYS": "7",
    "CORS_ORIGINS": "http://testserver",
    "EVALUATOR_USERNAME": "test_evaluator",
    "EVALUATOR_PASSWORD": "test-only-strong-password-123",
    "SCHEDULER_ENABLED": "false",
    "TICKER_REFRESH_SECONDS": "30",
    "APP_TITLE": "Economic Indicators API Tests",
    "APP_VERSION": "test",
})


def pytest_sessionfinish(session, exitstatus):
    """Close test DB handles and remove only this suite's temporary directory."""
    try:
        from app import database
        database.close_connection()
    except (ImportError, RuntimeError):
        pass
    import shutil
    shutil.rmtree(_test_root, ignore_errors=True)
