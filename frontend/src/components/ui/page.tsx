"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Layout primitives for a fixed-viewport application.
 *
 * The window never scrolls. Each screen is a `Page`: a bar that stays put and
 * a body that scrolls under it. Scrolling a list of two hundred requirements
 * should not carry away the header telling you which analysis they belong to,
 * and reaching a row at the bottom should not mean scrolling the navigation
 * off the screen first.
 *
 *   <Page>
 *     <PageBar title="Compliance matrix" actions={…} />
 *     <PageBody>…</PageBody>
 *   </Page>
 *
 * `min-h-0` appears on every flex and grid child here on purpose: without it a
 * grid track refuses to shrink below its content, the region never overflows,
 * and the whole window starts scrolling again.
 */

export function Page({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      // The explicit `minmax(0,1fr)` column matters as much as the rows: a grid
      // item defaults to `min-width: auto`, so without it a wide table refuses
      // to shrink and pushes the whole layout sideways.
      className={cn(
        "grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)] grid-rows-[auto_minmax(0,1fr)]",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

/**
 * The bar that does not move. Keep it to one line of identity and one row of
 * controls — anything longer belongs in the body, where there is room to read.
 */
export function PageBar({
  eyebrow,
  title,
  description,
  actions,
  meta,
  below,
  className,
  ...props
}: {
  eyebrow?: React.ReactNode;
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  /** A line of counts or status set beside the title. */
  meta?: React.ReactNode;
  /** Filters or tabs, on their own rule under the title. */
  below?: React.ReactNode;
  className?: string;
} & Omit<React.HTMLAttributes<HTMLElement>, "title">) {
  return (
    <header
      className={cn("shrink-0 border-b border-line bg-paper", className)}
      {...props}
    >
      <div className="mx-auto flex w-full max-w-[92rem] flex-wrap items-end justify-between gap-x-8 gap-y-4 px-6 pb-5 pt-7 lg:px-10">
        <div className="min-w-0 max-w-2xl">
          {eyebrow ? <p className="eyebrow pb-2">{eyebrow}</p> : null}
          <div className="flex min-w-0 flex-wrap items-baseline gap-x-4 gap-y-1">
            <h1 className="display-tight min-w-0 text-2xl text-ink sm:text-3xl">{title}</h1>
            {meta ? <div className="flex items-center gap-2">{meta}</div> : null}
          </div>
          {description ? (
            <p className="mt-2 text-base leading-relaxed text-ink-soft">{description}</p>
          ) : null}
        </div>
        {actions ? (
          <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>
        ) : null}
      </div>
      {below ? (
        <div className="mx-auto w-full max-w-[92rem] px-6 pb-3 lg:px-10">{below}</div>
      ) : null}
    </header>
  );
}

/**
 * The region that scrolls. `size="prose"` narrows the measure for reading
 * screens; `flush` hands the padding to the child, which a full-bleed table or
 * board wants to control itself.
 */
export function PageBody({
  size = "wide",
  flush = false,
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & {
  size?: "wide" | "prose" | "full";
  flush?: boolean;
}) {
  return (
    <div className={cn("scroll-region min-h-0", flush ? "" : "px-6 py-8 lg:px-10", className)} {...props}>
      <div
        className={cn(
          "mx-auto w-full",
          size === "prose" && "max-w-[54rem]",
          size === "wide" && "max-w-[92rem]",
          size === "full" && "max-w-none",
        )}
      >
        {children}
      </div>
    </div>
  );
}

/**
 * Two panes that scroll independently — a list beside a detail, a document
 * beside its findings. Below the breakpoint they stack and the page body
 * scrolls as one, because two scroll regions on a phone is a trap.
 */
export function Split({
  aside,
  side = "right",
  width = "24rem",
  className,
  children,
}: {
  aside: React.ReactNode;
  side?: "left" | "right";
  width?: string;
  className?: string;
  children: React.ReactNode;
}) {
  const asidePane = (
    <aside
      className={cn(
        "hidden min-h-0 shrink-0 border-line xl:flex xl:flex-col",
        side === "right" ? "border-l" : "border-r",
      )}
      style={{ width }}
    >
      {aside}
    </aside>
  );

  return (
    <div className={cn("flex min-h-0 min-w-0 flex-1", className)}>
      {side === "left" ? asidePane : null}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">{children}</div>
      {side === "right" ? asidePane : null}
    </div>
  );
}

/**
 * A titled band inside a page body. Sections are separated by space and a rule
 * rather than by nesting another card inside a card.
 */
export function Section({
  title,
  description,
  actions,
  className,
  children,
  ...props
}: Omit<React.HTMLAttributes<HTMLElement>, "title"> & {
  title?: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <section className={cn("min-w-0", className)} {...props}>
      {title || actions ? (
        <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-2 pb-4">
          <div className="min-w-0">
            {title ? <h2 className="text-xl leading-snug text-ink">{title}</h2> : null}
            {description ? (
              <p className="mt-1 text-sm leading-relaxed text-ink-soft">{description}</p>
            ) : null}
          </div>
          {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
        </div>
      ) : null}
      {children}
    </section>
  );
}

/**
 * A pane whose header pins while its content scrolls. This is what the Margin,
 * the workspace tab list, and every long panel are built from.
 */
export function Pane({
  header,
  footer,
  className,
  bodyClassName,
  children,
}: {
  header?: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
  bodyClassName?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cn("flex min-h-0 flex-1 flex-col", className)}>
      {header ? <div className="shrink-0 border-b border-line">{header}</div> : null}
      <div className={cn("scroll-region min-h-0 flex-1", bodyClassName)}>{children}</div>
      {footer ? <div className="shrink-0 border-t border-line">{footer}</div> : null}
    </div>
  );
}

/** The label above a pane's contents. Quiet, monospaced, one line. */
export function PaneTitle({
  children,
  actions,
  className,
}: {
  children: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex h-11 items-center justify-between gap-3 px-4", className)}>
      <p className="eyebrow truncate">{children}</p>
      {actions ? <div className="flex shrink-0 items-center gap-0.5">{actions}</div> : null}
    </div>
  );
}

/**
 * The default screen: one scroll region filling the shell's main area, with
 * the page's own header pinned at its top. Views keep their own measure — this
 * only supplies the scrolling and the gutters, so a board can run wide while a
 * settings page stays narrow.
 */
export function ScrollPage({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("scroll-region min-h-0 flex-1 px-6 pb-16 lg:px-10", className)} {...props}>
      {children}
    </div>
  );
}
