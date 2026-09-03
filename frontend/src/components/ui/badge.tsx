"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 text-2xs font-medium leading-5 whitespace-nowrap",
  {
    variants: {
      tone: {
        neutral: "border-line-strong bg-paper-sunk text-ink-soft",
        patina: "border-[color-mix(in_oklab,var(--patina)_30%,transparent)] bg-patina-tint text-patina",
        seal: "border-[color-mix(in_oklab,var(--seal)_30%,transparent)] bg-[var(--seal-tint)] text-seal",
        ochre: "border-[color-mix(in_oklab,var(--ochre)_34%,transparent)] bg-[var(--ochre-tint)] text-[color-mix(in_oklab,var(--ochre)_82%,var(--ink))]",
        leaf: "border-[color-mix(in_oklab,var(--leaf)_30%,transparent)] bg-[var(--leaf-tint)] text-leaf",
        slate: "border-[color-mix(in_oklab,var(--slate)_28%,transparent)] bg-[var(--slate-tint)] text-slate",
        ink: "border-ink/25 bg-ink text-[var(--paper-raised)]",
      },
      shape: {
        default: "",
        mono: "font-mono tracking-[0.04em] uppercase",
      },
    },
    defaultVariants: { tone: "neutral", shape: "default" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, tone, shape, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ tone, shape }), className)} {...props} />;
}

export { badgeVariants };
