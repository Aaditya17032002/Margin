export const WORKSPACE_TABS = [
  { id: "go-no-go", label: "Go / No-Go" },
  { id: "overview", label: "Overview & Dates" },
  { id: "scope", label: "Scope" },
  { id: "matrix", label: "Compliance Matrix" },
  { id: "legal", label: "Legal & Regulatory" },
  { id: "evaluation", label: "Eligibility & Evaluation" },
  { id: "risks", label: "Risks & Red Flags" },
  { id: "questions", label: "Q&A Builder" },
  { id: "silent", label: "SILENT Ledger" },
  { id: "amendments", label: "Amendments" },
  { id: "versions", label: "Versions & Activity" },
] as const;

export type WorkspaceTabId = (typeof WORKSPACE_TABS)[number]["id"];
