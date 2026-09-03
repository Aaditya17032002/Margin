"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * One level of elevation, ever. Margin uses a single card depth and separates
 * groups with rules and space instead of nesting boxes inside boxes.
 */
export function Panel({
  className,
  children,
  as: Tag = "section",
  ...props
}: React.HTMLAttributes<HTMLElement> & { as?: React.ElementType }) {
  return (
    <Tag
      className={cn(
        "rounded-lg border border-line bg-paper-raised shadow-[var(--shadow-raised)]",
        className,
      )}
      {...props}
    >
      {children}
    </Tag>
  );
}

export function PanelHeader({
  title,
  description,
  actions,
  className,
  ...props
}: {
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
} & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("flex items-start justify-between gap-4 border-b border-line px-5 py-4", className)}
      {...props}
    >
      <div className="min-w-0 space-y-0.5">
        <h3 className="text-lg leading-snug text-ink">{title}</h3>
        {description ? <p className="text-sm text-ink-soft">{description}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function Well({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("rounded-md border border-line bg-paper-sunk px-4 py-3", className)}
      {...props}
    >
      {children}
    </div>
  );
}

export function Separator({
  orientation = "horizontal",
  className,
}: {
  orientation?: "horizontal" | "vertical";
  className?: string;
}) {
  return (
    <div
      role="separator"
      aria-orientation={orientation}
      className={cn(
        "bg-line",
        orientation === "horizontal" ? "h-px w-full" : "h-full w-px",
        className,
      )}
    />
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  className,
}: {
  eyebrow?: React.ReactNode;
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <header className={cn("flex flex-wrap items-end justify-between gap-x-6 gap-y-4", className)}>
      <div className="min-w-0 max-w-2xl space-y-1.5">
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        <h1 className="display-tight text-3xl text-ink">{title}</h1>
        {description ? <p className="text-base text-ink-soft">{description}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}

export function Kbd({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <kbd
      className={cn(
        "inline-flex h-5 min-w-5 items-center justify-center rounded-xs border border-line-strong bg-paper px-1.5",
        "font-mono text-2xs text-ink-soft shadow-[0_1px_0_var(--line-strong)]",
        className,
      )}
    >
      {children}
    </kbd>
  );
}
