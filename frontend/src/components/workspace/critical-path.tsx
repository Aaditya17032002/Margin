"use client";

import * as React from "react";
import { AlertTriangle, CalendarClock, CheckCircle2, Clock } from "lucide-react";

import { cn, pluralize } from "@/lib/utils";
import { decisionApi } from "@/lib/api";
import { longDate } from "@/lib/dates";
import { Panel, PanelHeader, Well } from "@/components/ui/surface";
import { Callout, EmptyState } from "@/components/ui/feedback";
import { Badge } from "@/components/ui/badge";
import type { Analysis, CriticalPath, PathItem } from "@/types";

/**
 * What can still stop this response going out, in the order it will.
 *
 * A deadline list says the proposal is due in nine days. A task list says
 * forty things are open. Neither says the thing a capture manager actually
 * needs, which is which of the forty can still be finished and which one is
 * already too late.
 *
 * The distinction the view refuses to blur: **at risk** is slipping and
 * recoverable if somebody moves today; **past the point** means the date this
 * needed to start has gone, and either scope comes out or the deadline moves.
 * Both of those are decisions rather than tasks, and showing them the same
 * colour would hide that.
 */

const STATE: Record<
  PathItem["state"],
  { label: string; tone: "seal" | "ochre" | "leaf"; Icon: typeof Clock }
> = {
  "past the point": { label: "Past the point", tone: "seal", Icon: AlertTriangle },
  "at risk": { label: "At risk", tone: "ochre", Icon: Clock },
  clear: { label: "Clear", tone: "leaf", Icon: CheckCircle2 },
};

export function CriticalPathPanel({ analysis }: { analysis: Analysis }) {
  const [path, setPath] = React.useState<CriticalPath | null>(null);

  React.useEffect(() => {
    let live = true;
    decisionApi
      .path(analysis.id)
      .then((result) => {
        if (live) setPath(result);
      })
      .catch(() => {
        if (live) setPath(null);
      });
    return () => {
      live = false;
    };
  }, [analysis.id, analysis.updatedAt]);

  if (!path) {
    return <EmptyState title="Working the deadline backwards" description="One moment." />;
  }

  if (!path.submission) {
    return (
      <EmptyState
        title="No submission date to schedule against"
        description={path.notes[0] ?? "Set the proposal due date and this becomes a real path."}
      />
    );
  }

  const { summary } = path;

  return (
    <div className="space-y-5">
      {summary.blockingPastThePoint > 0 ? (
        <Callout
          tone="seal"
          title={`${pluralize(summary.blockingPastThePoint, "mandatory requirement")} is past the point it had to start`}
        >
          This is not a warning any more. Either scope comes out or the deadline moves, and both
          of those are conversations rather than tasks.
        </Callout>
      ) : summary.pastThePoint > 0 ? (
        <Callout tone="ochre" title={`${summary.pastThePoint} item(s) are past their start date`}>
          None of them is mandatory, so the bid is not at stake — but the schedule is no longer
          the one anybody agreed to.
        </Callout>
      ) : (
        <Callout tone="leaf" title="Everything can still be finished in time">
          On the dates the team has set, and assuming the review rounds that are open.
        </Callout>
      )}

      <Panel>
        <PanelHeader
          title="The chain to submission"
          description={`Due ${longDate(path.submission)}. Each gate is serial — a review cannot read a section nobody has drafted.`}
        />
        <ol className="divide-y divide-line">
          {path.steps.map((step) => (
            <li key={step.label} className="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-5 py-3">
              <span
                className={cn(
                  "w-32 shrink-0 font-mono text-xs tabular-nums",
                  step.state === "past the point" ? "text-seal" : "text-ink-soft",
                )}
              >
                {step.due ? longDate(step.due) : "—"}
              </span>
              <span className="text-sm text-ink">{step.label}</span>
              {step.state !== "clear" ? (
                <Badge tone={step.state === "past the point" ? "seal" : "ochre"}>{step.state}</Badge>
              ) : null}
              <span className="min-w-0 flex-1 text-xs leading-relaxed text-ink-faint">
                {step.detail}
              </span>
            </li>
          ))}
        </ol>
      </Panel>

      {path.notes.map((note) => (
        <Well key={note}>
          <p className="text-xs leading-relaxed text-ink-soft">{note}</p>
        </Well>
      ))}

      <Panel>
        <PanelHeader
          title="Requirements against the clock"
          description={`${summary.pastThePoint} past the point, ${summary.atRisk} at risk, ${summary.clear} clear.`}
        />
        {path.items.length === 0 ? (
          <p className="px-5 py-6 text-sm text-ink-soft">
            Nothing is outstanding. Every open requirement is complete or has no date to measure
            against.
          </p>
        ) : (
          <ul className="divide-y divide-line">
            {path.items.map((item) => {
              const state = STATE[item.state];
              return (
                <li
                  key={item.requirementId}
                  className="flex flex-col gap-2 px-5 py-3 @2xl:flex-row @2xl:items-start"
                >
                  <span
                    className={cn(
                      "mt-0.5 shrink-0 [&_svg]:size-4",
                      item.state === "past the point"
                        ? "text-seal"
                        : item.state === "at risk"
                          ? "text-[color-mix(in_oklab,var(--ochre)_82%,var(--ink))]"
                          : "text-ink-faint",
                    )}
                  >
                    <state.Icon />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs text-patina">{item.reference}</span>
                      <Badge tone={state.tone}>{state.label}</Badge>
                      {item.blocking ? <Badge tone="seal">Mandatory</Badge> : null}
                      {item.owner ? (
                        <Badge tone="neutral">{item.owner}</Badge>
                      ) : (
                        <Badge tone="ochre">Unowned</Badge>
                      )}
                      {item.latestStart ? (
                        <span className="flex items-center gap-1 font-mono text-2xs text-ink-faint">
                          <CalendarClock className="size-3" aria-hidden />
                          start by {longDate(item.latestStart)}
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-1 text-sm leading-relaxed text-ink">{item.text}</p>
                    <p className="mt-1 text-xs leading-relaxed text-ink-soft">{item.reason}</p>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </Panel>

      <Well>
        <p className="text-xs leading-relaxed text-ink-soft">
          <strong className="font-medium text-ink">Nothing here estimates how long work takes.</strong>{" "}
          It uses the dates your team set and the review rounds you have opened. A tool inventing a
          duration is a tool inventing a crisis, and the only thing worse than an unhelpful
          schedule is a confident wrong one.
        </p>
      </Well>
    </div>
  );
}
