"use client";

import * as React from "react";
import Link from "next/link";
import { motion, useReducedMotion } from "motion/react";
import { format, parseISO } from "date-fns";
import { Download } from "lucide-react";

import { initials, pluralize } from "@/lib/utils";
import { dayKey, relative } from "@/lib/dates";
import { Button } from "@/components/ui/button";
import { PageHeader, Panel } from "@/components/ui/surface";
import { SearchField } from "@/components/ui/input";
import { Avatar, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/controls";
import { EmptyState } from "@/components/ui/feedback";
import { notify } from "@/components/ui/toaster";
import { useReportsStore } from "@/stores/workspace";
import { useAnalysesStore } from "@/stores/analyses";
import type { ActivityEntry } from "@/types";

export function ActivityView() {
  const reduce = useReducedMotion();
  const activity = useReportsStore((s) => s.activity);
  const analyses = useAnalysesStore((s) => s.analyses);

  const [query, setQuery] = React.useState("");
  const [actor, setActor] = React.useState("all");

  const actors = React.useMemo(() => [...new Set(activity.map((a) => a.actor))].sort(), [activity]);

  const filtered = activity.filter((entry) => {
    if (actor !== "all" && entry.actor !== actor) return false;
    if (!query.trim()) return true;
    return `${entry.actor} ${entry.action} ${entry.target ?? ""}`.toLowerCase().includes(query.toLowerCase());
  });

  const grouped = React.useMemo(() => {
    const map = new Map<string, ActivityEntry[]>();
    for (const entry of filtered) {
      const key = dayKey(entry.at);
      map.set(key, [...(map.get(key) ?? []), entry]);
    }
    return [...map.entries()];
  }, [filtered]);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        eyebrow="Workspace"
        title="Activity"
        description="Every change to every analysis, in the order it happened."
        actions={
          <Button
            variant="secondary"
            onClick={() =>
              notify.success("Audit trail exported.", {
                description: `${pluralize(activity.length, "entry", "entries")} as CSV.`,
              })
            }
          >
            <Download />
            Export trail
          </Button>
        }
      />

      <div className="flex flex-wrap items-center gap-3">
        <SearchField
          value={query}
          onValueChange={setQuery}
          placeholder="Search the trail…"
          className="w-full max-w-sm"
        />
        <Select value={actor} onValueChange={setActor}>
          <SelectTrigger className="w-48" aria-label="Filter by person">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Everyone</SelectItem>
            {actors.map((name) => (
              <SelectItem key={name} value={name}>
                {name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {grouped.length === 0 ? (
        <EmptyState
          title="Nothing recorded"
          description="Actions taken in the workspace — decisions, assignments, exports — are written here as they happen."
          action={
            <Button
              variant="secondary"
              onClick={() => {
                setQuery("");
                setActor("all");
              }}
            >
              Clear filters
            </Button>
          }
        />
      ) : (
        <div className="space-y-6">
          {grouped.map(([key, entries]) => (
            <section key={key}>
              <h2 className="sticky top-16 z-10 -mx-1 mb-3 bg-paper/92 px-1 py-1 text-sm font-medium text-ink backdrop-blur-sm">
                {format(parseISO(entries[0].at), "EEEE, MMMM d")}
              </h2>
              <Panel className="overflow-hidden">
                <ol className="relative">
                  {entries.map((entry, index) => {
                    const analysis = entry.analysisId
                      ? analyses.find((a) => a.id === entry.analysisId)
                      : undefined;
                    return (
                      <motion.li
                        key={entry.id}
                        initial={reduce ? false : { opacity: 0, x: -6 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{
                          delay: Math.min(index * 0.025, 0.2),
                          duration: 0.24,
                          ease: [0.32, 0.72, 0, 1],
                        }}
                        className="relative flex gap-3.5 border-b border-line px-5 py-3.5 last:border-b-0"
                      >
                        {index < entries.length - 1 ? (
                          <span
                            aria-hidden
                            className="absolute left-[2.05rem] top-10 h-[calc(100%-1.5rem)] w-px bg-line"
                          />
                        ) : null}
                        <Avatar
                          name={entry.actor}
                          size="xs"
                          tone={["patina", "slate", "ochre", "leaf", "seal"][initials(entry.actor).charCodeAt(0) % 5]}
                          className="relative z-10 mt-0.5"
                        />
                        <div className="min-w-0 flex-1">
                          <p className="text-sm leading-relaxed text-ink-soft">
                            <span className="font-medium text-ink">{entry.actor}</span> {entry.action}{" "}
                            {analysis ? (
                              <Link
                                href={`/app/analyses/${analysis.id}`}
                                className="text-ink underline decoration-[var(--line-strong)] underline-offset-4 transition-colors hover:decoration-current"
                              >
                                {entry.target ?? analysis.solicitationNumber}
                              </Link>
                            ) : entry.target ? (
                              <span className="text-ink">{entry.target}</span>
                            ) : null}
                          </p>
                          <p className="font-mono text-2xs text-ink-faint tabular">
                            {format(parseISO(entry.at), "HH:mm")} · {relative(entry.at)}
                          </p>
                        </div>
                      </motion.li>
                    );
                  })}
                </ol>
              </Panel>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
