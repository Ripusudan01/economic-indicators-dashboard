"""
auth/routes.py — Authentication endpoints: login, token refresh, logout.

POST /auth/login   — username + password → access token + refresh token
POST /auth/refresh — refresh token → new access token + rotated refresh token
POST /auth/logout  — revoke refresh token
"""
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app import database as db
from app.auth.jwt import (
    create_access_token,
    create_refresh_token,
    store_refresh_token,
    revoke_refresh_token,
    validate_refresh_token,
    get_current_user,
)
from app.config import get_settings
import bcrypt

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def verify_password(plain: str, hashed: str) -> bool:
    if len(plain.encode("utf-8")) > 72:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def get_password_hash(plain: str) -> str:
    if len(plain.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 bytes")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def get_user_by_username(username: str) -> dict | None:
    row = db.fetchone(
        "SELECT id, username, password_hash, role FROM users WHERE username = ?",
        (username,),
    )
    return dict(row) if row else None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    """
    Authenticate with username and password.
    Returns a short-lived access token and a long-lived refresh token.
    The refresh token is for server-side rotation; revoke on logout.
    """
    user = get_user_by_username(body.username)
    if user is None or not verify_password(body.password, user["password_hash"]):
        # Return the same error for unknown user and wrong password
        # to avoid username enumeration.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    settings = get_settings()
    access_token = create_access_token(user["id"], user["username"], user["role"])
    raw_refresh, refresh_hash = create_refresh_token()
    store_refresh_token(user["id"], refresh_hash, settings.refresh_token_expire_days)

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest):
    """
    Rotate the refresh token and issue a new access token.
    The old refresh token is invalidated on use (one-time rotation).
    """
    settings = get_settings()
    user_data = validate_refresh_token(body.refresh_token)
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    access_token = create_access_token(
        user_data["user_id"], user_data["username"], user_data["role"]
    )
    raw_refresh, refresh_hash = create_refresh_token()
    store_refresh_token(user_data["user_id"], refresh_hash, settings.refresh_token_expire_days)

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: RefreshRequest, _user=Depends(get_current_user)):
    """
    Revoke the refresh token. Access tokens are stateless and expire naturally.
    Client must discard both tokens after calling this endpoint.
    """
    token_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()
    revoke_refresh_token(token_hash)
