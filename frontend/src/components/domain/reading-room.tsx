"use client";

import * as React from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { Check } from "lucide-react";

import { cn } from "@/lib/utils";
import { AGENT_BY_ID } from "@/data/agents";
import type { AgentId } from "@/types";

export type AgentPhase = "waiting" | "reading" | "done";

/**
 * The agent roster. Reading is shown as a queue of specialists working in
 * sequence — the honest shape of what is happening — rather than as a spinner
 * that says nothing. Each name lights as its pass begins and settles when the
 * pass is finished.
 */
export function AgentRoster({
  agents,
  phases,
  className,
}: {
  agents: AgentId[];
  phases: Record<string, AgentPhase>;
  className?: string;
}) {
  const reduce = useReducedMotion();
  return (
    <ol className={cn("space-y-0", className)}>
      {agents.map((id, index) => {
        const agent = AGENT_BY_ID[id];
        const phase = phases[id] ?? "waiting";
        return (
          <li key={id} className="relative flex gap-3.5 pb-5 last:pb-0">
            {index < agents.length - 1 ? (
              <span
                aria-hidden
                className={cn(
                  "absolute left-[13px] top-7 h-[calc(100%-1.75rem)] w-px transition-colors duration-500",
                  phase === "done" ? "bg-patina" : "bg-line",
                )}
              />
            ) : null}

            <span
              className={cn(
                "relative z-10 flex size-[26px] shrink-0 items-center justify-center rounded-full border",
                "transition-[background-color,border-color,color] duration-300 ease-[cubic-bezier(0.32,0.72,0,1)]",
                phase === "done" && "border-patina bg-patina text-[var(--patina-ink)]",
                phase === "reading" && "border-patina bg-patina-tint text-patina",
                phase === "waiting" && "border-line-strong bg-paper-sunk text-ink-faint",
              )}
            >
              {phase === "done" ? (
                <Check className="size-3.5" strokeWidth={3} aria-hidden />
              ) : phase === "reading" ? (
                <motion.span
                  className="size-2 rounded-full bg-patina"
                  animate={reduce ? undefined : { opacity: [1, 0.35, 1] }}
                  transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
                />
              ) : (
                <span className="font-mono text-2xs">{index + 1}</span>
              )}
            </span>

            <div className="min-w-0 pt-0.5">
              <p
                className={cn(
                  "text-sm font-medium transition-colors duration-300",
                  phase === "waiting" ? "text-ink-faint" : "text-ink",
                )}
              >
                {agent.name}
              </p>
              <p
                className={cn(
                  "text-xs leading-snug transition-opacity duration-300",
                  phase === "waiting" ? "text-ink-faint/70" : "text-ink-soft",
                )}
              >
                {agent.duty}
              </p>
            </div>

            <span
              className={cn(
                "ml-auto shrink-0 self-start pt-1 font-mono text-2xs uppercase tracking-[0.11em]",
                phase === "done" && "text-patina",
                phase === "reading" && "text-ochre",
                phase === "waiting" && "text-ink-faint/60",
              )}
            >
              {phase === "done" ? "done" : phase === "reading" ? "reading" : "queued"}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

/** The reasoning ticker — short lines, one at a time, the way thinking sounds. */
export function ReasoningTicker({
  lines,
  className,
}: {
  lines: { id: string; text: string; agent: string }[];
  className?: string;
}) {
  const reduce = useReducedMotion();
  const recent = lines.slice(-5);

  return (
    <div className={cn("relative h-40 overflow-hidden", className)}>
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 z-10 h-12 bg-gradient-to-b from-[var(--paper-raised)] to-transparent"
      />
      <div className="flex h-full flex-col justify-end gap-2">
        <AnimatePresence initial={false}>
          {recent.map((line, index) => (
            <motion.p
              key={line.id}
              initial={reduce ? { opacity: 0 } : { opacity: 0, y: 10 }}
              animate={{ opacity: index === recent.length - 1 ? 1 : 0.42 - index * 0.02, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.28, ease: [0.32, 0.72, 0, 1] }}
              className="flex gap-2.5 text-sm leading-snug"
            >
              <span className="shrink-0 font-mono text-2xs uppercase tracking-[0.1em] text-patina/80 pt-0.5">
                {line.agent}
              </span>
              <span className="text-ink-soft">{line.text}</span>
            </motion.p>
          ))}
        </AnimatePresence>
      </div>
      <span className="sr-only" aria-live="polite">
        {recent.at(-1)?.text}
      </span>
    </div>
  );
}

/** The slim progress line at the top of the reading room. */
export function ReadingProgress({ value }: { value: number }) {
  const reduce = useReducedMotion();
  return (
    <div
      role="progressbar"
      aria-valuenow={Math.round(value)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label="Analysis progress"
      className="fixed inset-x-0 top-0 z-50 h-[3px] bg-transparent"
    >
      <motion.div
        className="h-full bg-patina"
        initial={reduce ? false : { width: 0 }}
        animate={{ width: `${Math.min(100, value)}%` }}
        transition={{ duration: 0.5, ease: [0.32, 0.72, 0, 1] }}
      />
    </div>
  );
}
