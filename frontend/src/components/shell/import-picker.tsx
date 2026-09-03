"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { ChevronRight, FileText, Folder, FolderOpen, Plug } from "lucide-react";

import { cn, formatBytes } from "@/lib/utils";
import { relative } from "@/lib/dates";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Segmented } from "@/components/ui/controls";
import { EmptyState } from "@/components/ui/feedback";
import { notify } from "@/components/ui/toaster";
import { useIntegrationsStore } from "@/stores/workspace";
import { useAnalysesStore } from "@/stores/analyses";
import { useSessionStore } from "@/stores/session";
import { usePrefsStore } from "@/stores/workspace";
import { useUIStore } from "@/stores/ui";
import type { FileNode, IntegrationId } from "@/types";

export function ImportPicker() {
  const open = useUIStore((s) => s.importOpen);
  const setOpen = useUIStore((s) => s.setImportOpen);
  const integrations = useIntegrationsStore((s) => s.integrations);
  const connect = useIntegrationsStore((s) => s.connect);
  const createAnalysis = useAnalysesStore((s) => s.createAnalysis);
  const defaultMode = usePrefsStore((s) => s.defaultMode);
  const user = useSessionStore((s) => s.user);
  const router = useRouter();

  const [sourceId, setSourceId] = React.useState<IntegrationId>("sharepoint");
  const source = integrations.find((i) => i.id === sourceId);

  function startFrom(file: FileNode) {
    const id = createAnalysis({
      title: file.name.replace(/\.[^.]+$/, "").replace(/[_-]/g, " "),
      agency: "Pending intake",
      mode: defaultMode,
      fileName: file.name,
      fileSize: file.size ?? 0,
      source: sourceId,
      owner: user?.name ?? "Amara Osei",
    });
    setOpen(false);
    notify.success("Import started.", { description: `${file.name} is queued for a ${defaultMode.replace("-", " ")} read.` });
    router.push(`/app/analyses/${id}/run`);
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetContent
        title="Import a solicitation"
        description="Browse a connected source and start the read without downloading anything."
      >
        <Segmented
          ariaLabel="Import source"
          value={sourceId}
          onValueChange={(v) => setSourceId(v as IntegrationId)}
          options={integrations.map((i) => ({ value: i.id, label: i.name }))}
          className="mb-5"
        />

        {!source ? null : !source.connected ? (
          <EmptyState
            title={`${source.name} isn't connected`}
            description={source.blurb}
            action={
              <Button
                variant="primary"
                onClick={() => {
                  connect(source.id);
                  notify.success(`${source.name} connected.`);
                }}
              >
                <Plug />
                Connect {source.name}
              </Button>
            }
          />
        ) : (
          <div className="space-y-1">
            <p className="pb-2 font-mono text-2xs uppercase tracking-[0.13em] text-ink-faint">
              {source.account}
            </p>
            <FileTree nodes={source.tree} onPick={startFrom} />
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}

export function FileTree({
  nodes,
  onPick,
  depth = 0,
}: {
  nodes: FileNode[];
  onPick: (node: FileNode) => void;
  depth?: number;
}) {
  return (
    <ul className={cn("space-y-0.5", depth > 0 && "ml-4 border-l border-line pl-3")}>
      {nodes.map((node) => (
        <FileNodeRow key={node.id} node={node} onPick={onPick} depth={depth} />
      ))}
    </ul>
  );
}

function FileNodeRow({
  node,
  onPick,
  depth,
}: {
  node: FileNode;
  onPick: (node: FileNode) => void;
  depth: number;
}) {
  const [open, setOpen] = React.useState(depth === 0);

  if (node.kind === "folder") {
    return (
      <li>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-ink-soft transition-colors duration-150 hover:bg-paper-sunk hover:text-ink"
        >
          <ChevronRight
            className={cn(
              "size-3.5 shrink-0 text-ink-faint transition-transform duration-200 ease-[cubic-bezier(0.32,0.72,0,1)]",
              open && "rotate-90",
            )}
            aria-hidden
          />
          {open ? (
            <FolderOpen className="size-4 shrink-0 text-ochre" aria-hidden />
          ) : (
            <Folder className="size-4 shrink-0 text-ink-faint" aria-hidden />
          )}
          <span className="truncate">{node.name}</span>
        </button>
        {open && node.children ? <FileTree nodes={node.children} onPick={onPick} depth={depth + 1} /> : null}
      </li>
    );
  }

  return (
    <li>
      <button
        type="button"
        onClick={() => onPick(node)}
        className="group flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm text-ink-soft transition-colors duration-150 hover:bg-paper-sunk hover:text-ink"
      >
        <span className="w-3.5 shrink-0" aria-hidden />
        <FileText className="size-4 shrink-0 text-ink-faint" aria-hidden />
        <span className="min-w-0 flex-1 truncate">{node.name}</span>
        {node.size ? (
          <span className="shrink-0 font-mono text-2xs text-ink-faint">{formatBytes(node.size)}</span>
        ) : null}
        {node.modified ? (
          <span className="hidden shrink-0 text-2xs text-ink-faint sm:inline">{relative(node.modified)}</span>
        ) : null}
        <span className="shrink-0 text-2xs font-medium text-patina opacity-0 transition-opacity duration-150 group-hover:opacity-100">
          Analyse
        </span>
      </button>
    </li>
  );
}
