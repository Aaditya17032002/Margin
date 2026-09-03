"use client";

import * as React from "react";
import { Drawer } from "vaul";
import { X } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "./button";

export const Sheet = Drawer.Root;
export const SheetTrigger = Drawer.Trigger;
export const SheetClose = Drawer.Close;

export function SheetContent({
  title,
  description,
  children,
  footer,
  className,
  direction = "right",
}: {
  title: React.ReactNode;
  description?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
  direction?: "right" | "bottom" | "left";
}) {
  const positional =
    direction === "bottom"
      ? "inset-x-0 bottom-0 mt-24 max-h-[88vh] rounded-t-2xl border-t"
      : direction === "left"
        ? "inset-y-0 left-0 w-[min(30rem,92vw)] rounded-r-2xl border-r"
        : "inset-y-0 right-0 w-[min(34rem,94vw)] rounded-l-2xl border-l";

  return (
    <Drawer.Portal>
      <Drawer.Overlay className="fixed inset-0 z-50 bg-[color-mix(in_oklab,var(--ink)_38%,transparent)]" />
      <Drawer.Content
        className={cn(
          "fixed z-50 flex flex-col border-line bg-paper-raised shadow-[var(--shadow-overlay)] outline-none",
          positional,
          className,
        )}
      >
        {direction === "bottom" ? (
          <div className="mx-auto mt-3 h-1 w-10 shrink-0 rounded-full bg-[var(--line-strong)]" aria-hidden />
        ) : null}
        <div className="flex items-start justify-between gap-6 border-b border-line px-6 py-5">
          <div className="min-w-0 space-y-1">
            <Drawer.Title className="text-xl leading-snug text-ink">{title}</Drawer.Title>
            {description ? (
              <Drawer.Description className="text-sm text-ink-soft">{description}</Drawer.Description>
            ) : null}
          </div>
          <Drawer.Close asChild>
            <Button variant="quiet" size="iconSm" aria-label="Close">
              <X />
            </Button>
          </Drawer.Close>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">{children}</div>
        {footer ? (
          <div className="flex items-center justify-end gap-2 border-t border-line px-6 py-4">
            {footer}
          </div>
        ) : null}
      </Drawer.Content>
    </Drawer.Portal>
  );
}
