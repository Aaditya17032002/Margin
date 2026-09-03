import { create } from "zustand";
import { persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";

import {
  seedActivity,
  seedExports,
  seedIntegrations,
  seedKnowledge,
  seedNotifications,
  seedTeam,
  seedTemplates,
} from "@/data";
import { createId } from "@/lib/utils";
import { persistConfig } from "./persist";
import type {
  ActivityEntry,
  AppNotification,
  ExportRecord,
  Integration,
  IntegrationId,
  PastBid,
  Prefs,
  Role,
  TeamMember,
  Template,
} from "@/types";

/* ------------------------------------------------------------------ */
/* Notifications                                                        */
/* ------------------------------------------------------------------ */

interface NotificationsState {
  items: AppNotification[];
  push: (input: Omit<AppNotification, "id" | "at" | "read">) => string;
  markRead: (id: string, read?: boolean) => void;
  markAllRead: () => string[];
  restoreUnread: (ids: string[]) => void;
  remove: (id: string) => AppNotification | undefined;
  restore: (item: AppNotification) => void;
  clearAll: () => AppNotification[];
  resetToSeed: () => void;
}

export const useNotificationsStore = create<NotificationsState>()(
  persist(
    immer((set, get) => ({
      items: seedNotifications,

      push: (input) => {
        const id = createId("n");
        set((s) => {
          s.items.unshift({ ...input, id, at: new Date().toISOString(), read: false });
        });
        return id;
      },

      markRead: (id, read = true) =>
        set((s) => {
          const target = s.items.find((n) => n.id === id);
          if (target) target.read = read;
        }),

      markAllRead: () => {
        const changed = get().items.filter((n) => !n.read).map((n) => n.id);
        set((s) => {
          for (const n of s.items) n.read = true;
        });
        return changed;
      },

      restoreUnread: (ids) =>
        set((s) => {
          for (const n of s.items) if (ids.includes(n.id)) n.read = false;
        }),

      remove: (id) => {
        const existing = get().items.find((n) => n.id === id);
        set((s) => {
          s.items = s.items.filter((n) => n.id !== id);
        });
        return existing;
      },

      restore: (item) =>
        set((s) => {
          if (!s.items.some((n) => n.id === item.id)) s.items.unshift(item);
        }),

      clearAll: () => {
        const all = get().items;
        set((s) => {
          s.items = [];
        });
        return all;
      },

      resetToSeed: () =>
        set((s) => {
          s.items = structuredClone(seedNotifications);
        }),
    })),
    persistConfig<NotificationsState>("notifications", (s) => ({ items: s.items })),
  ),
);

export const selectUnreadCount = (state: NotificationsState) =>
  state.items.filter((n) => !n.read).length;

/* ------------------------------------------------------------------ */
/* Team                                                                 */
/* ------------------------------------------------------------------ */

interface TeamState {
  members: TeamMember[];
  invite: (input: { name: string; email: string; role: Role; title: string }) => string;
  updateMember: (id: string, patch: Partial<TeamMember>) => void;
  setRole: (id: string, role: Role) => Role | undefined;
  removeMember: (id: string) => TeamMember | undefined;
  restoreMember: (member: TeamMember) => void;
  resendInvite: (id: string) => void;
  resetToSeed: () => void;
}

const TONES = ["patina", "slate", "ochre", "leaf", "seal", "ink"];

export const useTeamStore = create<TeamState>()(
  persist(
    immer((set, get) => ({
      members: seedTeam,

      invite: ({ name, email, role, title }) => {
        const id = createId("u");
        set((s) => {
          s.members.push({
            id,
            name,
            email,
            role,
            title,
            status: "invited",
            lastActive: new Date().toISOString(),
            initialsColor: TONES[s.members.length % TONES.length],
          });
        });
        return id;
      },

      updateMember: (id, patch) =>
        set((s) => {
          const target = s.members.find((m) => m.id === id);
          if (target) Object.assign(target, patch);
        }),

      setRole: (id, role) => {
        const previous = get().members.find((m) => m.id === id)?.role;
        set((s) => {
          const target = s.members.find((m) => m.id === id);
          if (target) target.role = role;
        });
        return previous;
      },

      removeMember: (id) => {
        const existing = get().members.find((m) => m.id === id);
        set((s) => {
          s.members = s.members.filter((m) => m.id !== id);
        });
        return existing;
      },

      restoreMember: (member) =>
        set((s) => {
          if (!s.members.some((m) => m.id === member.id)) s.members.push(member);
        }),

      resendInvite: (id) =>
        set((s) => {
          const target = s.members.find((m) => m.id === id);
          if (target) target.lastActive = new Date().toISOString();
        }),

      resetToSeed: () =>
        set((s) => {
          s.members = structuredClone(seedTeam);
        }),
    })),
    persistConfig<TeamState>("team", (s) => ({ members: s.members })),
  ),
);

/* ------------------------------------------------------------------ */
/* Integrations                                                         */
/* ------------------------------------------------------------------ */

interface IntegrationsState {
  integrations: Integration[];
  connect: (id: IntegrationId, account?: string) => void;
  disconnect: (id: IntegrationId) => Integration | undefined;
  reconnect: (integration: Integration) => void;
  resetToSeed: () => void;
}

export const useIntegrationsStore = create<IntegrationsState>()(
  persist(
    immer((set, get) => ({
      integrations: seedIntegrations,

      connect: (id, account) =>
        set((s) => {
          const target = s.integrations.find((i) => i.id === id);
          if (!target) return;
          target.connected = true;
          target.connectedAt = new Date().toISOString();
          target.account = account ?? target.account ?? "a.osei@thornfield.co";
        }),

      disconnect: (id) => {
        const existing = get().integrations.find((i) => i.id === id);
        set((s) => {
          const target = s.integrations.find((i) => i.id === id);
          if (target) {
            target.connected = false;
            target.connectedAt = undefined;
          }
        });
        return existing ? structuredClone(existing) : undefined;
      },

      reconnect: (integration) =>
        set((s) => {
          const target = s.integrations.find((i) => i.id === integration.id);
          if (target) {
            target.connected = integration.connected;
            target.connectedAt = integration.connectedAt;
            target.account = integration.account;
          }
        }),

      resetToSeed: () =>
        set((s) => {
          s.integrations = structuredClone(seedIntegrations);
        }),
    })),
    persistConfig<IntegrationsState>("integrations", (s) => ({ integrations: s.integrations })),
  ),
);

/* ------------------------------------------------------------------ */
/* Templates                                                            */
/* ------------------------------------------------------------------ */

interface TemplatesState {
  templates: Template[];
  addTemplate: (input: Omit<Template, "id" | "updatedAt" | "usageCount">) => string;
  updateTemplate: (id: string, patch: Partial<Template>) => void;
  deleteTemplate: (id: string) => Template | undefined;
  restoreTemplate: (template: Template) => void;
  duplicateTemplate: (id: string) => string | undefined;
  recordUse: (id: string) => void;
  resetToSeed: () => void;
}

export const useTemplatesStore = create<TemplatesState>()(
  persist(
    immer((set, get) => ({
      templates: seedTemplates,

      addTemplate: (input) => {
        const id = createId("t");
        set((s) => {
          s.templates.unshift({ ...input, id, updatedAt: new Date().toISOString(), usageCount: 0 });
        });
        return id;
      },

      updateTemplate: (id, patch) =>
        set((s) => {
          const target = s.templates.find((t) => t.id === id);
          if (target) {
            Object.assign(target, patch);
            target.updatedAt = new Date().toISOString();
          }
        }),

      deleteTemplate: (id) => {
        const existing = get().templates.find((t) => t.id === id);
        set((s) => {
          s.templates = s.templates.filter((t) => t.id !== id);
        });
        return existing;
      },

      restoreTemplate: (template) =>
        set((s) => {
          if (!s.templates.some((t) => t.id === template.id)) s.templates.unshift(template);
        }),

      duplicateTemplate: (id) => {
        const source = get().templates.find((t) => t.id === id);
        if (!source) return undefined;
        const newId = createId("t");
        set((s) => {
          s.templates.unshift({
            ...structuredClone(source),
            id: newId,
            name: `${source.name} (copy)`,
            updatedAt: new Date().toISOString(),
            usageCount: 0,
          });
        });
        return newId;
      },

      recordUse: (id) =>
        set((s) => {
          const target = s.templates.find((t) => t.id === id);
          if (target) target.usageCount += 1;
        }),

      resetToSeed: () =>
        set((s) => {
          s.templates = structuredClone(seedTemplates);
        }),
    })),
    persistConfig<TemplatesState>("templates", (s) => ({ templates: s.templates })),
  ),
);

/* ------------------------------------------------------------------ */
/* Knowledge — institutional memory                                     */
/* ------------------------------------------------------------------ */

interface KnowledgeState {
  bids: PastBid[];
  addBid: (input: Omit<PastBid, "id">) => string;
  updateBid: (id: string, patch: Partial<PastBid>) => void;
  deleteBid: (id: string) => PastBid | undefined;
  restoreBid: (bid: PastBid) => void;
  resetToSeed: () => void;
}

export const useKnowledgeStore = create<KnowledgeState>()(
  persist(
    immer((set, get) => ({
      bids: seedKnowledge,

      addBid: (input) => {
        const id = createId("k");
        set((s) => {
          s.bids.unshift({ ...input, id });
        });
        return id;
      },

      updateBid: (id, patch) =>
        set((s) => {
          const target = s.bids.find((b) => b.id === id);
          if (target) Object.assign(target, patch);
        }),

      deleteBid: (id) => {
        const existing = get().bids.find((b) => b.id === id);
        set((s) => {
          s.bids = s.bids.filter((b) => b.id !== id);
        });
        return existing;
      },

      restoreBid: (bid) =>
        set((s) => {
          if (!s.bids.some((b) => b.id === bid.id)) s.bids.unshift(bid);
        }),

      resetToSeed: () =>
        set((s) => {
          s.bids = structuredClone(seedKnowledge);
        }),
    })),
    persistConfig<KnowledgeState>("knowledge", (s) => ({ bids: s.bids })),
  ),
);

/* ------------------------------------------------------------------ */
/* Reports & activity                                                   */
/* ------------------------------------------------------------------ */

interface ReportsState {
  exports: ExportRecord[];
  activity: ActivityEntry[];
  addExport: (input: Omit<ExportRecord, "id" | "at">) => string;
  updateExport: (id: string, patch: Partial<ExportRecord>) => void;
  deleteExport: (id: string) => ExportRecord | undefined;
  restoreExport: (record: ExportRecord) => void;
  log: (input: Omit<ActivityEntry, "id" | "at">) => void;
  resetToSeed: () => void;
}

export const useReportsStore = create<ReportsState>()(
  persist(
    immer((set, get) => ({
      exports: seedExports,
      activity: seedActivity,

      addExport: (input) => {
        const id = createId("x");
        set((s) => {
          s.exports.unshift({ ...input, id, at: new Date().toISOString() });
        });
        return id;
      },

      updateExport: (id, patch) =>
        set((s) => {
          const target = s.exports.find((x) => x.id === id);
          if (target) Object.assign(target, patch);
        }),

      deleteExport: (id) => {
        const existing = get().exports.find((x) => x.id === id);
        set((s) => {
          s.exports = s.exports.filter((x) => x.id !== id);
        });
        return existing;
      },

      restoreExport: (record) =>
        set((s) => {
          if (!s.exports.some((x) => x.id === record.id)) s.exports.unshift(record);
        }),

      log: (input) =>
        set((s) => {
          s.activity.unshift({ ...input, id: createId("a"), at: new Date().toISOString() });
          if (s.activity.length > 200) s.activity.length = 200;
        }),

      resetToSeed: () =>
        set((s) => {
          s.exports = structuredClone(seedExports);
          s.activity = structuredClone(seedActivity);
        }),
    })),
    persistConfig<ReportsState>("reports", (s) => ({ exports: s.exports, activity: s.activity })),
  ),
);

/* ------------------------------------------------------------------ */
/* Preferences                                                          */
/* ------------------------------------------------------------------ */

interface PrefsState extends Prefs {
  setAppearance: (appearance: Prefs["appearance"]) => void;
  setDensity: (density: Prefs["density"]) => void;
  setDefaultMode: (mode: Prefs["defaultMode"]) => void;
  toggleShortcuts: () => void;
  toggleReduceMotion: () => void;
  setRailPinned: (pinned: boolean) => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  dismissCoach: () => void;
  resetCoach: () => void;
  setNotify: (key: keyof Prefs["notify"], value: boolean) => void;
  resetToSeed: () => void;
}

const defaultPrefs: Prefs = {
  appearance: "paper",
  density: "comfortable",
  defaultMode: "standard",
  shortcutsEnabled: true,
  reduceMotion: false,
  marginRailPinned: false,
  sidebarCollapsed: false,
  coachDismissed: false,
  notify: {
    deadlines: true,
    lowConfidence: true,
    mentions: true,
    amendments: true,
    weeklyDigest: false,
  },
};

export const usePrefsStore = create<PrefsState>()(
  persist(
    immer((set) => ({
      ...defaultPrefs,

      setAppearance: (appearance) =>
        set((s) => {
          s.appearance = appearance;
        }),
      setDensity: (density) =>
        set((s) => {
          s.density = density;
        }),
      setDefaultMode: (mode) =>
        set((s) => {
          s.defaultMode = mode;
        }),
      toggleShortcuts: () =>
        set((s) => {
          s.shortcutsEnabled = !s.shortcutsEnabled;
        }),
      toggleReduceMotion: () =>
        set((s) => {
          s.reduceMotion = !s.reduceMotion;
        }),
      setRailPinned: (pinned) =>
        set((s) => {
          s.marginRailPinned = pinned;
        }),
      setSidebarCollapsed: (collapsed) =>
        set((s) => {
          s.sidebarCollapsed = collapsed;
        }),
      dismissCoach: () =>
        set((s) => {
          s.coachDismissed = true;
        }),
      resetCoach: () =>
        set((s) => {
          s.coachDismissed = false;
        }),
      setNotify: (key, value) =>
        set((s) => {
          s.notify[key] = value;
        }),
      resetToSeed: () => set(() => ({ ...defaultPrefs })),
    })),
    persistConfig<PrefsState>("prefs", (s) => ({
      appearance: s.appearance,
      density: s.density,
      defaultMode: s.defaultMode,
      shortcutsEnabled: s.shortcutsEnabled,
      reduceMotion: s.reduceMotion,
      marginRailPinned: s.marginRailPinned,
      sidebarCollapsed: s.sidebarCollapsed,
      coachDismissed: s.coachDismissed,
      notify: s.notify,
    })),
  ),
);
