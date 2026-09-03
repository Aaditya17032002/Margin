"use client";

import * as React from "react";
import Link from "next/link";
import { motion } from "motion/react";

import { cn } from "@/lib/utils";
import { Wordmark } from "@/components/domain/marks";

const ASIDE_LINES = [
  "L.3.1  Volume I, Technical, shall not exceed forty (40) pages,",
  "excluding resumes and the cross-reference matrix.",
  "",
  "M.2.1  Award will be made to the offeror whose proposal",
  "represents the best value to the Agency.",
  "",
  "C.5.4  The contractor shall complete transition-in within",
  "thirty (30) calendar days of the notice to proceed.",
];

/**
 * Auth screens keep the page metaphor: the form sits on the leaf, and the
 * right-hand leaf is the document being read, so the product's argument is
 * visible before anybody has signed in.
 */
export function AuthFrame({
  eyebrow,
  title,
  description,
  children,
  footer,
  aside,
}: {
  eyebrow?: string;
  title: string;
  description?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  aside?: React.ReactNode;
}) {
  return (
    <div className="grid min-h-dvh bg-paper lg:grid-cols-[1fr_0.85fr]">
      <div className="flex flex-col px-5 py-8 sm:px-10 lg:px-14">
        <Link href="/" className="inline-flex w-fit rounded-sm" aria-label="Margin, home">
          <Wordmark />
        </Link>

        <main id="main" className="flex flex-1 items-center py-10">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
            className="w-full max-w-sm"
          >
            {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
            <h1 className="display-tight mt-2 text-3xl leading-tight text-ink">{title}</h1>
            {description ? (
              <div className="mt-3 text-sm leading-relaxed text-ink-soft">{description}</div>
            ) : null}
            <div className="mt-8">{children}</div>
          </motion.div>
        </main>

        {footer ? <div className="text-sm text-ink-soft">{footer}</div> : null}
      </div>

      <aside className="relative hidden overflow-hidden border-l border-line bg-paper-raised lg:block">
        <div
          aria-hidden
          className="absolute inset-y-0 left-14 w-px bg-[color-mix(in_oklab,var(--seal)_20%,transparent)]"
        />
        <div className="flex h-full flex-col justify-center px-14 py-16">
          {aside ?? <DefaultAside />}
        </div>
      </aside>
    </div>
  );
}

function DefaultAside() {
  return (
    <div className="max-w-md">
      <p className="eyebrow">Why the name</p>
      <p className="display-tight mt-3 font-display text-2xl leading-snug text-ink">
        The margin is where the reader answers the text.
      </p>
      <p className="mt-4 text-sm leading-relaxed text-ink-soft">
        Every finding Margin produces carries the page, the section, and the line it stands on. Nothing is asserted
        without it.
      </p>

      <div className="paper-grain mt-8 rounded-md border border-line bg-paper px-5 py-5 shadow-[var(--shadow-raised)]">
        <pre className="scrollbar-none overflow-x-auto font-mono text-[11.5px] leading-[1.9] text-ink-soft">
          {ASIDE_LINES.map((line, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.25 + index * 0.06, duration: 0.4 }}
              className={cn(index === 0 || index === 1 ? "highlight-clause text-ink" : "")}
            >
              {line || " "}
            </motion.div>
          ))}
        </pre>
      </div>
    </div>
  );
}

/** Microsoft and Google marks, drawn rather than imported as logos. */
export function MicrosoftGlyph({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" className={cn("size-4", className)} aria-hidden>
      <rect x="0.5" y="0.5" width="6.6" height="6.6" fill="#F25022" />
      <rect x="8.9" y="0.5" width="6.6" height="6.6" fill="#7FBA00" />
      <rect x="0.5" y="8.9" width="6.6" height="6.6" fill="#00A4EF" />
      <rect x="8.9" y="8.9" width="6.6" height="6.6" fill="#FFB900" />
    </svg>
  );
}

export function GoogleGlyph({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 18 18" className={cn("size-4", className)} aria-hidden>
      <path
        fill="#4285F4"
        d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62Z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.81.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A9 9 0 0 0 9 18Z"
      />
      <path fill="#FBBC05" d="M3.97 10.72a5.4 5.4 0 0 1 0-3.44V4.95H.96a9 9 0 0 0 0 8.1l3.01-2.33Z" />
      <path
        fill="#EA4335"
        d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .96 4.95l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58Z"
      />
    </svg>
  );
}
