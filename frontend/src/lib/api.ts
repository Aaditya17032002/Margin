/**
 * The one place the frontend talks to the backend.
 *
 * Requests go to the same origin the page was served from — Caddy answers
 * `/api/*` in the compose topology, and `next.config.ts` rewrites it to the
 * backend during `npm run dev`. `NEXT_PUBLIC_API_URL` overrides that for the
 * unusual case of a backend on a different host.
 *
 * Tokens live in localStorage so a refresh survives a reload.
 */

import type {
  ActivityEntry,
  Analysis,
  AnalysisMode,
  AppNotification,
  DocType,
  ExportRecord,
  FileNode,
  Integration,
  IntegrationId,
  MatrixRow,
  MatrixStatus,
  Org,
  PastBid,
  Prefs,
  QAQuestion,
  Role,
  SessionUser,
  Template,
  TeamMember,
} from "@/types";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");

const ACCESS_KEY = "margin.access_token";
const REFRESH_KEY = "margin.refresh_token";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

export function getAccessToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

type ApiOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  auth?: boolean;
};

function url(path: string) {
  if (path.startsWith("http")) return path;
  return `${API_BASE}${path.startsWith("/") ? "" : "/"}${path}`;
}

async function parseError(res: Response): Promise<ApiError> {
  try {
    const data = (await res.json()) as { detail?: string | { msg?: string }[] };
    const detail =
      typeof data.detail === "string"
        ? data.detail
        : Array.isArray(data.detail)
          ? data.detail.map((d) => d.msg ?? JSON.stringify(d)).join("; ")
          : res.statusText;
    return new ApiError(res.status, detail || res.statusText);
  } catch {
    return new ApiError(res.status, res.statusText);
  }
}

export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { body, auth = true, headers, ...rest } = options;

  const reqHeaders = new Headers(headers);
  const isFormData = body instanceof FormData;
  if (body !== undefined && !isFormData && !reqHeaders.has("Content-Type")) {
    reqHeaders.set("Content-Type", "application/json");
  }
  if (auth) {
    const token = getAccessToken();
    if (token) reqHeaders.set("Authorization", `Bearer ${token}`);
  }

  const payload = body === undefined ? undefined : isFormData ? body : JSON.stringify(body);

  let res = await fetch(url(path), { ...rest, headers: reqHeaders, body: payload });

  // One silent refresh on 401, then retry.
  if (res.status === 401 && auth) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      const retryHeaders = new Headers(reqHeaders);
      retryHeaders.set("Authorization", `Bearer ${getAccessToken()}`);
      res = await fetch(url(path), { ...rest, headers: retryHeaders, body: payload });
    }
  }

  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return undefined as T;

  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

async function tryRefresh(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  try {
    const data = await api<{ accessToken: string; refreshToken: string }>("/api/v1/auth/refresh", {
      method: "POST",
      body: { refreshToken: refresh },
      auth: false,
    });
    setTokens(data.accessToken, data.refreshToken);
    return true;
  } catch {
    clearTokens();
    return false;
  }
}

/* ------------------------------------------------------------------ */
/* Auth                                                                 */
/* ------------------------------------------------------------------ */

interface Tokens {
  accessToken: string;
  refreshToken: string;
}

export const authApi = {
  login: (email: string, password: string) =>
    api<Tokens>("/api/v1/auth/login", { method: "POST", body: { email, password }, auth: false }),

  signup: (input: { name: string; email: string; org: string; password: string }) =>
    api<Tokens>("/api/v1/auth/signup", { method: "POST", body: input, auth: false }),

  microsoft: () =>
    api<Tokens>("/api/v1/auth/microsoft", { method: "POST", body: {}, auth: false }),

  me: () => api<{ user: SessionUser; org: Org }>("/api/v1/auth/me"),

  updateMe: (patch: Partial<SessionUser>) =>
    api<SessionUser>("/api/v1/auth/me", { method: "PATCH", body: patch }),

  updateOrg: (patch: Partial<Org>) =>
    api<Org>("/api/v1/auth/org", { method: "PATCH", body: patch }),

  logout: () => api<void>("/api/v1/auth/logout", { method: "POST" }),
};

/* ------------------------------------------------------------------ */
/* Analyses                                                             */
/* ------------------------------------------------------------------ */

export interface CreateAnalysisInput {
  title: string;
  agency: string;
  solicitationNumber?: string;
  docType?: DocType;
  mode: AnalysisMode;
  fileName: string;
  fileSize: number;
  source: Analysis["source"];
  owner: string;
}

export const analysesApi = {
  list: () => api<Analysis[]>("/api/v1/analyses"),

  get: (id: string) => api<Analysis>(`/api/v1/analyses/${id}`),

  create: (input: CreateAnalysisInput) =>
    api<Analysis>("/api/v1/analyses", { method: "POST", body: input }),

  update: (id: string, patch: Partial<Analysis>) =>
    api<Analysis>(`/api/v1/analyses/${id}`, { method: "PATCH", body: patch }),

  remove: (id: string) => api<void>(`/api/v1/analyses/${id}`, { method: "DELETE" }),

  duplicate: (id: string) => api<Analysis>(`/api/v1/analyses/${id}/duplicate`, { method: "POST" }),

  restore: (id: string) => api<Analysis>(`/api/v1/analyses/${id}/restore`, { method: "POST" }),

  decide: (id: string, decision: Analysis["goNoGo"], note?: string) =>
    api<Analysis>(`/api/v1/analyses/${id}/decide`, { method: "POST", body: { decision, note } }),

  run: (id: string, idempotencyKey?: string) =>
    api<{ jobId: string; status: string }>(`/api/v1/analyses/${id}/run`, {
      method: "POST",
      body: { idempotencyKey },
    }),

  uploadDocument: (id: string, file: File, kind: "base" | "attachment" | "amendment" = "base") => {
    const form = new FormData();
    form.append("file", file);
    form.append("kind", kind);
    return api<{ id: string; fileName: string; pageCount: number; hasText: boolean }>(
      `/api/v1/analyses/${id}/document`,
      { method: "POST", body: form },
    );
  },

  versions: (id: string) => api<Analysis["versions"]>(`/api/v1/analyses/${id}/versions`),
};

/* ------------------------------------------------------------------ */
/* Matrix                                                               */
/* ------------------------------------------------------------------ */

export const matrixApi = {
  list: (analysisId: string) => api<MatrixRow[]>(`/api/v1/analyses/${analysisId}/matrix`),

  create: (analysisId: string, row: Omit<MatrixRow, "id" | "analysisId">) =>
    api<MatrixRow>(`/api/v1/analyses/${analysisId}/matrix`, { method: "POST", body: row }),

  update: (analysisId: string, rowId: string, patch: Partial<MatrixRow>) =>
    api<MatrixRow>(`/api/v1/analyses/${analysisId}/matrix/${rowId}`, {
      method: "PATCH",
      body: patch,
    }),

  remove: (analysisId: string, rowId: string) =>
    api<void>(`/api/v1/analyses/${analysisId}/matrix/${rowId}`, { method: "DELETE" }),

  bulk: (analysisId: string, ids: string[], patch: { owner?: string | null; status?: MatrixStatus }) =>
    api<{ updated: number }>(`/api/v1/analyses/${analysisId}/matrix/bulk`, {
      method: "POST",
      body: { ids, ...patch },
    }),
};

/* ------------------------------------------------------------------ */
/* Questions                                                            */
/* ------------------------------------------------------------------ */

export const questionsApi = {
  list: (analysisId: string) => api<QAQuestion[]>(`/api/v1/analyses/${analysisId}/questions`),

  create: (analysisId: string, input: Omit<QAQuestion, "id" | "analysisId" | "order" | "sent">) =>
    api<QAQuestion>(`/api/v1/analyses/${analysisId}/questions`, { method: "POST", body: input }),

  update: (analysisId: string, questionId: string, patch: Partial<QAQuestion>) =>
    api<QAQuestion>(`/api/v1/analyses/${analysisId}/questions/${questionId}`, {
      method: "PATCH",
      body: patch,
    }),

  remove: (analysisId: string, questionId: string) =>
    api<void>(`/api/v1/analyses/${analysisId}/questions/${questionId}`, { method: "DELETE" }),

  reorder: (analysisId: string, orderedIds: string[]) =>
    api<{ reordered: number }>(`/api/v1/analyses/${analysisId}/questions/reorder`, {
      method: "PATCH",
      body: { orderedIds },
    }),
};

/* ------------------------------------------------------------------ */
/* Findings                                                             */
/* ------------------------------------------------------------------ */

export type FindingSection =
  | "identity"
  | "scope"
  | "legal"
  | "eligibility"
  | "pricing"
  | "postAward";

export const findingsApi = {
  update: (
    analysisId: string,
    section: FindingSection,
    findingId: string,
    patch: { verified?: boolean; flagged?: boolean; value?: string; detail?: string },
  ) =>
    api<unknown>(`/api/v1/analyses/${analysisId}/findings/${section}.${findingId}`, {
      method: "PATCH",
      body: patch,
    }),
};

/* ------------------------------------------------------------------ */
/* Workspace resources                                                  */
/* ------------------------------------------------------------------ */

export const notificationsApi = {
  list: () => api<AppNotification[]>("/api/v1/notifications"),

  create: (input: Omit<AppNotification, "id" | "at" | "read">) =>
    api<AppNotification>("/api/v1/notifications", { method: "POST", body: input }),

  markRead: (id: string, read = true) =>
    api<AppNotification>(`/api/v1/notifications/${id}`, { method: "PATCH", body: { read } }),

  markAllRead: () => api<{ status: string }>("/api/v1/notifications/read-all", { method: "POST" }),

  remove: (id: string) => api<void>(`/api/v1/notifications/${id}`, { method: "DELETE" }),

  clearAll: () => api<void>("/api/v1/notifications", { method: "DELETE" }),
};

export const teamApi = {
  list: () => api<TeamMember[]>("/api/v1/team/members"),

  invite: (input: { name: string; email: string; role: Role; title: string }) =>
    api<TeamMember>("/api/v1/team/invites", { method: "POST", body: input }),

  update: (id: string, patch: Partial<Pick<TeamMember, "role" | "title" | "status">>) =>
    api<TeamMember>(`/api/v1/team/members/${id}`, { method: "PATCH", body: patch }),

  remove: (id: string) => api<void>(`/api/v1/team/members/${id}`, { method: "DELETE" }),
};

export const integrationsApi = {
  list: () => api<Integration[]>("/api/v1/integrations"),

  /**
   * Begin a real Microsoft consent round trip. Answers 501 when the deployment
   * has no Microsoft credentials, which is the signal to fall back to marking
   * the connection by hand.
   */
  authorize: (id: IntegrationId) =>
    api<{ url: string; scopes: string[] }>(`/api/v1/integrations/${id}/authorize`, {
      method: "POST",
    }),

  /** The workspace's drop box: post a document here and Margin reads it. */
  ingestAddress: () =>
    api<{ url: string; method: string; field: string; note: string }>("/api/v1/ingest/address"),

  connect: (id: IntegrationId, account?: string) =>
    api<Integration>(`/api/v1/integrations/${id}/connect`, { method: "POST", body: { account } }),

  disconnect: (id: IntegrationId) =>
    api<Integration>(`/api/v1/integrations/${id}/disconnect`, { method: "DELETE" }),

  files: (id: IntegrationId) => api<FileNode[]>(`/api/v1/integrations/${id}/files`),

  import: (id: IntegrationId, fileIds: string[], analysisId?: string) =>
    api<{ imported: number; results: { fileId: string; analysisId?: string; error?: string }[] }>(
      `/api/v1/integrations/${id}/import`,
      { method: "POST", body: { fileIds, analysisId } },
    ),
};

export const templatesApi = {
  list: () => api<Template[]>("/api/v1/templates"),

  create: (input: Omit<Template, "id" | "updatedAt" | "usageCount">) =>
    api<Template>("/api/v1/templates", { method: "POST", body: input }),

  update: (id: string, patch: Partial<Template>) =>
    api<Template>(`/api/v1/templates/${id}`, { method: "PATCH", body: patch }),

  remove: (id: string) => api<void>(`/api/v1/templates/${id}`, { method: "DELETE" }),
};

export const knowledgeApi = {
  list: () => api<PastBid[]>("/api/v1/knowledge"),

  create: (input: Omit<PastBid, "id">) =>
    api<PastBid>("/api/v1/knowledge", { method: "POST", body: input }),

  update: (id: string, patch: Partial<PastBid>) =>
    api<PastBid>(`/api/v1/knowledge/${id}`, { method: "PATCH", body: patch }),

  remove: (id: string) => api<void>(`/api/v1/knowledge/${id}`, { method: "DELETE" }),
};

export const reportsApi = {
  list: () => api<ExportRecord[]>("/api/v1/reports"),

  generate: (
    analysisId: string,
    input: {
      templateName: string;
      format: ExportRecord["format"];
      destination: ExportRecord["destination"];
      idempotencyKey?: string;
    },
  ) => api<ExportRecord>(`/api/v1/analyses/${analysisId}/report`, { method: "POST", body: input }),

  /**
   * Fetch the rendered file and hand it to the browser.
   *
   * Opening the URL in a new tab cannot work: the endpoint is authenticated
   * with a bearer token held in this tab, and a plain navigation carries no
   * Authorization header — so every download answered 401 and looked to a user
   * like reports simply could not be downloaded. Fetching it here keeps the
   * header, and the object URL does the saving.
   */
  download: async (id: string, filename: string) => {
    const res = await fetch(url(`/api/v1/reports/${id}`), {
      headers: { Authorization: `Bearer ${getAccessToken() ?? ""}` },
    });
    if (!res.ok) throw await parseError(res);

    const blob = await res.blob();
    const href = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = href;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    // Revoked on the next frame: Safari cancels a download whose blob URL is
    // released in the same tick as the click.
    requestAnimationFrame(() => URL.revokeObjectURL(href));
  },
};

export const activityApi = {
  list: (limit = 100) => api<ActivityEntry[]>(`/api/v1/activity?limit=${limit}`),

  log: (input: Omit<ActivityEntry, "id" | "at">) =>
    api<ActivityEntry>("/api/v1/activity", { method: "POST", body: input }),
};

export const deadlinesApi = {
  list: () =>
    api<
      {
        id: string;
        label: string;
        at: string;
        timezone: string;
        kind: string;
        analysisId: string;
        analysisTitle: string;
      }[]
    >("/api/v1/deadlines"),
};

export const prefsApi = {
  get: () => api<Prefs>("/api/v1/preferences"),
  update: (patch: Partial<Prefs>) => api<Prefs>("/api/v1/preferences", { method: "PUT", body: patch }),
};

export const searchApi = {
  query: (q: string) =>
    api<{ kind: "analysis" | "knowledge"; id: string; title: string; snippet: string; score: number }[]>(
      `/api/v1/search?q=${encodeURIComponent(q)}`,
    ),
};

/* ------------------------------------------------------------------ */
/* Server-sent events                                                   */
/* ------------------------------------------------------------------ */

export interface RunEvent {
  event: string;
  agent?: string;
  text?: string;
  finding?: unknown;
  error?: string;
  [key: string]: unknown;
}

export interface EventStream {
  /** Closes the connection. */
  stop: () => void;
  /** Resolves when the server confirms it is subscribed — it sends a
   *  `stream_ready` frame once, after the subscription exists. Anything that
   *  would publish an event must wait on this: the channel has no replay, so an
   *  event sent before the subscription lands is simply lost. Falls back to the
   *  response headers for a stream that sends no such frame. */
  ready: Promise<void>;
}

/**
 * `EventSource` cannot carry an Authorization header, so the stream is read off
 * a plain fetch instead.
 */
export function streamEvents(
  path: string,
  onEvent: (event: RunEvent) => void,
  onError?: (error: unknown) => void,
  options: { readyEvent?: string } = {},
): EventStream {
  const controller = new AbortController();
  let markReady: () => void = () => {};
  const ready = new Promise<void>((resolve) => {
    markReady = resolve;
  });

  void (async () => {
    try {
      const res = await fetch(url(path), {
        headers: { Authorization: `Bearer ${getAccessToken() ?? ""}`, Accept: "text/event-stream" },
        signal: controller.signal,
      });
      if (!res.ok || !res.body) throw await parseError(res);
      if (!options.readyEvent) markReady();

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // A frame ends at a blank line, and the spec allows CRLF, LF or CR as
        // the line break — sse-starlette sends CRLF, so matching only "\n\n"
        // finds no boundary at all and the stream goes silent.
        for (;;) {
          const boundary = buffer.search(/\r\n\r\n|\n\n|\r\r/);
          if (boundary === -1) break;
          const frame = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + (buffer[boundary] === "\r" && buffer[boundary + 1] === "\n" ? 4 : 2));

          const data = frame
            .split(/\r\n|\n|\r/)
            .filter((line) => line.startsWith("data:"))
            .map((line) => line.slice(5).trim())
            .join("");
          if (!data) continue;

          try {
            const parsed = JSON.parse(data) as RunEvent;
            if (options.readyEvent && parsed.event === options.readyEvent) {
              markReady();
            } else {
              onEvent(parsed);
            }
          } catch {
            // Keep-alives and comments are not JSON; ignoring them is correct.
          }
        }
      }
    } catch (error) {
      markReady();
      if ((error as Error)?.name === "AbortError") return;
      onError?.(error);
    }
  })();

  return { stop: () => controller.abort(), ready };
}

export { API_BASE };
