"use client";

import * as React from "react";
import { MailPlus, MoreHorizontal, Send, ShieldCheck, Trash2, UserPlus } from "lucide-react";

import { pluralize } from "@/lib/utils";
import { relative } from "@/lib/dates";
import { Button } from "@/components/ui/button";
import { PageHeader, Panel, PanelHeader, Well } from "@/components/ui/surface";
import { Badge } from "@/components/ui/badge";
import { Field, Input, SearchField } from "@/components/ui/input";
import { Avatar, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/controls";
import { Table, TableFrame, Td, Th, Tr } from "@/components/ui/table";
import {
  ConfirmDialog,
  Dialog,
  DialogContent,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/overlay";
import { EmptyState } from "@/components/ui/feedback";
import { notify } from "@/components/ui/toaster";
import { useTeamStore } from "@/stores/workspace";
import { useSessionStore } from "@/stores/session";
import type { Role, TeamMember } from "@/types";

const ROLE_COPY: Record<Role, { label: string; blurb: string }> = {
  admin: { label: "Admin", blurb: "Full access, including billing and integrations." },
  reviewer: { label: "Reviewer", blurb: "Can decide go/no-go and verify findings." },
  writer: { label: "Writer", blurb: "Can edit the matrix, questions, and reports." },
  viewer: { label: "Viewer", blurb: "Read-only across every analysis." },
};

const STATUS_TONE: Record<TeamMember["status"], "leaf" | "ochre" | "neutral"> = {
  active: "leaf",
  invited: "ochre",
  suspended: "neutral",
};

export function TeamView() {
  const members = useTeamStore((s) => s.members);
  const invite = useTeamStore((s) => s.invite);
  const setRole = useTeamStore((s) => s.setRole);
  const updateMember = useTeamStore((s) => s.updateMember);
  const removeMember = useTeamStore((s) => s.removeMember);
  const restoreMember = useTeamStore((s) => s.restoreMember);
  const resendInvite = useTeamStore((s) => s.resendInvite);
  const org = useSessionStore((s) => s.org);
  const user = useSessionStore((s) => s.user);

  const [query, setQuery] = React.useState("");
  const [open, setOpen] = React.useState(false);
  const [confirm, setConfirm] = React.useState<TeamMember | null>(null);
  const [draft, setDraft] = React.useState({ name: "", email: "", title: "", role: "writer" as Role });

  const filtered = members.filter((m) =>
    [m.name, m.email, m.title, m.role].join(" ").toLowerCase().includes(query.trim().toLowerCase()),
  );

  const seatsUsed = members.filter((m) => m.status !== "suspended").length;
  const seats = org?.seats ?? 12;
  const emailValid = /.+@.+\..+/.test(draft.email);

  function submitInvite() {
    if (!draft.name.trim() || !emailValid) return;
    invite({
      name: draft.name.trim(),
      email: draft.email.trim(),
      role: draft.role,
      title: draft.title.trim() || "Capture team",
    });
    setOpen(false);
    setDraft({ name: "", email: "", title: "", role: "writer" });
    notify.success("Invitation sent.", { description: `${draft.email} · ${ROLE_COPY[draft.role].label}` });
  }

  return (
    <div className="mx-auto max-w-[76rem] space-y-6">
      <PageHeader
        eyebrow="Workspace"
        title="Team"
        description="Who can see the documents, and who can decide what happens next."
        actions={
          <Button variant="primary" onClick={() => setOpen(true)}>
            <UserPlus />
            Invite someone
          </Button>
        }
      />

      <div className="grid gap-3 sm:grid-cols-3">
        <Well className="space-y-1">
          <p className="eyebrow">Seats used</p>
          <p className="display-tight text-2xl text-ink tabular">
            {seatsUsed}
            <span className="text-ink-faint"> / {seats}</span>
          </p>
        </Well>
        <Well className="space-y-1">
          <p className="eyebrow">Pending invitations</p>
          <p className="display-tight text-2xl text-ink tabular">
            {members.filter((m) => m.status === "invited").length}
          </p>
        </Well>
        <Well className="space-y-1">
          <p className="eyebrow">Reviewers</p>
          <p className="display-tight text-2xl text-ink tabular">
            {members.filter((m) => m.role === "admin" || m.role === "reviewer").length}
          </p>
        </Well>
      </div>

      <Panel>
        <PanelHeader
          title="Members"
          description={pluralize(members.length, "person", "people")}
          actions={
            <SearchField
              value={query}
              onValueChange={setQuery}
              placeholder="Search the team…"
              className="w-56"
            />
          }
        />

        {filtered.length === 0 ? (
          <div className="p-5">
            <EmptyState
              title="Nobody matches"
              description="Try a different name, email, or role."
              action={
                <Button variant="secondary" onClick={() => setQuery("")}>
                  Clear search
                </Button>
              }
            />
          </div>
        ) : (
          <TableFrame className="border-0">
            <Table>
              <thead>
                <tr>
                  <Th>Member</Th>
                  <Th className="hidden md:table-cell">Title</Th>
                  <Th>Role</Th>
                  <Th className="hidden sm:table-cell">Status</Th>
                  <Th className="text-right">Actions</Th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((member) => {
                  const isYou = member.email === user?.email;
                  return (
                    <Tr key={member.id}>
                      <Td>
                        <div className="flex min-w-0 items-center gap-3">
                          <Avatar
                            name={member.name}
                            tone={member.initialsColor}
                            size="sm"
                            presence={member.status === "active" ? "online" : undefined}
                          />
                          <div className="min-w-0">
                            <p className="truncate text-sm text-ink">
                              {member.name}
                              {isYou ? <span className="ml-1.5 text-xs text-ink-faint">(you)</span> : null}
                            </p>
                            <p className="truncate font-mono text-2xs text-ink-faint">{member.email}</p>
                          </div>
                        </div>
                      </Td>
                      <Td className="hidden md:table-cell">
                        <span className="text-sm text-ink-soft">{member.title}</span>
                      </Td>
                      <Td>
                        <Select
                          value={member.role}
                          onValueChange={(value) => {
                            const previous = setRole(member.id, value as Role);
                            notify.success(`${member.name} is now a ${ROLE_COPY[value as Role].label.toLowerCase()}.`, {
                              undo: previous ? () => setRole(member.id, previous) : undefined,
                            });
                          }}
                        >
                          <SelectTrigger className="h-8 w-32" aria-label={`Role for ${member.name}`}>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {(Object.keys(ROLE_COPY) as Role[]).map((role) => (
                              <SelectItem key={role} value={role}>
                                {ROLE_COPY[role].label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </Td>
                      <Td className="hidden sm:table-cell">
                        <div className="space-y-0.5">
                          <Badge tone={STATUS_TONE[member.status]}>
                            {member.status === "invited"
                              ? "Invited"
                              : member.status === "active"
                                ? "Active"
                                : "Suspended"}
                          </Badge>
                          <p className="text-2xs text-ink-faint">
                            {member.status === "invited" ? "Sent" : "Seen"} {relative(member.lastActive)}
                          </p>
                        </div>
                      </Td>
                      <Td>
                        <div className="flex justify-end">
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="quiet" size="iconSm" aria-label={`Actions for ${member.name}`}>
                                <MoreHorizontal />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuLabel>{member.name}</DropdownMenuLabel>
                              {member.status === "invited" ? (
                                <DropdownMenuItem
                                  onSelect={() => {
                                    resendInvite(member.id);
                                    notify.success("Invitation resent.");
                                  }}
                                >
                                  <Send />
                                  Resend invitation
                                </DropdownMenuItem>
                              ) : null}
                              <DropdownMenuItem
                                onSelect={() =>
                                  notify.info("Draft opened in Outlook.", { description: member.email })
                                }
                              >
                                <MailPlus />
                                Email {member.name.split(" ")[0]}
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onSelect={() => {
                                  const next = member.status === "suspended" ? "active" : "suspended";
                                  updateMember(member.id, { status: next });
                                  notify.success(
                                    next === "suspended" ? "Access suspended." : "Access restored.",
                                    { undo: () => updateMember(member.id, { status: member.status }) },
                                  );
                                }}
                              >
                                <ShieldCheck />
                                {member.status === "suspended" ? "Restore access" : "Suspend access"}
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                destructive
                                disabled={isYou}
                                onSelect={() => setConfirm(member)}
                              >
                                <Trash2 />
                                Remove from workspace
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      </Td>
                    </Tr>
                  );
                })}
              </tbody>
            </Table>
          </TableFrame>
        )}
      </Panel>

      <Panel className="p-5">
        <h2 className="text-lg text-ink">What each role can do</h2>
        <dl className="mt-4 grid gap-4 sm:grid-cols-2">
          {(Object.keys(ROLE_COPY) as Role[]).map((role) => (
            <div key={role} className="space-y-1">
              <dt className="text-sm font-medium text-ink">{ROLE_COPY[role].label}</dt>
              <dd className="text-sm leading-relaxed text-ink-soft">{ROLE_COPY[role].blurb}</dd>
            </div>
          ))}
        </dl>
      </Panel>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          title="Invite someone"
          description="They will get an email and appear here as invited until they accept."
          footer={
            <>
              <Button variant="ghost" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={submitInvite}
                disabled={!draft.name.trim() || !emailValid}
              >
                Send invitation
              </Button>
            </>
          }
        >
          <div className="space-y-4">
            <Field label="Name" htmlFor="inv-name" required>
              <Input
                id="inv-name"
                value={draft.name}
                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                placeholder="Priya Raghunathan"
              />
            </Field>
            <Field
              label="Work email"
              htmlFor="inv-email"
              required
              error={draft.email && !emailValid ? "That doesn't look like an email address." : undefined}
            >
              <Input
                id="inv-email"
                type="email"
                value={draft.email}
                onChange={(e) => setDraft({ ...draft, email: e.target.value })}
                aria-invalid={Boolean(draft.email) && !emailValid}
                placeholder={`name@${org?.domain ?? "thornfield.co"}`}
              />
            </Field>
            <Field label="Title" htmlFor="inv-title">
              <Input
                id="inv-title"
                value={draft.title}
                onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                placeholder="Proposal manager"
              />
            </Field>
            <Field label="Role" htmlFor="inv-role" hint={ROLE_COPY[draft.role].blurb}>
              <Select value={draft.role} onValueChange={(v) => setDraft({ ...draft, role: v as Role })}>
                <SelectTrigger id="inv-role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(Object.keys(ROLE_COPY) as Role[]).map((role) => (
                    <SelectItem key={role} value={role}>
                      {ROLE_COPY[role].label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          </div>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={Boolean(confirm)}
        onOpenChange={(o) => !o && setConfirm(null)}
        title="Remove from the workspace?"
        destructive
        confirmLabel="Remove"
        description={
          confirm
            ? `${confirm.name} will lose access immediately. Work they assigned stays where it is.`
            : ""
        }
        onConfirm={() => {
          if (!confirm) return;
          const removed = removeMember(confirm.id);
          setConfirm(null);
          if (removed) notify.success(`${removed.name} removed.`, { undo: () => restoreMember(removed) });
        }}
      />
    </div>
  );
}
