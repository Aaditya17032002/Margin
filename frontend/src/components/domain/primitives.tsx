"use client";

import * as React from "react";
import { CheckCircle2, FileWarning, Quote } from "lucide-react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Tooltip } from "@/components/ui/overlay";
import { useUIStore } from "@/stores/ui";
import { QuillMark } from "./marks";
import type { Citation, DocType, MatrixStatus, RequirementType, Stage, Stakes } from "@/types";

/* ---------------------------------------------------------------- */
/* Citation — the doorway to the Margin rail                         */
/* ---------------------------------------------------------------- */

export function CitationChip({
  citation,
  analysisId,
  label,
  origin,
  className,
  compact = false,
}: {
  citation: Citation;
  analysisId: string;
  label?: string;
  origin?: string;
  className?: string;
  /** Tighter padding for data-grid cells. Still the same type size. */
  compact?: boolean;
}) {
  const peek = useUIStore((s) => s.peek);
  const hold = useUIStore((s) => s.hold);
  const release = useUIStore((s) => s.release);
  const active = useUIStore((s) => s.source?.citation.id === citation.id);

  const payload = { citation, analysisId, label: label ?? origin ?? "Source", origin };

  return (
    <button
      type="button"
      data-citation={citation.id}
      data-active={active || undefined}
      onMouseEnter={() => peek(payload)}
      onMouseLeave={release}
      onFocus={() => peek(payload)}
      onBlur={release}
      onClick={() => hold(payload)}
      title={citation.quote}
      aria-label={`Show source: page ${citation.page}, ${citation.section}`}
      className={cn(
        "group inline-flex max-w-full shrink-0 items-center gap-2 rounded-md border font-mono text-xs leading-none",
        "transition-[background-color,border-color,color] duration-150 ease-[cubic-bezier(0.32,0.72,0,1)]",
        active
          ? "border-patina bg-patina-tint text-patina"
          : "border-line-strong bg-paper-raised text-ink-soft hover:border-patina hover:bg-patina-tint hover:text-patina",
        compact ? "h-7 px-2" : "h-8 px-2.5",
        className,
      )}
    >
      <Quote className="size-3.5 shrink-0 opacity-70" aria-hidden />
      <span className="flex min-w-0 items-baseline gap-1.5">
        <span className={cn("shrink-0 tabular", active ? "text-patina" : "text-ink group-hover:text-patina")}>
          p.{citation.page}
        </span>
        <span className="shrink-0 text-ink-faint/70" aria-hidden>
          ·
        </span>
        <span className="min-w-0 truncate">{citation.section}</span>
      </span>
    </button>
  );
}

/**
 * A source line: the chip, then the quoted clause. Used under findings,
 * gates, and risks — never inline with badges.
 */
export function CitationMeta({
  citation,
  analysisId,
  label,
  origin,
  quote = true,
  compact = false,
  clamp,
  aside,
  className,
}: {
  citation: Citation;
  analysisId: string;
  label?: string;
  origin?: string;
  quote?: boolean;
  compact?: boolean;
  /** Line-clamp the quoted clause. Tables use 2; cards leave it open. */
  clamp?: 1 | 2 | 3;
  aside?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("min-w-0 space-y-2 border-t border-line pt-3.5", className)}>
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <CitationChip
          citation={citation}
          analysisId={analysisId}
          label={label}
          origin={origin}
          compact={compact}
        />
        {aside ? <div className="shrink-0">{aside}</div> : null}
      </div>
      {quote && citation.quote ? (
        <p
          className={cn(
            "max-w-prose text-[13px] italic leading-relaxed text-ink-faint",
            clamp === 1 && "line-clamp-1",
            clamp === 2 && "line-clamp-2",
            clamp === 3 && "line-clamp-3",
          )}
        >
          “{citation.quote}”
        </p>
      ) : null}
    </div>
  );
}

/* ---------------------------------------------------------------- */
/* Confidence as ink                                                  */
/* ---------------------------------------------------------------- */

export function confidenceLabel(confidence: number) {
  if (confidence >= 0.93) return "High";
  if (confidence >= 0.85) return "Good";
  if (confidence >= 0.75) return "Moderate";
  return "Needs review";
}

export function ConfidenceMeter({
  confidence,
  className,
  showLabel = true,
}: {
  confidence: number;
  className?: string;
  showLabel?: boolean;
}) {
  const pct = Math.round(confidence * 100);
  const low = confidence < 0.85;
  return (
    <Tooltip content={`${confidenceLabel(confidence)} confidence · ${pct}%`}>
      <span className={cn("inline-flex items-center gap-1.5", className)}>
        <span className="flex items-end gap-[2px]" aria-hidden>
          {[0.72, 0.82, 0.9, 0.96].map((threshold, i) => (
            <span
              key={threshold}
              className={cn(
                "w-[3px] rounded-[1px] transition-colors duration-200",
                confidence >= threshold ? "bg-ink-soft" : "bg-[var(--line-strong)]",
              )}
              style={{ height: 5 + i * 2.5 }}
            />
          ))}
        </span>
        {showLabel ? (
          <span className={cn("font-mono text-2xs", low ? "text-ochre" : "text-ink-faint")}>{pct}%</span>
        ) : null}
        <span className="sr-only">{confidenceLabel(confidence)} confidence, {pct} percent</span>
      </span>
    </Tooltip>
  );
}

export function NeedsReviewMark({ className }: { className?: string }) {
  return (
    <Tooltip content="Below the review threshold — a person should confirm this">
      <span className={cn("inline-flex text-ochre", className)}>
        <QuillMark className="size-3.5" label="Needs review" />
      </span>
    </Tooltip>
  );
}

/* ---------------------------------------------------------------- */
/* Badges                                                             */
/* ---------------------------------------------------------------- */

const STAKES_COPY: Record<Stakes, { label: string; tone: "seal" | "ochre" | "slate" }> = {
  disqualifying: { label: "Disqualifying", tone: "seal" },
  scored: { label: "Scored", tone: "ochre" },
  informational: { label: "Informational", tone: "slate" },
};

export function StakesBadge({ stakes, className }: { stakes: Stakes; className?: string }) {
  const { label, tone } = STAKES_COPY[stakes];
  return (
    <Badge tone={tone} className={className}>
      {stakes === "disqualifying" ? <FileWarning className="size-3" aria-hidden /> : null}
      {label}
    </Badge>
  );
}

const DOC_TONE: Record<DocType, "patina" | "slate" | "ochre" | "neutral"> = {
  RFP: "patina",
  RFI: "slate",
  RFQ: "slate",
  IFB: "ochre",
  "Sources Sought": "neutral",
  BAA: "slate",
  "Task Order": "ochre",
};

export function DocTypeBadge({ docType, className }: { docType: DocType; className?: string }) {
  return (
    <Badge tone={DOC_TONE[docType]} shape="mono" className={className}>
      {docType}
    </Badge>
  );
}

const STAGE_COPY: Record<Stage, { label: string; tone: "neutral" | "slate" | "ochre" | "leaf" }> = {
  triage: { label: "Triage", tone: "neutral" },
  analyzing: { label: "Analyzing", tone: "slate" },
  review: { label: "Review", tone: "ochre" },
  decided: { label: "Decided", tone: "leaf" },
};

export function StageBadge({ stage, className }: { stage: Stage; className?: string }) {
  const { label, tone } = STAGE_COPY[stage];
  return (
    <Badge tone={tone} className={className}>
      {label}
    </Badge>
  );
}

const TYPE_TONE: Record<RequirementType, "seal" | "ochre" | "slate"> = {
  shall: "seal",
  should: "ochre",
  may: "slate",
};

export function RequirementTypeBadge({ type }: { type: RequirementType }) {
  return (
    <Badge tone={TYPE_TONE[type]} shape="mono">
      {type}
    </Badge>
  );
}

const STATUS_COPY: Record<MatrixStatus, { label: string; tone: "neutral" | "slate" | "ochre" | "leaf" }> = {
  unassigned: { label: "Unassigned", tone: "neutral" },
  assigned: { label: "Assigned", tone: "slate" },
  drafted: { label: "Drafted", tone: "ochre" },
  "in-review": { label: "In review", tone: "ochre" },
  complete: { label: "Complete", tone: "leaf" },
};

export function MatrixStatusBadge({ status }: { status: MatrixStatus }) {
  const { label, tone } = STATUS_COPY[status];
  return (
    <Badge tone={tone}>
      {status === "complete" ? <CheckCircle2 className="size-3" aria-hidden /> : null}
      {label}
    </Badge>
  );
}

export const STAGE_ORDER: Stage[] = ["triage", "analyzing", "review", "decided"];
export const STAGE_LABEL = Object.fromEntries(
  Object.entries(STAGE_COPY).map(([k, v]) => [k, v.label]),
) as Record<Stage, string>;
export const MATRIX_STATUS_LABEL = Object.fromEntries(
  Object.entries(STATUS_COPY).map(([k, v]) => [k, v.label]),
) as Record<MatrixStatus, string>;
