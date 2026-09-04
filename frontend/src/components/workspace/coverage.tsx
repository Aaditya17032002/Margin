"use client";

import * as React from "react";
import { motion, useReducedMotion } from "motion/react";
import { FileText, FileWarning, Layers, Paperclip } from "lucide-react";

import { cn, pluralize } from "@/lib/utils";
import { listItem, staggerList } from "@/lib/motion";
import { Panel, PanelHeader, Well } from "@/components/ui/surface";
import { Callout, EmptyState } from "@/components/ui/feedback";
import { Badge } from "@/components/ui/badge";
import { Tooltip } from "@/components/ui/overlay";
import type { Analysis, CoverageDocument, CoverageState, LedgerDelta } from "@/types";

/**
 * The reading ledger.
 *
 * This tab exists to make the product's central claim falsifiable. Everywhere
 * else the analysis says what it found; here it says what it read, document by
 * document, and — more usefully — what it did not.
 *
 * The one design rule: never collapse the two kinds of reading into a single
 * percentage. *Scanned* means every known pattern was matched against the text,
 * which is complete and shallow. *Analysed* means a specialist reasoned over
 * it, which is deep and selective. A lone "97% covered" would be true of
 * neither and would be read as both.
 */

const AGENT_LABELS: Record<string, string> = {
  intake: "Intake",
  scope: "Scope",
  compliance: "Compliance",
  eligibility: "Eligibility",
  evaluation: "Evaluation",
  risk: "Risk",
  pricing: "Pricing",
  dates: "Dates",
  qa: "Q&A",
  verifier: "Verifier",
};

const KIND_LABELS: Record<string, string> = {
  base: "Base document",
  attachment: "Attachment",
  amendment: "Amendment",
  response: "Response",
};

const STATE_BADGE: Record<CoverageState, { tone: "leaf" | "slate" | "ochre" | "seal"; label: string }> = {
  analysed: { tone: "leaf", label: "Analysed" },
  scanned: { tone: "leaf", label: "Fully read" },
  no_text: { tone: "seal", label: "No text" },
  unreached: { tone: "ochre", label: "Gap" },
};

export function CoveragePanel({ analysis }: { analysis: Analysis }) {
  const reduce = useReducedMotion();
  const coverage = analysis.coverage;

  // An analysis stored before the ledger existed, or one that has not run,
  // has nothing to prove yet — and saying so is better than showing zeroes
  // that read as a failure.
  if (!coverage || !coverage.documents.length) {
    return (
      <EmptyState
        title="No reading ledger for this analysis"
        description="The ledger is written while an analysis runs. Run this solicitation to record what was read, page by page, and what was not."
      />
    );
  }

  const { totals, documents } = coverage;
  const agents = Object.entries(coverage.byAgent).sort((a, b) => b[1] - a[1]);

  return (
    <div className="space-y-5">
      <LedgerChange delta={analysis.ledger} />

      {coverage.complete ? (
        <Callout tone="leaf" title="Every page of the package was read">
          All {totals.pages} {pluralize(totals.pages, "page")} across{" "}
          {totals.documents} {pluralize(totals.documents, "document")} were matched against every
          extraction pattern Margin knows. {totals.pagesAnalysed} of them were also read in depth by a
          specialist.
        </Callout>
      ) : (
        <Callout tone="ochre" title="Part of this package was not read">
          {gapSentence(totals.chunksUnreached, totals.emptyDocuments)} Everything below is counted from
          the run itself, not estimated — treat the gaps as unreviewed until they are closed.
        </Callout>
      )}

      <Panel>
        <PanelHeader
          title="What was read"
          description="Two numbers, because they are two different claims."
        />
        <div className="grid grid-cols-1 gap-px bg-line @sm:grid-cols-3">
          <Metric
            label="Pages scanned"
            value={`${totals.pagesScanned} / ${totals.pages}`}
            detail="Matched against every known pattern — obligations, limits, forms, certifications, dates, clauses. Complete, and shallow."
          />
          <Metric
            label="Pages analysed in depth"
            value={`${totals.pagesAnalysed} / ${totals.pages}`}
            detail="Held in a specialist's context and reasoned over. Deep, and by necessity selective — retrieval chooses what each specialist reads."
          />
          <Metric
            label="Passages unreached"
            value={String(totals.chunksUnreached)}
            tone={totals.chunksUnreached ? "ochre" : "leaf"}
            detail="Text neither pass touched. This should be zero, and the ledger exists to prove it rather than assume it."
          />
        </div>
      </Panel>

      <Panel>
        <PanelHeader
          title="Document by document"
          description={`${totals.documents} ${pluralize(totals.documents, "document")} in this package, including every attachment and amendment.`}
        />
        <motion.ul
          variants={reduce ? undefined : staggerList()}
          initial={reduce ? undefined : "hidden"}
          animate={reduce ? undefined : "show"}
          className="divide-y divide-line"
        >
          {documents.map((doc) => (
            <motion.li key={doc.documentId} variants={reduce ? undefined : listItem}>
              <DocumentRow doc={doc} />
            </motion.li>
          ))}
        </motion.ul>
      </Panel>

      {agents.length ? (
        <Panel>
          <PanelHeader
            title="Who read what"
            description="Passages each specialist had in context. A low number is not a fault — it is how narrow that specialist's question is."
          />
          <div className="px-5 pb-5">
            <ul className="space-y-2">
              {agents.map(([agent, count]) => {
                const share = totals.chunks ? count / totals.chunks : 0;
                return (
                  <li key={agent} className="flex items-center gap-3">
                    <span className="w-28 shrink-0 text-xs text-ink-soft">
                      {AGENT_LABELS[agent] ?? agent}
                    </span>
                    <span className="h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-paper-sunk">
                      <span
                        className="block h-full rounded-full bg-patina"
                        style={{ width: `${Math.max(2, Math.round(share * 100))}%` }}
                      />
                    </span>
                    <span className="w-24 shrink-0 text-right font-mono text-2xs text-ink-faint">
                      {count} {pluralize(count, "passage")}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        </Panel>
      ) : null}

      <Well>
        <p className="text-xs leading-relaxed text-ink-soft">
          <strong className="font-medium text-ink">Why two numbers.</strong> A single
          &ldquo;fully covered&rdquo; figure would overstate the depth of the reading or understate its
          breadth. Scanning is exhaustive and literal; analysis is interpretive and selective. Margin
          reports both so a reviewer can tell which one backs any given finding.
        </p>
      </Well>
    </div>
  );
}

/**
 * What the last run did to the Requirement Ledger.
 *
 * The number that earns its place here is `removedWithWork`: requirements
 * somebody had already assigned or drafted against, that this read of the
 * package no longer finds. Under the old behaviour those rows were deleted and
 * the work went with them, silently. Now they are kept, and named.
 */
function LedgerChange({ delta }: { delta?: LedgerDelta }) {
  if (!delta || (!delta.added && !delta.updated && !delta.removed && !delta.unchanged)) return null;

  const total = delta.added + delta.updated + delta.unchanged;
  const stranded = delta.removedWithWork ?? [];

  return (
    <Panel>
      <PanelHeader
        title="What the last run changed"
        description="Requirements keep their identity across reads, so ownership and status survive a re-run."
      />
      <div className="px-5 pb-5">
        <p className="text-sm text-ink-soft tabular-nums">
          {total} {pluralize(total, "requirement")} in the ledger — {delta.added} new,{" "}
          {delta.updated} changed, {delta.unchanged} unchanged.
          {delta.removed ? ` ${delta.removed} no longer found.` : ""}
        </p>
        {stranded.length ? (
          <Callout tone="ochre" title="Assigned work whose requirement is gone" className="mt-4">
            The latest read of the package no longer finds{" "}
            {stranded.length === 1 ? "a requirement" : `${stranded.length} requirements`} that someone
            was already working: {stranded.join(", ")}. Either an amendment removed{" "}
            {stranded.length === 1 ? "it" : "them"} — in which case the work can stop — or the
            extraction missed {stranded.length === 1 ? "it" : "them"} this time, in which case it
            cannot. The {stranded.length === 1 ? "row is" : "rows are"} kept either way; nothing was
            deleted.
          </Callout>
        ) : null}
      </div>
    </Panel>
  );
}

function gapSentence(unreached: number, empty: number): string {
  const parts: string[] = [];
  if (unreached) {
    parts.push(`${unreached} ${pluralize(unreached, "passage")} ${unreached === 1 ? "was" : "were"} not reached by any pass.`);
  }
  if (empty) {
    parts.push(
      `${empty} ${pluralize(empty, "document")} produced no readable text — most likely a scan with no text layer, which needs OCR or a text copy before it can be read at all.`,
    );
  }
  return parts.join(" ");
}

function Metric({
  label,
  value,
  detail,
  tone = "neutral",
}: {
  label: string;
  value: string;
  detail: string;
  tone?: "neutral" | "leaf" | "ochre";
}) {
  return (
    <div className="bg-paper-raised px-5 py-4">
      <p className="text-2xs font-medium uppercase tracking-[0.08em] text-ink-faint">{label}</p>
      <p
        className={cn(
          "mt-1 font-mono text-2xl leading-none tabular-nums",
          tone === "ochre" && "text-[color-mix(in_oklab,var(--ochre)_82%,var(--ink))]",
          tone === "leaf" && "text-leaf",
          tone === "neutral" && "text-ink",
        )}
      >
        {value}
      </p>
      <p className="mt-2 text-xs leading-relaxed text-ink-soft">{detail}</p>
    </div>
  );
}

function DocumentRow({ doc }: { doc: CoverageDocument }) {
  const badge = STATE_BADGE[doc.state] ?? STATE_BADGE.scanned;
  const Icon = doc.state === "no_text" ? FileWarning : doc.kind === "base" ? FileText : doc.kind === "amendment" ? Layers : Paperclip;
  const scannedPages = Math.max(0, doc.pages - unreachedPageCount(doc));

  return (
    <div className="flex flex-col gap-3 px-5 py-4 @md:flex-row @md:items-start @md:gap-5">
      <span className="mt-0.5 shrink-0 text-ink-faint [&_svg]:size-4">
        <Icon />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="truncate text-sm text-ink">{doc.name}</span>
          <Badge tone="neutral" shape="mono">
            {KIND_LABELS[doc.kind] ?? doc.kind}
          </Badge>
          <Badge tone={badge.tone}>{badge.label}</Badge>
        </div>
        {doc.state === "no_text" ? (
          <p className="mt-1.5 text-xs leading-relaxed text-ink-soft">
            {doc.note || "No text could be extracted. Nothing in this document was read."}
          </p>
        ) : (
          <p className="mt-1.5 text-xs text-ink-soft tabular-nums">
            {scannedPages} of {doc.pages} {pluralize(doc.pages, "page")} scanned ·{" "}
            {doc.pagesAnalysed} analysed in depth
          </p>
        )}
        {doc.unreachedPages.length ? (
          <Tooltip content="No pass reached these pages. Nothing on them backs any finding.">
            <p className="mt-1.5 font-mono text-2xs text-[color-mix(in_oklab,var(--ochre)_82%,var(--ink))]">
              Not reached: p. {doc.unreachedPages.map(spanLabel).join(", ")}
            </p>
          </Tooltip>
        ) : null}
      </div>
    </div>
  );
}

function unreachedPageCount(doc: CoverageDocument): number {
  return doc.unreachedPages.reduce((total, [start, end]) => total + (end - start + 1), 0);
}

function spanLabel([start, end]: [number, number]): string {
  return start === end ? String(start) : `${start}–${end}`;
}
