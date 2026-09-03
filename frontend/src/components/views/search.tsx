"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Search as SearchIcon } from "lucide-react";

import { pluralize } from "@/lib/utils";
import { searchEverything } from "@/lib/derive";
import { Button } from "@/components/ui/button";
import { PageHeader, Panel, PanelHeader } from "@/components/ui/surface";
import { SearchField } from "@/components/ui/input";
import { Segmented } from "@/components/ui/controls";
import { EmptyState } from "@/components/ui/feedback";
import {
  CitationMeta,
  ConfidenceMeter,
  DocTypeBadge,
  MatrixStatusBadge,
  RequirementTypeBadge,
  StageBadge,
  StakesBadge,
} from "@/components/domain/primitives";
import { useAnalysesStore } from "@/stores/analyses";
import { useMatrixStore } from "@/stores/matrix";

export function SearchView() {
  const router = useRouter();
  const params = useSearchParams();
  const analyses = useAnalysesStore((s) => s.analyses);
  const rows = useMatrixStore((s) => s.rows);

  // The field is seeded from the URL once; after that the field leads and the
  // URL follows, so typing never fights the router.
  const [query, setQuery] = React.useState(() => params.get("q") ?? "");
  const [scope, setScope] = React.useState("all");

  // Keep the URL shareable without thrashing history on every keystroke.
  React.useEffect(() => {
    const id = window.setTimeout(() => {
      const next = query.trim() ? `/app/search?q=${encodeURIComponent(query.trim())}` : "/app/search";
      router.replace(next, { scroll: false });
    }, 350);
    return () => window.clearTimeout(id);
  }, [query, router]);

  const results = React.useMemo(() => searchEverything(query, analyses, rows), [query, analyses, rows]);
  const total = results.analyses.length + results.findings.length + results.requirements.length;

  const showAnalyses = scope === "all" || scope === "analyses";
  const showFindings = scope === "all" || scope === "findings";
  const showRequirements = scope === "all" || scope === "requirements";

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        eyebrow="Search"
        title={query.trim() ? `Results for “${query.trim()}”` : "Search everything"}
        description={
          query.trim()
            ? `${pluralize(total, "match", "matches")} across analyses, findings, and requirements.`
            : "Solicitation numbers, agencies, clause references, or any phrase from a finding."
        }
      />

      <div className="flex flex-wrap items-center gap-3">
        <SearchField
          value={query}
          onValueChange={setQuery}
          placeholder="Search analyses, findings, requirements…"
          className="w-full max-w-lg"
          autoFocus
        />
        <Segmented
          ariaLabel="Result type"
          value={scope}
          onValueChange={setScope}
          options={[
            { value: "all", label: "All" },
            { value: "analyses", label: `Analyses (${results.analyses.length})` },
            { value: "findings", label: `Findings (${results.findings.length})` },
            { value: "requirements", label: `Requirements (${results.requirements.length})` },
          ]}
        />
      </div>

      {!query.trim() ? (
        <EmptyState
          illustration={<SearchIcon className="size-7 text-patina" aria-hidden />}
          title="Start typing"
          description="Search reaches into every finding and every extracted requirement, not just titles. Press ⌘K anywhere for the same thing in a hurry."
        />
      ) : total === 0 ? (
        <EmptyState
          title="Nothing matched"
          description="Try a clause reference like L.3.2, an agency name, or a phrase from the document."
          action={
            <Button variant="secondary" onClick={() => setQuery("")}>
              Clear search
            </Button>
          }
        />
      ) : (
        <div className="space-y-5">
          {showAnalyses && results.analyses.length > 0 ? (
            <Panel>
              <PanelHeader title="Analyses" description={pluralize(results.analyses.length, "match", "matches")} />
              <ul className="divide-y divide-line">
                {results.analyses.map((analysis) => (
                  <li key={analysis.id}>
                    <Link
                      href={`/app/analyses/${analysis.id}`}
                      className="block px-5 py-4 transition-colors duration-150 hover:bg-paper-sunk"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <DocTypeBadge docType={analysis.docType} />
                        <StageBadge stage={analysis.stage} />
                        <span className="font-mono text-2xs text-ink-faint">{analysis.solicitationNumber}</span>
                      </div>
                      <p className="mt-1.5 text-sm text-ink">{analysis.title}</p>
                      <p className="text-xs text-ink-faint">
                        {analysis.agency} · {analysis.naics} · {analysis.setAside}
                      </p>
                    </Link>
                  </li>
                ))}
              </ul>
            </Panel>
          ) : null}

          {showFindings && results.findings.length > 0 ? (
            <Panel>
              <PanelHeader title="Findings" description={pluralize(results.findings.length, "match", "matches")} />
              <ul className="divide-y divide-line">
                {results.findings.slice(0, 40).map(({ finding, analysis }) => (
                  <li key={`${analysis.id}-${finding.id}`} className="px-5 py-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <StakesBadge stakes={finding.stakes} />
                      <Link
                        href={`/app/analyses/${analysis.id}`}
                        className="font-mono text-2xs text-ink-faint underline-offset-4 hover:underline"
                      >
                        {analysis.solicitationNumber}
                      </Link>
                    </div>
                    <p className="mt-1.5 text-xs uppercase tracking-[0.08em] text-ink-faint">{finding.label}</p>
                    <p className="mt-1 text-sm leading-relaxed text-ink">{finding.value}</p>
                    <CitationMeta
                      className="mt-1"
                      citation={finding.citation}
                      analysisId={analysis.id}
                      label={finding.label}
                      origin="Search"
                      aside={<ConfidenceMeter confidence={finding.confidence} />}
                      clamp={2}
                    />
                  </li>
                ))}
              </ul>
            </Panel>
          ) : null}

          {showRequirements && results.requirements.length > 0 ? (
            <Panel>
              <PanelHeader
                title="Requirements"
                description={pluralize(results.requirements.length, "match", "matches")}
              />
              <ul className="divide-y divide-line">
                {results.requirements.slice(0, 40).map(({ row, analysis }) => (
                  <li key={row.id} className="px-5 py-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-2xs text-ink">{row.reference}</span>
                      <RequirementTypeBadge type={row.type} />
                      <MatrixStatusBadge status={row.status} />
                      <Link
                        href={`/app/analyses/${analysis.id}?tab=matrix`}
                        className="font-mono text-2xs text-ink-faint underline-offset-4 hover:underline"
                      >
                        {analysis.solicitationNumber}
                      </Link>
                    </div>
                    <p className="mt-1.5 text-sm leading-relaxed text-ink">{row.requirement}</p>
                    <p className="mt-1 text-xs text-ink-faint">
                      {row.owner ? `Owned by ${row.owner}` : "Unassigned"}
                      {row.responseLocation ? ` · ${row.responseLocation}` : ""}
                    </p>
                    <CitationMeta
                      className="mt-1"
                      citation={row.citation}
                      analysisId={analysis.id}
                      label={row.reference}
                      origin="Search"
                      compact
                      clamp={2}
                    />
                  </li>
                ))}
              </ul>
            </Panel>
          ) : null}
        </div>
      )}
    </div>
  );
}
