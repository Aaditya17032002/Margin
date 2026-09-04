"use client";

import * as React from "react";
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { Check, Download, Filter, Plus, Trash2, X } from "lucide-react";

import { cn, pluralize } from "@/lib/utils";
import { matrixProgress } from "@/lib/derive";
import { Button } from "@/components/ui/button";
import { SearchField } from "@/components/ui/input";
import { Checkbox, Combobox, Progress, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/controls";
import { Pagination, Table, TableFrame, Td, Th, Tr } from "@/components/ui/table";
import { EmptyState } from "@/components/ui/feedback";
import { Tooltip } from "@/components/ui/overlay";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/overlay";
import { Badge } from "@/components/ui/badge";
import { notify } from "@/components/ui/toaster";
import {
  CitationMeta,
  MATRIX_STATUS_LABEL,
  RequirementTypeBadge,
  StakesBadge,
} from "@/components/domain/primitives";
import { useMatrixStore } from "@/stores/matrix";
import { useTeamStore } from "@/stores/workspace";
import type { MatrixRow, MatrixStatus, RequirementType } from "@/types";

const STATUSES: MatrixStatus[] = ["unassigned", "assigned", "drafted", "in-review", "complete"];
const TYPES: RequirementType[] = ["shall", "should", "may"];

/**
 * The matrix is the working surface where a compliance lead spends the week, so
 * every cell that a person changes is editable in place: owner, response
 * location, and status all commit on the spot with an undoable acknowledgement.
 */
export function ComplianceMatrix({
  analysisId,
  showAnalysisColumn = false,
  analysisTitles,
  className,
}: {
  analysisId?: string;
  showAnalysisColumn?: boolean;
  analysisTitles?: Record<string, string>;
  /** Pass `min-h-0 flex-1` to let the grid own the height it is given. */
  className?: string;
}) {
  const allRows = useMatrixStore((s) => s.rows);
  const updateRow = useMatrixStore((s) => s.updateRow);
  const deleteRow = useMatrixStore((s) => s.deleteRow);
  const restoreRow = useMatrixStore((s) => s.restoreRow);
  const bulkAssign = useMatrixStore((s) => s.bulkAssign);
  const bulkStatus = useMatrixStore((s) => s.bulkStatus);
  const bulkDelete = useMatrixStore((s) => s.bulkDelete);
  const restoreMany = useMatrixStore((s) => s.restoreMany);
  const addRow = useMatrixStore((s) => s.addRow);
  const members = useTeamStore((s) => s.members);

  const [query, setQuery] = React.useState("");
  const [typeFilter, setTypeFilter] = React.useState<RequirementType | "all">("all");
  const [stakesFilter, setStakesFilter] = React.useState<string>("all");
  const [statusFilter, setStatusFilter] = React.useState<string>("all");
  const [checkFilter, setCheckFilter] = React.useState<string>("all");
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [selection, setSelection] = React.useState<Record<string, boolean>>({});

  const scoped = React.useMemo(
    () => (analysisId ? allRows.filter((r) => r.analysisId === analysisId) : allRows),
    [allRows, analysisId],
  );

  const filtered = React.useMemo(
    () =>
      scoped.filter((row) => {
        if (typeFilter !== "all" && row.type !== typeFilter) return false;
        if (stakesFilter !== "all" && row.stakes !== stakesFilter) return false;
        if (statusFilter !== "all" && row.status !== statusFilter) return false;
        if (checkFilter !== "all" && (row.verification ?? "substantive") !== checkFilter) return false;
        return true;
      }),
    [scoped, typeFilter, stakesFilter, statusFilter, checkFilter],
  );

  const owners = React.useMemo(
    () => members.filter((m) => m.status === "active").map((m) => ({ value: m.name, label: m.name })),
    [members],
  );

  const columns = React.useMemo<ColumnDef<MatrixRow>[]>(() => {
    const base: ColumnDef<MatrixRow>[] = [
      {
        id: "select",
        header: ({ table }) => (
          <Checkbox
            aria-label="Select all rows"
            checked={
              table.getIsAllPageRowsSelected()
                ? true
                : table.getIsSomePageRowsSelected()
                  ? "indeterminate"
                  : false
            }
            onCheckedChange={(value) => table.toggleAllPageRowsSelected(value === true)}
          />
        ),
        cell: ({ row }) => (
          <Checkbox
            aria-label={`Select ${row.original.reference}`}
            checked={row.getIsSelected()}
            onCheckedChange={(value) => row.toggleSelected(value === true)}
          />
        ),
        size: 36,
        enableSorting: false,
      },
      {
        accessorKey: "reference",
        header: "Ref",
        cell: ({ row }) => (
          <span className="whitespace-nowrap font-mono text-xs text-patina">{row.original.reference}</span>
        ),
        size: 64,
      },
      {
        accessorKey: "requirement",
        header: "Requirement",
        cell: ({ row }) => (
          <div className="max-w-xl space-y-2.5 py-0.5">
            <p className="text-sm leading-relaxed text-ink">{row.original.requirement}</p>
            {row.original.note ? (
              <p className="text-xs italic leading-relaxed text-ink-faint">{row.original.note}</p>
            ) : null}
            <CitationMeta
              citation={row.original.citation}
              analysisId={row.original.analysisId}
              label={row.original.reference}
              origin="Compliance matrix"
              compact
              clamp={2}
            />
            <Provenance row={row.original} />
          </div>
        ),
      },
      {
        accessorKey: "type",
        header: "Type",
        cell: ({ row }) => <RequirementTypeBadge type={row.original.type} />,
        size: 80,
      },
      {
        accessorKey: "stakes",
        header: "Stakes",
        cell: ({ row }) => <StakesBadge stakes={row.original.stakes} />,
        size: 130,
      },
      {
        accessorKey: "owner",
        header: "Owner",
        cell: ({ row }) => (
          <Combobox
            className="w-36"
            allowClear
            value={row.original.owner}
            options={owners}
            placeholder="Unassigned"
            onValueChange={(value) => {
              const previous = row.original.owner;
              updateRow(row.original.id, {
                owner: value,
                status: value
                  ? row.original.status === "unassigned"
                    ? "assigned"
                    : row.original.status
                  : "unassigned",
              });
              notify.success(value ? `Assigned to ${value}.` : "Owner cleared.", {
                description: row.original.reference,
                undo: () => updateRow(row.original.id, { owner: previous, status: row.original.status }),
              });
            }}
          />
        ),
        size: 150,
      },
      {
        accessorKey: "responseLocation",
        header: "Response location",
        cell: ({ row }) => <EditableCell row={row.original} onCommit={updateRow} />,
        size: 190,
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => (
          <div>
          <Select
            value={row.original.status}
            onValueChange={(value) => {
              const previous = row.original.status;
              updateRow(row.original.id, { status: value as MatrixStatus });
              notify.success(`Marked ${MATRIX_STATUS_LABEL[value as MatrixStatus].toLowerCase()}.`, {
                description: row.original.reference,
                undo: () => updateRow(row.original.id, { status: previous }),
              });
            }}
          >
            <SelectTrigger className="h-8 w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATUSES.map((status) => (
                <SelectItem key={status} value={status}>
                  {MATRIX_STATUS_LABEL[status]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Clearance row={row.original} />
          </div>
        ),
        size: 140,
      },
      {
        id: "actions",
        header: "",
        cell: ({ row }) => (
          <Button
            variant="quiet"
            size="iconSm"
            aria-label={`Dismiss ${row.original.reference}`}
            onClick={() => {
              const removed = deleteRow(row.original.id);
              if (!removed) return;
              notify.success("Requirement dismissed.", {
                description: removed.row.reference,
                undo: () => restoreRow(removed.row, removed.index),
              });
            }}
          >
            <Trash2 />
          </Button>
        ),
        size: 40,
        enableSorting: false,
      },
    ];

    if (showAnalysisColumn) {
      base.splice(2, 0, {
        id: "analysis",
        header: "Analysis",
        cell: ({ row }) => (
          <span className="block max-w-40 truncate text-xs text-ink-faint">
            {analysisTitles?.[row.original.analysisId] ?? row.original.analysisId}
          </span>
        ),
        size: 160,
      });
    }

    return base;
  }, [analysisTitles, deleteRow, owners, restoreRow, showAnalysisColumn, updateRow]);

  const table = useReactTable({
    data: filtered,
    columns,
    state: { sorting, rowSelection: selection, globalFilter: query },
    onSortingChange: setSorting,
    onRowSelectionChange: setSelection,
    onGlobalFilterChange: setQuery,
    getRowId: (row) => row.id,
    globalFilterFn: (row, _columnId, value) =>
      `${row.original.reference} ${row.original.requirement} ${row.original.owner ?? ""}`
        .toLowerCase()
        .includes(String(value).toLowerCase()),
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 20 } },
  });

  const selectedIds = Object.keys(selection).filter((id) => selection[id]);
  const progress = matrixProgress(scoped);
  const filtersActive =
    typeFilter !== "all" ||
    stakesFilter !== "all" ||
    statusFilter !== "all" ||
    checkFilter !== "all" ||
    Boolean(query);

  return (
    <div className={cn("flex flex-col gap-4", className)}>
      <div className="grid shrink-0 grid-cols-2 gap-3 @2xl:grid-cols-4">
        <Stat label="Requirements" value={String(progress.total)} />
        <Stat label="Disqualifying" value={String(progress.disqualifying)} tone="seal" />
        <Stat label="Unassigned" value={String(progress.unassigned)} tone={progress.unassigned ? "ochre" : undefined} />
        <div className="rounded-lg border border-line bg-paper-raised px-4 py-3">
          <p className="eyebrow">Complete</p>
          <p className="mt-1 font-display text-xl leading-none text-ink tabular">{progress.percent}%</p>
          <Progress value={progress.percent} className="mt-2" tone="leaf" label="Matrix completion" />
        </div>
      </div>

      <div className="flex shrink-0 flex-wrap items-center gap-2.5">
        <SearchField
          value={query}
          onValueChange={setQuery}
          placeholder="Filter requirements"
          className="min-w-56 flex-1"
        />
        <Select value={typeFilter} onValueChange={(v) => setTypeFilter(v as RequirementType | "all")}>
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All types</SelectItem>
            {TYPES.map((type) => (
              <SelectItem key={type} value={type}>
                {type}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={stakesFilter} onValueChange={setStakesFilter}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All stakes</SelectItem>
            <SelectItem value="disqualifying">Disqualifying</SelectItem>
            <SelectItem value="scored">Scored</SelectItem>
            <SelectItem value="informational">Informational</SelectItem>
          </SelectContent>
        </Select>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {STATUSES.map((status) => (
              <SelectItem key={status} value={status}>
                {MATRIX_STATUS_LABEL[status]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {/* Mechanical rules are the ones a machine settles on its own — page
            counts, fonts, forms, file names. Being able to see only those, or
            only the ones needing a judgement, is how a compliance lead splits
            an afternoon's work from a week's. */}
        <Select value={checkFilter} onValueChange={setCheckFilter}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Any check</SelectItem>
            <SelectItem value="mechanical">Counted</SelectItem>
            <SelectItem value="substantive">Needs judgement</SelectItem>
          </SelectContent>
        </Select>
        {filtersActive ? (
          <Button
            variant="quiet"
            size="sm"
            onClick={() => {
              setQuery("");
              setTypeFilter("all");
              setStakesFilter("all");
              setStatusFilter("all");
            }}
          >
            <X />
            Clear
          </Button>
        ) : null}
        {analysisId ? (
          <Button
            variant="secondary"
            size="md"
            onClick={() => {
              const first = scoped[0];
              addRow({
                analysisId,
                reference: "—",
                requirement: "New requirement",
                type: "shall",
                stakes: "scored",
                owner: null,
                responseLocation: "",
                status: "unassigned",
                citation: first?.citation ?? {
                  id: "manual",
                  page: 1,
                  section: "§ manual",
                  quote: "Added by hand.",
                  bbox: { x: 0.1, y: 0.1, w: 0.8, h: 0.04 },
                },
              });
              notify.success("Row added.", { description: "Edit it in place." });
            }}
          >
            <Plus />
            Add row
          </Button>
        ) : null}
      </div>

      {selectedIds.length > 0 ? (
        <div className="flex flex-wrap items-center gap-2.5 rounded-md border border-line bg-paper-raised px-4 py-2.5 shadow-[var(--shadow-raised)]">
          <span className="text-sm text-ink">{pluralize(selectedIds.length, "row")} selected</span>
          <span className="h-4 w-px bg-line" aria-hidden />
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm">
                <Filter />
                Assign to
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              <DropdownMenuLabel>Owner</DropdownMenuLabel>
              {owners.map((owner) => (
                <DropdownMenuItem
                  key={owner.value}
                  onSelect={() => {
                    bulkAssign(selectedIds, owner.value);
                    notify.success(`${pluralize(selectedIds.length, "row")} assigned to ${owner.label}.`, {
                      undo: () => bulkAssign(selectedIds, null),
                    });
                    setSelection({});
                  }}
                >
                  {owner.label}
                </DropdownMenuItem>
              ))}
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onSelect={() => {
                  bulkAssign(selectedIds, null);
                  notify.success("Owners cleared.");
                  setSelection({});
                }}
              >
                Clear owner
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm">
                <Check />
                Set status
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              {STATUSES.map((status) => (
                <DropdownMenuItem
                  key={status}
                  onSelect={() => {
                    bulkStatus(selectedIds, status);
                    notify.success(`${pluralize(selectedIds.length, "row")} marked ${MATRIX_STATUS_LABEL[status].toLowerCase()}.`);
                    setSelection({});
                  }}
                >
                  {MATRIX_STATUS_LABEL[status]}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              const removed = bulkDelete(selectedIds);
              notify.success(`${pluralize(removed.length, "row")} removed.`, {
                undo: () => restoreMany(removed),
              });
              setSelection({});
            }}
          >
            <Trash2 />
            Delete
          </Button>

          <Button
            variant="quiet"
            size="sm"
            className="ml-auto"
            onClick={() => {
              notify.success("Matrix exported.", {
                description: `${pluralize(selectedIds.length, "row")} written to DOCX.`,
                action: { label: "Download", onClick: () => notify.info("Download started.") },
              });
            }}
          >
            <Download />
            Export selection
          </Button>
        </div>
      ) : null}

      {filtered.length === 0 ? (
        <EmptyState
          title={filtersActive ? "No requirements match" : "No requirements extracted"}
          description={
            filtersActive
              ? "Loosen a filter — there may be requirements of another type or status."
              : "Run a Standard or Matrix-only read and every shall, must and will in the document will land here, each with its clause."
          }
        />
      ) : (
        <TableFrame
          className="min-h-0 flex-1"
          footer={
            <Pagination
              page={table.getState().pagination.pageIndex}
              pageCount={table.getPageCount()}
              total={filtered.length}
              onPageChange={(page) => table.setPageIndex(page)}
            />
          }
        >
          <Table>
            <thead>
              {table.getHeaderGroups().map((group) => (
                <tr key={group.id}>
                  {group.headers.map((header) => (
                    <Th
                      key={header.id}
                      style={{ width: header.getSize() }}
                      sortable={header.column.getCanSort()}
                      sorted={header.column.getIsSorted()}
                      onSort={header.column.getToggleSortingHandler() as () => void}
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                    </Th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row) => (
                <Tr key={row.id} selected={row.getIsSelected()}>
                  {row.getVisibleCells().map((cell) => (
                    <Td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</Td>
                  ))}
                </Tr>
              ))}
            </tbody>
          </Table>
        </TableFrame>
      )}
    </div>
  );
}

/**
 * How this requirement is known, and how it can be checked.
 *
 * Both halves matter to whoever is signing the response. A requirement the
 * pattern sweep and a specialist both found is stronger than one only a model
 * saw; a requirement that can be checked by counting should never be argued
 * about. Neither fact is visible in the requirement's text, so it is shown
 * beside it rather than left to be assumed.
 */
function Provenance({ row }: { row: MatrixRow }) {
  const sources = row.sources ?? [];
  const mechanical = (row.verification ?? "substantive") === "mechanical";
  const bothPasses = sources.includes("sweep") && sources.includes("model");
  const modelOnly = sources.includes("model") && !sources.includes("sweep");

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <Tooltip
        content={
          mechanical
            ? "Checked by counting — page limits, fonts, margins, forms, file names. Never decided by a model."
            : "Needs a person to read it. A model can draft the assessment; it cannot settle it."
        }
      >
        <Badge tone={mechanical ? "slate" : "neutral"} shape="mono">
          {mechanical ? "Counted" : "Judgement"}
        </Badge>
      </Tooltip>
      {bothPasses ? (
        <Tooltip content="Found by the deterministic sweep and by a specialist. Agreement between the two is the strongest signal extraction produces.">
          <Badge tone="leaf" shape="mono">
            Corroborated
          </Badge>
        </Tooltip>
      ) : null}
      {modelOnly ? (
        <Tooltip content="Only a specialist reported this — no pattern matched it. Worth reading against the source before relying on it.">
          <Badge tone="ochre" shape="mono">
            Model only
          </Badge>
        </Tooltip>
      ) : null}
      {sources.includes("manual") ? (
        <Tooltip content="Added or edited by hand. A run that does not find it will leave it alone.">
          <Badge tone="neutral" shape="mono">
            By hand
          </Badge>
        </Tooltip>
      ) : null}
      {row.state === "removed" ? (
        <Tooltip content="The latest read of the package did not find this. It is kept so it can be accounted for, not deleted.">
          <Badge tone="seal" shape="mono">
            Not in latest read
          </Badge>
        </Tooltip>
      ) : null}
    </div>
  );
}

/**
 * A disqualifying requirement is not cleared because a model said so.
 *
 * Marking one complete records who did it; until then the row says what is
 * missing. This is the difference between a matrix that tracks work and one
 * that launders an assumption into a green tick.
 */
function Clearance({ row }: { row: MatrixRow }) {
  if (row.stakes !== "disqualifying" || row.status !== "complete") return null;
  if (row.confirmedBy) {
    return (
      <p className="mt-1 flex items-center gap-1 text-2xs text-leaf">
        <Check className="size-3" />
        Confirmed by {row.confirmedBy}
      </p>
    );
  }
  return (
    <p className="mt-1 text-2xs text-[color-mix(in_oklab,var(--ochre)_82%,var(--ink))]">
      Needs a person to confirm
    </p>
  );
}

function EditableCell({
  row,
  onCommit,
}: {
  row: MatrixRow;
  onCommit: (id: string, patch: Partial<MatrixRow>) => void;
}) {
  // The draft only exists while the cell is open; the row itself is read at
  // every other moment, so an external edit never has to be synced in.
  const [draft, setDraft] = React.useState<string | null>(null);
  const editing = draft !== null;
  const value = draft ?? row.responseLocation;

  const setEditing = (open: boolean) => setDraft(open ? row.responseLocation : null);
  const setValue = (next: string) => setDraft(next);

  function commit() {
    setDraft(null);
    if (value === row.responseLocation) return;
    const previous = row.responseLocation;
    onCommit(row.id, { responseLocation: value });
    notify.success("Response location updated.", {
      description: row.reference,
      undo: () => onCommit(row.id, { responseLocation: previous }),
    });
  }

  if (!editing) {
    return (
      <button
        type="button"
        onClick={() => setEditing(true)}
        className={cn(
          "w-full rounded-sm px-2 py-1 text-left text-sm transition-colors duration-150 hover:bg-paper-sunk",
          value ? "text-ink-soft" : "text-ink-faint italic",
        )}
      >
        {value || "Not placed"}
      </button>
    );
  }

  return (
    <input
      autoFocus
      value={value}
      onChange={(e) => setValue(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") commit();
        if (e.key === "Escape") setDraft(null);
      }}
      aria-label={`Response location for ${row.reference}`}
      className="w-full rounded-sm border border-patina bg-paper-raised px-2 py-1 text-sm outline-none"
    />
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "seal" | "ochre" }) {
  return (
    <div className="rounded-lg border border-line bg-paper-raised px-4 py-3">
      <p className="eyebrow">{label}</p>
      <p
        className="mt-1 font-display text-xl leading-none tabular"
        style={{ color: tone ? `var(--${tone})` : "var(--ink)" }}
      >
        {value}
      </p>
    </div>
  );
}
