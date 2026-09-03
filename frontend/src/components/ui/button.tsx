"use client";

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * The shadcn defaults are deliberately not used here. Margin's buttons sit on
 * warm paper, so their resting state is a hairline and a tint rather than a
 * shadow, and the press affordance is a one-pixel settle rather than a scale —
 * a control on a compliance screen should feel like a key, not a toy.
 */
const buttonVariants = cva(
  cn(
    "relative inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-md font-medium",
    "transition-[background-color,color,border-color,box-shadow,translate] duration-150 ease-[cubic-bezier(0.32,0.72,0,1)]",
    "disabled:pointer-events-none disabled:opacity-45",
    "active:translate-y-px",
    "[&_svg]:pointer-events-none [&_svg]:shrink-0",
  ),
  {
    variants: {
      variant: {
        primary:
          "bg-patina text-[var(--patina-ink)] shadow-[inset_0_1px_0_rgba(255,255,255,0.14)] hover:bg-patina-hover",
        secondary:
          "border border-line-strong bg-paper-raised text-ink hover:bg-paper-sunk hover:border-[var(--ink-faint)]",
        ghost: "text-ink-soft hover:bg-paper-sunk hover:text-ink",
        quiet: "text-ink-faint hover:text-ink",
        danger: "bg-seal text-[color:var(--paper-raised)] hover:brightness-110",
        outlineDanger:
          "border border-seal/45 text-seal hover:bg-[color:var(--seal-tint)]",
        link: "text-patina underline decoration-[color:var(--line-strong)] underline-offset-4 hover:decoration-current",
      },
      size: {
        xs: "h-7 px-2.5 text-xs [&_svg]:size-3.5",
        sm: "h-8 px-3 text-sm [&_svg]:size-4",
        md: "h-9 px-4 text-sm [&_svg]:size-4",
        lg: "h-11 px-6 text-base [&_svg]:size-[18px]",
        icon: "size-9 [&_svg]:size-4",
        iconSm: "size-7 [&_svg]:size-3.5",
      },
    },
    defaultVariants: { variant: "secondary", size: "md" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant, size, asChild = false, loading = false, children, disabled, ...props },
  ref,
) {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || loading}
      data-loading={loading || undefined}
      {...props}
    >
      {loading ? (
        <>
          <Loader2 className="size-4 animate-spin motion-reduce:animate-none" aria-hidden />
          <span className="contents">{children}</span>
        </>
      ) : (
        children
      )}
    </Comp>
  );
});

/** A primary action with an adjacent menu trigger, sharing one seam. */
export function SplitButton({
  children,
  onAction,
  menu,
  className,
  variant = "primary",
  size = "md",
  ...props
}: {
  children: React.ReactNode;
  onAction?: () => void;
  menu: React.ReactNode;
  className?: string;
  variant?: VariantProps<typeof buttonVariants>["variant"];
  size?: VariantProps<typeof buttonVariants>["size"];
} & Omit<React.HTMLAttributes<HTMLDivElement>, "children">) {
  return (
    <div className={cn("inline-flex", className)} {...props}>
      <Button
        variant={variant}
        size={size}
        onClick={onAction}
        className="rounded-r-none border-r-0 pr-3"
      >
        {children}
      </Button>
      <span
        aria-hidden
        className={cn(
          "w-px self-stretch",
          variant === "primary" ? "bg-black/15" : "bg-[var(--line-strong)]",
        )}
      />
      {menu}
    </div>
  );
}

export { buttonVariants };
