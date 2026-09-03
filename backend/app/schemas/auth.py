"""Auth schemas — login, signup, token responses."""

from __future__ import annotations

from pydantic import EmailStr, Field

from app.schemas.common import CamelModel


class LoginRequest(CamelModel):
    email: str
    password: str = Field(min_length=6)


class SignupRequest(CamelModel):
    name: str = Field(min_length=1)
    email: str
    org: str = Field(min_length=1)
    password: str = Field(min_length=6)


class MicrosoftAuthRequest(CamelModel):
    code: str | None = None
    id_token: str | None = None


class TokenResponse(CamelModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(CamelModel):
    refresh_token: str


class SessionUserResponse(CamelModel):
    id: str
    name: str
    email: str
    title: str
    avatar_tone: str = Field(alias="avatarTone")
    signature: str
    timezone: str


class OrgResponse(CamelModel):
    id: str
    name: str
    domain: str
    plan: str
    seats: int
    seats_used: int = Field(alias="seatsUsed")
    duns: str
    cage: str


class MeResponse(CamelModel):
    user: SessionUserResponse
    org: OrgResponse
