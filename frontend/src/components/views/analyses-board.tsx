"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  KeyboardSensor,
  closestCorners,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { useSortable, SortableContext, verticalListSortingStrategy, sortableKeyboardCoordinates } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import {
  Copy,
  Filter,
  LayoutGrid,
  MoreHorizontal,
  Plus,
  Rows3,
  Trash2,
  Upload,
} from "lucide-react";

import { cn, formatCurrency, pluralize } from "@/lib/utils";
import { relative } from "@/lib/dates";
import { analysisHealth, nextDeadlineFor } from "@/lib/derive";
import { listItem, staggerList } from "@/lib/motion";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/surface";
import { SearchField } from "@/components/ui/input";
import { Segmented, Checkbox } from "@/components/ui/controls";
import { EmptyState } from "@/components/ui/feedback";
import { Table, TableFrame, Td, Th, Tr } from "@/components/ui/table";
import {
  ConfirmDialog,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  Tooltip,
} from "@/components/ui/overlay";
import { notify } from "@/components/ui/toaster";
import { MiniGauge } from "@/components/domain/gauge";
import { DocTypeBadge, STAGE_LABEL, STAGE_ORDER, StageBadge } from "@/components/domain/primitives";
import { DeadlineLine } from "@/components/domain/deadline";
import { useAnalysesStore } from "@/stores/analyses";
import { useReportsStore } from "@/stores/workspace";
import { useUIStore } from "@/stores/ui";
import type { Analysis, Stage } from "@/types";

export function AnalysesBoardView() {
  const router = useRouter();
  const reduce = useReducedMotion();
  const analyses = useAnalysesStore((s) => s.analyses);
  const setStage = useAnalysesStore((s) => s.setStage);
  const deleteAnalysis = useAnalysesStore((s) => s.deleteAnalysis);
  const restoreAnalysis = useAnalysesStore((s) => s.restoreAnalysis);
  const duplicateAnalysis = useAnalysesStore((s) => s.duplicateAnalysis);
  const log = useReportsStore((s) => s.log);
  const setImportOpen = useUIStore((s) => s.setImportOpen);

  const [view, setView] = React.useState<"kanban" | "table">("kanban");
  const [query, setQuery] = React.useState("");
  const [docFilter, setDocFilter] = React.useState<string[]>([]);
  const [selected, setSelected] = React.useState<string[]>([]);
  const [dragging, setDragging] = React.useState<Analysis | null>(null);
  const [confirmDelete, setConfirmDelete] = React.useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    return analyses.filter((a) => {
      if (docFilter.length && !docFilter.includes(a.docType)) return false;
      if (!q) return true;
      return [a.title, a.agency, a.solicitationNumber, a.owner, ...a.tags]
        .join(" ")
        .toLowerCase()
        .includes(q);
    });
  }, [analyses, query, docFilter]);

  const docTypes = React.useMemo(
    () => Array.from(new Set(analyses.map((a) => a.docType))).sort(),
    [analyses],
  );

  function handleDragStart(event: DragStartEvent) {
    const found = analyses.find((a) => a.id === event.active.id);
    setDragging(found ?? null);
  }

  function handleDragEnd(event: DragEndEvent) {
    setDragging(null);
    const { active, over } = event;
    if (!over) return;
    const targetStage = (over.data.current?.stage ?? over.id) as Stage;
    if (!STAGE_ORDER.includes(targetStage)) return;
    const analysis = analyses.find((a) => a.id === active.id);
    if (!analysis || analysis.stage === targetStage) return;

    const previous = setStage(analysis.id, targetStage);
    log({ actor: "You", action: `moved to ${STAGE_LABEL[targetStage]}`, target: analysis.solicitationNumber, analysisId: analysis.id });
    notify.success(`Moved to ${STAGE_LABEL[targetStage]}.`, {
      description: analysis.solicitationNumber,
      undo: previous ? () => setStage(analysis.id, previous) : undefined,
    });
  }

  function handleDelete(id: string) {
    const analysis = analyses.find((a) => a.id === id);
    const index = analyses.findIndex((a) => a.id === id);
    if (!analysis) return;
    deleteAnalysis(id);
    setSelected((s) => s.filter((v) => v !== id));
    notify.success("Analysis deleted.", {
      description: analysis.solicitationNumber,
      undo: () => restoreAnalysis(analysis, index),
    });
  }

  function bulkMove(stage: Stage) {
    const affected = selected
      .map((id) => ({ id, previous: setStage(id, stage) }))
      .filter((entry) => entry.previous);
    notify.success(`${pluralize(affected.length, "analysis", "analyses")} moved to ${STAGE_LABEL[stage]}.`, {
      undo: () => affected.forEach((entry) => entry.previous && setStage(entry.id, entry.previous)),
    });
    setSelected([]);
  }

  return (
    <div className="mx-auto max-w-[86rem] space-y-6">
      <PageHeader
        eyebrow="Pipeline"
        title="Analyses"
        description="Every solicitation Margin has read, arranged by how far along the decision is."
        actions={
          <>
            <Button variant="secondary" onClick={() => setImportOpen(true)}>
              <Upload />
              Import
            </Button>
            <Button asChild variant="primary">
              <Link href="/app/analyses/new">
                <Plus />
                New analysis
              </Link>
            </Button>
          </>
        }
      />

      <div className="flex flex-wrap items-center gap-3">
        <SearchField
          value={query}
          onValueChange={setQuery}
          placeholder="Search by title, agency, number, owner"
          className="min-w-64 flex-1"
        />

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="secondary" size="md">
              <Filter />
              Document type
              {docFilter.length ? (
                <span className="ml-1 rounded-xs bg-patina-tint px-1.5 py-px font-mono text-2xs text-patina">
                  {docFilter.length}
                </span>
              ) : null}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Filter by type</DropdownMenuLabel>
            {docTypes.map((type) => (
              <DropdownMenuItem
                key={type}
                onSelect={(e) => {
                  e.preventDefault();
                  setDocFilter((current) =>
                    current.includes(type) ? current.filter((t) => t !== type) : [...current, type],
                  );
                }}
              >
                <Checkbox checked={docFilter.includes(type)} className="pointer-events-none" />
                {type}
              </DropdownMenuItem>
            ))}
            {docFilter.length ? (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem onSelect={() => setDocFilter([])}>Clear filter</DropdownMenuItem>
              </>
            ) : null}
          </DropdownMenuContent>
        </DropdownMenu>

        <Segmented
          ariaLabel="View"
          value={view}
          onValueChange={(v) => setView(v as "kanban" | "table")}
          options={[
            { value: "kanban", label: "Board", icon: <LayoutGrid /> },
            { value: "table", label: "Table", icon: <Rows3 /> },
          ]}
        />
      </div>

      <AnimatePresence>
        {selected.length > 0 ? (
          <motion.div
            initial={reduce ? { opacity: 0 } : { opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.2, ease: [0.32, 0.72, 0, 1] }}
            className="flex flex-wrap items-center gap-3 rounded-md border border-line bg-paper-raised px-4 py-2.5 shadow-[var(--shadow-raised)]"
          >
            <span className="text-sm text-ink">{pluralize(selected.length, "analysis", "analyses")} selected</span>
            <span className="h-4 w-px bg-line" aria-hidden />
            {STAGE_ORDER.map((stage) => (
              <Button key={stage} variant="ghost" size="sm" onClick={() => bulkMove(stage)}>
                Move to {STAGE_LABEL[stage]}
              </Button>
            ))}
            <Button variant="quiet" size="sm" className="ml-auto" onClick={() => setSelected([])}>
              Clear
            </Button>
          </motion.div>
        ) : null}
      </AnimatePresence>

      {filtered.length === 0 ? (
        <EmptyState
          title={query || docFilter.length ? "Nothing matched those filters" : "No analyses yet"}
          description={
            query || docFilter.length
              ? "Try a different agency, solicitation number, or document type."
              : "Upload a solicitation and Margin will read every line, then show you what it found and what the document never said."
          }
          action={
            query || docFilter.length ? (
              <Button
                variant="secondary"
                onClick={() => {
                  setQuery("");
                  setDocFilter([]);
                }}
              >
                Clear filters
              </Button>
            ) : (
              <Button asChild variant="primary">
                <Link href="/app/analyses/new">
                  <Plus />
                  Start an analysis
                </Link>
              </Button>
            )
          }
        />
      ) : view === "kanban" ? (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div className="grid gap-4 lg:grid-cols-4">
            {STAGE_ORDER.map((stage) => (
              <KanbanColumn
                key={stage}
                stage={stage}
                analyses={filtered.filter((a) => a.stage === stage)}
                onDelete={(id) => setConfirmDelete(id)}
                onDuplicate={(id) => {
                  void duplicateAnalysis(id).then((newId) => {
                    if (newId) notify.success("Analysis duplicated.", { description: "The copy starts at Triage." });
                  });
                }}
              />
            ))}
          </div>
          <DragOverlay dropAnimation={{ duration: 220, easing: "cubic-bezier(0.32,0.72,0,1)" }}>
            {dragging ? <KanbanCard analysis={dragging} overlay /> : null}
          </DragOverlay>
        </DndContext>
      ) : (
        <TableFrame>
          <Table>
            <thead>
              <tr>
                <Th className="w-10">
                  <Checkbox
                    aria-label="Select all"
                    checked={
                      selected.length === filtered.length && filtered.length > 0
                        ? true
                        : selected.length > 0
                          ? "indeterminate"
                          : false
                    }
                    onCheckedChange={(checked) =>
                      setSelected(checked === true ? filtered.map((a) => a.id) : [])
                    }
                  />
                </Th>
                <Th>Solicitation</Th>
                <Th>Agency</Th>
                <Th>Stage</Th>
                <Th>Reading</Th>
                <Th className="text-right">Value</Th>
                <Th>Next date</Th>
                <Th className="w-10" />
              </tr>
            </thead>
            <tbody>
              {filtered.map((analysis) => {
                const next = nextDeadlineFor(analysis);
                const health = analysisHealth(analysis);
                return (
                  <Tr key={analysis.id} selected={selected.includes(analysis.id)}>
                    <Td>
                      <Checkbox
                        aria-label={`Select ${analysis.title}`}
                        checked={selected.includes(analysis.id)}
                        onCheckedChange={(checked) =>
                          setSelected((s) =>
                            checked ? [...s, analysis.id] : s.filter((id) => id !== analysis.id),
                          )
                        }
                      />
                    </Td>
                    <Td>
                      <Link
                        href={`/app/analyses/${analysis.id}`}
                        className="block max-w-md space-y-1 transition-colors duration-150 hover:text-patina"
                      >
                        <span className="flex items-center gap-2">
                          <DocTypeBadge docType={analysis.docType} />
                          {health.hardGatesFailed > 0 ? (
                            <span className="font-mono text-2xs uppercase tracking-[0.1em] text-seal">blocked</span>
                          ) : null}
                        </span>
                        <span className="block truncate font-medium text-ink">{analysis.title}</span>
                        <span className="block truncate font-mono text-2xs text-ink-faint">
                          {analysis.solicitationNumber}
                        </span>
                      </Link>
                    </Td>
                    <Td className="max-w-40 truncate">{analysis.agency}</Td>
                    <Td>
                      <StageBadge stage={analysis.stage} />
                    </Td>
                    <Td>
                      <MiniGauge gates={analysis.gates} decision={analysis.goNoGo} />
                    </Td>
                    <Td className="text-right font-mono tabular">
                      {analysis.estimatedValue ? formatCurrency(analysis.estimatedValue) : "—"}
                    </Td>
                    <Td className="whitespace-nowrap text-xs">
                      {next ? `${next.label} · ${relative(next.at)}` : "—"}
                    </Td>
                    <Td>
                      <RowMenu
                        analysis={analysis}
                        onDelete={() => setConfirmDelete(analysis.id)}
                        onDuplicate={() => {
                          duplicateAnalysis(analysis.id);
                          notify.success("Analysis duplicated.");
                        }}
                        onOpen={() => router.push(`/app/analyses/${analysis.id}`)}
                      />
                    </Td>
                  </Tr>
                );
              })}
            </tbody>
          </Table>
        </TableFrame>
      )}

      <ConfirmDialog
        open={Boolean(confirmDelete)}
        onOpenChange={(open) => !open && setConfirmDelete(null)}
        title="Delete this analysis?"
        destructive
        confirmLabel="Delete"
        description="The findings, compliance matrix rows, and questions stay in place until you undo. You will have a moment to change your mind."
        onConfirm={() => confirmDelete && handleDelete(confirmDelete)}
      />
    </div>
  );
}

function KanbanColumn({
  stage,
  analyses,
  onDelete,
  onDuplicate,
}: {
  stage: Stage;
  analyses: Analysis[];
  onDelete: (id: string) => void;
  onDuplicate: (id: string) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: stage, data: { stage } });
  const reduce = useReducedMotion();

  return (
    <section
      ref={setNodeRef}
      aria-label={STAGE_LABEL[stage]}
      className={cn(
        "flex min-h-56 flex-col rounded-lg border bg-paper-raised transition-colors duration-200",
        isOver ? "border-patina bg-patina-tint/40" : "border-line",
      )}
    >
      <header className="flex items-center justify-between gap-2 border-b border-line px-3.5 py-2.5">
        <div className="flex items-center gap-2">
          <StageBadge stage={stage} />
          <span className="font-mono text-2xs tabular text-ink-faint">{analyses.length}</span>
        </div>
      </header>
      <SortableContext items={analyses.map((a) => a.id)} strategy={verticalListSortingStrategy}>
        <motion.div
          variants={staggerList()}
          initial={reduce ? false : "hidden"}
          animate="visible"
          className="flex-1 space-y-2.5 p-2.5"
        >
          {analyses.length === 0 ? (
            <p className="px-1 py-6 text-center text-xs text-ink-faint">Drop an analysis here</p>
          ) : (
            analyses.map((analysis) => (
              <SortableCard
                key={analysis.id}
                analysis={analysis}
                onDelete={() => onDelete(analysis.id)}
                onDuplicate={() => onDuplicate(analysis.id)}
              />
            ))
          )}
        </motion.div>
      </SortableContext>
    </section>
  );
}

function SortableCard({
  analysis,
  onDelete,
  onDuplicate,
}: {
  analysis: Analysis;
  onDelete: () => void;
  onDuplicate: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: analysis.id,
    data: { stage: analysis.stage },
  });

  return (
    <motion.div variants={listItem}>
      <div
        ref={setNodeRef}
        style={{ transform: CSS.Translate.toString(transform), transition }}
        className={cn(isDragging && "opacity-35")}
        {...attributes}
        {...listeners}
      >
        <KanbanCard analysis={analysis} onDelete={onDelete} onDuplicate={onDuplicate} />
      </div>
    </motion.div>
  );
}

function KanbanCard({
  analysis,
  overlay,
  onDelete,
  onDuplicate,
}: {
  analysis: Analysis;
  overlay?: boolean;
  onDelete?: () => void;
  onDuplicate?: () => void;
}) {
  const health = analysisHealth(analysis);
  const next = nextDeadlineFor(analysis);

  return (
    <article
      className={cn(
        "group relative rounded-md border border-line bg-paper-raised p-3.5",
        "transition-[box-shadow,border-color] duration-200 ease-[cubic-bezier(0.32,0.72,0,1)]",
        overlay
          ? "rotate-[1.5deg] cursor-grabbing shadow-[var(--shadow-overlay)]"
          : "cursor-grab hover:border-[var(--line-strong)] hover:shadow-[var(--shadow-raised)]",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <DocTypeBadge docType={analysis.docType} />
        {!overlay && (onDelete || onDuplicate) ? (
          <div className="opacity-0 transition-opacity duration-150 focus-within:opacity-100 group-hover:opacity-100">
            <RowMenu analysis={analysis} onDelete={onDelete} onDuplicate={onDuplicate} compact />
          </div>
        ) : null}
      </div>

      <Link
        href={`/app/analyses/${analysis.id}`}
        onClick={(e) => e.stopPropagation()}
        className="mt-2 block text-sm font-medium leading-snug text-ink transition-colors duration-150 hover:text-patina"
      >
        {analysis.title}
      </Link>
      <p className="mt-1 truncate font-mono text-2xs text-ink-faint">{analysis.solicitationNumber}</p>
      <p className="mt-0.5 truncate text-xs text-ink-faint">{analysis.agency}</p>

      <div className="mt-3 space-y-2 border-t border-line pt-2.5">
        <MiniGauge gates={analysis.gates} decision={analysis.goNoGo} />
        {next ? (
          <DeadlineLine at={next.at} timezone={next.timezone} label={next.label} />
        ) : (
          <p className="text-xs text-ink-faint">No dates extracted yet</p>
        )}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-2xs text-ink-faint">
          <span>{health.findings} findings</span>
          {health.needsReview > 0 ? <span className="text-ochre">{health.needsReview} to review</span> : null}
          {health.criticalRisks > 0 ? <span className="text-seal">{health.criticalRisks} critical</span> : null}
        </div>
      </div>
    </article>
  );
}

function RowMenu({
  analysis,
  onDelete,
  onDuplicate,
  onOpen,
  compact,
}: {
  analysis: Analysis;
  onDelete?: () => void;
  onDuplicate?: () => void;
  onOpen?: () => void;
  compact?: boolean;
}) {
  return (
    <DropdownMenu>
      <Tooltip content="Actions">
        <DropdownMenuTrigger asChild>
          <Button
            variant="quiet"
            size="iconSm"
            aria-label={`Actions for ${analysis.title}`}
            onPointerDown={(e) => e.stopPropagation()}
            className={compact ? "" : ""}
          >
            <MoreHorizontal />
          </Button>
        </DropdownMenuTrigger>
      </Tooltip>
      <DropdownMenuContent align="end">
        {onOpen ? <DropdownMenuItem onSelect={onOpen}>Open workspace</DropdownMenuItem> : null}
        {onDuplicate ? (
          <DropdownMenuItem onSelect={onDuplicate}>
            <Copy />
            Duplicate
          </DropdownMenuItem>
        ) : null}
        {onDelete ? (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem destructive onSelect={onDelete}>
              <Trash2 />
              Delete
            </DropdownMenuItem>
          </>
        ) : null}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
