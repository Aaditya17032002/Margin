"use client";

import * as React from "react";
import Link from "next/link";
import { format, isSameDay, parseISO, startOfMonth } from "date-fns";
import { Download } from "lucide-react";

import { cn, pluralize } from "@/lib/utils";
import { dayKey, formatInZone, urgency, zoneAbbr } from "@/lib/dates";
import { useNow } from "@/hooks/use-now";
import { collectDeadlines, type DeadlineRow } from "@/lib/derive";
import { Button } from "@/components/ui/button";
import { PageHeader, Panel, PanelHeader, Well } from "@/components/ui/surface";
import { Badge } from "@/components/ui/badge";
import { Segmented } from "@/components/ui/controls";
import { Calendar } from "@/components/ui/datetime";
import { EmptyState } from "@/components/ui/feedback";
import { notify } from "@/components/ui/toaster";
import { DeadlineCountdown } from "@/components/domain/deadline";
import { CitationMeta } from "@/components/domain/primitives";
import { useAnalysesStore } from "@/stores/analyses";

const KIND_COPY: Record<
  DeadlineRow["kind"],
  { label: string; tone: "seal" | "ochre" | "leaf" | "slate" | "neutral" | "patina" }
> = {
  "questions-due": { label: "Questions due", tone: "ochre" },
  "proposal-due": { label: "Proposal due", tone: "seal" },
  "site-visit": { label: "Site visit", tone: "slate" },
  award: { label: "Award", tone: "leaf" },
  amendment: { label: "Amendment", tone: "neutral" },
  start: { label: "Period of performance", tone: "patina" },
};

const MARKER_TONE: Record<DeadlineRow["kind"], "seal" | "ochre" | "leaf" | "slate"> = {
  "questions-due": "ochre",
  "proposal-due": "seal",
  "site-visit": "slate",
  award: "leaf",
  amendment: "slate",
  start: "leaf",
};

export function DeadlinesView() {
  const analyses = useAnalysesStore((s) => s.analyses);
  const now = useNow(60_000);
  const [month, setMonth] = React.useState(() => startOfMonth(new Date()));
  const [selected, setSelected] = React.useState<Date | null>(null);
  const [scope, setScope] = React.useState<"upcoming" | "all">("upcoming");
  const [kind, setKind] = React.useState<DeadlineRow["kind"] | "all">("all");

  const all = React.useMemo(() => collectDeadlines(analyses), [analyses]);

  const markers = React.useMemo(() => {
    const map: Record<string, { tone: "seal" | "ochre" | "leaf" | "slate"; count: number }> = {};
    for (const row of all) {
      const key = dayKey(row.at);
      const existing = map[key];
      // A proposal deadline outranks anything else sharing its square.
      const tone = MARKER_TONE[row.kind];
      map[key] = {
        tone: existing?.tone === "seal" ? "seal" : tone,
        count: (existing?.count ?? 0) + 1,
      };
    }
    return map;
  }, [all]);

  const listed = React.useMemo(() => {
    return all.filter((row) => {
      if (kind !== "all" && row.kind !== kind) return false;
      if (selected) return isSameDay(parseISO(row.at), selected);
      // Before the clock is available every date counts as upcoming, which is
      // the right answer for the server pass and corrects itself on mount.
      if (scope === "upcoming" && now > 0) return parseISO(row.at).getTime() >= now;
      return true;
    });
  }, [all, kind, scope, selected, now]);

  const grouped = React.useMemo(() => {
    const map = new Map<string, DeadlineRow[]>();
    for (const row of listed) {
      const key = dayKey(row.at);
      map.set(key, [...(map.get(key) ?? []), row]);
    }
    return [...map.entries()];
  }, [listed]);

  const nextCritical = all.find((row) => urgency(row.at, now) === "critical" && row.kind === "proposal-due");

  return (
    <div className="mx-auto max-w-[76rem] space-y-6">
      <PageHeader
        eyebrow="Calendar"
        title="Deadlines"
        description="Every date the documents named, in the time zone the agency wrote it in."
        actions={
          <Button
            variant="secondary"
            onClick={() =>
              notify.success("Calendar exported.", {
                description: `${pluralize(all.length, "date")} as an .ics feed.`,
                action: { label: "Open in Outlook", onClick: () => notify.info("Opening Outlook…") },
              })
            }
          >
            <Download />
            Export .ics
          </Button>
        }
      />

      {nextCritical ? (
        <Well className="border-l-[3px] border-l-seal bg-[var(--seal-tint)]">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="min-w-0">
              <p className="text-sm font-medium text-ink">{nextCritical.analysisTitle}</p>
              <p className="text-xs text-ink-soft">
                {nextCritical.label} · {nextCritical.solicitationNumber}
              </p>
            </div>
            <DeadlineCountdown at={nextCritical.at} timezone={nextCritical.timezone} size="md" />
          </div>
        </Well>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[20rem_1fr]">
        <div className="space-y-4 lg:sticky lg:top-20 lg:self-start">
          <Panel className="p-4">
            <Calendar
              month={month}
              onMonthChange={setMonth}
              selected={selected}
              onSelect={(day) => setSelected((prev) => (prev && isSameDay(prev, day) ? null : day))}
              markers={markers}
            />
            {selected ? (
              <div className="mt-3 flex items-center justify-between border-t border-line pt-3">
                <p className="text-xs text-ink-soft">Showing {format(selected, "MMMM d")}</p>
                <Button variant="quiet" size="sm" onClick={() => setSelected(null)}>
                  Clear
                </Button>
              </div>
            ) : null}
          </Panel>

          <Panel className="p-4">
            <p className="eyebrow mb-3">Legend</p>
            <ul className="space-y-2">
              {(Object.keys(KIND_COPY) as DeadlineRow["kind"][]).map((k) => (
                <li key={k}>
                  <button
                    type="button"
                    onClick={() => setKind((prev) => (prev === k ? "all" : k))}
                    aria-pressed={kind === k}
                    className={cn(
                      "flex w-full items-center gap-2.5 rounded-sm px-1.5 py-1 text-left text-sm transition-colors duration-150",
                      kind === k ? "bg-paper-sunk text-ink" : "text-ink-soft hover:bg-paper-sunk hover:text-ink",
                    )}
                  >
                    <span
                      aria-hidden
                      className="size-1.5 shrink-0 rounded-full"
                      style={{ backgroundColor: `var(--${MARKER_TONE[k]})` }}
                    />
                    {KIND_COPY[k].label}
                    <span className="ml-auto font-mono text-2xs text-ink-faint tabular">
                      {all.filter((d) => d.kind === k).length}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </Panel>
        </div>

        <Panel>
          <PanelHeader
            title={selected ? format(selected, "EEEE, MMMM d") : scope === "upcoming" ? "Upcoming" : "Every date"}
            description={`${pluralize(listed.length, "date")} across ${pluralize(
              new Set(listed.map((d) => d.analysisId)).size,
              "analysis",
              "analyses",
            )}`}
            actions={
              selected ? null : (
                <Segmented
                  ariaLabel="Date range"
                  value={scope}
                  onValueChange={(v) => setScope(v as "upcoming" | "all")}
                  options={[
                    { value: "upcoming", label: "Upcoming" },
                    { value: "all", label: "All" },
                  ]}
                />
              )
            }
          />

          {grouped.length === 0 ? (
            <div className="p-5">
              <EmptyState
                title="Nothing on this date"
                description="Pick another day, or clear the filter to see the whole calendar."
                action={
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setSelected(null);
                      setKind("all");
                    }}
                  >
                    Clear filters
                  </Button>
                }
              />
            </div>
          ) : (
            <ul className="divide-y divide-line">
              {grouped.map(([key, rows]) => (
                <li key={key}>
                  <div className="sticky top-14 z-10 flex items-baseline gap-3 border-b border-line bg-paper-raised/92 px-5 py-2 backdrop-blur-sm">
                    <span className="font-mono text-2xs uppercase tracking-[0.1em] text-ink-faint">
                      {format(parseISO(rows[0].at), "EEE")}
                    </span>
                    <span className="text-sm text-ink">{format(parseISO(rows[0].at), "MMMM d, yyyy")}</span>
                  </div>
                  <ul className="divide-y divide-line">
                    {rows.map((row) => (
                      <DeadlineRowItem key={`${row.analysisId}-${row.id}`} row={row} now={now} />
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </div>
  );
}

function DeadlineRowItem({ row, now }: { row: DeadlineRow; now: number }) {
  const state = urgency(row.at, now);
  const copy = KIND_COPY[row.kind];

  return (
    <li
      className={cn(
        "flex flex-wrap items-start justify-between gap-x-6 gap-y-3 px-5 py-4",
        state === "past" && "opacity-60",
      )}
    >
      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={copy.tone}>{copy.label}</Badge>
          <span className="font-mono text-2xs text-ink-faint">{row.solicitationNumber}</span>
        </div>
        <Link
          href={`/app/analyses/${row.analysisId}`}
          className="block truncate text-sm text-ink underline-offset-4 hover:underline"
        >
          {row.analysisTitle}
        </Link>
        <p className="text-xs text-ink-faint">
          {row.label} · {formatInZone(row.at, row.timezone, "time")} {zoneAbbr(row.timezone)}
        </p>
        {row.citation ? (
          <CitationMeta
            citation={row.citation}
            analysisId={row.analysisId}
            label={row.label}
            origin="Deadlines"
            clamp={2}
          />
        ) : null}
      </div>
      <div className="shrink-0">
        <DeadlineCountdown at={row.at} timezone={row.timezone} size="sm" showZone={false} />
      </div>
    </li>
  );
}
