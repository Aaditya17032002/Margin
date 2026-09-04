"use client";

import * as React from "react";
import { AlertTriangle, ArrowRight, Check, MessageSquarePlus } from "lucide-react";

import { cn, pluralize } from "@/lib/utils";
import { contradictionsApi } from "@/lib/api";
import { relative } from "@/lib/dates";
import { Button } from "@/components/ui/button";
import { Panel, PanelHeader, Well } from "@/components/ui/surface";
import { Callout, EmptyState } from "@/components/ui/feedback";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/input";
import { notify } from "@/components/ui/toaster";
import { CitationMeta } from "@/components/domain/primitives";
import type { Analysis, Contradiction, ContradictionSide } from "@/types";

/**
 * Requirements that cannot both be met.
 *
 * Everywhere else in the workspace, a problem is something Margin found in the
 * document. Here the document is the problem: both clauses were extracted
 * correctly and they disagree with each other, which is why no amount of
 * reading the response can settle it.
 *
 * The two clauses are shown side by side, at equal weight, with a
 * recommendation underneath rather than a pre-selected answer. Choosing for the
 * team would be choosing which requirement they write to.
 */

const DIMENSION_LABEL: Record<string, string> = {
  page_limit: "Page limit",
  word_limit: "Word limit",
  font_size: "Font size",
  margin: "Margins",
  file_size: "File size",
  copies: "Copies",
  deadline: "Deadline",
  permission: "Forbidden vs permitted",
};

export function ContradictionsPanel({ analysis }: { analysis: Analysis }) {
  const [rows, setRows] = React.useState<Contradiction[] | null>(null);
  const [showResolved, setShowResolved] = React.useState(false);
  const [reloads, setReloads] = React.useState(0);
  const reload = React.useCallback(() => setReloads((n) => n + 1), []);

  React.useEffect(() => {
    let live = true;
    contradictionsApi
      .list(analysis.id, true)
      .then((result) => {
        if (live) setRows(result);
      })
      .catch(() => {
        if (live) setRows([]);
      });
    return () => {
      live = false;
    };
  }, [analysis.id, reloads]);

  if (!rows) {
    return <EmptyState title="Checking for clauses that disagree" description="One moment." />;
  }

  const open = rows.filter((row) => row.state === "open");
  const settled = rows.filter((row) => row.state !== "open");
  const visible = showResolved ? rows : open;

  if (rows.length === 0) {
    return (
      <div className="space-y-5">
        <EmptyState
          title="No requirements in this package contradict each other"
          description="Margin compares every countable claim in the package — page limits, word limits, fonts, margins, file sizes, copies, deadlines — plus prohibitions contradicted by permissions. Nothing here disagrees."
        />
        <Why />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {open.length ? (
        <Callout
          tone="seal"
          title={`${pluralize(open.length, "requirement pair")} cannot both be met`}
        >
          Each clause below was extracted correctly. The disagreement is in the document, and
          until somebody decides which governs, the team is writing to whichever one they
          happened to read.
        </Callout>
      ) : (
        <Callout tone="leaf" title="Every contradiction has been settled">
          {settled.length} {pluralize(settled.length, "decision")} recorded, each with a reason.
        </Callout>
      )}

      {settled.length ? (
        <div className="flex items-center gap-2">
          <Button variant="quiet" size="sm" onClick={() => setShowResolved((value) => !value)}>
            {showResolved ? "Hide settled" : `Show ${settled.length} settled`}
          </Button>
        </div>
      ) : null}

      {visible.map((row) => (
        <Conflict key={row.id} analysis={analysis} row={row} onChange={reload} />
      ))}

      <Why />
    </div>
  );
}

function Why() {
  return (
    <Well>
      <p className="text-xs leading-relaxed text-ink-soft">
        <strong className="font-medium text-ink">Why this is not decided for you.</strong> An
        amendment usually supersedes what it amends, and a specific attachment usually beats
        general language — both true often enough to be worth saying, and wrong often enough that
        a machine acting on them alone would be picking which requirement your team writes to.
        Margin recommends and records; the decision stays yours, with your name on it.
      </p>
    </Well>
  );
}

function Conflict({
  analysis,
  row,
  onChange,
}: {
  analysis: Analysis;
  row: Contradiction;
  onChange: () => void;
}) {
  const [governs, setGoverns] = React.useState<string>(row.recommendedId || "");
  const [reason, setReason] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const settled = row.state !== "open";

  async function decide(outcome: "resolved" | "disputed" | "dismissed") {
    setBusy(true);
    try {
      const result = await contradictionsApi.resolve(analysis.id, row.id, {
        outcome,
        governsId: outcome === "resolved" ? governs : undefined,
        resolution: reason.trim(),
      });
      notify.success(
        outcome === "resolved" ? "Recorded which clause governs." : "Recorded.",
        {
          description: result.superseded
            ? `${result.superseded} is now superseded and will stop appearing as live work.`
            : undefined,
        },
      );
      onChange();
    } catch (error) {
      notify.error(
        error instanceof Error && error.message ? error.message : "That could not be saved.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Panel>
      <PanelHeader
        title={
          <span className="flex flex-wrap items-center gap-2">
            <Badge tone={row.severity === "blocking" ? "seal" : "ochre"}>
              <AlertTriangle className="size-3" aria-hidden />
              {DIMENSION_LABEL[row.dimension] ?? row.dimension}
            </Badge>
            {settled ? (
              <Badge tone={row.state === "disputed" ? "ochre" : "leaf"}>{row.state}</Badge>
            ) : null}
          </span>
        }
        description={row.summary}
      />

      <div className="grid gap-px bg-line @2xl:grid-cols-2">
        <Side
          analysis={analysis}
          side={row.left}
          recommended={row.recommendedId === row.left.requirementId}
          governs={row.governsId === row.left.requirementId}
          selectable={!settled}
          selected={governs === row.left.requirementId}
          onSelect={() => setGoverns(row.left.requirementId)}
        />
        <Side
          analysis={analysis}
          side={row.right}
          recommended={row.recommendedId === row.right.requirementId}
          governs={row.governsId === row.right.requirementId}
          selectable={!settled}
          selected={governs === row.right.requirementId}
          onSelect={() => setGoverns(row.right.requirementId)}
        />
      </div>

      <div className="space-y-3 px-5 py-4">
        {row.rationale ? (
          <p className="text-xs leading-relaxed text-ink-soft">
            <strong className="font-medium text-ink">Margin&rsquo;s reading:</strong>{" "}
            {row.rationale}
          </p>
        ) : null}

        {settled ? (
          <p className="text-sm leading-relaxed text-ink-soft">
            {row.resolution}
            <span className="ml-2 text-2xs text-ink-faint">
              {row.resolvedBy}
              {row.resolvedAt ? ` · ${relative(row.resolvedAt)}` : ""}
            </span>
          </p>
        ) : (
          <>
            <Textarea
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="Why this one governs. Six weeks from now this is the only record of why the team wrote to one clause and not the other."
              rows={2}
              aria-label="Why this clause governs"
            />
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                disabled={busy || !governs || !reason.trim()}
                onClick={() => decide("resolved")}
              >
                <Check /> This one governs
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={busy || !reason.trim()}
                onClick={() => decide("disputed")}
              >
                <MessageSquarePlus /> The document is wrong — ask the agency
              </Button>
              <Button
                variant="quiet"
                size="sm"
                disabled={busy || !reason.trim()}
                onClick={() => decide("dismissed")}
              >
                Not a conflict
              </Button>
            </div>
          </>
        )}
      </div>
    </Panel>
  );
}

function Side({
  analysis,
  side,
  recommended,
  governs,
  selectable,
  selected,
  onSelect,
}: {
  analysis: Analysis;
  side: ContradictionSide;
  recommended: boolean;
  governs: boolean;
  selectable: boolean;
  selected: boolean;
  onSelect: () => void;
}) {
  const body = (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-xs text-patina">{side.reference}</span>
        <Badge tone="neutral" shape="mono">
          {side.value}
        </Badge>
        {side.stakes === "disqualifying" ? <Badge tone="seal">Mandatory</Badge> : null}
        {recommended ? <Badge tone="slate">Margin&rsquo;s reading</Badge> : null}
        {governs ? (
          <Badge tone="leaf">
            <Check className="size-3" aria-hidden />
            Governs
          </Badge>
        ) : null}
      </div>
      <p className="mt-2 text-sm leading-relaxed text-ink">{side.text}</p>
      <div className="mt-2">
        <CitationMeta
          citation={side.citation}
          analysisId={analysis.id}
          label={side.reference}
          origin="Contradiction"
          compact
          clamp={2}
        />
      </div>
    </>
  );

  if (!selectable) {
    return <div className="bg-paper-raised px-5 py-4">{body}</div>;
  }

  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={cn(
        "bg-paper-raised px-5 py-4 text-left transition-colors duration-150",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-patina/40",
        selected ? "bg-[var(--leaf-tint)]" : "hover:bg-paper-sunk",
      )}
    >
      {body}
      <span className="mt-3 flex items-center gap-1 text-2xs text-ink-faint">
        {selected ? "Selected as governing" : "Select as governing"}
        <ArrowRight className="size-3" aria-hidden />
      </span>
    </button>
  );
}
