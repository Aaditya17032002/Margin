"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { motion, useReducedMotion } from "motion/react";
import { ArrowRight, Check, FolderOpen, Mail } from "lucide-react";

import { cn } from "@/lib/utils";
import { listItem, staggerList } from "@/lib/motion";
import { MODES } from "@/data/agents";
import { Button } from "@/components/ui/button";
import { PageHeader, Panel, PanelHeader, Well } from "@/components/ui/surface";
import { Dropzone, type DroppedFile } from "@/components/ui/dropzone";
import { Field, Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/controls";
import { Callout } from "@/components/ui/feedback";
import { notify } from "@/components/ui/toaster";
import { AGENT_BY_ID } from "@/data/agents";
import { useAnalysesStore } from "@/stores/analyses";
import { usePrefsStore, useIntegrationsStore } from "@/stores/workspace";
import { useSessionStore } from "@/stores/session";
import { useUIStore } from "@/stores/ui";
import type { AnalysisMode, DocType } from "@/types";

const DOC_TYPES: DocType[] = ["RFP", "RFI", "RFQ", "IFB", "Sources Sought", "BAA", "Task Order"];

export function NewAnalysisView() {
  const router = useRouter();
  const reduce = useReducedMotion();
  const defaultMode = usePrefsStore((s) => s.defaultMode);
  const createAnalysis = useAnalysesStore((s) => s.createAnalysis);
  const user = useSessionStore((s) => s.user);
  const integrations = useIntegrationsStore((s) => s.integrations);
  const setImportOpen = useUIStore((s) => s.setImportOpen);

  const [files, setFiles] = React.useState<DroppedFile[]>([]);
  const [mode, setMode] = React.useState<AnalysisMode>(defaultMode);
  const [title, setTitle] = React.useState("");
  const [agency, setAgency] = React.useState("");
  const [number, setNumber] = React.useState("");
  const [docType, setDocType] = React.useState<DocType>("RFP");
  const [submitting, setSubmitting] = React.useState(false);

  /** The file name is a decent first draft of the title, until somebody types one. */
  function acceptFiles(next: DroppedFile[]) {
    setFiles(next);
    if (next.length && !title.trim()) {
      setTitle(next[0].name.replace(/\.[^.]+$/, "").replace(/[_-]/g, " "));
    }
  }

  const selectedMode = MODES.find((m) => m.id === mode)!;
  const ready = files.length > 0 && title.trim().length > 1;

  async function start() {
    if (!ready) return;
    setSubmitting(true);
    const id = createAnalysis({
      title: title.trim(),
      agency: agency.trim() || "Pending intake",
      solicitationNumber: number.trim() || undefined,
      docType,
      mode,
      fileName: files[0].name,
      fileSize: files[0].size,
      source: "upload",
      owner: user?.name ?? "Amara Osei",
    });
    notify.success("Reading has started.", { description: `${selectedMode.name} pass over ${files[0].name}.` });
    router.push(`/app/analyses/${id}/run`);
  }

  const connected = integrations.filter((i) => i.connected);

  return (
    <div className="mx-auto max-w-[68rem] space-y-7">
      <PageHeader
        eyebrow="New analysis"
        title="Give Margin something to read"
        description="Upload the solicitation, or pull it straight from a connected source. Amendments can be layered on afterwards."
      />

      <div className="grid gap-6 lg:grid-cols-[1.25fr_1fr]">
        <div className="space-y-6">
          <Panel>
            <PanelHeader title="The document" description="One solicitation per analysis. Attachments are welcome." />
            <div className="space-y-5 px-5 py-5">
              <Dropzone files={files} onFilesChange={acceptFiles} />

              {connected.length > 0 ? (
                <div className="flex flex-wrap items-center gap-2 border-t border-line pt-4">
                  <span className="text-sm text-ink-soft">Or import from</span>
                  {connected.map((integration) => (
                    <Button key={integration.id} variant="secondary" size="sm" onClick={() => setImportOpen(true)}>
                      {integration.id === "outlook" ? <Mail /> : <FolderOpen />}
                      {integration.name}
                    </Button>
                  ))}
                </div>
              ) : (
                <Callout tone="slate" title="No sources connected">
                  Connect Outlook or SharePoint and solicitations can be analysed without ever leaving the inbox.
                </Callout>
              )}
            </div>
          </Panel>

          <Panel>
            <PanelHeader title="What we already know" description="Anything left blank is filled in by the Intake pass." />
            <div className="grid gap-4 px-5 py-5 sm:grid-cols-2">
              <Field label="Title" htmlFor="new-title" required className="sm:col-span-2">
                <Input
                  id="new-title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Statewide Digital Learning Platform"
                />
              </Field>
              <Field label="Agency" htmlFor="new-agency">
                <Input
                  id="new-agency"
                  value={agency}
                  onChange={(e) => setAgency(e.target.value)}
                  placeholder="Texas Education Agency"
                />
              </Field>
              <Field label="Solicitation number" htmlFor="new-number">
                <Input
                  id="new-number"
                  value={number}
                  onChange={(e) => setNumber(e.target.value)}
                  placeholder="TEA-2026-DLP-114"
                  className="font-mono"
                />
              </Field>
              <Field label="Document type">
                <Select value={docType} onValueChange={(v) => setDocType(v as DocType)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DOC_TYPES.map((type) => (
                      <SelectItem key={type} value={type}>
                        {type}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
            </div>
          </Panel>
        </div>

        <div className="space-y-6">
          <Panel>
            <PanelHeader title="How deep should it read?" description="Every mode cites; they differ in how much they chase." />
            <motion.div
              variants={staggerList(0.03)}
              initial={reduce ? false : "hidden"}
              animate="visible"
              role="radiogroup"
              aria-label="Analysis mode"
              className="divide-y divide-[var(--line)]"
            >
              {MODES.map((option) => {
                const active = option.id === mode;
                return (
                  <motion.button
                    key={option.id}
                    variants={listItem}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={() => setMode(option.id)}
                    className={cn(
                      "flex w-full items-start gap-3 px-5 py-3.5 text-left transition-colors duration-150",
                      active ? "bg-patina-tint" : "hover:bg-paper-sunk",
                    )}
                  >
                    <span
                      className={cn(
                        "mt-1 flex size-4 shrink-0 items-center justify-center rounded-full border transition-colors duration-150",
                        active ? "border-patina bg-patina" : "border-line-strong bg-paper-sunk",
                      )}
                      aria-hidden
                    >
                      {active ? <Check className="size-2.5 text-[var(--patina-ink)]" strokeWidth={3.5} /> : null}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="flex items-baseline justify-between gap-3">
                        <span className={cn("text-sm font-medium", active ? "text-patina" : "text-ink")}>
                          {option.name}
                        </span>
                        <span className="shrink-0 font-mono text-2xs text-ink-faint">{option.minutes}</span>
                      </span>
                      <span className="mt-0.5 block text-sm leading-relaxed text-ink-soft">{option.blurb}</span>
                    </span>
                  </motion.button>
                );
              })}
            </motion.div>
          </Panel>

          <Well className="space-y-3">
            <p className="eyebrow">Who will read it</p>
            <ul className="flex flex-wrap gap-1.5">
              {selectedMode.agents.map((agentId) => (
                <li
                  key={agentId}
                  className="rounded-sm border border-line-strong bg-paper-raised px-2 py-0.5 font-mono text-2xs text-ink-soft"
                >
                  {AGENT_BY_ID[agentId].name}
                </li>
              ))}
            </ul>
            <p className="text-xs leading-relaxed text-ink-faint">
              {selectedMode.passes} · every finding is checked against its clause by the Verifier before it reaches you.
            </p>
          </Well>

          <Button variant="primary" size="lg" className="w-full" disabled={!ready} loading={submitting} onClick={start}>
            Start reading
            <ArrowRight />
          </Button>
          {!ready ? (
            <p className="text-center text-xs text-ink-faint">
              Add a document and a title to begin.
            </p>
          ) : null}
        </div>
      </div>
    </div>
  );
}
