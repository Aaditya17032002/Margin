import { useAnalysesStore } from "./analyses";
import { useMatrixStore } from "./matrix";
import { useQAStore } from "./qa";
import {
  useIntegrationsStore,
  useKnowledgeStore,
  useNotificationsStore,
  usePrefsStore,
  useReportsStore,
  useTeamStore,
  useTemplatesStore,
} from "./workspace";

/**
 * Loading and clearing live here rather than in the store barrel so the session
 * store can sign out cleanly without importing a module that imports it back.
 */

/** Org-wide collections, loaded once after sign-in. */
const WORKSPACE = [
  useAnalysesStore,
  useNotificationsStore,
  useTeamStore,
  useIntegrationsStore,
  useTemplatesStore,
  useKnowledgeStore,
  useReportsStore,
];

/** Everything holding server data, cleared on sign-out. */
const CLEARABLE = [...WORKSPACE, useMatrixStore, useQAStore];

/**
 * Fetch the org's collections. Safe to call repeatedly — each store no-ops once
 * it has loaded, unless asked to refresh.
 */
export async function loadWorkspace(options: { force?: boolean } = {}) {
  await Promise.all([
    ...WORKSPACE.map((store) => store.getState().load(options)),
    usePrefsStore.getState().load(),
  ]);
}

/** Drop every trace of the previous account from memory. */
export function clearWorkspace() {
  for (const store of CLEARABLE) store.getState().clear();
}
