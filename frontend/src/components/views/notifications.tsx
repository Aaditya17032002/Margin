"use client";

import * as React from "react";
import Link from "next/link";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import {
  AlertTriangle,
  AtSign,
  BellOff,
  CalendarClock,
  CheckCheck,
  FileDown,
  GitCompare,
  Info,
  Trash2,
} from "lucide-react";

import { cn, pluralize } from "@/lib/utils";
import { relative } from "@/lib/dates";
import { Button } from "@/components/ui/button";
import { PageHeader, Panel } from "@/components/ui/surface";
import { Segmented } from "@/components/ui/controls";
import { ConfirmDialog } from "@/components/ui/overlay";
import { EmptyState } from "@/components/ui/feedback";
import { notify } from "@/components/ui/toaster";
import { useNotificationsStore } from "@/stores/workspace";
import type { AppNotification } from "@/types";

const KIND: Record<
  AppNotification["kind"],
  { icon: typeof Info; label: string; tone: string }
> = {
  deadline: { icon: CalendarClock, label: "Deadline", tone: "text-seal" },
  review: { icon: AlertTriangle, label: "Review", tone: "text-ochre" },
  mention: { icon: AtSign, label: "Mention", tone: "text-patina" },
  system: { icon: Info, label: "System", tone: "text-slate" },
  export: { icon: FileDown, label: "Export", tone: "text-leaf" },
  amendment: { icon: GitCompare, label: "Amendment", tone: "text-ochre" },
};

export function NotificationsView() {
  const reduce = useReducedMotion();
  const items = useNotificationsStore((s) => s.items);
  const markRead = useNotificationsStore((s) => s.markRead);
  const markAllRead = useNotificationsStore((s) => s.markAllRead);
  const restoreUnread = useNotificationsStore((s) => s.restoreUnread);
  const remove = useNotificationsStore((s) => s.remove);
  const restore = useNotificationsStore((s) => s.restore);
  const clearAll = useNotificationsStore((s) => s.clearAll);
  const reload = useNotificationsStore((s) => s.load);

  const [filter, setFilter] = React.useState<string>("all");
  const [confirmClear, setConfirmClear] = React.useState(false);

  const unread = items.filter((n) => !n.read).length;
  const filtered = items.filter((item) => {
    if (filter === "all") return true;
    if (filter === "unread") return !item.read;
    return item.kind === filter;
  });

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        eyebrow="Workspace"
        title="Notifications"
        description={unread ? `${pluralize(unread, "unread notice")}.` : "Everything here has been read."}
        actions={
          <>
            <Button
              variant="secondary"
              disabled={unread === 0}
              onClick={() => {
                const changed = markAllRead();
                notify.success("All marked as read.", {
                  undo: changed.length ? () => restoreUnread(changed) : undefined,
                });
              }}
            >
              <CheckCheck />
              Mark all read
            </Button>
            <Button variant="quiet" disabled={items.length === 0} onClick={() => setConfirmClear(true)}>
              <Trash2 />
              Clear
            </Button>
          </>
        }
      />

      <Segmented
        ariaLabel="Filter notifications"
        value={filter}
        onValueChange={setFilter}
        options={[
          { value: "all", label: "All" },
          { value: "unread", label: `Unread${unread ? ` (${unread})` : ""}` },
          { value: "deadline", label: "Deadlines" },
          { value: "review", label: "Review" },
          { value: "mention", label: "Mentions" },
          { value: "amendment", label: "Amendments" },
        ]}
      />

      {filtered.length === 0 ? (
        <EmptyState
          illustration={<BellOff className="size-7 text-patina" aria-hidden />}
          title={items.length === 0 ? "Nothing waiting" : "Nothing in this filter"}
          description={
            items.length === 0
              ? "Deadlines, low-confidence findings, and amendments will arrive here as they happen."
              : "Switch filters to see the rest."
          }
          action={
            items.length === 0 ? (
              <Button variant="secondary" onClick={() => void reload({ force: true })}>
                Check again
              </Button>
            ) : (
              <Button variant="secondary" onClick={() => setFilter("all")}>
                Show everything
              </Button>
            )
          }
        />
      ) : (
        <Panel className="overflow-hidden">
          <ul className="divide-y divide-line">
            <AnimatePresence initial={false}>
              {filtered.map((item) => {
                const meta = KIND[item.kind];
                const Icon = meta.icon;
                return (
                  <motion.li
                    key={item.id}
                    layout={!reduce}
                    initial={reduce ? false : { opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={reduce ? { opacity: 0 } : { opacity: 0, x: -12 }}
                    transition={{ duration: 0.2, ease: [0.32, 0.72, 0, 1] }}
                    className={cn("group relative", !item.read && "bg-patina-tint/45")}
                  >
                    {!item.read ? (
                      <span aria-hidden className="absolute inset-y-0 left-0 w-[3px] bg-patina" />
                    ) : null}
                    <div className="flex items-start gap-3.5 px-5 py-4">
                      <span className={cn("mt-0.5 shrink-0", meta.tone)}>
                        <Icon className="size-4" aria-hidden />
                      </span>
                      <div className="min-w-0 flex-1 space-y-1">
                        <div className="flex flex-wrap items-baseline gap-x-2.5">
                          <p className={cn("text-sm", item.read ? "text-ink-soft" : "font-medium text-ink")}>
                            {item.title}
                          </p>
                          <span className="font-mono text-2xs text-ink-faint">{relative(item.at)}</span>
                        </div>
                        <p className="text-sm leading-relaxed text-ink-soft">{item.body}</p>
                        {item.href ? (
                          <Link
                            href={item.href}
                            onClick={() => markRead(item.id)}
                            className="inline-block pt-0.5 text-xs font-medium text-patina underline-offset-4 hover:underline"
                          >
                            Open {meta.label.toLowerCase()}
                          </Link>
                        ) : null}
                      </div>
                      <div className="flex shrink-0 items-center gap-1 opacity-0 transition-opacity duration-150 focus-within:opacity-100 group-hover:opacity-100">
                        <Button
                          variant="quiet"
                          size="iconSm"
                          aria-label={item.read ? "Mark as unread" : "Mark as read"}
                          onClick={() => markRead(item.id, !item.read)}
                        >
                          <CheckCheck />
                        </Button>
                        <Button
                          variant="quiet"
                          size="iconSm"
                          aria-label="Dismiss notification"
                          onClick={() => {
                            const removed = remove(item.id);
                            if (removed) {
                              notify.success("Notification dismissed.", { undo: () => restore(removed) });
                            }
                          }}
                        >
                          <Trash2 />
                        </Button>
                      </div>
                    </div>
                  </motion.li>
                );
              })}
            </AnimatePresence>
          </ul>
        </Panel>
      )}

      <ConfirmDialog
        open={confirmClear}
        onOpenChange={setConfirmClear}
        title="Clear every notification?"
        destructive
        confirmLabel="Clear all"
        description="The list empties. You will have a moment to undo."
        onConfirm={() => {
          const all = clearAll();
          setConfirmClear(false);
          notify.success("Notifications cleared.", {
            undo: () => all.forEach((n) => restore(n)),
          });
        }}
      />
    </div>
  );
}
