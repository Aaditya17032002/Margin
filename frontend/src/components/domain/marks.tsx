"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Three custom motifs carry the product's voice where a stock icon would flatten
 * it: a wax seal for a hard stop, a quill mark for something a person still has
 * to look at, and a bronze gate for the go/no-go decision itself.
 */

export function WaxSeal({ className, label }: { className?: string; label?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={cn("size-12", className)} role="img" aria-label={label ?? "Disqualifying"}>
      <defs>
        <radialGradient id="wax-body" cx="38%" cy="32%" r="72%">
          <stop offset="0%" stopColor="color-mix(in oklab, var(--seal) 72%, white)" />
          <stop offset="58%" stopColor="var(--seal)" />
          <stop offset="100%" stopColor="color-mix(in oklab, var(--seal) 74%, black)" />
        </radialGradient>
      </defs>
      {/* Irregular edge — wax never lands as a circle. */}
      <path
        d="M32 3.4c5.1-.6 8 3.6 12.6 4.9 4.6 1.3 9.4-.6 12 3.4 2.6 4-.4 8.3.6 12.9 1 4.6 5.4 7.2 4.7 11.9-.7 4.7-5.7 6.1-8.2 10-2.5 3.9-2 9-6 11.3-4 2.3-8.1-.7-12.8-.2-4.7.5-8.2 4.4-12.6 3-4.4-1.4-5.3-6.4-8.7-9.5-3.4-3.1-8.6-3.5-10-8-1.4-4.5 2.2-7.9 2.8-12.5.6-4.6-1.9-9.2 1-12.9 2.9-3.7 7.9-2.4 12-4.6C23.5 11 26.9 4 32 3.4Z"
        fill="url(#wax-body)"
      />
      <circle cx="32" cy="32" r="17.5" fill="none" stroke="color-mix(in oklab, var(--seal) 62%, black)" strokeWidth="1.2" opacity="0.55" />
      <path
        d="M32 21.5 34.9 28l7 .6-5.3 4.6 1.6 6.9L32 36.4l-6.2 3.7 1.6-6.9L22.1 28.6l7-.6L32 21.5Z"
        fill="color-mix(in oklab, var(--seal) 58%, black)"
        opacity="0.5"
      />
      <path
        d="M18 16c3.4-2.6 8-4.2 12-4.4"
        stroke="color-mix(in oklab, white 55%, transparent)"
        strokeWidth="1.6"
        strokeLinecap="round"
        fill="none"
        opacity="0.5"
      />
    </svg>
  );
}

/** A margin annotation mark — the reader's tick beside a line worth a second look. */
export function QuillMark({ className, label }: { className?: string; label?: string }) {
  return (
    <svg
      viewBox="0 0 16 16"
      className={cn("size-4", className)}
      fill="none"
      role="img"
      aria-label={label ?? "Needs review"}
    >
      <path
        d="M3 13.2c1.4-4.6 4-8.2 8.4-10.6"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
      <path d="M11.4 2.6c.9.4 1.5 1.1 1.8 2.1-1.4.6-2.6.3-3.4-.7l1.6-1.4Z" fill="currentColor" />
      <path d="M3 13.2 2 14.4l1.9-.2" fill="currentColor" />
    </svg>
  );
}

/** The bronze gate: two leaves that swing apart as confidence in a bid rises. */
export function BronzeGate({
  open,
  className,
}: {
  /** 0 = shut, 1 = fully open. */
  open: number;
  className?: string;
}) {
  const swing = Math.max(0, Math.min(1, open));
  const shift = swing * 13;
  return (
    <svg viewBox="0 0 96 64" className={cn("w-full", className)} fill="none" aria-hidden>
      <defs>
        <linearGradient id="gate-metal" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="color-mix(in oklab, var(--patina) 68%, white)" />
          <stop offset="100%" stopColor="var(--patina)" />
        </linearGradient>
      </defs>
      <path d="M4 60h88" stroke="var(--line-strong)" strokeWidth="1.5" strokeLinecap="round" />
      <g transform={`translate(${-shift} 0)`} opacity={0.94}>
        <rect x="14" y="14" width="32" height="46" rx="1.5" fill="url(#gate-metal)" opacity="0.14" />
        <path d="M14 14h32v46" stroke="url(#gate-metal)" strokeWidth="1.4" />
        <path d="M22 60V20M30 60V20M38 60V20" stroke="var(--patina)" strokeWidth="1.1" opacity="0.62" />
        <path d="M14 32h32" stroke="var(--patina)" strokeWidth="1.1" opacity="0.62" />
      </g>
      <g transform={`translate(${shift} 0)`} opacity={0.94}>
        <rect x="50" y="14" width="32" height="46" rx="1.5" fill="url(#gate-metal)" opacity="0.14" />
        <path d="M82 14H50v46" stroke="url(#gate-metal)" strokeWidth="1.4" />
        <path d="M58 60V20M66 60V20M74 60V20" stroke="var(--patina)" strokeWidth="1.1" opacity="0.62" />
        <path d="M50 32h32" stroke="var(--patina)" strokeWidth="1.1" opacity="0.62" />
      </g>
      <path d="M8 14h80" stroke="var(--patina)" strokeWidth="2" strokeLinecap="round" />
      <path d="M10 10.5h76" stroke="var(--line-strong)" strokeWidth="1" strokeLinecap="round" />
    </svg>
  );
}

/** The wordmark: a page with its margin rule, which is the whole product idea. */
export function MarginMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 28 28" className={cn("size-7", className)} fill="none" aria-hidden>
      <rect x="3.5" y="2.5" width="21" height="23" rx="2.5" fill="var(--paper-raised)" stroke="var(--ink)" strokeWidth="1.4" />
      <path d="M18.5 2.5v23" stroke="var(--patina)" strokeWidth="1.4" />
      <path d="M7.5 9h8M7.5 13.5h8M7.5 18h5" stroke="var(--ink)" strokeWidth="1.3" strokeLinecap="round" opacity="0.5" />
      <circle cx="21.5" cy="11" r="1.6" fill="var(--patina)" />
    </svg>
  );
}

export function Wordmark({ className, showText = true }: { className?: string; showText?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <MarginMark />
      {showText ? (
        <span className="font-display text-xl font-medium tracking-[-0.02em] text-ink">Margin</span>
      ) : null}
    </span>
  );
}
