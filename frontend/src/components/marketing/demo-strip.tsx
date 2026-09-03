"use client";

import * as React from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";

import { Quote } from "lucide-react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

interface DemoFinding {
  id: string;
  label: string;
  value: string;
  stakes: "disqualifying" | "scored";
  page: number;
  section: string;
  line: number;
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
    value: "Volume I is capped at 40 pages, excluding resumes and the matrix.",
    stakes: "disqualifying",
    page: 47,
    section: "L.3.1",
    line: 1,
  },
  {
    id: "d2",
    label: "Type size",
    value: "12-point Times New Roman; tables may drop to 10-point.",
    stakes: "disqualifying",
    page: 47,
    section: "L.3.2",
    line: 4,
  },
  {
    id: "d3",
    label: "Proposal due",
    value: "2:00 p.m. Central. Late submissions fall under FAR 52.215-1.",
    stakes: "disqualifying",
    page: 48,
    section: "L.4.1",
    line: 6,
  },
];

/**
 * A working fragment of the workspace: findings on the left, the cited page
 * on the right. Height comes from the content, not from padding around it.
 */
export function DemoStrip({ className }: { className?: string }) {
  const { finding, take } = useDemoCycle();

  return (
    <div
      className={cn(
        "grid overflow-hidden rounded-lg border border-line bg-line shadow-[var(--shadow-raised)]",
        "sm:grid-cols-[minmax(13rem,0.9fr)_minmax(0,1.2fr)]",
        className,
      )}
    >
      <FindingList finding={finding} take={take} />
      <SourcePage finding={finding} />
    </div>
  );
}

/**
 * The product idea as a page: argument in the margin, source on the sheet.
 * Not a second copy of the workspace card.
 */
export function ManuscriptDemo({ className }: { className?: string }) {
  const { finding, take } = useDemoCycle();

  return (
    <div className={cn("min-w-0", className)}>
      <div className="flex flex-wrap gap-2 pb-4">
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
                "inline-flex h-8 items-center gap-2 rounded-md border px-2.5 font-mono text-xs leading-none",
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
    }, 3400);
    return () => window.clearInterval(id);
  }, [manual, reduce]);

  const finding = FINDINGS.find((f) => f.id === active) ?? FINDINGS[0];
  const take = (id: string) => {
    setManual(true);
    setActive(id);
  };

  return { finding, take };
}

function FindingList({
  finding,
  take,
}: {
  finding: DemoFinding;
  take: (id: string) => void;
}) {
  return (
    <div className="flex flex-col bg-paper-raised">
      <div className="flex items-baseline justify-between gap-3 border-b border-line px-3.5 py-2.5">
        <p className="eyebrow">Findings</p>
        <p className="font-mono text-2xs text-ink-faint">TEA-2026-RFP-0147</p>
      </div>
      <ul>
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
                  "w-full px-3.5 py-3 text-left transition-colors duration-150",
                  on ? "bg-paper-sunk" : "hover:bg-paper-sunk/50",
                )}
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-ink">{item.label}</span>
                  {on ? (
                    <Badge tone={item.stakes === "disqualifying" ? "seal" : "ochre"}>
                      {item.stakes === "disqualifying" ? "Hard" : "Scored"}
                    </Badge>
                  ) : null}
                </div>
                {on ? (
                  <>
                    <p className="mt-1.5 text-xs leading-snug text-ink-soft">{item.value}</p>
                    <p className="mt-2.5 inline-flex h-7 items-center gap-1.5 rounded-md border border-patina bg-patina-tint px-2 font-mono text-xs text-patina">
                      <Quote className="size-3 opacity-70" aria-hidden />
                      p.{item.page}
                      <span className="text-patina/60" aria-hidden>
                        ·
                      </span>
                      {item.section}
                    </p>
                  </>
                ) : (
                  <p className="mt-1 font-mono text-2xs text-ink-faint">
                    p.{item.page} · {item.section}
                  </p>
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function SourcePage({ finding, framed = false }: { finding: DemoFinding; framed?: boolean }) {
  const start = Math.max(0, finding.line - 1);
  const end = Math.min(PAGE_LINES.length, start + 5);
  const lines = PAGE_LINES.slice(start, end);

  return (
    <div className={cn("bg-paper-sunk", framed && "overflow-hidden rounded-md border border-line")}>
      <div className="flex items-baseline justify-between gap-3 border-b border-line px-3.5 py-2">
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
      <div className="relative px-3.5 py-2.5">
        <span
          aria-hidden
          className="pointer-events-none absolute inset-y-2.5 left-[2.65rem] w-px bg-[color-mix(in_oklab,var(--seal)_28%,transparent)]"
        />
        <div className="space-y-0.5 font-mono text-[11px] leading-[1.6] text-ink-soft">
          {lines.map((line, i) => {
            const index = start + i;
            const lit = index >= finding.line && index <= finding.line + 1;
            return (
              <p key={index} className="flex gap-2.5">
                <span className="w-4 shrink-0 select-none text-right text-2xs text-ink-faint/55 tabular">
                  {index + 1}
                </span>
                <span className={cn("min-w-0", lit && "highlight-clause text-ink")}>{line}</span>
              </p>
            );
          })}
        </div>
      </div>
    </div>
  );
}
