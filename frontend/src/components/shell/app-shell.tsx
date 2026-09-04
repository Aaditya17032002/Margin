"use client";

import * as React from "react";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";
import { CommandPalette } from "./command-palette";
import { GlobalShortcuts, ShortcutsDialog } from "./shortcuts";
import { ImportPicker } from "./import-picker";
import { Coachmarks } from "./coachmarks";
import { useWorkspaceData } from "@/hooks/use-workspace-data";
import { usePrefsStore } from "@/stores/workspace";
import { useUIStore } from "@/stores/ui";

/**
 * The workspace frame — a fixed viewport, not a long document.
 *
 * The window itself never scrolls. Navigation and the top bar hold their
 * position, and whatever is on screen owns its own overflow. That is the
 * difference between a tool you work in all day and a page you read once:
 * reaching the last row of a long table should not first scroll away the
 * controls you need to act on it.
 *
 * `overflow-hidden` and `min-h-0` are load-bearing. A grid track will not
 * shrink below its content without them, and the moment one region refuses to
 * shrink the whole window starts scrolling again.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const density = usePrefsStore((s) => s.density);
  const closeRail = useUIStore((s) => s.closeRail);

  useWorkspaceData();

  // The workspace owns the viewport: the window itself must not scroll, only
  // the regions inside it. Declared on <html> rather than in a class so the
  // marketing pages, which do scroll, are untouched.
  React.useEffect(() => {
    document.documentElement.dataset.shell = "app";
    return () => {
      delete document.documentElement.dataset.shell;
    };
  }, []);

  // A source that belonged to the previous screen has no business surviving it.
  React.useEffect(() => {
    closeRail();
  }, [pathname, closeRail]);

  return (
    <div
      className="flex h-dvh overflow-hidden bg-paper"
      data-density={density}
    >
      <Sidebar />
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <Topbar />
        {/* A flex column so whatever a screen renders can claim the
            remaining height with `flex-1` and scroll inside it. A percentage
            height here would depend on the parent resolving one first. */}
        <main id="main" className={cn("flex min-h-0 flex-1 flex-col overflow-hidden")}>
          {children}
        </main>
      </div>

      <CommandPalette />
      <ShortcutsDialog />
      <ImportPicker />
      <GlobalShortcuts />
      <Coachmarks />
    </div>
  );
}
