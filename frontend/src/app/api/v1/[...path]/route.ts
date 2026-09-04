/**
 * The development proxy for `/api/v1/*`.
 *
 * In the compose topology Caddy answers these paths and Next never sees them.
 * Running `next dev` on its own, something has to stand in — and a
 * `next.config.ts` rewrite is not enough: it buffers a response instead of
 * streaming it, which silently kills every server-sent event the reading room
 * and the notification bell depend on. A route handler hands the upstream body
 * back untouched, so bytes reach the browser as the backend writes them.
 */

const BACKEND = (process.env.BACKEND_ORIGIN ?? "http://localhost:8000").replace(/\/$/, "");

/** Never cached, always run per request — this is a proxy, not a page. */
export const dynamic = "force-dynamic";

/** Hop-by-hop headers are meaningless to the next connection, and a stale
 *  content-length would contradict a streamed body. */
const STRIPPED = new Set([
  "connection",
  "keep-alive",
  "transfer-encoding",
  "upgrade",
  "content-length",
  "content-encoding",
  "host",
]);

async function proxy(request: Request, path: string[]) {
  const incoming = new URL(request.url);
  const target = `${BACKEND}/api/v1/${path.map(encodeURIComponent).join("/")}${incoming.search}`;

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!STRIPPED.has(key.toLowerCase())) headers.set(key, value);
  });
  // Compression is what turns a live stream into one buffered blob.
  headers.set("accept-encoding", "identity");

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
      // Required by undici whenever a request carries a streamed body.
      duplex: "half",
      redirect: "manual",
      cache: "no-store",
    } as RequestInit & { duplex: "half" });
  } catch {
    return Response.json(
      { detail: `The API at ${BACKEND} is not reachable. Is the backend running?` },
      { status: 502 },
    );
  }

  const responseHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!STRIPPED.has(key.toLowerCase())) responseHeaders.set(key, value);
  });
  if (upstream.headers.get("content-type")?.includes("text/event-stream")) {
    responseHeaders.set("cache-control", "no-cache, no-transform");
    responseHeaders.set("x-accel-buffering", "no");
  }

  // The body is passed through as a stream; nothing here reads it.
  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}

async function segments(context: { params: Promise<unknown> }) {
  const params = (await context.params) as { path?: string[] };
  return params.path ?? [];
}

export async function GET(request: Request, context: { params: Promise<unknown> }) {
  return proxy(request, await segments(context));
}
export async function POST(request: Request, context: { params: Promise<unknown> }) {
  return proxy(request, await segments(context));
}
export async function PUT(request: Request, context: { params: Promise<unknown> }) {
  return proxy(request, await segments(context));
}
export async function PATCH(request: Request, context: { params: Promise<unknown> }) {
  return proxy(request, await segments(context));
}
export async function DELETE(request: Request, context: { params: Promise<unknown> }) {
  return proxy(request, await segments(context));
}
export async function HEAD(request: Request, context: { params: Promise<unknown> }) {
  return proxy(request, await segments(context));
}
