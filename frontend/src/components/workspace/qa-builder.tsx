"use client";

import * as React from "react";
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import { restrictToVerticalAxis, restrictToParentElement } from "@dnd-kit/modifiers";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { motion, useReducedMotion } from "motion/react";
import { GripVertical, Plus, Send, Trash2 } from "lucide-react";

import { cn, pluralize } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/controls";
import { Textarea, Field } from "@/components/ui/input";
import { Callout, EmptyState } from "@/components/ui/feedback";
import { Dialog, DialogContent, Tooltip } from "@/components/ui/overlay";
import { notify } from "@/components/ui/toaster";
import { CitationMeta } from "@/components/domain/primitives";
import { useQAStore, useQuestionsFor } from "@/stores/qa";
import { useIntegrationsStore, useReportsStore } from "@/stores/workspace";
import type { Analysis, QAQuestion } from "@/types";

const SOURCE_LABEL: Record<QAQuestion["sourceKind"], { label: string; tone: "slate" | "ochre" | "seal" | "neutral" }> = {
  silent: { label: "From the SILENT ledger", tone: "slate" },
  contradiction: { label: "Contradiction", tone: "seal" },
  ambiguity: { label: "Ambiguity", tone: "ochre" },
  manual: { label: "Added by hand", tone: "neutral" },
};

/**
 * Questions are ordered by impact first and author intent second, because the
 * ones that move the go/no-go are the ones that must survive an agency's habit
 * of answering only the first few.
 */
export function QAndABuilder({ analysis }: { analysis: Analysis }) {
  const reduce = useReducedMotion();
  const questions = useQuestionsFor(analysis.id);
  const reorder = useQAStore((s) => s.reorder);
  const toggleImpact = useQAStore((s) => s.toggleImpact);
  const addQuestion = useQAStore((s) => s.addQuestion);
  const deleteQuestion = useQAStore((s) => s.deleteQuestion);
  const restoreQuestion = useQAStore((s) => s.restoreQuestion);
  const markSent = useQAStore((s) => s.markSent);
  const outlook = useIntegrationsStore((s) => s.integrations.find((i) => i.id === "outlook"));
  const log = useReportsStore((s) => s.log);

  const [composing, setComposing] = React.useState(false);
  const [draft, setDraft] = React.useState("");
  const [rationale, setRationale] = React.useState("");

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const impactful = questions.filter((q) => q.goNoGoImpact);
  const unsent = questions.filter((q) => !q.sent);

  function onDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const ids = questions.map((q) => q.id);
    const next = arrayMove(ids, ids.indexOf(String(active.id)), ids.indexOf(String(over.id)));
    reorder(analysis.id, next);
    notify.success("Question order updated.");
  }

  function submitDraft() {
    if (draft.trim().length < 8) return;
    const id = addQuestion({
      analysisId: analysis.id,
      text: draft.trim(),
      rationale: rationale.trim() || "Added by the capture team.",
      sourceKind: "manual",
      goNoGoImpact: false,
    });
    setDraft("");
    setRationale("");
    setComposing(false);
    notify.success("Question added.", {
      undo: () => deleteQuestion(id),
    });
  }

  function send() {
    markSent(analysis.id);
    log({ actor: "You", action: "sent the question set for", target: analysis.solicitationNumber, analysisId: analysis.id });
    notify.success("Questions sent to the agency contact.", {
      description: outlook?.connected
        ? `Composed in Outlook as ${outlook.account}.`
        : "Copied to the clipboard — Outlook is not connected.",
      action: { label: "Open in Outlook", onClick: () => notify.info("Opening Outlook…") },
    });
  }

  if (questions.length === 0) {
    return (
      <EmptyState
        title="No questions yet"
        description="Questions are compiled from the SILENT ledger and from contradictions between sections. Convert a ledger entry, or write one by hand."
        action={
          <Button variant="primary" onClick={() => setComposing(true)}>
            <Plus />
            Write a question
          </Button>
        }
      />
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-ink-soft">
          {pluralize(questions.length, "question")} · {impactful.length} affect the go/no-go ·{" "}
          {unsent.length} unsent
        </p>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => setComposing(true)}>
            <Plus />
            Add question
          </Button>
          <Button variant="primary" onClick={send} disabled={unsent.length === 0}>
            <Send />
            Send to agency
          </Button>
        </div>
      </div>

      {impactful.length > 0 ? (
        <Callout tone="ochre" title={`${pluralize(impactful.length, "question")} could change the decision`}>
          These float to the top of the set. Agencies answer in order and rarely answer everything.
        </Callout>
      ) : null}

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={onDragEnd}
        modifiers={[restrictToVerticalAxis, restrictToParentElement]}
      >
        <SortableContext items={questions.map((q) => q.id)} strategy={verticalListSortingStrategy}>
          <ol className="space-y-2.5">
            {questions.map((question, index) => (
              <SortableQuestion
                key={question.id}
                question={question}
                index={index}
                analysisId={analysis.id}
                reduce={Boolean(reduce)}
                onToggleImpact={() => {
                  toggleImpact(question.id);
                  notify.success(
                    question.goNoGoImpact ? "No longer marked as decision-affecting." : "Marked as decision-affecting.",
                    { description: "It has been reordered accordingly." },
                  );
                }}
                onDelete={() => {
                  const removed = deleteQuestion(question.id);
                  if (!removed) return;
                  notify.success("Question removed.", { undo: () => restoreQuestion(removed) });
                }}
              />
            ))}
          </ol>
        </SortableContext>
      </DndContext>

      <Dialog open={composing} onOpenChange={setComposing}>
        <DialogContent
          title="Write a question"
          description="Ask it the way you would ask the contracting officer."
          footer={
            <>
              <Button variant="ghost" onClick={() => setComposing(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={submitDraft} disabled={draft.trim().length < 8}>
                Add to the set
              </Button>
            </>
          }
        >
          <div className="space-y-4">
            <Field label="Question" htmlFor="qa-text" required>
              <Textarea
                id="qa-text"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Section C.5 authorises liquidated damages but states no rate. Will the agency publish one before proposals are due?"
                className="min-h-28"
              />
            </Field>
            <Field label="Why it matters" htmlFor="qa-rationale" hint="Kept internal">
              <Textarea
                id="qa-rationale"
                value={rationale}
                onChange={(e) => setRationale(e.target.value)}
                placeholder="Unbounded exposure cannot be priced."
              />
            </Field>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function SortableQuestion({
  question,
  index,
  analysisId,
  reduce,
  onToggleImpact,
  onDelete,
}: {
  question: QAQuestion;
  index: number;
  analysisId: string;
  reduce: boolean;
  onToggleImpact: () => void;
  onDelete: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: question.id,
  });
  const source = SOURCE_LABEL[question.sourceKind];

  return (
    <motion.li
      ref={setNodeRef}
      style={{ transform: CSS.Translate.toString(transform), transition }}
      layout={!reduce}
      transition={{ type: "spring", stiffness: 520, damping: 42 }}
      className={cn(
        "group relative rounded-lg border bg-paper-raised px-4 py-4",
        question.goNoGoImpact ? "border-l-[3px] border-l-ochre border-line" : "border-line",
        isDragging && "z-10 shadow-[var(--shadow-overlay)]",
      )}
    >
      <div className="flex items-start gap-3">
        <button
          {...attributes}
          {...listeners}
          aria-label={`Reorder question ${index + 1}`}
          className="mt-0.5 cursor-grab touch-none rounded-sm p-0.5 text-ink-faint transition-colors duration-150 hover:text-ink active:cursor-grabbing"
        >
          <GripVertical className="size-4" />
        </button>

        <span className="mt-0.5 shrink-0 font-mono text-xs tabular text-ink-faint">
          Q-{String(index + 1).padStart(2, "0")}
        </span>

        <div className="min-w-0 flex-1 space-y-3">
          <p className="text-sm leading-relaxed text-ink">{question.text}</p>
          <p className="text-sm leading-relaxed text-ink-faint">{question.rationale}</p>
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={source.tone}>{source.label}</Badge>
            {question.sent ? <Badge tone="leaf">Sent</Badge> : null}
          </div>
          {question.citation ? (
            <CitationMeta
              citation={question.citation}
              analysisId={analysisId}
              label={`Question ${index + 1}`}
              origin="Q&A"
              clamp={2}
            />
          ) : null}
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <Tooltip content="Affects the go/no-go decision">
            <label className="flex cursor-pointer items-center gap-2">
              <span className="hidden text-2xs uppercase tracking-[0.1em] text-ink-faint sm:inline">impact</span>
              <Switch
                checked={question.goNoGoImpact}
                onCheckedChange={onToggleImpact}
                aria-label="Affects the go/no-go decision"
              />
            </label>
          </Tooltip>
          <Button
            variant="quiet"
            size="iconSm"
            aria-label="Remove question"
            onClick={onDelete}
            className="opacity-0 transition-opacity duration-150 focus-visible:opacity-100 group-hover:opacity-100"
          >
            <Trash2 />
          </Button>
        </div>
      </div>
    </motion.li>
  );
}
