"use client";

import * as React from "react";
import { motion, useReducedMotion } from "motion/react";
import { Check, MoreHorizontal, Flag } from "lucide-react";

import { cn } from "@/lib/utils";
import { listItem, staggerList } from "@/lib/motion";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/overlay";
import { useUIStore } from "@/stores/ui";
import { CitationMeta, ConfidenceMeter, NeedsReviewMark, StakesBadge } from "./primitives";
import type { Finding } from "@/types";

/**
 * A finding is set like an entry in a reference work, not like a card: a label
 * in the left column, the claim in the right, and the cited clause on its own
 * source line beneath. Ink saturation follows confidence, so a shaky finding
 * literally reads lighter than a certain one.
 */
export function FindingEntry({
  finding,
  analysisId,
  sectionLabel,
  onVerify,
  onFlag,
  className,
}: {
  finding: Finding;
  analysisId: string;
  sectionLabel?: string;
  onVerify?: () => void;
  onFlag?: () => void;
  className?: string;
}) {
  const peek = useUIStore((s) => s.peek);
  const release = useUIStore((s) => s.release);
  const active = useUIStore((s) => s.source?.citation.id === finding.citation.id);
  const lowConfidence = finding.confidence < 0.85;

  return (
    <motion.article
      variants={listItem}
      onMouseEnter={() => peek({ citation: finding.citation, analysisId, label: finding.label, origin: sectionLabel })}
      onMouseLeave={release}
      className={cn(
        "group relative grid gap-x-6 gap-y-3 border-b border-line py-5 last:border-b-0",
        "sm:grid-cols-[minmax(9rem,11rem)_1fr]",
        "transition-colors duration-200",
        active && "bg-[color-mix(in_oklab,var(--patina-tint)_55%,transparent)]",
        className,
      )}
    >
      {/* Left rail marks the entry the way a printed margin would. */}
      <span
        aria-hidden
        className={cn(
          "absolute -left-4 top-4 h-6 w-px origin-top scale-y-0 bg-patina transition-transform duration-200 ease-[cubic-bezier(0.32,0.72,0,1)]",
          "group-hover:scale-y-100",
          active && "scale-y-100",
        )}
      />

      <div className="space-y-1.5">
        <h4 className="text-sm font-medium leading-snug text-ink-soft">{finding.label}</h4>
        <div className="flex flex-wrap items-center gap-1.5">
          <StakesBadge stakes={finding.stakes} />
          {finding.verified ? (
            <span className="inline-flex items-center gap-1 font-mono text-2xs text-leaf">
              <Check className="size-3" strokeWidth={3} aria-hidden />
              Verified
            </span>
          ) : null}
          {lowConfidence ? <NeedsReviewMark /> : null}
          {finding.flagged ? (
            <span className="inline-flex items-center gap-1 font-mono text-2xs text-seal">
              <Flag className="size-3" aria-hidden />
              Flagged
            </span>
          ) : null}
        </div>
      </div>

      <div className="min-w-0 space-y-3">
        <p
          className="ink-confidence text-base leading-relaxed"
          style={{ "--confidence": finding.confidence } as React.CSSProperties}
        >
          {finding.value}
        </p>
        {finding.detail ? (
          <p className="text-sm leading-relaxed text-ink-soft">{finding.detail}</p>
        ) : null}
        <CitationMeta
          citation={finding.citation}
          analysisId={analysisId}
          label={finding.label}
          origin={sectionLabel}
          aside={<ConfidenceMeter confidence={finding.confidence} />}
        />
      </div>

      {onVerify || onFlag ? (
        <div className="absolute right-0 top-3 opacity-0 transition-opacity duration-150 focus-within:opacity-100 group-hover:opacity-100">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="quiet" size="iconSm" aria-label={`Actions for ${finding.label}`}>
                <MoreHorizontal />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {onVerify ? (
                <DropdownMenuItem onSelect={onVerify}>
                  <Check />
                  {finding.verified ? "Remove verification" : "Mark verified"}
                </DropdownMenuItem>
              ) : null}
              {onFlag ? (
                <DropdownMenuItem onSelect={onFlag}>
                  <Flag />
                  {finding.flagged ? "Clear flag" : "Flag for review"}
                </DropdownMenuItem>
              ) : null}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      ) : null}
    </motion.article>
  );
}

export function FindingList({
  findings,
  analysisId,
  sectionLabel,
  onVerify,
  onFlag,
  className,
}: {
  findings: Finding[];
  analysisId: string;
  sectionLabel?: string;
  onVerify?: (id: string) => void;
  onFlag?: (id: string) => void;
  className?: string;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      variants={staggerList()}
      initial={reduce ? false : "hidden"}
      animate="visible"
      className={cn("pl-4", className)}
    >
      {findings.map((finding) => (
        <FindingEntry
          key={finding.id}
          finding={finding}
          analysisId={analysisId}
          sectionLabel={sectionLabel}
          onVerify={onVerify ? () => onVerify(finding.id) : undefined}
          onFlag={onFlag ? () => onFlag(finding.id) : undefined}
        />
      ))}
    </motion.div>
  );
}
