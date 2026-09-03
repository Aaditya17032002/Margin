"use client";

import * as React from "react";
import Link from "next/link";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { CloudUpload, Download, FileText, Mail, RotateCcw, Trash2 } from "lucide-react";

import { formatBytes, pluralize } from "@/lib/utils";
import { relative } from "@/lib/dates";
import { Button } from "@/components/ui/button";
import { PageHeader, Panel, PanelHeader, Well } from "@/components/ui/surface";
import { Badge } from "@/components/ui/badge";
import { Field } from "@/components/ui/input";
import { Progress, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/controls";
import { Table, TableFrame, Td, Th, Tr } from "@/components/ui/table";
import { EmptyState } from "@/components/ui/feedback";
import { notify } from "@/components/ui/toaster";
import { useAnalysesStore } from "@/stores/analyses";
import { useIntegrationsStore, useReportsStore, useTemplatesStore } from "@/stores/workspace";
import type { ExportRecord } from "@/types";

const DESTINATION_COPY: Record<ExportRecord["destination"], string> = {
  download: "Download",
  onedrive: "OneDrive",
  outlook: "Outlook",
};

const STATUS_TONE: Record<ExportRecord["status"], "leaf" | "ochre" | "seal"> = {
  ready: "leaf",
  generating: "ochre",
  failed: "seal",
};

export function ReportsView() {
  const reduce = useReducedMotion();
  const analyses = useAnalysesStore((s) => s.analyses);
  const allTemplates = useTemplatesStore((s) => s.templates);
  const templates = allTemplates.filter((t) => t.kind === "report");
  const recordUse = useTemplatesStore((s) => s.recordUse);
  const exports = useReportsStore((s) => s.exports);
  const addExport = useReportsStore((s) => s.addExport);
  const updateExport = useReportsStore((s) => s.updateExport);
  const deleteExport = useReportsStore((s) => s.deleteExport);
  const restoreExport = useReportsStore((s) => s.restoreExport);
  const log = useReportsStore((s) => s.log);
  const integrations = useIntegrationsStore((s) => s.integrations);

  // Null means "whatever is first once the stores have rehydrated", which keeps
  // the selects populated without an effect chasing the store.
  const [chosenAnalysis, setChosenAnalysis] = React.useState<string | null>(null);
  const [chosenTemplate, setChosenTemplate] = React.useState<string | null>(null);
  const [format, setFormat] = React.useState<ExportRecord["format"]>("DOCX");
  const [destination, setDestination] = React.useState<ExportRecord["destination"]>("download");
  const [progress, setProgress] = React.useState<number | null>(null);

  const analysisId = chosenAnalysis ?? analyses[0]?.id ?? "";
  const templateId = chosenTemplate ?? templates[0]?.id ?? "";
  const setAnalysisId = setChosenAnalysis;
  const setTemplateId = setChosenTemplate;

  const analysis = analyses.find((a) => a.id === analysisId);
  const template = templates.find((t) => t.id === templateId);
  const oneDrive = integrations.find((i) => i.id === "onedrive");
  const outlook = integrations.find((i) => i.id === "outlook");

  const destinationBlocked =
    (destination === "onedrive" && !oneDrive?.connected) || (destination === "outlook" && !outlook?.connected);

  /** The generation is fake, but the wait is honest: a report takes a moment. */
  async function generate() {
    if (!analysis || !template || progress !== null) return;
    setProgress(0);
    const id = addExport({
      analysisId: analysis.id,
      analysisTitle: analysis.title,
      templateName: template.name,
      format,
      size: 0,
      destination,
      status: "generating",
    });

    for (const step of [18, 42, 68, 88, 100]) {
      await new Promise((r) => setTimeout(r, 260 + Math.random() * 220));
      setProgress(step);
    }

    updateExport(id, {
      status: "ready",
      size: 180_000 + template.sections.length * 24_000 + analysis.pageCount * 900,
    });
    recordUse(template.id);
    log({
      actor: "You",
      action: `generated ${template.name} for`,
      target: analysis.solicitationNumber,
      analysisId: analysis.id,
    });
    setProgress(null);

    notify.success("Report ready.", {
      description: `${template.name} · ${format} · ${DESTINATION_COPY[destination]}`,
      action: {
        label: destination === "outlook" ? "Open in Outlook" : "Download",
        onClick: () => notify.info(destination === "outlook" ? "Opening Outlook…" : "Download started."),
      },
    });
  }

  return (
    <div className="mx-auto max-w-[76rem] space-y-6">
      <PageHeader
        eyebrow="Export"
        title="Reports"
        description="Turn an analysis into the document your reviewers actually read."
      />

      <div className="grid gap-6 lg:grid-cols-[22rem_1fr]">
        <Panel className="p-5 lg:sticky lg:top-20 lg:self-start">
          <h2 className="text-lg text-ink">Generate</h2>
          <p className="mt-0.5 text-sm text-ink-soft">Every citation travels with the text.</p>

          <div className="mt-5 space-y-4">
            <Field label="Analysis" htmlFor="rep-analysis">
              <Select value={analysisId} onValueChange={setAnalysisId}>
                <SelectTrigger id="rep-analysis">
                  <SelectValue placeholder="Choose an analysis" />
                </SelectTrigger>
                <SelectContent>
                  {analyses.map((a) => (
                    <SelectItem key={a.id} value={a.id}>
                      {a.solicitationNumber} · {a.agency}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            <Field label="Template" htmlFor="rep-template">
              <Select value={templateId} onValueChange={setTemplateId}>
                <SelectTrigger id="rep-template">
                  <SelectValue placeholder="Choose a template" />
                </SelectTrigger>
                <SelectContent>
                  {templates.map((t) => (
                    <SelectItem key={t.id} value={t.id}>
                      {t.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Format" htmlFor="rep-format">
                <Select value={format} onValueChange={(v) => setFormat(v as ExportRecord["format"])}>
                  <SelectTrigger id="rep-format">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="DOCX">DOCX</SelectItem>
                    <SelectItem value="PDF">PDF</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
              <Field label="Destination" htmlFor="rep-dest">
                <Select
                  value={destination}
                  onValueChange={(v) => setDestination(v as ExportRecord["destination"])}
                >
                  <SelectTrigger id="rep-dest">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="download">Download</SelectItem>
                    <SelectItem value="onedrive">OneDrive</SelectItem>
                    <SelectItem value="outlook">Email via Outlook</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
            </div>

            {template ? (
              <Well className="space-y-2">
                <p className="eyebrow">Contents</p>
                <ol className="space-y-1">
                  {template.sections.map((section, i) => (
                    <li key={section} className="flex items-baseline gap-2.5 text-xs text-ink-soft">
                      <span className="font-mono text-2xs text-ink-faint tabular">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <span className="truncate">{section}</span>
                    </li>
                  ))}
                </ol>
              </Well>
            ) : null}

            {destinationBlocked ? (
              <p className="text-xs text-ochre">
                {destination === "onedrive" ? "OneDrive" : "Outlook"} is not connected.{" "}
                <Link href="/app/integrations" className="underline underline-offset-2">
                  Connect it
                </Link>{" "}
                to send there.
              </p>
            ) : null}

            <AnimatePresence>
              {progress !== null ? (
                <motion.div
                  initial={reduce ? { opacity: 0 } : { opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="space-y-2 overflow-hidden"
                >
                  <Progress value={progress} label="Generating report" />
                  <p className="font-mono text-2xs text-ink-faint tabular">
                    Composing sections · {progress}%
                  </p>
                </motion.div>
              ) : null}
            </AnimatePresence>

            <Button
              variant="primary"
              className="w-full"
              onClick={generate}
              loading={progress !== null}
              disabled={!analysis || !template || destinationBlocked}
            >
              <FileText />
              Generate report
            </Button>
          </div>
        </Panel>

        <Panel>
          <PanelHeader
            title="Export history"
            description={pluralize(exports.length, "report")}
          />
          {exports.length === 0 ? (
            <div className="p-5">
              <EmptyState
                title="No exports yet"
                description="Generate a report and it will be listed here with everything needed to find it again."
              />
            </div>
          ) : (
            <TableFrame className="border-0">
              <Table>
                <thead>
                  <tr>
                    <Th>Report</Th>
                    <Th className="hidden md:table-cell">Template</Th>
                    <Th className="hidden sm:table-cell">Destination</Th>
                    <Th>Status</Th>
                    <Th className="text-right">Actions</Th>
                  </tr>
                </thead>
                <tbody>
                  {exports.map((record) => (
                    <Tr key={record.id}>
                      <Td>
                        <div className="min-w-0 space-y-0.5">
                          <Link
                            href={`/app/analyses/${record.analysisId}`}
                            className="block truncate text-sm text-ink underline-offset-4 hover:underline"
                          >
                            {record.analysisTitle}
                          </Link>
                          <p className="font-mono text-2xs text-ink-faint tabular">
                            {record.format} · {record.size ? formatBytes(record.size) : "—"} · {relative(record.at)}
                          </p>
                        </div>
                      </Td>
                      <Td className="hidden md:table-cell">
                        <span className="text-sm text-ink-soft">{record.templateName}</span>
                      </Td>
                      <Td className="hidden sm:table-cell">
                        <span className="inline-flex items-center gap-1.5 text-sm text-ink-soft">
                          {record.destination === "onedrive" ? (
                            <CloudUpload className="size-3.5 text-ink-faint" aria-hidden />
                          ) : record.destination === "outlook" ? (
                            <Mail className="size-3.5 text-ink-faint" aria-hidden />
                          ) : (
                            <Download className="size-3.5 text-ink-faint" aria-hidden />
                          )}
                          {DESTINATION_COPY[record.destination]}
                        </span>
                      </Td>
                      <Td>
                        <Badge tone={STATUS_TONE[record.status]}>
                          {record.status === "ready"
                            ? "Ready"
                            : record.status === "generating"
                              ? "Generating"
                              : "Failed"}
                        </Badge>
                      </Td>
                      <Td>
                        <div className="flex items-center justify-end gap-1">
                          {record.status === "failed" ? (
                            <Button
                              variant="quiet"
                              size="iconSm"
                              aria-label="Retry export"
                              onClick={() => {
                                updateExport(record.id, { status: "ready" });
                                notify.success("Report regenerated.");
                              }}
                            >
                              <RotateCcw />
                            </Button>
                          ) : (
                            <Button
                              variant="quiet"
                              size="iconSm"
                              aria-label={`Download ${record.analysisTitle}`}
                              onClick={() => notify.info("Download started.")}
                            >
                              <Download />
                            </Button>
                          )}
                          <Button
                            variant="quiet"
                            size="iconSm"
                            aria-label={`Delete export of ${record.analysisTitle}`}
                            onClick={() => {
                              const removed = deleteExport(record.id);
                              if (removed) {
                                notify.success("Export removed.", { undo: () => restoreExport(removed) });
                              }
                            }}
                          >
                            <Trash2 />
                          </Button>
                        </div>
                      </Td>
                    </Tr>
                  ))}
                </tbody>
              </Table>
            </TableFrame>
          )}
        </Panel>
      </div>
    </div>
  );
}
