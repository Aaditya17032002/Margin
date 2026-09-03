"use client";

import * as React from "react";
import * as CheckboxPrimitive from "@radix-ui/react-checkbox";
import * as RadioGroupPrimitive from "@radix-ui/react-radio-group";
import * as SwitchPrimitive from "@radix-ui/react-switch";
import * as SliderPrimitive from "@radix-ui/react-slider";
import * as SelectPrimitive from "@radix-ui/react-select";
import * as ToggleGroupPrimitive from "@radix-ui/react-toggle-group";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import * as AccordionPrimitive from "@radix-ui/react-accordion";
import * as ProgressPrimitive from "@radix-ui/react-progress";
import * as AvatarPrimitive from "@radix-ui/react-avatar";
import { Check, ChevronDown, ChevronsUpDown, Minus, Search, X } from "lucide-react";

import { cn, initials } from "@/lib/utils";
import { floatingSurface } from "./overlay";
import { fieldSurface } from "./input";

/* ---------------------------------------------------------------- */
/* Checkbox / Radio / Switch                                          */
/* ---------------------------------------------------------------- */

export const Checkbox = React.forwardRef<
  React.ComponentRef<typeof CheckboxPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof CheckboxPrimitive.Root>
>(function Checkbox({ className, ...props }, ref) {
  return (
    <CheckboxPrimitive.Root
      ref={ref}
      className={cn(
        "peer size-4 shrink-0 rounded-xs border border-line-strong bg-paper-sunk",
        "transition-[background-color,border-color] duration-150 ease-[cubic-bezier(0.32,0.72,0,1)]",
        "hover:border-[var(--ink-faint)]",
        "data-[state=checked]:border-patina data-[state=checked]:bg-patina",
        "data-[state=indeterminate]:border-patina data-[state=indeterminate]:bg-patina",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    >
      <CheckboxPrimitive.Indicator className="flex items-center justify-center text-[var(--patina-ink)]">
        {props.checked === "indeterminate" ? (
          <Minus className="size-3" strokeWidth={3} />
        ) : (
          <Check className="size-3" strokeWidth={3} />
        )}
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  );
});

export const RadioGroup = RadioGroupPrimitive.Root;

export const RadioGroupItem = React.forwardRef<
  React.ComponentRef<typeof RadioGroupPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof RadioGroupPrimitive.Item>
>(function RadioGroupItem({ className, ...props }, ref) {
  return (
    <RadioGroupPrimitive.Item
      ref={ref}
      className={cn(
        "size-4 shrink-0 rounded-full border border-line-strong bg-paper-sunk",
        "transition-[border-color] duration-150",
        "hover:border-[var(--ink-faint)] data-[state=checked]:border-patina",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    >
      <RadioGroupPrimitive.Indicator className="flex size-full items-center justify-center">
        <span className="size-2 rounded-full bg-patina" />
      </RadioGroupPrimitive.Indicator>
    </RadioGroupPrimitive.Item>
  );
});

export const Switch = React.forwardRef<
  React.ComponentRef<typeof SwitchPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SwitchPrimitive.Root>
>(function Switch({ className, ...props }, ref) {
  return (
    <SwitchPrimitive.Root
      ref={ref}
      className={cn(
        "peer inline-flex h-5 w-9 shrink-0 items-center rounded-full border border-line-strong p-0.5",
        "transition-colors duration-200 ease-[cubic-bezier(0.32,0.72,0,1)]",
        "bg-paper-sunk data-[state=checked]:border-patina data-[state=checked]:bg-patina",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    >
      <SwitchPrimitive.Thumb
        className={cn(
          "pointer-events-none block size-3.5 rounded-full bg-[var(--paper-raised)] shadow-[0_1px_2px_rgba(0,0,0,0.18)]",
          "transition-transform duration-200 ease-[cubic-bezier(0.32,0.72,0,1)]",
          "data-[state=checked]:translate-x-4",
        )}
      />
    </SwitchPrimitive.Root>
  );
});

export function SettingRow({
  label,
  description,
  control,
  className,
}: {
  label: React.ReactNode;
  description?: React.ReactNode;
  control: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-start justify-between gap-8 py-3.5", className)}>
      <div className="min-w-0 space-y-0.5">
        <p className="text-sm font-medium text-ink">{label}</p>
        {description ? <p className="text-sm text-ink-soft">{description}</p> : null}
      </div>
      <div className="shrink-0 pt-0.5">{control}</div>
    </div>
  );
}

/* ---------------------------------------------------------------- */
/* Slider                                                             */
/* ---------------------------------------------------------------- */

export const Slider = React.forwardRef<
  React.ComponentRef<typeof SliderPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SliderPrimitive.Root>
>(function Slider({ className, ...props }, ref) {
  return (
    <SliderPrimitive.Root
      ref={ref}
      className={cn("relative flex w-full touch-none select-none items-center", className)}
      {...props}
    >
      <SliderPrimitive.Track className="relative h-1 w-full grow overflow-hidden rounded-full bg-paper-sunk ring-1 ring-inset ring-[var(--line-strong)]">
        <SliderPrimitive.Range className="absolute h-full bg-patina" />
      </SliderPrimitive.Track>
      <SliderPrimitive.Thumb className="block size-4 rounded-full border border-patina bg-paper-raised shadow-[var(--shadow-raised)] transition-transform duration-150 hover:scale-105" />
    </SliderPrimitive.Root>
  );
});

/* ---------------------------------------------------------------- */
/* Select                                                             */
/* ---------------------------------------------------------------- */

export const Select = SelectPrimitive.Root;
export const SelectValue = SelectPrimitive.Value;

export const SelectTrigger = React.forwardRef<
  React.ComponentRef<typeof SelectPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger>
>(function SelectTrigger({ className, children, ...props }, ref) {
  return (
    <SelectPrimitive.Trigger
      ref={ref}
      className={cn(
        fieldSurface,
        "flex h-9 items-center justify-between gap-2 px-3 text-sm data-[placeholder]:text-ink-faint",
        className,
      )}
      {...props}
    >
      <span className="truncate text-left">{children}</span>
      <SelectPrimitive.Icon asChild>
        <ChevronDown className="size-4 shrink-0 text-ink-faint transition-transform duration-200 group-data-[state=open]:rotate-180" />
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  );
});

export function SelectContent({
  className,
  children,
  ...props
}: React.ComponentPropsWithoutRef<typeof SelectPrimitive.Content>) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        position="popper"
        sideOffset={6}
        className={cn(
          floatingSurface,
          "max-h-72 min-w-[var(--radix-select-trigger-width)] overflow-hidden p-1",
          className,
        )}
        {...props}
      >
        <SelectPrimitive.Viewport>{children}</SelectPrimitive.Viewport>
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  );
}

export function SelectItem({
  className,
  children,
  ...props
}: React.ComponentPropsWithoutRef<typeof SelectPrimitive.Item>) {
  return (
    <SelectPrimitive.Item
      className={cn(
        "relative flex cursor-default select-none items-center rounded-sm py-1.5 pl-7 pr-2.5 text-sm text-ink-soft outline-none",
        "data-[highlighted]:bg-paper-sunk data-[highlighted]:text-ink",
        "data-[state=checked]:text-ink",
        className,
      )}
      {...props}
    >
      <span className="absolute left-2 flex size-3.5 items-center justify-center">
        <SelectPrimitive.ItemIndicator>
          <Check className="size-3.5 text-patina" strokeWidth={2.5} />
        </SelectPrimitive.ItemIndicator>
      </span>
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
    </SelectPrimitive.Item>
  );
}

export function SelectLabel({
  className,
  ...props
}: React.ComponentPropsWithoutRef<typeof SelectPrimitive.Label>) {
  return (
    <SelectPrimitive.Label
      className={cn("px-2.5 pb-1 pt-2 font-mono text-2xs uppercase tracking-[0.13em] text-ink-faint", className)}
      {...props}
    />
  );
}

/* ---------------------------------------------------------------- */
/* Segmented control                                                  */
/* ---------------------------------------------------------------- */

export function Segmented({
  value,
  onValueChange,
  options,
  className,
  size = "md",
  ariaLabel,
}: {
  value: string;
  onValueChange: (value: string) => void;
  options: { value: string; label: React.ReactNode; icon?: React.ReactNode }[];
  className?: string;
  size?: "sm" | "md";
  ariaLabel: string;
}) {
  return (
    <ToggleGroupPrimitive.Root
      type="single"
      value={value}
      onValueChange={(next) => next && onValueChange(next)}
      aria-label={ariaLabel}
      className={cn(
        "inline-flex items-center gap-0.5 rounded-md border border-line-strong bg-paper-sunk p-0.5",
        className,
      )}
    >
      {options.map((option) => (
        <ToggleGroupPrimitive.Item
          key={option.value}
          value={option.value}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-sm font-medium text-ink-soft",
            "transition-[background-color,color,box-shadow] duration-150 ease-[cubic-bezier(0.32,0.72,0,1)]",
            "hover:text-ink",
            "data-[state=on]:bg-paper-raised data-[state=on]:text-ink data-[state=on]:shadow-[0_1px_2px_rgba(33,29,23,0.08)]",
            size === "sm" ? "h-6 px-2 text-xs [&_svg]:size-3.5" : "h-7 px-2.5 text-sm [&_svg]:size-4",
          )}
        >
          {option.icon}
          {option.label}
        </ToggleGroupPrimitive.Item>
      ))}
    </ToggleGroupPrimitive.Root>
  );
}

/* ---------------------------------------------------------------- */
/* Tabs                                                               */
/* ---------------------------------------------------------------- */

export const Tabs = TabsPrimitive.Root;

export function TabsList({
  className,
  ...props
}: React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>) {
  return (
    <TabsPrimitive.List
      className={cn("scrollbar-none flex gap-1 overflow-x-auto border-b border-line", className)}
      {...props}
    />
  );
}

export function TabsTrigger({
  className,
  ...props
}: React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      className={cn(
        "relative whitespace-nowrap px-3 py-2.5 text-sm font-medium text-ink-faint",
        "transition-colors duration-150 hover:text-ink",
        "after:absolute after:inset-x-2 after:bottom-[-1px] after:h-[2px] after:rounded-full after:bg-transparent",
        "after:transition-colors after:duration-200",
        "data-[state=active]:text-ink data-[state=active]:after:bg-patina",
        className,
      )}
      {...props}
    />
  );
}

export function TabsContent({
  className,
  ...props
}: React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>) {
  return (
    <TabsPrimitive.Content
      className={cn("focus-visible:outline-none data-[state=active]:animate-[rise_240ms_var(--ease-editorial)_both]", className)}
      {...props}
    />
  );
}

/* ---------------------------------------------------------------- */
/* Accordion                                                          */
/* ---------------------------------------------------------------- */

export const Accordion = AccordionPrimitive.Root;

export function AccordionItem({
  className,
  ...props
}: React.ComponentPropsWithoutRef<typeof AccordionPrimitive.Item>) {
  return <AccordionPrimitive.Item className={cn("border-b border-line", className)} {...props} />;
}

export function AccordionTrigger({
  className,
  children,
  ...props
}: React.ComponentPropsWithoutRef<typeof AccordionPrimitive.Trigger>) {
  return (
    <AccordionPrimitive.Header className="flex">
      <AccordionPrimitive.Trigger
        className={cn(
          "group flex flex-1 items-center justify-between gap-4 py-4 text-left text-base font-medium text-ink",
          "transition-colors duration-150 hover:text-patina",
          className,
        )}
        {...props}
      >
        {children}
        <ChevronDown className="size-4 shrink-0 text-ink-faint transition-transform duration-260 ease-[cubic-bezier(0.32,0.72,0,1)] group-data-[state=open]:rotate-180" />
      </AccordionPrimitive.Trigger>
    </AccordionPrimitive.Header>
  );
}

export function AccordionContent({
  className,
  children,
  ...props
}: React.ComponentPropsWithoutRef<typeof AccordionPrimitive.Content>) {
  return (
    <AccordionPrimitive.Content
      className={cn(
        "overflow-hidden text-sm text-ink-soft",
        "data-[state=open]:animate-[fade_200ms_var(--ease-editorial)_both]",
        className,
      )}
      {...props}
    >
      <div className="pb-4 pr-8 leading-relaxed">{children}</div>
    </AccordionPrimitive.Content>
  );
}

/* ---------------------------------------------------------------- */
/* Progress                                                           */
/* ---------------------------------------------------------------- */

export function Progress({
  value,
  className,
  tone = "patina",
  label,
}: {
  value: number;
  className?: string;
  tone?: "patina" | "ochre" | "seal" | "leaf";
  label?: string;
}) {
  const bar = {
    patina: "bg-patina",
    ochre: "bg-ochre",
    seal: "bg-seal",
    leaf: "bg-leaf",
  }[tone];
  return (
    <ProgressPrimitive.Root
      value={value}
      aria-label={label}
      className={cn("relative h-1.5 w-full overflow-hidden rounded-full bg-paper-sunk ring-1 ring-inset ring-[var(--line)]", className)}
    >
      <ProgressPrimitive.Indicator
        className={cn("h-full rounded-full transition-transform duration-500 ease-[cubic-bezier(0.32,0.72,0,1)]", bar)}
        style={{ transform: `translateX(-${100 - Math.max(0, Math.min(100, value))}%)` }}
      />
    </ProgressPrimitive.Root>
  );
}

/* ---------------------------------------------------------------- */
/* Avatar                                                             */
/* ---------------------------------------------------------------- */

const TONE_CLASS: Record<string, string> = {
  patina: "bg-patina-tint text-patina",
  slate: "bg-[var(--slate-tint)] text-slate",
  ochre: "bg-[var(--ochre-tint)] text-[color-mix(in_oklab,var(--ochre)_80%,var(--ink))]",
  leaf: "bg-[var(--leaf-tint)] text-leaf",
  seal: "bg-[var(--seal-tint)] text-seal",
  ink: "bg-paper-sunk text-ink-soft",
};

export function Avatar({
  name,
  tone = "patina",
  size = "md",
  className,
  presence,
}: {
  name: string;
  tone?: string;
  size?: "xs" | "sm" | "md" | "lg";
  className?: string;
  presence?: "online" | "away" | "offline";
}) {
  const sizeClass = {
    xs: "size-6 text-2xs",
    sm: "size-7 text-xs",
    md: "size-9 text-sm",
    lg: "size-14 text-lg",
  }[size];
  return (
    <span className={cn("relative inline-flex shrink-0", className)}>
      <AvatarPrimitive.Root
        className={cn(
          "inline-flex items-center justify-center overflow-hidden rounded-full border border-line font-medium",
          TONE_CLASS[tone] ?? TONE_CLASS.patina,
          sizeClass,
        )}
      >
        <AvatarPrimitive.Fallback className="font-sans tracking-tight">
          {initials(name)}
        </AvatarPrimitive.Fallback>
      </AvatarPrimitive.Root>
      {presence ? (
        <span
          aria-label={`${name} is ${presence}`}
          className={cn(
            "absolute -bottom-px -right-px size-2.5 rounded-full border-2 border-[var(--paper-raised)]",
            presence === "online" && "bg-leaf",
            presence === "away" && "bg-ochre",
            presence === "offline" && "bg-[var(--line-strong)]",
          )}
        />
      ) : null}
    </span>
  );
}

export function AvatarGroup({
  names,
  tones,
  max = 4,
  size = "sm",
}: {
  names: string[];
  tones?: string[];
  max?: number;
  size?: "xs" | "sm" | "md";
}) {
  const shown = names.slice(0, max);
  const rest = names.length - shown.length;
  return (
    <div className="flex items-center">
      {shown.map((name, i) => (
        <Avatar
          key={name}
          name={name}
          tone={tones?.[i] ?? ["patina", "slate", "ochre", "leaf", "seal"][i % 5]}
          size={size}
          className={cn(i > 0 && "-ml-2", "ring-2 ring-[var(--paper-raised)] rounded-full")}
        />
      ))}
      {rest > 0 ? (
        <span className="-ml-2 inline-flex size-7 items-center justify-center rounded-full border border-line bg-paper-sunk text-2xs font-medium text-ink-soft ring-2 ring-[var(--paper-raised)]">
          +{rest}
        </span>
      ) : null}
    </div>
  );
}

/* ---------------------------------------------------------------- */
/* Combobox / multi-select / tags                                     */
/* ---------------------------------------------------------------- */

export function Combobox({
  value,
  onValueChange,
  options,
  placeholder = "Select",
  emptyLabel = "Nothing matched",
  className,
  allowClear,
}: {
  value: string | null;
  onValueChange: (value: string | null) => void;
  options: { value: string; label: string; hint?: string }[];
  placeholder?: string;
  emptyLabel?: string;
  className?: string;
  allowClear?: boolean;
}) {
  const [open, setOpen] = React.useState(false);
  const [query, setQuery] = React.useState("");
  const selected = options.find((o) => o.value === value);
  const filtered = options.filter((o) => o.label.toLowerCase().includes(query.toLowerCase()));
  const listId = React.useId();

  return (
    <div className={cn("relative", className)}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => setOpen((v) => !v)}
        className={cn(fieldSurface, "flex h-9 items-center justify-between gap-2 px-3 text-left text-sm")}
      >
        <span className={cn("truncate", !selected && "text-ink-faint")}>
          {selected?.label ?? placeholder}
        </span>
        <ChevronsUpDown className="size-3.5 shrink-0 text-ink-faint" />
      </button>
      {open ? (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} aria-hidden />
          <div
            id={listId}
            role="listbox"
            className={cn(
              floatingSurface,
              "absolute left-0 right-0 top-[calc(100%+6px)] z-50 overflow-hidden",
              "animate-[rise_180ms_var(--ease-editorial)_both]",
            )}
          >
            <div className="flex items-center gap-2 border-b border-line px-3">
              <Search className="size-3.5 text-ink-faint" aria-hidden />
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Filter"
                className="h-9 w-full bg-transparent text-sm outline-none placeholder:text-ink-faint"
              />
            </div>
            <div className="max-h-56 overflow-y-auto p-1">
              {allowClear ? (
                <button
                  type="button"
                  role="option"
                  aria-selected={value === null}
                  onClick={() => {
                    onValueChange(null);
                    setOpen(false);
                    setQuery("");
                  }}
                  className="flex w-full items-center rounded-sm px-2.5 py-1.5 text-left text-sm text-ink-faint hover:bg-paper-sunk"
                >
                  Clear selection
                </button>
              ) : null}
              {filtered.length === 0 ? (
                <p className="px-2.5 py-3 text-sm text-ink-faint">{emptyLabel}</p>
              ) : (
                filtered.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    role="option"
                    aria-selected={option.value === value}
                    onClick={() => {
                      onValueChange(option.value);
                      setOpen(false);
                      setQuery("");
                    }}
                    className={cn(
                      "flex w-full items-center justify-between gap-3 rounded-sm px-2.5 py-1.5 text-left text-sm",
                      "hover:bg-paper-sunk",
                      option.value === value ? "text-ink" : "text-ink-soft",
                    )}
                  >
                    <span className="truncate">{option.label}</span>
                    {option.value === value ? <Check className="size-3.5 shrink-0 text-patina" /> : null}
                    {option.hint && option.value !== value ? (
                      <span className="shrink-0 font-mono text-2xs text-ink-faint">{option.hint}</span>
                    ) : null}
                  </button>
                ))
              )}
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}

export function TagsInput({
  values,
  onValuesChange,
  placeholder = "Add a tag",
  className,
}: {
  values: string[];
  onValuesChange: (values: string[]) => void;
  placeholder?: string;
  className?: string;
}) {
  const [draft, setDraft] = React.useState("");

  function commit() {
    const tag = draft.trim();
    if (!tag || values.includes(tag)) return setDraft("");
    onValuesChange([...values, tag]);
    setDraft("");
  }

  return (
    <div
      className={cn(
        fieldSurface,
        "flex min-h-9 flex-wrap items-center gap-1.5 px-2 py-1.5 focus-within:border-patina focus-within:bg-paper-raised",
        className,
      )}
    >
      {values.map((tag) => (
        <span
          key={tag}
          className="inline-flex items-center gap-1 rounded-sm border border-line-strong bg-paper-raised px-1.5 py-0.5 text-xs text-ink-soft"
        >
          {tag}
          <button
            type="button"
            onClick={() => onValuesChange(values.filter((t) => t !== tag))}
            aria-label={`Remove ${tag}`}
            className="text-ink-faint transition-colors hover:text-seal"
          >
            <X className="size-3" />
          </button>
        </span>
      ))}
      <input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === ",") {
            e.preventDefault();
            commit();
          }
          if (e.key === "Backspace" && !draft && values.length) {
            onValuesChange(values.slice(0, -1));
          }
        }}
        onBlur={commit}
        placeholder={values.length ? "" : placeholder}
        className="min-w-24 flex-1 bg-transparent text-sm outline-none placeholder:text-ink-faint"
      />
    </div>
  );
}
