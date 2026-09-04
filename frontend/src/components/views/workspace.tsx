"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { ChevronLeft, Download, Mail, MoreHorizontal, Copy, RefreshCw, Trash2 } from "lucide-react";

import { cn, pluralize } from "@/lib/utils";
import { analysisHealth, nextDeadlineFor } from "@/lib/derive";
import { Button, SplitButton } from "@/components/ui/button";
import { AvatarGroup, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/controls";
import {
  ConfirmDialog,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  Tooltip,
} from "@/components/ui/overlay";
import { EmptyState } from "@/components/ui/feedback";
import { Page, Split } from "@/components/ui/page";
import { MarginPane, MarginSheet } from "@/components/shell/margin-rail";
import { notify } from "@/components/ui/toaster";
import { MiniGauge } from "@/components/domain/gauge";
import { DocTypeBadge, STAGE_LABEL, STAGE_ORDER } from "@/components/domain/primitives";
import { DeadlineLine } from "@/components/domain/deadline";
import { WORKSPACE_TABS, type WorkspaceTabId } from "@/components/workspace/tabs";
import { CoveragePanel } from "@/components/workspace/coverage";
import { ResponseGapPanel } from "@/components/workspace/response-gap";
import { VerificationPanel } from "@/components/workspace/verification";
import {
  AmendmentsPanel,
  ComplianceMatrix,
  EvaluationPanel,
  FindingsPanel,
  GoNoGoPanel,
  OverviewPanel,
  QAndABuilder,
  RisksPanel,
  SilentPanel,
  ResearchPanel,
  VersionsPanel,
} from "@/components/workspace/panels";
import { useAnalysisData } from "@/hooks/use-workspace-data";
import { useAnalysesStore } from "@/stores/analyses";
import { useRowsFor } from "@/stores/matrix";
import { useQuestionsFor } from "@/stores/qa";
import { useReportsStore, useTemplatesStore } from "@/stores/workspace";
import { useUIStore } from "@/stores/ui";
import type { Analysis, Citation, Stage } from "@/types";

export function WorkspaceView({ analysisId }: { analysisId: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const reduce = useReducedMotion();
  const analysis = useAnalysesStore((s) => s.analyses.find((a) => a.id === analysisId));
  const setStage = useAnalysesStore((s) => s.setStage);
  const deleteAnalysis = useAnalysesStore((s) => s.deleteAnalysis);
  const restoreAnalysis = useAnalysesStore((s) => s.restoreAnalysis);
  const duplicateAnalysis = useAnalysesStore((s) => s.duplicateAnalysis);
  const matrixRows = useRowsFor(analysisId);
  const questions = useQuestionsFor(analysisId);
  const templates = useTemplatesStore((s) => s.templates);
  const generateReport = useReportsStore((s) => s.generate);
  const log = useReportsStore((s) => s.log);

  useAnalysisData(analysisId);

  // The query string is the single source of truth for the active section, so a
  // deep link, the back button, and a click on the rail all agree.
  const tabParam = searchParams.get("tab") as WorkspaceTabId | null;
  const tab: WorkspaceTabId =
    tabParam && WORKSPACE_TABS.some((t) => t.id === tabParam) ? tabParam : "go-no-go";
  const [confirmDelete, setConfirmDelete] = React.useState(false);

  // The Margin is never blank when there is something it could be showing.
  useOpeningCitation(analysis, tab);

  const setTab = React.useCallback(
    (next: WorkspaceTabId) => {
      router.replace(`/app/analyses/${analysisId}?tab=${next}`, { scroll: false });
    },
    [router, analysisId],
  );

  // [ and ] walk the sections without leaving the keyboard.
  React.useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (target?.tagName === "INPUT" || target?.tagName === "TEXTAREA" || target?.isContentEditable) return;
      if (event.key !== "[" && event.key !== "]") return;
      event.preventDefault();
      const index = WORKSPACE_TABS.findIndex((t) => t.id === tab);
      const next =
        event.key === "]"
          ? WORKSPACE_TABS[Math.min(WORKSPACE_TABS.length - 1, index + 1)]
          : WORKSPACE_TABS[Math.max(0, index - 1)];
      setTab(next.id);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [tab, setTab]);

  if (!analysis) {
    return (
      <div className="mx-auto max-w-2xl py-16">
        <EmptyState
          title="That analysis is gone"
          description="It may have been deleted, or the link may be from a different device. The board has everything that still exists."
          action={
            <Button asChild variant="primary">
              <Link href="/app/analyses">Back to the board</Link>
            </Button>
          }
        />
      </div>
    );
  }

  const health = analysisHealth(analysis);
  const next = nextDeadlineFor(analysis);
  const unsentQuestions = questions.filter((q) => !q.sent).length;
  const unassignedRows = matrixRows.filter((r) => r.status === "unassigned").length;

  // A gap in the reading is the one thing on this rail that invalidates
  // everything else, so it is counted the same way a failed hard gate is.
  // Derived from what the workspace already has, so the rail does not need a
  // second request to know whether anything is blocking.
  const verificationBlocking =
    (analysis.response?.summary?.blocking ?? 0) +
    (analysis.ledger?.invalidated?.length ?? 0) +
    (analysis.coverage?.totals.emptyDocuments ?? 0) +
    (analysis.gates ?? []).filter((g) => g.weight === "hard" && !g.answer).length;

  const coverageGaps =
    (analysis.coverage?.totals.chunksUnreached ?? 0) +
    (analysis.coverage?.totals.emptyDocuments ?? 0);

  const counts: Partial<Record<WorkspaceTabId, { value: number; tone: "seal" | "ochre" | "neutral" }>> = {
    "go-no-go": health.hardGatesFailed
      ? { value: health.hardGatesFailed, tone: "seal" }
      : undefined,
    // The queue's blocking count is the one number on this rail that means
    // "stop what you are doing". Everything else is a category of work.
    verify: verificationBlocking ? { value: verificationBlocking, tone: "seal" } : undefined,
    coverage: coverageGaps ? { value: coverageGaps, tone: "ochre" } : undefined,
    // Mandatory requirements the draft does not answer. Nothing else on
    // the rail outranks it once a response is bound.
    response: analysis.response?.summary?.blocking
      ? { value: analysis.response.summary.blocking, tone: "seal" }
      : undefined,
    matrix: unassignedRows ? { value: unassignedRows, tone: "ochre" } : undefined,
    risks: health.criticalRisks ? { value: health.criticalRisks, tone: "seal" } : undefined,
    questions: unsentQuestions ? { value: unsentQuestions, tone: "ochre" } : undefined,
    silent: analysis.silent.length ? { value: analysis.silent.length, tone: "neutral" } : undefined,
    amendments: analysis.amendments.length ? { value: analysis.amendments.length, tone: "neutral" } : undefined,
  };

  async function exportWith(templateName: string) {
    if (!analysis) return;
    const id = await generateReport(analysis.id, {
      templateName,
      format: "DOCX",
      destination: "download",
    });
    if (!id) {
      notify.error("The export could not be started.");
      return;
    }
    log({ actor: "You", action: `exported ${templateName} for`, target: analysis.solicitationNumber, analysisId: analysis.id });
    notify.success("Report queued.", {
      description: `${templateName} · DOCX — it appears under Reports once rendered.`,
      action: { label: "Reports", onClick: () => router.push("/app/reports") },
    });
  }

  return (
    <Page>
      <header className="shrink-0 border-b border-line bg-paper-raised">
        <div className="flex flex-wrap items-start justify-between gap-x-8 gap-y-4 px-6 pb-4 pt-5 lg:px-8">
          <div className="min-w-0 max-w-2xl">
            <div className="flex flex-wrap items-center gap-2 pb-2">
              <Button asChild variant="quiet" size="sm" className="-ml-2 h-6 px-1.5 text-xs">
                <Link href="/app/analyses">
                  <ChevronLeft />
                  All analyses
                </Link>
              </Button>
              <span className="text-ink-faint/50" aria-hidden>
                /
              </span>
              <DocTypeBadge docType={analysis.docType} />
              <span className="font-mono text-2xs text-ink-faint">{analysis.solicitationNumber}</span>
              <span className="text-ink-faint/60" aria-hidden>
                ·
              </span>
              <span className="text-xs text-ink-faint">{analysis.agency}</span>
            </div>
            <h1 className="display-tight truncate text-2xl leading-tight text-ink">{analysis.title}</h1>
            <div className="flex flex-wrap items-center gap-x-5 gap-y-2 pt-2.5">
              <MiniGauge gates={analysis.gates} decision={analysis.goNoGo} />
              <span className="text-xs text-ink-faint">
                {pluralize(health.findings, "finding")} · {pluralize(health.verified, "verified", "verified")}
                {health.needsReview > 0 ? ` · ${health.needsReview} to review` : ""}
              </span>
              <AvatarGroup names={[analysis.owner, ...analysis.collaborators]} />
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {next ? (
              <div className="mr-2 hidden min-w-44 lg:block">
                <DeadlineLine at={next.at} timezone={next.timezone} label={next.label} />
              </div>
            ) : null}

            <Select
              value={analysis.stage}
              onValueChange={(value) => {
                const previous = setStage(analysis.id, value as Stage);
                notify.success(`Moved to ${STAGE_LABEL[value as Stage]}.`, {
                  undo: previous ? () => setStage(analysis.id, previous) : undefined,
                });
              }}
            >
              <SelectTrigger className="w-36">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STAGE_ORDER.map((stage) => (
                  <SelectItem key={stage} value={stage}>
                    {STAGE_LABEL[stage]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <SplitButton
              onAction={() => exportWith(templates[0]?.name ?? "Full Solicitation Analysis")}
              menu={
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="primary" size="md" className="rounded-l-none px-2" aria-label="Export options">
                      <MoreHorizontal />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuLabel>Export with</DropdownMenuLabel>
                    {templates
                      .filter((t) => t.kind === "report")
                      .map((template) => (
                        <DropdownMenuItem key={template.id} onSelect={() => exportWith(template.name)}>
                          <Download />
                          {template.name}
                        </DropdownMenuItem>
                      ))}
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onSelect={() =>
                        notify.success("Report emailed.", {
                          description: "Sent via Outlook to the capture distribution list.",
                        })
                      }
                    >
                      <Mail />
                      Email via Outlook
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              }
            >
              <Download />
              Export
            </SplitButton>

            <DropdownMenu>
              <Tooltip content="More actions">
                <DropdownMenuTrigger asChild>
                  <Button variant="secondary" size="icon" aria-label="More actions">
                    <MoreHorizontal />
                  </Button>
                </DropdownMenuTrigger>
              </Tooltip>
              <DropdownMenuContent align="end">
                <DropdownMenuItem asChild>
                  <Link href={`/app/analyses/${analysis.id}/run`}>
                    <RefreshCw />
                    Re-read the document
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem
                  onSelect={() => {
                    duplicateAnalysis(analysis.id);
                    notify.success("Analysis duplicated.");
                  }}
                >
                  <Copy />
                  Duplicate
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem destructive onSelect={() => setConfirmDelete(true)}>
                  <Trash2 />
                  Delete analysis
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      <Split aside={<MarginPane />} width="24rem">
        {/* Below the split breakpoint the sections become a horizontal scroller
            above the content; above it they hold a rail of their own. */}
        <nav aria-label="Analysis sections" className="shrink-0 border-b border-line bg-paper-raised lg:hidden">
          <ul className="scrollbar-none flex gap-1 overflow-x-auto px-4 py-2">
            {WORKSPACE_TABS.map((item) => (
              <li key={item.id} className="shrink-0">
                <TabButton
                  item={item}
                  active={tab === item.id}
                  count={counts[item.id]}
                  reduce={Boolean(reduce)}
                  onSelect={() => setTab(item.id)}
                />
              </li>
            ))}
          </ul>
        </nav>

        <div className="flex min-h-0 flex-1">
          <nav
            aria-label="Analysis sections"
            className="scroll-region hidden w-56 shrink-0 border-r border-line bg-paper-raised px-3 py-4 lg:block"
          >
            <ul className="space-y-1">
              {WORKSPACE_TABS.map((item) => (
                <li key={item.id}>
                  <TabButton
                    item={item}
                    active={tab === item.id}
                    count={counts[item.id]}
                    reduce={Boolean(reduce)}
                    onSelect={() => setTab(item.id)}
                  />
                </li>
              ))}
            </ul>
          </nav>

          {/* The one region on this screen that scrolls. Everything framing it
              — identity, sections, the Margin — stays where it was put. */}
          {/* `@container` so the panels lay themselves out against the width
              they actually have. A viewport breakpoint would put two columns in
              this pane on a wide screen even when the Margin has taken most of
              the room. */}
          <div className="scroll-region @container min-h-0 min-w-0 flex-1 px-6 py-7 lg:px-8">
            <AnimatePresence mode="wait">
              <motion.div
                key={tab}
                initial={reduce ? { opacity: 0 } : { opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={reduce ? { opacity: 0 } : { opacity: 0, y: -4 }}
                transition={{ duration: 0.22, ease: [0.32, 0.72, 0, 1] }}
                className="mx-auto max-w-[64rem]"
              >
                {tab === "go-no-go" ? <GoNoGoPanel analysis={analysis} /> : null}
                {tab === "overview" ? <OverviewPanel analysis={analysis} /> : null}
                {tab === "verify" ? (
                  <VerificationPanel analysis={analysis} onOpenTab={(next) => setTab(next as WorkspaceTabId)} />
                ) : null}
                {tab === "coverage" ? <CoveragePanel analysis={analysis} /> : null}
                {tab === "response" ? <ResponseGapPanel analysis={analysis} /> : null}
                {tab === "scope" ? (
                  <FindingsPanel
                    analysis={analysis}
                    sections={[
                      { key: "scope", title: "Scope of work", description: "What is actually being bought." },
                      { key: "postAward", title: "Post-award obligations", description: "What follows the signature." },
                    ]}
                  />
                ) : null}
                {tab === "matrix" ? <ComplianceMatrix analysisId={analysis.id} /> : null}
                {tab === "legal" ? (
                  <FindingsPanel
                    analysis={analysis}
                    sections={[
                      {
                        key: "legal",
                        title: "Legal & regulatory",
                        description: "Statutes, standards, and the terms that are not negotiable.",
                      },
                    ]}
                  />
                ) : null}
                {tab === "evaluation" ? <EvaluationPanel analysis={analysis} /> : null}
                {tab === "risks" ? <RisksPanel analysis={analysis} /> : null}
                {tab === "questions" ? <QAndABuilder analysis={analysis} /> : null}
                {tab === "silent" ? <SilentPanel analysis={analysis} /> : null}
                {tab === "research" ? <ResearchPanel analysis={analysis} /> : null}
                {tab === "amendments" ? <AmendmentsPanel analysis={analysis} /> : null}
                {tab === "versions" ? <VersionsPanel analysis={analysis} /> : null}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </Split>

      <MarginSheet />

      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title="Delete this analysis?"
        destructive
        confirmLabel="Delete"
        description="Everything in this workspace goes with it. You will have a moment to undo."
        onConfirm={() => {
          const index = useAnalysesStore.getState().analyses.findIndex((a) => a.id === analysis.id);
          const removed = deleteAnalysis(analysis.id);
          router.push("/app/analyses");
          if (removed) {
            notify.success("Analysis deleted.", {
              description: removed.solicitationNumber,
              undo: () => restoreAnalysis(removed, index),
            });
          }
        }}
      />
    </Page>
  );
}

/**
 * The first citation a section can offer, so the Margin opens holding a real
 * clause instead of an instruction about clauses. A person who has pinned a
 * source, or pointed at one themselves, is left alone.
 */
function useOpeningCitation(analysis: Analysis | undefined, tab: WorkspaceTabId) {
  const peek = useUIStore((s) => s.peek);

  React.useEffect(() => {
    if (!analysis) return;
    const state = useUIStore.getState();
    if (state.pinned) return;

    const opening = firstCitationFor(analysis, tab);
    if (!opening) return;
    peek(opening);
    // Only when the section or the analysis changes — pointing at a different
    // finding inside a section must not be undone on the next render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analysis?.id, tab]);
}

function firstCitationFor(analysis: Analysis, tab: WorkspaceTabId) {
  const pick = (
    citation: Citation | undefined,
    label: string,
    origin: string,
  ) => (citation?.quote ? { citation, analysisId: analysis.id, label, origin } : undefined);

  switch (tab) {
    case "go-no-go": {
      const gate = analysis.gates.find((g) => g.citation?.quote);
      return gate ? pick(gate.citation, gate.question, "Go / No-Go") : undefined;
    }
    case "scope": {
      const finding = [...analysis.scope, ...analysis.postAward].find((f) => f.citation?.quote);
      return finding ? pick(finding.citation, finding.label, "Scope") : undefined;
    }
    case "legal": {
      const finding = analysis.legal.find((f) => f.citation?.quote);
      return finding ? pick(finding.citation, finding.label, "Legal & regulatory") : undefined;
    }
    case "evaluation": {
      const factor = analysis.evaluation.find((f) => f.citation?.quote);
      return factor ? pick(factor.citation, factor.name, "Evaluation") : undefined;
    }
    case "risks": {
      const risk = analysis.risks.find((r) => r.citation?.quote);
      return risk ? pick(risk.citation, risk.title, "Risk") : undefined;
    }
    case "overview": {
      const finding = analysis.identity.find((f) => f.citation?.quote);
      return finding ? pick(finding.citation, finding.label, "Overview") : undefined;
    }
    default:
      return undefined;
  }
}

/**
 * One section in the workspace rail. Shared by the vertical rail and the
 * horizontal scroller so the two can never drift apart.
 */
function TabButton({
  item,
  active,
  count,
  reduce,
  onSelect,
}: {
  item: (typeof WORKSPACE_TABS)[number];
  active: boolean;
  count?: { value: number; tone: "seal" | "ochre" | "neutral" };
  reduce: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-current={active ? "page" : undefined}
      className={cn(
        "relative flex w-full items-center justify-between gap-2 whitespace-nowrap rounded-md px-3 py-2 text-left text-sm",
        "transition-colors duration-150 ease-[cubic-bezier(0.32,0.72,0,1)]",
        active ? "text-ink" : "text-ink-soft hover:bg-paper-sunk hover:text-ink",
      )}
    >
      {active ? (
        <motion.span
          layoutId="workspace-tab"
          transition={reduce ? { duration: 0 } : { type: "spring", stiffness: 480, damping: 42 }}
          className="absolute inset-0 -z-10 rounded-md bg-patina-tint ring-1 ring-inset ring-[color-mix(in_oklab,var(--patina)_22%,transparent)]"
        />
      ) : null}
      <span className="truncate">{item.label}</span>
      {count ? (
        <span
          className="shrink-0 rounded-xs px-1.5 py-px font-mono text-2xs tabular"
          style={{
            color: count.tone === "neutral" ? "var(--ink-faint)" : `var(--${count.tone})`,
            backgroundColor:
              count.tone === "neutral"
                ? "var(--paper-sunk)"
                : `color-mix(in oklab, var(--${count.tone}) 12%, transparent)`,
          }}
        >
          {count.value}
        </span>
      ) : null}
    </button>
  );
}
