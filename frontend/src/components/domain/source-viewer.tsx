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
  const span = useCitedLines(citation, page?.lines);

  React.useEffect(() => {
    highlightRef.current?.scrollIntoView({
      block: "center",
      behavior: reduce ? "auto" : "smooth",
    });
  }, [citation.id, reduce]);

  if (!page) {
    return <Unlocated citation={citation} reason="missing-page" />;
  }
  if (citation.located === false) {
    return <Unlocated citation={citation} reason="unmatched" />;
  }

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
              const isCited = span !== null && index >= span[0] && index <= span[1];
              return (
                <p key={index} className="flex gap-3">
                  <span className="w-4 shrink-0 select-none text-right text-2xs text-ink-faint/60">
                    {index + 1}
                  </span>
                  {isCited ? (
                    <motion.span
                      ref={index === span[0] ? highlightRef : undefined}
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

/**
 * Which lines of the page the quote covers.
 *
 * The backend resolves this when it grounds the citation, and that answer is
 * authoritative — it searched the whole document, not one page. The client-side
 * match is only for citations written before grounding existed, and it is
 * deliberately strict: the old code asked whether the quote *contained* the
 * line, which is true of every blank line on the page, so every source view
 * opened with the empty lines lit up and scrolled to the first of them.
 */
function useCitedLines(
  citation: Citation,
  lines: string[] | undefined,
): [number, number] | null {
  return React.useMemo(() => {
    const given = citation.lines;
    if (Array.isArray(given) && given.length === 2) {
      const [first, last] = given;
      if (Number.isInteger(first) && Number.isInteger(last) && first >= 0) {
        return [first, Math.max(first, last)];
      }
    }
    if (!lines?.length) return null;

    const needle = squash(citation.quote);
    if (needle.length < 16) return null;

    let first = -1;
    let last = -1;
    for (let i = 0; i < lines.length; i += 1) {
      const line = squash(lines[i]);
      // A line counts as cited only if it carries real text that the quote
      // actually contains — eight characters is past "the", "and", "1.".
      if (line.length >= 8 && needle.includes(line)) {
        if (first === -1) first = i;
        last = i;
      }
    }
    return first === -1 ? null : [first, last];
  }, [citation.lines, citation.quote, lines]);
}

function squash(text: string): string {
  return text
    .replace(/[\u2018\u2019]/g, "'")
    .replace(/[\u201c\u201d]/g, '"')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");
}

/**
 * A citation with no home in the document. Saying that plainly is worth more
 * than a highlight over an arbitrary line: it tells a reader this one finding
 * needs checking, without casting doubt on the rest of the page.
 */
function Unlocated({ citation, reason }: { citation: Citation; reason: "missing-page" | "unmatched" }) {
  return (
    <div className="space-y-3">
      <div className="rounded-md border border-dashed border-line-strong bg-paper-sunk px-4 py-5">
        <p className="text-sm font-medium text-ink">
          {reason === "missing-page"
            ? `Page ${citation.page} is not in the indexed extract.`
            : "This quote could not be found in the document."}
        </p>
        <p className="mt-1.5 text-xs leading-relaxed text-ink-faint">
          {reason === "missing-page"
            ? "The document may have been re-uploaded since this pass ran. Re-run the analysis to re-anchor its sources."
            : "Margin anchors every citation by searching the extract for the quoted text. This one did not match, so the finding is shown without a source rather than pointed at the wrong clause."}
        </p>
      </div>
      {citation.quote ? (
        <blockquote className="border-l-2 border-[color-mix(in_oklab,var(--seal)_40%,transparent)] pl-3 text-sm italic leading-relaxed text-ink-soft">
          “{citation.quote}”
        </blockquote>
      ) : null}
    </div>
  );
}
