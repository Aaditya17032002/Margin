"""Auth router — signup, login, refresh, logout, me, Microsoft OAuth."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, DbSession
from app.core.provisioning import ensure_org_provisioned
from app.core.rate_limit import limiter
from app.core.security import (
    AuthUser,
    RequireRole,
    TokenType,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models.org import Org
from app.db.models.preference import Preference, DEFAULT_PREFS
from app.db.models.team_member import TeamMember
from app.db.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    MicrosoftAuthRequest,
    OrgResponse,
    OrgUpdate,
    RefreshRequest,
    SessionUserResponse,
    SessionUserUpdate,
    SignupRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, db: DbSession):
    # Check if email exists
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    # Create org
    domain = body.email.split("@")[1] if "@" in body.email else "unknown.com"
    org = Org(
        id=str(uuid.uuid4()),
        name=body.org,
        domain=domain,
    )
    db.add(org)

    # Create user
    user = User(
        id=str(uuid.uuid4()),
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        role="admin",
        org_id=org.id,
        title="",
        signature=f"{body.name} · {body.org}",
    )
    db.add(user)
    # The org and the user have to exist before anything can reference them:
    # SQLAlchemy has no relationship here to infer the insert order from.
    await db.flush()

    db.add(Preference(user_id=user.id, org_id=org.id, data=dict(DEFAULT_PREFS)))
    await ensure_org_provisioned(db, user)
    await db.flush()

    return TokenResponse(
        access_token=create_token(user_id=user.id, org_id=org.id, role=user.role, token_type=TokenType.ACCESS),
        refresh_token=create_token(user_id=user.id, org_id=org.id, role=user.role, token_type=TokenType.REFRESH),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DbSession):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="That email and password combination wasn't recognised.",
        )

    return TokenResponse(
        access_token=create_token(user_id=user.id, org_id=user.org_id, role=user.role, token_type=TokenType.ACCESS),
        refresh_token=create_token(user_id=user.id, org_id=user.org_id, role=user.role, token_type=TokenType.REFRESH),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: DbSession):
    payload = decode_token(body.refresh_token)
    if payload.get("type") != TokenType.REFRESH.value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not a refresh token")

    user_id = payload["sub"]
    org_id = payload["org"]
    role = payload["role"]

    return TokenResponse(
        access_token=create_token(user_id=user_id, org_id=org_id, role=role, token_type=TokenType.ACCESS),
        refresh_token=create_token(user_id=user_id, org_id=org_id, role=role, token_type=TokenType.REFRESH),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(user: CurrentUser):
    # In a production system, we'd add the refresh token JTI to a revocation list in Redis.
    # For now, stateless JWT logout is a client-side token discard.
    return None


@router.get("/me", response_model=MeResponse)
async def me(user: CurrentUser, db: DbSession):
    result = await db.execute(select(User).where(User.id == user.id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    org_result = await db.execute(select(Org).where(Org.id == user.org_id))
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Org not found")

    # Backfill for orgs created before provisioning existed; a no-op afterwards.
    await ensure_org_provisioned(db, db_user)
    await db.flush()

    return MeResponse(
        user=SessionUserResponse(
            id=db_user.id,
            name=db_user.name,
            email=db_user.email,
            title=db_user.title or "",
            avatarTone=db_user.avatar_tone or "patina",
            signature=db_user.signature or "",
            timezone=db_user.timezone or "America/Chicago",
        ),
        org=OrgResponse(
            id=org.id,
            name=org.name,
            domain=org.domain,
            plan=org.plan,
            seats=org.seats,
            seatsUsed=org.seats_used,
            duns=org.duns or "",
            cage=org.cage or "",
        ),
    )


@router.patch("/me", response_model=SessionUserResponse)
async def update_me(body: SessionUserUpdate, user: CurrentUser, db: DbSession):
    """Edit your own profile. The team roster carries the same name, so it moves
    with it — a roster that disagrees with the profile is worse than either."""
    result = await db.execute(select(User).where(User.id == user.id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    for key, value in body.model_dump(exclude_unset=True, by_alias=False).items():
        if hasattr(db_user, key):
            setattr(db_user, key, value)

    member_result = await db.execute(
        select(TeamMember).where(TeamMember.org_id == user.org_id, TeamMember.email == db_user.email)
    )
    member = member_result.scalar_one_or_none()
    if member:
        member.name = db_user.name
        member.title = db_user.title or ""

    await db.flush()
    return SessionUserResponse(
        id=db_user.id,
        name=db_user.name,
        email=db_user.email,
        title=db_user.title or "",
        avatarTone=db_user.avatar_tone or "patina",
        signature=db_user.signature or "",
        timezone=db_user.timezone or "America/Chicago",
    )


@router.patch("/org", response_model=OrgResponse)
async def update_org(body: OrgUpdate, user: CurrentUser, db: DbSession):
    result = await db.execute(select(Org).where(Org.id == user.org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Org not found")

    for key, value in body.model_dump(exclude_unset=True, by_alias=False).items():
        if hasattr(org, key):
            setattr(org, key, value)

    await db.flush()
    return OrgResponse(
        id=org.id,
        name=org.name,
        domain=org.domain,
        plan=org.plan,
        seats=org.seats,
        seatsUsed=org.seats_used,
        duns=org.duns or "",
        cage=org.cage or "",
    )


@router.post("/microsoft", response_model=TokenResponse)
async def microsoft_auth(body: MicrosoftAuthRequest, db: DbSession):
    """Microsoft OAuth — in mock/dev mode, creates a demo user.
    In production, this exchanges the auth code via MSAL.
    """
    from app.core.config import get_settings
    settings = get_settings()

    if settings.PROVIDER_MODE == "mock" or not settings.MS_CLIENT_ID:
        # Mock mode: create/find a demo user
        email = "demo@thornfield.co"
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            org = Org(id=str(uuid.uuid4()), name="Thornfield Group", domain="thornfield.co")
            db.add(org)
            user = User(
                id=str(uuid.uuid4()),
                name="Demo User",
                email=email,
                password_hash=hash_password("demo-password"),
                role="admin",
                org_id=org.id,
            )
            db.add(user)
            await db.flush()
            db.add(Preference(user_id=user.id, org_id=org.id, data=dict(DEFAULT_PREFS)))

        await ensure_org_provisioned(db, user)
        await db.flush()

        return TokenResponse(
            access_token=create_token(user_id=user.id, org_id=user.org_id, role=user.role, token_type=TokenType.ACCESS),
            refresh_token=create_token(user_id=user.id, org_id=user.org_id, role=user.role, token_type=TokenType.REFRESH),
        )

    # Real MSAL flow would go here
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Configure MS_CLIENT_ID for real OAuth")
