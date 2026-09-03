"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { Dialog, DialogContent } from "@/components/ui/overlay";
import { Kbd } from "@/components/ui/surface";
import { Switch } from "@/components/ui/controls";
import { usePrefsStore } from "@/stores/workspace";
import { useUIStore } from "@/stores/ui";

export const SHORTCUT_GROUPS = [
  {
    group: "Anywhere",
    items: [
      { keys: ["⌘", "K"], label: "Open the command palette" },
      { keys: ["?"], label: "Show this reference" },
      { keys: ["G", "then", "D"], label: "Go to the dashboard" },
      { keys: ["G", "then", "A"], label: "Go to analyses" },
      { keys: ["G", "then", "M"], label: "Go to the compliance matrix" },
      { keys: ["N"], label: "Start a new analysis" },
    ],
  },
  {
    group: "The Margin",
    items: [
      { keys: ["→"], label: "Move focus into the rail" },
      { keys: ["Esc"], label: "Release the rail" },
      { keys: ["P"], label: "Pin or unpin the current source" },
    ],
  },
  {
    group: "Workspace",
    items: [
      { keys: ["["], label: "Previous section" },
      { keys: ["]"], label: "Next section" },
      { keys: ["V"], label: "Verify the focused finding" },
      { keys: ["E"], label: "Export the current analysis" },
    ],
  },
  {
    group: "Tables",
    items: [
      { keys: ["/"], label: "Focus the filter" },
      { keys: ["X"], label: "Select the focused row" },
      { keys: ["Enter"], label: "Open the focused row" },
    ],
  },
];

export function ShortcutsDialog() {
  const open = useUIStore((s) => s.shortcutsOpen);
  const setOpen = useUIStore((s) => s.setShortcutsOpen);
  const enabled = usePrefsStore((s) => s.shortcutsEnabled);
  const toggle = usePrefsStore((s) => s.toggleShortcuts);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent
        size="lg"
        title="Keyboard shortcuts"
        description="Every flow in Margin can be run without a mouse."
        footer={
          <label className="mr-auto flex items-center gap-3 text-sm text-ink-soft">
            <Switch checked={enabled} onCheckedChange={toggle} />
            Shortcuts enabled
          </label>
        }
      >
        <div className="grid gap-x-10 gap-y-6 sm:grid-cols-2">
          {SHORTCUT_GROUPS.map((group) => (
            <div key={group.group}>
              <p className="eyebrow pb-2">{group.group}</p>
              <dl className="space-y-0">
                {group.items.map((item) => (
                  <div
                    key={item.label}
                    className="flex items-center justify-between gap-4 border-b border-line py-2 last:border-b-0"
                  >
                    <dt className="text-sm text-ink-soft">{item.label}</dt>
                    <dd className="flex shrink-0 items-center gap-1">
                      {item.keys.map((key, i) =>
                        key === "then" ? (
                          <span key={i} className="px-0.5 text-2xs text-ink-faint">
                            then
                          </span>
                        ) : (
                          <Kbd key={i}>{key}</Kbd>
                        ),
                      )}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}

/** Global chords. Deliberately inert while typing, and switchable off in prefs. */
export function GlobalShortcuts() {
  const router = useRouter();
  const enabled = usePrefsStore((s) => s.shortcutsEnabled);
  const setShortcutsOpen = useUIStore((s) => s.setShortcutsOpen);
  const setPinned = useUIStore((s) => s.setPinned);
  const pendingG = React.useRef(false);

  React.useEffect(() => {
    if (!enabled) return;

    function onKey(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.isContentEditable ||
        event.metaKey ||
        event.ctrlKey ||
        event.altKey
      ) {
        return;
      }

      const key = event.key.toLowerCase();

      if (pendingG.current) {
        pendingG.current = false;
        const routes: Record<string, string> = {
          d: "/app",
          a: "/app/analyses",
          m: "/app/matrix",
          t: "/app/team",
          s: "/app/settings",
          k: "/app/knowledge",
          r: "/app/reports",
          i: "/app/integrations",
        };
        if (routes[key]) {
          event.preventDefault();
          router.push(routes[key]);
          return;
        }
      }

      if (key === "g") {
        pendingG.current = true;
        window.setTimeout(() => {
          pendingG.current = false;
        }, 1400);
        return;
      }

      if (event.key === "?") {
        event.preventDefault();
        setShortcutsOpen(true);
      }
      if (key === "n") {
        event.preventDefault();
        router.push("/app/analyses/new");
      }
      if (key === "p" && useUIStore.getState().source) {
        event.preventDefault();
        setPinned(!useUIStore.getState().pinned);
      }
    }

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [enabled, router, setPinned, setShortcutsOpen]);

  return null;
}
