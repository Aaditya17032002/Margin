"use client";

import * as React from "react";
import { AlertTriangle, Award, BookOpen, Check, Copy, History } from "lucide-react";

import { cn } from "@/lib/utils";
import { memoryApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tooltip } from "@/components/ui/overlay";
import { notify } from "@/components/ui/toaster";
import type { ContentSuggestion, MatrixRow, PastPerformanceMatch } from "@/types";

/**
 * What the organisation already knows, offered where a requirement is being
 * worked rather than in a library nobody opens at 2am.
 *
 * The rule both halves obey: never hand somebody text or a claim without the
 * context that decides whether to use it. A paragraph that answered L.4.2 on a
 * won bid and was signed off by a named person is a completely different thing
 * from some old text about quality control, and a matrix that showed them the
 * same way would be worse than showing neither.
 */
export function RequirementMemory({
  analysisId,
  row,
}: {
  analysisId: string;
  row: MatrixRow;
}) {
  const [open, setOpen] = React.useState(false);
  const [content, setContent] = React.useState<ContentSuggestion[] | null>(null);
  const [performance, setPerformance] = React.useState<PastPerformanceMatch[] | null>(null);

  React.useEffect(() => {
    if (!open) return;
    let live = true;
    Promise.allSettled([
      memoryApi.content(analysisId, row.id),
      memoryApi.pastPerformance(analysisId, row.id),
    ]).then(([blocks, records]) => {
      if (!live) return;
      setContent(blocks.status === "fulfilled" ? blocks.value : []);
      setPerformance(records.status === "fulfilled" ? records.value : []);
    });
    return () => {
      live = false;
    };
  }, [analysisId, row.id, open]);

  if (!open) {
    return (
      <Button variant="quiet" size="sm" onClick={() => setOpen(true)}>
        <History /> Have we done this before?
      </Button>
    );
  }

  const nothing = content?.length === 0 && performance?.length === 0;

  return (
    <div className="mt-2 space-y-3 rounded-sm border border-line bg-paper-sunk p-3">
      {content === null ? (
        <p className="text-xs text-ink-faint">Looking…</p>
      ) : nothing ? (
        <p className="text-xs leading-relaxed text-ink-soft">
          Nothing in the library answers a requirement like this, and no past contract is close
          enough to put forward. That is a fact about the library rather than about the
          requirement — worth adding to once this response is written.
        </p>
      ) : null}

      {content?.length ? (
        <div className="space-y-2">
          <p className="flex items-center gap-1.5 text-2xs uppercase tracking-[0.08em] text-ink-faint">
            <BookOpen className="size-3" aria-hidden />
            Text that answered something like this
          </p>
          {content.map((block) => (
            <Block key={block.blockId} block={block} />
          ))}
        </div>
      ) : null}

      {performance?.length ? (
        <div className="space-y-2">
          <p className="flex items-center gap-1.5 text-2xs uppercase tracking-[0.08em] text-ink-faint">
            <Award className="size-3" aria-hidden />
            Contracts that might support this
          </p>
          {performance.map((match) => (
            <Relevance key={match.recordId} match={match} />
          ))}
        </div>
      ) : null}

      <Button variant="quiet" size="sm" onClick={() => setOpen(false)}>
        Close
      </Button>
    </div>
  );
}

const OUTCOME_TONE: Record<ContentSuggestion["outcome"], "leaf" | "seal" | "neutral"> = {
  won: "leaf",
  lost: "seal",
  no_award: "neutral",
  withdrawn: "neutral",
  unknown: "neutral",
};

function Block({ block }: { block: ContentSuggestion }) {
  const [expanded, setExpanded] = React.useState(false);

  return (
    <div className="rounded-sm border border-line bg-paper-raised p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-ink">{block.title}</span>
        <Badge tone={OUTCOME_TONE[block.outcome]} shape="mono">
          {block.outcome.replace("_", " ")}
        </Badge>
        {block.verifiedBy ? (
          <Badge tone="leaf">
            <Check className="size-3" aria-hidden />
            Verified
          </Badge>
        ) : null}
        {block.timesUsed ? (
          <span className="text-2xs text-ink-faint">used {block.timesUsed}×</span>
        ) : null}
      </div>

      {/* The sentence that makes this worth offering rather than just similar. */}
      <p className="mt-1.5 text-2xs leading-relaxed text-ink-soft">{block.provenance}</p>

      {block.cautions.length ? (
        <ul className="mt-1.5 space-y-0.5">
          {block.cautions.map((caution) => (
            <li
              key={caution}
              className="flex items-start gap-1.5 text-2xs leading-relaxed text-[color-mix(in_oklab,var(--ochre)_82%,var(--ink))]"
            >
              <AlertTriangle className="mt-0.5 size-3 shrink-0" aria-hidden />
              {caution}
            </li>
          ))}
        </ul>
      ) : null}

      <p
        className={cn(
          "mt-2 whitespace-pre-wrap text-xs leading-relaxed text-ink",
          expanded ? "" : "line-clamp-3",
        )}
      >
        {block.text}
      </p>

      <div className="mt-2 flex gap-2">
        <Button variant="quiet" size="sm" onClick={() => setExpanded((value) => !value)}>
          {expanded ? "Less" : "Read it all"}
        </Button>
        <Button
          variant="quiet"
          size="sm"
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(block.text);
              await memoryApi.useBlock(block.blockId);
              notify.success("Copied.", {
                description: "Recorded as used, so the library knows this text is still in play.",
              });
            } catch {
              notify.error("It could not be copied.");
            }
          }}
        >
          <Copy /> Copy
        </Button>
      </div>
    </div>
  );
}

function Relevance({ match }: { match: PastPerformanceMatch }) {
  return (
    <div className="rounded-sm border border-line bg-paper-raised p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-ink">{match.record.title}</span>
        {match.record.ongoing ? <Badge tone="leaf">Current</Badge> : null}
        {match.record.value ? (
          <span className="font-mono text-2xs text-ink-faint">
            ${match.record.value.toLocaleString()}
          </span>
        ) : null}
      </div>

      {/* Each signal separately: the case, not the number. */}
      <ul className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1">
        {Object.entries(match.signals).map(([name, signal]) => (
          <li key={name}>
            <Tooltip content={signal.detail ?? (signal.shared ?? []).join(", ")}>
              <span className="text-2xs text-ink-soft">
                <span className="uppercase tracking-[0.08em] text-ink-faint">{name}</span>{" "}
                {Math.round(signal.score * 100)}%
              </span>
            </Tooltip>
          </li>
        ))}
      </ul>

      {match.concerns.length ? (
        <ul className="mt-1.5 space-y-0.5">
          {match.concerns.map((concern) => (
            <li
              key={concern}
              className="flex items-start gap-1.5 text-2xs leading-relaxed text-[color-mix(in_oklab,var(--ochre)_82%,var(--ink))]"
            >
              <AlertTriangle className="mt-0.5 size-3 shrink-0" aria-hidden />
              {concern}
            </li>
          ))}
        </ul>
      ) : null}

      {match.record.reference.name ? (
        <p className="mt-1.5 text-2xs text-ink-faint">
          Reference: {match.record.reference.name}
          {match.record.reference.title ? `, ${match.record.reference.title}` : ""}
        </p>
      ) : null}
    </div>
  );
}
