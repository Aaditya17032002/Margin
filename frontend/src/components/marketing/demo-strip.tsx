"use client";

import * as React from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { Quote } from "lucide-react";

import { cn } from "@/lib/utils";

interface DemoFinding {
  id: string;
  label: string;
  value: string;
  stakes: "disqualifying" | "scored";
  page: number;
  section: string;
  /** Index into PAGE_LINES where the supporting clause begins. */
  line: number;
  span: number;
}

const PAGE_LINES = [
  "L.3.1  The offeror shall submit its proposal in two separate volumes.",
  "Volume I, Technical, shall not exceed forty (40) pages, excluding",
  "resumes, letters of commitment, and the cross-reference matrix.",
  "Volume II, Price, is not page limited.",
  "L.3.2  Text shall be no smaller than 12-point Times New Roman.",
  "Tables and figures may use 10-point type if legible at 100 percent.",
  "L.4.1  Proposals are due no later than 2:00 p.m. Central Time.",
  "Late proposals will be handled in accordance with FAR 52.215-1(c)(3).",
];

const FINDINGS: DemoFinding[] = [
  {
    id: "d1",
    label: "Page limit",
    value: "Volume I is capped at 40 pages, excluding resumes and the cross-reference matrix.",
    stakes: "disqualifying",
    page: 47,
    section: "L.3.1",
    line: 1,
    span: 2,
  },
  {
    id: "d2",
    label: "Type size",
    value: "12-point Times New Roman throughout; tables may drop to 10-point if legible.",
    stakes: "disqualifying",
    page: 47,
    section: "L.3.2",
    line: 4,
    span: 2,
  },
  {
    id: "d3",
    label: "Proposal due",
    value: "2:00 p.m. Central. Anything later falls under FAR 52.215-1(c)(3).",
    stakes: "disqualifying",
    page: 48,
    section: "L.4.1",
    line: 6,
    span: 2,
  },
];

/**
 * The product in one frame: findings on the left, the page they stand on to
 * the right, and a highlight that moves as attention moves. This is the whole
 * argument for Margin, so on the landing page it is given room to be read
 * rather than compressed into a thumbnail.
 */
export function DemoStrip({ className }: { className?: string }) {
  const { finding, take } = useDemoCycle();

  return (
    <div
      className={cn(
        "grid overflow-hidden rounded-xl border border-line bg-line/70 shadow-[var(--shadow-float)]",
        // Stacked on a phone, the single column still needs a zero minimum or
        // the monospaced clause below widens the whole page.
        "grid-cols-[minmax(0,1fr)] lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]",
        className,
      )}
    >
      <FindingList finding={finding} take={take} />
      <SourcePage finding={finding} />
    </div>
  );
}

/**
 * The same idea told as a page rather than a product screenshot: the citation
 * chips read as marginalia, and the sheet below is the document itself.
 */
export function ManuscriptDemo({ className }: { className?: string }) {
  const { finding, take } = useDemoCycle();

  return (
    <div className={cn("min-w-0", className)}>
      <div className="flex flex-wrap gap-2 pb-5">
        {FINDINGS.map((item) => {
          const on = item.id === finding.id;
          return (
            <button
              key={item.id}
              type="button"
              onMouseEnter={() => take(item.id)}
              onFocus={() => take(item.id)}
              onClick={() => take(item.id)}
              aria-pressed={on}
              className={cn(
                "inline-flex h-9 items-center gap-2 rounded-md border px-3 font-mono text-xs leading-none",
                "transition-colors duration-150",
                on
                  ? "border-patina bg-patina-tint text-patina"
                  : "border-line-strong bg-paper-raised text-ink-soft hover:border-patina hover:text-patina",
              )}
            >
              <Quote className="size-3.5 shrink-0 opacity-70" aria-hidden />
              <span className="flex items-baseline gap-1.5 whitespace-nowrap">
                <span className={cn("tabular", on ? "text-patina" : "text-ink")}>p.{item.page}</span>
                <span className="text-ink-faint/70" aria-hidden>
                  ·
                </span>
                <span>{item.section}</span>
              </span>
            </button>
          );
        })}
      </div>
      <SourcePage finding={finding} framed />
    </div>
  );
}

function useDemoCycle() {
  const reduce = useReducedMotion();
  const [active, setActive] = React.useState(FINDINGS[0].id);
  const [manual, setManual] = React.useState(false);

  React.useEffect(() => {
    if (manual || reduce) return;
    const id = window.setInterval(() => {
      setActive((current) => {
        const index = FINDINGS.findIndex((f) => f.id === current);
        return FINDINGS[(index + 1) % FINDINGS.length].id;
      });
    }, 3800);
    return () => window.clearInterval(id);
  }, [manual, reduce]);

  const finding = FINDINGS.find((f) => f.id === active) ?? FINDINGS[0];
  const take = (id: string) => {
    setManual(true);
    setActive(id);
  };

  return { finding, take };
}

function FindingList({ finding, take }: { finding: DemoFinding; take: (id: string) => void }) {
  const reduce = useReducedMotion();

  return (
    <div className="flex flex-col bg-paper-raised">
      <div className="flex items-baseline justify-between gap-3 border-b border-line px-5 py-3.5">
        <p className="eyebrow">Findings</p>
        <p className="font-mono text-2xs text-ink-faint">TEA-2026-RFP-0147</p>
      </div>
      <ul className="flex-1">
        {FINDINGS.map((item) => {
          const on = item.id === finding.id;
          return (
            <li key={item.id} className="border-b border-line last:border-b-0">
              <button
                type="button"
                onMouseEnter={() => take(item.id)}
                onFocus={() => take(item.id)}
                onClick={() => take(item.id)}
                aria-pressed={on}
                className={cn(
                  "relative w-full px-5 py-4 text-left transition-colors duration-200",
                  on ? "bg-paper-sunk" : "hover:bg-paper-sunk/50",
                )}
              >
                {on ? (
                  <motion.span
                    layoutId="demo-marker"
                    transition={reduce ? { duration: 0 } : { type: "spring", stiffness: 460, damping: 40 }}
                    aria-hidden
                    className="absolute inset-y-0 left-0 w-[3px] bg-patina"
                  />
                ) : null}
                <div className="flex items-center gap-2.5">
                  <span className="text-sm font-medium text-ink">{item.label}</span>
                  <span
                    className={cn(
                      "font-mono text-2xs uppercase tracking-[0.1em] transition-colors",
                      on ? "text-seal" : "text-ink-faint/70",
                    )}
                  >
                    {item.stakes === "disqualifying" ? "Hard" : "Scored"}
                  </span>
                </div>
                <p
                  className={cn(
                    "mt-1.5 text-sm leading-relaxed transition-colors",
                    on ? "text-ink-soft" : "text-ink-faint",
                  )}
                >
                  {item.value}
                </p>
                <p
                  className={cn(
                    "mt-3 inline-flex h-7 items-center gap-1.5 rounded-md border px-2.5 font-mono text-xs transition-colors",
                    on
                      ? "border-patina bg-patina-tint text-patina"
                      : "border-transparent text-ink-faint",
                  )}
                >
                  <Quote className="size-3 opacity-70" aria-hidden />
                  p.{item.page}
                  <span className="opacity-60" aria-hidden>
                    ·
                  </span>
                  {item.section}
                </p>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function SourcePage({ finding, framed = false }: { finding: DemoFinding; framed?: boolean }) {
  const reduce = useReducedMotion();

  return (
    <div className={cn("bg-paper-sunk", framed && "overflow-hidden rounded-lg border border-line")}>
      <div className="flex items-baseline justify-between gap-3 border-b border-line px-5 py-3.5">
        <p className="eyebrow">The Margin</p>
        <AnimatePresence mode="wait">
          <motion.p
            key={finding.id}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.16 }}
            className="font-mono text-2xs text-ink-faint"
          >
            p.{finding.page} · {finding.section}
          </motion.p>
        </AnimatePresence>
      </div>
      <div className="relative px-5 py-5">
        {/* The red rule a printed solicitation carries down its binding edge. */}
        <span
          aria-hidden
          className="pointer-events-none absolute inset-y-5 left-[3.15rem] w-px bg-[color-mix(in_oklab,var(--seal)_26%,transparent)]"
        />
        <div className="space-y-1 font-mono text-xs leading-[1.85] text-ink-soft">
          {PAGE_LINES.map((line, index) => {
            const lit = index >= finding.line && index < finding.line + finding.span;
            return (
              <p key={index} className="flex gap-3">
                <span className="w-5 shrink-0 select-none text-right text-2xs text-ink-faint/55 tabular">
                  {index + 1}
                </span>
                <span className="relative min-w-0 break-words">
                  {/* The highlight fades rather than sliding: two lines light at
                      once, and a shared layout id cannot be in two places. */}
                  <motion.span
                    aria-hidden
                    initial={false}
                    animate={{ opacity: lit ? 1 : 0 }}
                    transition={{ duration: reduce ? 0 : 0.24, ease: [0.32, 0.72, 0, 1] }}
                    className="highlight-clause absolute -inset-x-1 inset-y-0 -z-10 rounded-sm"
                  />
                  {/* Wrapped rather than scrolled: on a phone a clause that
                      runs off the edge is worse than one that takes two lines. */}
                  <span className={cn("transition-colors duration-200", lit ? "text-ink" : undefined)}>
                    {line}
                  </span>
                </span>
              </p>
            );
          })}
        </div>
      </div>
    </div>
  );
}
