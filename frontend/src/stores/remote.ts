import { toast } from "sonner";

import { ApiError } from "@/lib/api";

/**
 * Every collection in the workspace now lives on the server. The stores keep a
 * local copy so the UI stays synchronous and optimistic, and each one reports
 * the same three things about that copy: whether it has been fetched, whether a
 * fetch is in flight, and what went wrong if one did.
 */
export type LoadStatus = "idle" | "loading" | "ready" | "error";

export interface RemoteSlice {
  status: LoadStatus;
  error: string | null;
  loaded: boolean;
}

export const initialRemote: RemoteSlice = {
  status: "idle",
  error: null,
  loaded: false,
};

export function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) return error.detail;
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

/**
 * Writes are optimistic: the store mutates first so the interface answers
 * immediately, then the request goes out. If it fails the caller is told, and
 * the store reloads rather than trying to invert an edit it no longer has the
 * original for.
 */
export function fireAndForget(promise: Promise<unknown>, fallback = "That change could not be saved.") {
  void promise.catch((error: unknown) => {
    toast.error("Not saved", { description: errorMessage(error, fallback) });
  });
}
