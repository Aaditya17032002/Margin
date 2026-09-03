"use client";

import { Toaster as SonnerToaster, toast } from "sonner";
import { AlertTriangle, CheckCircle2, Info, ShieldAlert } from "lucide-react";

/**
 * Every acknowledgement in Margin lands here. The banner is a paper card with a
 * semantic left accent rather than a coloured tile, so a success and a hard
 * failure read as the same object with a different mark in the margin.
 */
export function Toaster() {
  return (
    <SonnerToaster
      position="top-right"
      offset={16}
      gap={10}
      visibleToasts={4}
      duration={5200}
      closeButton={false}
      toastOptions={{
        unstyled: true,
        classNames: {
          toast:
            "group pointer-events-auto flex w-[380px] max-w-[calc(100vw-2rem)] items-start gap-3 rounded-lg border border-line border-l-[3px] border-l-[var(--line-strong)] bg-paper-raised px-4 py-3.5 shadow-[var(--shadow-float)]",
          title: "text-sm font-medium text-ink leading-snug",
          description: "text-sm text-ink-soft leading-relaxed mt-0.5",
          actionButton:
            "shrink-0 rounded-sm border border-line-strong bg-paper-sunk px-2.5 py-1 text-xs font-medium text-ink transition-colors hover:bg-paper hover:border-[var(--ink-faint)]",
          cancelButton:
            "shrink-0 rounded-sm px-2 py-1 text-xs font-medium text-ink-faint transition-colors hover:text-ink",
          icon: "shrink-0 mt-px [&_svg]:size-4",
          success: "!border-l-leaf [&_[data-icon]_svg]:text-leaf",
          error: "!border-l-seal [&_[data-icon]_svg]:text-seal",
          warning: "!border-l-ochre [&_[data-icon]_svg]:text-ochre",
          info: "!border-l-slate [&_[data-icon]_svg]:text-slate",
        },
      }}
      icons={{
        success: <CheckCircle2 aria-hidden />,
        error: <ShieldAlert aria-hidden />,
        warning: <AlertTriangle aria-hidden />,
        info: <Info aria-hidden />,
      }}
    />
  );
}

type Options = {
  description?: string;
  undo?: () => void;
  action?: { label: string; onClick: () => void };
  duration?: number;
};

function withAction(options?: Options) {
  if (!options) return {};
  const { description, undo, action, duration } = options;
  return {
    description,
    duration,
    action: undo
      ? { label: "Undo", onClick: undo }
      : action
        ? { label: action.label, onClick: action.onClick }
        : undefined,
  };
}

export const notify = {
  success: (message: string, options?: Options) => toast.success(message, withAction(options)),
  error: (message: string, options?: Options) => toast.error(message, withAction(options)),
  warning: (message: string, options?: Options) => toast.warning(message, withAction(options)),
  info: (message: string, options?: Options) => toast.info(message, withAction(options)),
  promise: toast.promise,
  dismiss: toast.dismiss,
};
