"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { ArrowRight, Check } from "lucide-react";

import { AGENT_BY_ID, MODE_BY_ID } from "@/data/agents";
import { analysesApi, streamEvents, type RunEvent } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Panel } from "@/components/ui/surface";
import { Callout } from "@/components/ui/feedback";
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
 * Watching an expert work, not watching a spinner. The roster, the reasoning
 * ticker and the findings all come from the backend's event stream for this
 * run — nothing here is simulated, so if an agent is slow the page is slow with
 * it, and if a run fails the page says so.
 */
export function RunAnalysisView({ analysisId }: { analysisId: string }) {
  const router = useRouter();
  const reduce = useReducedMotion();
  const analysis = useAnalysesStore((s) => s.analyses.find((a) => a.id === analysisId));
  const refreshAnalysis = useAnalysesStore((s) => s.refreshOne);
  const loadMatrix = useMatrixStore((s) => s.load);
  const loadQuestions = useQAStore((s) => s.load);
  const loadNotifications = useNotificationsStore((s) => s.load);
  const loadReports = useReportsStore((s) => s.load);

  const [phases, setPhases] = React.useState<Record<string, AgentPhase>>({});
  const [lines, setLines] = React.useState<{ id: string; text: string; agent: string }[]>([]);
  const [surfaced, setSurfaced] = React.useState<Finding[]>([]);
  const [ranToCompletion, setRanToCompletion] = React.useState(false);
  const [failure, setFailure] = React.useState<string | null>(null);
  const started = React.useRef(false);
  const settled = React.useRef(false);

  const agents: AgentId[] = analysis ? MODE_BY_ID[analysis.mode].agents : [];

  // Arriving at a finished read — a refresh, or a back button — should show the
  // finished state immediately rather than waiting on a stream that is over.
  const alreadyRead = Boolean(analysis && analysis.identity.length > 0);
  const finished = ranToCompletion || alreadyRead;

  const done = agents.filter((id) => phases[id] === "done").length;
  const progress = finished ? 100 : agents.length ? (done / agents.length) * 100 : 0;

  React.useEffect(() => {
    if (!analysis || alreadyRead) return;

    // Subscription and polling are set up on every run of this effect and torn
    // down by its cleanup — a ref guard here would survive React re-mounting
    // the component and leave the room permanently deaf. Only the request to
    // start the run is guarded, because that one must not happen twice.

    // The stream is opened, and *acknowledged*, before the run is asked for.
    // The channel has no replay: an agent that starts before the subscription
    // lands is an agent that never appears to have run at all.
    const stream = streamEvents(
      `/api/v1/analyses/${analysisId}/events`,
      (event) => handleEvent(event),
      (error) => setFailure(error instanceof Error ? error.message : "The event stream dropped."),
      { readyEvent: "stream_ready" },
    );

    void stream.ready.then(() => {
      if (started.current) return;
      started.current = true;
      return analysesApi.run(analysisId).catch((error: unknown) => {
        setFailure(error instanceof Error ? error.message : "The analysis could not be started.");
      });
    });

    // A dropped connection must not leave the room waiting forever, so the
    // analysis itself is the second opinion on whether the read is over.
    const poll = window.setInterval(async () => {
      const current = await refreshAnalysis(analysisId);
      if (current && current.stage !== "analyzing" && current.identity.length > 0) {
        window.clearInterval(poll);
        void finish();
      }
    }, 3000);

    return () => {
      stream.stop();
      window.clearInterval(poll);
    };

    function handleEvent(event: RunEvent) {
      const agent = typeof event.agent === "string" ? event.agent : "orchestrator";

      switch (event.event) {
        case "agent_started":
          setPhases((p) => ({ ...p, [agent]: "reading" }));
          break;

        case "reasoning_tick":
          if (typeof event.text === "string") {
            const text = event.text;
            setLines((current) => [
              ...current,
              {
                id: `${agent}-${current.length}`,
                text,
                agent: AGENT_BY_ID[agent as AgentId]?.name ?? agent,
              },
            ]);
          }
          break;

        case "finding_emitted":
          if (isFinding(event.finding)) {
            const finding = event.finding;
            setSurfaced((current) =>
              current.some((f) => f.id === finding.id) ? current : [...current, finding],
            );
          }
          break;

        case "agent_completed":
          setPhases((p) => ({ ...p, [agent]: "done" }));
          break;

        case "run_completed":
          void finish();
          break;

        case "run_error":
          setFailure(typeof event.error === "string" ? event.error : "The read failed.");
          break;
      }
    }

    async function finish() {
      // Both the stream and the poll can get here; only the first one counts.
      if (settled.current) return;
      settled.current = true;

      // The worker has already committed by the time it publishes this, so a
      // reload here reads the finished analysis rather than a half-written one.
      const fresh = await refreshAnalysis(analysisId);
      await Promise.all([
        loadMatrix(analysisId, { force: true }),
        loadQuestions(analysisId, { force: true }),
        loadNotifications({ force: true }),
        loadReports({ force: true }),
      ]);
      setRanToCompletion(true);
      notify.success("Analysis complete.", {
        description: fresh?.summary || "Every finding is cited and ready to verify.",
      });
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
      <ReadingProgress value={progress} />

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

        {failure ? (
          <Callout tone="seal" title="The read stopped">
            {failure} Nothing was written to the analysis — you can start it again from the board.
          </Callout>
        ) : null}

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
                        analysisId={analysis.id}
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

/** The stream carries whatever the agent emitted; only render what is shaped
 *  like a finding with a citation behind it. */
function isFinding(value: unknown): value is Finding {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Partial<Finding>;
  return (
    typeof candidate.id === "string" &&
    typeof candidate.label === "string" &&
    typeof candidate.value === "string" &&
    typeof candidate.citation === "object" &&
    candidate.citation !== null
  );
}
