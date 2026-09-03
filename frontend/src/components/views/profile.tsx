"use client";

import * as React from "react";
import Link from "next/link";
import { format, parseISO } from "date-fns";
import { Pencil } from "lucide-react";

import { cn, pluralize } from "@/lib/utils";
import { relative } from "@/lib/dates";
import { Button } from "@/components/ui/button";
import { PageHeader, Panel, PanelHeader, Separator, Well } from "@/components/ui/surface";
import { Badge } from "@/components/ui/badge";
import { Field, Input, Textarea } from "@/components/ui/input";
import { Avatar, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/controls";
import { notify } from "@/components/ui/toaster";
import { useSessionStore } from "@/stores/session";
import { useAnalysesStore } from "@/stores/analyses";
import { useMatrixStore } from "@/stores/matrix";
import { useReportsStore, useTeamStore } from "@/stores/workspace";

const TONES = ["patina", "slate", "ochre", "leaf", "seal", "ink"];

interface ProfileDraft {
  name: string;
  title: string;
  signature: string;
  avatarTone: string;
}

export function ProfileView() {
  const user = useSessionStore((s) => s.user);
  const org = useSessionStore((s) => s.org);
  const updateUser = useSessionStore((s) => s.updateUser);
  const analyses = useAnalysesStore((s) => s.analyses);
  const rows = useMatrixStore((s) => s.rows);
  const activity = useReportsStore((s) => s.activity);
  const members = useTeamStore((s) => s.members);

  const [editing, setEditing] = React.useState(false);
  const [edits, setEdits] = React.useState<ProfileDraft | null>(null);

  const draft: ProfileDraft = edits ?? {
    name: user?.name ?? "",
    title: user?.title ?? "",
    signature: user?.signature ?? "",
    avatarTone: user?.avatarTone ?? "patina",
  };
  const setDraft = (next: ProfileDraft) => setEdits(next);

  if (!user) return null;

  const owned = analyses.filter((a) => a.owner === user.name);
  const assigned = rows.filter((r) => r.owner === user.name);
  const mine = activity.filter((a) => a.actor === user.name || a.actor === "You").slice(0, 12);
  const membership = members.find((m) => m.email === user.email);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        eyebrow="Workspace"
        title="Profile"
        description="Your details, your signature block, and what you are carrying."
        actions={
          editing ? null : (
            <Button variant="secondary" onClick={() => setEditing(true)}>
              <Pencil />
              Edit profile
            </Button>
          )
        }
      />

      <Panel className="p-6">
        <div className="flex flex-wrap items-start gap-6">
          <Avatar name={draft.name} tone={draft.avatarTone} size="lg" presence="online" />
          <div className="min-w-0 flex-1 space-y-1">
            <h2 className="display-tight text-2xl text-ink">{draft.name}</h2>
            <p className="text-sm text-ink-soft">{draft.title}</p>
            <p className="font-mono text-xs text-ink-faint">{user.email}</p>
            <div className="flex flex-wrap items-center gap-2 pt-2">
              {membership ? <Badge tone="patina">{membership.role}</Badge> : null}
              <Badge tone="neutral">{org?.name ?? "Thornfield & Co"}</Badge>
              <Badge tone="neutral" shape="mono">
                {user.timezone.replace("_", " ")}
              </Badge>
            </div>
          </div>
        </div>

        {editing ? (
          <>
            <Separator className="my-5" />
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Name" htmlFor="pf-name">
                <Input
                  id="pf-name"
                  value={draft.name}
                  onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                />
              </Field>
              <Field label="Title" htmlFor="pf-title">
                <Input
                  id="pf-title"
                  value={draft.title}
                  onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                />
              </Field>
              <Field label="Avatar colour" htmlFor="pf-tone" className="sm:col-span-2">
                <Select value={draft.avatarTone} onValueChange={(v) => setDraft({ ...draft, avatarTone: v })}>
                  <SelectTrigger id="pf-tone" className="w-48">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TONES.map((tone) => (
                      <SelectItem key={tone} value={tone}>
                        {tone.charAt(0).toUpperCase() + tone.slice(1)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
              <Field
                label="Signature block"
                htmlFor="pf-signature"
                hint="Appended to exported reports and agency emails"
                className="sm:col-span-2"
              >
                <Textarea
                  id="pf-signature"
                  value={draft.signature}
                  onChange={(e) => setDraft({ ...draft, signature: e.target.value })}
                />
              </Field>
            </div>
            <div className="mt-4 flex justify-end gap-2 border-t border-line pt-4">
              <Button
                variant="ghost"
                onClick={() => {
                  setEdits(null);
                  setEditing(false);
                }}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={() => {
                  updateUser(draft);
                  setEdits(null);
                  setEditing(false);
                  notify.success("Profile updated.");
                }}
              >
                Save profile
              </Button>
            </div>
          </>
        ) : (
          <>
            <Separator className="my-5" />
            <p className="eyebrow mb-2">Signature</p>
            <Well className="font-mono text-sm leading-relaxed text-ink-soft">{user.signature}</Well>
          </>
        )}
      </Panel>

      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Analyses owned" value={String(owned.length)} />
        <Stat label="Requirements assigned" value={String(assigned.length)} />
        <Stat
          label="Completed"
          value={`${assigned.length ? Math.round((assigned.filter((r) => r.status === "complete").length / assigned.length) * 100) : 0}%`}
        />
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Panel>
          <PanelHeader title="Your analyses" description={pluralize(owned.length, "analysis", "analyses")} />
          {owned.length === 0 ? (
            <p className="px-5 py-6 text-sm text-ink-soft">Nothing assigned to you yet.</p>
          ) : (
            <ul className="divide-y divide-line">
              {owned.map((analysis) => (
                <li key={analysis.id}>
                  <Link
                    href={`/app/analyses/${analysis.id}`}
                    className="block px-5 py-3.5 transition-colors duration-150 hover:bg-paper-sunk"
                  >
                    <p className="truncate text-sm text-ink">{analysis.title}</p>
                    <p className="font-mono text-2xs text-ink-faint">
                      {analysis.solicitationNumber} · {analysis.stage}
                    </p>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel>
          <PanelHeader title="Recent activity" />
          {mine.length === 0 ? (
            <p className="px-5 py-6 text-sm text-ink-soft">No recorded activity yet.</p>
          ) : (
            <ul className="divide-y divide-line">
              {mine.map((entry) => (
                <li key={entry.id} className="px-5 py-3">
                  <p className="text-sm leading-relaxed text-ink-soft">
                    You {entry.action} <span className="text-ink">{entry.target ?? ""}</span>
                  </p>
                  <p className="font-mono text-2xs text-ink-faint">
                    {format(parseISO(entry.at), "MMM d, HH:mm")} · {relative(entry.at)}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Well className="space-y-1">
      <p className="eyebrow">{label}</p>
      <p className={cn("display-tight text-2xl text-ink tabular")}>{value}</p>
    </Well>
  );
}
