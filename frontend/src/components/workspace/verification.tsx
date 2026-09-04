"use client";

import * as React from "react";
import {
  AlertTriangle,
  ArrowRight,
  CircleHelp,
  FileWarning,
  Layers,
  Quote,
  ScanLine,
  ShieldAlert,
} from "lucide-react";

import { cn, pluralize } from "@/lib/utils";
import { verificationApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Panel, PanelHeader, Well } from "@/components/ui/surface";
import { Callout, EmptyState } from "@/components/ui/feedback";
import { Badge } from "@/components/ui/badge";
import { CitationMeta } from "@/components/domain/primitives";
import type { Analysis, VerificationCorpus, VerificationItem, VerificationQueue } from "@/types";

/**
 * The verification queue.
 *
 * Every other tab shows what Margin concluded. This one shows what it could
 * not, which is the more useful list once a deadline is close. Items are
 * ordered by what it costs to be wrong rather than by where they came from,
 * because a scanned attachment nobody could read and an unsigned mandatory
 * requirement are the same kind of problem to whoever has to submit.
 *
 * Each row says four things: what needs deciding, why a machine could not
 * decide it, what happens if nobody does, and where to go. An item missing any
 * of those is noise in a list whose whole value is that everything in it is
 * real work.
 */

const KIND_ICON: Record<VerificationItem["kind"], typeof ScanLine> = {
  coverage: FileWarning,
  ledger: Layers,
  amendment: Layers,
  gate: ShieldAlert,
  citation: Quote,
  requirement: AlertTriangle,
  response: CircleHelp,
};

const SEVERITY: Record<
  VerificationItem["severity"],
  { label: string; tone: "seal" | "ochre" | "neutral"; blurb: string }
> = {
  blocking: {
    label: "Could lose the bid",
    tone: "seal",
    blurb: "Wrong here and the bid can be lost outright.",
  },
  important: {
    label: "Important",
    tone: "ochre",
    blurb: "Wrong here and a score suffers, or a claim turns out to rest on nothing.",
  },
  routine: {
    label: "Before submission",
    tone: "neutral",
    blurb: "Worth a look before submission, not before lunch.",
  },
};

export function VerificationPanel({
  analysis,
  onOpenTab,
}: {
  analysis: Analysis;
  onOpenTab?: (tab: string) => void;
}) {
  const [queue, setQueue] = React.useState<VerificationQueue | null>(null);
  const [error, setError] = React.useState("");

  React.useEffect(() => {
    let live = true;
    verificationApi
      .queue(analysis.id)
      .then((result) => {
        if (live) setQueue(result);
      })
      .catch(() => {
        if (live) setError("The queue could not be loaded.");
      });
    return () => {
      live = false;
    };
  }, [analysis.id, analysis.updatedAt]);

  if (error) {
    return <Callout tone="ochre" title="Could not load the queue">{error}</Callout>;
  }
  if (!queue) {
    return <EmptyState title="Working out what still needs a person" description="One moment." />;
  }
  if (queue.items.length === 0) {
    return (
      <EmptyState
        title="Nothing is waiting on a person"
        description="Every requirement has an owner, every mandatory answer has a signature, every claim is grounded in the document, and no page went unread. Re-check after the next run or the next amendment."
      />
    );
  }

  const groups: VerificationItem["severity"][] = ["blocking", "important", "routine"];

  return (
    <div className="space-y-5">
      <Panel>
        <PanelHeader
          title="What still needs a person"
          description="Ordered by what it costs to be wrong, not by where it came from."
        />
        <div className="grid grid-cols-3 gap-px bg-line">
          {groups.map((severity) => (
            <div key={severity} className="bg-paper-raised px-5 py-4">
              <p className="text-2xs font-medium uppercase tracking-[0.08em] text-ink-faint">
                {SEVERITY[severity].label}
              </p>
              <p
                className={cn(
                  "mt-1 font-mono text-2xl leading-none tabular-nums",
                  severity === "blocking" && "text-seal",
                  severity === "important" && "text-[color-mix(in_oklab,var(--ochre)_82%,var(--ink))]",
                  severity === "routine" && "text-ink",
                )}
              >
                {queue.summary[severity]}
              </p>
              <p className="mt-2 text-xs leading-relaxed text-ink-soft">{SEVERITY[severity].blurb}</p>
            </div>
          ))}
        </div>
      </Panel>

      {queue.summary.blocking > 0 ? (
        <Callout
          tone="seal"
          title={`${queue.summary.blocking} ${pluralize(queue.summary.blocking, "item")} could lose this bid`}
        >
          Nothing else in the workspace outranks these.
        </Callout>
      ) : (
        <Callout tone="leaf" title="Nothing here can lose the bid on its own">
          What is left changes a score or leaves a claim ungrounded. Both are worth an hour.
        </Callout>
      )}

      {groups.map((severity) => {
        const items = queue.items.filter((item) => item.severity === severity);
        if (!items.length) return null;
        return (
          <Panel key={severity}>
            <PanelHeader
              title={SEVERITY[severity].label}
              description={`${items.length} ${pluralize(items.length, "item")}`}
            />
            <ul className="divide-y divide-line">
              {items.map((item) => (
                <li key={item.id}>
                  <QueueRow analysis={analysis} item={item} onOpenTab={onOpenTab} />
                </li>
              ))}
            </ul>
          </Panel>
        );
      })}

      <Disagreement analysisId={analysis.id} />

      <Well>
        <p className="text-xs leading-relaxed text-ink-soft">
          <strong className="font-medium text-ink">This list is derived, never stored.</strong> Every
          item is read from the current state of the coverage ledger, the requirement ledger and the
          response trace, so settling something removes it here immediately. There is no second copy
          to reconcile, and nothing to mark done twice.
        </p>
      </Well>
    </div>
  );
}

/**
 * What happened last time somebody checked.
 *
 * Every confirmation and correction on this analysis is a labelled example
 * produced by somebody holding the document, and it is shown here for one
 * reason: to say whether the machine's answers on *this* solicitation have been
 * worth trusting. `wouldHaveShipped` counts corrections out of "answered" —
 * the ones that would have gone out in a proposal.
 *
 * It appears only once there is something to say. A panel reporting a 0%
 * correction rate over two judgements is worse than no panel.
 */
function Disagreement({ analysisId }: { analysisId: string }) {
  const [corpus, setCorpus] = React.useState<VerificationCorpus | null>(null);

  React.useEffect(() => {
    let live = true;
    verificationApi
      .corpus(analysisId)
      .then((result) => {
        if (live) setCorpus(result);
      })
      .catch(() => {
        if (live) setCorpus(null);
      });
    return () => {
      live = false;
    };
  }, [analysisId]);

  // Below this the rate is noise dressed as a measurement.
  if (!corpus || corpus.total < 5) return null;

  const worst = corpus.byRule.filter((bucket) => bucket.corrected > 0).slice(0, 4);

  return (
    <Panel>
      <PanelHeader
        title="How often the checks have been right here"
        description={`${corpus.total} ${pluralize(corpus.total, "judgement")} recorded on this analysis.`}
      />
      <div className="space-y-4 px-5 pb-5 pt-1">
        <p className="text-sm text-ink-soft tabular-nums">
          {corpus.confirmed} confirmed, {corpus.corrected} overruled, {corpus.flagged} flagged —{" "}
          a {(corpus.correctionRate * 100).toFixed(0)}% correction rate.
        </p>
        {corpus.wouldHaveShipped > 0 ? (
          <Callout tone="ochre" title={`${corpus.wouldHaveShipped} of those would have gone out`}>
            The check said the requirement was answered and a person found that it was not. Those
            are the corrections worth reading — not because somebody made a mistake, but because
            the check did.
          </Callout>
        ) : null}
        {worst.length ? (
          <div>
            <p className="text-2xs uppercase tracking-[0.08em] text-ink-faint">
              Most often overruled
            </p>
            <ul className="mt-2 space-y-1.5">
              {worst.map((bucket) => (
                <li key={bucket.name} className="flex items-center gap-3 text-xs">
                  <span className="w-40 shrink-0 font-mono text-2xs text-ink-soft">
                    {bucket.name.replace(/[._]/g, " ")}
                  </span>
                  <span className="h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-paper-sunk">
                    <span
                      className="block h-full rounded-full bg-[var(--ochre)]"
                      style={{ width: `${Math.max(2, Math.round(bucket.correctionRate * 100))}%` }}
                    />
                  </span>
                  <span className="w-28 shrink-0 text-right font-mono text-2xs text-ink-faint tabular-nums">
                    {bucket.corrected}/{bucket.total} overruled
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </Panel>
  );
}

function QueueRow({
  analysis,
  item,
  onOpenTab,
}: {
  analysis: Analysis;
  item: VerificationItem;
  onOpenTab?: (tab: string) => void;
}) {
  const Icon = KIND_ICON[item.kind] ?? CircleHelp;

  return (
    <div className="flex flex-col gap-3 px-5 py-4 @2xl:flex-row @2xl:items-start">
      <span className="mt-0.5 shrink-0 text-ink-faint [&_svg]:size-4">
        <Icon />
      </span>
      <div className="min-w-0 flex-1 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm leading-snug text-ink">{item.title}</span>
          {item.reference ? (
            <span className="font-mono text-2xs text-patina">{item.reference}</span>
          ) : null}
          {item.owner ? <Badge tone="neutral">{item.owner}</Badge> : null}
        </div>

        {item.detail ? (
          <p className="text-xs leading-relaxed text-ink-soft">{item.detail}</p>
        ) : null}

        <dl className="grid gap-x-6 gap-y-1 text-xs leading-relaxed @lg:grid-cols-2">
          <div>
            <dt className="text-2xs uppercase tracking-[0.08em] text-ink-faint">
              Why this needs you
            </dt>
            <dd className="text-ink-soft">{item.why}</dd>
          </div>
          <div>
            <dt className="text-2xs uppercase tracking-[0.08em] text-ink-faint">
              If nobody does
            </dt>
            <dd className="text-ink-soft">{item.consequence}</dd>
          </div>
        </dl>

        {item.citation?.quote ? (
          <CitationMeta
            citation={item.citation}
            analysisId={analysis.id}
            label={item.reference || item.title}
            origin="Verification"
            compact
            clamp={2}
          />
        ) : null}
      </div>

      {onOpenTab ? (
        <Button variant="secondary" size="sm" className="shrink-0" onClick={() => onOpenTab(item.tab)}>
          Go there <ArrowRight />
        </Button>
      ) : null}
    </div>
  );
}
