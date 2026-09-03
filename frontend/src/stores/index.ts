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

import { useAnalysesStore } from "./analyses";
import { useMatrixStore } from "./matrix";
import { useQAStore } from "./qa";
import { useSessionStore } from "./session";
import {
  useIntegrationsStore,
  useKnowledgeStore,
  useNotificationsStore,
  usePrefsStore,
  useReportsStore,
  useTeamStore,
  useTemplatesStore,
} from "./workspace";

const PERSISTED = [
  useSessionStore,
  useAnalysesStore,
  useMatrixStore,
  useQAStore,
  useNotificationsStore,
  useTeamStore,
  useIntegrationsStore,
  useTemplatesStore,
  useKnowledgeStore,
  useReportsStore,
  usePrefsStore,
];

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
    }
  }
  useHydrationStore.getState().markHydrated();
}

export function resetAllData() {
  useAnalysesStore.getState().resetToSeed();
  useMatrixStore.getState().resetToSeed();
  useQAStore.getState().resetToSeed();
  useNotificationsStore.getState().resetToSeed();
  useTeamStore.getState().resetToSeed();
  useIntegrationsStore.getState().resetToSeed();
  useTemplatesStore.getState().resetToSeed();
  useKnowledgeStore.getState().resetToSeed();
  useReportsStore.getState().resetToSeed();
}
