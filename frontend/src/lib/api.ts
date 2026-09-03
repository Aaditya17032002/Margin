/**
 * Thin fetch wrapper for the Margin backend.
 * Tokens live in localStorage so refresh survives a reload.
 */

const API_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "")) ||
  "http://localhost:8000";

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
  const url = path.startsWith("http") ? path : `${API_BASE}${path.startsWith("/") ? "" : "/"}${path}`;

  const reqHeaders = new Headers(headers);
  if (body !== undefined && !reqHeaders.has("Content-Type")) {
    reqHeaders.set("Content-Type", "application/json");
  }
  if (auth) {
    const token = getAccessToken();
    if (token) reqHeaders.set("Authorization", `Bearer ${token}`);
  }

  let res = await fetch(url, {
    ...rest,
    headers: reqHeaders,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  // One silent refresh on 401, then retry.
  if (res.status === 401 && auth) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      const retryHeaders = new Headers(reqHeaders);
      retryHeaders.set("Authorization", `Bearer ${getAccessToken()}`);
      res = await fetch(url, {
        ...rest,
        headers: retryHeaders,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    }
  }

  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
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

export const authApi = {
  login: (email: string, password: string) =>
    api<{ accessToken: string; refreshToken: string }>("/api/v1/auth/login", {
      method: "POST",
      body: { email, password },
      auth: false,
    }),

  signup: (input: { name: string; email: string; org: string; password: string }) =>
    api<{ accessToken: string; refreshToken: string }>("/api/v1/auth/signup", {
      method: "POST",
      body: input,
      auth: false,
    }),

  microsoft: () =>
    api<{ accessToken: string; refreshToken: string }>("/api/v1/auth/microsoft", {
      method: "POST",
      body: {},
      auth: false,
    }),

  me: () =>
    api<{
      user: {
        id: string;
        name: string;
        email: string;
        title: string;
        avatarTone: string;
        signature: string;
        timezone: string;
      };
      org: {
        id: string;
        name: string;
        domain: string;
        plan: string;
        seats: number;
        seatsUsed: number;
        duns: string;
        cage: string;
      };
    }>("/api/v1/auth/me"),

  logout: () => api<void>("/api/v1/auth/logout", { method: "POST" }),
};

export const analysesApi = {
  list: () => api<unknown[]>("/api/v1/analyses"),
  get: (id: string) => api<unknown>(`/api/v1/analyses/${id}`),
};

export { API_BASE };
