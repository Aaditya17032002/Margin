"use client";

import * as React from "react";
import { motion, useReducedMotion } from "motion/react";
import { Check, CloudUpload, FolderTree, Mail, Plug, RefreshCw, ShieldCheck, Unplug } from "lucide-react";

import { cn } from "@/lib/utils";
import { relative } from "@/lib/dates";
import { Button } from "@/components/ui/button";
import { PageHeader, Panel, PanelHeader, Separator, Well } from "@/components/ui/surface";
import { Badge } from "@/components/ui/badge";
import { Segmented } from "@/components/ui/controls";
import { Callout } from "@/components/ui/feedback";
import { ConfirmDialog } from "@/components/ui/overlay";
import { notify } from "@/components/ui/toaster";
import { FileTree } from "@/components/shell/import-picker";
import { useIntegrationsStore, usePrefsStore } from "@/stores/workspace";
import { useAnalysesStore } from "@/stores/analyses";
import { useSessionStore } from "@/stores/session";
import { useRouter } from "next/navigation";
import type { FileNode, Integration, IntegrationId } from "@/types";

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
  const createAnalysis = useAnalysesStore((s) => s.createAnalysis);
  const defaultMode = usePrefsStore((s) => s.defaultMode);
  const user = useSessionStore((s) => s.user);

  const [connecting, setConnecting] = React.useState<IntegrationId | null>(null);
  const [confirm, setConfirm] = React.useState<Integration | null>(null);
  const [browsing, setBrowsing] = React.useState<IntegrationId>("sharepoint");

  const browseSource = integrations.find((i) => i.id === browsing);
  const browsable = integrations.filter((i) => i.id !== "outlook");

  /** The Microsoft handshake is theatre here, but it should still take a beat. */
  async function runConnect(integration: Integration) {
    setConnecting(integration.id);
    await new Promise((r) => setTimeout(r, 900));
    connect(integration.id, user?.email);
    setConnecting(null);
    notify.success(`${integration.name} connected.`, {
      description: `Signed in as ${user?.email ?? "a.osei@thornfield.co"}.`,
    });
  }

  function startFrom(file: FileNode, sourceId: IntegrationId) {
    const id = createAnalysis({
      title: file.name.replace(/\.[^.]+$/, "").replace(/[_-]/g, " "),
      agency: "Pending intake",
      mode: defaultMode,
      fileName: file.name,
      fileSize: file.size ?? 0,
      source: sourceId,
      owner: user?.name ?? "Amara Osei",
    });
    notify.success("Import started.", { description: file.name });
    router.push(`/app/analyses/${id}/run`);
  }

  return (
    <div className="mx-auto max-w-[76rem] space-y-6">
      <PageHeader
        eyebrow="Workspace"
        title="Integrations"
        description="Margin reads from where your solicitations already live, and sends reports back the same way."
      />

      <Callout tone="slate" title="Nothing leaves your tenant" icon={<ShieldCheck aria-hidden />}>
        Documents are read in place. Margin stores citations and findings, never a second copy of the file.
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

      <Panel>
        <PanelHeader
          title="Browse and import"
          description="Pick a file and Margin starts reading it straight away."
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
              <FileTree nodes={browseSource.tree} onPick={(node) => startFrom(node, browseSource.id)} />
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
