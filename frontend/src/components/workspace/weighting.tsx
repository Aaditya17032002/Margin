"use client";

import * as React from "react";
import { AlertTriangle, Scale } from "lucide-react";

import { cn, pluralize } from "@/lib/utils";
import { weightingApi } from "@/lib/api";
import { Panel, PanelHeader, Well } from "@/components/ui/surface";
import { Callout, EmptyState } from "@/components/ui/feedback";
import { Badge } from "@/components/ui/badge";
import { Tooltip } from "@/components/ui/overlay";
import { CitationMeta } from "@/components/domain/primitives";
import type { Analysis, FactorCoverage, WeightingLens } from "@/types";

/**
 * Where the score is, and whether the response is there.
 *
 * The compliance matrix treats every requirement as equally worth answering.
 * Evaluators do not. Section M says technical approach is forty percent and
 * past performance is ten, and a team with four days left should spend them on
 * the forty rather than on whatever happens to be red.
 *
 * Factors are ordered by weight share × weakness, so the top of the list is
 * where the most points are least defended. Deliberately not a predicted
 * score: nothing here knows how an evaluator reads, and a number that looked
 * like a score would be believed.
 */

const STATUS_TONE: Record<string, "leaf" | "ochre" | "seal" | "slate" | "neutral"> = {
  satisfied: "leaf",
  partial: "ochre",
  failed: "seal",
  not_found: "seal",
  unverifiable: "slate",
  unchecked: "neutral",
};

const STATUS_LABEL: Record<string, string> = {
  satisfied: "Answered",
  partial: "Partly",
  failed: "Fails",
  not_found: "Not addressed",
  unverifiable: "Unknown",
  unchecked: "Not checked",
};

export function WeightingPanel({ analysis }: { analysis: Analysis }) {
  const [lens, setLens] = React.useState<WeightingLens | null>(null);

  React.useEffect(() => {
    let live = true;
    weightingApi
      .lens(analysis.id)
      .then((result) => {
        if (live) setLens(result);
      })
      .catch(() => {
        if (live) setLens(null);
      });
    return () => {
      live = false;
    };
  }, [analysis.id, analysis.updatedAt]);

  if (!lens) {
    return <EmptyState title="Reading Section M against the ledger" description="One moment." />;
  }

  if (!lens.factors.length) {
    return (
      <EmptyState
        title="No evaluation factors were extracted"
        description="This lens maps Section M to the requirements it scores. Without factors there is nothing to weight against — check the Eligibility & Evaluation tab for what the read found."
      />
    );
  }

  const { summary } = lens;
  const weighted = lens.factors.filter((factor) => factor.weight > 0);

  return (
    <div className="space-y-5">
      {summary.weighted === 0 ? (
        <Callout tone="slate" title="This solicitation states no weights">
          Every factor below carries the same unstated importance. Showing them as equally
          weighted would be inventing the thing this view exists to reveal, so the ordering here
          is by name rather than by exposure.
        </Callout>
      ) : lens.responseBound ? (
        <Callout
          tone={summary.weightAtRisk > 0.3 ? "seal" : summary.weightAtRisk > 0.1 ? "ochre" : "leaf"}
          title={`${Math.round(summary.weightAtRisk * 100)}% of the stated weight is not fully answered`}
        >
          Weighted by what each factor is worth, not by how many requirements are open. The
          factors below are ordered by where the most points are least defended.
        </Callout>
      ) : (
        <Callout tone="slate" title="No response is bound yet">
          The factors and their requirements are mapped. How well the response covers them needs a
          draft to measure against — bind one on the Response Gap tab.
        </Callout>
      )}

      {summary.blocking.length ? (
        <Callout
          tone="seal"
          title={`${pluralize(summary.blocking.length, "mandatory requirement")} under a scored factor is unanswered`}
        >
          {summary.blocking.join(", ")}
        </Callout>
      ) : null}

      {(weighted.length ? weighted : lens.factors).map((factor) => (
        <Factor key={factor.factorId} analysis={analysis} factor={factor} bound={lens.responseBound} />
      ))}

      {summary.unmapped.length ? (
        <Panel>
          <PanelHeader
            title="Factors with no requirements under them"
            description="Either the extraction missed the requirements this factor scores, or the factor is not about requirements at all. Both are worth knowing."
          />
          <ul className="px-5 py-4">
            {summary.unmapped.map((name) => (
              <li key={name} className="text-sm text-ink-soft">
                {name}
              </li>
            ))}
          </ul>
        </Panel>
      ) : null}

      <Well>
        <p className="text-xs leading-relaxed text-ink-soft">
          <strong className="font-medium text-ink">This is not a predicted score.</strong> Nothing
          here knows how an evaluator reads, and a number that looked like a score would be
          believed. What it reports is coverage under a factor, which is a fact — and how a
          requirement came to sit under a factor is shown on every row, so you can disagree with
          it.
        </p>
      </Well>
    </div>
  );
}

function Factor({
  analysis,
  factor,
  bound,
}: {
  analysis: Analysis;
  factor: FactorCoverage;
  bound: boolean;
}) {
  const percent = Math.round(factor.share * 100);
  const weakness = Math.round(factor.weakness * 100);

  return (
    <Panel>
      <PanelHeader
        title={
          <span className="flex flex-wrap items-center gap-2">
            <Scale className="size-4 text-ink-faint" aria-hidden />
            <span>{factor.name}</span>
            {factor.weight > 0 ? (
              <Badge tone="neutral" shape="mono">
                {factor.weight}
                {percent && percent !== factor.weight ? ` · ${percent}% of weight` : ""}
              </Badge>
            ) : (
              <Badge tone="neutral">No weight stated</Badge>
            )}
            {factor.blocking.length ? (
              <Badge tone="seal">
                <AlertTriangle className="size-3" aria-hidden />
                {factor.blocking.length} mandatory unanswered
              </Badge>
            ) : null}
          </span>
        }
        description={factor.method}
      />

      {bound && factor.weight > 0 ? (
        <div className="px-5 pt-4">
          <div className="flex items-center gap-3">
            <span className="w-28 shrink-0 text-2xs uppercase tracking-[0.08em] text-ink-faint">
              Not answered
            </span>
            <span className="h-2 min-w-0 flex-1 overflow-hidden rounded-full bg-paper-sunk">
              <span
                className={cn(
                  "block h-full rounded-full",
                  weakness > 60 ? "bg-seal" : weakness > 25 ? "bg-[var(--ochre)]" : "bg-leaf",
                )}
                style={{ width: `${Math.max(2, weakness)}%` }}
              />
            </span>
            <span className="w-40 shrink-0 text-right font-mono text-2xs text-ink-faint tabular-nums">
              {weakness}% of {factor.requirements}{" "}
              {pluralize(factor.requirements, "requirement")}
            </span>
          </div>
        </div>
      ) : null}

      {factor.requirementDetail.length ? (
        <ul className="mt-3 divide-y divide-line">
          {factor.requirementDetail.map((requirement) => (
            <li
              key={requirement.id}
              className="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-5 py-3"
            >
              <span className="font-mono text-2xs text-patina">{requirement.reference}</span>
              <Badge tone={STATUS_TONE[requirement.status] ?? "neutral"}>
                {STATUS_LABEL[requirement.status] ?? requirement.status}
              </Badge>
              {requirement.stakes === "disqualifying" ? <Badge tone="seal">Mandatory</Badge> : null}
              <span className="min-w-0 flex-1 text-sm leading-relaxed text-ink">
                {requirement.text}
              </span>
              <Tooltip content={`Mapped to this factor because it ${requirement.matchedBy}.`}>
                <span className="shrink-0 text-2xs text-ink-faint">why</span>
              </Tooltip>
              {requirement.owner ? (
                <span className="shrink-0 text-2xs text-ink-faint">{requirement.owner}</span>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="px-5 py-4 text-sm text-ink-soft">
          No requirement in the ledger maps to this factor.
        </p>
      )}

      {factor.citation?.quote ? (
        <div className="px-5 pb-4">
          <CitationMeta
            citation={factor.citation}
            analysisId={analysis.id}
            label={factor.name}
            origin="Evaluation weighting"
            compact
            clamp={2}
          />
        </div>
      ) : null}
    </Panel>
  );
}
