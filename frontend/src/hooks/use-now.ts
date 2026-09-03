"use client";

import * as React from "react";

/**
 * The clock as an external store rather than an effect.
 *
 * Rendering "now" during the server pass would guarantee a hydration mismatch,
 * so the server snapshot is deliberately zero and every consumer treats zero as
 * "not mounted yet" — the countdown shows a dash for one frame instead of a
 * wrong number. Subscribing at a coarse interval also keeps the whole app on a
 * single timer per interval rather than one per countdown.
 */
export function useNow(intervalMs = 1000): number {
  const subscribe = React.useCallback(
    (onChange: () => void) => {
      const id = window.setInterval(onChange, intervalMs);
      return () => window.clearInterval(id);
    },
    [intervalMs],
  );

  return React.useSyncExternalStore(
    subscribe,
    () => Math.floor(Date.now() / intervalMs) * intervalMs,
    () => 0,
  );
}

/** True once the client has taken over — safe to render time-dependent output. */
export function useMounted(): boolean {
  return useNow(60_000) !== 0;
}
