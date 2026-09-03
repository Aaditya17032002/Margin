import { create } from "zustand";
import { persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";

import { ApiError, authApi, clearTokens, setTokens } from "@/lib/api";
import { persistConfig } from "./persist";
import { fireAndForget } from "./remote";
import { clearWorkspace } from "./workspace-lifecycle";
import type { Org, SessionUser } from "@/types";

interface SessionState {
  user: SessionUser | null;
  org: Org | null;
  status: "idle" | "pending" | "error";
  error: string | null;
  onboarded: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<boolean>;
  loginWithMicrosoft: () => Promise<boolean>;
  signup: (input: { name: string; email: string; org: string; password: string }) => Promise<boolean>;
  logout: () => void;
  updateUser: (patch: Partial<SessionUser>) => void;
  updateOrg: (patch: Partial<Org>) => void;
  completeOnboarding: () => void;
  resetOnboarding: () => void;
  restoreFromApi: () => Promise<boolean>;
}

async function hydrateSession(
  set: (fn: (s: SessionState) => void) => void,
): Promise<boolean> {
  try {
    const me = await authApi.me();
    set((s) => {
      s.status = "idle";
      s.error = null;
      s.user = me.user;
      s.org = me.org;
      s.isAuthenticated = true;
    });
    return true;
  } catch (err) {
    clearTokens();
    set((s) => {
      s.status = "error";
      s.error =
        err instanceof ApiError
          ? err.detail
          : "That email and password combination wasn't recognised.";
      s.user = null;
      s.org = null;
      s.isAuthenticated = false;
    });
    return false;
  }
}

export const useSessionStore = create<SessionState>()(
  persist(
    immer((set) => ({
      user: null,
      org: null,
      status: "idle",
      error: null,
      onboarded: false,
      isAuthenticated: false,

      login: async (email, password) => {
        set((s) => {
          s.status = "pending";
          s.error = null;
        });
        try {
          const tokens = await authApi.login(email, password);
          setTokens(tokens.accessToken, tokens.refreshToken);
          return await hydrateSession(set);
        } catch (err) {
          set((s) => {
            s.status = "error";
            s.error =
              err instanceof ApiError
                ? err.detail
                : "That email and password combination wasn't recognised.";
            s.isAuthenticated = false;
          });
          return false;
        }
      },

      loginWithMicrosoft: async () => {
        set((s) => {
          s.status = "pending";
          s.error = null;
        });
        try {
          const tokens = await authApi.microsoft();
          setTokens(tokens.accessToken, tokens.refreshToken);
          return await hydrateSession(set);
        } catch (err) {
          set((s) => {
            s.status = "error";
            s.error = err instanceof ApiError ? err.detail : "Microsoft sign-in failed.";
            s.isAuthenticated = false;
          });
          return false;
        }
      },

      signup: async (input) => {
        set((s) => {
          s.status = "pending";
          s.error = null;
        });
        try {
          const tokens = await authApi.signup(input);
          setTokens(tokens.accessToken, tokens.refreshToken);
          const ok = await hydrateSession(set);
          if (ok) {
            set((s) => {
              s.onboarded = false;
            });
          }
          return ok;
        } catch (err) {
          set((s) => {
            s.status = "error";
            s.error = err instanceof ApiError ? err.detail : "Could not create the account.";
            s.isAuthenticated = false;
          });
          return false;
        }
      },

      logout: () => {
        void authApi.logout().catch(() => undefined);
        clearTokens();
        clearWorkspace();
        set((s) => {
          s.user = null;
          s.org = null;
          s.isAuthenticated = false;
          s.status = "idle";
          s.error = null;
        });
      },

      updateUser: (patch) => {
        set((s) => {
          if (s.user) Object.assign(s.user, patch);
        });
        fireAndForget(authApi.updateMe(patch), "Your profile could not be saved.");
      },

      updateOrg: (patch) => {
        set((s) => {
          if (s.org) Object.assign(s.org, patch);
        });
        fireAndForget(authApi.updateOrg(patch), "The organisation could not be saved.");
      },

      completeOnboarding: () =>
        set((s) => {
          s.onboarded = true;
        }),

      resetOnboarding: () =>
        set((s) => {
          s.onboarded = false;
        }),

      restoreFromApi: async () => hydrateSession(set),
    })),
    persistConfig<SessionState>("session", (s) => ({
      user: s.user,
      org: s.org,
      isAuthenticated: s.isAuthenticated,
      onboarded: s.onboarded,
    })),
  ),
);
