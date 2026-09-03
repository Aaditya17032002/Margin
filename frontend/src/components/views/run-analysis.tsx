"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { ArrowRight, Check } from "lucide-react";

import { AGENT_BY_ID, MODE_BY_ID } from "@/data/agents";
import { seedAnalyses } from "@/data";
import { Button } from "@/components/ui/button";
import { Panel } from "@/components/ui/surface";
import { notify } from "@/components/ui/toaster";
import { AgentRoster, ReadingProgress, ReasoningTicker, type AgentPhase } from "@/components/domain/reading-room";
import { CitationMeta, StakesBadge } from "@/components/domain/primitives";
import { Wordmark } from "@/components/domain/marks";
import { useAnalysesStore } from "@/stores/analyses";
import { useMatrixStore } from "@/stores/matrix";
import { useQAStore } from "@/stores/qa";
import { useNotificationsStore, useReportsStore } from "@/stores/workspace";
import type { AgentId, Finding } from "@/types";

/**
 * Watching an expert work, not watching a spinner. Each agent takes the floor
 * in turn, its reasoning streams a line at a time, and the findings it produces
 * settle into the page as they are confirmed. When the roster finishes, the
 * seeded analysis is grafted onto the new record and the workspace opens.
 */
export function RunAnalysisView({ analysisId }: { analysisId: string }) {
  const router = useRouter();
  const reduce = useReducedMotion();
  const analysis = useAnalysesStore((s) => s.analyses.find((a) => a.id === analysisId));
  const updateAnalysis = useAnalysesStore((s) => s.updateAnalysis);
  const addRow = useMatrixStore((s) => s.addRow);
  const addQuestion = useQAStore((s) => s.addQuestion);
  const pushNotification = useNotificationsStore((s) => s.push);
  const log = useReportsStore((s) => s.log);

  const [phases, setPhases] = React.useState<Record<string, AgentPhase>>({});
  const [lines, setLines] = React.useState<{ id: string; text: string; agent: string }[]>([]);
  const [surfaced, setSurfaced] = React.useState<Finding[]>([]);
  const [progress, setProgress] = React.useState(0);
  const [ranToCompletion, setRanToCompletion] = React.useState(false);
  const started = React.useRef(false);

  const agents: AgentId[] = analysis ? MODE_BY_ID[analysis.mode].agents : [];

  // Arriving at a finished read — a refresh, or a back button — should show the
  // finished state immediately rather than replaying the performance.
  const alreadyRead = Boolean(analysis && analysis.identity.length > 0);
  const finished = ranToCompletion || alreadyRead;

  // A blank analysis borrows the shape of a seeded one so the theatre has real
  // material to stream; which template is used depends on the document type.
  const template = React.useMemo(() => {
    if (!analysis) return seedAnalyses[0];
    return (
      seedAnalyses.find((a) => a.docType === analysis.docType) ??
      seedAnalyses.find((a) => a.id !== analysis.id) ??
      seedAnalyses[0]
    );
  }, [analysis]);

  React.useEffect(() => {
    if (!analysis || started.current || agents.length === 0 || alreadyRead) return;
    started.current = true;

    const timers: number[] = [];
    const perAgent = reduce ? 320 : 1100;
    const templateFindings = [
      ...template.identity,
      ...template.scope,
      ...template.legal,
      ...template.eligibility,
    ];

    updateAnalysis(analysis.id, { stage: "analyzing" });

    agents.forEach((agentId, index) => {
      const start = index * perAgent;
      timers.push(
        window.setTimeout(() => {
          setPhases((p) => ({ ...p, [agentId]: "reading" }));
          setProgress(((index + 0.15) / agents.length) * 100);
        }, start),
      );

      const agentLines = AGENT_BY_ID[agentId].lines;
      agentLines.forEach((text, lineIndex) => {
        timers.push(
          window.setTimeout(
            () => {
              setLines((current) => [
                ...current,
                { id: `${agentId}-${lineIndex}`, text, agent: AGENT_BY_ID[agentId].name },
              ]);
            },
            start + 90 + (lineIndex * perAgent) / (agentLines.length + 0.6),
          ),
        );
      });

      // Findings settle in as the agent that produced them finishes.
      const share = Math.ceil(templateFindings.length / agents.length);
      const slice = templateFindings.slice(index * share, (index + 1) * share);
      slice.forEach((finding, i) => {
        timers.push(
          window.setTimeout(
            () => setSurfaced((current) => [...current, finding]),
            start + perAgent * 0.55 + i * 120,
          ),
        );
      });

      timers.push(
        window.setTimeout(() => {
          setPhases((p) => ({ ...p, [agentId]: "done" }));
          setProgress(((index + 1) / agents.length) * 100);
        }, start + perAgent * 0.94),
      );
    });

    timers.push(
      window.setTimeout(
        () => {
          graft();
          setRanToCompletion(true);
          setProgress(100);
        },
        agents.length * perAgent + 320,
      ),
    );

    return () => timers.forEach(window.clearTimeout);

    function graft() {
      if (!analysis) return;
      updateAnalysis(analysis.id, {
        stage: "review",
        summary: template.summary,
        identity: template.identity.map((f) => ({ ...f, id: `${analysis.id}_${f.id}` })),
        scope: template.scope.map((f) => ({ ...f, id: `${analysis.id}_${f.id}` })),
        legal: template.legal.map((f) => ({ ...f, id: `${analysis.id}_${f.id}` })),
        eligibility: template.eligibility.map((f) => ({ ...f, id: `${analysis.id}_${f.id}` })),
        pricing: template.pricing.map((f) => ({ ...f, id: `${analysis.id}_${f.id}` })),
        postAward: template.postAward.map((f) => ({ ...f, id: `${analysis.id}_${f.id}` })),
        gates: template.gates.map((g) => ({ ...g, id: `${analysis.id}_${g.id}` })),
        evaluation: template.evaluation,
        risks: template.risks,
        silent: template.silent,
        dates: template.dates,
        clins: template.clins,
        pages: template.pages,
        naics: template.naics,
        setAside: template.setAside,
        placeOfPerformance: template.placeOfPerformance,
        estimatedValue: template.estimatedValue,
        pageCount: template.pageCount,
        agency: analysis.agency === "Pending intake" ? template.agency : analysis.agency,
        versions: [
          {
            id: `${analysis.id}_v1`,
            label: `${MODE_BY_ID[analysis.mode].name} pass`,
            at: new Date().toISOString(),
            author: "Margin",
            note: `${templateFindings.length} findings extracted, every one verified against its clause.`,
          },
        ],
      });

      // Compliance and questions are produced by their own agents, so they only
      // appear when those agents were part of the mode.
      if (agents.includes("compliance")) {
        const rows = useMatrixStore
          .getState()
          .rows.filter((r) => r.analysisId === template.id)
          .slice(0, 16);
        for (const row of rows) {
          addRow({ ...row, analysisId: analysis.id, owner: null, responseLocation: "", status: "unassigned" });
        }
      }
      if (agents.includes("qa")) {
        const questions = useQAStore
          .getState()
          .questions.filter((q) => q.analysisId === template.id)
          .slice(0, 8);
        for (const question of questions) {
          addQuestion({
            analysisId: analysis.id,
            text: question.text,
            rationale: question.rationale,
            sourceKind: question.sourceKind,
            goNoGoImpact: question.goNoGoImpact,
            citation: question.citation,
          });
        }
      }

      pushNotification({
        kind: "review",
        title: "Analysis complete",
        body: `${analysis.title} has been read. ${template.gates.filter((g) => g.weight === "hard" && g.met === false).length} hard gates need attention.`,
        analysisId: analysis.id,
        href: `/app/analyses/${analysis.id}`,
      });
      log({ actor: "Margin", action: "completed the reading of", target: analysis.title, analysisId: analysis.id });
      notify.success("Analysis complete.", { description: "Every finding is cited and ready to verify." });
    }
    // The choreography runs exactly once per analysis.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analysis?.id]);

  if (!analysis) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <p className="text-sm text-ink-faint">That analysis is no longer here.</p>
      </div>
    );
  }

  const mode = MODE_BY_ID[analysis.mode];

  return (
    <div className="relative min-h-[calc(100dvh-3.5rem)] bg-paper px-5 py-8 lg:px-10">
      <ReadingProgress value={finished ? 100 : progress} />

      <div className="mx-auto max-w-[74rem] space-y-8">
        <header className="space-y-2">
          <div className="flex items-center gap-2.5">
            <Wordmark showText={false} />
            <p className="eyebrow">The reading room</p>
          </div>
          <h1 className="display-tight text-3xl text-ink">{analysis.title}</h1>
          <p className="text-sm text-ink-soft">
            {mode.name} · {mode.passes} · {analysis.fileName}
          </p>
        </header>

        <div className="grid gap-6 lg:grid-cols-[22rem_1fr]">
          <div className="space-y-6">
            <Panel className="px-5 py-5">
              <p className="eyebrow pb-4">Roster</p>
              <AgentRoster agents={agents} phases={phases} />
            </Panel>

            <Panel className="overflow-hidden px-5 py-4">
              <p className="eyebrow pb-2">Reasoning</p>
              <ReasoningTicker lines={lines} />
            </Panel>
          </div>

          <Panel className="min-h-[32rem]">
            <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-3.5">
              <p className="eyebrow">Findings as they settle</p>
              <span className="font-mono text-2xs tabular text-ink-faint">{surfaced.length}</span>
            </div>

            <div className="px-5 py-2">
              <AnimatePresence initial={false}>
                {surfaced.map((finding, index) => (
                  <motion.div
                    key={`${finding.id}-${index}`}
                    initial={reduce ? { opacity: 0 } : { opacity: 0, y: 14, filter: "blur(3px)" }}
                    animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                    transition={{
                      type: "spring",
                      stiffness: 340,
                      damping: 34,
                      delay: reduce ? 0 : 0.02,
                    }}
                    className="grid gap-x-5 gap-y-2 border-b border-line py-4 last:border-b-0 sm:grid-cols-[10rem_1fr]"
                  >
                    <div className="space-y-1.5">
                      <p className="text-sm font-medium text-ink-soft">{finding.label}</p>
                      <StakesBadge stakes={finding.stakes} />
                    </div>
                    <div className="min-w-0 space-y-3">
                      <p
                        className="ink-confidence text-sm leading-relaxed"
                        style={{ "--confidence": finding.confidence } as React.CSSProperties}
                      >
                        {finding.value}
                      </p>
                      <CitationMeta
                        citation={finding.citation}
                        analysisId={template.id}
                        label={finding.label}
                        origin="Reading room"
                        clamp={2}
                      />
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {surfaced.length === 0 ? (
                <div className="flex min-h-72 flex-col items-center justify-center gap-3 text-center">
                  <motion.div
                    animate={reduce ? undefined : { opacity: [0.4, 1, 0.4] }}
                    transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
                    className="font-mono text-2xs uppercase tracking-[0.16em] text-ink-faint"
                  >
                    opening the document
                  </motion.div>
                  <p className="max-w-xs text-sm leading-relaxed text-ink-faint">
                    Nothing appears here until a finding can point at the line it came from.
                  </p>
                </div>
              ) : null}
            </div>
          </Panel>
        </div>

        <AnimatePresence>
          {finished ? (
            <motion.div
              initial={reduce ? { opacity: 0 } : { opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
              className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-line border-l-[3px] border-l-leaf bg-[var(--leaf-tint)] px-5 py-4"
            >
              <div className="flex items-start gap-3">
                <Check className="mt-0.5 size-4 shrink-0 text-leaf" aria-hidden />
                <div>
                  <p className="text-sm font-medium text-ink">The read is finished.</p>
                  <p className="text-sm text-ink-soft">
                    Every claim resolves to a page and a section. What the document never said is waiting in the SILENT ledger.
                  </p>
                </div>
              </div>
              <Button variant="primary" onClick={() => router.push(`/app/analyses/${analysis.id}`)}>
                Open the workspace
                <ArrowRight />
              </Button>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
    </div>
  );
}
