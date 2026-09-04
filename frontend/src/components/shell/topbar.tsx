"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Bell, Command, LogOut, Menu, Search, Settings, User, Keyboard } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/ui/surface";
import { Avatar } from "@/components/ui/controls";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  Tooltip,
} from "@/components/ui/overlay";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Wordmark } from "@/components/domain/marks";
import { PRIMARY_NAV, SECONDARY_NAV, ALL_NAV } from "./navigation";
import { useSessionStore } from "@/stores/session";
import { useNotificationsStore, selectUnreadCount } from "@/stores/workspace";
import { useUIStore } from "@/stores/ui";
import { useAnalysesStore } from "@/stores/analyses";
import { notify } from "@/components/ui/toaster";

export function Topbar() {
  const pathname = usePathname();
  const router = useRouter();
  const user = useSessionStore((s) => s.user);
  const logout = useSessionStore((s) => s.logout);
  const unread = useNotificationsStore(selectUnreadCount);
  const setCommandOpen = useUIStore((s) => s.setCommandOpen);
  const setShortcutsOpen = useUIStore((s) => s.setShortcutsOpen);
  const [mobileNav, setMobileNav] = React.useState(false);
  const crumbs = useBreadcrumbs(pathname);

  return (
    <header className="z-40 flex h-16 shrink-0 items-center gap-3 border-b border-line bg-paper-raised px-4 lg:px-6">
      <Button
        variant="ghost"
        size="icon"
        className="lg:hidden"
        aria-label="Open navigation"
        onClick={() => setMobileNav(true)}
      >
        <Menu />
      </Button>

      <div className="lg:hidden">
        <Wordmark showText={false} />
      </div>

      <nav aria-label="Breadcrumb" className="hidden min-w-0 flex-1 md:block">
        <ol className="flex items-center gap-1.5 text-sm">
          {crumbs.map((crumb, i) => (
            <li key={crumb.href} className="flex min-w-0 items-center gap-1.5">
              {i > 0 ? (
                <span aria-hidden className="text-ink-faint/70">
                  /
                </span>
              ) : null}
              {i === crumbs.length - 1 ? (
                <span className="truncate font-medium text-ink" aria-current="page">
                  {crumb.label}
                </span>
              ) : (
                <Link
                  href={crumb.href}
                  className="truncate text-ink-faint transition-colors duration-150 hover:text-ink"
                >
                  {crumb.label}
                </Link>
              )}
            </li>
          ))}
        </ol>
      </nav>

      <div className="ml-auto flex items-center gap-1.5">
        <button
          type="button"
          onClick={() => setCommandOpen(true)}
          className={cn(
            "hidden h-9 min-w-56 items-center gap-2 rounded-md border border-line-strong bg-paper-sunk px-3 text-left text-sm text-ink-faint sm:flex",
            "transition-colors duration-150 hover:border-[var(--ink-faint)] hover:text-ink-soft",
          )}
          data-coach="palette"
        >
          <Search className="size-4 shrink-0" aria-hidden />
          <span className="flex-1">Search or jump to…</span>
          <Kbd>
            <Command className="size-2.5" aria-hidden />K
          </Kbd>
        </button>

        <Tooltip content="Command palette" shortcut="⌘K">
          <Button variant="ghost" size="icon" className="sm:hidden" aria-label="Open command palette" onClick={() => setCommandOpen(true)}>
            <Search />
          </Button>
        </Tooltip>

        <Tooltip content="Keyboard shortcuts" shortcut="?">
          <Button variant="ghost" size="icon" aria-label="Keyboard shortcuts" onClick={() => setShortcutsOpen(true)}>
            <Keyboard />
          </Button>
        </Tooltip>

        <Tooltip content={unread > 0 ? `${unread} unread` : "Notifications"}>
          <Button asChild variant="ghost" size="icon" className="relative">
            <Link href="/app/notifications" aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`}>
              <Bell />
              {unread > 0 ? (
                <span
                  aria-hidden
                  className="absolute right-1.5 top-1.5 size-2 rounded-full bg-seal ring-2 ring-[var(--paper-raised)]"
                />
              ) : null}
            </Link>
          </Button>
        </Tooltip>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              className="ml-1 rounded-full transition-opacity duration-150 hover:opacity-85"
              aria-label="Account menu"
            >
              <Avatar name={user?.name ?? ""} tone="patina" size="sm" presence="online" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-60">
            <div className="px-2.5 py-2">
              <p className="truncate text-sm font-medium text-ink">{user?.name}</p>
              <p className="truncate text-xs text-ink-faint">{user?.email}</p>
            </div>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link href="/app/profile">
                <User />
                Profile
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/app/settings">
                <Settings />
                Settings
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => setShortcutsOpen(true)}>
              <Keyboard />
              Keyboard shortcuts
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuLabel>Session</DropdownMenuLabel>
            <DropdownMenuItem
              destructive
              onSelect={() => {
                logout();
                notify.success("Signed out.", { description: "Your work stays on this device." });
                router.push("/login");
              }}
            >
              <LogOut />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <Sheet open={mobileNav} onOpenChange={setMobileNav} direction="left">
        <SheetContent direction="left" title="Navigate" description="Everything in the workspace">
          <div className="space-y-6">
            {PRIMARY_NAV.map((group) => (
              <div key={group.group}>
                <p className="pb-1.5 font-mono text-2xs uppercase tracking-[0.14em] text-ink-faint">
                  {group.group}
                </p>
                <ul className="space-y-0.5">
                  {group.items.map((item) => (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        onClick={() => setMobileNav(false)}
                        className="flex items-center gap-3 rounded-md px-2.5 py-2.5 text-sm text-ink-soft hover:bg-paper-sunk hover:text-ink"
                      >
                        <item.icon className="size-4" aria-hidden />
                        {item.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
            <div>
              <p className="pb-1.5 font-mono text-2xs uppercase tracking-[0.14em] text-ink-faint">Account</p>
              <ul className="space-y-0.5">
                {SECONDARY_NAV.map((item) => (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      onClick={() => setMobileNav(false)}
                      className="flex items-center gap-3 rounded-md px-2.5 py-2.5 text-sm text-ink-soft hover:bg-paper-sunk hover:text-ink"
                    >
                      <item.icon className="size-4" aria-hidden />
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </header>
  );
}

function useBreadcrumbs(pathname: string) {
  const analyses = useAnalysesStore((s) => s.analyses);
  return React.useMemo(() => {
    const segments = pathname.split("/").filter(Boolean);
    const crumbs: { href: string; label: string }[] = [{ href: "/app", label: "Margin" }];
    let href = "";
    segments.forEach((segment, index) => {
      href += `/${segment}`;
      if (segment === "app") return;
      const nav = ALL_NAV.find((n) => n.href === href);
      if (nav) {
        crumbs.push({ href, label: nav.label });
        return;
      }
      const analysis = analyses.find((a) => a.id === segment);
      if (analysis) {
        crumbs.push({ href, label: analysis.solicitationNumber });
        return;
      }
      if (segment === "new") crumbs.push({ href, label: "New analysis" });
      else if (segment === "run") crumbs.push({ href, label: "Reading room" });
      else if (index === segments.length - 1)
        crumbs.push({ href, label: segment.charAt(0).toUpperCase() + segment.slice(1) });
    });
    return crumbs;
  }, [pathname, analyses]);
}
