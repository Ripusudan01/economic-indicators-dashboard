"""
auth/jwt.py — JWT token creation, verification, and refresh token utilities.

Design:
- Access tokens: short-lived (30 min), signed HS256 JWT.
- Refresh tokens: long-lived (7 days), stored as SHA-256 hash in DB.
- Never return raw secrets to the browser.
- Token expiry is enforced server-side; client must refresh before expiry.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app import database as db

bearer_scheme = HTTPBearer()


# ── Token creation ────────────────────────────────────────────────────────────

def create_access_token(user_id: int, username: str, role: str) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token() -> tuple[str, str]:
    """
    Create a cryptographically random refresh token.
    Returns (raw_token, token_hash).
    Store only the hash in the DB; send the raw token to the client.
    """
    raw = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, token_hash


# ── Token verification ────────────────────────────────────────────────────────

def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.
    Raises HTTPException(401) on any validation failure.
    """
    settings = get_settings()
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require_sub": True, "require_exp": True, "require_iat": True},
        )
        if payload.get("type") != "access" or not str(payload.get("sub", "")).isdigit():
            raise credentials_error
        return payload
    except JWTError:
        raise credentials_error


# ── FastAPI dependencies ──────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict[str, Any]:
    """
    FastAPI dependency: extract and validate the Bearer JWT from the request.
    Inject this into any route that requires evaluation authentication.

    Usage:
        @router.get("/protected")
        def protected(user=Depends(get_current_user)):
            ...
    """
    return decode_access_token(credentials.credentials)


# ── Refresh token DB helpers ──────────────────────────────────────────────────

def store_refresh_token(user_id: int, token_hash: str, expire_days: int) -> None:
    """Persist a new refresh token hash in the database."""
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=expire_days)
    ).isoformat()
    db.execute(
        """
        INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
        VALUES (?, ?, ?)
        """,
        (user_id, token_hash, expires_at),
    )
    db.commit()


def revoke_refresh_token(token_hash: str) -> None:
    """Mark a refresh token as revoked (logout)."""
    db.execute(
        "UPDATE refresh_tokens SET revoked = 1 WHERE token_hash = ?",
        (token_hash,),
    )
    db.commit()


def validate_refresh_token(raw_token: str) -> dict | None:
    """
    Validate a raw refresh token against the DB.
    Returns the user row if valid, None otherwise.
    Revokes the token as part of rotation (one-time use).
    """
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    row = db.fetchone(
        """
        SELECT rt.id, rt.user_id, rt.expires_at, rt.revoked,
               u.username, u.role
        FROM refresh_tokens rt
        JOIN users u ON u.id = rt.user_id
        WHERE rt.token_hash = ?
        """,
        (token_hash,),
    )
    if row is None:
        return None
    if row["revoked"]:
        return None

    # Check expiry
    expires_at = datetime.fromisoformat(row["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        return None

    # Atomically consume the token so simultaneous refresh requests cannot both succeed.
    cursor = db.execute(
        "UPDATE refresh_tokens SET revoked=1 WHERE token_hash=? AND revoked=0",
        (token_hash,),
    )
    if cursor.rowcount != 1:
        return None
    db.commit()
    return dict(row)
