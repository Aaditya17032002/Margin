"use client";

import * as React from "react";
import * as LabelPrimitive from "@radix-ui/react-label";
import { Search, X } from "lucide-react";

import { cn } from "@/lib/utils";

/** Inputs are sunk wells in the paper rather than raised boxes. */
const fieldSurface = cn(
  "w-full rounded-md border border-line-strong bg-paper-sunk text-ink",
  "placeholder:text-ink-faint/80",
  "transition-[border-color,box-shadow,background-color] duration-150 ease-[cubic-bezier(0.32,0.72,0,1)]",
  "hover:border-[var(--ink-faint)]",
  "focus:border-patina focus:bg-paper-raised focus:outline-none focus:ring-2 focus:ring-[color-mix(in_oklab,var(--patina)_28%,transparent)]",
  "disabled:cursor-not-allowed disabled:opacity-55",
  "aria-[invalid=true]:border-seal aria-[invalid=true]:ring-2 aria-[invalid=true]:ring-[color-mix(in_oklab,var(--seal)_20%,transparent)]",
);

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return <input ref={ref} className={cn(fieldSurface, "h-9 px-3 text-sm", className)} {...props} />;
  },
);

export const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(function Textarea({ className, ...props }, ref) {
  return (
    <textarea
      ref={ref}
      className={cn(fieldSurface, "min-h-24 resize-y px-3 py-2 text-sm leading-relaxed", className)}
      {...props}
    />
  );
});

export const Label = React.forwardRef<
  React.ComponentRef<typeof LabelPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root>
>(function Label({ className, ...props }, ref) {
  return (
    <LabelPrimitive.Root
      ref={ref}
      className={cn("text-sm font-medium text-ink", className)}
      {...props}
    />
  );
});

export function Field({
  label,
  hint,
  error,
  required,
  htmlFor,
  children,
  className,
}: {
  label?: React.ReactNode;
  hint?: React.ReactNode;
  error?: string;
  required?: boolean;
  htmlFor?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("space-y-1.5", className)}>
      {label ? (
        <div className="flex items-baseline justify-between gap-3">
          <Label htmlFor={htmlFor}>
            {label}
            {required ? (
              <span className="ml-1 text-seal" aria-hidden>
                *
              </span>
            ) : null}
          </Label>
          {hint && !error ? <span className="text-xs text-ink-faint">{hint}</span> : null}
        </div>
      ) : null}
      {children}
      {error ? (
        <p role="alert" className="text-xs text-seal">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function SearchField({
  value,
  onValueChange,
  placeholder = "Search",
  className,
  onClear,
  ...props
}: {
  value: string;
  onValueChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  onClear?: () => void;
} & Omit<React.InputHTMLAttributes<HTMLInputElement>, "value" | "onChange">) {
  return (
    <div className={cn("relative", className)}>
      <Search
        className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-ink-faint"
        aria-hidden
      />
      <input
        type="search"
        value={value}
        onChange={(e) => onValueChange(e.target.value)}
        placeholder={placeholder}
        className={cn(fieldSurface, "h-9 pl-8.5 pr-8 text-sm [&::-webkit-search-cancel-button]:hidden")}
        {...props}
      />
      {value ? (
        <button
          type="button"
          onClick={() => {
            onValueChange("");
            onClear?.();
          }}
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded-xs p-0.5 text-ink-faint transition-colors hover:text-ink"
          aria-label="Clear search"
        >
          <X className="size-3.5" />
        </button>
      ) : null}
    </div>
  );
}

export { fieldSurface };
