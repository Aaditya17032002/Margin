import Link from "next/link";
import type { Metadata } from "next";
import { ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Wordmark } from "@/components/domain/marks";

export const metadata: Metadata = {
  title: "Page not found",
};

const SUGGESTIONS = [
  { href: "/app", label: "Dashboard", hint: "Where every bid stands today" },
  { href: "/app/analyses", label: "Analyses", hint: "Every solicitation in flight" },
  { href: "/app/deadlines", label: "Deadlines", hint: "Calendar and countdowns" },
  { href: "/", label: "Home", hint: "What Margin is for" },
];

export default function NotFound() {
  return (
    <div className="flex min-h-dvh flex-col bg-paper px-5 py-8 sm:px-10">
      <Link href="/" className="inline-flex w-fit rounded-sm" aria-label="Margin, home">
        <Wordmark />
      </Link>

      <main id="main" className="flex flex-1 items-center py-16">
        <div className="mx-auto grid w-full max-w-3xl gap-10 sm:grid-cols-[auto_1fr] sm:gap-14">
          {/* A page torn at the margin — the number lives where the rule would be. */}
          <div aria-hidden className="relative shrink-0">
            <svg viewBox="0 0 120 150" className="h-40 w-auto sm:h-48" fill="none">
              <path
                d="M8 4.5h72l32 30v111H8Z"
                fill="var(--paper-raised)"
                stroke="var(--line-strong)"
                strokeWidth="1.2"
              />
              <path d="M80 4.5v30h32" stroke="var(--line-strong)" strokeWidth="1.2" />
              <path d="M30 4.5v141" stroke="var(--seal)" strokeWidth="1.2" opacity="0.35" />
              <path
                d="M42 60h50M42 72h50M42 84h34"
                stroke="var(--line-strong)"
                strokeWidth="1.4"
                strokeLinecap="round"
              />
              <path
                d="M42 104c8-6 16 6 24 0s16 6 24 0"
                stroke="var(--ochre)"
                strokeWidth="1.4"
                strokeLinecap="round"
                opacity="0.6"
              />
              <text
                x="19"
                y="130"
                textAnchor="middle"
                className="font-mono"
                fontSize="11"
                fill="var(--ink-faint)"
              >
                404
              </text>
            </svg>
          </div>

          <div className="max-w-md">
            <p className="eyebrow">Page not found</p>
            <h1 className="display-tight mt-2 text-3xl leading-tight text-ink sm:text-4xl">
              This page is not in the document.
            </h1>
            <p className="mt-4 text-base leading-relaxed text-ink-soft">
              The address does not resolve to anything we hold. It may have been an analysis that was deleted, or a
              link from a different workspace.
            </p>

            <ul className="mt-8 divide-y divide-line border-y border-line">
              {SUGGESTIONS.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="group flex items-center justify-between gap-4 py-3 transition-colors duration-150"
                  >
                    <span>
                      <span className="block text-sm text-ink">{item.label}</span>
                      <span className="block text-xs text-ink-faint">{item.hint}</span>
                    </span>
                    <ArrowRight className="size-4 shrink-0 -translate-x-1 text-ink-faint opacity-0 transition-all duration-200 group-hover:translate-x-0 group-hover:opacity-100" />
                  </Link>
                </li>
              ))}
            </ul>

            <Button asChild variant="primary" className="mt-8">
              <Link href="/app">Back to the dashboard</Link>
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}
