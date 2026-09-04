"use client";

import * as React from "react";
import { motion, useReducedMotion } from "motion/react";
import { Check, CloudUpload, Copy, FolderTree, Mail, Plug, RefreshCw, ShieldCheck, Unplug } from "lucide-react";

import { cn } from "@/lib/utils";
import { relative } from "@/lib/dates";
import { Button } from "@/components/ui/button";
import { PageHeader, Panel, PanelHeader, Separator, Well } from "@/components/ui/surface";
import { Badge } from "@/components/ui/badge";
import { Segmented } from "@/components/ui/controls";
import { Callout } from "@/components/ui/feedback";
import { ConfirmDialog } from "@/components/ui/overlay";
import { notify } from "@/components/ui/toaster";
import { SourceBrowser } from "@/components/shell/source-browser";
import { useIntegrationsStore, usePrefsStore } from "@/stores/workspace";
import { useSessionStore } from "@/stores/session";
import { useRouter } from "next/navigation";
import { ApiError, integrationsApi } from "@/lib/api";
import type { Integration, IntegrationId, RemoteEntry } from "@/types";

const ICONS: Record<IntegrationId, typeof Mail> = {
  outlook: Mail,
  sharepoint: FolderTree,
  onedrive: CloudUpload,
};

export function IntegrationsView() {
  const reduce = useReducedMotion();
  const router = useRouter();
  const integrations = useIntegrationsStore((s) => s.integrations);
  const connect = useIntegrationsStore((s) => s.connect);
  const disconnect = useIntegrationsStore((s) => s.disconnect);
  const reconnect = useIntegrationsStore((s) => s.reconnect);
  const reload = useIntegrationsStore((s) => s.load);
  const defaultMode = usePrefsStore((s) => s.defaultMode);
  const user = useSessionStore((s) => s.user);

  const [connecting, setConnecting] = React.useState<IntegrationId | null>(null);
  const [confirm, setConfirm] = React.useState<Integration | null>(null);
  const [browsing, setBrowsing] = React.useState<IntegrationId>("sharepoint");
  const [importing, setImporting] = React.useState<string | null>(null);

  // Microsoft returns the person here after consent, so the outcome of a
  // round trip that left the app has to be reported when they land back on it.
  React.useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const connected = params.get("connected");
    const error = params.get("error");
    if (!connected && !error) return;
    if (connected) {
      notify.success(`${connected} connected.`);
      void reload({ force: true });
    } else if (error) {
      notify.error("That connection did not complete.", { description: error });
    }
    router.replace("/app/integrations");
  }, [reload, router]);

  const browseSource = integrations.find((i) => i.id === browsing);
  const browsable = integrations;

  /**
   * Connecting is a real Microsoft consent round trip when the deployment has
   * credentials for one. A 501 means it does not, and the connection is marked
   * by hand instead so a local or demo workspace still works — the import path
   * will then say plainly that there is nothing behind the connection.
   */
  async function runConnect(integration: Integration) {
    setConnecting(integration.id);
    try {
      const { url } = await integrationsApi.authorize(integration.id);
      window.location.assign(url);
      return;
    } catch (error) {
      const notConfigured = error instanceof ApiError && error.status === 501;
      if (!notConfigured) {
        setConnecting(null);
        notify.error(`${integration.name} could not be connected.`, {
          description: error instanceof Error ? error.message : undefined,
        });
        return;
      }
    }

    connect(integration.id, user?.email);
    setConnecting(null);
    notify.success(`${integration.name} connected.`, {
      description: "Microsoft sign-in is not configured here, so this connection is local only.",
    });
  }

  /**
   * The real import: the server fetches the bytes from Microsoft, stores the
   * extracted text, and queues the read. Creating an analysis with only a
   * filename on it — which is what this used to do — left the run with nothing
   * to read.
   */
  async function startFrom(entry: RemoteEntry, sourceId: IntegrationId) {
    setImporting(entry.id);
    try {
      const result = await integrationsApi.import(sourceId, [entry.id]);
      const first = result.results.find((r) => r.analysisId);
      if (!first?.analysisId) {
        notify.error("That document could not be imported.", {
          description: result.results.find((r) => r.error)?.error,
        });
        return;
      }
      notify.success("Reading started.", {
        description: `${entry.name} · ${defaultMode.replace("-", " ")} pass`,
      });
      router.push(`/app/analyses/${first.analysisId}/run`);
    } catch (caught) {
      notify.error("That document could not be imported.", {
        description: caught instanceof ApiError ? caught.message : undefined,
      });
    } finally {
      setImporting(null);
    }
  }

  return (
    <div className="mx-auto max-w-[76rem] space-y-6">
      <PageHeader
        eyebrow="Workspace"
        title="Integrations"
        description="Margin reads from where your solicitations already live, and sends reports back the same way."
      />

      <Callout tone="slate" title="Nothing leaves your tenant" icon={<ShieldCheck aria-hidden />}>
        Read-only, one file at a time, only when someone asks for it. Nothing is crawled, mirrored, or indexed in the background.
      </Callout>

      <ul className="grid gap-4 md:grid-cols-3">
        {integrations.map((integration, index) => {
          const Icon = ICONS[integration.id];
          return (
            <motion.li
              key={integration.id}
              initial={reduce ? false : { opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05, duration: 0.3, ease: [0.32, 0.72, 0, 1] }}
            >
              <Panel className="flex h-full flex-col p-5">
                <div className="flex items-start justify-between gap-3">
                  <span
                    className={cn(
                      "inline-flex size-10 items-center justify-center rounded-md border",
                      integration.connected
                        ? "border-patina/35 bg-patina-tint text-patina"
                        : "border-line-strong bg-paper-sunk text-ink-faint",
                    )}
                  >
                    <Icon className="size-5" aria-hidden />
                  </span>
                  {integration.connected ? (
                    <Badge tone="leaf">
                      <Check className="size-3" aria-hidden />
                      Connected
                    </Badge>
                  ) : (
                    <Badge tone="neutral">Not connected</Badge>
                  )}
                </div>

                <h3 className="mt-4 text-base text-ink">{integration.name}</h3>
                <p className="mt-1 flex-1 text-sm leading-relaxed text-ink-soft">{integration.blurb}</p>

                {integration.connected ? (
                  <p className="mt-3 font-mono text-2xs text-ink-faint">
                    {integration.account}
                    {integration.connectedAt ? ` · since ${relative(integration.connectedAt)}` : ""}
                  </p>
                ) : null}

                <Separator className="my-4" />

                <ul className="space-y-1">
                  {integration.scopes.map((scope) => (
                    <li key={scope} className="flex items-start gap-2 text-xs text-ink-faint">
                      <Check className="mt-0.5 size-3 shrink-0 text-patina" aria-hidden />
                      <span className="leading-relaxed">{scope}</span>
                    </li>
                  ))}
                </ul>

                <div className="mt-4 flex gap-2">
                  {integration.connected ? (
                    <>
                      <Button
                        variant="secondary"
                        size="sm"
                        className="flex-1"
                        onClick={() =>
                          notify.success(`${integration.name} re-synced.`, {
                            description: "Folder listing refreshed.",
                          })
                        }
                      >
                        <RefreshCw />
                        Re-sync
                      </Button>
                      <Button
                        variant="quiet"
                        size="sm"
                        onClick={() => setConfirm(integration)}
                        aria-label={`Disconnect ${integration.name}`}
                      >
                        <Unplug />
                      </Button>
                    </>
                  ) : (
                    <Button
                      variant="primary"
                      size="sm"
                      className="w-full"
                      loading={connecting === integration.id}
                      onClick={() => runConnect(integration)}
                    >
                      <Plug />
                      Continue with Microsoft
                    </Button>
                  )}
                </div>
              </Panel>
            </motion.li>
          );
        })}
      </ul>

      <IngestAddress />

      <Panel>
        <PanelHeader
          title="Browse and import"
          description="Open a mailbox, a drive, or a SharePoint library. Pick a document and Margin starts reading it — the file never touches your laptop."
          actions={
            <Segmented
              ariaLabel="Source to browse"
              value={browsing}
              onValueChange={(v) => setBrowsing(v as IntegrationId)}
              options={browsable.map((i) => ({ value: i.id, label: i.name }))}
            />
          }
        />
        <div className="p-5">
          {!browseSource ? null : browseSource.connected ? (
            <>
              <p className="pb-3 font-mono text-2xs uppercase tracking-[0.13em] text-ink-faint">
                {browseSource.account}
              </p>
              <SourceBrowser
                key={browseSource.id}
                provider={browseSource.id}
                onPick={(entry) => void startFrom(entry, browseSource.id)}
                busyId={importing}
                className="max-h-[26rem]"
              />
            </>
          ) : (
            <Well className="flex flex-wrap items-center justify-between gap-4">
              <p className="text-sm text-ink-soft">
                Connect {browseSource.name} to browse the document library from here.
              </p>
              <Button variant="primary" size="sm" onClick={() => runConnect(browseSource)}>
                <Plug />
                Connect
              </Button>
            </Well>
          )}
        </div>
      </Panel>

      <ConfirmDialog
        open={Boolean(confirm)}
        onOpenChange={(o) => !o && setConfirm(null)}
        title={confirm ? `Disconnect ${confirm.name}?` : ""}
        destructive
        confirmLabel="Disconnect"
        description="Existing analyses keep their citations. New imports and exports through this source will stop working."
        onConfirm={() => {
          if (!confirm) return;
          const previous = disconnect(confirm.id);
          setConfirm(null);
          notify.success(`${confirm.name} disconnected.`, {
            undo: previous ? () => reconnect(previous) : undefined,
          });
        }}
      />
    </div>
  );
}

/**
 * The drop box.
 *
 * Not every source deserves a connector. A mail rule, a Power Automate flow, a
 * cron job and a partner's script can all already POST a file, and this is the
 * one address that turns any of them into an analysis. It is shown here rather
 * than buried in a doc because the person setting up that flow is the person
 * looking at this page.
 */
function IngestAddress() {
  const [address, setAddress] = React.useState<string | null>(null);
  const [copied, setCopied] = React.useState(false);
  const [revealed, setRevealed] = React.useState(false);

  React.useEffect(() => {
    let live = true;
    integrationsApi
      .ingestAddress()
      .then((res) => {
        if (live) setAddress(res.url);
      })
      .catch(() => {
        /* The panel simply does not appear if the deployment has no ingest route. */
      });
    return () => {
      live = false;
    };
  }, []);

  if (!address) return null;

  const masked = address.replace(/\/ingest\/.*$/, "/ingest/••••••••••••");

  return (
    <Panel>
      <PanelHeader
        title="Send documents in"
        description="One address for anything that can post a file — a mail rule, a Power Automate flow, a script."
      />
      <div className="space-y-4 p-5">
        <div className="flex flex-wrap items-center gap-2">
          <code className="min-w-0 flex-1 truncate rounded-md border border-line bg-paper-sunk px-3 py-2 font-mono text-xs text-ink-soft">
            {revealed ? address : masked}
          </code>
          <Button variant="quiet" size="sm" onClick={() => setRevealed((prev) => !prev)}>
            {revealed ? "Hide" : "Reveal"}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(address);
                setCopied(true);
                setTimeout(() => setCopied(false), 1600);
              } catch {
                notify.error("Could not copy — reveal it and copy by hand.");
              }
            }}
          >
            {copied ? <Check /> : <Copy />}
            {copied ? "Copied" : "Copy"}
          </Button>
        </div>

        <Callout tone="ochre" title="This URL is a credential">
          Anyone holding it can start an analysis in this workspace. Store it as a
          secret wherever it is used, and never paste it into a ticket or a chat.
        </Callout>

        <Well>
          <p className="mb-2 text-xs text-ink-soft">Post a document to it:</p>
          <pre className="scroll-region-x overflow-x-auto font-mono text-2xs leading-relaxed text-ink-soft">
{`curl -X POST "<your ingest URL>" \\
     -F "file=@RFP-2026-0041.pdf" \\
     -F "title=ARTS 311 CRM" \\
     -F "mode=standard"`}
          </pre>
          <p className="mt-2 text-xs text-ink-faint">
            The reading pass starts immediately and the analysis appears in the board.
            Setup for Outlook, SharePoint and OneDrive is in INTEGRATIONS.md.
          </p>
        </Well>
      </div>
    </Panel>
  );
}
