import { create } from "zustand";

export { useSessionStore } from "./session";
export { useAnalysesStore, selectAnalysis, allFindings } from "./analyses";
export { useMatrixStore, useRowsFor } from "./matrix";
export { useQAStore, useQuestionsFor } from "./qa";
export {
  useNotificationsStore,
  selectUnreadCount,
  useTeamStore,
  useIntegrationsStore,
  useTemplatesStore,
  useKnowledgeStore,
  useReportsStore,
  usePrefsStore,
} from "./workspace";
export { useUIStore } from "./ui";
export { loadWorkspace, clearWorkspace } from "./workspace-lifecycle";

import { useSessionStore } from "./session";
import { usePrefsStore } from "./workspace";
import { clearWorkspace } from "./workspace-lifecycle";

/**
 * Only two stores keep anything in localStorage: the session, so a reload does
 * not bounce a signed-in person to the login screen, and preferences, because
 * appearance has to be right on the first paint. Everything else is fetched
 * from the backend once there is a session to fetch it with.
 */
const PERSISTED = [useSessionStore, usePrefsStore];

/**
 * Guards and shells need to know when localStorage has finished replaying, or
 * they will bounce a signed-in person to the login screen for a frame.
 */
export const useHydrationStore = create<{ hydrated: boolean; markHydrated: () => void }>()((set) => ({
  hydrated: false,
  markHydrated: () => set({ hydrated: true }),
}));

export async function rehydrateAll() {
  await Promise.all(PERSISTED.map((store) => store.persist.rehydrate()));
  // If a prior session claimed to be signed in, confirm the JWT still works.
  const session = useSessionStore.getState();
  if (session.isAuthenticated) {
    const ok = await session.restoreFromApi();
    if (!ok) {
      useSessionStore.setState({
        user: null,
        org: null,
        isAuthenticated: false,
        status: "idle",
        error: null,
      });
      clearWorkspace();
    }
  }
  useHydrationStore.getState().markHydrated();
}
