"use client";

import * as React from "react";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";
import { CommandPalette } from "./command-palette";
import { GlobalShortcuts, ShortcutsDialog } from "./shortcuts";
import { ImportPicker } from "./import-picker";
import { MarginRail } from "./margin-rail";
import { Coachmarks } from "./coachmarks";
import { useWorkspaceData } from "@/hooks/use-workspace-data";
import { usePrefsStore } from "@/stores/workspace";
import { useUIStore } from "@/stores/ui";

/**
 * The workspace frame: navigation on the left, the working surface in the
 * middle, and the Margin on the right. The rail is mounted for every route so
 * a citation is always one hover away, whichever screen you are on.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const density = usePrefsStore((s) => s.density);
  const closeRail = useUIStore((s) => s.closeRail);

  useWorkspaceData();

  // A source that belonged to the previous screen has no business surviving it.
  React.useEffect(() => {
    closeRail();
  }, [pathname, closeRail]);

  const bare = pathname.endsWith("/run");
  // The workspace is the one place where every panel is citation-bearing, so the
  // Margin holds its column there whether or not anything is being pointed at.
  const railHint = /^\/app\/analyses\/[^/]+$/.test(pathname);

  return (
    <div className="flex min-h-dvh bg-paper" data-density={density}>
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <div className="flex min-w-0 flex-1">
          <main
            id="main"
            className={cn(
              "relative z-10 min-w-0 flex-1",
              bare ? "" : density === "compact" ? "px-5 py-5 lg:px-7" : "px-5 py-7 lg:px-9 lg:py-9",
            )}
          >
            {children}
          </main>
          <MarginRail hint={railHint && !bare} />
        </div>
      </div>

      <CommandPalette />
      <ShortcutsDialog />
      <ImportPicker />
      <GlobalShortcuts />
      <Coachmarks />
    </div>
  );
}
