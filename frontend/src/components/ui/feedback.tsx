"use client";

import * as React from "react";
import { AlertTriangle, CheckCircle2, Info, ShieldAlert } from "lucide-react";

import { cn } from "@/lib/utils";

/* ---------------------------------------------------------------- */
/* Callout — an inline banner keyed to what is at stake              */
/* ---------------------------------------------------------------- */

const TONES = {
  seal: {
    wrap: "border-l-seal bg-[var(--seal-tint)]",
    icon: "text-seal",
    Icon: ShieldAlert,
  },
  ochre: {
    wrap: "border-l-ochre bg-[var(--ochre-tint)]",
    icon: "text-[color-mix(in_oklab,var(--ochre)_82%,var(--ink))]",
    Icon: AlertTriangle,
  },
  leaf: {
    wrap: "border-l-leaf bg-[var(--leaf-tint)]",
    icon: "text-leaf",
    Icon: CheckCircle2,
  },
  slate: {
    wrap: "border-l-slate bg-[var(--slate-tint)]",
    icon: "text-slate",
    Icon: Info,
  },
} as const;

export function Callout({
  tone = "slate",
  title,
  children,
  action,
  className,
  icon,
}: {
  tone?: keyof typeof TONES;
  title?: React.ReactNode;
  children?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
  icon?: React.ReactNode;
}) {
  const config = TONES[tone];
  const Icon = config.Icon;
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-md border border-line border-l-[3px] px-4 py-3",
        config.wrap,
        className,
      )}
    >
      <span className={cn("mt-0.5 shrink-0 [&_svg]:size-4", config.icon)}>
        {icon ?? <Icon aria-hidden />}
      </span>
      <div className="min-w-0 flex-1 space-y-2">
        {title ? <p className="text-sm font-medium text-ink">{title}</p> : null}
        {children ? <div className="text-sm leading-relaxed text-ink-soft">{children}</div> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

/* ---------------------------------------------------------------- */
/* Skeletons — paper-toned, with a slow sheen rather than a pulse    */
/* ---------------------------------------------------------------- */

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={cn("shimmer rounded-sm bg-paper-sunk motion-reduce:animate-none", className)}
    />
  );
}

export function SkeletonText({ lines = 3, className }: { lines?: number; className?: string }) {
  return (
    <div className={cn("space-y-2", className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn("h-3.5", i === lines - 1 ? "w-2/5" : i % 3 === 1 ? "w-11/12" : "w-full")}
        />
      ))}
    </div>
  );
}

export function SkeletonPanel({ className }: { className?: string }) {
  return (
    <div className={cn("rounded-lg border border-line bg-paper-raised p-5", className)}>
      <Skeleton className="h-4 w-40" />
      <div className="mt-4 space-y-2.5">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-11/12" />
        <Skeleton className="h-3 w-1/2" />
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- */
/* Empty & error states                                               */
/* ---------------------------------------------------------------- */

export function EmptyState({
  illustration,
  title,
  description,
  action,
  className,
}: {
  illustration?: React.ReactNode;
  title: string;
  description: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-start gap-5 rounded-lg border border-dashed border-line-strong bg-paper-raised px-8 py-10",
        className,
      )}
    >
      {illustration ?? <EmptyMark />}
      <div className="max-w-md space-y-1.5">
        <h3 className="text-lg text-ink">{title}</h3>
        <p className="text-sm leading-relaxed text-ink-soft">{description}</p>
      </div>
      {action}
    </div>
  );
}

/** A blank sheet with a single margin rule — the visual opposite of a finding. */
export function EmptyMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 96 72"
      className={cn("h-16 w-auto", className)}
      fill="none"
      aria-hidden
    >
      <rect x="8.5" y="4.5" width="63" height="63" rx="3" stroke="var(--line-strong)" />
      <path d="M60 4.5v63" stroke="var(--line-strong)" strokeDasharray="3 3" />
      <path d="M18 20h34M18 30h34M18 40h22" stroke="var(--line-strong)" strokeLinecap="round" />
      <circle cx="79" cy="52" r="12.5" fill="var(--paper-raised)" stroke="var(--patina)" />
      <path d="M79 46.5v11M73.5 52h11" stroke="var(--patina)" strokeLinecap="round" />
    </svg>
  );
}

export function ErrorState({
  title = "Something went wrong",
  description,
  action,
  className,
}: {
  title?: string;
  description: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-start gap-5 rounded-lg border border-line border-l-[3px] border-l-seal bg-[var(--seal-tint)] px-8 py-10",
        className,
      )}
    >
      <ShieldAlert className="size-7 text-seal" aria-hidden />
      <div className="max-w-md space-y-1.5">
        <h3 className="text-lg text-ink">{title}</h3>
        <p className="text-sm leading-relaxed text-ink-soft">{description}</p>
      </div>
      {action}
    </div>
  );
}

/* ---------------------------------------------------------------- */
/* Step progress                                                      */
/* ---------------------------------------------------------------- */

export function StepRail({
  steps,
  current,
  className,
}: {
  steps: { id: string; label: string; hint?: string }[];
  current: number;
  className?: string;
}) {
  return (
    <ol className={cn("space-y-0", className)}>
      {steps.map((step, index) => {
        const state = index < current ? "done" : index === current ? "active" : "upcoming";
        return (
          <li key={step.id} className="relative flex gap-3.5 pb-7 last:pb-0">
            {index < steps.length - 1 ? (
              <span
                aria-hidden
                className={cn(
                  "absolute left-[11px] top-6 h-[calc(100%-1.5rem)] w-px",
                  state === "done" ? "bg-patina" : "bg-line",
                )}
              />
            ) : null}
            <span
              className={cn(
                "relative z-10 mt-0.5 flex size-[22px] shrink-0 items-center justify-center rounded-full border text-2xs font-medium",
                "transition-colors duration-260 ease-[cubic-bezier(0.32,0.72,0,1)]",
                state === "done" && "border-patina bg-patina text-[var(--patina-ink)]",
                state === "active" && "border-patina bg-paper-raised text-patina",
                state === "upcoming" && "border-line-strong bg-paper-sunk text-ink-faint",
              )}
            >
              {state === "done" ? <CheckCircle2 className="size-3.5" /> : index + 1}
            </span>
            <div className="min-w-0 pt-px">
              <p
                className={cn(
                  "text-sm font-medium transition-colors duration-200",
                  state === "upcoming" ? "text-ink-faint" : "text-ink",
                )}
              >
                {step.label}
              </p>
              {step.hint ? <p className="text-xs text-ink-faint">{step.hint}</p> : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
