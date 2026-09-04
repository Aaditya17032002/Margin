"use client";

import * as React from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import {
  ChevronRight,
  CloudUpload,
  FileText,
  Folder,
  Home,
  Inbox,
  Library,
  Mail,
  Paperclip,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";

import { cn, formatBytes } from "@/lib/utils";
import { relative } from "@/lib/dates";
import { ApiError, integrationsApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { SearchField } from "@/components/ui/input";
import { EmptyState, Skeleton } from "@/components/ui/feedback";
import type { IntegrationId, RemoteEntry } from "@/types";

/**
 * Browsing a connected source.
 *
 * One component for all three, because the walk is the same shape everywhere —
 * open a thing, see what is inside it, pick a document. What differs is only
 * what a level *means*, and that is presentation: a mailbox lists threads with
 * senders, a drive lists folders and files, SharePoint starts a level higher at
 * the sites a person can reach.
 *
 * Nothing is fetched until a level is opened, and no bytes move until someone
 * picks a document. The browser holds its own breadcrumb rather than asking the
 * server to compute one: it already knows the name of everything it clicked.
 */

// Rows of decreasing width read as a list settling rather than a bar chart.
const SKELETON_WIDTHS = ["w-2/3", "w-1/2", "w-3/5", "w-2/5", "w-1/2", "w-1/3"];

/** A stable identity for "nothing here", so filtering does not re-run. */
const EMPTY: RemoteEntry[] = [];

interface Crumb {
  token: string;
  name: string;
}

const ROOT_CRUMB: Record<IntegrationId, { name: string; icon: typeof Home }> = {
  outlook: { name: "Inbox", icon: Inbox },
  onedrive: { name: "My files", icon: CloudUpload },
  sharepoint: { name: "Sites", icon: Library },
};

const EMPTY_COPY: Record<IntegrationId, { title: string; description: string }> = {
  outlook: {
    title: "No mail with a readable attachment",
    description:
      "Margin looks through the 40 most recent messages that carry an attachment, and shows the ones with a PDF, Word file, or text document on them.",
  },
  onedrive: {
    title: "Nothing readable here",
    description:
      "This folder has no PDF, Word file, or text document in it. Folders are always shown, so you can keep looking.",
  },
  sharepoint: {
    title: "Nothing readable here",
    description:
      "This library has no PDF, Word file, or text document in it. Open another library or site.",
  },
};

export function SourceBrowser({
  provider,
  onPick,
  busyId,
  className,
}: {
  provider: IntegrationId;
  /** Called with the entry to read. The caller owns the import. */
  onPick: (entry: RemoteEntry) => void;
  /** The entry currently being imported, so its row can show the work. */
  busyId?: string | null;
  className?: string;
}) {
  const reduce = useReducedMotion();
  const [crumbs, setCrumbs] = React.useState<Crumb[]>([]);
  // One state per level rather than a loading flag: which level the data
  // belongs to is what "still loading" actually means, so deriving it keeps
  // the effect from having to set state before it has any.
  const [loaded, setLoaded] = React.useState<{ token: string; entries: RemoteEntry[] } | null>(null);
  const [failed, setFailed] = React.useState<{ token: string; message: string; consent?: string } | null>(null);
  const [query, setQuery] = React.useState("");
  const [nonce, setNonce] = React.useState(0);

  const token = crumbs.at(-1)?.token ?? "";
  const entries = React.useMemo(
    () => (loaded?.token === token ? loaded.entries : EMPTY),
    [loaded, token],
  );
  const error = failed?.token === token ? failed : null;
  const loading = loaded?.token !== token && !error;

  React.useEffect(() => {
    let cancelled = false;
    integrationsApi
      .browse(provider, token)
      .then((result) => {
        if (!cancelled) setLoaded({ token, entries: result.entries });
      })
      .catch((caught: unknown) => {
        if (!cancelled) setFailed({ token, ...readError(caught) });
      });
    return () => {
      cancelled = true;
    };
  }, [provider, token, nonce]);

  const reload = React.useCallback(() => {
    setLoaded(null);
    setFailed(null);
    setNonce((n) => n + 1);
  }, []);

  const filtered = React.useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return entries;
    return entries.filter(
      (entry) =>
        entry.name.toLowerCase().includes(needle) || entry.subtitle.toLowerCase().includes(needle),
    );
  }, [entries, query]);

  function open(entry: RemoteEntry) {
    if (entry.importable) {
      onPick(entry);
      return;
    }
    setCrumbs((prev) => [...prev, { token: entry.id, name: entry.name }]);
    setQuery("");
  }

  const Root = ROOT_CRUMB[provider];

  return (
    <div className={cn("flex min-h-0 flex-col gap-3", className)}>
      <div className="flex shrink-0 flex-wrap items-center gap-2">
        <nav aria-label="Location" className="flex min-w-0 flex-1 items-center gap-1 text-sm">
          <button
            type="button"
            onClick={() => setCrumbs([])}
            className={cn(
              "inline-flex shrink-0 items-center gap-1.5 rounded-sm px-1.5 py-1 transition-colors duration-150",
              crumbs.length === 0
                ? "text-ink"
                : "text-ink-soft hover:bg-paper-sunk hover:text-ink",
            )}
          >
            <Root.icon className="size-3.5" aria-hidden />
            {Root.name}
          </button>
          {crumbs.map((crumb, index) => (
            <React.Fragment key={crumb.token}>
              <ChevronRight className="size-3 shrink-0 text-ink-faint/70" aria-hidden />
              <button
                type="button"
                onClick={() => setCrumbs((prev) => prev.slice(0, index + 1))}
                className={cn(
                  "min-w-0 truncate rounded-sm px-1.5 py-1 transition-colors duration-150",
                  index === crumbs.length - 1
                    ? "text-ink"
                    : "text-ink-soft hover:bg-paper-sunk hover:text-ink",
                )}
              >
                {crumb.name}
              </button>
            </React.Fragment>
          ))}
        </nav>
        <Button
          variant="quiet"
          size="iconSm"
          aria-label="Refresh"
          onClick={reload}
          disabled={loading}
        >
          <RefreshCw className={cn(loading && "animate-spin")} />
        </Button>
      </div>

      {entries.length > 8 ? (
        <SearchField
          value={query}
          onValueChange={setQuery}
          placeholder={provider === "outlook" ? "Filter by subject or sender" : "Filter this folder"}
          className="shrink-0"
        />
      ) : null}

      <div className="scroll-region min-h-0 flex-1">
        {loading ? (
          <ul className="space-y-1" aria-busy>
            {Array.from({ length: 6 }, (_, index) => (
              <li key={index} className="flex items-center gap-3 px-2 py-2.5">
                <Skeleton className="size-4 shrink-0 rounded-sm" />
                <Skeleton className={cn("h-3.5", SKELETON_WIDTHS[index])} />
              </li>
            ))}
          </ul>
        ) : error ? (
          <BrowseError error={error} provider={provider} onRetry={reload} />
        ) : filtered.length === 0 ? (
          <EmptyState
            title={query ? "Nothing matches that" : EMPTY_COPY[provider].title}
            description={
              query
                ? "Clear the filter to see everything at this level."
                : EMPTY_COPY[provider].description
            }
            action={
              query ? (
                <Button variant="secondary" size="sm" onClick={() => setQuery("")}>
                  Clear filter
                </Button>
              ) : undefined
            }
          />
        ) : (
          <motion.ul
            key={token}
            initial={reduce ? false : { opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18, ease: [0.32, 0.72, 0, 1] }}
            className="space-y-0.5"
          >
            <AnimatePresence initial={false}>
              {filtered.map((entry) => (
                <EntryRow
                  key={entry.id}
                  entry={entry}
                  busy={busyId === entry.id}
                  onOpen={() => open(entry)}
                />
              ))}
            </AnimatePresence>
          </motion.ul>
        )}
      </div>
    </div>
  );
}

const KIND_ICON = {
  site: Library,
  drive: Folder,
  folder: Folder,
  message: Mail,
  file: FileText,
} as const;

function EntryRow({
  entry,
  busy,
  onOpen,
}: {
  entry: RemoteEntry;
  busy: boolean;
  onOpen: () => void;
}) {
  const Icon = entry.kind === "file" && entry.id.startsWith("msg:") ? Paperclip : KIND_ICON[entry.kind];

  return (
    <li>
      <button
        type="button"
        onClick={onOpen}
        disabled={busy}
        className={cn(
          "group flex w-full items-center gap-3 rounded-md px-2.5 py-2.5 text-left",
          "transition-colors duration-150 hover:bg-paper-sunk disabled:opacity-60",
        )}
      >
        <Icon
          className={cn(
            "size-4 shrink-0",
            entry.kind === "file" ? "text-ink-faint" : "text-ochre",
          )}
          aria-hidden
        />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm text-ink">{entry.name}</span>
          {entry.subtitle ? (
            <span className="mt-0.5 block truncate text-2xs text-ink-faint">{entry.subtitle}</span>
          ) : null}
        </span>
        {entry.size ? (
          <span className="hidden shrink-0 font-mono text-2xs text-ink-faint sm:inline">
            {formatBytes(entry.size)}
          </span>
        ) : null}
        {entry.modified ? (
          <span className="hidden shrink-0 text-2xs text-ink-faint md:inline">
            {relative(entry.modified)}
          </span>
        ) : null}
        <span
          className={cn(
            "shrink-0 text-2xs font-medium",
            busy
              ? "text-patina"
              : entry.importable
                ? "text-patina opacity-0 transition-opacity duration-150 group-hover:opacity-100"
                : "text-ink-faint",
          )}
        >
          {busy ? "Reading…" : entry.importable ? "Read this" : <ChevronRight className="size-3.5" aria-hidden />}
        </span>
      </button>
    </li>
  );
}

/**
 * A failure with a remedy attached.
 *
 * The one that matters is admin consent: SharePoint needs a tenant
 * administrator to grant `Sites.Read.All`, and until they do, every browse
 * returns 403. Saying "something went wrong" there would send a person to
 * support for something only their own IT can fix.
 */
function BrowseError({
  error,
  provider,
  onRetry,
}: {
  error: { message: string; consent?: string } | null;
  provider: IntegrationId;
  onRetry: () => void;
}) {
  if (error?.consent) {
    return (
      <div className="rounded-lg border border-ochre/35 bg-ochre-tint/40 p-5">
        <p className="flex items-center gap-2 text-sm font-medium text-ink">
          <ShieldAlert className="size-4 shrink-0 text-ochre" aria-hidden />
          An administrator has to approve this first
        </p>
        <p className="mt-2 text-sm leading-relaxed text-ink-soft">
          {provider === "sharepoint" ? "SharePoint" : "This source"} reads across sites your
          organisation controls, so Microsoft requires a tenant administrator to grant it once for
          everyone. Nobody can consent to it on their own.
        </p>
        <div className="mt-3 rounded-md border border-line bg-paper-raised p-3">
          <p className="font-mono text-2xs uppercase tracking-[0.12em] text-ink-faint">
            What to ask them for
          </p>
          <p className="mt-1.5 font-mono text-xs text-ink">{error.consent}</p>
          <p className="mt-2 text-xs leading-relaxed text-ink-soft">
            In the Azure portal: Microsoft Entra ID → App registrations → Margin → API permissions →
            <span className="text-ink"> Grant admin consent</span>. Both are read-only; Margin never
            asks for write access.
          </p>
        </div>
        <Button variant="secondary" size="sm" className="mt-3" onClick={onRetry}>
          <RefreshCw />
          Try again
        </Button>
      </div>
    );
  }

  return (
    <EmptyState
      title="That source could not be read"
      description={error?.message ?? "Microsoft did not answer. It may be a moment's outage."}
      action={
        <Button variant="secondary" size="sm" onClick={onRetry}>
          <RefreshCw />
          Try again
        </Button>
      }
    />
  );
}

function readError(caught: unknown): { message: string; consent?: string } {
  if (caught instanceof ApiError) {
    // The consent case arrives as a structured detail so the UI can name the
    // permission instead of echoing a Graph error code at a person.
    const detail = caught.detail as unknown;
    if (detail && typeof detail === "object" && "reason" in detail) {
      const shaped = detail as { reason?: string; scope?: string; message?: string };
      if (shaped.reason === "admin_consent_required") {
        return { message: shaped.message ?? "", consent: shaped.scope ?? "the requested permission" };
      }
    }
    if (typeof detail === "string" && detail.includes("admin_consent_required")) {
      return { message: detail, consent: "Sites.Read.All and Files.Read.All" };
    }
    return { message: caught.message };
  }
  return { message: caught instanceof Error ? caught.message : "Unknown error" };
}
