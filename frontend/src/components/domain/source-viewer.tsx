"use client";

import * as React from "react";
import { motion, useReducedMotion } from "motion/react";

import { cn } from "@/lib/utils";
import type { Analysis, Citation } from "@/types";

/**
 * The source viewer renders the solicitation page itself and lays a highlight
 * layer over the cited lines — the same two-layer architecture a PDF viewer
 * uses (page beneath, absolutely-positioned boxes above), with the text layer
 * kept selectable so a reader can copy the clause straight out of the rail.
 */
export function SourceViewer({
  analysis,
  citation,
  compact = false,
  className,
}: {
  analysis: Analysis;
  citation: Citation;
  compact?: boolean;
  className?: string;
}) {
  const reduce = useReducedMotion();
  const page = analysis.pages.find((p) => p.page === citation.page);
  const highlightRef = React.useRef<HTMLSpanElement>(null);

  React.useEffect(() => {
    highlightRef.current?.scrollIntoView({
      block: "center",
      behavior: reduce ? "auto" : "smooth",
    });
  }, [citation.id, reduce]);

  if (!page) {
    return (
      <div className="rounded-md border border-dashed border-line-strong bg-paper-sunk px-4 py-8 text-center text-sm text-ink-faint">
        Page {citation.page} is not in the indexed extract for this document.
      </div>
    );
  }

  const quoteLines = citation.quote.split(" ");

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <p className="font-mono text-xs text-ink-soft">
          <span className="tabular text-ink">p.{page.page}</span>
          <span className="mx-1.5 text-ink-faint/70" aria-hidden>
            ·
          </span>
          {citation.section}
        </p>
        <PageMap pages={analysis.pages.map((p) => p.page)} current={citation.page} bbox={citation.bbox} />
      </div>

      <motion.div
        key={citation.id}
        initial={reduce ? false : { opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: [0.32, 0.72, 0, 1] }}
        className={cn(
          "relative overflow-hidden rounded-md border border-line-strong bg-[var(--paper-raised)]",
          "shadow-[var(--shadow-raised)]",
        )}
      >
        {/* The printed margin rule, which is where the product gets its name. */}
        <span aria-hidden className="absolute inset-y-0 left-9 w-px bg-[color-mix(in_oklab,var(--seal)_22%,transparent)]" />

        <div className={cn("relative max-h-[46vh] overflow-y-auto py-5 pl-12 pr-5", compact && "max-h-64")}>
          {page.heading ? (
            <p className="mb-3 font-display text-sm font-medium text-ink">{page.heading}</p>
          ) : null}
          <div className="space-y-2.5 font-mono text-xs leading-[1.75] text-ink-soft">
            {page.lines.map((line, index) => {
              const isCited = citation.quote.includes(line) || quoteLines.includes(line);
              return (
                <p key={index} className="flex gap-3">
                  <span className="w-4 shrink-0 select-none text-right text-2xs text-ink-faint/60">
                    {index + 1}
                  </span>
                  {isCited ? (
                    <motion.span
                      ref={index === page.lines.findIndex((l) => citation.quote.includes(l)) ? highlightRef : undefined}
                      initial={reduce ? false : { backgroundSize: "0% 100%" }}
                      animate={{ backgroundSize: "100% 100%" }}
                      transition={{ duration: 0.42, ease: [0.32, 0.72, 0, 1], delay: 0.06 }}
                      className="highlight-clause bg-no-repeat px-1 text-ink"
                    >
                      {line}
                    </motion.span>
                  ) : (
                    <span className="px-1">{line}</span>
                  )}
                </p>
              );
            })}
          </div>
        </div>
      </motion.div>

      <blockquote className="border-l-2 border-[color-mix(in_oklab,var(--seal)_40%,transparent)] pl-3 text-sm italic leading-relaxed text-ink-soft">
        “{citation.quote}”
      </blockquote>
    </div>
  );
}

/** A schematic of where on the page the clause sits — orientation at a glance. */
function PageMap({
  pages,
  current,
  bbox,
}: {
  pages: number[];
  current: number;
  bbox: Citation["bbox"];
}) {
  const index = pages.indexOf(current);
  return (
    <span className="inline-flex items-center gap-2">
      <span className="font-mono text-2xs text-ink-faint">
        {index + 1}/{pages.length}
      </span>
      <svg viewBox="0 0 24 32" className="h-7 w-auto" aria-hidden>
        <rect x="0.6" y="0.6" width="22.8" height="30.8" rx="1.6" fill="var(--paper-sunk)" stroke="var(--line-strong)" strokeWidth="1" />
        <rect
          x={bbox.x * 24}
          y={bbox.y * 32}
          width={bbox.w * 24}
          height={Math.max(1.6, bbox.h * 32)}
          rx="0.8"
          fill="var(--gold-highlight)"
          stroke="var(--gold-highlight-edge)"
          strokeWidth="0.6"
        />
      </svg>
    </span>
  );
}
