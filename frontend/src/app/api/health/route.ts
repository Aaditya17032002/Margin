/** Container healthcheck. Deliberately does not touch the backend: this answers
 *  whether the web server is up, not whether the whole stack is. */
export function GET() {
  return Response.json({ status: "ok" });
}
