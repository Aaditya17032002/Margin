"use client";

import * as React from "react";
import { motion, useReducedMotion } from "motion/react";
import { Copy, Eye, FileStack, MoreHorizontal, Pencil, Plus, Trash2 } from "lucide-react";

import { cn } from "@/lib/utils";
import { relative } from "@/lib/dates";
import { Button } from "@/components/ui/button";
import { PageHeader, Panel, Separator } from "@/components/ui/surface";
import { Badge } from "@/components/ui/badge";
import { Field, Input, SearchField, Textarea } from "@/components/ui/input";
import { Segmented, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, TagsInput } from "@/components/ui/controls";
import {
  ConfirmDialog,
  Dialog,
  DialogContent,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/overlay";
import { EmptyState } from "@/components/ui/feedback";
import { notify } from "@/components/ui/toaster";
import { useTemplatesStore } from "@/stores/workspace";
import type { Template } from "@/types";

const KIND_COPY: Record<Template["kind"], { label: string; tone: "patina" | "slate" | "ochre" }> = {
  report: { label: "Report", tone: "patina" },
  boilerplate: { label: "Boilerplate", tone: "slate" },
  dpa: { label: "DPA clause set", tone: "ochre" },
};

type Draft = {
  name: string;
  kind: Template["kind"];
  description: string;
  format: Template["format"];
  sections: string[];
};

const emptyDraft: Draft = {
  name: "",
  kind: "report",
  description: "",
  format: "DOCX",
  sections: [],
};

export function TemplatesView() {
  const reduce = useReducedMotion();
  const templates = useTemplatesStore((s) => s.templates);
  const addTemplate = useTemplatesStore((s) => s.addTemplate);
  const updateTemplate = useTemplatesStore((s) => s.updateTemplate);
  const deleteTemplate = useTemplatesStore((s) => s.deleteTemplate);
  const restoreTemplate = useTemplatesStore((s) => s.restoreTemplate);
  const duplicateTemplate = useTemplatesStore((s) => s.duplicateTemplate);

  const [query, setQuery] = React.useState("");
  const [kind, setKind] = React.useState<string>("all");
  const [editing, setEditing] = React.useState<Template | null>(null);
  const [open, setOpen] = React.useState(false);
  const [draft, setDraft] = React.useState<Draft>(emptyDraft);
  const [preview, setPreview] = React.useState<Template | null>(null);
  const [confirm, setConfirm] = React.useState<Template | null>(null);

  const filtered = templates.filter((template) => {
    if (kind !== "all" && template.kind !== kind) return false;
    if (!query.trim()) return true;
    const q = query.toLowerCase();
    return [template.name, template.description, ...template.sections].join(" ").toLowerCase().includes(q);
  });

  function openCreate() {
    setDraft(emptyDraft);
    setEditing(null);
    setOpen(true);
  }

  function openEdit(template: Template) {
    setDraft({
      name: template.name,
      kind: template.kind,
      description: template.description,
      format: template.format,
      sections: template.sections,
    });
    setEditing(template);
    setOpen(true);
  }

  function save() {
    const payload = {
      name: draft.name.trim(),
      kind: draft.kind,
      description: draft.description.trim(),
      format: draft.format,
      sections: draft.sections,
    };
    if (editing) {
      updateTemplate(editing.id, payload);
      notify.success("Template saved.");
    } else {
      addTemplate(payload);
      notify.success("Template created.");
    }
    setOpen(false);
    setEditing(null);
  }

  return (
    <div className="mx-auto max-w-[76rem] space-y-6">
      <PageHeader
        eyebrow="Library"
        title="Templates"
        description="The shapes your reports take, and the boilerplate you stop rewriting."
        actions={
          <Button variant="primary" onClick={openCreate}>
            <Plus />
            New template
          </Button>
        }
      />

      <div className="flex flex-wrap items-center gap-3">
        <SearchField
          value={query}
          onValueChange={setQuery}
          placeholder="Search templates…"
          className="w-full max-w-sm"
        />
        <Segmented
          ariaLabel="Filter by kind"
          value={kind}
          onValueChange={setKind}
          options={[
            { value: "all", label: "All" },
            { value: "report", label: "Reports" },
            { value: "boilerplate", label: "Boilerplate" },
            { value: "dpa", label: "DPA" },
          ]}
        />
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          illustration={<FileStack className="size-7 text-patina" aria-hidden />}
          title={templates.length === 0 ? "No templates yet" : "Nothing matches"}
          description={
            templates.length === 0
              ? "Templates decide what an exported report contains and in what order. Start from a blank one and add sections."
              : "Try another phrase, or show every kind."
          }
          action={
            <Button variant="primary" onClick={openCreate}>
              <Plus />
              New template
            </Button>
          }
        />
      ) : (
        <ul className="grid gap-4 md:grid-cols-2">
          {filtered.map((template, index) => (
            <motion.li
              key={template.id}
              initial={reduce ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: Math.min(index * 0.035, 0.24), duration: 0.26, ease: [0.32, 0.72, 0, 1] }}
            >
              <Panel className="flex h-full flex-col p-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone={KIND_COPY[template.kind].tone}>{KIND_COPY[template.kind].label}</Badge>
                      <Badge tone="neutral" shape="mono">
                        {template.format}
                      </Badge>
                    </div>
                    <h3 className="text-base leading-snug text-ink">{template.name}</h3>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="quiet" size="iconSm" aria-label={`Actions for ${template.name}`}>
                        <MoreHorizontal />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onSelect={() => setPreview(template)}>
                        <Eye />
                        Preview
                      </DropdownMenuItem>
                      <DropdownMenuItem onSelect={() => openEdit(template)}>
                        <Pencil />
                        Edit
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onSelect={() => {
                          duplicateTemplate(template.id);
                          notify.success("Template duplicated.");
                        }}
                      >
                        <Copy />
                        Duplicate
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem destructive onSelect={() => setConfirm(template)}>
                        <Trash2 />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>

                <p className="mt-2 text-sm leading-relaxed text-ink-soft">{template.description}</p>

                <Separator className="my-4" />

                <ol className="flex-1 space-y-1">
                  {template.sections.slice(0, 5).map((section, i) => (
                    <li key={section} className="flex items-baseline gap-2.5 text-sm text-ink-soft">
                      <span className="font-mono text-2xs text-ink-faint tabular">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <span className="truncate">{section}</span>
                    </li>
                  ))}
                  {template.sections.length > 5 ? (
                    <li className="pl-7 text-xs text-ink-faint">
                      +{template.sections.length - 5} more sections
                    </li>
                  ) : null}
                </ol>

                <div className="mt-4 flex items-center justify-between border-t border-line pt-3">
                  <p className="text-xs text-ink-faint">
                    Used {template.usageCount}× · edited {relative(template.updatedAt)}
                  </p>
                  <Button variant="quiet" size="sm" onClick={() => setPreview(template)}>
                    <Eye />
                    Preview
                  </Button>
                </div>
              </Panel>
            </motion.li>
          ))}
        </ul>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          title={editing ? "Edit template" : "New template"}
          description="Sections are emitted in the order you list them."
          className="max-w-xl"
          footer={
            <>
              <Button variant="ghost" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={save} disabled={draft.name.trim().length < 3}>
                {editing ? "Save changes" : "Create template"}
              </Button>
            </>
          }
        >
          <div className="space-y-4">
            <Field label="Name" htmlFor="tpl-name" required>
              <Input
                id="tpl-name"
                value={draft.name}
                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                placeholder="Full Solicitation Analysis"
              />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Kind" htmlFor="tpl-kind">
                <Select value={draft.kind} onValueChange={(v) => setDraft({ ...draft, kind: v as Template["kind"] })}>
                  <SelectTrigger id="tpl-kind">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(Object.keys(KIND_COPY) as Template["kind"][]).map((key) => (
                      <SelectItem key={key} value={key}>
                        {KIND_COPY[key].label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
              <Field label="Format" htmlFor="tpl-format">
                <Select
                  value={draft.format}
                  onValueChange={(v) => setDraft({ ...draft, format: v as Template["format"] })}
                >
                  <SelectTrigger id="tpl-format">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="DOCX">DOCX</SelectItem>
                    <SelectItem value="PDF">PDF</SelectItem>
                    <SelectItem value="MD">Markdown</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
            </div>
            <Field label="Description" htmlFor="tpl-desc">
              <Textarea
                id="tpl-desc"
                value={draft.description}
                onChange={(e) => setDraft({ ...draft, description: e.target.value })}
              />
            </Field>
            <Field label="Sections" hint="Press Enter after each">
              <TagsInput
                values={draft.sections}
                onValuesChange={(sections) => setDraft({ ...draft, sections })}
                placeholder="Executive summary"
              />
            </Field>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(preview)} onOpenChange={(o) => !o && setPreview(null)}>
        <DialogContent
          title={preview?.name ?? "Preview"}
          description={preview ? `${preview.format} · ${preview.sections.length} sections` : undefined}
          className="max-w-2xl"
          footer={
            <>
              <Button variant="ghost" onClick={() => setPreview(null)}>
                Close
              </Button>
              <Button
                variant="primary"
                onClick={() => {
                  notify.success("Template applied to the next export.");
                  setPreview(null);
                }}
              >
                Use this template
              </Button>
            </>
          }
        >
          {preview ? <TemplatePreview template={preview} /> : null}
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={Boolean(confirm)}
        onOpenChange={(o) => !o && setConfirm(null)}
        title="Delete this template?"
        destructive
        confirmLabel="Delete"
        description={confirm ? `“${confirm.name}” will no longer be offered when exporting.` : ""}
        onConfirm={() => {
          if (!confirm) return;
          const removed = deleteTemplate(confirm.id);
          setConfirm(null);
          if (removed) notify.success("Template deleted.", { undo: () => restoreTemplate(removed) });
        }}
      />
    </div>
  );
}

/** A paper mock of the generated document — deliberately not a real render. */
function TemplatePreview({ template }: { template: Template }) {
  return (
    <div className="paper-grain rounded-md border border-line bg-paper px-8 py-7 shadow-[var(--shadow-raised)]">
      <p className="eyebrow">Thornfield &amp; Co · {template.format}</p>
      <h4 className="display-tight mt-2 text-xl text-ink">{template.name}</h4>
      <div className="mt-1 h-px w-16 bg-patina" aria-hidden />
      <ol className="mt-6 space-y-4">
        {template.sections.map((section, i) => (
          <li key={section} className="space-y-2">
            <div className="flex items-baseline gap-3">
              <span className="font-mono text-2xs text-ink-faint tabular">{String(i + 1).padStart(2, "0")}</span>
              <span className="text-sm font-medium text-ink">{section}</span>
            </div>
            <div className="ml-9 space-y-1.5" aria-hidden>
              {[0, 1, 2].map((line) => (
                <div
                  key={line}
                  className={cn("h-1.5 rounded-full bg-paper-sunk", line === 2 ? "w-2/5" : line === 1 ? "w-11/12" : "w-full")}
                />
              ))}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
