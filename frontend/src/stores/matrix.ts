import { create } from "zustand";
import { useShallow } from "zustand/react/shallow";
import { persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";

import { seedMatrix } from "@/data";
import { createId } from "@/lib/utils";
import { persistConfig } from "./persist";
import type { MatrixRow, MatrixStatus } from "@/types";

interface MatrixState {
  rows: MatrixRow[];
  addRow: (row: Omit<MatrixRow, "id">) => string;
  updateRow: (id: string, patch: Partial<MatrixRow>) => void;
  deleteRow: (id: string) => { row: MatrixRow; index: number } | undefined;
  restoreRow: (row: MatrixRow, index: number) => void;
  bulkAssign: (ids: string[], owner: string | null) => void;
  bulkStatus: (ids: string[], status: MatrixStatus) => void;
  bulkDelete: (ids: string[]) => MatrixRow[];
  restoreMany: (rows: MatrixRow[]) => void;
  resetToSeed: () => void;
}

export const useMatrixStore = create<MatrixState>()(
  persist(
    immer((set, get) => ({
      rows: seedMatrix,

      addRow: (row) => {
        const id = createId("m");
        set((s) => {
          s.rows.push({ ...row, id });
        });
        return id;
      },

      updateRow: (id, patch) =>
        set((s) => {
          const target = s.rows.find((r) => r.id === id);
          if (target) Object.assign(target, patch);
        }),

      deleteRow: (id) => {
        const index = get().rows.findIndex((r) => r.id === id);
        if (index === -1) return undefined;
        const row = get().rows[index];
        set((s) => {
          s.rows.splice(index, 1);
        });
        return { row, index };
      },

      restoreRow: (row, index) =>
        set((s) => {
          s.rows.splice(Math.min(index, s.rows.length), 0, row);
        }),

      bulkAssign: (ids, owner) =>
        set((s) => {
          for (const row of s.rows) {
            if (ids.includes(row.id)) {
              row.owner = owner;
              if (owner && row.status === "unassigned") row.status = "assigned";
              if (!owner) row.status = "unassigned";
            }
          }
        }),

      bulkStatus: (ids, status) =>
        set((s) => {
          for (const row of s.rows) {
            if (ids.includes(row.id)) row.status = status;
          }
        }),

      bulkDelete: (ids) => {
        const removed = get().rows.filter((r) => ids.includes(r.id));
        set((s) => {
          s.rows = s.rows.filter((r) => !ids.includes(r.id));
        });
        return removed;
      },

      restoreMany: (rows) =>
        set((s) => {
          const existing = new Set(s.rows.map((r) => r.id));
          for (const row of rows) if (!existing.has(row.id)) s.rows.push(row);
        }),

      resetToSeed: () =>
        set((s) => {
          s.rows = structuredClone(seedMatrix);
        }),
    })),
    persistConfig<MatrixState>("matrix", (s) => ({ rows: s.rows })),
  ),
);

/**
 * Derived slices are subscribed through `useShallow`. A bare selector that
 * filters would hand `useSyncExternalStore` a fresh array on every read, which
 * it reads as a change and re-renders forever.
 */
export const useRowsFor = (analysisId: string) =>
  useMatrixStore(useShallow((s) => s.rows.filter((r) => r.analysisId === analysisId)));
