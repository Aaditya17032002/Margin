import { create } from "zustand";
import { persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";

import {
  activityApi,
  integrationsApi,
  knowledgeApi,
  notificationsApi,
  prefsApi,
  reportsApi,
  teamApi,
  templatesApi,
} from "@/lib/api";
import { persistConfig } from "./persist";
import { errorMessage, fireAndForget, initialRemote, type RemoteSlice } from "./remote";
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

interface NotificationsState extends RemoteSlice {
  items: AppNotification[];
  load: (options?: { force?: boolean }) => Promise<void>;
  receive: (item: AppNotification) => void;
  push: (input: Omit<AppNotification, "id" | "at" | "read">) => Promise<string | undefined>;
  markRead: (id: string, read?: boolean) => void;
  markAllRead: () => string[];
  restoreUnread: (ids: string[]) => void;
  remove: (id: string) => AppNotification | undefined;
  restore: (item: AppNotification) => void;
  clearAll: () => AppNotification[];
  clear: () => void;
}

export const useNotificationsStore = create<NotificationsState>()(
  immer((set, get) => ({
    ...initialRemote,
    items: [],

    load: async ({ force = false } = {}) => {
      if (get().loaded && !force) return;
      set((s) => {
        s.status = "loading";
        s.error = null;
      });
      try {
        const items = await notificationsApi.list();
        set((s) => {
          s.items = items;
          s.status = "ready";
          s.loaded = true;
        });
      } catch (error) {
        set((s) => {
          s.status = "error";
          s.error = errorMessage(error, "Notifications could not be loaded.");
        });
      }
    },

    /** A notification that arrived on the live stream rather than a fetch. */
    receive: (item) =>
      set((s) => {
        if (s.items.some((n) => n.id === item.id)) return;
        s.items.unshift(item);
      }),

    push: async (input) => {
      try {
        const created = await notificationsApi.create(input);
        set((s) => {
          if (!s.items.some((n) => n.id === created.id)) s.items.unshift(created);
        });
        return created.id;
      } catch (error) {
        set((s) => {
          s.error = errorMessage(error, "The notification could not be raised.");
        });
        return undefined;
      }
    },

    markRead: (id, read = true) => {
      set((s) => {
        const target = s.items.find((n) => n.id === id);
        if (target) target.read = read;
      });
      fireAndForget(notificationsApi.markRead(id, read));
    },

    markAllRead: () => {
      const changed = get()
        .items.filter((n) => !n.read)
        .map((n) => n.id);
      set((s) => {
        for (const n of s.items) n.read = true;
      });
      if (changed.length) fireAndForget(notificationsApi.markAllRead());
      return changed;
    },

    restoreUnread: (ids) => {
      set((s) => {
        for (const n of s.items) if (ids.includes(n.id)) n.read = false;
      });
      for (const id of ids) fireAndForget(notificationsApi.markRead(id, false));
    },

    remove: (id) => {
      const existing = get().items.find((n) => n.id === id);
      set((s) => {
        s.items = s.items.filter((n) => n.id !== id);
      });
      if (existing) fireAndForget(notificationsApi.remove(id));
      return existing;
    },

    restore: (item) => {
      set((s) => {
        if (!s.items.some((n) => n.id === item.id)) s.items.unshift(item);
      });
      const { id: _id, at: _at, read: _read, ...payload } = item;
      void notificationsApi
        .create(payload)
        .then((created) => {
          set((s) => {
            const local = s.items.find((n) => n.id === item.id);
            if (local) local.id = created.id;
          });
        })
        .catch(() => {
          set((s) => {
            s.items = s.items.filter((n) => n.id !== item.id);
          });
        });
    },

    clearAll: () => {
      const all = get().items;
      set((s) => {
        s.items = [];
      });
      if (all.length) fireAndForget(notificationsApi.clearAll());
      return all;
    },

    clear: () =>
      set((s) => {
        s.items = [];
        s.status = "idle";
        s.error = null;
        s.loaded = false;
      }),
  })),
);

export const selectUnreadCount = (state: NotificationsState) =>
  state.items.filter((n) => !n.read).length;

/* ------------------------------------------------------------------ */
/* Team                                                                 */
/* ------------------------------------------------------------------ */

interface TeamState extends RemoteSlice {
  members: TeamMember[];
  load: (options?: { force?: boolean }) => Promise<void>;
  invite: (input: {
    name: string;
    email: string;
    role: Role;
    title: string;
  }) => Promise<string | undefined>;
  updateMember: (id: string, patch: Partial<TeamMember>) => void;
  setRole: (id: string, role: Role) => Role | undefined;
  removeMember: (id: string) => TeamMember | undefined;
  restoreMember: (member: TeamMember) => void;
  resendInvite: (id: string) => void;
  clear: () => void;
}

export const useTeamStore = create<TeamState>()(
  immer((set, get) => ({
    ...initialRemote,
    members: [],

    load: async ({ force = false } = {}) => {
      if (get().loaded && !force) return;
      set((s) => {
        s.status = "loading";
        s.error = null;
      });
      try {
        const members = await teamApi.list();
        set((s) => {
          s.members = members;
          s.status = "ready";
          s.loaded = true;
        });
      } catch (error) {
        set((s) => {
          s.status = "error";
          s.error = errorMessage(error, "The team could not be loaded.");
        });
      }
    },

    invite: async (input) => {
      try {
        const member = await teamApi.invite(input);
        set((s) => {
          s.members.push(member);
        });
        return member.id;
      } catch (error) {
        set((s) => {
          s.error = errorMessage(error, "The invitation could not be sent.");
        });
        return undefined;
      }
    },

    updateMember: (id, patch) => {
      set((s) => {
        const target = s.members.find((m) => m.id === id);
        if (target) Object.assign(target, patch);
      });
      const { role, title, status } = patch;
      fireAndForget(teamApi.update(id, { role, title, status }));
    },

    setRole: (id, role) => {
      const previous = get().members.find((m) => m.id === id)?.role;
      set((s) => {
        const target = s.members.find((m) => m.id === id);
        if (target) target.role = role;
      });
      if (previous) fireAndForget(teamApi.update(id, { role }));
      return previous;
    },

    removeMember: (id) => {
      const existing = get().members.find((m) => m.id === id);
      set((s) => {
        s.members = s.members.filter((m) => m.id !== id);
      });
      if (existing) fireAndForget(teamApi.remove(id), "That person could not be removed.");
      return existing;
    },

    restoreMember: (member) => {
      set((s) => {
        if (!s.members.some((m) => m.id === member.id)) s.members.push(member);
      });
      void teamApi
        .invite({ name: member.name, email: member.email, role: member.role, title: member.title })
        .then((created) => {
          set((s) => {
            const local = s.members.find((m) => m.id === member.id);
            if (local) local.id = created.id;
          });
        })
        .catch(() => {
          set((s) => {
            s.members = s.members.filter((m) => m.id !== member.id);
          });
        });
    },

    resendInvite: (id) =>
      set((s) => {
        const target = s.members.find((m) => m.id === id);
        if (target) target.lastActive = new Date().toISOString();
      }),

    clear: () =>
      set((s) => {
        s.members = [];
        s.status = "idle";
        s.error = null;
        s.loaded = false;
      }),
  })),
);

/* ------------------------------------------------------------------ */
/* Integrations                                                         */
/* ------------------------------------------------------------------ */

interface IntegrationsState extends RemoteSlice {
  integrations: Integration[];
  load: (options?: { force?: boolean }) => Promise<void>;
  connect: (id: IntegrationId, account?: string) => void;
  disconnect: (id: IntegrationId) => Integration | undefined;
  reconnect: (integration: Integration) => void;
  clear: () => void;
}

export const useIntegrationsStore = create<IntegrationsState>()(
  immer((set, get) => ({
    ...initialRemote,
    integrations: [],

    load: async ({ force = false } = {}) => {
      if (get().loaded && !force) return;
      set((s) => {
        s.status = "loading";
        s.error = null;
      });
      try {
        const integrations = await integrationsApi.list();
        set((s) => {
          s.integrations = integrations;
          s.status = "ready";
          s.loaded = true;
        });
      } catch (error) {
        set((s) => {
          s.status = "error";
          s.error = errorMessage(error, "The integrations could not be loaded.");
        });
      }
    },

    connect: (id, account) => {
      set((s) => {
        const target = s.integrations.find((i) => i.id === id);
        if (!target) return;
        target.connected = true;
        target.connectedAt = new Date().toISOString();
        if (account) target.account = account;
      });
      void integrationsApi
        .connect(id, account)
        .then((updated) => {
          set((s) => {
            const index = s.integrations.findIndex((i) => i.id === id);
            if (index !== -1) s.integrations[index] = updated;
          });
        })
        .catch((error: unknown) => {
          set((s) => {
            const target = s.integrations.find((i) => i.id === id);
            if (target) {
              target.connected = false;
              target.connectedAt = undefined;
            }
            s.error = errorMessage(error, "That source could not be connected.");
          });
        });
    },

    disconnect: (id) => {
      const existing = get().integrations.find((i) => i.id === id);
      set((s) => {
        const target = s.integrations.find((i) => i.id === id);
        if (target) {
          target.connected = false;
          target.connectedAt = undefined;
        }
      });
      if (existing) fireAndForget(integrationsApi.disconnect(id));
      return existing ? structuredClone(existing) : undefined;
    },

    reconnect: (integration) => {
      set((s) => {
        const target = s.integrations.find((i) => i.id === integration.id);
        if (target) {
          target.connected = integration.connected;
          target.connectedAt = integration.connectedAt;
          target.account = integration.account;
        }
      });
      if (integration.connected) {
        fireAndForget(integrationsApi.connect(integration.id, integration.account));
      }
    },

    clear: () =>
      set((s) => {
        s.integrations = [];
        s.status = "idle";
        s.error = null;
        s.loaded = false;
      }),
  })),
);

/* ------------------------------------------------------------------ */
/* Templates                                                            */
/* ------------------------------------------------------------------ */

interface TemplatesState extends RemoteSlice {
  templates: Template[];
  load: (options?: { force?: boolean }) => Promise<void>;
  addTemplate: (
    input: Omit<Template, "id" | "updatedAt" | "usageCount">,
  ) => Promise<string | undefined>;
  updateTemplate: (id: string, patch: Partial<Template>) => void;
  deleteTemplate: (id: string) => Template | undefined;
  restoreTemplate: (template: Template) => void;
  duplicateTemplate: (id: string) => Promise<string | undefined>;
  recordUse: (id: string) => void;
  clear: () => void;
}

export const useTemplatesStore = create<TemplatesState>()(
  immer((set, get) => ({
    ...initialRemote,
    templates: [],

    load: async ({ force = false } = {}) => {
      if (get().loaded && !force) return;
      set((s) => {
        s.status = "loading";
        s.error = null;
      });
      try {
        const templates = await templatesApi.list();
        set((s) => {
          s.templates = templates;
          s.status = "ready";
          s.loaded = true;
        });
      } catch (error) {
        set((s) => {
          s.status = "error";
          s.error = errorMessage(error, "The templates could not be loaded.");
        });
      }
    },

    addTemplate: async (input) => {
      try {
        const created = await templatesApi.create(input);
        set((s) => {
          s.templates.unshift(created);
        });
        return created.id;
      } catch (error) {
        set((s) => {
          s.error = errorMessage(error, "The template could not be created.");
        });
        return undefined;
      }
    },

    updateTemplate: (id, patch) => {
      set((s) => {
        const target = s.templates.find((t) => t.id === id);
        if (target) {
          Object.assign(target, patch);
          target.updatedAt = new Date().toISOString();
        }
      });
      const { name, description, sections } = patch;
      fireAndForget(templatesApi.update(id, { name, description, sections }));
    },

    deleteTemplate: (id) => {
      const existing = get().templates.find((t) => t.id === id);
      set((s) => {
        s.templates = s.templates.filter((t) => t.id !== id);
      });
      if (existing) fireAndForget(templatesApi.remove(id));
      return existing;
    },

    restoreTemplate: (template) => {
      set((s) => {
        if (!s.templates.some((t) => t.id === template.id)) s.templates.unshift(template);
      });
      const { id: _id, updatedAt: _updatedAt, usageCount: _usageCount, ...payload } = template;
      void templatesApi
        .create(payload)
        .then((created) => {
          set((s) => {
            const local = s.templates.find((t) => t.id === template.id);
            if (local) local.id = created.id;
          });
        })
        .catch(() => {
          set((s) => {
            s.templates = s.templates.filter((t) => t.id !== template.id);
          });
        });
    },

    duplicateTemplate: async (id) => {
      const source = get().templates.find((t) => t.id === id);
      if (!source) return undefined;
      try {
        const created = await templatesApi.create({
          name: `${source.name} (copy)`,
          kind: source.kind,
          description: source.description,
          sections: [...source.sections],
          format: source.format,
        });
        set((s) => {
          s.templates.unshift(created);
        });
        return created.id;
      } catch (error) {
        set((s) => {
          s.error = errorMessage(error, "The template could not be duplicated.");
        });
        return undefined;
      }
    },

    // Usage is a local reading aid; the count the server keeps is authoritative
    // and comes back on the next load.
    recordUse: (id) =>
      set((s) => {
        const target = s.templates.find((t) => t.id === id);
        if (target) target.usageCount += 1;
      }),

    clear: () =>
      set((s) => {
        s.templates = [];
        s.status = "idle";
        s.error = null;
        s.loaded = false;
      }),
  })),
);

/* ------------------------------------------------------------------ */
/* Knowledge — institutional memory                                     */
/* ------------------------------------------------------------------ */

interface KnowledgeState extends RemoteSlice {
  bids: PastBid[];
  load: (options?: { force?: boolean }) => Promise<void>;
  addBid: (input: Omit<PastBid, "id">) => Promise<string | undefined>;
  updateBid: (id: string, patch: Partial<PastBid>) => void;
  deleteBid: (id: string) => PastBid | undefined;
  restoreBid: (bid: PastBid) => void;
  clear: () => void;
}

export const useKnowledgeStore = create<KnowledgeState>()(
  immer((set, get) => ({
    ...initialRemote,
    bids: [],

    load: async ({ force = false } = {}) => {
      if (get().loaded && !force) return;
      set((s) => {
        s.status = "loading";
        s.error = null;
      });
      try {
        const bids = await knowledgeApi.list();
        set((s) => {
          s.bids = bids;
          s.status = "ready";
          s.loaded = true;
        });
      } catch (error) {
        set((s) => {
          s.status = "error";
          s.error = errorMessage(error, "The knowledge base could not be loaded.");
        });
      }
    },

    addBid: async (input) => {
      try {
        const created = await knowledgeApi.create(input);
        set((s) => {
          s.bids.unshift(created);
        });
        return created.id;
      } catch (error) {
        set((s) => {
          s.error = errorMessage(error, "That bid could not be recorded.");
        });
        return undefined;
      }
    },

    updateBid: (id, patch) => {
      set((s) => {
        const target = s.bids.find((b) => b.id === id);
        if (target) Object.assign(target, patch);
      });
      const { title, outcome, debrief, lessons } = patch;
      fireAndForget(knowledgeApi.update(id, { title, outcome, debrief, lessons }));
    },

    deleteBid: (id) => {
      const existing = get().bids.find((b) => b.id === id);
      set((s) => {
        s.bids = s.bids.filter((b) => b.id !== id);
      });
      if (existing) fireAndForget(knowledgeApi.remove(id));
      return existing;
    },

    restoreBid: (bid) => {
      set((s) => {
        if (!s.bids.some((b) => b.id === bid.id)) s.bids.unshift(bid);
      });
      const { id: _id, ...payload } = bid;
      void knowledgeApi
        .create(payload)
        .then((created) => {
          set((s) => {
            const local = s.bids.find((b) => b.id === bid.id);
            if (local) local.id = created.id;
          });
        })
        .catch(() => {
          set((s) => {
            s.bids = s.bids.filter((b) => b.id !== bid.id);
          });
        });
    },

    clear: () =>
      set((s) => {
        s.bids = [];
        s.status = "idle";
        s.error = null;
        s.loaded = false;
      }),
  })),
);

/* ------------------------------------------------------------------ */
/* Reports & activity                                                   */
/* ------------------------------------------------------------------ */

interface ReportsState extends RemoteSlice {
  exports: ExportRecord[];
  activity: ActivityEntry[];
  load: (options?: { force?: boolean }) => Promise<void>;
  generate: (
    analysisId: string,
    input: {
      templateName: string;
      format: ExportRecord["format"];
      destination: ExportRecord["destination"];
    },
  ) => Promise<string | undefined>;
  updateExport: (id: string, patch: Partial<ExportRecord>) => void;
  deleteExport: (id: string) => ExportRecord | undefined;
  restoreExport: (record: ExportRecord) => void;
  log: (input: Omit<ActivityEntry, "id" | "at">) => void;
  clear: () => void;
}

export const useReportsStore = create<ReportsState>()(
  immer((set, get) => ({
    ...initialRemote,
    exports: [],
    activity: [],

    load: async ({ force = false } = {}) => {
      if (get().loaded && !force) return;
      set((s) => {
        s.status = "loading";
        s.error = null;
      });
      try {
        const [exports, activity] = await Promise.all([reportsApi.list(), activityApi.list()]);
        set((s) => {
          s.exports = exports;
          s.activity = activity;
          s.status = "ready";
          s.loaded = true;
        });
      } catch (error) {
        set((s) => {
          s.status = "error";
          s.error = errorMessage(error, "The export history could not be loaded.");
        });
      }
    },

    generate: async (analysisId, input) => {
      try {
        const record = await reportsApi.generate(analysisId, input);
        set((s) => {
          s.exports.unshift(record);
        });
        return record.id;
      } catch (error) {
        set((s) => {
          s.error = errorMessage(error, "The report could not be generated.");
        });
        return undefined;
      }
    },

    // Export status is owned by the worker; local edits are display-only and a
    // reload replaces them with what actually happened.
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

    log: (input) => {
      const optimisticId = `pending_${Date.now()}`;
      set((s) => {
        s.activity.unshift({ ...input, id: optimisticId, at: new Date().toISOString() });
        if (s.activity.length > 200) s.activity.length = 200;
      });
      void activityApi
        .log(input)
        .then((entry) => {
          set((s) => {
            const local = s.activity.find((a) => a.id === optimisticId);
            if (local) {
              local.id = entry.id;
              local.at = entry.at;
            }
          });
        })
        .catch(() => {
          set((s) => {
            s.activity = s.activity.filter((a) => a.id !== optimisticId);
          });
        });
    },

    clear: () =>
      set((s) => {
        s.exports = [];
        s.activity = [];
        s.status = "idle";
        s.error = null;
        s.loaded = false;
      }),
  })),
);

/* ------------------------------------------------------------------ */
/* Preferences                                                          */
/* ------------------------------------------------------------------ */

interface PrefsState extends Prefs {
  load: () => Promise<void>;
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
  resetToDefaults: () => void;
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

/**
 * Preferences are the one collection kept in localStorage as well as on the
 * server: appearance has to be applied on the first paint, long before an
 * authenticated request could come back.
 */
export const usePrefsStore = create<PrefsState>()(
  persist(
    immer((set) => {
      const sync = (patch: Partial<Prefs>) => fireAndForget(prefsApi.update(patch));

      return {
        ...defaultPrefs,

        load: async () => {
          try {
            const prefs = await prefsApi.get();
            set((s) => {
              Object.assign(s, prefs);
            });
          } catch {
            // Preferences are not worth interrupting a sign-in for; the local
            // copy stands until the next successful read.
          }
        },

        setAppearance: (appearance) => {
          set((s) => {
            s.appearance = appearance;
          });
          sync({ appearance });
        },
        setDensity: (density) => {
          set((s) => {
            s.density = density;
          });
          sync({ density });
        },
        setDefaultMode: (defaultMode) => {
          set((s) => {
            s.defaultMode = defaultMode;
          });
          sync({ defaultMode });
        },
        toggleShortcuts: () => {
          let shortcutsEnabled = false;
          set((s) => {
            s.shortcutsEnabled = !s.shortcutsEnabled;
            shortcutsEnabled = s.shortcutsEnabled;
          });
          sync({ shortcutsEnabled });
        },
        toggleReduceMotion: () => {
          let reduceMotion = false;
          set((s) => {
            s.reduceMotion = !s.reduceMotion;
            reduceMotion = s.reduceMotion;
          });
          sync({ reduceMotion });
        },
        setRailPinned: (marginRailPinned) => {
          set((s) => {
            s.marginRailPinned = marginRailPinned;
          });
          sync({ marginRailPinned });
        },
        setSidebarCollapsed: (sidebarCollapsed) => {
          set((s) => {
            s.sidebarCollapsed = sidebarCollapsed;
          });
          sync({ sidebarCollapsed });
        },
        dismissCoach: () => {
          set((s) => {
            s.coachDismissed = true;
          });
          sync({ coachDismissed: true });
        },
        resetCoach: () => {
          set((s) => {
            s.coachDismissed = false;
          });
          sync({ coachDismissed: false });
        },
        setNotify: (key, value) => {
          let notify = defaultPrefs.notify;
          set((s) => {
            s.notify[key] = value;
            notify = { ...s.notify };
          });
          sync({ notify });
        },
        resetToDefaults: () => {
          set(() => ({ ...defaultPrefs }));
          sync(defaultPrefs);
        },
      };
    }),
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
