import { parseISO } from "date-fns";

import { allFindings } from "@/stores/analyses";
import { gateScore } from "@/components/domain/gauge";
import type { Analysis, Finding, KeyDate, MatrixRow } from "@/types";

export interface DeadlineRow extends KeyDate {
  analysisId: string;
  analysisTitle: string;
  solicitationNumber: string;
}

export function collectDeadlines(analyses: Analysis[]): DeadlineRow[] {
  return analyses
    .flatMap((analysis) =>
      analysis.dates.map((date) => ({
        ...date,
        analysisId: analysis.id,
        analysisTitle: analysis.title,
        solicitationNumber: analysis.solicitationNumber,
      })),
    )
    .sort((a, b) => parseISO(a.at).getTime() - parseISO(b.at).getTime());
}

export function upcomingDeadlines(analyses: Analysis[], limit?: number) {
  const now = Date.now();
  const rows = collectDeadlines(analyses).filter((d) => parseISO(d.at).getTime() >= now);
  return typeof limit === "number" ? rows.slice(0, limit) : rows;
}

export interface ReviewItem {
  finding: Finding;
  analysisId: string;
  analysisTitle: string;
  solicitationNumber: string;
  reason: "low-confidence" | "flagged";
}

/** Anything a person still has to look at: light ink or an explicit flag. */
export function reviewQueue(analyses: Analysis[]): ReviewItem[] {
  return analyses
    .flatMap((analysis) =>
      allFindings(analysis)
        .filter((f) => (f.confidence < 0.85 || f.flagged) && !f.verified)
        .map((finding) => ({
          finding,
          analysisId: analysis.id,
          analysisTitle: analysis.title,
          solicitationNumber: analysis.solicitationNumber,
          reason: finding.confidence < 0.85 ? ("low-confidence" as const) : ("flagged" as const),
        })),
    )
    .sort((a, b) => a.finding.confidence - b.finding.confidence);
}

export function matrixProgress(rows: MatrixRow[]) {
  const total = rows.length;
  const complete = rows.filter((r) => r.status === "complete").length;
  const unassigned = rows.filter((r) => r.status === "unassigned").length;
  const disqualifying = rows.filter((r) => r.stakes === "disqualifying").length;
  return {
    total,
    complete,
    unassigned,
    disqualifying,
    percent: total === 0 ? 0 : Math.round((complete / total) * 100),
  };
}

export function analysisHealth(analysis: Analysis) {
  const findings = allFindings(analysis);
  const needsReview = findings.filter((f) => f.confidence < 0.85 && !f.verified).length;
  const flagged = findings.filter((f) => f.flagged).length;
  const verified = findings.filter((f) => f.verified).length;
  const hardGatesFailed = analysis.gates.filter((g) => g.weight === "hard" && g.met === false).length;
  return {
    findings: findings.length,
    needsReview,
    flagged,
    verified,
    hardGatesFailed,
    score: gateScore(analysis.gates),
    criticalRisks: analysis.risks.filter((r) => r.severity === "critical").length,
  };
}

export function portfolioStats(analyses: Analysis[], rows: MatrixRow[]) {
  const active = analyses.filter((a) => a.stage !== "decided");
  const pipeline = active.reduce((sum, a) => sum + a.estimatedValue, 0);
  const review = reviewQueue(analyses).length;
  const requirements = rows.length;
  const blocked = analyses.filter((a) =>
    a.gates.some((g) => g.weight === "hard" && g.met === false),
  ).length;
  return { active: active.length, pipeline, review, requirements, blocked, total: analyses.length };
}

export function nextDeadlineFor(analysis: Analysis) {
  const now = Date.now();
  return (
    analysis.dates
      .filter((d) => parseISO(d.at).getTime() >= now)
      .sort((a, b) => parseISO(a.at).getTime() - parseISO(b.at).getTime())[0] ?? null
  );
}

export function searchEverything(
  query: string,
  analyses: Analysis[],
  rows: MatrixRow[],
) {
  const q = query.trim().toLowerCase();
  if (!q) return { analyses: [], findings: [], requirements: [] };

  const matchedAnalyses = analyses.filter((a) =>
    [a.title, a.agency, a.solicitationNumber, a.naics, a.setAside, ...a.tags]
      .join(" ")
      .toLowerCase()
      .includes(q),
  );

  const findings = analyses.flatMap((analysis) =>
    allFindings(analysis)
      .filter((f) => `${f.label} ${f.value} ${f.detail ?? ""}`.toLowerCase().includes(q))
      .map((finding) => ({ finding, analysis })),
  );

  const requirements = rows
    .filter((r) => `${r.reference} ${r.requirement}`.toLowerCase().includes(q))
    .map((row) => ({ row, analysis: analyses.find((a) => a.id === row.analysisId) }))
    .filter((r): r is { row: MatrixRow; analysis: Analysis } => Boolean(r.analysis));

  return { analyses: matchedAnalyses, findings, requirements };
}
