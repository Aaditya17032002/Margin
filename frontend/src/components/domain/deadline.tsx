"use client";

import * as React from "react";

import { cn } from "@/lib/utils";
import { countdown, formatInZone, urgency, zoneAbbr } from "@/lib/dates";
import { useNow } from "@/hooks/use-now";

const TONE: Record<ReturnType<typeof urgency>, string> = {
  past: "text-ink-faint",
  critical: "text-seal",
  near: "text-ochre",
  steady: "text-ink-soft",
};

export function DeadlineCountdown({
  at,
  timezone,
  label,
  className,
  size = "md",
  showZone = true,
}: {
  at: string;
  timezone: string;
  label?: string;
  className?: string;
  size?: "sm" | "md" | "lg";
  showZone?: boolean;
}) {
  const now = useNow(1000);
  const mounted = now !== 0;
  const state = urgency(at, now);
  const c = countdown(at, new Date(now));

  const digits =
    size === "lg" ? "text-2xl" : size === "md" ? "text-lg" : "text-sm";

  return (
    <div className={cn("space-y-1", className)}>
      {label ? <p className="text-sm font-medium text-ink">{label}</p> : null}
      <p
        className={cn("font-mono tabular leading-none", digits, TONE[state])}
        aria-live="off"
        suppressHydrationWarning
      >
        {!mounted ? (
          <span className="text-ink-faint">—</span>
        ) : state === "past" ? (
          <span>Passed {c.days > 0 ? `${c.days}d ago` : `${c.hours}h ago`}</span>
        ) : (
          <>
            <Unit value={c.days} suffix="d" />
            <Unit value={c.hours} suffix="h" />
            <Unit value={c.minutes} suffix="m" />
            {c.days === 0 ? <Unit value={c.seconds} suffix="s" /> : null}
          </>
        )}
      </p>
      <p className="text-xs text-ink-faint">
        {formatInZone(at, timezone)}
        {showZone ? ` ${zoneAbbr(timezone)}` : ""}
      </p>
    </div>
  );
}

function Unit({ value, suffix }: { value: number; suffix: string }) {
  return (
    <span className="mr-1.5 inline-block">
      {value}
      <span className="ml-px text-[0.7em] opacity-70">{suffix}</span>
    </span>
  );
}

/** A single line for lists — the shape a bid coordinator scans down. */
export function DeadlineLine({
  at,
  timezone,
  label,
  context,
  className,
}: {
  at: string;
  timezone: string;
  label: string;
  context?: React.ReactNode;
  className?: string;
}) {
  const now = useNow(30_000);
  const mounted = now !== 0;
  const state = urgency(at, now);
  const c = countdown(at, new Date(now));

  return (
    <div className={cn("flex items-baseline justify-between gap-4", className)}>
      <div className="min-w-0">
        <p className="truncate text-sm text-ink">{label}</p>
        {context ? <p className="truncate text-xs text-ink-faint">{context}</p> : null}
      </div>
      <div className="shrink-0 text-right">
        <p className={cn("font-mono text-sm tabular", TONE[state])} suppressHydrationWarning>
          {!mounted ? "—" : state === "past" ? "Passed" : c.days > 0 ? `${c.days}d ${c.hours}h` : `${c.hours}h ${c.minutes}m`}
        </p>
        <p className="text-2xs text-ink-faint">
          {formatInZone(at, timezone, "date")} · {zoneAbbr(timezone)}
        </p>
      </div>
    </div>
  );
}
