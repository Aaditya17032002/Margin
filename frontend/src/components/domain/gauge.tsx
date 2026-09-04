"use client";

import * as React from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";

import { cn } from "@/lib/utils";
import { stamp } from "@/lib/motion";
import { WaxSeal } from "./marks";
import type { Gate, GoNoGo } from "@/types";

/**
 * The gauge answers one question — how far open is the gate? — by reading the
 * analysis's own gates rather than by taking a score as input. A hard gate that
 * is unmet caps the reading regardless of how well the rest reads, because that
 * is how the decision actually works.
 */
export function gateScore(gates: Gate[]) {
  if (gates.length === 0) return 0;
  const hard = gates.filter((g) => g.weight === "hard");
  const failedHard = hard.filter((g) => g.met === false).length;
  const value = gates.reduce((sum, gate) => {
    const weight = gate.weight === "hard" ? 1 : 0.55;
    const points = gate.met === true ? 1 : gate.met === null ? 0.5 : 0;
    return sum + points * weight;
  }, 0);
  const total = gates.reduce((sum, gate) => sum + (gate.weight === "hard" ? 1 : 0.55), 0);
  const raw = value / total;
  // Any unmet hard gate caps the reading — the gate cannot be more than ajar.
  return failedHard > 0 ? Math.min(raw, 0.34 / failedHard) : raw;
}

export function verdictFor(score: number, decision: GoNoGo) {
  if (decision === "bid") return { label: "Bid", tone: "leaf" as const };
  if (decision === "no-bid") return { label: "No-bid", tone: "seal" as const };
  if (decision === "watch") return { label: "Watch", tone: "slate" as const };
  if (score >= 0.72) return { label: "Leaning bid", tone: "leaf" as const };
  if (score >= 0.42) return { label: "Unresolved", tone: "ochre" as const };
  return { label: "Leaning no-bid", tone: "seal" as const };
}

/**
 * A true half-circle: the baseline is flat, the ends sit level with it, and
 * NO-BID and BID label the two ends from below where nothing can reach them.
 * The old arc opened past horizontal on both sides, which pushed its end
 * labels up into the verdict line.
 */
const ARC_START = 180;
const ARC_END = 360;

/** One geometry, scaled by CSS. Text inside the SVG scales with the dial. */
const BOX = { w: 240, h: 134, cx: 120, cy: 108, r: 88, stroke: 10 };

const SIZE_WIDTH = { sm: "10rem", md: "15rem", lg: "19rem" } as const;

function polar(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = (angleDeg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function arcPath(cx: number, cy: number, r: number, from: number, to: number) {
  const start = polar(cx, cy, r, from);
  const end = polar(cx, cy, r, to);
  const large = Math.abs(to - from) > 180 ? 1 : 0;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${large} 1 ${end.x} ${end.y}`;
}

/** Eleven ticks, one per tenth, drawn just outside the band. */
const TICKS = Array.from({ length: 11 }, (_, i) => i / 10);

export function GoNoGoGauge({
  gates,
  decision,
  size = "md",
  className,
  showSeal = true,
}: {
  gates: Gate[];
  decision: GoNoGo;
  size?: "sm" | "md" | "lg";
  className?: string;
  showSeal?: boolean;
}) {
  const reduce = useReducedMotion();
  const score = gateScore(gates);
  const verdict = verdictFor(score, decision);
  const angle = ARC_START + (ARC_END - ARC_START) * score;
  const hardFailed = gates.some((g) => g.weight === "hard" && g.met === false);
  const met = gates.filter((g) => g.met === true).length;

  const toneVar = `var(--${verdict.tone})`;
  const marker = polar(BOX.cx, BOX.cy, BOX.r, angle);
  const track = arcPath(BOX.cx, BOX.cy, BOX.r, ARC_START, ARC_END);

  return (
    <div
      className={cn("relative inline-flex w-full flex-col items-center", className)}
      style={{ maxWidth: SIZE_WIDTH[size] }}
    >
      <svg
        viewBox={`0 0 ${BOX.w} ${BOX.h}`}
        className="w-full overflow-visible"
        role="img"
        aria-label={`Go/no-go reading: ${verdict.label}, ${met} of ${gates.length} gates met, ${Math.round(score * 100)} percent`}
      >
        {/* The band a reader measures against: one solid, quiet stroke. A
            dotted track reads as decoration and makes the dial look drawn
            rather than machined. */}
        <path
          d={track}
          fill="none"
          stroke="var(--paper-sunk)"
          strokeWidth={BOX.stroke}
          strokeLinecap="round"
        />
        <path
          d={track}
          fill="none"
          stroke="var(--line)"
          strokeWidth={1}
          strokeLinecap="round"
          opacity={0.9}
        />

        <g stroke="var(--line-strong)" strokeLinecap="round">
          {TICKS.map((t) => {
            const a = ARC_START + (ARC_END - ARC_START) * t;
            const major = t === 0 || t === 0.5 || t === 1;
            const inner = polar(BOX.cx, BOX.cy, BOX.r + BOX.stroke / 2 + 3, a);
            const outer = polar(BOX.cx, BOX.cy, BOX.r + BOX.stroke / 2 + (major ? 9 : 6), a);
            return (
              <line
                key={t}
                x1={inner.x}
                y1={inner.y}
                x2={outer.x}
                y2={outer.y}
                strokeWidth={major ? 1.6 : 1}
                opacity={major ? 0.9 : 0.5}
              />
            );
          })}
        </g>

        {/* The reading itself. `pathLength` keeps the sweep proportional to the
            arc, so the fill and the marker arrive together. */}
        <motion.path
          d={arcPath(BOX.cx, BOX.cy, BOX.r, ARC_START, Math.max(ARC_START + 0.35, angle))}
          fill="none"
          stroke={toneVar}
          strokeWidth={BOX.stroke}
          strokeLinecap="round"
          initial={reduce ? false : { pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: reduce ? 0 : 0.85, ease: [0.16, 1, 0.3, 1] }}
        />

        {/* A marker where the reading lands, instead of a needle. A needle on a
            half dial sweeps straight through the verdict at the halfway mark,
            which is precisely where an unresolved analysis sits. */}
        <motion.g
          initial={reduce ? false : { opacity: 0, scale: 0.6 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: reduce ? 0 : 0.55, duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
          style={{ originX: `${marker.x}px`, originY: `${marker.y}px` }}
        >
          <circle cx={marker.x} cy={marker.y} r={BOX.stroke / 2 + 2.5} fill="var(--paper-raised)" />
          <circle cx={marker.x} cy={marker.y} r={BOX.stroke / 2 - 0.5} fill={toneVar} />
          <circle cx={marker.x} cy={marker.y} r={BOX.stroke / 2 - 3.4} fill="var(--paper-raised)" />
        </motion.g>

        {/* The verdict lives inside the dial, above the baseline — the one
            place on a half-circle nothing else occupies. */}
        <text
          x={BOX.cx}
          y={BOX.cy - 30}
          textAnchor="middle"
          className="font-display"
          fill={toneVar}
          fontSize={22}
          style={{ letterSpacing: "-0.01em" }}
        >
          {verdict.label}
        </text>
        <text
          x={BOX.cx}
          y={BOX.cy - 12}
          textAnchor="middle"
          className="fill-[var(--ink-faint)] font-mono"
          fontSize={8}
          style={{ letterSpacing: "0.12em" }}
        >
          {met} OF {gates.length} GATES MET
        </text>

        {/* Below the baseline, level with the arc ends, anchored outward so
            they lean away from the dial rather than into it. */}
        <text
          x={BOX.cx - BOX.r}
          y={BOX.cy + 18}
          textAnchor="start"
          className="fill-[var(--ink-faint)] font-mono"
          fontSize={8}
          style={{ letterSpacing: "0.1em" }}
        >
          NO-BID
        </text>
        <text
          x={BOX.cx + BOX.r}
          y={BOX.cy + 18}
          textAnchor="end"
          className="fill-[var(--ink-faint)] font-mono"
          fontSize={8}
          style={{ letterSpacing: "0.1em" }}
        >
          BID
        </text>
      </svg>

      <AnimatePresence>
        {showSeal && hardFailed ? (
          <motion.div
            initial={reduce ? { opacity: 0 } : { opacity: 0, scale: 1.6, rotate: -22 }}
            animate={reduce ? { opacity: 1 } : { opacity: 1, scale: 1, rotate: -11 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={reduce ? { duration: 0.2 } : { ...stamp, delay: 0.55 }}
            className="pointer-events-none absolute -right-2 bottom-0"
          >
            <WaxSeal className={size === "sm" ? "size-11" : "size-14"} label="A hard gate is unmet" />
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

/** A compact reading for the workspace header and list rows. */
export function MiniGauge({ gates, decision }: { gates: Gate[]; decision: GoNoGo }) {
  const score = gateScore(gates);
  const verdict = verdictFor(score, decision);
  return (
    <span className="inline-flex items-center gap-2">
      <span className="relative inline-flex h-1.5 w-16 overflow-hidden rounded-full bg-paper-sunk ring-1 ring-inset ring-[var(--line)]">
        <motion.span
          className="h-full rounded-full"
          style={{ backgroundColor: `var(--${verdict.tone})` }}
          initial={{ width: 0 }}
          animate={{ width: `${Math.max(6, score * 100)}%` }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        />
      </span>
      <span className="text-xs font-medium" style={{ color: `var(--${verdict.tone})` }}>
        {verdict.label}
      </span>
    </span>
  );
}
