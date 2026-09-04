"""Integrations router — connect a Microsoft tenant, browse it, read from it.

Connecting is a real OAuth round trip against the customer's tenant; browsing
and importing are live Graph calls. When Microsoft credentials are not
configured the same endpoints fall back to the stored tree, so local
development and the demo tenant behave the same way the real thing does
without pretending a connection exists.

See INTEGRATIONS.md for the permissions each provider needs.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession, RedisClient
from app.core.documents import store_document
from app.core.logging import get_logger
from app.core.queue import enqueue
from app.db.models.analysis import Analysis
from app.db.models.integration import Integration
from app.integrations import graph
from app.schemas.resources import ConnectRequest, ImportRequest, IntegrationResponse

router = APIRouter(prefix="/integrations", tags=["integrations"])
logger = get_logger()

# The consent hand-off is a browser redirect, so the link between "who started
# this" and "who came back" has to survive outside the session. Ten minutes is
# longer than a consent screen takes and shorter than a stolen link is useful.
STATE_TTL_SECONDS = 600


def _to_response(i: Integration) -> dict:
    return {
        "id": i.provider,
        "name": i.name,
        "blurb": i.blurb or "",
        "connected": i.connected,
        "account": i.account,
        "connectedAt": i.connected_at,
        "scopes": i.scopes or [],
        "tree": i.tree or [],
    }


async def _load(provider: str, org_id: str, db: DbSession) -> Integration:
    result = await db.execute(
        select(Integration).where(Integration.provider == provider, Integration.org_id == org_id)
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Integration '{provider}' not found"
        )
    return integration


def _redirect_uri(request: Request, provider: str) -> str:
    """The registered reply URL. Must match the app registration exactly."""
    configured = get_settings().MS_REDIRECT_URI
    base = configured.rsplit("/api/", 1)[0] if "/api/" in configured else str(request.base_url).rstrip("/")
    return f"{base}/api/v1/integrations/{provider}/callback"


@router.get("", response_model=list[IntegrationResponse])
async def list_integrations(user: CurrentUser, db: DbSession):
    result = await db.execute(select(Integration).where(Integration.org_id == user.org_id))
    return [_to_response(i) for i in result.scalars().all()]


@router.post("/{provider}/authorize")
async def start_authorization(
    provider: str, request: Request, user: CurrentUser, db: DbSession, redis: RedisClient
):
    """Where to send the person for consent, and the state that proves it was us."""
    await _load(provider, user.org_id, db)
    if provider not in graph.PROVIDER_SCOPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown provider")
    if not graph.is_configured():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "Microsoft sign-in is not configured. Set MS_CLIENT_ID, MS_CLIENT_SECRET "
                "and MS_TENANT_ID — see INTEGRATIONS.md."
            ),
        )

    state = secrets.token_urlsafe(24)
    await redis.set(f"oauth_state:{state}", f"{user.org_id}:{provider}", ex=STATE_TTL_SECONDS)
    return {
        "url": graph.authorize_url(provider, state, _redirect_uri(request, provider)),
        "scopes": graph.PROVIDER_SCOPES[provider],
    }


@router.get("/{provider}/callback")
async def finish_authorization(
    provider: str,
    request: Request,
    db: DbSession,
    redis: RedisClient,
    code: str | None = None,
    state: str | None = None,
    error_description: str | None = None,
):
    """Microsoft sends the person back here. This route is deliberately not
    authenticated — the `state` is what proves the round trip is genuine."""
    settings = get_settings()
    app_url = settings.ALLOWED_ORIGINS[0] if settings.ALLOWED_ORIGINS else ""

    if error_description:
        return RedirectResponse(f"{app_url}/app/integrations?error={error_description[:200]}")
    if not code or not state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing code or state")

    owner = await redis.get(f"oauth_state:{state}")
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That sign-in link has expired. Start the connection again.",
        )
    await redis.delete(f"oauth_state:{state}")
    org_id, _, state_provider = str(owner).partition(":")
    if state_provider != provider:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provider mismatch")

    integration = await _load(provider, org_id, db)
    try:
        payload = await graph.exchange_code(provider, code, _redirect_uri(request, provider))
    except graph.GraphError as exc:
        return RedirectResponse(f"{app_url}/app/integrations?error={str(exc)[:200]}")

    refresh_token = payload.get("refresh_token")
    if not refresh_token:
        return RedirectResponse(
            f"{app_url}/app/integrations?error=Microsoft did not return a refresh token. "
            "Check that offline_access is granted."
        )

    integration.connected = True
    integration.connected_at = datetime.now(UTC).isoformat()
    integration.token_ref = graph.seal(refresh_token)
    integration.scopes = graph.PROVIDER_SCOPES[provider]
    try:
        access = payload.get("access_token", "")
        me = await graph._get(access, "/me") if access else {}
        integration.account = str(me.get("userPrincipalName") or me.get("mail") or "")[:320] or None
    except graph.GraphError:
        # The connection is real even if we could not read the profile.
        pass
    await db.flush()
    logger.info("integration_connected", provider=provider, org_id=org_id)
    return RedirectResponse(f"{app_url}/app/integrations?connected={provider}")


@router.post("/{provider}/connect")
async def connect_integration(provider: str, body: ConnectRequest, user: CurrentUser, db: DbSession):
    """Record a connection made outside the OAuth flow.

    This is how a tenant that provisions tokens by another route (an admin
    consent grant applied out of band, or a development stub) marks a provider
    live. It cannot invent credentials: without a token the browse and import
    endpoints will say the connection needs authorising.
    """
    integration = await _load(provider, user.org_id, db)
    integration.connected = True
    integration.connected_at = datetime.now(UTC).isoformat()
    if body.account:
        integration.account = body.account
    await db.flush()
    return _to_response(integration)


@router.delete("/{provider}/disconnect")
async def disconnect_integration(provider: str, user: CurrentUser, db: DbSession):
    integration = await _load(provider, user.org_id, db)
    integration.connected = False
    integration.connected_at = None
    # The stored refresh token goes with the connection. Keeping it would mean
    # "disconnect" left standing access behind.
    integration.token_ref = None
    graph.forget(integration.id)
    await db.flush()
    logger.info("integration_disconnected", provider=provider, org_id=user.org_id)
    return _to_response(integration)


@router.get("/{provider}/browse")
async def browse_source(
    provider: str, user: CurrentUser, db: DbSession, path: str = ""
):
    """One level of a connected source, live.

    ``path`` is an opaque token this endpoint issued. The client walks the tree
    by handing back whatever it was given, which keeps mail, personal drives
    and SharePoint libraries behind one contract.
    """
    integration = await _load(provider, user.org_id, db)
    if not integration.connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"'{provider}' is not connected"
        )
    if not integration.token_ref or not graph.is_configured():
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail=(
                "This connection has no Microsoft credentials behind it. "
                "Reconnect it — see INTEGRATIONS.md."
            ),
        )

    try:
        access = await graph.access_token(integration.id, provider, integration.token_ref)
        entries = await graph.browse(access, provider, path)
    except graph.ConsentRequired as exc:
        # Not a failure to retry: an administrator has to act.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"reason": "admin_consent_required", "scope": exc.scope, "message": str(exc)},
        ) from exc
    except graph.GraphError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return {"provider": provider, "path": path, "entries": [e.as_dict() for e in entries]}


@router.post("/{provider}/import")
async def import_files(
    provider: str,
    body: ImportRequest,
    user: CurrentUser,
    db: DbSession,
):
    """Pull the chosen files out of the tenant and start reading them.

    This is the whole point of connecting an integration: a solicitation that
    landed in a mailbox or a SharePoint library becomes an analysis without
    anyone downloading it to a laptop first.
    """
    integration = await _load(provider, user.org_id, db)
    if not integration.connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Integration '{provider}' not connected"
        )
    if not body.file_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files were chosen.")
    if not integration.token_ref or not graph.is_configured():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "This connection has no Microsoft credentials behind it, so there is "
                "nothing to import from. Reconnect it — see INTEGRATIONS.md."
            ),
        )

    settings = get_settings()
    try:
        access = await graph.access_token(integration.id, provider, integration.token_ref)
    except graph.ConsentRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"reason": "admin_consent_required", "scope": exc.scope, "message": str(exc)},
        ) from exc
    except graph.GraphError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    started: list[dict] = []
    for file_id in body.file_ids[:10]:
        try:
            content, filename = await graph.download(access, provider, file_id)
        except graph.GraphError as exc:
            logger.warning("import_download_failed", provider=provider, error=str(exc))
            started.append({"fileId": file_id, "error": str(exc)})
            continue
        if len(content) > settings.MAX_UPLOAD_BYTES:
            started.append({"fileId": file_id, "error": "That file is over the size limit."})
            continue

        analysis = await _target_analysis(db, user, body.analysis_id, filename, provider)
        await store_document(
            db, analysis, content=content, filename=filename, kind="base", source=provider
        )
        job = await enqueue("app.workers.run_analysis.run_analysis_task", analysis.id)
        if job is None:
            analysis.stage = "triage"
        started.append({"fileId": file_id, "analysisId": analysis.id, "queued": job is not None})

    await db.flush()
    imported = sum(1 for item in started if "analysisId" in item)
    logger.info("integration_import", provider=provider, requested=len(body.file_ids), imported=imported)
    return {"imported": imported, "results": started}


async def _target_analysis(
    db: DbSession, user: CurrentUser, analysis_id: str | None, filename: str, provider: str
) -> Analysis:
    if analysis_id:
        result = await db.execute(
            select(Analysis).where(
                Analysis.id == analysis_id,
                Analysis.org_id == user.org_id,
                Analysis.deleted_at.is_(None),
            )
        )
        existing = result.scalar_one_or_none()
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
        return existing

    import uuid

    analysis = Analysis(
        id=f"an_{uuid.uuid4().hex[:12]}",
        org_id=user.org_id,
        title=filename.rsplit(".", 1)[0][:500],
        agency="Not yet determined",
        mode="standard",
        stage="triage",
        owner=user.id,
        source=provider,
        file_name=filename,
    )
    db.add(analysis)
    await db.flush()
    return analysis
