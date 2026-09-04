"use client";

import * as React from "react";
import { AlertTriangle, Check, CircleHelp, FileUp, Minus, RefreshCw, ScanLine, X } from "lucide-react";

import { cn, pluralize } from "@/lib/utils";
import { responseApi } from "@/lib/api";
import { relative } from "@/lib/dates";
import { Button } from "@/components/ui/button";
import { Panel, PanelHeader, Well } from "@/components/ui/surface";
import { Callout, EmptyState } from "@/components/ui/feedback";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/controls";
import { Tooltip } from "@/components/ui/overlay";
import { notify } from "@/components/ui/toaster";
import { CitationMeta } from "@/components/domain/primitives";
import type { Analysis, CheckStatus, ResponseCheck } from "@/types";

/**
 * The response gap view.
 *
 * Deliberately not a chat over two documents. Every row starts from a
 * requirement in this solicitation's ledger and traces it into the draft:
 *
 *     solicitation clause / page → response section / page → status →
 *     evidence → gap → risk → owner
 *
 * Two things the design refuses to blur. A page count that was *counted* and a
 * model's reading of a narrative section are different kinds of claim, so
 * every row says which it is. And a mandatory requirement is never shown as
 * settled on a machine's say-so — "satisfied" on one reads as awaiting a
 * signature until somebody gives it.
 */

const STATUS: Record<CheckStatus, { label: string; tone: "leaf" | "ochre" | "seal" | "slate" | "neutral"; Icon: typeof Check }> = {
  satisfied: { label: "Answered", tone: "leaf", Icon: Check },
  partial: { label: "Partly answered", tone: "ochre", Icon: Minus },
  failed: { label: "Does not comply", tone: "seal", Icon: X },
  not_found: { label: "Not addressed", tone: "seal", Icon: AlertTriangle },
  unverifiable: { label: "Could not tell", tone: "slate", Icon: CircleHelp },
};

const FILTERS: { value: string; label: string }[] = [
  { value: "attention", label: "Needs attention" },
  { value: "all", label: "Every requirement" },
  { value: "failed", label: "Does not comply" },
  { value: "not_found", label: "Not addressed" },
  { value: "unverifiable", label: "Could not tell" },
  { value: "awaiting", label: "Awaiting sign-off" },
  { value: "satisfied", label: "Answered" },
];

export function ResponseGapPanel({ analysis }: { analysis: Analysis }) {
  const binding = analysis.response;
  const bound = Boolean(binding?.documentId || binding?.version);

  const [checks, setChecks] = React.useState<ResponseCheck[] | null>(null);
  const [filter, setFilter] = React.useState("attention");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  // Bumping this re-fetches. A token rather than a callback in the dependency
  // list, so the effect owns the request and can abandon its own result when
  // the analysis changes under it.
  const [reloads, setReloads] = React.useState(0);
  const load = React.useCallback(() => setReloads((n) => n + 1), []);

  React.useEffect(() => {
    if (!bound) return;
    let live = true;
    responseApi
      .checks(analysis.id)
      .then((rows) => {
        if (!live) return;
        setChecks(rows);
        setError("");
      })
      .catch(() => {
        if (live) setError("The trace could not be loaded.");
      });
    return () => {
      live = false;
    };
  }, [analysis.id, bound, reloads]);

  async function upload(file: File) {
    setBusy(true);
    try {
      const result = await responseApi.bind(analysis.id, file, file.name);
      notify.success(`Draft ${result.version} bound to this solicitation.`, {
        description: "Checking it against every requirement now.",
      });
      window.setTimeout(load, 1500);
    } catch (e) {
      notify.error(
        e instanceof Error && e.message
          ? e.message
          : "The response could not be bound to this analysis.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (!bound) {
    return <BindResponse analysis={analysis} busy={busy} onUpload={upload} />;
  }

  const summary = binding?.summary;
  const rows = checks ?? [];
  const visible = rows.filter((row) => {
    if (filter === "all") return true;
    if (filter === "awaiting") return row.needsConfirmation;
    if (filter === "attention") {
      return row.status !== "satisfied" || row.needsConfirmation;
    }
    return row.status === filter;
  });

  return (
    <div className="space-y-5">
      <Panel>
        <PanelHeader
          title={binding?.label || binding?.fileName || "Draft response"}
          description={
            binding?.at
              ? `Draft ${binding.version} · checked ${relative(binding.at)} against ${summary?.total ?? 0} ${pluralize(summary?.total ?? 0, "requirement")}`
              : "Bound, and waiting for its first check."
          }
          actions={
            <div className="flex items-center gap-2">
              <UploadButton busy={busy} onUpload={upload} label="Upload a new draft" />
              <Button
                variant="secondary"
                size="sm"
                onClick={async () => {
                  await responseApi.recheck(analysis.id);
                  notify.success("Re-checking the draft.");
                  window.setTimeout(load, 1500);
                }}
              >
                <RefreshCw /> Re-check
              </Button>
            </div>
          }
        />
        {summary ? (
          <div className="grid grid-cols-2 gap-px bg-line @lg:grid-cols-4">
            <Metric
              label="Cleared"
              value={summary.cleared}
              detail="Answered and signed off. Smaller than the answered count, on purpose."
            />
            <Metric
              label="Awaiting sign-off"
              value={summary.awaitingConfirmation}
              tone={summary.awaitingConfirmation ? "ochre" : "neutral"}
              detail="A mandatory requirement a rule or a model called answered. It is a recommendation until a person signs it."
            />
            <Metric
              label="Could lose the bid"
              value={summary.blocking}
              tone={summary.blocking ? "seal" : "leaf"}
              detail="Mandatory requirements the response does not answer, or fails."
            />
            <Metric
              label="Requirements traced"
              value={summary.total}
              detail="Every open requirement in the ledger, checked against this draft."
            />
          </div>
        ) : null}
      </Panel>

      {summary?.blocking ? (
        <Callout tone="seal" title={`${pluralize(summary.blocking, "requirement")} could lose this bid`}>
          These are mandatory and the draft does not answer them. Nothing else on this page
          matters more.
        </Callout>
      ) : null}

      <div className="flex flex-wrap items-center gap-3">
        <Select value={filter} onValueChange={setFilter}>
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {FILTERS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span className="text-xs text-ink-faint tabular-nums">
          {visible.length} of {rows.length} shown
        </span>
      </div>

      {error ? <Callout tone="ochre" title="Could not load the trace">{error}</Callout> : null}

      {visible.length === 0 ? (
        <EmptyState
          title={checks === null ? "Checking the draft" : "Nothing in this view"}
          description={
            checks === null
              ? "The trace appears here once every requirement has been checked."
              : "Change the filter to see the rest of the trace."
          }
        />
      ) : (
        <Panel>
          <ul className="divide-y divide-line">
            {visible.map((check) => (
              <li key={check.id}>
                <TraceRow analysis={analysis} check={check} onChange={load} />
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </div>
  );
}

function BindResponse({
  analysis,
  busy,
  onUpload,
}: {
  analysis: Analysis;
  busy: boolean;
  onUpload: (file: File) => void;
}) {
  const read = Boolean(analysis.coverage?.totals.pages);
  return (
    <div className="space-y-5">
      <EmptyState
        title="No draft response bound to this solicitation"
        description={
          read
            ? "Upload your draft and Margin checks it against every requirement it extracted from this package — clause by clause, with the page each answer is on and the gap where there isn't one."
            : "Run the analysis first. Without a requirement ledger there is nothing to check a response against, and a gap report built on no requirements would show a clean sheet."
        }
        action={read ? <UploadButton busy={busy} onUpload={onUpload} label="Upload the draft" /> : undefined}
      />
      <Well>
        <p className="text-xs leading-relaxed text-ink-soft">
          <strong className="font-medium text-ink">What this is not.</strong> It is not a chat over
          two documents, and it does not check the draft against a general idea of a good proposal.
          Every row begins at a requirement in <em>this</em> solicitation&rsquo;s ledger, so a gap is
          a gap against something the agency actually wrote.
        </p>
      </Well>
    </div>
  );
}

function UploadButton({
  busy,
  onUpload,
  label,
}: {
  busy: boolean;
  onUpload: (file: File) => void;
  label: string;
}) {
  const input = React.useRef<HTMLInputElement>(null);
  return (
    <>
      <input
        ref={input}
        type="file"
        className="sr-only"
        accept=".pdf,.docx,.doc,.txt,.md"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onUpload(file);
          event.target.value = "";
        }}
      />
      <Button size="sm" disabled={busy} onClick={() => input.current?.click()}>
        <FileUp /> {busy ? "Uploading…" : label}
      </Button>
    </>
  );
}

function Metric({
  label,
  value,
  detail,
  tone = "neutral",
}: {
  label: string;
  value: number;
  detail: string;
  tone?: "neutral" | "leaf" | "ochre" | "seal";
}) {
  return (
    <div className="bg-paper-raised px-5 py-4">
      <p className="text-2xs font-medium uppercase tracking-[0.08em] text-ink-faint">{label}</p>
      <p
        className={cn(
          "mt-1 font-mono text-2xl leading-none tabular-nums",
          tone === "seal" && "text-seal",
          tone === "ochre" && "text-[color-mix(in_oklab,var(--ochre)_82%,var(--ink))]",
          tone === "leaf" && "text-leaf",
          tone === "neutral" && "text-ink",
        )}
      >
        {value}
      </p>
      <p className="mt-2 text-xs leading-relaxed text-ink-soft">{detail}</p>
    </div>
  );
}

/** One requirement, traced from the solicitation into the draft. */
function TraceRow({
  analysis,
  check,
  onChange,
}: {
  analysis: Analysis;
  check: ResponseCheck;
  onChange: () => void;
}) {
  const status = STATUS[check.status] ?? STATUS.unverifiable;
  const [saving, setSaving] = React.useState(false);

  async function decide(patch: { status?: CheckStatus; confirmed?: boolean }) {
    setSaving(true);
    try {
      await responseApi.decide(analysis.id, check.id, patch);
      notify.success(patch.confirmed ? "Signed off." : "Recorded.", { description: check.reference });
      onChange();
    } catch {
      notify.error("That could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="grid gap-4 px-5 py-4 @3xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      {/* The solicitation half. */}
      <div className="min-w-0 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-xs text-patina">{check.reference}</span>
          {check.stakes === "disqualifying" ? <Badge tone="seal">Mandatory</Badge> : null}
          <RiskBadge risk={check.risk} />
        </div>
        <p className="text-sm leading-relaxed text-ink">{check.requirement}</p>
        <CitationMeta
          citation={check.citation}
          analysisId={analysis.id}
          label={check.reference}
          origin="Response gap"
          compact
          clamp={2}
        />
      </div>

      {/* The response half. */}
      <div className="min-w-0 space-y-2 border-l-0 @3xl:border-l @3xl:border-line @3xl:pl-5">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={status.tone}>
            <status.Icon className="size-3" aria-hidden />
            {status.label}
          </Badge>
          <DecidedBadge check={check} />
          {check.needsConfirmation ? (
            <Tooltip content="A mandatory requirement is never cleared by a rule or a model alone. Signing it off is what settles it.">
              <Badge tone="ochre">Awaiting sign-off</Badge>
            </Tooltip>
          ) : null}
          {check.confirmedBy ? (
            <Badge tone="leaf">
              <Check className="size-3" aria-hidden />
              Signed off
            </Badge>
          ) : null}
        </div>

        {check.detail ? <p className="text-sm leading-relaxed text-ink-soft">{check.detail}</p> : null}

        {check.gap ? (
          <p className="rounded-sm border-l-2 border-seal/45 bg-[var(--seal-tint)] px-3 py-1.5 text-sm leading-relaxed text-ink">
            {check.gap}
          </p>
        ) : null}

        {check.evidence?.quote ? (
          <div className="rounded-sm border border-line bg-paper-sunk px-3 py-2">
            <p className="text-2xs uppercase tracking-[0.08em] text-ink-faint">
              {check.evidence.documentName || "Response"}
              {check.evidence.page ? ` · p.${check.evidence.page}` : ""}
              {check.evidence.section ? ` · ${check.evidence.section}` : ""}
            </p>
            <p className="mt-1 line-clamp-3 text-xs leading-relaxed text-ink-soft">
              {check.evidence.quote}
            </p>
            {check.evidence.located === false ? (
              <p className="mt-1.5 text-2xs text-[color-mix(in_oklab,var(--ochre)_82%,var(--ink))]">
                This passage could not be found in the response, so the claim resting on it was
                downgraded.
              </p>
            ) : null}
          </div>
        ) : null}

        <div className="flex flex-wrap items-center gap-2 pt-1">
          {check.needsConfirmation ? (
            <Button size="sm" variant="secondary" disabled={saving} onClick={() => decide({ confirmed: true })}>
              <Check /> Sign off
            </Button>
          ) : null}
          {check.status !== "failed" ? (
            <Button
              size="sm"
              variant="quiet"
              disabled={saving}
              onClick={() => decide({ status: "failed" })}
            >
              Mark as a gap
            </Button>
          ) : null}
          {check.status !== "satisfied" ? (
            <Button
              size="sm"
              variant="quiet"
              disabled={saving}
              onClick={() => decide({ status: "satisfied", confirmed: true })}
            >
              I have answered this
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function RiskBadge({ risk }: { risk: ResponseCheck["risk"] }) {
  if (risk === "low") return null;
  return (
    <Badge tone={risk === "high" ? "seal" : "ochre"} shape="mono">
      {risk === "high" ? "Could lose the bid" : "Scored risk"}
    </Badge>
  );
}

/**
 * What kind of claim this row is making. A counted page limit and a model's
 * reading of a narrative section are not equally certain, and a view that
 * showed them identically would invite a reader to treat them as if they were.
 */
function DecidedBadge({ check }: { check: ResponseCheck }) {
  if (check.decidedBy === "human") {
    return (
      <Tooltip content="A person decided this. It outranks both the rule and the model.">
        <Badge tone="neutral" shape="mono">
          Decided by a person
        </Badge>
      </Tooltip>
    );
  }
  if (check.decidedBy === "rule") {
    return (
      <Tooltip
        content={
          check.rule
            ? `Counted by the ${check.rule.replace(/[._]/g, " ")} rule — never judged by a model.`
            : "Decided by a rule, not a model."
        }
      >
        <Badge tone="slate" shape="mono">
          <ScanLine className="size-3" aria-hidden />
          Counted
        </Badge>
      </Tooltip>
    );
  }
  return (
    <Tooltip content="Read by a model, which is instructed to say it cannot tell rather than guess.">
      <Badge tone="neutral" shape="mono">
        Read
      </Badge>
    </Tooltip>
  );
}
