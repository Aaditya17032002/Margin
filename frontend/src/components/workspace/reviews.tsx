"use client";

import * as React from "react";
import { Check, ClipboardCheck, Plus, ScanLine, X } from "lucide-react";

import { cn, pluralize } from "@/lib/utils";
import { reviewsApi } from "@/lib/api";
import { relative } from "@/lib/dates";
import { Button } from "@/components/ui/button";
import { Panel, PanelHeader, Well } from "@/components/ui/surface";
import { Callout, EmptyState } from "@/components/ui/feedback";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/controls";
import { Input, Textarea } from "@/components/ui/input";
import { Tooltip } from "@/components/ui/overlay";
import { notify } from "@/components/ui/toaster";
import type {
  Analysis,
  FindingSeverity,
  ReviewColour,
  ReviewFinding,
  ReviewRound,
  ReviewVerdict,
  WhiteGloveItem,
} from "@/types";

/**
 * Colour-team reviews.
 *
 * The rounds a capture team runs before a proposal goes out, and the sign-off
 * that closes each one. Two things this view refuses to blur:
 *
 * A round belongs to a *draft*. When a newer draft is bound, a closed round
 * stops saying anything about what is being sent, and the view says so rather
 * than letting a green tick age out quietly.
 *
 * A round closed over unresolved must-fix findings is shown as an override,
 * never as a pass. The point of an override is that somebody accepted a known
 * risk, and hiding the decision hides the risk with it.
 */

const COLOURS: { value: ReviewColour; label: string }[] = [
  { value: "pink", label: "Pink — approach and structure" },
  { value: "red", label: "Red — score it as the evaluator will" },
  { value: "gold", label: "Gold — is this a bid we will make?" },
  { value: "white_glove", label: "White glove — production check" },
];

const COLOUR_LABEL: Record<ReviewColour, string> = {
  pink: "Pink team",
  red: "Red team",
  gold: "Gold team",
  white_glove: "White glove",
};

const COLOUR_TONE: Record<ReviewColour, "seal" | "ochre" | "leaf" | "slate"> = {
  pink: "ochre",
  red: "seal",
  gold: "leaf",
  white_glove: "slate",
};

const SEVERITY: Record<FindingSeverity, { label: string; tone: "seal" | "ochre" | "neutral" }> = {
  must_fix: { label: "Must fix", tone: "seal" },
  should_fix: { label: "Should fix", tone: "ochre" },
  consider: { label: "Consider", tone: "neutral" },
};

const VERDICTS: { value: ReviewVerdict; label: string }[] = [
  { value: "proceed", label: "Proceed" },
  { value: "proceed_with_fixes", label: "Proceed with fixes" },
  { value: "do_not_proceed", label: "Do not proceed" },
];

export function ReviewsPanel({ analysis }: { analysis: Analysis }) {
  const [rounds, setRounds] = React.useState<ReviewRound[] | null>(null);
  const [charters, setCharters] = React.useState<Record<string, string>>({});
  const [reloads, setReloads] = React.useState(0);
  const [colour, setColour] = React.useState<ReviewColour>("red");
  const [busy, setBusy] = React.useState(false);
  const reload = React.useCallback(() => setReloads((n) => n + 1), []);

  React.useEffect(() => {
    let live = true;
    reviewsApi
      .list(analysis.id)
      .then((result) => {
        if (!live) return;
        setRounds(result.rounds);
        setCharters(result.charters);
      })
      .catch(() => {
        if (live) setRounds([]);
      });
    return () => {
      live = false;
    };
  }, [analysis.id, reloads]);

  const currentDraft = analysis.response?.version ?? 0;

  async function open() {
    setBusy(true);
    try {
      await reviewsApi.open(analysis.id, { colour });
      notify.success(`${COLOUR_LABEL[colour]} opened against draft ${currentDraft}.`);
      reload();
    } catch (error) {
      notify.error(
        error instanceof Error && error.message ? error.message : "The round could not be opened.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (!rounds) {
    return <EmptyState title="Loading the review history" description="One moment." />;
  }

  if (!currentDraft) {
    return (
      <EmptyState
        title="No draft to review"
        description="A review round is opened against a version of the response. Bind a draft on the Response Gap tab first — a round with nothing to review is a meeting, and its record would say a draft passed when no draft existed."
      />
    );
  }

  return (
    <div className="space-y-5">
      <Panel>
        <PanelHeader
          title="Open a round"
          description={`Against draft ${currentDraft}, the version currently bound.`}
          actions={
            <div className="flex items-center gap-2">
              <Select value={colour} onValueChange={(value) => setColour(value as ReviewColour)}>
                <SelectTrigger className="w-72">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {COLOURS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button size="sm" disabled={busy} onClick={open}>
                <Plus /> Open
              </Button>
            </div>
          }
        />
        {charters[colour] ? (
          <div className="px-5 pb-5">
            <Well>
              <p className="text-xs leading-relaxed text-ink-soft">{charters[colour]}</p>
            </Well>
          </div>
        ) : null}
      </Panel>

      {rounds.length === 0 ? (
        <EmptyState
          title="No rounds yet"
          description="Pink for the approach, Red as the evaluator will score it, Gold for whether this is a bid you will make, and White glove for everything Margin can read but cannot see in extracted text."
        />
      ) : (
        rounds.map((round) => (
          <Round
            key={round.id}
            analysis={analysis}
            round={round}
            currentDraft={currentDraft}
            onChange={reload}
          />
        ))
      )}
    </div>
  );
}

function Round({
  analysis,
  round,
  currentDraft,
  onChange,
}: {
  analysis: Analysis;
  round: ReviewRound;
  currentDraft: number;
  onChange: () => void;
}) {
  const stale = round.status === "closed" && round.responseVersion < currentDraft;
  const openFindings = round.findings.filter((f) => f.state === "open");

  return (
    <Panel>
      <PanelHeader
        title={
          <span className="flex flex-wrap items-center gap-2">
            <Badge tone={COLOUR_TONE[round.colour]}>{COLOUR_LABEL[round.colour]}</Badge>
            <span>Draft {round.responseVersion}</span>
            {round.status === "closed" ? (
              <Badge tone={round.overrideReason ? "ochre" : "leaf"}>
                {round.overrideReason ? "Closed with an override" : "Signed off"}
              </Badge>
            ) : (
              <Badge tone="neutral">Open</Badge>
            )}
          </span>
        }
        description={
          round.status === "closed"
            ? `${(round.verdict ?? "").replace(/_/g, " ")} — signed by ${round.closedBy} ${round.closedAt ? relative(round.closedAt) : ""}`
            : `${round.reviewers.join(", ") || "No reviewers named"} · opened ${round.openedAt ? relative(round.openedAt) : ""}`
        }
        actions={
          round.colour === "white_glove" && round.status === "open" ? (
            <WhiteGloveChecklist analysis={analysis} round={round} />
          ) : undefined
        }
      />

      <div className="space-y-4 px-5 pb-5">
        {stale ? (
          <Callout tone="ochre" title={`This round read draft ${round.responseVersion}`}>
            The draft now bound is {currentDraft}. A round says something about the version it
            read and nothing about a later one — what has been reviewed is not what is being
            sent.
          </Callout>
        ) : null}

        {round.overrideReason ? (
          <Callout tone="ochre" title="Closed over unresolved must-fix findings">
            {round.overrideReason}
          </Callout>
        ) : null}

        {round.charter ? (
          <p className="text-xs leading-relaxed text-ink-faint">{round.charter}</p>
        ) : null}

        {round.findings.length ? (
          <ul className="divide-y divide-line rounded-sm border border-line">
            {round.findings.map((finding) => (
              <li key={finding.id}>
                <Finding
                  analysis={analysis}
                  round={round}
                  finding={finding}
                  onChange={onChange}
                />
              </li>
            ))}
          </ul>
        ) : null}

        {round.status === "open" ? (
          <>
            <RaiseFinding analysis={analysis} round={round} onChange={onChange} />
            <CloseRound
              analysis={analysis}
              round={round}
              openMustFix={openFindings.filter((f) => f.severity === "must_fix").length}
              onChange={onChange}
            />
          </>
        ) : null}
      </div>
    </Panel>
  );
}

function Finding({
  analysis,
  round,
  finding,
  onChange,
}: {
  analysis: Analysis;
  round: ReviewRound;
  finding: ReviewFinding;
  onChange: () => void;
}) {
  const [rejecting, setRejecting] = React.useState(false);
  const [reason, setReason] = React.useState("");
  const severity = SEVERITY[finding.severity];

  async function resolve(state: ReviewFinding["state"], resolution?: string) {
    try {
      await reviewsApi.resolve(analysis.id, round.id, finding.id, { state, resolution });
      onChange();
    } catch (error) {
      notify.error(
        error instanceof Error && error.message ? error.message : "That could not be saved.",
      );
    }
  }

  return (
    <div className="space-y-2 px-4 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={severity.tone}>{severity.label}</Badge>
        {finding.location ? (
          <span className="font-mono text-2xs text-patina">{finding.location}</span>
        ) : null}
        {finding.state !== "open" ? (
          <Badge tone={finding.state === "rejected" ? "neutral" : "leaf"}>
            {finding.state}
            {finding.resolvedBy ? ` by ${finding.resolvedBy}` : ""}
          </Badge>
        ) : null}
        <span className="ml-auto text-2xs text-ink-faint">{finding.raisedBy}</span>
      </div>
      <p className="text-sm leading-relaxed text-ink">{finding.text}</p>
      {finding.resolution ? (
        <p className="text-xs leading-relaxed text-ink-soft">{finding.resolution}</p>
      ) : null}

      {round.status === "open" && finding.state === "open" ? (
        rejecting ? (
          <div className="space-y-2">
            <Textarea
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="Why this does not need fixing. The reviewer who raised it needs to see that it was considered."
              rows={2}
              aria-label="Why the finding is being rejected"
            />
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="secondary"
                disabled={!reason.trim()}
                onClick={() => resolve("rejected", reason.trim())}
              >
                Reject with that reason
              </Button>
              <Button size="sm" variant="quiet" onClick={() => setRejecting(false)}>
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="secondary" onClick={() => resolve("fixed")}>
              <Check /> Fixed
            </Button>
            <Button size="sm" variant="quiet" onClick={() => resolve("accepted")}>
              Accepted as is
            </Button>
            <Button size="sm" variant="quiet" onClick={() => setRejecting(true)}>
              <X /> Reject
            </Button>
          </div>
        )
      ) : null}
    </div>
  );
}

function RaiseFinding({
  analysis,
  round,
  onChange,
}: {
  analysis: Analysis;
  round: ReviewRound;
  onChange: () => void;
}) {
  const [text, setText] = React.useState("");
  const [location, setLocation] = React.useState("");
  const [severity, setSeverity] = React.useState<FindingSeverity>("should_fix");

  return (
    <div className="space-y-2 rounded-sm border border-line bg-paper-sunk p-3">
      <Textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="What did you find?"
        rows={2}
        aria-label="The finding"
      />
      <div className="flex flex-wrap gap-2">
        <Input
          value={location}
          onChange={(event) => setLocation(event.target.value)}
          placeholder="Where — Volume I, §3.2"
          aria-label="Where in the response"
          className="max-w-56"
        />
        <Select value={severity} onValueChange={(value) => setSeverity(value as FindingSeverity)}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {(Object.keys(SEVERITY) as FindingSeverity[]).map((key) => (
              <SelectItem key={key} value={key}>
                {SEVERITY[key].label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          size="sm"
          disabled={!text.trim()}
          onClick={async () => {
            await reviewsApi.raise(analysis.id, round.id, {
              text: text.trim(),
              severity,
              location: location.trim(),
            });
            setText("");
            setLocation("");
            onChange();
          }}
        >
          <Plus /> Add finding
        </Button>
      </div>
    </div>
  );
}

function CloseRound({
  analysis,
  round,
  openMustFix,
  onChange,
}: {
  analysis: Analysis;
  round: ReviewRound;
  openMustFix: number;
  onChange: () => void;
}) {
  const [verdict, setVerdict] = React.useState<ReviewVerdict>("proceed");
  const [note, setNote] = React.useState("");
  const [override, setOverride] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  return (
    <div className="space-y-2 rounded-sm border border-line p-3">
      <p className="text-2xs uppercase tracking-[0.08em] text-ink-faint">Sign the round off</p>
      {openMustFix > 0 ? (
        <Callout tone="ochre" title={`${pluralize(openMustFix, "must-fix finding")} still open`}>
          Resolve them, or close the round with a written reason. A deadline sometimes wins — and
          when it does, it wins on the record, as an override rather than as a pass.
        </Callout>
      ) : null}
      <div className="flex flex-wrap items-center gap-2">
        <Select value={verdict} onValueChange={(value) => setVerdict(value as ReviewVerdict)}>
          <SelectTrigger className="w-52">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {VERDICTS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          value={note}
          onChange={(event) => setNote(event.target.value)}
          placeholder="Note (optional)"
          aria-label="Sign-off note"
          className="min-w-56 flex-1"
        />
      </div>
      {openMustFix > 0 ? (
        <Textarea
          value={override}
          onChange={(event) => setOverride(event.target.value)}
          placeholder="Why you are closing this with must-fix findings open. This is recorded as an override."
          rows={2}
          aria-label="Override reason"
        />
      ) : null}
      <Button
        size="sm"
        disabled={busy || (openMustFix > 0 && !override.trim())}
        onClick={async () => {
          setBusy(true);
          try {
            await reviewsApi.close(analysis.id, round.id, {
              verdict,
              note: note.trim() || undefined,
              overrideReason: override.trim() || undefined,
            });
            notify.success("Round signed off.", {
              description: openMustFix > 0 ? "Recorded as an override." : undefined,
            });
            onChange();
          } catch (error) {
            notify.error(
              error instanceof Error && error.message ? error.message : "The round could not be closed.",
            );
          } finally {
            setBusy(false);
          }
        }}
      >
        <ClipboardCheck /> Close the round
      </Button>
    </div>
  );
}

/**
 * What a white-glove round has to check by hand.
 *
 * Every mechanical rule that came back `unverifiable`: fonts, margins,
 * spacing, signatures, copies, binding. Margin can read those requirements and
 * count nothing about them, because they are properties of the rendered file
 * rather than of extracted text. This is a list of exactly what it could not
 * see — which is what a production check is for.
 */
function WhiteGloveChecklist({ analysis, round }: { analysis: Analysis; round: ReviewRound }) {
  const [items, setItems] = React.useState<WhiteGloveItem[] | null>(null);
  const [shown, setShown] = React.useState(false);

  React.useEffect(() => {
    if (!shown) return;
    let live = true;
    reviewsApi
      .checklist(analysis.id, round.id)
      .then((result) => {
        if (live) setItems(result.items);
      })
      .catch(() => {
        if (live) setItems([]);
      });
    return () => {
      live = false;
    };
  }, [analysis.id, round.id, shown]);

  if (!shown) {
    return (
      <Button variant="secondary" size="sm" onClick={() => setShown(true)}>
        <ScanLine /> What to check by hand
      </Button>
    );
  }

  if (!items?.length) {
    return (
      <span className="text-xs text-ink-faint">
        {items ? "Nothing was left unchecked by the rules." : "Loading…"}
      </span>
    );
  }

  return (
    <div className="w-full max-w-2xl space-y-2">
      <p className="text-2xs uppercase tracking-[0.08em] text-ink-faint">
        {items.length} rule{items.length === 1 ? "" : "s"} the checks could not settle
      </p>
      <ul className="space-y-1.5">
        {items.map((item) => (
          <li key={item.checkId} className="flex flex-wrap items-baseline gap-2 text-xs">
            <span className="font-mono text-2xs text-patina">{item.reference}</span>
            <Tooltip content={item.whyNotChecked}>
              <Badge tone="slate" shape="mono">
                {item.rule.replace(/[._]/g, " ")}
              </Badge>
            </Tooltip>
            <span
              className={cn(
                "min-w-0 flex-1 leading-relaxed text-ink-soft",
                item.stakes === "disqualifying" && "text-ink",
              )}
            >
              {item.requirement}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
