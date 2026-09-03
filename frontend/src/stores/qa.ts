import { create } from "zustand";
import { useShallow } from "zustand/react/shallow";
import { persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";

import { seedQuestions } from "@/data";
import { createId } from "@/lib/utils";
import { persistConfig } from "./persist";
import type { QAQuestion } from "@/types";

interface QAState {
  questions: QAQuestion[];
  addQuestion: (input: Omit<QAQuestion, "id" | "order" | "sent">) => string;
  updateQuestion: (id: string, patch: Partial<QAQuestion>) => void;
  deleteQuestion: (id: string) => QAQuestion | undefined;
  restoreQuestion: (question: QAQuestion) => void;
  toggleImpact: (id: string) => void;
  reorder: (analysisId: string, orderedIds: string[]) => void;
  markSent: (analysisId: string, ids?: string[]) => void;
  resetToSeed: () => void;
}

export const useQAStore = create<QAState>()(
  persist(
    immer((set, get) => ({
      questions: seedQuestions,

      addQuestion: (input) => {
        const id = createId("q");
        const siblings = get().questions.filter((q) => q.analysisId === input.analysisId);
        set((s) => {
          s.questions.push({ ...input, id, order: siblings.length, sent: false });
        });
        return id;
      },

      updateQuestion: (id, patch) =>
        set((s) => {
          const target = s.questions.find((q) => q.id === id);
          if (target) Object.assign(target, patch);
        }),

      deleteQuestion: (id) => {
        const existing = get().questions.find((q) => q.id === id);
        set((s) => {
          s.questions = s.questions.filter((q) => q.id !== id);
        });
        return existing;
      },

      restoreQuestion: (question) =>
        set((s) => {
          if (!s.questions.some((q) => q.id === question.id)) s.questions.push(question);
        }),

      toggleImpact: (id) =>
        set((s) => {
          const target = s.questions.find((q) => q.id === id);
          if (target) target.goNoGoImpact = !target.goNoGoImpact;
        }),

      reorder: (analysisId, orderedIds) =>
        set((s) => {
          orderedIds.forEach((id, index) => {
            const target = s.questions.find((q) => q.id === id && q.analysisId === analysisId);
            if (target) target.order = index;
          });
        }),

      markSent: (analysisId, ids) =>
        set((s) => {
          for (const q of s.questions) {
            if (q.analysisId !== analysisId) continue;
            if (ids && !ids.includes(q.id)) continue;
            q.sent = true;
          }
        }),

      resetToSeed: () =>
        set((s) => {
          s.questions = structuredClone(seedQuestions);
        }),
    })),
    persistConfig<QAState>("qa", (s) => ({ questions: s.questions })),
  ),
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
