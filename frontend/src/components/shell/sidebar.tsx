"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, useReducedMotion } from "motion/react";
import { Check, ChevronsLeft, ChevronsRight, ChevronsUpDown, Plus } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Tooltip } from "@/components/ui/overlay";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/overlay";
import { Wordmark, MarginMark } from "@/components/domain/marks";
import { PRIMARY_NAV, SECONDARY_NAV } from "./navigation";
import { usePrefsStore } from "@/stores/workspace";
import { useSessionStore } from "@/stores/session";

export function Sidebar({ className }: { className?: string }) {
  const pathname = usePathname();
  const collapsed = usePrefsStore((s) => s.sidebarCollapsed);
  const setCollapsed = usePrefsStore((s) => s.setSidebarCollapsed);
  const org = useSessionStore((s) => s.org);
  const reduce = useReducedMotion();

  return (
    <nav
      aria-label="Primary"
      data-collapsed={collapsed || undefined}
      className={cn(
        "group/sidebar sticky top-0 hidden h-dvh shrink-0 flex-col border-r border-line bg-paper-raised lg:flex",
        "transition-[width] duration-260 ease-[cubic-bezier(0.32,0.72,0,1)]",
        collapsed ? "w-[4.25rem]" : "w-[15.5rem]",
        className,
      )}
    >
      <div className={cn("flex h-14 items-center border-b border-line", collapsed ? "justify-center px-2" : "px-4")}>
        <Link
          href="/app"
          className="inline-flex items-center gap-2 rounded-sm focus-visible:outline-2"
          aria-label="Margin — dashboard"
        >
          {collapsed ? <MarginMark /> : <Wordmark />}
        </Link>
      </div>

      {!collapsed ? (
        <div className="border-b border-line px-3 py-3">
          <OrgSwitcher name={org?.name ?? "Thornfield Group"} plan={org?.plan ?? "Practice"} />
        </div>
      ) : null}

      <div className="min-h-0 flex-1 overflow-y-auto px-3 py-4">
        {!collapsed ? (
          <Button asChild variant="primary" size="sm" className="mb-5 w-full">
            <Link href="/app/analyses/new">
              <Plus />
              New analysis
            </Link>
          </Button>
        ) : (
          <Tooltip content="New analysis" side="right" shortcut="N">
            <Button asChild variant="primary" size="icon" className="mb-5">
              <Link href="/app/analyses/new" aria-label="New analysis">
                <Plus />
              </Link>
            </Button>
          </Tooltip>
        )}

        <div className="space-y-6">
          {PRIMARY_NAV.map((group) => (
            <div key={group.group}>
              {!collapsed ? (
                <p className="px-2.5 pb-1.5 font-mono text-2xs uppercase tracking-[0.14em] text-ink-faint">
                  {group.group}
                </p>
              ) : (
                <span className="mx-auto mb-2 block h-px w-6 bg-line" aria-hidden />
              )}
              <ul className="space-y-0.5">
                {group.items.map((item) => {
                  const active = item.exact ? pathname === item.href : pathname.startsWith(item.href);
                  const link = (
                    <Link
                      href={item.href}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "relative flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm",
                        "transition-colors duration-150 ease-[cubic-bezier(0.32,0.72,0,1)]",
                        collapsed && "justify-center px-0",
                        active ? "text-ink" : "text-ink-soft hover:bg-paper-sunk hover:text-ink",
                      )}
                    >
                      {active ? (
                        <motion.span
                          layoutId="nav-active"
                          transition={reduce ? { duration: 0 } : { type: "spring", stiffness: 480, damping: 42 }}
                          className="absolute inset-0 -z-10 rounded-md bg-patina-tint ring-1 ring-inset ring-[color-mix(in_oklab,var(--patina)_22%,transparent)]"
                        />
                      ) : null}
                      <item.icon className={cn("size-4 shrink-0", active && "text-patina")} aria-hidden />
                      {!collapsed ? <span className="truncate">{item.label}</span> : null}
                    </Link>
                  );
                  return (
                    <li key={item.href}>
                      {collapsed ? (
                        <Tooltip content={item.label} side="right">
                          {link}
                        </Tooltip>
                      ) : (
                        link
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      </div>

      <div className="border-t border-line px-3 py-3">
        <ul className="space-y-0.5">
          {SECONDARY_NAV.map((item) => {
            const active = pathname.startsWith(item.href);
            const link = (
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition-colors duration-150",
                  collapsed && "justify-center px-0",
                  active ? "bg-paper-sunk text-ink" : "text-ink-soft hover:bg-paper-sunk hover:text-ink",
                )}
              >
                <item.icon className="size-4 shrink-0" aria-hidden />
                {!collapsed ? <span className="truncate">{item.label}</span> : null}
              </Link>
            );
            return (
              <li key={item.href}>
                {collapsed ? (
                  <Tooltip content={item.label} side="right">
                    {link}
                  </Tooltip>
                ) : (
                  link
                )}
              </li>
            );
          })}
        </ul>
        <Button
          variant="quiet"
          size="sm"
          onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className={cn("mt-2 w-full", collapsed && "px-0")}
        >
          {collapsed ? <ChevronsRight /> : <ChevronsLeft />}
          {!collapsed ? <span>Collapse</span> : null}
        </Button>
      </div>
    </nav>
  );
}

function OrgSwitcher({ name, plan }: { name: string; plan: string }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          className={cn(
            "flex w-full items-center gap-2.5 rounded-md border border-line bg-paper-sunk px-2.5 py-2 text-left",
            "transition-colors duration-150 hover:border-[var(--line-strong)]",
          )}
        >
          <span className="flex size-7 shrink-0 items-center justify-center rounded-sm bg-ink font-display text-sm text-[var(--paper-raised)]">
            {name.charAt(0)}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-medium text-ink">{name}</span>
            <span className="block truncate font-mono text-2xs uppercase tracking-[0.1em] text-ink-faint">
              {plan} plan
            </span>
          </span>
          <ChevronsUpDown className="size-3.5 shrink-0 text-ink-faint" aria-hidden />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        <DropdownMenuLabel>Organisations</DropdownMenuLabel>
        <DropdownMenuItem>
          <Check className="text-patina" />
          {name}
        </DropdownMenuItem>
        <DropdownMenuItem>
          <span className="size-4" />
          Thornfield Federal LLC
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href="/app/settings?tab=organization">Organisation settings</Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
