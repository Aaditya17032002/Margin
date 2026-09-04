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
  // `title` on a DOM element is a string tooltip, and intersecting it with
  // ReactNode narrowed this prop to `ReactNode & string` — so a header could
  // only ever be given plain text, silently, and only at the call site that
  // tried something else.
} & Omit<React.HTMLAttributes<HTMLDivElement>, "title">) {
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
    /*
     * Pinned to the top of the page's scroll region, and bled out to the
     * gutters so nothing shows through behind it. Which analysis you are
     * looking at, and the controls that act on it, should not scroll away
     * while you read the rows underneath.
     */
    <header
      className={cn(
        "sticky top-0 z-20 -mx-6 mb-2 flex flex-wrap items-end justify-between gap-x-6 gap-y-4",
        "border-b border-line bg-paper px-6 pb-5 pt-7 lg:-mx-10 lg:px-10",
        className,
      )}
    >
      <div className="min-w-0 max-w-2xl space-y-1.5">
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        <h1 className="display-tight text-2xl text-ink sm:text-3xl">{title}</h1>
        {description ? <p className="text-base leading-relaxed text-ink-soft">{description}</p> : null}
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
