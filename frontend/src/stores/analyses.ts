import { create } from "zustand";
import { persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";

import { seedAnalyses } from "@/data";
import { MODE_BY_ID } from "@/data/agents";
import { createId } from "@/lib/utils";
import { persistConfig } from "./persist";
import type { Analysis, AnalysisMode, Finding, GoNoGo, Stage } from "@/types";

interface AnalysesState {
  analyses: Analysis[];
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
  }) => string;
  updateAnalysis: (id: string, patch: Partial<Analysis>) => void;
  deleteAnalysis: (id: string) => Analysis | undefined;
  restoreAnalysis: (analysis: Analysis, index?: number) => void;
  duplicateAnalysis: (id: string) => string | undefined;
  setStage: (id: string, stage: Stage) => Stage | undefined;
  decide: (id: string, decision: GoNoGo, note?: string) => GoNoGo | undefined;
  toggleFindingVerified: (analysisId: string, findingId: string) => void;
  toggleFindingFlag: (analysisId: string, findingId: string) => void;
  updateFinding: (analysisId: string, findingId: string, patch: Partial<Finding>) => void;
  addTag: (id: string, tag: string) => void;
  removeTag: (id: string, tag: string) => void;
  resetToSeed: () => void;
}

const FINDING_KEYS = [
  "identity",
  "scope",
  "legal",
  "eligibility",
  "pricing",
  "postAward",
] as const;

function eachFinding(analysis: Analysis, fn: (finding: Finding) => void) {
  for (const key of FINDING_KEYS) {
    for (const finding of analysis[key]) fn(finding);
  }
}

export function allFindings(analysis: Analysis): Finding[] {
  return FINDING_KEYS.flatMap((key) => analysis[key]);
}

export const useAnalysesStore = create<AnalysesState>()(
  persist(
    immer((set, get) => ({
      analyses: seedAnalyses,

      createAnalysis: ({ title, agency, solicitationNumber, docType, mode, fileName, fileSize, source, owner }) => {
        const id = createId("an");
        const now = new Date().toISOString();
        const blank: Analysis = {
          id,
          title,
          solicitationNumber: solicitationNumber || "Pending assignment",
          agency,
          docType: docType ?? "RFP",
          mode,
          stage: "triage",
          goNoGo: "undecided",
          createdAt: now,
          updatedAt: now,
          owner,
          collaborators: [],
          naics: "Not yet determined",
          setAside: "Not yet determined",
          placeOfPerformance: "Not yet determined",
          estimatedValue: 0,
          pageCount: 0,
          fileName,
          fileSize,
          source,
          tags: [MODE_BY_ID[mode].name],
          summary: "",
          identity: [],
          scope: [],
          legal: [],
          eligibility: [],
          pricing: [],
          postAward: [],
          gates: [],
          evaluation: [],
          risks: [],
          silent: [],
          dates: [],
          clins: [],
          amendments: [],
          pages: [],
          versions: [],
        };
        set((s) => {
          s.analyses.unshift(blank);
        });
        return id;
      },

      updateAnalysis: (id, patch) =>
        set((s) => {
          const target = s.analyses.find((a) => a.id === id);
          if (!target) return;
          Object.assign(target, patch);
          target.updatedAt = new Date().toISOString();
        }),

      deleteAnalysis: (id) => {
        const existing = get().analyses.find((a) => a.id === id);
        set((s) => {
          s.analyses = s.analyses.filter((a) => a.id !== id);
        });
        return existing;
      },

      restoreAnalysis: (analysis, index) =>
        set((s) => {
          if (s.analyses.some((a) => a.id === analysis.id)) return;
          if (typeof index === "number" && index >= 0 && index <= s.analyses.length) {
            s.analyses.splice(index, 0, analysis);
          } else {
            s.analyses.unshift(analysis);
          }
        }),

      duplicateAnalysis: (id) => {
        const source = get().analyses.find((a) => a.id === id);
        if (!source) return undefined;
        const newId = createId("an");
        const now = new Date().toISOString();
        const copy: Analysis = {
          ...structuredClone(source),
          id: newId,
          title: `${source.title} (copy)`,
          stage: "triage",
          goNoGo: "undecided",
          decisionNote: undefined,
          createdAt: now,
          updatedAt: now,
        };
        set((s) => {
          const index = s.analyses.findIndex((a) => a.id === id);
          s.analyses.splice(index + 1, 0, copy);
        });
        return newId;
      },

      setStage: (id, stage) => {
        const previous = get().analyses.find((a) => a.id === id)?.stage;
        set((s) => {
          const target = s.analyses.find((a) => a.id === id);
          if (!target) return;
          target.stage = stage;
          target.updatedAt = new Date().toISOString();
        });
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
        return previous;
      },

      toggleFindingVerified: (analysisId, findingId) =>
        set((s) => {
          const target = s.analyses.find((a) => a.id === analysisId);
          if (!target) return;
          eachFinding(target, (f) => {
            if (f.id === findingId) f.verified = !f.verified;
          });
          target.updatedAt = new Date().toISOString();
        }),

      toggleFindingFlag: (analysisId, findingId) =>
        set((s) => {
          const target = s.analyses.find((a) => a.id === analysisId);
          if (!target) return;
          eachFinding(target, (f) => {
            if (f.id === findingId) f.flagged = !f.flagged;
          });
          target.updatedAt = new Date().toISOString();
        }),

      updateFinding: (analysisId, findingId, patch) =>
        set((s) => {
          const target = s.analyses.find((a) => a.id === analysisId);
          if (!target) return;
          eachFinding(target, (f) => {
            if (f.id === findingId) Object.assign(f, patch);
          });
          target.updatedAt = new Date().toISOString();
        }),

      addTag: (id, tag) =>
        set((s) => {
          const target = s.analyses.find((a) => a.id === id);
          if (!target || target.tags.includes(tag)) return;
          target.tags.push(tag);
        }),

      removeTag: (id, tag) =>
        set((s) => {
          const target = s.analyses.find((a) => a.id === id);
          if (!target) return;
          target.tags = target.tags.filter((t) => t !== tag);
        }),

      resetToSeed: () =>
        set((s) => {
          s.analyses = structuredClone(seedAnalyses);
        }),
    })),
    persistConfig<AnalysesState>("analyses", (s) => ({ analyses: s.analyses })),
  ),
);

export const selectAnalysis = (id: string) => (state: AnalysesState) =>
  state.analyses.find((a) => a.id === id);
