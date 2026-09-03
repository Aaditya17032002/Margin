"use client";

import * as React from "react";
import { motion, useReducedMotion } from "motion/react";

import { cn } from "@/lib/utils";
import { useNow } from "@/hooks/use-now";
import { CitationMeta } from "./primitives";
import type { EvaluationFactor } from "@/types";

const RING_TONES = ["var(--patina)", "var(--ochre)", "var(--slate)", "var(--leaf)", "var(--seal)"];

/**
 * The evaluation donut is drawn as a set of arcs on a shared radius rather than
 * as a filled pie, so a 10-point factor stays legible next to a 35-point one
 * without a legend blowout.
 */
export function EvaluationDonut({
  factors,
  analysisId,
  className,
}: {
  factors: EvaluationFactor[];
  analysisId: string;
  className?: string;
}) {
  const reduce = useReducedMotion();
  const [active, setActive] = React.useState<string | null>(null);
  const total = factors.reduce((sum, f) => sum + f.weight, 0) || 1;
  const radius = 62;
  const circumference = 2 * Math.PI * radius;

  const arcs = factors.map((factor, index) => {
    const fraction = factor.weight / total;
    const preceding = factors.slice(0, index).reduce((sum, f) => sum + f.weight, 0) / total;
    return {
      factor,
      tone: RING_TONES[index % RING_TONES.length],
      dash: fraction * circumference,
      gap: circumference - fraction * circumference,
      offset: -preceding * circumference,
    };
  });

  const highlighted = factors.find((f) => f.id === active);

  return (
    <div className={cn("flex flex-wrap items-start gap-8", className)}>
      <div className="relative shrink-0">
        <svg viewBox="0 0 160 160" className="size-40 -rotate-90" role="img" aria-label="Evaluation weights">
          <circle cx="80" cy="80" r={radius} fill="none" stroke="var(--paper-sunk)" strokeWidth="15" />
          {arcs.map(({ factor, tone, dash, gap, offset }) => (
            <motion.circle
              key={factor.id}
              cx="80"
              cy="80"
              r={radius}
              fill="none"
              stroke={tone}
              strokeWidth={active === factor.id ? 19 : 15}
              strokeDasharray={`${Math.max(0, dash - 2)} ${gap + 2}`}
              strokeDashoffset={offset}
              strokeLinecap="butt"
              initial={reduce ? false : { opacity: 0 }}
              animate={{ opacity: active && active !== factor.id ? 0.32 : 1 }}
              transition={{ duration: 0.24, ease: [0.32, 0.72, 0, 1] }}
              onMouseEnter={() => setActive(factor.id)}
              onMouseLeave={() => setActive(null)}
              className="cursor-default transition-[stroke-width] duration-200"
            />
          ))}
        </svg>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-display text-2xl leading-none text-ink tabular">
            {highlighted ? highlighted.weight : total}
          </span>
          <span className="mt-1 max-w-24 text-center font-mono text-2xs uppercase tracking-[0.1em] text-ink-faint">
            {highlighted ? "points" : "total points"}
          </span>
        </div>
      </div>

      <ul className="min-w-0 flex-1 space-y-0">
        {arcs.map(({ factor, tone }) => (
          <li
            key={factor.id}
            onMouseEnter={() => setActive(factor.id)}
            onMouseLeave={() => setActive(null)}
            className={cn(
              "space-y-2.5 border-b border-line py-3.5 last:border-b-0",
              "transition-opacity duration-200",
              active && active !== factor.id && "opacity-55",
            )}
          >
            <div className="flex items-baseline gap-3">
              <span
                aria-hidden
                className="mt-1.5 size-2 shrink-0 rounded-[1px]"
                style={{ backgroundColor: tone }}
              />
              <div className="min-w-0 flex-1">
                <p className="text-sm text-ink">{factor.name}</p>
                <p className="text-xs text-ink-faint">{factor.method}</p>
              </div>
              <span className="shrink-0 font-mono text-sm tabular text-ink-soft">{factor.weight}</span>
            </div>
            <CitationMeta
              className="ml-5"
              citation={factor.citation}
              analysisId={analysisId}
              label={factor.name}
              origin="Evaluation"
              compact
              clamp={2}
            />
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Confidence spread across a set of findings — a quick read on how solid a pass was. */
export function ConfidenceDistribution({
  confidences,
  className,
}: {
  confidences: number[];
  className?: string;
}) {
  const reduce = useReducedMotion();
  const buckets = [
    { label: "<75", min: 0, max: 0.75, tone: "var(--seal)" },
    { label: "75–84", min: 0.75, max: 0.85, tone: "var(--ochre)" },
    { label: "85–92", min: 0.85, max: 0.93, tone: "var(--slate)" },
    { label: "93+", min: 0.93, max: 1.01, tone: "var(--leaf)" },
  ].map((bucket) => ({
    ...bucket,
    count: confidences.filter((c) => c >= bucket.min && c < bucket.max).length,
  }));
  const max = Math.max(1, ...buckets.map((b) => b.count));

  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex h-24 items-end gap-2">
        {buckets.map((bucket) => (
          <div key={bucket.label} className="flex flex-1 flex-col items-center gap-1.5">
            <span className="font-mono text-2xs tabular text-ink-faint">{bucket.count}</span>
            <motion.div
              className="w-full rounded-t-[2px]"
              style={{ backgroundColor: bucket.tone }}
              initial={reduce ? false : { height: 0 }}
              animate={{ height: `${Math.max(3, (bucket.count / max) * 72)}px` }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            />
          </div>
        ))}
      </div>
      <div className="flex gap-2 border-t border-line pt-1.5">
        {buckets.map((bucket) => (
          <span key={bucket.label} className="flex-1 text-center font-mono text-2xs text-ink-faint">
            {bucket.label}
          </span>
        ))}
      </div>
    </div>
  );
}

/** A horizontal timeline of the dates in a solicitation. */
export function DeadlineTimeline({
  points,
  className,
}: {
  points: { id: string; label: string; at: string; tone: string }[];
  className?: string;
}) {
  const reduce = useReducedMotion();
  // Zero until the client takes over, which parks "today" at the left edge for
  // exactly one frame rather than mismatching the server's idea of now.
  const now = useNow(60_000);

  if (points.length === 0) return null;

  const times = points.map((p) => new Date(p.at).getTime());
  const min = Math.min(...times, now || Math.min(...times));
  const max = Math.max(...times);
  const span = Math.max(1, max - min);
  const nowPct = now === 0 ? 0 : ((now - min) / span) * 100;

  return (
    <div className={cn("relative pb-12 pt-8", className)}>
      <div className="relative h-px w-full bg-line">
        <motion.div
          className="absolute inset-y-0 left-0 bg-patina"
          initial={reduce ? false : { width: 0 }}
          animate={{ width: `${Math.max(0, Math.min(100, nowPct))}%` }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        />
        <span
          className="absolute top-1/2 z-10 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-[var(--paper-raised)] bg-ink"
          style={{ left: `${Math.max(0, Math.min(100, nowPct))}%` }}
          aria-label="Today"
        />
        {points.map((point, index) => {
          const pct = ((new Date(point.at).getTime() - min) / span) * 100;
          const above = index % 2 === 0;
          return (
            <div
              key={point.id}
              className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2"
              style={{ left: `${Math.max(0, Math.min(100, pct))}%` }}
            >
              <span
                className="block size-2 rounded-full ring-2 ring-[var(--paper-raised)]"
                style={{ backgroundColor: point.tone }}
              />
              <span
                className={cn(
                  "absolute left-1/2 w-28 -translate-x-1/2 text-center text-2xs leading-tight text-ink-soft",
                  above ? "bottom-4" : "top-4",
                )}
              >
                {point.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
