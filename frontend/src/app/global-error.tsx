"use client";

/**
 * Replaces the root layout entirely when the failure is in the layout itself,
 * so it cannot rely on fonts, tokens, or any component from the design system.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: "100dvh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "2rem",
          background: "#F6F2E9",
          color: "#211D17",
          fontFamily: "Iowan Old Style, Georgia, serif",
        }}
      >
        <div style={{ maxWidth: "34rem" }}>
          <p
            style={{
              margin: 0,
              fontFamily: "ui-monospace, monospace",
              fontSize: "0.6875rem",
              letterSpacing: "0.13em",
              textTransform: "uppercase",
              color: "#8A8072",
            }}
          >
            Application error
          </p>
          <h1 style={{ margin: "0.5rem 0 0", fontSize: "1.875rem", fontWeight: 500, letterSpacing: "-0.028em" }}>
            Margin failed to start.
          </h1>
          <p style={{ margin: "1rem 0 0", lineHeight: 1.65, color: "#5B5347", fontFamily: "system-ui, sans-serif" }}>
            Nothing you saved has been deleted. Reload the page to try again.
            {error.digest ? ` (digest ${error.digest})` : ""}
          </p>
          <button
            type="button"
            onClick={reset}
            style={{
              marginTop: "1.75rem",
              padding: "0.5rem 1rem",
              border: "1px solid #211D17",
              borderRadius: "0.25rem",
              background: "#211D17",
              color: "#FCFAF4",
              font: "inherit",
              fontSize: "0.875rem",
              cursor: "pointer",
            }}
          >
            Reload
          </button>
        </div>
      </body>
    </html>
  );
}
