import type { NextConfig } from "next";

/**
 * The browser always talks to the same origin it loaded from, so there is no
 * CORS surface and server-sent events share the page's connection budget.
 *
 * In the compose topology Caddy answers `/api/*` before Next sees it. Running
 * `npm run dev` on its own, `src/app/api/v1/[...path]/route.ts` stands in — a
 * route handler rather than a rewrite, because a rewrite buffers the response
 * and a buffered event stream never arrives.
 */
const nextConfig: NextConfig = {
  output: "standalone",
};

export default nextConfig;
