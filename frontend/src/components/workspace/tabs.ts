export const WORKSPACE_TABS = [
  { id: "go-no-go", label: "Go / No-Go" },
  { id: "verify", label: "Needs You" },
  { id: "overview", label: "Overview & Dates" },
  { id: "coverage", label: "Coverage" },
  { id: "scope", label: "Scope" },
  { id: "matrix", label: "Compliance Matrix" },
  { id: "contradictions", label: "Conflicts" },
  { id: "response", label: "Response Gap" },
  { id: "reviews", label: "Reviews" },
  { id: "legal", label: "Legal & Regulatory" },
  { id: "evaluation", label: "Eligibility & Evaluation" },
  { id: "risks", label: "Risks & Red Flags" },
  { id: "questions", label: "Q&A Builder" },
  { id: "silent", label: "SILENT Ledger" },
  { id: "research", label: "External Research" },
  { id: "amendments", label: "Amendments" },
  { id: "versions", label: "Versions & Activity" },
] as const;

export type WorkspaceTabId = (typeof WORKSPACE_TABS)[number]["id"];
