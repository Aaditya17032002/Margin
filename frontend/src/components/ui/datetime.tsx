"use client";

import * as React from "react";
import {
  addMonths,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  isSameMonth,
  parseISO,
  startOfMonth,
  startOfWeek,
  subMonths,
} from "date-fns";
import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react";

import { cn } from "@/lib/utils";
import { formatInZone, zoneAbbr } from "@/lib/dates";
import { Button } from "./button";
import { Popover, PopoverContent, PopoverTrigger } from "./overlay";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./controls";
import { fieldSurface } from "./input";

const ZONES = [
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Phoenix",
  "America/Los_Angeles",
  "UTC",
];

export function MonthGrid({
  month,
  selected,
  onSelect,
  markers,
  className,
}: {
  month: Date;
  selected?: Date | null;
  onSelect?: (date: Date) => void;
  markers?: Record<string, { tone: "seal" | "ochre" | "leaf" | "slate"; count: number }>;
  className?: string;
}) {
  const days = eachDayOfInterval({
    start: startOfWeek(startOfMonth(month), { weekStartsOn: 1 }),
    end: endOfWeek(endOfMonth(month), { weekStartsOn: 1 }),
  });
  const today = new Date();

  return (
    <div className={cn("space-y-1", className)}>
      <div className="grid grid-cols-7 gap-1">
        {["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"].map((label) => (
          <div key={label} className="pb-1 text-center font-mono text-2xs uppercase tracking-[0.1em] text-ink-faint">
            {label}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {days.map((day) => {
          const key = format(day, "yyyy-MM-dd");
          const marker = markers?.[key];
          const outside = !isSameMonth(day, month);
          const isToday = isSameDay(day, today);
          const isSelected = selected ? isSameDay(day, selected) : false;
          return (
            <button
              key={key}
              type="button"
              onClick={() => onSelect?.(day)}
              aria-current={isToday ? "date" : undefined}
              aria-pressed={isSelected}
              className={cn(
                "relative flex aspect-square flex-col items-center justify-center rounded-sm text-sm tabular",
                "transition-colors duration-150 ease-[cubic-bezier(0.32,0.72,0,1)]",
                outside ? "text-ink-faint/55" : "text-ink-soft",
                "hover:bg-paper-sunk hover:text-ink",
                isToday && "font-medium text-ink ring-1 ring-inset ring-[var(--line-strong)]",
                isSelected && "bg-patina text-[var(--patina-ink)] hover:bg-patina-hover hover:text-[var(--patina-ink)]",
              )}
            >
              {format(day, "d")}
              {marker ? (
                <span
                  aria-hidden
                  className="absolute bottom-1 size-1 rounded-full"
                  style={{
                    backgroundColor: isSelected ? "var(--patina-ink)" : `var(--${marker.tone})`,
                  }}
                />
              ) : null}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function Calendar({
  selected,
  onSelect,
  markers,
  month: controlledMonth,
  onMonthChange,
  className,
}: {
  selected?: Date | null;
  onSelect?: (date: Date) => void;
  markers?: Record<string, { tone: "seal" | "ochre" | "leaf" | "slate"; count: number }>;
  month?: Date;
  onMonthChange?: (month: Date) => void;
  className?: string;
}) {
  const [internal, setInternal] = React.useState(() => startOfMonth(selected ?? new Date()));
  const month = controlledMonth ?? internal;
  const setMonth = (next: Date) => {
    setInternal(next);
    onMonthChange?.(next);
  };

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex items-center justify-between">
        <h3 className="text-base text-ink">{format(month, "MMMM yyyy")}</h3>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="iconSm" aria-label="Previous month" onClick={() => setMonth(subMonths(month, 1))}>
            <ChevronLeft />
          </Button>
          <Button variant="ghost" size="iconSm" aria-label="Next month" onClick={() => setMonth(addMonths(month, 1))}>
            <ChevronRight />
          </Button>
        </div>
      </div>
      <MonthGrid month={month} selected={selected} onSelect={onSelect} markers={markers} />
    </div>
  );
}

/**
 * Deadlines in this domain are always somebody else's local time, so the zone
 * is part of the control rather than a footnote beneath it.
 */
export function DateTimePicker({
  value,
  timezone,
  onChange,
  onTimezoneChange,
  label,
  className,
}: {
  value: string | null;
  timezone: string;
  onChange: (iso: string) => void;
  onTimezoneChange: (zone: string) => void;
  label?: string;
  className?: string;
}) {
  const [open, setOpen] = React.useState(false);
  const date = value ? parseISO(value) : null;
  const time = date ? format(date, "HH:mm") : "17:00";

  function applyDate(next: Date) {
    const [h, m] = time.split(":").map(Number);
    const merged = new Date(next);
    merged.setHours(h, m, 0, 0);
    onChange(merged.toISOString());
  }

  function applyTime(nextTime: string) {
    const [h, m] = nextTime.split(":").map(Number);
    const base = date ? new Date(date) : new Date();
    base.setHours(h, m, 0, 0);
    onChange(base.toISOString());
  }

  return (
    <div className={cn("space-y-1.5", className)}>
      {label ? <p className="text-sm font-medium text-ink">{label}</p> : null}
      <div className="flex flex-wrap items-center gap-2">
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <button
              type="button"
              className={cn(fieldSurface, "flex h-9 min-w-44 items-center gap-2 px-3 text-left text-sm")}
            >
              <CalendarDays className="size-4 shrink-0 text-ink-faint" aria-hidden />
              <span className={cn(!date && "text-ink-faint")}>
                {date ? formatInZone(date.toISOString(), timezone, "date") : "Pick a date"}
              </span>
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-80">
            <Calendar
              selected={date}
              onSelect={(next) => {
                applyDate(next);
                setOpen(false);
              }}
            />
          </PopoverContent>
        </Popover>

        <input
          type="time"
          value={time}
          onChange={(e) => applyTime(e.target.value)}
          aria-label="Time"
          className={cn(fieldSurface, "h-9 w-28 px-3 text-sm tabular")}
        />

        <Select value={timezone} onValueChange={onTimezoneChange}>
          <SelectTrigger className="h-9 w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {ZONES.map((zone) => (
              <SelectItem key={zone} value={zone}>
                {zone.replace("_", " ")} · {zoneAbbr(zone)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {date ? (
        <p className="font-mono text-2xs text-ink-faint">
          {formatInZone(date.toISOString(), timezone)} {zoneAbbr(timezone)}
        </p>
      ) : null}
    </div>
  );
}
