"use client";

import * as React from "react";
import { motion, useReducedMotion } from "motion/react";
import { BookMarked, Pencil, Plus, Trash2 } from "lucide-react";

import { cn, formatCurrency } from "@/lib/utils";
import { longDate } from "@/lib/dates";
import { Button } from "@/components/ui/button";
import { PageHeader, Panel, Separator, Well } from "@/components/ui/surface";
import { Badge } from "@/components/ui/badge";
import { Field, Input, SearchField, Textarea } from "@/components/ui/input";
import { Segmented, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, TagsInput } from "@/components/ui/controls";
import { ConfirmDialog, Dialog, DialogContent } from "@/components/ui/overlay";
import { EmptyState } from "@/components/ui/feedback";
import { notify } from "@/components/ui/toaster";
import { useKnowledgeStore } from "@/stores/workspace";
import type { PastBid } from "@/types";

const OUTCOME: Record<PastBid["outcome"], { label: string; tone: "leaf" | "seal" | "neutral" | "ochre" }> = {
  won: { label: "Won", tone: "leaf" },
  lost: { label: "Lost", tone: "seal" },
  "no-bid": { label: "No-bid", tone: "neutral" },
  pending: { label: "Awaiting award", tone: "ochre" },
};

type Draft = {
  title: string;
  agency: string;
  outcome: PastBid["outcome"];
  value: string;
  submittedAt: string;
  debrief: string;
  incumbent: string;
  scoreGap: string;
  lessons: string[];
};

const emptyDraft: Draft = {
  title: "",
  agency: "",
  outcome: "won",
  value: "",
  submittedAt: new Date().toISOString().slice(0, 10),
  debrief: "",
  incumbent: "",
  scoreGap: "",
  lessons: [],
};

/**
 * Institutional memory is the reason a firm stops re-learning the same debrief.
 * Every entry here is written to be read two years later by somebody new.
 */
export function KnowledgeView() {
  const reduce = useReducedMotion();
  const bids = useKnowledgeStore((s) => s.bids);
  const addBid = useKnowledgeStore((s) => s.addBid);
  const updateBid = useKnowledgeStore((s) => s.updateBid);
  const deleteBid = useKnowledgeStore((s) => s.deleteBid);
  const restoreBid = useKnowledgeStore((s) => s.restoreBid);

  const [query, setQuery] = React.useState("");
  const [outcome, setOutcome] = React.useState<string>("all");
  const [editing, setEditing] = React.useState<PastBid | null>(null);
  const [creating, setCreating] = React.useState(false);
  const [draft, setDraft] = React.useState<Draft>(emptyDraft);
  const [confirm, setConfirm] = React.useState<PastBid | null>(null);

  const filtered = bids.filter((bid) => {
    if (outcome !== "all" && bid.outcome !== outcome) return false;
    if (!query.trim()) return true;
    const q = query.toLowerCase();
    return [bid.title, bid.agency, bid.debrief, ...bid.lessons].join(" ").toLowerCase().includes(q);
  });

  const won = bids.filter((b) => b.outcome === "won");
  const decided = bids.filter((b) => b.outcome === "won" || b.outcome === "lost");
  const winRate = decided.length ? Math.round((won.length / decided.length) * 100) : 0;
  const captured = won.reduce((sum, b) => sum + b.value, 0);

  function openCreate() {
    setDraft(emptyDraft);
    setEditing(null);
    setCreating(true);
  }

  function openEdit(bid: PastBid) {
    setDraft({
      title: bid.title,
      agency: bid.agency,
      outcome: bid.outcome,
      value: String(bid.value),
      submittedAt: bid.submittedAt.slice(0, 10),
      debrief: bid.debrief,
      incumbent: bid.incumbent ?? "",
      scoreGap: bid.scoreGap ?? "",
      lessons: bid.lessons,
    });
    setEditing(bid);
    setCreating(true);
  }

  function save() {
    const payload = {
      title: draft.title.trim(),
      agency: draft.agency.trim(),
      outcome: draft.outcome,
      value: Number(draft.value.replace(/[^0-9.]/g, "")) || 0,
      submittedAt: new Date(`${draft.submittedAt}T12:00:00Z`).toISOString(),
      debrief: draft.debrief.trim(),
      incumbent: draft.incumbent.trim() || undefined,
      scoreGap: draft.scoreGap.trim() || undefined,
      lessons: draft.lessons,
    };
    if (editing) {
      updateBid(editing.id, payload);
      notify.success("Entry updated.");
    } else {
      addBid(payload);
      notify.success("Added to institutional memory.");
    }
    setCreating(false);
    setEditing(null);
  }

  return (
    <div className="mx-auto max-w-[76rem] space-y-6">
      <PageHeader
        eyebrow="Library"
        title="Institutional memory"
        description="Past bids, debriefs, and the lessons that should shape the next pursuit."
        actions={
          <Button variant="primary" onClick={openCreate}>
            <Plus />
            Record a bid
          </Button>
        }
      />

      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Recorded pursuits" value={String(bids.length)} />
        <Stat label="Win rate" value={`${winRate}%`} hint={`${won.length} of ${decided.length} decided`} />
        <Stat label="Value captured" value={formatCurrency(captured)} />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <SearchField
          value={query}
          onValueChange={setQuery}
          placeholder="Search debriefs and lessons…"
          className="w-full max-w-sm"
        />
        <Segmented
          ariaLabel="Filter by outcome"
          value={outcome}
          onValueChange={setOutcome}
          options={[
            { value: "all", label: "All" },
            { value: "won", label: "Won" },
            { value: "lost", label: "Lost" },
            { value: "no-bid", label: "No-bid" },
            { value: "pending", label: "Pending" },
          ]}
        />
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          illustration={<BookMarked className="size-7 text-patina" aria-hidden />}
          title={bids.length === 0 ? "No history yet" : "Nothing matches"}
          description={
            bids.length === 0
              ? "Record the outcome of a pursuit and the debrief that followed. The next analysis will be sharper for it."
              : "Loosen the filter, or search for a different phrase."
          }
          action={
            bids.length === 0 ? (
              <Button variant="primary" onClick={openCreate}>
                <Plus />
                Record a bid
              </Button>
            ) : (
              <Button
                variant="secondary"
                onClick={() => {
                  setQuery("");
                  setOutcome("all");
                }}
              >
                Clear filters
              </Button>
            )
          }
        />
      ) : (
        <ul className="space-y-3">
          {filtered.map((bid, index) => (
            <motion.li
              key={bid.id}
              initial={reduce ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: Math.min(index * 0.03, 0.2), duration: 0.26, ease: [0.32, 0.72, 0, 1] }}
            >
              <Panel className="group p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0 space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone={OUTCOME[bid.outcome].tone}>{OUTCOME[bid.outcome].label}</Badge>
                      <span className="text-xs text-ink-faint">{bid.agency}</span>
                      <span className="text-ink-faint/60" aria-hidden>
                        ·
                      </span>
                      <span className="text-xs text-ink-faint">{longDate(bid.submittedAt)}</span>
                    </div>
                    <h3 className="text-lg leading-snug text-ink">{bid.title}</h3>
                    <p className="font-mono text-xs text-ink-faint tabular">
                      {formatCurrency(bid.value, false)}
                      {bid.scoreGap ? ` · ${bid.scoreGap}` : ""}
                      {bid.incumbent ? ` · incumbent ${bid.incumbent}` : ""}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-1 opacity-0 transition-opacity duration-150 focus-within:opacity-100 group-hover:opacity-100">
                    <Button variant="quiet" size="iconSm" aria-label="Edit entry" onClick={() => openEdit(bid)}>
                      <Pencil />
                    </Button>
                    <Button variant="quiet" size="iconSm" aria-label="Delete entry" onClick={() => setConfirm(bid)}>
                      <Trash2 />
                    </Button>
                  </div>
                </div>

                <Separator className="my-4" />

                <p className="max-w-3xl text-sm leading-relaxed text-ink-soft">{bid.debrief}</p>

                {bid.lessons.length > 0 ? (
                  <ul className="mt-4 space-y-1.5">
                    {bid.lessons.map((lesson, i) => (
                      <li key={i} className="flex gap-2.5 text-sm text-ink-soft">
                        <span className="mt-[7px] size-1 shrink-0 rounded-full bg-patina" aria-hidden />
                        <span className="leading-relaxed">{lesson}</span>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </Panel>
            </motion.li>
          ))}
        </ul>
      )}

      <Dialog open={creating} onOpenChange={setCreating}>
        <DialogContent
          title={editing ? "Edit the record" : "Record a bid"}
          description="Written for whoever picks up this agency next."
          className="max-w-xl"
          footer={
            <>
              <Button variant="ghost" onClick={() => setCreating(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={save} disabled={draft.title.trim().length < 3}>
                {editing ? "Save changes" : "Add entry"}
              </Button>
            </>
          }
        >
          <div className="space-y-4">
            <Field label="Solicitation title" htmlFor="kb-title" required>
              <Input
                id="kb-title"
                value={draft.title}
                onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                placeholder="Statewide Assessment Delivery Platform"
              />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Agency" htmlFor="kb-agency">
                <Input
                  id="kb-agency"
                  value={draft.agency}
                  onChange={(e) => setDraft({ ...draft, agency: e.target.value })}
                />
              </Field>
              <Field label="Outcome" htmlFor="kb-outcome">
                <Select
                  value={draft.outcome}
                  onValueChange={(v) => setDraft({ ...draft, outcome: v as PastBid["outcome"] })}
                >
                  <SelectTrigger id="kb-outcome">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(Object.keys(OUTCOME) as PastBid["outcome"][]).map((key) => (
                      <SelectItem key={key} value={key}>
                        {OUTCOME[key].label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
              <Field label="Value" htmlFor="kb-value" hint="USD">
                <Input
                  id="kb-value"
                  inputMode="numeric"
                  value={draft.value}
                  onChange={(e) => setDraft({ ...draft, value: e.target.value })}
                  placeholder="4200000"
                />
              </Field>
              <Field label="Submitted" htmlFor="kb-date">
                <Input
                  id="kb-date"
                  type="date"
                  value={draft.submittedAt}
                  onChange={(e) => setDraft({ ...draft, submittedAt: e.target.value })}
                />
              </Field>
              <Field label="Incumbent" htmlFor="kb-incumbent">
                <Input
                  id="kb-incumbent"
                  value={draft.incumbent}
                  onChange={(e) => setDraft({ ...draft, incumbent: e.target.value })}
                />
              </Field>
              <Field label="Score gap" htmlFor="kb-gap" hint="As stated in the debrief">
                <Input
                  id="kb-gap"
                  value={draft.scoreGap}
                  onChange={(e) => setDraft({ ...draft, scoreGap: e.target.value })}
                  placeholder="4.5 points on Technical Approach"
                />
              </Field>
            </div>
            <Field label="Debrief" htmlFor="kb-debrief">
              <Textarea
                id="kb-debrief"
                value={draft.debrief}
                onChange={(e) => setDraft({ ...draft, debrief: e.target.value })}
                className="min-h-24"
                placeholder="What the agency actually said, not what we hoped they meant."
              />
            </Field>
            <Field label="Lessons" hint="Press Enter after each">
              <TagsInput
                values={draft.lessons}
                onValuesChange={(lessons) => setDraft({ ...draft, lessons })}
                placeholder="Price the transition period explicitly"
              />
            </Field>
          </div>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={Boolean(confirm)}
        onOpenChange={(open) => !open && setConfirm(null)}
        title="Delete this record?"
        destructive
        confirmLabel="Delete"
        description={confirm ? `“${confirm.title}” and its lessons will be removed.` : ""}
        onConfirm={() => {
          if (!confirm) return;
          const removed = deleteBid(confirm.id);
          setConfirm(null);
          if (removed) notify.success("Record deleted.", { undo: () => restoreBid(removed) });
        }}
      />
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Well className="space-y-1">
      <p className="eyebrow">{label}</p>
      <p className={cn("display-tight text-2xl text-ink tabular")}>{value}</p>
      {hint ? <p className="text-xs text-ink-faint">{hint}</p> : null}
    </Well>
  );
}
