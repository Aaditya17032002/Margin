"""Microsoft Graph: the way a document actually gets from Outlook, SharePoint,
or OneDrive into an analysis.

The shape of this module follows from one decision: Margin never keeps a copy
of anything it has not been handed on purpose. Browsing is live against Graph,
and bytes are only fetched at the moment someone picks a file to read. Nothing
is synced, mirrored, or crawled in the background.

Tokens are the sensitive part. Only the refresh token is stored, encrypted at
rest with a key derived from ``SECRET_KEY``; access tokens are held in memory
for the few minutes they are valid and never written down. See INTEGRATIONS.md
for which permissions each provider needs and why.
"""

from __future__ import annotations

import base64
import hashlib
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger()

GRAPH = "https://graph.microsoft.com/v1.0"

# The least each provider can be given and still do its job. Anything wider is
# access the customer's security team would have to justify.
PROVIDER_SCOPES: dict[str, list[str]] = {
    "outlook": ["offline_access", "User.Read", "Mail.Read"],
    "onedrive": ["offline_access", "User.Read", "Files.Read"],
    "sharepoint": ["offline_access", "User.Read", "Sites.Read.All", "Files.Read.All"],
}

# What Margin will read. Everything else Graph offers is refused at the door.
READABLE_SUFFIXES = (".pdf", ".docx", ".doc", ".txt", ".md", ".rtf", ".htm", ".html")


class GraphError(RuntimeError):
    """A Graph call failed in a way the caller should surface to a person."""


@dataclass(frozen=True)
class RemoteFile:
    id: str
    name: str
    size: int
    path: str
    kind: str  # "file" | "folder"
    modified: str = ""

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "size": self.size,
            "path": self.path,
            "kind": self.kind,
            "modified": self.modified,
        }


# ── Token storage ────────────────────────────────────────────────────────


def _cipher() -> Fernet:
    """A Fernet key derived from the app secret.

    Deriving rather than adding another required setting means an existing
    deployment does not have to rotate anything to gain encrypted tokens, and
    rotating ``SECRET_KEY`` correctly invalidates every stored refresh token.
    """
    digest = hashlib.sha256(get_settings().SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def seal(refresh_token: str) -> str:
    return _cipher().encrypt(refresh_token.encode()).decode()


def unseal(stored: str | None) -> str | None:
    if not stored:
        return None
    try:
        return _cipher().decrypt(stored.encode()).decode()
    except InvalidToken:
        # The secret was rotated, or the row predates encryption. Either way the
        # connection has to be re-authorised; pretending otherwise would loop.
        logger.warning("integration_token_unreadable")
        return None


# ── OAuth ────────────────────────────────────────────────────────────────


def is_configured() -> bool:
    settings = get_settings()
    return bool(settings.MS_CLIENT_ID and settings.MS_CLIENT_SECRET and settings.MS_TENANT_ID)


def _authority() -> str:
    return f"https://login.microsoftonline.com/{get_settings().MS_TENANT_ID}"


def authorize_url(provider: str, state: str, redirect_uri: str) -> str:
    """Where to send a person to grant consent."""
    scopes = PROVIDER_SCOPES.get(provider)
    if not scopes:
        raise GraphError(f"Unknown provider: {provider}")
    query = urlencode(
        {
            "client_id": get_settings().MS_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "response_mode": "query",
            "scope": " ".join(scopes),
            "state": state,
            # Always ask. A silent re-consent hides a scope change from the
            # person whose mailbox it is.
            "prompt": "select_account",
        }
    )
    return f"{_authority()}/oauth2/v2.0/authorize?{query}"


async def exchange_code(provider: str, code: str, redirect_uri: str) -> dict:
    return await _token_request(
        {
            "client_id": get_settings().MS_CLIENT_ID,
            "client_secret": get_settings().MS_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "scope": " ".join(PROVIDER_SCOPES[provider]),
        }
    )


async def refresh(provider: str, refresh_token: str) -> dict:
    return await _token_request(
        {
            "client_id": get_settings().MS_CLIENT_ID,
            "client_secret": get_settings().MS_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": " ".join(PROVIDER_SCOPES[provider]),
        }
    )


async def _token_request(form: dict) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{_authority()}/oauth2/v2.0/token", data=form)
    if response.status_code >= 400:
        detail = response.json().get("error_description", response.text)[:300]
        logger.error("graph_token_failed", status=response.status_code)
        raise GraphError(f"Microsoft rejected the sign-in: {detail}")
    return response.json()


# Access tokens live here for the few minutes they are valid, keyed by the
# integration row. Never persisted.
_ACCESS: dict[str, tuple[str, float]] = {}


async def access_token(integration_id: str, provider: str, sealed_refresh: str | None) -> str:
    cached = _ACCESS.get(integration_id)
    if cached and cached[1] > time.time() + 60:
        return cached[0]

    token = unseal(sealed_refresh)
    if not token:
        raise GraphError("This connection needs to be re-authorised.")
    payload = await refresh(provider, token)
    access = payload.get("access_token")
    if not access:
        raise GraphError("Microsoft returned no access token.")
    _ACCESS[integration_id] = (access, time.time() + float(payload.get("expires_in", 3600)))
    return access


def forget(integration_id: str) -> None:
    _ACCESS.pop(integration_id, None)


# ── Reading ──────────────────────────────────────────────────────────────


async def _get(access: str, path: str, **params: Any) -> dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            path if path.startswith("http") else f"{GRAPH}{path}",
            headers={"Authorization": f"Bearer {access}"},
            params=params or None,
        )
    if response.status_code >= 400:
        logger.error("graph_call_failed", path=path, status=response.status_code)
        raise GraphError(f"Microsoft Graph returned {response.status_code} for {path}.")
    return response.json()


async def list_files(access: str, provider: str, folder_id: str | None = None) -> list[RemoteFile]:
    """One level of the tree. Deliberately not recursive: a capture team picks a
    document, and crawling a tenant's whole drive is not that."""
    if provider == "outlook":
        return await _list_mail_attachments(access)

    if provider == "onedrive":
        path = "/me/drive/root/children" if not folder_id else f"/me/drive/items/{folder_id}/children"
    else:  # sharepoint
        path = (
            f"/drives/{folder_id}/root/children"
            if folder_id and folder_id.startswith("b!")
            else ("/me/followedSites" if not folder_id else f"/sites/{folder_id}/drive/root/children")
        )

    payload = await _get(access, path, **{"$top": 200})
    files: list[RemoteFile] = []
    for item in payload.get("value", []):
        is_folder = "folder" in item
        name = str(item.get("name") or item.get("displayName") or "")
        if not is_folder and not name.lower().endswith(READABLE_SUFFIXES):
            continue
        files.append(
            RemoteFile(
                id=str(item.get("id") or ""),
                name=name,
                size=int(item.get("size") or 0),
                path=str((item.get("parentReference") or {}).get("path") or ""),
                kind="folder" if is_folder else "file",
                modified=str(item.get("lastModifiedDateTime") or ""),
            )
        )
    return files


async def _list_mail_attachments(access: str) -> list[RemoteFile]:
    """Recent mail carrying a readable attachment. A solicitation usually
    arrives as one, and hunting for it in a browser is the thing this replaces."""
    payload = await _get(
        access,
        "/me/messages",
        **{
            "$filter": "hasAttachments eq true",
            "$select": "id,subject,receivedDateTime",
            "$orderby": "receivedDateTime desc",
            "$top": 25,
        },
    )
    files: list[RemoteFile] = []
    for message in payload.get("value", []):
        message_id = message.get("id")
        attachments = await _get(
            access, f"/me/messages/{message_id}/attachments", **{"$select": "id,name,size"}
        )
        for attachment in attachments.get("value", []):
            name = str(attachment.get("name") or "")
            if not name.lower().endswith(READABLE_SUFFIXES):
                continue
            files.append(
                RemoteFile(
                    # The mail id travels with the attachment id so a download
                    # can find it again without a second search.
                    id=f"{message_id}::{attachment.get('id')}",
                    name=name,
                    size=int(attachment.get("size") or 0),
                    path=str(message.get("subject") or ""),
                    kind="file",
                    modified=str(message.get("receivedDateTime") or ""),
                )
            )
    return files


async def download(access: str, provider: str, file_id: str) -> tuple[bytes, str]:
    """The bytes and the filename, fetched only when someone asks to read it."""
    if provider == "outlook":
        message_id, _, attachment_id = file_id.partition("::")
        payload = await _get(access, f"/me/messages/{message_id}/attachments/{attachment_id}")
        raw = payload.get("contentBytes")
        if not raw:
            raise GraphError("That attachment has no downloadable content.")
        return base64.b64decode(raw), str(payload.get("name") or "attachment")

    meta = await _get(
        access,
        f"/me/drive/items/{file_id}" if provider == "onedrive" else f"/drives/items/{file_id}",
    )
    url = meta.get("@microsoft.graph.downloadUrl")
    if not url:
        raise GraphError("Microsoft Graph did not return a download link for that file.")
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        response = await client.get(url)
    if response.status_code >= 400:
        raise GraphError(f"Downloading that file returned {response.status_code}.")
    return response.content, str(meta.get("name") or "document")
