"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Wordmark } from "@/components/domain/marks";
import { useSessionStore } from "@/stores/session";

const LINKS = [
  { href: "/#how", label: "How it reads" },
  { href: "/#margin", label: "The Margin" },
  { href: "/#evidence", label: "Evidence" },
  { href: "/pricing", label: "Pricing" },
];

export function MarketingHeader() {
  const pathname = usePathname();
  const authed = useSessionStore((s) => s.isAuthenticated);
  const [open, setOpen] = React.useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-line bg-paper/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[76rem] items-center gap-6 px-5 lg:px-8">
        <Link href="/" className="shrink-0 rounded-sm" aria-label="Margin, home">
          <Wordmark />
        </Link>

        <nav aria-label="Marketing" className="hidden flex-1 items-center gap-1 md:flex">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "rounded-md px-3 py-1.5 text-sm text-ink-soft transition-colors duration-150 hover:bg-paper-sunk hover:text-ink",
                pathname === link.href && "text-ink",
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="ml-auto hidden items-center gap-2 md:flex">
          {authed ? (
            <Button asChild variant="primary" size="sm">
              <Link href="/app">Open the workspace</Link>
            </Button>
          ) : (
            <>
              <Button asChild variant="ghost" size="sm">
                <Link href="/login">Sign in</Link>
              </Button>
              <Button asChild variant="primary" size="sm">
                <Link href="/signup">Start reading</Link>
              </Button>
            </>
          )}
        </div>

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-label={open ? "Close menu" : "Open menu"}
          className="ml-auto rounded-md p-1.5 text-ink-soft transition-colors hover:bg-paper-sunk hover:text-ink md:hidden"
        >
          {open ? <X className="size-5" /> : <Menu className="size-5" />}
        </button>
      </div>

      {open ? (
        <div className="border-t border-line bg-paper-raised px-5 py-4 md:hidden">
          <nav aria-label="Marketing" className="space-y-0.5">
            {LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className="block rounded-md px-2 py-2 text-sm text-ink-soft hover:bg-paper-sunk hover:text-ink"
              >
                {link.label}
              </Link>
            ))}
          </nav>
          <div className="mt-3 flex gap-2 border-t border-line pt-3">
            <Button asChild variant="secondary" size="sm" className="flex-1">
              <Link href="/login">Sign in</Link>
            </Button>
            <Button asChild variant="primary" size="sm" className="flex-1">
              <Link href={authed ? "/app" : "/signup"}>{authed ? "Workspace" : "Start reading"}</Link>
            </Button>
          </div>
        </div>
      ) : null}
    </header>
  );
}

const YEAR = new Date().getFullYear();

const FOOTER_GROUPS = [
  {
    title: "Product",
    links: [
      { href: "/#how", label: "How it reads" },
      { href: "/#margin", label: "The Margin" },
      { href: "/pricing", label: "Pricing" },
      { href: "/style", label: "Design system" },
      { href: "/app", label: "Live workspace" },
    ],
  },
  {
    title: "Use it for",
    links: [
      { href: "/#how", label: "Federal RFPs" },
      { href: "/#how", label: "State & local" },
      { href: "/#how", label: "Sources sought" },
      { href: "/#how", label: "Re-competes" },
    ],
  },
  {
    title: "Company",
    links: [
      { href: "/#evidence", label: "Customers" },
      { href: "/login", label: "Sign in" },
      { href: "/signup", label: "Start a trial" },
      { href: "/app/help", label: "Help" },
    ],
  },
];

export function MarketingFooter() {
  return (
    <footer className="border-t border-line bg-paper-raised">
      <div className="mx-auto max-w-[76rem] px-5 py-14 lg:px-8">
        <div className="grid gap-10 md:grid-cols-[1.4fr_repeat(3,1fr)]">
          <div className="max-w-xs space-y-3">
            <Wordmark />
            <p className="text-sm leading-relaxed text-ink-soft">
              Read the solicitation properly. Every finding carries the clause it came from, in the margin where it
              belongs.
            </p>
          </div>
          {FOOTER_GROUPS.map((group) => (
            <div key={group.title}>
              <p className="eyebrow pb-3">{group.title}</p>
              <ul className="space-y-2">
                {group.links.map((link, i) => (
                  <li key={`${link.href}-${i}`}>
                    <Link
                      href={link.href}
                      className="text-sm text-ink-soft underline-offset-4 transition-colors hover:text-ink hover:underline"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-wrap items-center justify-between gap-4 border-t border-line pt-6">
          <p className="font-mono text-2xs text-ink-faint">
            © {YEAR} Margin. A demonstration product — every solicitation shown is fictional.
          </p>
          <p className="font-mono text-2xs text-ink-faint">Set in Fraunces and Geist.</p>
        </div>
      </div>
    </footer>
  );
}
