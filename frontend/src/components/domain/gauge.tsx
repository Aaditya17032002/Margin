"use client";

import * as React from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";

import { cn } from "@/lib/utils";
import { stamp } from "@/lib/motion";
import { WaxSeal } from "./marks";
import type { Gate, GoNoGo } from "@/types";

/**
 * The gauge answers one question — how far open is the gate? — by reading the
 * four go/no-go gates rather than by taking a score as input. A hard gate that
 * is unmet shuts the needle down regardless of how well the rest reads, because
 * that is how the decision actually works.
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

const ARC_START = -212;
const ARC_END = 32;

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

  const dims = {
    sm: { box: 140, r: 52, stroke: 7, cx: 70, cy: 74 },
    md: { box: 200, r: 76, stroke: 9, cx: 100, cy: 106 },
    lg: { box: 260, r: 100, stroke: 11, cx: 130, cy: 138 },
  }[size];

  const toneVar = `var(--${verdict.tone})`;

  return (
    <div className={cn("relative inline-flex flex-col items-center", className)}>
      <svg
        viewBox={`0 0 ${dims.box} ${dims.box * 0.76}`}
        className="w-full max-w-full"
        role="img"
        aria-label={`Go/no-go reading: ${verdict.label}, ${Math.round(score * 100)} percent of gates satisfied`}
      >
        <path
          d={arcPath(dims.cx, dims.cy, dims.r, ARC_START, ARC_END)}
          fill="none"
          stroke="var(--paper-sunk)"
          strokeWidth={dims.stroke}
          strokeLinecap="round"
        />
        <path
          d={arcPath(dims.cx, dims.cy, dims.r, ARC_START, ARC_END)}
          fill="none"
          stroke="var(--line-strong)"
          strokeWidth={dims.stroke}
          strokeLinecap="round"
          opacity={0.5}
          strokeDasharray="1 7"
        />
        <motion.path
          d={arcPath(dims.cx, dims.cy, dims.r, ARC_START, Math.max(ARC_START + 0.4, angle))}
          fill="none"
          stroke={toneVar}
          strokeWidth={dims.stroke}
          strokeLinecap="round"
          initial={reduce ? false : { pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
        />

        {/* Needle — a machined pointer, weighted at the hub. */}
        <motion.g
          initial={reduce ? false : { rotate: ARC_START - 8 }}
          animate={{ rotate: angle }}
          transition={reduce ? { duration: 0 } : { type: "spring", stiffness: 90, damping: 15, mass: 1.1 }}
          style={{ originX: `${dims.cx}px`, originY: `${dims.cy}px` }}
        >
          <line
            x1={dims.cx}
            y1={dims.cy}
            x2={dims.cx + dims.r - dims.stroke * 1.6}
            y2={dims.cy}
            stroke="var(--ink)"
            strokeWidth={size === "sm" ? 1.6 : 2.2}
            strokeLinecap="round"
          />
        </motion.g>
        <circle cx={dims.cx} cy={dims.cy} r={size === "sm" ? 4 : 5.5} fill="var(--ink)" />
        <circle cx={dims.cx} cy={dims.cy} r={size === "sm" ? 1.6 : 2.2} fill="var(--paper-raised)" />

        <text
          x={dims.cx - dims.r + 2}
          y={dims.cy + 20}
          className="fill-[var(--ink-faint)] font-mono"
          fontSize={size === "sm" ? 7 : 9}
          textAnchor="middle"
        >
          NO-BID
        </text>
        <text
          x={dims.cx + dims.r - 2}
          y={dims.cy + 20}
          className="fill-[var(--ink-faint)] font-mono"
          fontSize={size === "sm" ? 7 : 9}
          textAnchor="middle"
        >
          BID
        </text>
      </svg>

      <div className="-mt-2 text-center">
        <p
          className={cn(
            "font-display leading-none",
            size === "sm" ? "text-lg" : size === "md" ? "text-2xl" : "text-3xl",
          )}
          style={{ color: toneVar }}
        >
          {verdict.label}
        </p>
        <p className="mt-1 font-mono text-2xs uppercase tracking-[0.13em] text-ink-faint">
          {gates.filter((g) => g.met === true).length} of {gates.length} gates met
        </p>
      </div>

      <AnimatePresence>
        {showSeal && hardFailed ? (
          <motion.div
            initial={reduce ? { opacity: 0 } : { opacity: 0, scale: 1.6, rotate: -22 }}
            animate={reduce ? { opacity: 1 } : { opacity: 1, scale: 1, rotate: -11 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={reduce ? { duration: 0.2 } : { ...stamp, delay: 0.55 }}
            className="pointer-events-none absolute -right-1 top-2"
          >
            <WaxSeal className={size === "sm" ? "size-11" : "size-16"} label="A hard gate is unmet" />
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
