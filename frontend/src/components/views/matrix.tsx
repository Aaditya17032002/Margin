"use client";

import * as React from "react";

import { PageHeader } from "@/components/ui/surface";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/controls";
import { ComplianceMatrix } from "@/components/workspace/compliance-matrix";
import { useAllMatrixData } from "@/hooks/use-workspace-data";
import { useAnalysesStore } from "@/stores/analyses";

/**
 * The same grid as the workspace tab, widened to every analysis at once — this
 * is how a compliance lead works a Friday afternoon across four bids.
 */
export function MatrixView() {
  const analyses = useAnalysesStore((s) => s.analyses);
  const [scope, setScope] = React.useState<string>("all");

  useAllMatrixData();

  const titles = React.useMemo(
    () => Object.fromEntries(analyses.map((a) => [a.id, a.solicitationNumber])),
    [analyses],
  );

  return (
    <div className="mx-auto max-w-[84rem] space-y-6">
      <PageHeader
        eyebrow="Requirements"
        title="Compliance matrix"
        description="Every shall, should, and may extracted from the documents — with the clause it came from still attached."
        actions={
          <Select value={scope} onValueChange={setScope}>
            <SelectTrigger className="w-64">
              <SelectValue placeholder="All analyses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All analyses</SelectItem>
              {analyses.map((analysis) => (
                <SelectItem key={analysis.id} value={analysis.id}>
                  {analysis.solicitationNumber} · {analysis.agency}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        }
      />

      <ComplianceMatrix
        analysisId={scope === "all" ? undefined : scope}
        showAnalysisColumn={scope === "all"}
        analysisTitles={titles}
      />
    </div>
  );
}
