"use client";

import * as React from "react";
import Link from "next/link";
import { motion, useReducedMotion } from "motion/react";
import { ArrowUpRight, Plus, Upload } from "lucide-react";

import { cn, formatCurrency, pluralize } from "@/lib/utils";
import { relative } from "@/lib/dates";
import { fadeUp, listItem, staggerList } from "@/lib/motion";
import { analysisHealth, portfolioStats, reviewQueue, upcomingDeadlines } from "@/lib/derive";
import { Button } from "@/components/ui/button";
import { Panel, PanelHeader, PageHeader } from "@/components/ui/surface";
import { EmptyState } from "@/components/ui/feedback";
import { Avatar } from "@/components/ui/controls";
import { GoNoGoGauge, MiniGauge, gateScore } from "@/components/domain/gauge";
import { DeadlineLine } from "@/components/domain/deadline";
import { CitationMeta, ConfidenceMeter, DocTypeBadge, StageBadge } from "@/components/domain/primitives";
import { useAnalysesStore } from "@/stores/analyses";
import { useMatrixStore } from "@/stores/matrix";
import { useReportsStore } from "@/stores/workspace";
import { useSessionStore } from "@/stores/session";
import { useUIStore } from "@/stores/ui";

export function DashboardView() {
  const reduce = useReducedMotion();
  const analyses = useAnalysesStore((s) => s.analyses);
  const rows = useMatrixStore((s) => s.rows);
  const activity = useReportsStore((s) => s.activity);
  const user = useSessionStore((s) => s.user);
  const setImportOpen = useUIStore((s) => s.setImportOpen);

  const stats = portfolioStats(analyses, rows);
  const deadlines = upcomingDeadlines(analyses, 5);
  const queue = reviewQueue(analyses).slice(0, 5);

  // The hero reads whichever live bid is closest to a decision it cannot make.
  const focus = React.useMemo(() => {
    const live = analyses.filter((a) => a.stage !== "decided" && a.gates.length > 0);
    if (live.length === 0) return analyses[0];
    return live.slice().sort((a, b) => {
      const aBlocked = a.gates.some((g) => g.weight === "hard" && g.met === false) ? 0 : 1;
      const bBlocked = b.gates.some((g) => g.weight === "hard" && g.met === false) ? 0 : 1;
      if (aBlocked !== bBlocked) return aBlocked - bBlocked;
      return gateScore(a.gates) - gateScore(b.gates);
    })[0];
  }, [analyses]);

  const firstName = (user?.name ?? "Amara Osei").split(" ")[0];

  return (
    <div className="mx-auto max-w-[80rem] space-y-8">
      <PageHeader
        eyebrow="Capture desk"
        title={`Good to see you, ${firstName}`}
        description={
          stats.blocked > 0
            ? `${pluralize(stats.blocked, "analysis", "analyses")} ${stats.blocked === 1 ? "is" : "are"} blocked on a hard gate, and ${stats.review} findings are still waiting on a human.`
            : `${stats.active} analyses in flight, ${stats.review} findings waiting on a human.`
        }
        actions={
          <>
            <Button variant="secondary" onClick={() => setImportOpen(true)}>
              <Upload />
              Import
            </Button>
            <Button asChild variant="primary">
              <Link href="/app/analyses/new">
                <Plus />
                New analysis
              </Link>
            </Button>
          </>
        }
      />

      <motion.div
        variants={staggerList(0.04)}
        initial={reduce ? false : "hidden"}
        animate="visible"
        className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
      >
        <Stat label="Active analyses" value={String(stats.active)} sub={`${stats.total} total`} />
        <Stat label="Pipeline value" value={formatCurrency(stats.pipeline)} sub="Estimated, active only" />
        <Stat
          label="Awaiting review"
          value={String(stats.review)}
          sub="Findings below threshold"
          tone={stats.review > 0 ? "ochre" : undefined}
        />
        <Stat
          label="Blocked on a gate"
          value={String(stats.blocked)}
          sub="Hard eligibility unmet"
          tone={stats.blocked > 0 ? "seal" : undefined}
        />
      </motion.div>

      <div className="grid gap-6 lg:grid-cols-[1.15fr_1fr]">
        {focus ? <GoNoGoHero analysisId={focus.id} /> : null}

        <div className="space-y-6">
          <Panel>
            <PanelHeader
              title="Next out the door"
              description="Countdowns run in the agency's timezone."
              actions={
                <Button asChild variant="quiet" size="sm">
                  <Link href="/app/deadlines">
                    All deadlines
                    <ArrowUpRight />
                  </Link>
                </Button>
              }
            />
            {deadlines.length === 0 ? (
              <div className="px-5 py-8 text-sm text-ink-faint">Nothing is due. Enjoy it while it lasts.</div>
            ) : (
              <ul className="divide-y divide-[var(--line)]">
                {deadlines.map((deadline) => (
                  <li key={`${deadline.analysisId}-${deadline.id}`} className="px-5 py-3.5">
                    <Link
                      href={`/app/analyses/${deadline.analysisId}`}
                      className="block rounded-sm transition-opacity duration-150 hover:opacity-85"
                    >
                      <DeadlineLine
                        at={deadline.at}
                        timezone={deadline.timezone}
                        label={deadline.label}
                        context={deadline.solicitationNumber}
                      />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel>
            <PanelHeader
              title="Review queue"
              description="Findings Margin is not confident enough to stand behind alone."
            />
            {queue.length === 0 ? (
              <div className="px-5 py-8 text-sm text-ink-faint">
                Nothing below the threshold. Every finding is carrying its own weight.
              </div>
            ) : (
              <ul className="divide-y divide-[var(--line)]">
                {queue.map((item) => (
                  <li key={item.finding.id} className="space-y-2.5 px-5 py-4">
                    <div className="flex items-baseline justify-between gap-3">
                      <div className="min-w-0">
                        <Link
                          href={`/app/analyses/${item.analysisId}`}
                          className="block truncate text-sm font-medium text-ink transition-colors duration-150 hover:text-patina"
                        >
                          {item.finding.label}
                        </Link>
                        <p className="mt-0.5 truncate font-mono text-2xs text-ink-faint">{item.solicitationNumber}</p>
                      </div>
                      <ConfidenceMeter confidence={item.finding.confidence} />
                    </div>
                    <p className="line-clamp-2 text-sm leading-relaxed text-ink-soft">{item.finding.value}</p>
                    <CitationMeta
                      citation={item.finding.citation}
                      analysisId={item.analysisId}
                      label={item.finding.label}
                      origin="Review queue"
                      clamp={2}
                    />
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Panel>
          <PanelHeader
            title="In flight"
            description="Everything that is not yet decided."
            actions={
              <Button asChild variant="quiet" size="sm">
                <Link href="/app/analyses">
                  Open board
                  <ArrowUpRight />
                </Link>
              </Button>
            }
          />
          {analyses.filter((a) => a.stage !== "decided").length === 0 ? (
            <div className="p-5">
              <EmptyState
                title="Nothing in flight"
                description="Upload a solicitation and Margin will read it end to end, then tell you what it found and what it could not find."
                action={
                  <Button asChild variant="primary">
                    <Link href="/app/analyses/new">
                      <Plus />
                      Start an analysis
                    </Link>
                  </Button>
                }
              />
            </div>
          ) : (
            <motion.ul
              variants={staggerList()}
              initial={reduce ? false : "hidden"}
              animate="visible"
              className="divide-y divide-[var(--line)]"
            >
              {analyses
                .filter((a) => a.stage !== "decided")
                .map((analysis) => {
                  const health = analysisHealth(analysis);
                  return (
                    <motion.li key={analysis.id} variants={listItem}>
                      <Link
                        href={`/app/analyses/${analysis.id}`}
                        className="group flex items-start gap-4 px-5 py-4 transition-colors duration-150 hover:bg-paper-sunk/60"
                      >
                        <div className="min-w-0 flex-1 space-y-1.5">
                          <div className="flex flex-wrap items-center gap-2">
                            <DocTypeBadge docType={analysis.docType} />
                            <StageBadge stage={analysis.stage} />
                            {health.hardGatesFailed > 0 ? (
                              <span className="font-mono text-2xs uppercase tracking-[0.1em] text-seal">
                                {pluralize(health.hardGatesFailed, "gate")} unmet
                              </span>
                            ) : null}
                          </div>
                          <p className="truncate text-base text-ink transition-colors duration-150 group-hover:text-patina">
                            {analysis.title}
                          </p>
                          <p className="truncate font-mono text-2xs text-ink-faint">
                            {analysis.solicitationNumber} · {analysis.agency} · {analysis.pageCount} pages
                          </p>
                        </div>
                        <div className="hidden shrink-0 flex-col items-end gap-2 sm:flex">
                          <MiniGauge gates={analysis.gates} decision={analysis.goNoGo} />
                          <span className="text-2xs text-ink-faint">
                            {health.needsReview > 0
                              ? `${health.needsReview} to review`
                              : `${health.findings} findings`}
                          </span>
                        </div>
                      </Link>
                    </motion.li>
                  );
                })}
            </motion.ul>
          )}
        </Panel>

        <Panel>
          <PanelHeader
            title="Recent activity"
            actions={
              <Button asChild variant="quiet" size="sm">
                <Link href="/app/activity">
                  Full trail
                  <ArrowUpRight />
                </Link>
              </Button>
            }
          />
          <ul className="divide-y divide-[var(--line)]">
            {activity.slice(0, 7).map((entry) => (
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
        </Panel>
      </div>
    </div>
  );
}

function GoNoGoHero({ analysisId }: { analysisId: string }) {
  const analysis = useAnalysesStore((s) => s.analyses.find((a) => a.id === analysisId));
  if (!analysis) return null;
  const blocking = analysis.gates.find((g) => g.weight === "hard" && g.met === false);
  const biggestRisk = analysis.risks.find((r) => r.severity === "critical") ?? analysis.risks[0];

  return (
    <motion.div variants={fadeUp} initial="hidden" animate="visible" data-coach="gauge">
      <Panel className="h-full overflow-hidden">
        <div className="flex flex-col gap-6 px-5 py-5 sm:flex-row sm:items-center">
          <div className="shrink-0 sm:w-52">
            <GoNoGoGauge gates={analysis.gates} decision={analysis.goNoGo} size="md" />
          </div>
          <div className="min-w-0 flex-1 space-y-3">
            <div className="space-y-1">
              <p className="eyebrow">Closest to a decision</p>
              <Link
                href={`/app/analyses/${analysis.id}`}
                className="block text-xl leading-snug text-ink transition-colors duration-150 hover:text-patina"
              >
                {analysis.title}
              </Link>
              <p className="font-mono text-2xs text-ink-faint">
                {analysis.solicitationNumber} · {analysis.agency}
              </p>
            </div>

            {blocking ? (
              <div className="rounded-md border border-line border-l-[3px] border-l-seal bg-[var(--seal-tint)] px-3.5 py-3">
                <p className="text-sm font-medium text-ink">{blocking.question}</p>
                <p className="mt-1 text-sm leading-relaxed text-ink-soft">{blocking.answer}</p>
                {blocking.citation ? (
                  <CitationMeta
                    className="mt-1"
                    citation={blocking.citation}
                    analysisId={analysis.id}
                    label="Blocking gate"
                    origin="Go / No-Go"
                    clamp={2}
                  />
                ) : null}
              </div>
            ) : biggestRisk ? (
              <div className="rounded-md border border-line border-l-[3px] border-l-ochre bg-[var(--ochre-tint)] px-3.5 py-3">
                <p className="text-sm font-medium text-ink">{biggestRisk.title}</p>
                <p className="mt-1 line-clamp-2 text-sm leading-relaxed text-ink-soft">{biggestRisk.narrative}</p>
              </div>
            ) : null}

            <Button asChild variant="secondary" size="sm">
              <Link href={`/app/analyses/${analysis.id}`}>
                Open the workspace
                <ArrowUpRight />
              </Link>
            </Button>
          </div>
        </div>
      </Panel>
    </motion.div>
  );
}

function Stat({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "seal" | "ochre" | "leaf";
}) {
  return (
    <motion.div variants={listItem}>
      <div className="rounded-lg border border-line bg-paper-raised px-4 py-3.5 shadow-[var(--shadow-raised)]">
        <p className="eyebrow">{label}</p>
        <p
          className={cn("mt-1.5 font-display text-2xl leading-none tabular", tone ? "" : "text-ink")}
          style={tone ? { color: `var(--${tone})` } : undefined}
        >
          {value}
        </p>
        {sub ? <p className="mt-1.5 text-xs text-ink-faint">{sub}</p> : null}
      </div>
    </motion.div>
  );
}
