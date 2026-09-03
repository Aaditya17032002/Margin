"""JWT token management, argon2 password hashing, and RBAC dependency."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Annotated

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

# ── Password hashing ────────────────────────────────────────────────────

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except VerificationError:
        return False


def needs_rehash(hashed: str) -> bool:
    return _ph.check_needs_rehash(hashed)


# ── JWT tokens ───────────────────────────────────────────────────────────


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


def create_token(
    *,
    user_id: str,
    org_id: str,
    role: str,
    token_type: TokenType,
    expires_delta: timedelta | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    if expires_delta is None:
        expires_delta = (
            timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            if token_type == TokenType.ACCESS
            else timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
    payload = {
        "sub": user_id,
        "org": org_id,
        "role": role,
        "type": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


# ── Auth dependency ──────────────────────────────────────────────────────

_bearer = HTTPBearer(auto_error=True)


class AuthUser:
    """Represents the authenticated user extracted from the JWT."""

    __slots__ = ("id", "org_id", "role")

    def __init__(self, *, id: str, org_id: str, role: str) -> None:
        self.id = id
        self.org_id = org_id
        self.role = role


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> AuthUser:
    payload = decode_token(credentials.credentials)
    if payload.get("type") != TokenType.ACCESS.value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not an access token")
    return AuthUser(
        id=payload["sub"],
        org_id=payload["org"],
        role=payload["role"],
    )


# ── RBAC ─────────────────────────────────────────────────────────────────

ROLE_HIERARCHY: dict[str, int] = {
    "viewer": 0,
    "writer": 1,
    "reviewer": 2,
    "admin": 3,
}


class RequireRole:
    """FastAPI dependency that enforces minimum role level."""

    def __init__(self, minimum: str) -> None:
        self._min_level = ROLE_HIERARCHY.get(minimum, 0)

    def __call__(self, user: Annotated[AuthUser, Depends(get_current_user)]) -> AuthUser:
        user_level = ROLE_HIERARCHY.get(user.role, 0)
        if user_level < self._min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role '{list(ROLE_HIERARCHY.keys())[self._min_level]}' or higher",
            )
        return user
