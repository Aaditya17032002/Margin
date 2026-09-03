"use client";

import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import * as DropdownMenuPrimitive from "@radix-ui/react-dropdown-menu";
import * as PopoverPrimitive from "@radix-ui/react-popover";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import * as HoverCardPrimitive from "@radix-ui/react-hover-card";
import { X } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "./button";

/* ---------------------------------------------------------------- */
/* Shared surfaces                                                    */
/* ---------------------------------------------------------------- */

const overlayBackdrop = cn(
  "fixed inset-0 z-50 bg-[color-mix(in_oklab,var(--ink)_38%,transparent)] backdrop-blur-[2px]",
  "data-[state=open]:animate-[fade_180ms_var(--ease-editorial)_both]",
  "data-[state=closed]:opacity-0 data-[state=closed]:transition-opacity data-[state=closed]:duration-150",
);

const floatingSurface = cn(
  "z-50 rounded-lg border border-line bg-paper-raised text-ink shadow-[var(--shadow-overlay)]",
  "origin-[var(--radix-popper-transform-origin)]",
  "data-[state=open]:animate-[rise_180ms_var(--ease-editorial)_both]",
  "data-[state=closed]:opacity-0 data-[state=closed]:transition-opacity data-[state=closed]:duration-120",
);

/* ---------------------------------------------------------------- */
/* Dialog                                                             */
/* ---------------------------------------------------------------- */

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;

export function DialogContent({
  className,
  children,
  title,
  description,
  footer,
  size = "md",
  ...props
}: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> & {
  title: React.ReactNode;
  description?: React.ReactNode;
  footer?: React.ReactNode;
  size?: "sm" | "md" | "lg";
}) {
  const width = { sm: "max-w-md", md: "max-w-xl", lg: "max-w-3xl" }[size];
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className={overlayBackdrop} />
      <DialogPrimitive.Content
        className={cn(
          "fixed left-1/2 top-1/2 z-50 w-[calc(100vw-2rem)] -translate-x-1/2 -translate-y-1/2",
          width,
          "rounded-xl border border-line bg-paper-raised shadow-[var(--shadow-overlay)]",
          "data-[state=open]:animate-[rise_220ms_var(--ease-editorial)_both]",
          "focus:outline-none",
          className,
        )}
        {...props}
      >
        <div className="flex items-start justify-between gap-6 border-b border-line px-6 py-5">
          <div className="space-y-1">
            <DialogPrimitive.Title className="text-xl leading-snug text-ink">
              {title}
            </DialogPrimitive.Title>
            {description ? (
              <DialogPrimitive.Description className="text-sm text-ink-soft">
                {description}
              </DialogPrimitive.Description>
            ) : null}
          </div>
          <DialogPrimitive.Close asChild>
            <Button variant="quiet" size="iconSm" aria-label="Close">
              <X />
            </Button>
          </DialogPrimitive.Close>
        </div>
        <div className="px-6 py-5">{children}</div>
        {footer ? (
          <div className="flex items-center justify-end gap-2 border-t border-line px-6 py-4">
            {footer}
          </div>
        ) : null}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  destructive = false,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: React.ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  onConfirm: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        size="sm"
        title={title}
        footer={
          <>
            <Button variant="ghost" onClick={() => onOpenChange(false)}>
              {cancelLabel}
            </Button>
            <Button
              variant={destructive ? "danger" : "primary"}
              onClick={() => {
                onConfirm();
                onOpenChange(false);
              }}
            >
              {confirmLabel}
            </Button>
          </>
        }
      >
        <p className="text-sm leading-relaxed text-ink-soft">{description}</p>
      </DialogContent>
    </Dialog>
  );
}

/* ---------------------------------------------------------------- */
/* Dropdown menu                                                      */
/* ---------------------------------------------------------------- */

export const DropdownMenu = DropdownMenuPrimitive.Root;
export const DropdownMenuTrigger = DropdownMenuPrimitive.Trigger;
export const DropdownMenuGroup = DropdownMenuPrimitive.Group;
export const DropdownMenuSub = DropdownMenuPrimitive.Sub;
export const DropdownMenuSubTrigger = DropdownMenuPrimitive.SubTrigger;

export function DropdownMenuContent({
  className,
  sideOffset = 6,
  ...props
}: React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Content>) {
  return (
    <DropdownMenuPrimitive.Portal>
      <DropdownMenuPrimitive.Content
        sideOffset={sideOffset}
        className={cn(floatingSurface, "min-w-52 overflow-hidden p-1", className)}
        {...props}
      />
    </DropdownMenuPrimitive.Portal>
  );
}

export function DropdownMenuItem({
  className,
  destructive,
  ...props
}: React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Item> & { destructive?: boolean }) {
  return (
    <DropdownMenuPrimitive.Item
      className={cn(
        "flex cursor-default select-none items-center gap-2.5 rounded-sm px-2.5 py-1.5 text-sm outline-none",
        "transition-colors duration-100",
        "data-[highlighted]:bg-paper-sunk data-[highlighted]:text-ink",
        "data-[disabled]:pointer-events-none data-[disabled]:opacity-45",
        "[&_svg]:size-4 [&_svg]:shrink-0 [&_svg]:text-ink-faint",
        destructive
          ? "text-seal data-[highlighted]:bg-[var(--seal-tint)] data-[highlighted]:text-seal [&_svg]:text-seal"
          : "text-ink-soft",
        className,
      )}
      {...props}
    />
  );
}

export function DropdownMenuLabel({
  className,
  ...props
}: React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Label>) {
  return (
    <DropdownMenuPrimitive.Label
      className={cn("px-2.5 pb-1 pt-2 font-mono text-2xs uppercase tracking-[0.13em] text-ink-faint", className)}
      {...props}
    />
  );
}

export function DropdownMenuSeparator({
  className,
  ...props
}: React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Separator>) {
  return (
    <DropdownMenuPrimitive.Separator className={cn("-mx-1 my-1 h-px bg-line", className)} {...props} />
  );
}

export function DropdownMenuCheckboxItem({
  className,
  children,
  ...props
}: React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.CheckboxItem>) {
  return (
    <DropdownMenuPrimitive.CheckboxItem
      className={cn(
        "flex cursor-default select-none items-center gap-2.5 rounded-sm py-1.5 pl-7 pr-2.5 text-sm text-ink-soft outline-none",
        "relative data-[highlighted]:bg-paper-sunk data-[highlighted]:text-ink",
        className,
      )}
      {...props}
    >
      <span className="absolute left-2 flex size-3.5 items-center justify-center">
        <DropdownMenuPrimitive.ItemIndicator>
          <span className="size-1.5 rounded-full bg-patina" />
        </DropdownMenuPrimitive.ItemIndicator>
      </span>
      {children}
    </DropdownMenuPrimitive.CheckboxItem>
  );
}

/* ---------------------------------------------------------------- */
/* Popover                                                            */
/* ---------------------------------------------------------------- */

export const Popover = PopoverPrimitive.Root;
export const PopoverTrigger = PopoverPrimitive.Trigger;
export const PopoverAnchor = PopoverPrimitive.Anchor;

export function PopoverContent({
  className,
  sideOffset = 8,
  ...props
}: React.ComponentPropsWithoutRef<typeof PopoverPrimitive.Content>) {
  return (
    <PopoverPrimitive.Portal>
      <PopoverPrimitive.Content
        sideOffset={sideOffset}
        className={cn(floatingSurface, "w-72 p-4 outline-none", className)}
        {...props}
      />
    </PopoverPrimitive.Portal>
  );
}

/* ---------------------------------------------------------------- */
/* Tooltip                                                            */
/* ---------------------------------------------------------------- */

export const TooltipProvider = TooltipPrimitive.Provider;
export const TooltipRoot = TooltipPrimitive.Root;
export const TooltipTrigger = TooltipPrimitive.Trigger;

export function Tooltip({
  content,
  children,
  side = "top",
  shortcut,
  delay = 240,
}: {
  content: React.ReactNode;
  children: React.ReactNode;
  side?: "top" | "right" | "bottom" | "left";
  shortcut?: string;
  delay?: number;
}) {
  return (
    <TooltipPrimitive.Root delayDuration={delay}>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          side={side}
          sideOffset={6}
          className={cn(
            "z-50 flex items-center gap-2 rounded-sm bg-ink px-2.5 py-1.5 text-xs text-[var(--paper-raised)]",
            "shadow-[var(--shadow-float)]",
            "data-[state=delayed-open]:animate-[fade_140ms_var(--ease-editorial)_both]",
          )}
        >
          {content}
          {shortcut ? (
            <span className="font-mono text-2xs text-[color-mix(in_oklab,var(--paper-raised)_62%,transparent)]">
              {shortcut}
            </span>
          ) : null}
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}

/* ---------------------------------------------------------------- */
/* Hover card                                                         */
/* ---------------------------------------------------------------- */

export const HoverCard = HoverCardPrimitive.Root;
export const HoverCardTrigger = HoverCardPrimitive.Trigger;

export function HoverCardContent({
  className,
  sideOffset = 8,
  ...props
}: React.ComponentPropsWithoutRef<typeof HoverCardPrimitive.Content>) {
  return (
    <HoverCardPrimitive.Portal>
      <HoverCardPrimitive.Content
        sideOffset={sideOffset}
        className={cn(floatingSurface, "w-80 p-4", className)}
        {...props}
      />
    </HoverCardPrimitive.Portal>
  );
}

export { floatingSurface };
