import { create } from "zustand";
import { useShallow } from "zustand/react/shallow";
import { immer } from "zustand/middleware/immer";

import { matrixApi } from "@/lib/api";
import { errorMessage, fireAndForget, initialRemote, type RemoteSlice } from "./remote";
import type { MatrixRow, MatrixStatus } from "@/types";

interface MatrixState extends RemoteSlice {
  rows: MatrixRow[];
  /** Analyses whose rows have been fetched — the matrix loads per analysis. */
  loadedFor: string[];
  load: (analysisId: string, options?: { force?: boolean }) => Promise<void>;
  addRow: (row: Omit<MatrixRow, "id">) => Promise<string | undefined>;
  updateRow: (id: string, patch: Partial<MatrixRow>) => void;
  deleteRow: (id: string) => { row: MatrixRow; index: number } | undefined;
  restoreRow: (row: MatrixRow, index: number) => void;
  bulkAssign: (ids: string[], owner: string | null) => void;
  bulkStatus: (ids: string[], status: MatrixStatus) => void;
  bulkDelete: (ids: string[]) => MatrixRow[];
  restoreMany: (rows: MatrixRow[]) => void;
  clear: () => void;
}

/** Bulk actions can span analyses; group them so each request stays scoped. */
function byAnalysis(rows: MatrixRow[]): Map<string, string[]> {
  const groups = new Map<string, string[]>();
  for (const row of rows) {
    const ids = groups.get(row.analysisId) ?? [];
    ids.push(row.id);
    groups.set(row.analysisId, ids);
  }
  return groups;
}

export const useMatrixStore = create<MatrixState>()(
  immer((set, get) => ({
    ...initialRemote,
    rows: [],
    loadedFor: [],

    load: async (analysisId, { force = false } = {}) => {
      if (!force && get().loadedFor.includes(analysisId)) return;
      set((s) => {
        s.status = "loading";
        s.error = null;
      });
      try {
        const rows = await matrixApi.list(analysisId);
        set((s) => {
          s.rows = [...s.rows.filter((r) => r.analysisId !== analysisId), ...rows];
          if (!s.loadedFor.includes(analysisId)) s.loadedFor.push(analysisId);
          s.status = "ready";
          s.loaded = true;
        });
      } catch (error) {
        set((s) => {
          s.status = "error";
          s.error = errorMessage(error, "The compliance matrix could not be loaded.");
        });
      }
    },

    addRow: async ({ analysisId, ...row }) => {
      try {
        const created = await matrixApi.create(analysisId, row);
        set((s) => {
          s.rows.push(created);
        });
        return created.id;
      } catch (error) {
        set((s) => {
          s.error = errorMessage(error, "The row could not be added.");
        });
        return undefined;
      }
    },

    updateRow: (id, patch) => {
      const target = get().rows.find((r) => r.id === id);
      set((s) => {
        const row = s.rows.find((r) => r.id === id);
        if (row) Object.assign(row, patch);
      });
      if (target) fireAndForget(matrixApi.update(target.analysisId, id, patch));
    },

    deleteRow: (id) => {
      const index = get().rows.findIndex((r) => r.id === id);
      if (index === -1) return undefined;
      const row = get().rows[index];
      set((s) => {
        s.rows.splice(index, 1);
      });
      fireAndForget(matrixApi.remove(row.analysisId, id), "The row could not be deleted.");
      return { row, index };
    },

    restoreRow: (row, index) => {
      // The server has no undelete for a row, so an undo re-creates it. The id
      // it comes back with is the server's, and the local copy takes it.
      set((s) => {
        s.rows.splice(Math.min(index, s.rows.length), 0, row);
      });
      const { id: _id, analysisId, ...payload } = row;
      void matrixApi
        .create(analysisId, payload)
        .then((created) => {
          set((s) => {
            const local = s.rows.find((r) => r.id === row.id);
            if (local) local.id = created.id;
          });
        })
        .catch(() => {
          set((s) => {
            s.rows = s.rows.filter((r) => r.id !== row.id);
            s.error = "The row could not be restored.";
          });
        });
    },

    bulkAssign: (ids, owner) => {
      const affected = get().rows.filter((r) => ids.includes(r.id));
      set((s) => {
        for (const row of s.rows) {
          if (!ids.includes(row.id)) continue;
          row.owner = owner;
          if (owner && row.status === "unassigned") row.status = "assigned";
          if (!owner) row.status = "unassigned";
        }
      });
      for (const [analysisId, rowIds] of byAnalysis(affected)) {
        fireAndForget(matrixApi.bulk(analysisId, rowIds, { owner }));
      }
    },

    bulkStatus: (ids, status) => {
      const affected = get().rows.filter((r) => ids.includes(r.id));
      set((s) => {
        for (const row of s.rows) {
          if (ids.includes(row.id)) row.status = status;
        }
      });
      for (const [analysisId, rowIds] of byAnalysis(affected)) {
        fireAndForget(matrixApi.bulk(analysisId, rowIds, { status }));
      }
    },

    bulkDelete: (ids) => {
      const removed = get().rows.filter((r) => ids.includes(r.id));
      set((s) => {
        s.rows = s.rows.filter((r) => !ids.includes(r.id));
      });
      for (const row of removed) {
        fireAndForget(matrixApi.remove(row.analysisId, row.id), "A row could not be deleted.");
      }
      return removed;
    },

    restoreMany: (rows) => {
      set((s) => {
        const existing = new Set(s.rows.map((r) => r.id));
        for (const row of rows) if (!existing.has(row.id)) s.rows.push(row);
      });
      for (const row of rows) {
        const { id: _id, analysisId, ...payload } = row;
        void matrixApi
          .create(analysisId, payload)
          .then((created) => {
            set((s) => {
              const local = s.rows.find((r) => r.id === row.id);
              if (local) local.id = created.id;
            });
          })
          .catch(() => {
            set((s) => {
              s.rows = s.rows.filter((r) => r.id !== row.id);
            });
          });
      }
    },

    clear: () =>
      set((s) => {
        s.rows = [];
        s.loadedFor = [];
        s.status = "idle";
        s.error = null;
        s.loaded = false;
      }),
  })),
);

/**
 * Derived slices are subscribed through `useShallow`. A bare selector that
 * filters would hand `useSyncExternalStore` a fresh array on every read, which
 * it reads as a change and re-renders forever.
 */
export const useRowsFor = (analysisId: string) =>
  useMatrixStore(useShallow((s) => s.rows.filter((r) => r.analysisId === analysisId)));
