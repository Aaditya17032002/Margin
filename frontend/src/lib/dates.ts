import {
  differenceInCalendarDays,
  differenceInMilliseconds,
  format,
  formatDistanceToNowStrict,
  parseISO,
} from "date-fns";

/**
 * Seed dates are expressed as offsets from the start of the current UTC day so
 * the demo never rots — deadlines stay live whenever the app is opened — while
 * remaining identical on the server and the client during hydration.
 */
export function anchor() {
  const now = new Date();
  return Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
}

export function offsetDays(days: number, hourUTC = 17, minuteUTC = 0) {
  return new Date(anchor() + days * 86_400_000 + hourUTC * 3_600_000 + minuteUTC * 60_000).toISOString();
}

export function offsetHours(hours: number) {
  return new Date(anchor() + hours * 3_600_000).toISOString();
}

export const TZ_LABELS: Record<string, string> = {
  "America/New_York": "ET",
  "America/Chicago": "CT",
  "America/Denver": "MT",
  "America/Los_Angeles": "PT",
  "America/Phoenix": "MST",
  UTC: "UTC",
};

export function formatInZone(iso: string, timezone: string, pattern = "MMM d, yyyy · h:mm a") {
  const date = parseISO(iso);
  // date-fns has no tz engine without the extra package; Intl does the work here.
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: timezone,
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).formatToParts(date);
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
  if (pattern === "date") return `${get("month")} ${get("day")}, ${get("year")}`;
  if (pattern === "time") return `${get("hour")}:${get("minute")} ${get("dayPeriod")}`;
  return `${get("month")} ${get("day")}, ${get("year")} · ${get("hour")}:${get("minute")} ${get("dayPeriod")}`;
}

export function zoneAbbr(timezone: string) {
  return TZ_LABELS[timezone] ?? timezone.split("/").pop()?.replace("_", " ") ?? timezone;
}

export interface Countdown {
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
  totalMs: number;
  past: boolean;
}

export function countdown(iso: string, from = new Date()): Countdown {
  const target = parseISO(iso);
  const totalMs = differenceInMilliseconds(target, from);
  const abs = Math.abs(totalMs);
  return {
    days: Math.floor(abs / 86_400_000),
    hours: Math.floor((abs % 86_400_000) / 3_600_000),
    minutes: Math.floor((abs % 3_600_000) / 60_000),
    seconds: Math.floor((abs % 60_000) / 1000),
    totalMs,
    past: totalMs < 0,
  };
}

export type Urgency = "past" | "critical" | "near" | "steady";

/**
 * `from` is passed in rather than read from the clock so a component can render
 * the same answer on the server and on the client's first paint.
 */
export function urgency(iso: string, from: number | Date = Date.now()): Urgency {
  const at = typeof from === "number" ? from : from.getTime();
  if (at === 0) return "steady";
  const target = parseISO(iso);
  if (target.getTime() < at) return "past";
  const days = differenceInCalendarDays(target, new Date(at));
  if (days <= 3) return "critical";
  if (days <= 10) return "near";
  return "steady";
}

export function relative(iso: string) {
  return formatDistanceToNowStrict(parseISO(iso), { addSuffix: true });
}

export function shortDate(iso: string) {
  return format(parseISO(iso), "MMM d");
}

export function longDate(iso: string) {
  return format(parseISO(iso), "MMMM d, yyyy");
}

export function dayKey(iso: string) {
  return format(parseISO(iso), "yyyy-MM-dd");
}
