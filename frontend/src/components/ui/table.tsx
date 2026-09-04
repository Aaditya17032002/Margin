"use client";

import * as React from "react";
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, ChevronsUpDown } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "./button";

export function TableFrame({
  className,
  footer,
  children,
}: {
  className?: string;
  /**
   * Pinned under the scroll region — pagination and row counts belong to the
   * frame, not to the rows. Inside the scrolling area they slide out of reach
   * exactly when a long result set makes them necessary.
   */
  footer?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className={cn("flex min-w-0 flex-col overflow-hidden rounded-lg border border-line bg-paper-raised", className)}>
      {/* Both axes scroll inside the frame: a wide table should not push the
          page sideways, and a long one should not carry the header away. */}
      <div className="scroll-region scroll-region-x min-h-0 flex-1">{children}</div>
      {footer ? <div className="shrink-0 border-t border-line bg-paper-raised">{footer}</div> : null}
    </div>
  );
}

export function Table({ className, ...props }: React.TableHTMLAttributes<HTMLTableElement>) {
  return <table className={cn("w-full border-collapse text-sm", className)} {...props} />;
}

export function Th({
  className,
  sortable,
  sorted,
  onSort,
  children,
  ...props
}: React.ThHTMLAttributes<HTMLTableCellElement> & {
  sortable?: boolean;
  sorted?: false | "asc" | "desc";
  onSort?: () => void;
}) {
  return (
    <th
      scope="col"
      aria-sort={sorted === "asc" ? "ascending" : sorted === "desc" ? "descending" : undefined}
      className={cn(
        // Sticky so the column names survive scrolling a long result set.
        "sticky top-0 z-10 border-b border-line bg-paper-sunk px-3.5 py-2.5 text-left align-middle",
        "font-mono text-2xs font-medium uppercase tracking-[0.11em] text-ink-faint",
        className,
      )}
      {...props}
    >
      {sortable ? (
        <button
          type="button"
          onClick={onSort}
          className="inline-flex items-center gap-1.5 transition-colors duration-150 hover:text-ink"
        >
          {children}
          {sorted === "asc" ? (
            <ArrowUp className="size-3" />
          ) : sorted === "desc" ? (
            <ArrowDown className="size-3" />
          ) : (
            <ChevronsUpDown className="size-3 opacity-55" />
          )}
        </button>
      ) : (
        children
      )}
    </th>
  );
}

export function Td({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={cn("border-b border-line px-3.5 py-3 align-top text-ink-soft", className)} {...props} />;
}

export function Tr({
  className,
  interactive,
  selected,
  ...props
}: React.HTMLAttributes<HTMLTableRowElement> & { interactive?: boolean; selected?: boolean }) {
  return (
    <tr
      data-selected={selected || undefined}
      className={cn(
        "transition-colors duration-120",
        interactive && "cursor-pointer hover:bg-paper-sunk/70",
        selected && "bg-patina-tint/60",
        "last:[&>td]:border-b-0",
        className,
      )}
      {...props}
    />
  );
}

export function Pagination({
  page,
  pageCount,
  onPageChange,
  total,
  className,
}: {
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
  total: number;
  className?: string;
}) {
  if (pageCount <= 1) {
    return (
      <div className={cn("flex items-center justify-between px-3.5 py-2.5 text-xs text-ink-faint", className)}>
        <span>{total} rows</span>
      </div>
    );
  }
  return (
    <div
      className={cn(
        "flex items-center justify-between gap-4 border-t border-line px-3.5 py-2.5 text-xs text-ink-faint",
        className,
      )}
    >
      <span>
        Page <span className="tabular text-ink-soft">{page + 1}</span> of{" "}
        <span className="tabular text-ink-soft">{pageCount}</span> · {total} rows
      </span>
      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="iconSm"
          aria-label="Previous page"
          disabled={page === 0}
          onClick={() => onPageChange(page - 1)}
        >
          <ChevronLeft />
        </Button>
        <Button
          variant="ghost"
          size="iconSm"
          aria-label="Next page"
          disabled={page >= pageCount - 1}
          onClick={() => onPageChange(page + 1)}
        >
          <ChevronRight />
        </Button>
      </div>
    </div>
  );
}
