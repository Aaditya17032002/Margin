import type { NextConfig } from "next";

/**
 * The browser always talks to the same origin it loaded from, so there is no
 * CORS surface and SSE streams share the page's connection budget. In the
 * compose topology Caddy answers `/api/*` before Next sees it; running
 * `npm run dev` on its own, this rewrite stands in for the proxy.
 */
const backendOrigin = process.env.BACKEND_ORIGIN ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendOrigin}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
