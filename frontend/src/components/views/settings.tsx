"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Check, Contrast, Moon, RotateCcw, Sun, Trash2 } from "lucide-react";

import { cn, formatBytes } from "@/lib/utils";
import { longDate } from "@/lib/dates";
import { useNow } from "@/hooks/use-now";
import { MODES } from "@/data/agents";
import { Button } from "@/components/ui/button";
import { PageHeader, Panel, PanelHeader, Separator, Well } from "@/components/ui/surface";
import { Badge } from "@/components/ui/badge";
import { Field, Input } from "@/components/ui/input";
import {
  Avatar,
  Segmented,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  SettingRow,
  Switch,
} from "@/components/ui/controls";
import { Callout } from "@/components/ui/feedback";
import { ConfirmDialog } from "@/components/ui/overlay";
import { notify } from "@/components/ui/toaster";
import { useSessionStore } from "@/stores/session";
import { useIntegrationsStore, usePrefsStore, useTeamStore } from "@/stores/workspace";
import { resetAllData } from "@/stores";
import type { Appearance, Prefs } from "@/types";

const TABS = [
  { id: "account", label: "Account" },
  { id: "organization", label: "Organisation" },
  { id: "roles", label: "Team & roles" },
  { id: "integrations", label: "Integrations" },
  { id: "notifications", label: "Notifications" },
  { id: "appearance", label: "Appearance" },
  { id: "analysis", label: "Analysis defaults" },
  { id: "billing", label: "Billing & plan" },
  { id: "security", label: "Security" },
  { id: "data", label: "Data & retention" },
  { id: "danger", label: "Danger zone" },
] as const;

type TabId = (typeof TABS)[number]["id"];

const APPEARANCES: { value: Appearance; label: string; icon: typeof Sun; hint: string }[] = [
  { value: "paper", label: "Paper", icon: Sun, hint: "Warm daylight stock" },
  { value: "dusk", label: "Dusk", icon: Moon, hint: "Low light, same ink" },
  { value: "contrast", label: "Contrast", icon: Contrast, hint: "Maximum legibility" },
];

const NOTIFY_COPY: { key: keyof Prefs["notify"]; label: string; description: string }[] = [
  { key: "deadlines", label: "Deadlines", description: "Seven days, three days, and twenty-four hours out." },
  { key: "lowConfidence", label: "Low-confidence findings", description: "When something needs a human eye." },
  { key: "mentions", label: "Mentions", description: "When a teammate names you on a requirement." },
  { key: "amendments", label: "Amendments", description: "When a watched solicitation is amended." },
  { key: "weeklyDigest", label: "Weekly digest", description: "Monday morning summary of the portfolio." },
];

export function SettingsView() {
  const router = useRouter();
  const params = useSearchParams();
  const requested = params.get("tab") as TabId | null;
  const tab: TabId = requested && TABS.some((t) => t.id === requested) ? requested : "account";

  return (
    <div className="mx-auto max-w-[72rem] space-y-6">
      <PageHeader
        eyebrow="Workspace"
        title="Settings"
        description="Account, organisation, and the defaults every new analysis inherits."
      />

      <div className="grid gap-6 lg:grid-cols-[13.5rem_1fr]">
        <nav aria-label="Settings sections" className="lg:sticky lg:top-20 lg:self-start">
          <ul className="scrollbar-none flex gap-1 overflow-x-auto border-b border-line pb-1 lg:block lg:space-y-0.5 lg:border-b-0 lg:pb-0">
            {TABS.map((item) => (
              <li key={item.id} className="shrink-0 lg:shrink">
                <button
                  type="button"
                  aria-current={tab === item.id ? "page" : undefined}
                  onClick={() => router.replace(`/app/settings?tab=${item.id}`, { scroll: false })}
                  className={cn(
                    "w-full whitespace-nowrap rounded-md px-2.5 py-2 text-left text-sm transition-colors duration-150",
                    tab === item.id
                      ? "bg-patina-tint text-ink ring-1 ring-inset ring-[color-mix(in_oklab,var(--patina)_22%,transparent)]"
                      : item.id === "danger"
                        ? "text-seal/85 hover:bg-[var(--seal-tint)] hover:text-seal"
                        : "text-ink-soft hover:bg-paper-sunk hover:text-ink",
                  )}
                >
                  {item.label}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <div className="min-w-0 space-y-5">
          {tab === "account" ? <AccountSection /> : null}
          {tab === "organization" ? <OrganizationSection /> : null}
          {tab === "roles" ? <RolesSection /> : null}
          {tab === "integrations" ? <IntegrationsSection /> : null}
          {tab === "notifications" ? <NotificationsSection /> : null}
          {tab === "appearance" ? <AppearanceSection /> : null}
          {tab === "analysis" ? <AnalysisSection /> : null}
          {tab === "billing" ? <BillingSection /> : null}
          {tab === "security" ? <SecuritySection /> : null}
          {tab === "data" ? <DataSection /> : null}
          {tab === "danger" ? <DangerSection /> : null}
        </div>
      </div>
    </div>
  );
}

interface AccountDraft {
  name: string;
  email: string;
  title: string;
  timezone: string;
}

function AccountSection() {
  const user = useSessionStore((s) => s.user);
  const updateUser = useSessionStore((s) => s.updateUser);

  // The form holds nothing until it is touched, so the store stays the source of
  // truth and there is no effect keeping two copies in step.
  const [edits, setEdits] = React.useState<AccountDraft | null>(null);
  const saved: AccountDraft = {
    name: user?.name ?? "",
    email: user?.email ?? "",
    title: user?.title ?? "",
    timezone: user?.timezone ?? "America/New_York",
  };
  const draft = edits ?? saved;
  const setDraft = (next: AccountDraft) => setEdits(next);

  const dirty =
    edits !== null &&
    (draft.name !== saved.name ||
      draft.email !== saved.email ||
      draft.title !== saved.title ||
      draft.timezone !== saved.timezone);

  return (
    <Panel>
      <PanelHeader title="Account" description="How you appear to the rest of the workspace." />
      <div className="space-y-5 p-5">
        <div className="flex items-center gap-4">
          <Avatar name={draft.name || "Margin User"} tone={user?.avatarTone ?? "patina"} size="lg" />
          <div className="space-y-1">
            <p className="text-sm text-ink">{draft.name || "Margin User"}</p>
            <p className="text-xs text-ink-faint">Initials are generated from your name.</p>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Full name" htmlFor="acct-name">
            <Input id="acct-name" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
          </Field>
          <Field label="Work email" htmlFor="acct-email">
            <Input
              id="acct-email"
              type="email"
              value={draft.email}
              onChange={(e) => setDraft({ ...draft, email: e.target.value })}
            />
          </Field>
          <Field label="Title" htmlFor="acct-title">
            <Input
              id="acct-title"
              value={draft.title}
              onChange={(e) => setDraft({ ...draft, title: e.target.value })}
            />
          </Field>
          <Field label="Time zone" htmlFor="acct-tz" hint="Used for every countdown">
            <Select value={draft.timezone} onValueChange={(v) => setDraft({ ...draft, timezone: v })}>
              <SelectTrigger id="acct-tz">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles", "UTC"].map(
                  (zone) => (
                    <SelectItem key={zone} value={zone}>
                      {zone.replace("_", " ")}
                    </SelectItem>
                  ),
                )}
              </SelectContent>
            </Select>
          </Field>
        </div>

        <div className="flex justify-end gap-2 border-t border-line pt-4">
          <Button variant="ghost" disabled={!dirty} onClick={() => setEdits(null)}>
            Discard
          </Button>
          <Button
            variant="primary"
            disabled={!dirty}
            onClick={() => {
              updateUser(draft);
              setEdits(null);
              notify.success("Account updated.");
            }}
          >
            Save changes
          </Button>
        </div>
      </div>
    </Panel>
  );
}

interface OrgDraft {
  name: string;
  domain: string;
  duns: string;
  cage: string;
}

function OrganizationSection() {
  const org = useSessionStore((s) => s.org);
  const updateOrg = useSessionStore((s) => s.updateOrg);

  const [edits, setEdits] = React.useState<OrgDraft | null>(null);
  const draft: OrgDraft = edits ?? {
    name: org?.name ?? "",
    domain: org?.domain ?? "",
    duns: org?.duns ?? "",
    cage: org?.cage ?? "",
  };
  const setDraft = (next: OrgDraft) => setEdits(next);

  return (
    <Panel>
      <PanelHeader title="Organisation" description="Identifiers that appear on every generated report." />
      <div className="space-y-5 p-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Legal name" htmlFor="org-name">
            <Input id="org-name" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
          </Field>
          <Field label="Email domain" htmlFor="org-domain">
            <Input
              id="org-domain"
              value={draft.domain}
              onChange={(e) => setDraft({ ...draft, domain: e.target.value })}
            />
          </Field>
          <Field label="UEI / DUNS" htmlFor="org-duns">
            <Input
              id="org-duns"
              className="font-mono"
              value={draft.duns}
              onChange={(e) => setDraft({ ...draft, duns: e.target.value })}
            />
          </Field>
          <Field label="CAGE code" htmlFor="org-cage">
            <Input
              id="org-cage"
              className="font-mono"
              value={draft.cage}
              onChange={(e) => setDraft({ ...draft, cage: e.target.value })}
            />
          </Field>
        </div>
        <div className="flex justify-end border-t border-line pt-4">
          <Button
            variant="primary"
            onClick={() => {
              updateOrg(draft);
              setEdits(null);
              notify.success("Organisation updated.");
            }}
          >
            Save changes
          </Button>
        </div>
      </div>
    </Panel>
  );
}

function RolesSection() {
  const members = useTeamStore((s) => s.members);
  return (
    <Panel>
      <PanelHeader
        title="Team & roles"
        description="Role changes and invitations live on the team page."
        actions={
          <Button asChild variant="secondary" size="sm">
            <Link href="/app/team">Open team</Link>
          </Button>
        }
      />
      <ul className="divide-y divide-line">
        {members.slice(0, 6).map((member) => (
          <li key={member.id} className="flex items-center gap-3 px-5 py-3">
            <Avatar name={member.name} tone={member.initialsColor} size="sm" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm text-ink">{member.name}</p>
              <p className="truncate font-mono text-2xs text-ink-faint">{member.email}</p>
            </div>
            <Badge tone="neutral">{member.role}</Badge>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

function IntegrationsSection() {
  const integrations = useIntegrationsStore((s) => s.integrations);
  return (
    <Panel>
      <PanelHeader
        title="Integrations"
        description="Connect and disconnect on the integrations hub."
        actions={
          <Button asChild variant="secondary" size="sm">
            <Link href="/app/integrations">Open hub</Link>
          </Button>
        }
      />
      <ul className="divide-y divide-line">
        {integrations.map((integration) => (
          <li key={integration.id} className="flex items-center justify-between gap-4 px-5 py-3.5">
            <div className="min-w-0">
              <p className="text-sm text-ink">{integration.name}</p>
              <p className="truncate font-mono text-2xs text-ink-faint">
                {integration.connected ? integration.account : "Not connected"}
              </p>
            </div>
            <Badge tone={integration.connected ? "leaf" : "neutral"}>
              {integration.connected ? "Connected" : "Off"}
            </Badge>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

function NotificationsSection() {
  const notifyPrefs = usePrefsStore((s) => s.notify);
  const setNotify = usePrefsStore((s) => s.setNotify);
  return (
    <Panel>
      <PanelHeader title="Notifications" description="What is worth interrupting you for." />
      <div className="divide-y divide-line px-5">
        {NOTIFY_COPY.map((item) => (
          <SettingRow
            key={item.key}
            label={item.label}
            description={item.description}
            control={
              <Switch
                checked={notifyPrefs[item.key]}
                onCheckedChange={(checked) => setNotify(item.key, checked)}
                aria-label={item.label}
              />
            }
          />
        ))}
      </div>
    </Panel>
  );
}

function AppearanceSection() {
  const appearance = usePrefsStore((s) => s.appearance);
  const setAppearance = usePrefsStore((s) => s.setAppearance);
  const density = usePrefsStore((s) => s.density);
  const setDensity = usePrefsStore((s) => s.setDensity);
  const reduceMotion = usePrefsStore((s) => s.reduceMotion);
  const toggleReduceMotion = usePrefsStore((s) => s.toggleReduceMotion);
  const shortcutsEnabled = usePrefsStore((s) => s.shortcutsEnabled);
  const toggleShortcuts = usePrefsStore((s) => s.toggleShortcuts);
  const resetCoach = usePrefsStore((s) => s.resetCoach);

  return (
    <Panel>
      <PanelHeader title="Appearance" description="The same ink, on different stock." />
      <div className="p-5">
        <div className="grid gap-3 sm:grid-cols-3">
          {APPEARANCES.map((option) => {
            const Icon = option.icon;
            const active = appearance === option.value;
            return (
              <button
                key={option.value}
                type="button"
                onClick={() => setAppearance(option.value)}
                aria-pressed={active}
                className={cn(
                  "group flex flex-col gap-3 rounded-md border p-4 text-left",
                  "transition-[border-color,background-color] duration-200 ease-[cubic-bezier(0.32,0.72,0,1)]",
                  active
                    ? "border-patina bg-patina-tint"
                    : "border-line-strong bg-paper-sunk hover:border-[var(--ink-faint)]",
                )}
              >
                <span className="flex items-center justify-between">
                  <Icon className={cn("size-4", active ? "text-patina" : "text-ink-faint")} aria-hidden />
                  {active ? <Check className="size-4 text-patina" aria-hidden /> : null}
                </span>
                <span>
                  <span className="block text-sm font-medium text-ink">{option.label}</span>
                  <span className="block text-xs text-ink-faint">{option.hint}</span>
                </span>
                <span
                  aria-hidden
                  data-appearance={option.value}
                  className="flex h-12 items-end gap-1 rounded-sm border border-line bg-paper p-2"
                >
                  <span className="h-2 flex-1 rounded-full bg-[var(--ink-faint)]" />
                  <span className="h-4 flex-1 rounded-full bg-[var(--patina)]" />
                  <span className="h-3 flex-1 rounded-full bg-[var(--ochre)]" />
                  <span className="h-6 flex-1 rounded-full bg-[var(--ink)]" />
                </span>
              </button>
            );
          })}
        </div>

        <Separator className="my-5" />

        <div className="divide-y divide-line">
          <SettingRow
            label="Density"
            description="Compact tightens the shell without shrinking the type."
            control={
              <Segmented
                ariaLabel="Density"
                value={density}
                onValueChange={(v) => setDensity(v as "comfortable" | "compact")}
                options={[
                  { value: "comfortable", label: "Comfortable" },
                  { value: "compact", label: "Compact" },
                ]}
              />
            }
          />
          <SettingRow
            label="Reduce motion"
            description="Transitions become instant. The system preference is honoured regardless."
            control={<Switch checked={reduceMotion} onCheckedChange={toggleReduceMotion} aria-label="Reduce motion" />}
          />
          <SettingRow
            label="Keyboard shortcuts"
            description="Single-key shortcuts across the workspace. ⌘K always works."
            control={
              <Switch checked={shortcutsEnabled} onCheckedChange={toggleShortcuts} aria-label="Keyboard shortcuts" />
            }
          />
          <SettingRow
            label="First-run notes"
            description="The three desk notes that appear the first time you open the dashboard."
            control={
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  resetCoach();
                  notify.info("The notes will be on the dashboard next time you open it.");
                }}
              >
                Show again
              </Button>
            }
          />
        </div>
      </div>
    </Panel>
  );
}

function AnalysisSection() {
  const defaultMode = usePrefsStore((s) => s.defaultMode);
  const setDefaultMode = usePrefsStore((s) => s.setDefaultMode);
  const railPinned = usePrefsStore((s) => s.marginRailPinned);
  const setRailPinned = usePrefsStore((s) => s.setRailPinned);

  return (
    <Panel>
      <PanelHeader title="Analysis defaults" description="What every new read inherits." />
      <div className="space-y-4 p-5">
        <ul className="grid gap-2.5 sm:grid-cols-2">
          {MODES.map((mode) => {
            const active = defaultMode === mode.id;
            return (
              <li key={mode.id}>
                <button
                  type="button"
                  onClick={() => setDefaultMode(mode.id)}
                  aria-pressed={active}
                  className={cn(
                    "flex h-full w-full flex-col gap-1 rounded-md border p-3.5 text-left",
                    "transition-[border-color,background-color] duration-200 ease-[cubic-bezier(0.32,0.72,0,1)]",
                    active
                      ? "border-patina bg-patina-tint"
                      : "border-line-strong bg-paper-sunk hover:border-[var(--ink-faint)]",
                  )}
                >
                  <span className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium text-ink">{mode.name}</span>
                    {active ? <Check className="size-3.5 shrink-0 text-patina" aria-hidden /> : null}
                  </span>
                  <span className="text-xs leading-relaxed text-ink-soft">{mode.blurb}</span>
                  <span className="mt-auto pt-1.5 font-mono text-2xs text-ink-faint">
                    {mode.minutes} · {mode.passes}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>

        <Separator />

        <div className="divide-y divide-line">
          <SettingRow
            label="Keep the Margin rail pinned"
            description="The source panel stays open instead of appearing on hover."
            control={<Switch checked={railPinned} onCheckedChange={setRailPinned} aria-label="Pin the Margin rail" />}
          />
        </div>
      </div>
    </Panel>
  );
}

function BillingSection() {
  const org = useSessionStore((s) => s.org);
  const members = useTeamStore((s) => s.members);
  const now = useNow(60_000);
  const used = members.filter((m) => m.status !== "suspended").length;
  const seats = org?.seats ?? 12;
  const renews = now === 0 ? null : longDate(new Date(now + 86_400_000 * 128).toISOString());

  return (
    <div className="space-y-5">
      <Panel>
        <PanelHeader title="Plan" description="Billed annually. Change anything at renewal." />
        <div className="space-y-4 p-5">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <Badge tone="patina">{org?.plan ?? "Practice"}</Badge>
              <p className="display-tight mt-2 text-3xl text-ink">
                $480
                <span className="text-base text-ink-faint"> / seat / year</span>
              </p>
              <p className="mt-1 text-sm text-ink-soft">
                {used} of {seats} seats in use{renews ? ` · renews ${renews}` : ""}
              </p>
            </div>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={() => notify.info("Invoices opened in a new tab.")}>
                Invoices
              </Button>
              <Button asChild variant="primary">
                <Link href="/pricing">Change plan</Link>
              </Button>
            </div>
          </div>

          <Well className="space-y-2">
            <p className="eyebrow">This period</p>
            <dl className="grid gap-3 sm:grid-cols-3">
              <div>
                <dt className="text-xs text-ink-faint">Documents read</dt>
                <dd className="text-lg text-ink tabular">146</dd>
              </div>
              <div>
                <dt className="text-xs text-ink-faint">Pages processed</dt>
                <dd className="text-lg text-ink tabular">18,402</dd>
              </div>
              <div>
                <dt className="text-xs text-ink-faint">Reports exported</dt>
                <dd className="text-lg text-ink tabular">63</dd>
              </div>
            </dl>
          </Well>
        </div>
      </Panel>

      <Panel>
        <PanelHeader title="Payment method" />
        <div className="flex items-center justify-between gap-4 p-5">
          <div className="flex items-center gap-3">
            <span className="flex h-8 w-12 items-center justify-center rounded-sm border border-line-strong bg-paper-sunk font-mono text-2xs text-ink-soft">
              VISA
            </span>
            <div>
              <p className="font-mono text-sm text-ink">•••• •••• •••• 4412</p>
              <p className="text-xs text-ink-faint">Expires 04 / 2029 · Thornfield &amp; Co</p>
            </div>
          </div>
          <Button variant="secondary" size="sm" onClick={() => notify.info("Card update opened.")}>
            Update
          </Button>
        </div>
      </Panel>
    </div>
  );
}

function SecuritySection() {
  const [twoFactor, setTwoFactor] = React.useState(true);
  const [sso, setSso] = React.useState(true);

  return (
    <div className="space-y-5">
      <Panel>
        <PanelHeader title="Security" description="How people get in, and how they are kept out." />
        <div className="divide-y divide-line px-5">
          <SettingRow
            label="Two-factor authentication"
            description="Required for admins and reviewers."
            control={
              <Switch
                checked={twoFactor}
                onCheckedChange={(v) => {
                  setTwoFactor(v);
                  notify.success(v ? "Two-factor required." : "Two-factor no longer required.");
                }}
                aria-label="Two-factor authentication"
              />
            }
          />
          <SettingRow
            label="Microsoft Entra SSO"
            description="Members sign in with their work account."
            control={<Switch checked={sso} onCheckedChange={setSso} aria-label="Microsoft SSO" />}
          />
          <SettingRow
            label="Session length"
            description="How long a session survives without activity."
            control={
              <Select defaultValue="8h">
                <SelectTrigger className="w-32" aria-label="Session length">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1h">1 hour</SelectItem>
                  <SelectItem value="8h">8 hours</SelectItem>
                  <SelectItem value="7d">7 days</SelectItem>
                </SelectContent>
              </Select>
            }
          />
        </div>
      </Panel>

      <Panel>
        <PanelHeader title="Active sessions" />
        <ul className="divide-y divide-line">
          {[
            { device: "Chrome · Windows", where: "Alexandria, VA", when: "Now", current: true },
            { device: "Safari · iPhone", where: "Alexandria, VA", when: "2 hours ago", current: false },
            { device: "Edge · Windows", where: "Reston, VA", when: "Yesterday", current: false },
          ].map((session) => (
            <li key={session.device} className="flex items-center justify-between gap-4 px-5 py-3.5">
              <div>
                <p className="text-sm text-ink">
                  {session.device}
                  {session.current ? <span className="ml-2 text-xs text-patina">this device</span> : null}
                </p>
                <p className="text-xs text-ink-faint">
                  {session.where} · {session.when}
                </p>
              </div>
              {session.current ? null : (
                <Button variant="quiet" size="sm" onClick={() => notify.success("Session revoked.")}>
                  Revoke
                </Button>
              )}
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}

function DataSection() {
  return (
    <Panel>
      <PanelHeader title="Data & retention" description="What Margin keeps, and for how long." />
      <div className="space-y-4 p-5">
        <Callout tone="slate" title="Source documents are never copied">
          Margin stores citations — a page, a section, and the quoted line — not the file itself. Disconnecting a
          source leaves your findings intact and their sources unreachable.
        </Callout>

        <div className="divide-y divide-line">
          <SettingRow
            label="Retain decided analyses"
            description="How long a decided bid stays in the workspace."
            control={
              <Select defaultValue="24">
                <SelectTrigger className="w-40" aria-label="Retention period">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="12">12 months</SelectItem>
                  <SelectItem value="24">24 months</SelectItem>
                  <SelectItem value="forever">Indefinitely</SelectItem>
                </SelectContent>
              </Select>
            }
          />
          <SettingRow
            label="Export everything"
            description="A single archive of analyses, matrices, questions, and the audit trail."
            control={
              <Button
                variant="secondary"
                size="sm"
                onClick={() =>
                  notify.success("Archive requested.", {
                    description: `Approximately ${formatBytes(48_200_000)} — you will get an email when it is ready.`,
                  })
                }
              >
                Request archive
              </Button>
            }
          />
        </div>
      </div>
    </Panel>
  );
}

function DangerSection() {
  const router = useRouter();
  const logout = useSessionStore((s) => s.logout);
  const resetOnboarding = useSessionStore((s) => s.resetOnboarding);
  const [confirmReset, setConfirmReset] = React.useState(false);
  const [confirmDelete, setConfirmDelete] = React.useState(false);

  return (
    <>
      <Panel className="border-seal/35">
        <PanelHeader
          title="Danger zone"
          description="These actions are immediate and, apart from the first, irreversible."
          className="border-b-seal/25"
        />
        <div className="divide-y divide-line px-5">
          <SettingRow
            label="Reset demo data"
            description="Return every analysis, matrix, and note to the seeded state."
            control={
              <Button variant="secondary" size="sm" onClick={() => setConfirmReset(true)}>
                <RotateCcw />
                Reset data
              </Button>
            }
          />
          <SettingRow
            label="Replay onboarding"
            description="Walk through the first-run wizard again."
            control={
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  resetOnboarding();
                  router.push("/onboarding");
                }}
              >
                Replay
              </Button>
            }
          />
          <SettingRow
            label="Delete this workspace"
            description="Every analysis, requirement, and report is removed."
            control={
              <Button variant="outlineDanger" size="sm" onClick={() => setConfirmDelete(true)}>
                <Trash2 />
                Delete workspace
              </Button>
            }
          />
        </div>
      </Panel>

      <ConfirmDialog
        open={confirmReset}
        onOpenChange={setConfirmReset}
        title="Reset all data?"
        confirmLabel="Reset"
        description="Your edits are discarded and the seeded portfolio returns. Preferences are kept."
        onConfirm={() => {
          resetAllData();
          setConfirmReset(false);
          notify.success("Demo data restored.");
        }}
      />

      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title="Delete the workspace?"
        destructive
        confirmLabel="Delete everything"
        description="This cannot be undone. You will be signed out immediately."
        onConfirm={() => {
          logout();
          router.push("/");
          notify.success("Workspace deleted.");
        }}
      />
    </>
  );
}
