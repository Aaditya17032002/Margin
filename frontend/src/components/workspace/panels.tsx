"use client";

import * as React from "react";
import Link from "next/link";
import { motion, useReducedMotion } from "motion/react";
import { ArrowRight, CircleSlash, FileDiff, MessageSquarePlus, Minus, Plus } from "lucide-react";

import { cn, formatCurrency, pluralize } from "@/lib/utils";
import { longDate, relative } from "@/lib/dates";
import { listItem, staggerList } from "@/lib/motion";
import { Button } from "@/components/ui/button";
import { Panel, PanelHeader, Well, Separator } from "@/components/ui/surface";
import { Callout, EmptyState } from "@/components/ui/feedback";
import { Badge } from "@/components/ui/badge";
import { Avatar, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/controls";
import { Textarea } from "@/components/ui/input";
import { Dialog, DialogContent, Tooltip } from "@/components/ui/overlay";
import { notify } from "@/components/ui/toaster";
import { GoNoGoGauge } from "@/components/domain/gauge";
import { EvaluationDonut, ConfidenceDistribution, DeadlineTimeline } from "@/components/domain/charts";
import { FindingList } from "@/components/domain/finding";
import { CitationMeta, DocTypeBadge } from "@/components/domain/primitives";
import { DeadlineCountdown } from "@/components/domain/deadline";
import { QAndABuilder } from "./qa-builder";
import { ComplianceMatrix } from "./compliance-matrix";
import { useAnalysesStore, allFindings } from "@/stores/analyses";
import { useQAStore } from "@/stores/qa";
import { useReportsStore } from "@/stores/workspace";
import type { Analysis, GoNoGo } from "@/types";

/* ================================================================ */
/* Go / No-Go                                                        */
/* ================================================================ */

export function GoNoGoPanel({ analysis }: { analysis: Analysis }) {
  const reduce = useReducedMotion();
  const decide = useAnalysesStore((s) => s.decide);
  const log = useReportsStore((s) => s.log);
  const [note, setNote] = React.useState(analysis.decisionNote ?? "");
  const [confirming, setConfirming] = React.useState<GoNoGo | null>(null);

  const biggestRisk = analysis.risks.find((r) => r.severity === "critical") ?? analysis.risks[0];

  function record(decision: GoNoGo) {
    const previous = decide(analysis.id, decision, note.trim() || undefined);
    log({
      actor: "You",
      action: `recorded a ${decision === "no-bid" ? "No-bid" : decision === "bid" ? "Bid" : "Watch"} decision on`,
      target: analysis.solicitationNumber,
      analysisId: analysis.id,
    });
    notify.success(
      decision === "bid" ? "Recorded: Bid." : decision === "no-bid" ? "Recorded: No-bid." : "Recorded: Watch.",
      {
        description: "The decision and its note are in the version history.",
        undo: previous ? () => decide(analysis.id, previous, analysis.decisionNote) : undefined,
      },
    );
    setConfirming(null);
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_1.15fr]">
      <div className="space-y-6">
        <Panel className="px-6 py-7">
          <div className="flex justify-center">
            <GoNoGoGauge gates={analysis.gates} decision={analysis.goNoGo} size="lg" />
          </div>
        </Panel>

        <Panel>
          <PanelHeader title="Record the decision" description="Reversible, and always attributed." />
          <div className="space-y-4 px-5 py-5">
            <Textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Why this way? One sentence is enough — it is what the next person reads."
              aria-label="Decision note"
            />
            <div className="flex flex-wrap gap-2">
              <Button
                variant={analysis.goNoGo === "bid" ? "primary" : "secondary"}
                onClick={() => setConfirming("bid")}
              >
                Bid
              </Button>
              <Button
                variant={analysis.goNoGo === "watch" ? "primary" : "secondary"}
                onClick={() => setConfirming("watch")}
              >
                Watch
              </Button>
              <Button
                variant={analysis.goNoGo === "no-bid" ? "danger" : "outlineDanger"}
                onClick={() => setConfirming("no-bid")}
              >
                No-bid
              </Button>
              {analysis.goNoGo !== "undecided" ? (
                <Button variant="quiet" onClick={() => record("undecided")}>
                  Reopen
                </Button>
              ) : null}
            </div>
            {analysis.decisionNote ? (
              <Well>
                <p className="eyebrow pb-1">Recorded note</p>
                <p className="text-sm leading-relaxed text-ink-soft">{analysis.decisionNote}</p>
              </Well>
            ) : null}
          </div>
        </Panel>
      </div>

      <div className="space-y-6">
        <Panel>
          <PanelHeader title="The four gates" description="Each one answered from the document, not from memory." />
          <motion.ul
            variants={staggerList()}
            initial={reduce ? false : "hidden"}
            animate="visible"
            className="divide-y divide-[var(--line)]"
          >
            {analysis.gates.map((gate) => (
              <motion.li key={gate.id} variants={listItem} className="space-y-3 px-5 py-5">
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-medium text-ink">{gate.question}</p>
                  <GateMark met={gate.met} weight={gate.weight} />
                </div>
                <p className="text-sm leading-relaxed text-ink-soft">{gate.answer}</p>
                {gate.citation ? (
                  <CitationMeta
                    citation={gate.citation}
                    analysisId={analysis.id}
                    label={gate.question}
                    origin="Go / No-Go"
                  />
                ) : null}
              </motion.li>
            ))}
          </motion.ul>
        </Panel>

        {biggestRisk ? (
          <Callout tone={biggestRisk.severity === "critical" ? "seal" : "ochre"} title="The single biggest risk">
            <p className="font-medium text-ink">{biggestRisk.title}</p>
            <p className="mt-1">{biggestRisk.narrative}</p>
            <p className="mt-2 text-ink">
              <span className="font-medium">What to do: </span>
              {biggestRisk.mitigation}
            </p>
            <CitationMeta
              className="mt-3"
              citation={biggestRisk.citation}
              analysisId={analysis.id}
              label={biggestRisk.title}
              origin="Risk"
            />
          </Callout>
        ) : null}
      </div>

      <Dialog open={Boolean(confirming)} onOpenChange={(open) => !open && setConfirming(null)}>
        <DialogContent
          size="sm"
          title={
            confirming === "bid"
              ? "Record a Bid decision?"
              : confirming === "no-bid"
                ? "Record a No-bid decision?"
                : "Mark this as Watch?"
          }
          footer={
            <>
              <Button variant="ghost" onClick={() => setConfirming(null)}>
                Cancel
              </Button>
              <Button
                variant={confirming === "no-bid" ? "danger" : "primary"}
                onClick={() => confirming && record(confirming)}
              >
                Record decision
              </Button>
            </>
          }
        >
          <p className="text-sm leading-relaxed text-ink-soft">
            {analysis.gates.filter((g) => g.weight === "hard" && g.met === false).length > 0 &&
            confirming === "bid"
              ? "A hard gate is still unmet. Recording a bid here is a deliberate override, and it will be logged as one."
              : "This moves the analysis to Decided and writes an entry into the version history. You can reopen it at any time."}
          </p>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function GateMark({ met, weight }: { met: boolean | null; weight: "hard" | "soft" }) {
  const tone = met === true ? "leaf" : met === false ? "seal" : "ochre";
  const label = met === true ? "Met" : met === false ? "Unmet" : "Unresolved";
  return (
    <span className="flex shrink-0 items-center gap-1.5">
      <Badge tone={tone}>{label}</Badge>
      {weight === "hard" ? (
        <Tooltip content="A hard gate — unmet means the bid is over">
          <span className="font-mono text-2xs uppercase tracking-[0.1em] text-ink-faint">hard</span>
        </Tooltip>
      ) : null}
    </span>
  );
}

/* ================================================================ */
/* Overview & dates                                                  */
/* ================================================================ */

export function OverviewPanel({ analysis }: { analysis: Analysis }) {
  const findings = allFindings(analysis);
  const timelinePoints = analysis.dates.map((d) => ({
    id: d.id,
    label: d.label,
    at: d.at,
    tone:
      d.kind === "proposal-due"
        ? "var(--seal)"
        : d.kind === "questions-due"
          ? "var(--ochre)"
          : d.kind === "award"
            ? "var(--leaf)"
            : "var(--slate)",
  }));

  return (
    <div className="space-y-6">
      {analysis.summary ? (
        <Panel className="px-6 py-5">
          <p className="eyebrow pb-2">What this is</p>
          <p className="max-w-3xl text-lg leading-relaxed text-ink-soft">{analysis.summary}</p>
        </Panel>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <Panel>
          <PanelHeader title="Identity" description="Who is buying, under what instrument, on what terms." />
          <div className="px-5 pb-2">
            <FindingList findings={analysis.identity} analysisId={analysis.id} sectionLabel="Identity" />
          </div>
        </Panel>

        <div className="space-y-6">
          <Panel>
            <PanelHeader title="At a glance" />
            <dl className="divide-y divide-[var(--line)]">
              <Row label="Instrument" value={<DocTypeBadge docType={analysis.docType} />} />
              <Row label="Agency" value={analysis.agency} />
              {analysis.subAgency ? <Row label="Office" value={analysis.subAgency} /> : null}
              <Row label="NAICS" value={analysis.naics} mono />
              <Row label="Set-aside" value={analysis.setAside} />
              <Row label="Place of performance" value={analysis.placeOfPerformance} />
              <Row
                label="Estimated value"
                value={analysis.estimatedValue ? formatCurrency(analysis.estimatedValue, false) : "Not stated"}
                mono
              />
              <Row label="Document" value={`${analysis.fileName} · ${analysis.pageCount} pages`} mono />
              <Row label="Owner" value={analysis.owner} />
            </dl>
          </Panel>

          <Panel>
            <PanelHeader title="Confidence spread" description={`${findings.length} findings in this read.`} />
            <div className="px-5 py-5">
              <ConfidenceDistribution confidences={findings.map((f) => f.confidence)} />
            </div>
          </Panel>
        </div>
      </div>

      <Panel>
        <PanelHeader title="Key dates" description="Held in the agency's timezone, counted down in yours." />
        {analysis.dates.length === 0 ? (
          <div className="px-5 py-8 text-sm text-ink-faint">No dates have been extracted from this document.</div>
        ) : (
          <>
            <div className="px-8">
              <DeadlineTimeline points={timelinePoints} />
            </div>
            <Separator />
            <ul className="divide-y divide-[var(--line)]">
              {analysis.dates.map((date) => (
                <li key={date.id} className="space-y-3 px-5 py-4">
                  <DeadlineCountdown at={date.at} timezone={date.timezone} label={date.label} size="md" />
                  {date.citation ? (
                    <CitationMeta
                      citation={date.citation}
                      analysisId={analysis.id}
                      label={date.label}
                      origin="Key dates"
                    />
                  ) : null}
                </li>
              ))}
            </ul>
          </>
        )}
      </Panel>

      {analysis.clins.length > 0 ? (
        <Panel>
          <PanelHeader title="Contract line items" description="As numbered in the solicitation." />
          <ul className="divide-y divide-[var(--line)]">
            {analysis.clins.map((clin) => (
              <li key={clin.id} className="flex flex-wrap items-baseline justify-between gap-4 px-5 py-3">
                <div className="min-w-0">
                  <span className="mr-3 font-mono text-xs text-patina">{clin.number}</span>
                  <span className="text-sm text-ink">{clin.description}</span>
                </div>
                <div className="flex shrink-0 items-baseline gap-5 font-mono text-xs text-ink-faint">
                  <span>{clin.quantity}</span>
                  <span className="tabular text-ink-soft">
                    {clin.ceiling ? formatCurrency(clin.ceiling, false) : "Unpriced"}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </Panel>
      ) : null}
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-6 px-5 py-2.5">
      <dt className="shrink-0 text-sm text-ink-faint">{label}</dt>
      <dd className={cn("min-w-0 text-right text-sm text-ink", mono && "font-mono text-xs")}>{value}</dd>
    </div>
  );
}

/* ================================================================ */
/* Simple finding sections                                           */
/* ================================================================ */

export function FindingsPanel({
  analysis,
  sections,
}: {
  analysis: Analysis;
  sections: { key: keyof Analysis; title: string; description?: string }[];
}) {
  const toggleVerified = useAnalysesStore((s) => s.toggleFindingVerified);
  const toggleFlag = useAnalysesStore((s) => s.toggleFindingFlag);

  const nonEmpty = sections.filter((section) => (analysis[section.key] as unknown[]).length > 0);

  if (nonEmpty.length === 0) {
    return (
      <EmptyState
        title="Nothing in this section"
        description="Either the document is silent here, or the pass that produces this section was not part of the chosen mode."
        action={
          <Button asChild variant="secondary">
            <Link href={`/app/analyses/${analysis.id}/run`}>Run a deeper read</Link>
          </Button>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      {nonEmpty.map((section) => (
        <Panel key={String(section.key)}>
          <PanelHeader title={section.title} description={section.description} />
          <div className="px-5 pb-2">
            <FindingList
              findings={analysis[section.key] as never}
              analysisId={analysis.id}
              sectionLabel={section.title}
              onVerify={(id) => {
                toggleVerified(analysis.id, id);
                notify.success("Finding verified.", { description: "It will stop appearing in the review queue." });
              }}
              onFlag={(id) => {
                toggleFlag(analysis.id, id);
                notify.info("Flag updated.");
              }}
            />
          </div>
        </Panel>
      ))}
    </div>
  );
}

/* ================================================================ */
/* Eligibility & evaluation                                          */
/* ================================================================ */

export function EvaluationPanel({ analysis }: { analysis: Analysis }) {
  const toggleVerified = useAnalysesStore((s) => s.toggleFindingVerified);

  return (
    <div className="space-y-6">
      {analysis.evaluation.length > 0 ? (
        <Panel>
          <PanelHeader
            title="How this will be scored"
            description="Reconstructed from the evaluation section, weight by weight."
          />
          <div className="px-5 py-6">
            <EvaluationDonut factors={analysis.evaluation} analysisId={analysis.id} />
          </div>
        </Panel>
      ) : null}

      {analysis.eligibility.length > 0 ? (
        <Panel>
          <PanelHeader
            title="Eligibility gates"
            description="The things that decide whether anyone reads your prose at all."
          />
          <div className="px-5 pb-2">
            <FindingList
              findings={analysis.eligibility}
              analysisId={analysis.id}
              sectionLabel="Eligibility"
              onVerify={(id) => {
                toggleVerified(analysis.id, id);
                notify.success("Finding verified.");
              }}
            />
          </div>
        </Panel>
      ) : null}

      {analysis.pricing.length > 0 ? (
        <Panel>
          <PanelHeader title="Pricing terms" />
          <div className="px-5 pb-2">
            <FindingList findings={analysis.pricing} analysisId={analysis.id} sectionLabel="Pricing" />
          </div>
        </Panel>
      ) : null}
    </div>
  );
}

/* ================================================================ */
/* Risks                                                             */
/* ================================================================ */

export function RisksPanel({ analysis }: { analysis: Analysis }) {
  const reduce = useReducedMotion();
  const [severity, setSeverity] = React.useState<string>("all");

  const filtered = analysis.risks.filter((r) => severity === "all" || r.severity === severity);

  if (analysis.risks.length === 0) {
    return (
      <EmptyState
        title="No risks recorded"
        description="The Risk pass either found nothing worth naming, or was not part of the mode used for this read."
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-ink-soft">
          {pluralize(analysis.risks.filter((r) => r.severity === "critical").length, "critical risk")} ·{" "}
          {pluralize(analysis.risks.length, "risk")} in total
        </p>
        <Select value={severity} onValueChange={setSeverity}>
          <SelectTrigger className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All severities</SelectItem>
            <SelectItem value="critical">Critical only</SelectItem>
            <SelectItem value="elevated">Elevated</SelectItem>
            <SelectItem value="moderate">Moderate</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <motion.div
        variants={staggerList()}
        initial={reduce ? false : "hidden"}
        animate="visible"
        className="space-y-3"
      >
        {filtered.map((risk) => (
          <motion.article
            key={risk.id}
            variants={listItem}
            className={cn(
              "rounded-lg border border-line border-l-[3px] bg-paper-raised px-5 py-4",
              risk.severity === "critical" && "border-l-seal",
              risk.severity === "elevated" && "border-l-ochre",
              risk.severity === "moderate" && "border-l-slate",
            )}
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <h3 className="text-base leading-snug text-ink">{risk.title}</h3>
              <div className="flex shrink-0 items-center gap-1.5">
                <Badge
                  tone={risk.severity === "critical" ? "seal" : risk.severity === "elevated" ? "ochre" : "slate"}
                >
                  {risk.severity}
                </Badge>
                <Badge tone="neutral">{risk.likelihood}</Badge>
              </div>
            </div>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-ink-soft">{risk.narrative}</p>
            <Well className="mt-3">
              <p className="eyebrow pb-1">Mitigation</p>
              <p className="text-sm leading-relaxed text-ink-soft">{risk.mitigation}</p>
            </Well>
            <CitationMeta
              className="mt-1"
              citation={risk.citation}
              analysisId={analysis.id}
              label={risk.title}
              origin="Risk"
            />
          </motion.article>
        ))}
      </motion.div>
    </div>
  );
}

/* ================================================================ */
/* SILENT ledger                                                     */
/* ================================================================ */

export function SilentPanel({ analysis }: { analysis: Analysis }) {
  const reduce = useReducedMotion();
  const addQuestion = useQAStore((s) => s.addQuestion);
  const deleteQuestion = useQAStore((s) => s.deleteQuestion);
  const questions = useQAStore((s) => s.questions);
  const updateAnalysis = useAnalysesStore((s) => s.updateAnalysis);

  function convert(itemId: string) {
    const item = analysis.silent.find((s) => s.id === itemId);
    if (!item) return;
    const questionId = addQuestion({
      analysisId: analysis.id,
      text: `The solicitation does not address ${item.topic.toLowerCase()}. ${item.expectation} Will the agency provide this before the question deadline?`,
      rationale: item.consequence,
      sourceKind: "silent",
      goNoGoImpact: false,
    });
    updateAnalysis(analysis.id, {
      silent: analysis.silent.map((s) =>
        s.id === itemId ? { ...s, convertedToQuestionId: questionId } : s,
      ),
    });
    notify.success("Added to the question set.", {
      description: item.topic,
      undo: () => {
        deleteQuestion(questionId);
        updateAnalysis(analysis.id, {
          silent: analysis.silent.map((s) =>
            s.id === itemId ? { ...s, convertedToQuestionId: undefined } : s,
          ),
        });
      },
    });
  }

  if (analysis.silent.length === 0) {
    return (
      <EmptyState
        title="The ledger is empty"
        description="Nothing conspicuous is missing from this document — or the pass that looks for absence has not been run."
      />
    );
  }

  return (
    <div className="space-y-4">
      <Callout tone="slate" title="What the document never said">
        A solicitation is defined as much by its silences as by its clauses. Each entry below is something a
        document of this kind would ordinarily state, and does not.
      </Callout>

      <motion.ul
        variants={staggerList()}
        initial={reduce ? false : "hidden"}
        animate="visible"
        className="space-y-3"
      >
        {analysis.silent.map((item) => {
          const converted = item.convertedToQuestionId
            ? questions.some((q) => q.id === item.convertedToQuestionId)
            : false;
          return (
            <motion.li
              key={item.id}
              variants={listItem}
              className={cn(
                "rounded-lg border border-dashed bg-paper-raised px-5 py-4",
                converted ? "border-patina/45" : "border-line-strong",
              )}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1 space-y-1.5">
                  <div className="flex items-center gap-2">
                    <CircleSlash className="size-3.5 shrink-0 text-ink-faint" aria-hidden />
                    <h3 className="text-base text-ink-soft">{item.topic}</h3>
                  </div>
                  {/* Ghosted treatment: absence should not read as loud as a finding. */}
                  <p className="text-sm leading-relaxed text-ink-faint">{item.expectation}</p>
                  <p className="text-sm leading-relaxed text-ink-soft">
                    <span className="font-medium text-ink">Consequence: </span>
                    {item.consequence}
                  </p>
                </div>
                {converted ? (
                  <Badge tone="patina">In the question set</Badge>
                ) : (
                  <Button variant="secondary" size="sm" onClick={() => convert(item.id)}>
                    <MessageSquarePlus />
                    Ask about it
                  </Button>
                )}
              </div>
            </motion.li>
          );
        })}
      </motion.ul>
    </div>
  );
}

/* ================================================================ */
/* Amendments & diff                                                 */
/* ================================================================ */

export function AmendmentsPanel({ analysis }: { analysis: Analysis }) {
  const reduce = useReducedMotion();
  const [left, setLeft] = React.useState(analysis.amendments[0]?.id ?? "");
  const [right, setRight] = React.useState(
    analysis.amendments[analysis.amendments.length - 1]?.id ?? "",
  );

  if (analysis.amendments.length === 0) {
    return (
      <EmptyState
        title="No amendments yet"
        description="When the agency posts one, run an Amendment Refresh and Margin will show only what moved — and flag it loudly if a deadline or a gate changed."
        action={
          <Button asChild variant="secondary">
            <Link href={`/app/analyses/${analysis.id}/run`}>Run an amendment refresh</Link>
          </Button>
        }
      />
    );
  }

  const target = analysis.amendments.find((a) => a.id === right) ?? analysis.amendments[0];
  const critical = target.changes.filter((c) => c.critical);

  return (
    <div className="space-y-5">
      <Panel>
        <PanelHeader
          title="Compare versions"
          description="Pick two points in the document's life and see only the difference."
        />
        <div className="flex flex-wrap items-end gap-3 px-5 py-5">
          <div className="min-w-44 flex-1">
            <p className="pb-1.5 text-sm font-medium text-ink">From</p>
            <Select value={left} onValueChange={setLeft}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {analysis.amendments.map((a) => (
                  <SelectItem key={a.id} value={a.id}>
                    {a.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <ArrowRight className="mb-2.5 size-4 shrink-0 text-ink-faint" aria-hidden />
          <div className="min-w-44 flex-1">
            <p className="pb-1.5 text-sm font-medium text-ink">To</p>
            <Select value={right} onValueChange={setRight}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {analysis.amendments.map((a) => (
                  <SelectItem key={a.id} value={a.id}>
                    {a.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </Panel>

      {critical.length > 0 ? (
        <Callout tone="seal" title={`${pluralize(critical.length, "change")} moved a deadline or a gate`}>
          {critical.map((c) => c.area).join(" · ")}
        </Callout>
      ) : null}

      <Panel>
        <PanelHeader title={target.label} description={`Issued ${longDate(target.issued)} · ${target.summary}`} />
        <motion.ul
          variants={staggerList()}
          initial={reduce ? false : "hidden"}
          animate="visible"
          className="divide-y divide-[var(--line)]"
        >
          {target.changes.map((change) => (
            <motion.li key={change.id} variants={listItem} className="px-5 py-4">
              <div className="flex flex-wrap items-center gap-2 pb-2">
                <DiffMark kind={change.kind} />
                <span className="font-mono text-xs text-ink-soft">{change.area}</span>
                {change.critical ? <Badge tone="seal">Critical</Badge> : null}
              </div>
              <div className="space-y-1.5">
                {change.before ? (
                  <p className="rounded-sm border-l-2 border-seal/45 bg-[var(--seal-tint)] px-3 py-1.5 text-sm leading-relaxed text-ink-soft line-through decoration-[color-mix(in_oklab,var(--seal)_50%,transparent)]">
                    {change.before}
                  </p>
                ) : null}
                {change.after ? (
                  <p className="rounded-sm border-l-2 border-leaf/45 bg-[var(--leaf-tint)] px-3 py-1.5 text-sm leading-relaxed text-ink">
                    {change.after}
                  </p>
                ) : null}
              </div>
            </motion.li>
          ))}
        </motion.ul>
      </Panel>
    </div>
  );
}

function DiffMark({ kind }: { kind: "added" | "changed" | "removed" }) {
  const config = {
    added: { tone: "leaf" as const, Icon: Plus, label: "Added" },
    changed: { tone: "ochre" as const, Icon: FileDiff, label: "Changed" },
    removed: { tone: "seal" as const, Icon: Minus, label: "Removed" },
  }[kind];
  return (
    <Badge tone={config.tone}>
      <config.Icon className="size-3" aria-hidden />
      {config.label}
    </Badge>
  );
}

/* ================================================================ */
/* Versions & activity                                               */
/* ================================================================ */

export function VersionsPanel({ analysis }: { analysis: Analysis }) {
  const allActivity = useReportsStore((s) => s.activity);
  const activity = allActivity.filter((a) => a.analysisId === analysis.id);

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Panel>
        <PanelHeader title="Version history" description="Every pass Margin made, and every human who changed it." />
        {analysis.versions.length === 0 ? (
          <div className="px-5 py-8 text-sm text-ink-faint">No versions recorded yet.</div>
        ) : (
          <ol className="px-5 py-5">
            {analysis.versions
              .slice()
              .reverse()
              .map((version, index, all) => (
                <li key={version.id} className="relative flex gap-4 pb-6 last:pb-0">
                  {index < all.length - 1 ? (
                    <span aria-hidden className="absolute left-[7px] top-4 h-[calc(100%-1rem)] w-px bg-line" />
                  ) : null}
                  <span
                    className={cn(
                      "relative z-10 mt-1.5 size-3.5 shrink-0 rounded-full border-2 border-[var(--paper-raised)]",
                      index === 0 ? "bg-patina" : "bg-[var(--line-strong)]",
                    )}
                  />
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-baseline gap-x-2.5">
                      <p className="text-sm font-medium text-ink">{version.label}</p>
                      <span className="font-mono text-2xs text-ink-faint">{relative(version.at)}</span>
                    </div>
                    <p className="text-sm leading-relaxed text-ink-soft">{version.note}</p>
                    <p className="text-2xs text-ink-faint">{version.author}</p>
                  </div>
                </li>
              ))}
          </ol>
        )}
      </Panel>

      <Panel>
        <PanelHeader title="Activity" description="Who touched what, and when." />
        {activity.length === 0 ? (
          <div className="px-5 py-8 text-sm text-ink-faint">No activity recorded for this analysis.</div>
        ) : (
          <ul className="divide-y divide-[var(--line)]">
            {activity.map((entry) => (
              <li key={entry.id} className="flex items-start gap-3 px-5 py-3">
                <Avatar name={entry.actor} size="xs" tone={entry.actor === "Margin" ? "patina" : "slate"} />
                <div className="min-w-0 flex-1">
                  <p className="text-sm leading-snug text-ink-soft">
                    <span className="font-medium text-ink">{entry.actor}</span> {entry.action}
                    {entry.target ? <span className="font-medium text-ink"> {entry.target}</span> : null}
                  </p>
                  <p className="text-2xs text-ink-faint">{relative(entry.at)}</p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}

export { QAndABuilder, ComplianceMatrix };
