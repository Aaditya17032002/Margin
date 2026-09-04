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
class RemoteEntry:
    """One row in the browser, whatever the provider calls it underneath.

    ``id`` is an opaque token. The client hands it back to browse into the
    entry, or to import it, and never has to know that a SharePoint file needs
    a drive id while a mail attachment needs a message id.
    """

    id: str
    name: str
    #: site | drive | folder | message | file
    kind: str
    size: int = 0
    modified: str = ""
    #: The second line: who sent the mail, which folder the file is in.
    subtitle: str = ""
    #: True when this is something Margin can read. Everything else is a
    #: container you open.
    importable: bool = False

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "size": self.size,
            "modified": self.modified,
            "subtitle": self.subtitle,
            "importable": self.importable,
        }


class ConsentRequired(GraphError):
    """The tenant has not granted a permission this call needs.

    Distinct from a plain failure because the remedy is a person — an
    administrator — not a retry, and the workspace should say which permission
    to ask them for.
    """

    def __init__(self, scope: str, message: str = "") -> None:
        self.scope = scope
        super().__init__(message or f"An administrator must grant {scope} for this tenant.")


# Which permission each provider needs an admin to consent to, when it needs one.
ADMIN_SCOPES = {"sharepoint": "Sites.Read.All and Files.Read.All"}


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
    if response.status_code in (401, 403):
        # 403 on a Sites/Files call in a tenant that never granted admin
        # consent is the single most common way this goes wrong, and it needs
        # a person, not a retry.
        body = response.text
        if "Authorization_RequestDenied" in body or "AADSTS65001" in body or "accessDenied" in body:
            raise ConsentRequired(ADMIN_SCOPES.get("sharepoint", "the requested permission"))
        logger.error("graph_call_denied", path=path, status=response.status_code)
        raise GraphError("This connection is not permitted to read that. It may need re-authorising.")
    if response.status_code >= 400:
        logger.error("graph_call_failed", path=path, status=response.status_code)
        raise GraphError(f"Microsoft Graph returned {response.status_code} for {path}.")
    return response.json()


# ── Browsing ─────────────────────────────────────────────────────────────
#
# One walk covers all three providers. The client passes back whatever `id` it
# was given and never learns that a SharePoint file needs a drive id while a
# mail attachment needs a message id.
#
#   outlook      ""                       → recent mail with attachments
#                "msg:<id>"               → that mail's attachments
#   onedrive     ""                       → drive root
#                "item:<id>"              → that folder
#   sharepoint   ""                       → sites
#                "site:<id>"              → that site's document libraries
#                "drive:<id>"             → library root
#                "drive:<id>/item:<id>"   → that folder


def _readable(name: str) -> bool:
    return name.lower().endswith(READABLE_SUFFIXES)


async def browse(access: str, provider: str, path: str = "") -> list[RemoteEntry]:
    """One level of a connected source."""
    path = (path or "").strip()
    if provider == "outlook":
        return await _browse_mail(access, path)
    if provider == "onedrive":
        return await _browse_onedrive(access, path)
    if provider == "sharepoint":
        return await _browse_sharepoint(access, path)
    raise GraphError(f"Unknown provider: {provider}")


async def _browse_mail(access: str, path: str) -> list[RemoteEntry]:
    if path.startswith("msg:"):
        message_id = path[4:]
        payload = await _get(
            access, f"/me/messages/{message_id}/attachments", **{"$select": "id,name,size,contentType"}
        )
        return [
            RemoteEntry(
                id=f"msg:{message_id}/att:{a.get('id')}",
                name=str(a.get("name") or ""),
                kind="file",
                size=int(a.get("size") or 0),
                importable=True,
            )
            for a in payload.get("value", [])
            if _readable(str(a.get("name") or ""))
        ]

    # The mailbox itself: recent threads that carry something readable.
    # `$expand` matters — fetching attachments per message was a request per
    # row, which made opening the mailbox take seconds.
    payload = await _get(
        access,
        "/me/messages",
        **{
            "$filter": "hasAttachments eq true",
            "$select": "id,subject,receivedDateTime,from",
            "$expand": "attachments($select=id,name,size)",
            "$orderby": "receivedDateTime desc",
            "$top": 40,
        },
    )
    entries: list[RemoteEntry] = []
    for message in payload.get("value", []):
        readable = [a for a in (message.get("attachments") or []) if _readable(str(a.get("name") or ""))]
        if not readable:
            continue
        sender = ((message.get("from") or {}).get("emailAddress") or {})
        entries.append(
            RemoteEntry(
                id=f"msg:{message.get('id')}",
                name=str(message.get("subject") or "(no subject)"),
                kind="message",
                size=sum(int(a.get("size") or 0) for a in readable),
                modified=str(message.get("receivedDateTime") or ""),
                subtitle=str(sender.get("name") or sender.get("address") or ""),
                # A single readable attachment is the common case; skipping a
                # click into a one-item folder is the whole point of noticing.
                importable=False,
            )
        )
    return entries


async def _browse_onedrive(access: str, path: str) -> list[RemoteEntry]:
    endpoint = (
        f"/me/drive/items/{path[5:]}/children" if path.startswith("item:") else "/me/drive/root/children"
    )
    payload = await _get(access, endpoint, **{"$top": 200, "$orderby": "folder,name"})
    return _drive_entries(payload, prefix="")


async def _browse_sharepoint(access: str, path: str) -> list[RemoteEntry]:
    if not path:
        # `search=*` is the only reliable way to enumerate sites a person can
        # reach; `followedSites` is empty for most people, which read as a
        # broken integration rather than an empty one.
        payload = await _get(access, "/sites", **{"search": "*", "$top": 100})
        return [
            RemoteEntry(
                id=f"site:{site.get('id')}",
                name=str(site.get("displayName") or site.get("name") or ""),
                kind="site",
                subtitle=str(site.get("webUrl") or ""),
            )
            for site in payload.get("value", [])
            if site.get("id")
        ]

    if path.startswith("site:"):
        payload = await _get(access, f"/sites/{path[5:]}/drives", **{"$top": 100})
        return [
            RemoteEntry(
                id=f"drive:{drive.get('id')}",
                name=str(drive.get("name") or "Documents"),
                kind="drive",
                subtitle=str(drive.get("description") or "Document library"),
            )
            for drive in payload.get("value", [])
            if drive.get("id")
        ]

    drive_id, _, rest = path.partition("/")
    drive_id = drive_id[6:]
    endpoint = (
        f"/drives/{drive_id}/items/{rest[5:]}/children"
        if rest.startswith("item:")
        else f"/drives/{drive_id}/root/children"
    )
    payload = await _get(access, endpoint, **{"$top": 200, "$orderby": "folder,name"})
    return _drive_entries(payload, prefix=f"drive:{drive_id}/")


def _drive_entries(payload: dict, prefix: str) -> list[RemoteEntry]:
    """Folders first, then readable files. Everything else is not shown —
    offering a .pptx Margin cannot read is a dead end dressed as a choice."""
    folders: list[RemoteEntry] = []
    files: list[RemoteEntry] = []
    for item in payload.get("value", []):
        name = str(item.get("name") or "")
        item_id = str(item.get("id") or "")
        if not item_id or not name:
            continue
        token = f"{prefix}item:{item_id}"
        if "folder" in item:
            count = int((item.get("folder") or {}).get("childCount") or 0)
            folders.append(
                RemoteEntry(
                    id=token,
                    name=name,
                    kind="folder",
                    modified=str(item.get("lastModifiedDateTime") or ""),
                    subtitle=f"{count} item{'' if count == 1 else 's'}" if count else "Empty",
                )
            )
        elif _readable(name):
            files.append(
                RemoteEntry(
                    id=token,
                    name=name,
                    kind="file",
                    size=int(item.get("size") or 0),
                    modified=str(item.get("lastModifiedDateTime") or ""),
                    subtitle=str(((item.get("lastModifiedBy") or {}).get("user") or {}).get("displayName") or ""),
                    importable=True,
                )
            )
    return folders + files


async def download(access: str, provider: str, file_id: str) -> tuple[bytes, str]:
    """The bytes and the filename, fetched only when someone asks to read it."""
    if provider == "outlook":
        return await _download_attachment(access, file_id)

    if provider == "onedrive":
        item_id = file_id[5:] if file_id.startswith("item:") else file_id
        meta = await _get(access, f"/me/drive/items/{item_id}")
    else:
        drive_part, _, item_part = file_id.partition("/")
        if not drive_part.startswith("drive:") or not item_part.startswith("item:"):
            raise GraphError("That file reference is not one Margin issued.")
        meta = await _get(access, f"/drives/{drive_part[6:]}/items/{item_part[5:]}")

    url = meta.get("@microsoft.graph.downloadUrl")
    if not url:
        raise GraphError("Microsoft Graph did not return a download link for that file.")
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        response = await client.get(url)
    if response.status_code >= 400:
        raise GraphError(f"Downloading that file returned {response.status_code}.")
    return response.content, str(meta.get("name") or "document")


async def _download_attachment(access: str, file_id: str) -> tuple[bytes, str]:
    message_part, _, attachment_part = file_id.partition("/")
    if not message_part.startswith("msg:") or not attachment_part.startswith("att:"):
        raise GraphError("That attachment reference is not one Margin issued.")
    payload = await _get(
        access, f"/me/messages/{message_part[4:]}/attachments/{attachment_part[4:]}"
    )
    raw = payload.get("contentBytes")
    if not raw:
        raise GraphError("That attachment has no downloadable content.")
    return base64.b64decode(raw), str(payload.get("name") or "attachment")
