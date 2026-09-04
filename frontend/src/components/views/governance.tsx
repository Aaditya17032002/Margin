"use client";

import * as React from "react";
import { ShieldCheck, Trash2 } from "lucide-react";

import { governanceApi } from "@/lib/api";
import { pluralize } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Callout, EmptyState } from "@/components/ui/feedback";
import { Panel, PanelHeader, Well } from "@/components/ui/surface";
import { SettingRow, Switch } from "@/components/ui/controls";
import { Input } from "@/components/ui/input";
import { notify } from "@/components/ui/toaster";
import type { PermissionModel, RetentionView, WorkspaceRole } from "@/types";

/**
 * The two settings surfaces that only work if they are shown honestly.
 *
 * A permission model people cannot see is one they work around — usually by
 * sharing an admin login, which turns a separation-of-duties control into
 * decoration. So the whole matrix is rendered, including what the signed-in
 * person cannot do and who they would have to ask.
 *
 * And a retention policy is unreadable as a number. "1095 days" means nothing
 * until it is "and that is these eleven pursuits, and here is what stays
 * whatever you set" — so the preview is not a separate screen, it is the
 * screen.
 */

const ROLE_ORDER: WorkspaceRole[] = ["admin", "reviewer", "writer", "viewer"];

const ROLE_TONE: Record<WorkspaceRole, "seal" | "ochre" | "leaf" | "neutral"> = {
  admin: "seal",
  reviewer: "leaf",
  writer: "ochre",
  viewer: "neutral",
};

export function PermissionsSection() {
  const [model, setModel] = React.useState<PermissionModel | null>(null);
  const [failed, setFailed] = React.useState(false);

  React.useEffect(() => {
    let live = true;
    governanceApi
      .permissions()
      .then((result) => {
        if (live) setModel(result);
      })
      .catch(() => {
        if (live) setFailed(true);
      });
    return () => {
      live = false;
    };
  }, []);

  if (failed) {
    return (
      <EmptyState
        title="The permission model could not be loaded"
        description="Nothing was changed. Try again, or ask an admin to check the workspace."
      />
    );
  }
  if (!model) {
    return <EmptyState title="Loading the permission model" description="One moment." />;
  }

  return (
    <div className="space-y-5">
      <Panel>
        <PanelHeader
          title="What you can do"
          description={`You are a ${model.you.role}, which ${model.you.purpose}.`}
          actions={<Badge tone={ROLE_TONE[model.you.role]}>{model.you.role}</Badge>}
        />
        <div className="space-y-3 px-5 pb-5">
          <Well>
            <p className="text-xs leading-relaxed text-ink-soft">
              <span className="font-medium text-ink">You can:</span>{" "}
              {model.you.can.map(humanise).join(", ") || "nothing"}.
            </p>
            {model.you.cannot.length > 0 ? (
              <p className="mt-1.5 text-xs leading-relaxed text-ink-soft">
                <span className="font-medium text-ink">You cannot:</span>{" "}
                {model.you.cannot.map(humanise).join(", ")}. A workspace admin can change that.
              </p>
            ) : null}
          </Well>
        </div>
      </Panel>

      <Panel>
        <PanelHeader
          title="Roles"
          description="Named after the decision each one governs, not after the table it writes to."
        />
        <div className="overflow-x-auto px-5 pb-5">
          <table className="w-full min-w-[40rem] text-left text-xs">
            <thead>
              <tr className="border-b border-line text-ink-faint">
                <th className="py-2 pr-4 font-medium">Authority</th>
                {ROLE_ORDER.map((role) => (
                  <th key={role} className="px-2 py-2 text-center font-medium capitalize">
                    {role}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {model.permissions.map((permission) => (
                <tr key={permission.name} className="border-b border-line/60">
                  <td className="py-2 pr-4 text-ink-soft">{permission.describes}</td>
                  {ROLE_ORDER.map((role) => (
                    <td key={role} className="px-2 py-2 text-center">
                      {permission.roles.includes(role) ? (
                        <ShieldCheck className="mx-auto size-3.5 text-leaf" aria-label="Allowed" />
                      ) : (
                        <span className="text-ink-faint" aria-label="Not allowed">
                          —
                        </span>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel>
        <PanelHeader
          title="Separation of duties"
          description="Enforced apart from the roles, because it depends on who opened the thing rather than on who is asking."
        />
        <div className="space-y-2 px-5 pb-5">
          {model.separationOfDuties.map((rule) => (
            <Well key={rule.action}>
              <p className="text-sm text-ink">{rule.action}</p>
              <p className="mt-0.5 text-xs text-ink-soft">{rule.rule}</p>
              <p className="mt-1 text-xs leading-relaxed text-ink-faint">{rule.why}</p>
            </Well>
          ))}
          <p className="text-xs leading-relaxed text-ink-faint">
            Admins are not exempt. An admin can grant themselves any role, so letting them skip
            the second pair of eyes would make the control decorative.
          </p>
        </div>
      </Panel>
    </div>
  );
}

function humanise(name: string) {
  return name.replace(/_/g, " ");
}

/* ------------------------------------------------------------------ */
/* Retention                                                            */
/* ------------------------------------------------------------------ */

const FIELDS: {
  key: "sourceDocumentsDays" | "extractedTextDays" | "responseDraftsDays" | "minimumHoldDays";
  policyKey: keyof RetentionView["policy"];
  label: string;
  description: string;
}[] = [
  {
    key: "sourceDocumentsDays",
    policyKey: "source_documents_days",
    label: "Uploaded files",
    description:
      "The original PDFs and attachments. Citations keep the document name, page and quote, so the matrix still reads after the file is gone.",
  },
  {
    key: "extractedTextDays",
    policyKey: "extracted_text_days",
    label: "Extracted text",
    description:
      "What Margin read the package from. Removing it means the package cannot be re-analysed, so hold it at least as long as the files.",
  },
  {
    key: "responseDraftsDays",
    policyKey: "response_drafts_days",
    label: "Draft responses",
    description:
      "Superseded drafts. The verdicts recorded against each one survive — what goes is the draft body, not the record of what was checked in it.",
  },
  {
    key: "minimumHoldDays",
    policyKey: "minimum_hold_days",
    label: "Minimum hold",
    description:
      "A floor nothing goes below, whatever the numbers above say. It is what stops a policy edited in a hurry from reaching back into last month.",
  },
];

export function RetentionSection() {
  const [view, setView] = React.useState<RetentionView | null>(null);
  const [draft, setDraft] = React.useState<Record<string, string>>({});
  const [busy, setBusy] = React.useState(false);
  const [failed, setFailed] = React.useState(false);

  const load = React.useCallback((result: RetentionView) => {
    setView(result);
    setDraft(
      Object.fromEntries(
        FIELDS.map((field) => [field.key, String(result.policy[field.policyKey] ?? 0)]),
      ),
    );
  }, []);

  React.useEffect(() => {
    let live = true;
    governanceApi
      .retention()
      .then((result) => {
        if (live) load(result);
      })
      .catch(() => {
        if (live) setFailed(true);
      });
    return () => {
      live = false;
    };
  }, [load]);

  if (failed) {
    return (
      <EmptyState
        title="The retention policy could not be loaded"
        description="Nothing was changed."
      />
    );
  }
  if (!view) {
    return <EmptyState title="Loading the retention policy" description="One moment." />;
  }

  async function save(patch: Record<string, number | boolean>) {
    setBusy(true);
    try {
      load(await governanceApi.setRetention(patch));
      notify.success("Retention policy saved.");
    } catch (error) {
      notify.error(
        error instanceof Error && error.message
          ? error.message
          : "The policy was not saved.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function dispose() {
    if (!view) return;
    setBusy(true);
    try {
      const result = await governanceApi.applyRetention(view.due.length);
      notify.success(
        `${result.count} ${pluralize(result.count, "item")} disposed of under the policy.`,
      );
      load(await governanceApi.retention());
    } catch (error) {
      notify.error(
        error instanceof Error && error.message
          ? error.message
          : "Nothing was disposed of.",
      );
    } finally {
      setBusy(false);
    }
  }

  const readOnly = !view.canEdit || busy;

  return (
    <div className="space-y-5">
      <Panel>
        <PanelHeader
          title="Data & retention"
          description="What ages out, when, and what is held whatever the policy says."
          actions={
            <Switch
              checked={view.enabled}
              disabled={readOnly}
              onCheckedChange={(next) => save({ enabled: next })}
              aria-label="Retention policy enabled"
            />
          }
        />
        <div className="space-y-4 p-5">
          <Callout tone="slate" title="Retention disposes of documents, not of the record">
            The requirement ledger, the verdicts, who signed off which round, the questions and
            the decision record are never in scope, on any policy. What was decided and on what
            basis is the thing an auditor asks for, it is small, and no plausible obligation is
            served by destroying it.
          </Callout>

          {view.problems.length > 0 ? (
            <Callout tone="ochre" title="This policy has problems">
              <ul className="space-y-1">
                {view.problems.map((problem) => (
                  <li key={problem}>{problem}</li>
                ))}
              </ul>
            </Callout>
          ) : null}

          <div className="divide-y divide-line">
            {FIELDS.map((field) => (
              <SettingRow
                key={field.key}
                label={field.label}
                description={field.description}
                control={
                  <div className="flex items-center gap-2">
                    <Input
                      type="number"
                      min={0}
                      className="w-28"
                      aria-label={`${field.label} — days`}
                      value={draft[field.key] ?? ""}
                      disabled={readOnly}
                      onChange={(event) =>
                        setDraft((prev) => ({ ...prev, [field.key]: event.target.value }))
                      }
                      onBlur={() => {
                        const next = Number(draft[field.key]);
                        if (!Number.isFinite(next) || next < 0) return;
                        if (next === view.policy[field.policyKey]) return;
                        void save({ [field.key]: next });
                      }}
                    />
                    <span className="text-xs text-ink-faint">days</span>
                  </div>
                }
              />
            ))}
          </div>

          {!view.canEdit ? (
            <p className="text-xs text-ink-faint">
              Only a workspace admin can change retention. You can see what the policy is and what
              it would dispose of.
            </p>
          ) : null}
        </div>
      </Panel>

      <Panel>
        <PanelHeader
          title="What this would dispose of"
          description={
            view.due.length
              ? `${view.due.length} ${pluralize(view.due.length, "item")} are past their retention period.`
              : "Nothing is currently past its retention period."
          }
          actions={
            view.due.length > 0 && view.canEdit && view.enabled ? (
              <Button size="sm" variant="secondary" disabled={busy} onClick={dispose}>
                <Trash2 /> Dispose of {view.due.length}
              </Button>
            ) : undefined
          }
        />
        <div className="space-y-3 px-5 pb-5">
          {view.due.length > 0 ? (
            <ul className="space-y-2">
              {view.due.map((item) => (
                <li key={`${item.analysisId}-${item.class}`}>
                  <Well>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm text-ink">{item.analysisTitle}</span>
                      <Badge tone="neutral">{item.label}</Badge>
                    </div>
                    <p className="mt-0.5 text-xs text-ink-soft">{item.detail}</p>
                  </Well>
                </li>
              ))}
            </ul>
          ) : null}

          <div>
            <p className="text-xs font-medium text-ink">Held whatever the policy says</p>
            <ul className="mt-1 space-y-0.5 text-xs text-ink-soft">
              {view.neverDisposed.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </div>

          {view.skipped.length > 0 ? (
            <div>
              <p className="text-xs font-medium text-ink">Kept, and why</p>
              <ul className="mt-1 space-y-0.5 text-xs text-ink-soft">
                {view.skipped.slice(0, 12).map((item) => (
                  <li key={item.analysisId}>
                    {item.analysisTitle} — {item.reason}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      </Panel>
    </div>
  );
}
