# Integrations

Margin reads solicitations. Solicitations arrive in a mailbox, a SharePoint
library, or a OneDrive folder. This document is everything an administrator
needs to let Margin reach them, and everything a developer needs to understand
what Margin does with that access.

There are two ways in, and most workspaces end up using both:

| | Setup | Best for |
|---|---|---|
| **Microsoft connectors** | One app registration, consented once per workspace | A person browsing their own mail or SharePoint and picking a document |
| **The ingest address** | Copy one URL out of Settings → Integrations | A flow, rule, or script that should hand Margin a file automatically |

---

## 1. What Margin does with the access

Read this before granting anything, because it is short and it is the whole
contract.

- **Nothing is synced.** Margin does not crawl, mirror, or index a tenant in the
  background. It lists one folder when someone opens it and downloads one file
  when someone picks it.
- **Read-only.** No connector asks for write, send, or delete on any Microsoft
  scope. Margin cannot alter a mailbox or a library.
- **Only readable documents.** Browsing filters to `.pdf`, `.docx`, `.doc`,
  `.txt`, `.md`, `.rtf`, `.htm`, `.html`. Other files are never listed and never
  fetched.
- **Only refresh tokens are stored**, encrypted at rest with a key derived from
  `SECRET_KEY`. Access tokens live in memory for the few minutes they are valid
  and are never written to the database. Disconnecting deletes the refresh
  token; rotating `SECRET_KEY` invalidates every stored token at once.
- **What is kept** is the document's extracted text and the file itself, on the
  workspace's own storage, so a re-read never has to go back to the tenant.

---

## 2. Microsoft app registration

One registration serves all three connectors.

### 2.1 Create it

Azure Portal → **Microsoft Entra ID** → **App registrations** → **New
registration**.

- **Name:** `Margin`
- **Supported account types:** *Accounts in this organizational directory only*
  (single tenant) unless you are running Margin for several tenants.
- **Redirect URI:** platform **Web**, value:

  ```
  https://<your-margin-host>/api/v1/integrations/outlook/callback
  ```

  Then add two more under **Authentication → Add URI**:

  ```
  https://<your-margin-host>/api/v1/integrations/sharepoint/callback
  https://<your-margin-host>/api/v1/integrations/onedrive/callback
  ```

  For local development add the same three against `http://localhost:8000`.
  These must match character for character — a trailing slash is a mismatch.

### 2.2 Client secret

**Certificates & secrets → New client secret.** Copy the **Value** (not the
Secret ID) immediately; it is shown once. Set a 12- or 24-month expiry and put
the renewal in a calendar — an expired secret takes every connector offline at
the same moment.

### 2.3 Record three values

From **Overview**: Application (client) ID, Directory (tenant) ID; plus the
secret value from above.

---

## 3. Permissions, per connector

All of these are **delegated** permissions (Microsoft Graph → *Delegated
permissions*). Margin acts as the signed-in person and can never see more than
they can. Add every scope for each connector you intend to enable.

### Outlook — reading solicitations out of mail

| Permission | Type | Why Margin needs it |
|---|---|---|
| `offline_access` | Delegated | Keeps the connection alive without asking for consent on every read. Without it, browsing breaks minutes after connecting. |
| `User.Read` | Delegated | Reads the signed-in account's name so the workspace can show which mailbox is connected. |
| `Mail.Read` | Delegated | Lists the 25 most recent messages that carry an attachment, and downloads the attachment someone picks. |

Margin never sends, moves, marks, or deletes mail. `Mail.Send` and
`Mail.ReadWrite` are not requested and must not be granted.

### OneDrive — reading a personal drive

| Permission | Type | Why Margin needs it |
|---|---|---|
| `offline_access` | Delegated | As above. |
| `User.Read` | Delegated | As above. |
| `Files.Read` | Delegated | Lists one folder at a time in the signed-in person's drive and downloads the file they pick. |

`Files.ReadWrite` is not requested. Margin cannot save anything into OneDrive.

### SharePoint — reading a team library

| Permission | Type | Why Margin needs it |
|---|---|---|
| `offline_access` | Delegated | As above. |
| `User.Read` | Delegated | As above. |
| `Sites.Read.All` | Delegated | Lists the sites the person follows, so they can find the right library. |
| `Files.Read.All` | Delegated | Reads documents from libraries the person already has access to. |

`Sites.Read.All` is tenant-wide in name but delegated in effect: Margin sees
only what the signed-in person can see. If your security posture requires it,
use `Sites.Selected` (application permission) instead and grant Margin access
to named sites only — note that this changes the flow to app-only auth and is
not what the connector implements today.

### Admin consent

`Sites.Read.All` and `Files.Read.All` require a Global Administrator or
Privileged Role Administrator to click **Grant admin consent for \<tenant\>** on
the **API permissions** page. `Mail.Read`, `Files.Read`, `User.Read` and
`offline_access` can be consented by each user at first connect, but granting
admin consent up front means nobody sees a consent dialog.

---

## 4. Configuring Margin

Set these on the API container (and the worker, which shares the same settings
module):

```bash
MS_CLIENT_ID=<application (client) id>
MS_CLIENT_SECRET=<the secret *value*>
MS_TENANT_ID=<directory (tenant) id>
MS_REDIRECT_URI=https://<your-margin-host>/api/v1/auth/microsoft/callback

# Used to derive the token-encryption key and the ingest address.
# Rotating this revokes every stored connector token and every ingest URL.
SECRET_KEY=<openssl rand -hex 64>

# Where the first ALLOWED_ORIGINS entry is the app the callback returns to.
ALLOWED_ORIGINS=https://<your-margin-host>
```

Restart the API. Settings → Integrations will now offer **Connect** rather than
reporting that Microsoft sign-in is not configured.

### Verifying

```bash
# 1. Start a connection (returns the consent URL and the scopes it will ask for)
curl -X POST https://<host>/api/v1/integrations/onedrive/authorize \
     -H "Authorization: Bearer <access token>"

# 2. Open that URL in a browser, consent, and you are redirected back.

# 3. Browse
curl https://<host>/api/v1/integrations/onedrive/files \
     -H "Authorization: Bearer <access token>"

# 4. Read a document
curl -X POST https://<host>/api/v1/integrations/onedrive/import \
     -H "Authorization: Bearer <access token>" \
     -H "Content-Type: application/json" \
     -d '{"fileIds":["<id from step 3>"]}'
```

Step 4 creates an analysis and starts the reading pass. Pass `"analysisId"`
alongside `fileIds` to attach the document to an analysis that already exists
instead of creating a new one.

---

## 5. The ingest address — a way in for everything else

Every workspace has one URL that accepts a document and starts reading it. It
needs no OAuth, no SDK, and no session, which makes it the right target for a
Power Automate flow, an Outlook rule, a cron job, or a partner's script.

Find it in the app under Settings → Integrations, or:

```bash
curl https://<host>/api/v1/ingest/address -H "Authorization: Bearer <token>"
```

```json
{
  "url": "https://<host>/api/v1/ingest/org_1a2b….9f8e7d…",
  "method": "POST",
  "field": "file"
}
```

Post to it:

```bash
curl -X POST "https://<host>/api/v1/ingest/<address>" \
     -F "file=@RFP-2026-0041.pdf" \
     -F "title=ARTS 311 CRM" \
     -F "agency=NYC DOT" \
     -F "mode=standard"
```

```json
{ "analysisId": "an_9f3c1d2e4b5a", "queued": true, "fileName": "RFP-2026-0041.pdf" }
```

`title`, `agency` and `mode` are optional; `mode` is one of `quick-triage`,
`standard`, `deep-research`, `matrix-only`, `qa-only` and defaults to
`standard`.

**The URL is the credential.** Anyone holding it can start an analysis in that
workspace. Store it as a secret in whatever is calling it, do not paste it into
a ticket, and rotate `SECRET_KEY` if it leaks — that invalidates every
workspace's address at once, so treat it as a break-glass action.

### Power Automate, in five steps

1. Trigger: *When a new email arrives (V3)* — filter to the mailbox and subject
   pattern that matters, with **Only with Attachments** set to *Yes*.
2. Action: *Get attachment (V2)*.
3. Action: **HTTP** → `POST` → the ingest URL.
4. Body: `multipart/form-data`, one part named `file`, content the attachment
   bytes, filename the attachment name.
5. Optional: add a `title` part bound to the mail subject.

The same shape works for SharePoint's *When a file is created in a folder*
trigger.

---

## 6. Troubleshooting

| What you see | What it means |
|---|---|
| `Microsoft sign-in is not configured` (501) | `MS_CLIENT_ID`, `MS_CLIENT_SECRET` or `MS_TENANT_ID` is unset on the API container. |
| `AADSTS50011: redirect URI mismatch` | The URI in the app registration is not character-identical to `https://<host>/api/v1/integrations/<provider>/callback`. |
| `Microsoft did not return a refresh token` | `offline_access` was not among the granted scopes. Add it and reconnect. |
| `That sign-in link has expired` | More than ten minutes passed between starting and finishing consent, or Redis restarted. Start again. |
| `This connection needs to be re-authorised` | The stored refresh token is gone or unreadable — usually `SECRET_KEY` was rotated. Disconnect and reconnect. |
| `AADSTS65001: user or administrator has not consented` | `Sites.Read.All` / `Files.Read.All` need admin consent. See §3. |
| Browsing returns an empty list | Expected when the folder holds no readable document type. Check the extensions in §1. |
| `Unknown ingest address` (404) | The URL is wrong, or `SECRET_KEY` changed since it was copied. Fetch the address again. |

---

## 7. What is not built yet

Stated plainly so nobody plans around it:

- **Application (app-only) permissions.** Every connector is delegated today.
  A daemon that reads a shared mailbox nobody signs into would need app-only
  auth and `Mail.Read` / `Sites.Selected` as application permissions.
- **Change notifications.** Margin does not subscribe to Graph webhooks, so a
  new file in a watched library does not import itself. Use the ingest address
  with a SharePoint trigger for that today.
- **Google Workspace and Box.** Neither is implemented. The ingest address is
  the supported path for both.
