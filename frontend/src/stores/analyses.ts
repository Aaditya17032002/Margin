import { create } from "zustand";
import { immer } from "zustand/middleware/immer";

import { analysesApi, findingsApi, type FindingSection } from "@/lib/api";
import { errorMessage, fireAndForget, initialRemote, type RemoteSlice } from "./remote";
import type { Analysis, AnalysisMode, Finding, GoNoGo, Stage } from "@/types";

interface AnalysesState extends RemoteSlice {
  analyses: Analysis[];
  load: (options?: { force?: boolean }) => Promise<void>;
  refreshOne: (id: string) => Promise<Analysis | undefined>;
  createAnalysis: (input: {
    title: string;
    agency: string;
    solicitationNumber?: string;
    docType?: Analysis["docType"];
    mode: AnalysisMode;
    fileName: string;
    fileSize: number;
    source: Analysis["source"];
    owner: string;
  }) => Promise<string | undefined>;
  updateAnalysis: (id: string, patch: Partial<Analysis>) => void;
  deleteAnalysis: (id: string) => Analysis | undefined;
  restoreAnalysis: (analysis: Analysis, index?: number) => void;
  duplicateAnalysis: (id: string) => Promise<string | undefined>;
  setStage: (id: string, stage: Stage) => Stage | undefined;
  decide: (id: string, decision: GoNoGo, note?: string) => GoNoGo | undefined;
  toggleFindingVerified: (analysisId: string, findingId: string) => void;
  toggleFindingFlag: (analysisId: string, findingId: string) => void;
  updateFinding: (analysisId: string, findingId: string, patch: Partial<Finding>) => void;
  addTag: (id: string, tag: string) => void;
  removeTag: (id: string, tag: string) => void;
  clear: () => void;
}

const FINDING_KEYS = [
  "identity",
  "scope",
  "legal",
  "eligibility",
  "pricing",
  "postAward",
] as const satisfies readonly FindingSection[];

function eachFinding(analysis: Analysis, fn: (finding: Finding) => void) {
  for (const key of FINDING_KEYS) {
    for (const finding of analysis[key] ?? []) fn(finding);
  }
}

/** Tolerates a section the server omitted: a lighter payload should thin the
 *  board, never crash it. */
export function allFindings(analysis: Analysis): Finding[] {
  return FINDING_KEYS.flatMap((key) => analysis[key] ?? []);
}

/** Which array a finding lives in — the backend addresses findings by section. */
function sectionOf(analysis: Analysis, findingId: string): FindingSection | undefined {
  return FINDING_KEYS.find((key) => (analysis[key] ?? []).some((f) => f.id === findingId));
}

export const useAnalysesStore = create<AnalysesState>()(
  immer((set, get) => ({
    ...initialRemote,
    analyses: [],

    load: async ({ force = false } = {}) => {
      if (get().status === "loading") return;
      if (get().loaded && !force) return;
      set((s) => {
        s.status = "loading";
        s.error = null;
      });
      try {
        const analyses = await analysesApi.list();
        set((s) => {
          s.analyses = analyses;
          s.status = "ready";
          s.loaded = true;
        });
      } catch (error) {
        set((s) => {
          s.status = "error";
          s.error = errorMessage(error, "The analyses could not be loaded.");
        });
      }
    },

    refreshOne: async (id) => {
      try {
        const analysis = await analysesApi.get(id);
        set((s) => {
          const index = s.analyses.findIndex((a) => a.id === id);
          if (index === -1) s.analyses.unshift(analysis);
          else s.analyses[index] = analysis;
        });
        return analysis;
      } catch {
        return undefined;
      }
    },

    createAnalysis: async (input) => {
      try {
        const created = await analysesApi.create(input);
        set((s) => {
          s.analyses.unshift(created);
          s.loaded = true;
        });
        return created.id;
      } catch (error) {
        set((s) => {
          s.error = errorMessage(error, "The analysis could not be created.");
        });
        return undefined;
      }
    },

    updateAnalysis: (id, patch) => {
      set((s) => {
        const target = s.analyses.find((a) => a.id === id);
        if (!target) return;
        Object.assign(target, patch);
        target.updatedAt = new Date().toISOString();
      });
      fireAndForget(analysesApi.update(id, patch));
    },

    deleteAnalysis: (id) => {
      const existing = get().analyses.find((a) => a.id === id);
      set((s) => {
        s.analyses = s.analyses.filter((a) => a.id !== id);
      });
      if (existing) fireAndForget(analysesApi.remove(id), "The analysis could not be deleted.");
      return existing;
    },

    restoreAnalysis: (analysis, index) => {
      set((s) => {
        if (s.analyses.some((a) => a.id === analysis.id)) return;
        if (typeof index === "number" && index >= 0 && index <= s.analyses.length) {
          s.analyses.splice(index, 0, analysis);
        } else {
          s.analyses.unshift(analysis);
        }
      });
      // Deletes are soft on the server, so an undo brings back the same record
      // with the id its matrix rows and questions still reference.
      fireAndForget(
        analysesApi.restore(analysis.id),
        "The analysis was restored here but not on the server.",
      );
    },

    duplicateAnalysis: async (id) => {
      try {
        const copy = await analysesApi.duplicate(id);
        set((s) => {
          const index = s.analyses.findIndex((a) => a.id === id);
          s.analyses.splice(index === -1 ? 0 : index + 1, 0, copy);
        });
        return copy.id;
      } catch (error) {
        set((s) => {
          s.error = errorMessage(error, "The analysis could not be duplicated.");
        });
        return undefined;
      }
    },

    setStage: (id, stage) => {
      const previous = get().analyses.find((a) => a.id === id)?.stage;
      set((s) => {
        const target = s.analyses.find((a) => a.id === id);
        if (!target) return;
        target.stage = stage;
        target.updatedAt = new Date().toISOString();
      });
      if (previous) fireAndForget(analysesApi.update(id, { stage }));
      return previous;
    },

    decide: (id, decision, note) => {
      const previous = get().analyses.find((a) => a.id === id)?.goNoGo;
      set((s) => {
        const target = s.analyses.find((a) => a.id === id);
        if (!target) return;
        target.goNoGo = decision;
        target.decisionNote = note;
        target.stage = decision === "undecided" ? "review" : "decided";
        target.updatedAt = new Date().toISOString();
      });
      if (previous) {
        fireAndForget(
          analysesApi.decide(id, decision, note),
          "The decision could not be recorded.",
        );
      }
      return previous;
    },

    toggleFindingVerified: (analysisId, findingId) => {
      const analysis = get().analyses.find((a) => a.id === analysisId);
      const section = analysis ? sectionOf(analysis, findingId) : undefined;
      let verified = false;
      set((s) => {
        const target = s.analyses.find((a) => a.id === analysisId);
        if (!target) return;
        eachFinding(target, (f) => {
          if (f.id === findingId) {
            f.verified = !f.verified;
            verified = Boolean(f.verified);
          }
        });
        target.updatedAt = new Date().toISOString();
      });
      if (section) {
        fireAndForget(findingsApi.update(analysisId, section, findingId, { verified }));
      }
    },

    toggleFindingFlag: (analysisId, findingId) => {
      const analysis = get().analyses.find((a) => a.id === analysisId);
      const section = analysis ? sectionOf(analysis, findingId) : undefined;
      let flagged = false;
      set((s) => {
        const target = s.analyses.find((a) => a.id === analysisId);
        if (!target) return;
        eachFinding(target, (f) => {
          if (f.id === findingId) {
            f.flagged = !f.flagged;
            flagged = Boolean(f.flagged);
          }
        });
        target.updatedAt = new Date().toISOString();
      });
      if (section) {
        fireAndForget(findingsApi.update(analysisId, section, findingId, { flagged }));
      }
    },

    updateFinding: (analysisId, findingId, patch) => {
      const analysis = get().analyses.find((a) => a.id === analysisId);
      const section = analysis ? sectionOf(analysis, findingId) : undefined;
      set((s) => {
        const target = s.analyses.find((a) => a.id === analysisId);
        if (!target) return;
        eachFinding(target, (f) => {
          if (f.id === findingId) Object.assign(f, patch);
        });
        target.updatedAt = new Date().toISOString();
      });
      if (section) fireAndForget(findingsApi.update(analysisId, section, findingId, patch));
    },

    addTag: (id, tag) => {
      let tags: string[] | undefined;
      set((s) => {
        const target = s.analyses.find((a) => a.id === id);
        if (!target || target.tags.includes(tag)) return;
        target.tags.push(tag);
        tags = [...target.tags];
      });
      if (tags) fireAndForget(analysesApi.update(id, { tags }));
    },

    removeTag: (id, tag) => {
      let tags: string[] | undefined;
      set((s) => {
        const target = s.analyses.find((a) => a.id === id);
        if (!target) return;
        target.tags = target.tags.filter((t) => t !== tag);
        tags = [...target.tags];
      });
      if (tags) fireAndForget(analysesApi.update(id, { tags }));
    },

    clear: () =>
      set((s) => {
        s.analyses = [];
        s.status = "idle";
        s.error = null;
        s.loaded = false;
      }),
  })),
);

export const selectAnalysis = (id: string) => (state: AnalysesState) =>
  state.analyses.find((a) => a.id === id);
