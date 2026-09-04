import { create } from "zustand";
import { useShallow } from "zustand/react/shallow";
import { immer } from "zustand/middleware/immer";

import { questionsApi } from "@/lib/api";
import { errorMessage, fireAndForget, initialRemote, type RemoteSlice } from "./remote";
import type { QAQuestion } from "@/types";

interface QAState extends RemoteSlice {
  questions: QAQuestion[];
  /** Analyses whose question set has been fetched. */
  loadedFor: string[];
  load: (analysisId: string, options?: { force?: boolean }) => Promise<void>;
  addQuestion: (
    input: Omit<QAQuestion, "id" | "order" | "sent">,
  ) => Promise<string | undefined>;
  updateQuestion: (id: string, patch: Partial<QAQuestion>) => void;
  deleteQuestion: (id: string) => QAQuestion | undefined;
  restoreQuestion: (question: QAQuestion) => void;
  toggleImpact: (id: string) => void;
  reorder: (analysisId: string, orderedIds: string[]) => void;
  markSent: (analysisId: string, ids?: string[]) => void;
  /**
   * Record what the agency said back.
   *
   * Returns the requirements whose answers this reopened — a section written
   * before a clarification is not an answer to the clarified clause, and the
   * caller has to be able to say so.
   */
  recordAnswer: (
    id: string,
    input: {
      answer: string;
      source: string;
      effect: "clarified" | "amended" | "withdrawn";
      revisedRequirement?: string;
    },
  ) => Promise<{ reopened: string[]; superseded: string | null; withdrawn: string | null }>;
  clear: () => void;
}

export const useQAStore = create<QAState>()(
  immer((set, get) => ({
    ...initialRemote,
    questions: [],
    loadedFor: [],

    load: async (analysisId, { force = false } = {}) => {
      if (!force && get().loadedFor.includes(analysisId)) return;
      set((s) => {
        s.status = "loading";
        s.error = null;
      });
      try {
        const questions = await questionsApi.list(analysisId);
        set((s) => {
          s.questions = [
            ...s.questions.filter((q) => q.analysisId !== analysisId),
            ...questions,
          ];
          if (!s.loadedFor.includes(analysisId)) s.loadedFor.push(analysisId);
          s.status = "ready";
          s.loaded = true;
        });
      } catch (error) {
        set((s) => {
          s.status = "error";
          s.error = errorMessage(error, "The question set could not be loaded.");
        });
      }
    },

    addQuestion: async ({ analysisId, ...input }) => {
      try {
        const created = await questionsApi.create(analysisId, input);
        set((s) => {
          s.questions.push(created);
        });
        return created.id;
      } catch (error) {
        set((s) => {
          s.error = errorMessage(error, "The question could not be added.");
        });
        return undefined;
      }
    },

    updateQuestion: (id, patch) => {
      const target = get().questions.find((q) => q.id === id);
      set((s) => {
        const question = s.questions.find((q) => q.id === id);
        if (question) Object.assign(question, patch);
      });
      if (target) fireAndForget(questionsApi.update(target.analysisId, id, patch));
    },

    deleteQuestion: (id) => {
      const existing = get().questions.find((q) => q.id === id);
      set((s) => {
        s.questions = s.questions.filter((q) => q.id !== id);
      });
      if (existing) {
        fireAndForget(
          questionsApi.remove(existing.analysisId, id),
          "The question could not be deleted.",
        );
      }
      return existing;
    },

    restoreQuestion: (question) => {
      set((s) => {
        if (!s.questions.some((q) => q.id === question.id)) s.questions.push(question);
      });
      const { id: _id, analysisId, order: _order, sent: _sent, ...payload } = question;
      void questionsApi
        .create(analysisId, payload)
        .then((created) => {
          set((s) => {
            const local = s.questions.find((q) => q.id === question.id);
            if (local) local.id = created.id;
          });
        })
        .catch(() => {
          set((s) => {
            s.questions = s.questions.filter((q) => q.id !== question.id);
            s.error = "The question could not be restored.";
          });
        });
    },

    toggleImpact: (id) => {
      const target = get().questions.find((q) => q.id === id);
      if (!target) return;
      const goNoGoImpact = !target.goNoGoImpact;
      set((s) => {
        const question = s.questions.find((q) => q.id === id);
        if (question) question.goNoGoImpact = goNoGoImpact;
      });
      fireAndForget(questionsApi.update(target.analysisId, id, { goNoGoImpact }));
    },

    reorder: (analysisId, orderedIds) => {
      set((s) => {
        orderedIds.forEach((id, index) => {
          const target = s.questions.find((q) => q.id === id && q.analysisId === analysisId);
          if (target) target.order = index;
        });
      });
      fireAndForget(questionsApi.reorder(analysisId, orderedIds));
    },

    recordAnswer: async (id, input) => {
      const empty = { reopened: [], superseded: null, withdrawn: null };
      const target = get().questions.find((q) => q.id === id);
      if (!target) return empty;
      try {
        const updated = await questionsApi.answer(target.analysisId, id, input);
        set((s) => {
          const local = s.questions.find((q) => q.id === id);
          if (local) Object.assign(local, updated);
        });
        return {
          reopened: updated.reopened ?? [],
          superseded: updated.superseded ?? null,
          withdrawn: updated.withdrawn ?? null,
        };
      } catch (error) {
        set((s) => {
          s.error = errorMessage(error, "The answer could not be recorded.");
        });
        return empty;
      }
    },

    markSent: (analysisId, ids) => {
      const affected = get().questions.filter(
        (q) => q.analysisId === analysisId && !q.sent && (!ids || ids.includes(q.id)),
      );
      set((s) => {
        for (const q of s.questions) {
          if (q.analysisId !== analysisId) continue;
          if (ids && !ids.includes(q.id)) continue;
          q.sent = true;
        }
      });
      for (const question of affected) {
        fireAndForget(questionsApi.update(analysisId, question.id, { sent: true }));
      }
    },

    clear: () =>
      set((s) => {
        s.questions = [];
        s.loadedFor = [];
        s.status = "idle";
        s.error = null;
        s.loaded = false;
      }),
  })),
);

/**
 * Impact-first, then author order — the ordering the Q&A builder promises.
 * Shallow comparison keeps the fresh array from looking like a change.
 */
export const useQuestionsFor = (analysisId: string) =>
  useQAStore(
    useShallow((s) =>
      s.questions
        .filter((q) => q.analysisId === analysisId)
        .sort((a, b) => Number(b.goNoGoImpact) - Number(a.goNoGoImpact) || a.order - b.order),
    ),
  );
