export type Stage = "triage" | "analyzing" | "review" | "decided";
export type GoNoGo = "bid" | "no-bid" | "watch" | "undecided";
export type Stakes = "disqualifying" | "scored" | "informational";
export type RequirementType = "shall" | "should" | "may";
export type MatrixStatus = "unassigned" | "assigned" | "drafted" | "in-review" | "complete";
export type Role = "admin" | "reviewer" | "writer" | "viewer";
export type Appearance = "paper" | "dusk" | "contrast";
export type Density = "comfortable" | "compact";

export type DocType =
  | "RFP"
  | "RFI"
  | "RFQ"
  | "IFB"
  | "Sources Sought"
  | "BAA"
  | "Task Order";

export type AnalysisMode =
  | "quick-triage"
  | "standard"
  | "deep-research"
  | "matrix-only"
  | "qa-only"
  | "amendment-refresh"
  | "recompete-compare";

export interface ModeDescriptor {
  id: AnalysisMode;
  name: string;
  blurb: string;
  minutes: string;
  passes: string;
  agents: AgentId[];
}

export type AgentId =
  | "intake"
  | "scope"
  | "compliance"
  | "eligibility"
  | "evaluation"
  | "risk"
  | "verifier"
  | "qa";

export interface AgentDescriptor {
  id: AgentId;
  name: string;
  duty: string;
  lines: string[];
}

/** Where a finding came from, precise enough to land the eye on the line. */
export interface Citation {
  id: string;
  page: number;
  section: string;
  quote: string;
  /** Normalised 0–1 box on the page, used by the source viewer's overlay layer. */
  bbox: { x: number; y: number; w: number; h: number };
  /**
   * `[firstLine, lastLine]` on that page, when the quote was resolved against
   * the extract. Present means the highlight is exact rather than inferred.
   */
  lines?: [number, number] | number[] | null;
  /** False when the quote was not found in the document — say so, do not guess. */
  located?: boolean;
  /** 1 for a verbatim match, lower for an approximate one. */
  matchScore?: number;
}

export interface Finding {
  id: string;
  label: string;
  value: string;
  detail?: string;
  /** 0–1. Drives ink saturation and the review queue. */
  confidence: number;
  stakes: Stakes;
  citation: Citation;
  verified?: boolean;
  flagged?: boolean;
}

export interface Gate {
  id: string;
  question: string;
  answer: string;
  met: boolean | null;
  citation?: Citation;
  weight: "hard" | "soft";
}

export interface EvaluationFactor {
  id: string;
  name: string;
  weight: number;
  method: string;
  citation: Citation;
}

export interface RiskItem {
  id: string;
  title: string;
  narrative: string;
  severity: "critical" | "elevated" | "moderate";
  likelihood: "likely" | "possible" | "unlikely";
  mitigation: string;
  citation: Citation;
}

export interface SilentItem {
  id: string;
  topic: string;
  expectation: string;
  consequence: string;
  convertedToQuestionId?: string;
}

export interface KeyDate {
  id: string;
  label: string;
  /** ISO string, always stored in UTC. */
  at: string;
  timezone: string;
  /** Every stage a pursuit passes through, in the order it happens. */
  kind:
    | "intent-due"
    | "questions-due"
    | "answers-expected"
    | "site-visit"
    | "solution-review"
    | "draft-review"
    | "final-review"
    | "proposal-due"
    | "orals"
    | "award"
    | "start"
    | "amendment";
  citation?: Citation | null;
  /**
   * `document` when the solicitation stated this date and the citation proves
   * it; `derived` when Margin placed the stage around a date that was stated.
   * A reader has to be able to tell the two apart at a glance.
   */
  source?: "document" | "derived";
}

export interface Clin {
  id: string;
  number: string;
  description: string;
  quantity: string;
  ceiling?: number;
}

export interface DocumentPage {
  page: number;
  heading?: string;
  lines: string[];
}

export interface AmendmentRecord {
  id: string;
  label: string;
  issued: string;
  summary: string;
  changes: {
    id: string;
    kind: "added" | "changed" | "removed";
    area: string;
    before?: string;
    after?: string;
    critical?: boolean;
  }[];
}

export interface ActivityEntry {
  id: string;
  at: string;
  actor: string;
  action: string;
  target?: string;
  analysisId?: string;
}

export interface Analysis {
  id: string;
  title: string;
  solicitationNumber: string;
  agency: string;
  subAgency?: string;
  docType: DocType;
  mode: AnalysisMode;
  stage: Stage;
  goNoGo: GoNoGo;
  decisionNote?: string;
  createdAt: string;
  updatedAt: string;
  owner: string;
  collaborators: string[];
  naics: string;
  setAside: string;
  placeOfPerformance: string;
  estimatedValue: number;
  pageCount: number;
  fileName: string;
  fileSize: number;
  source: "upload" | "sharepoint" | "onedrive" | "outlook";
  tags: string[];

  summary: string;
  identity: Finding[];
  scope: Finding[];
  legal: Finding[];
  eligibility: Finding[];
  pricing: Finding[];
  postAward: Finding[];

  gates: Gate[];
  evaluation: EvaluationFactor[];
  risks: RiskItem[];
  silent: SilentItem[];
  dates: KeyDate[];
  clins: Clin[];
  amendments: AmendmentRecord[];
  pages: DocumentPage[];
  versions: { id: string; label: string; at: string; author: string; note: string }[];
}

export interface MatrixRow {
  id: string;
  analysisId: string;
  reference: string;
  requirement: string;
  type: RequirementType;
  stakes: Stakes;
  owner: string | null;
  responseLocation: string;
  status: MatrixStatus;
  citation: Citation;
  note?: string;
}

export interface QAQuestion {
  id: string;
  analysisId: string;
  text: string;
  rationale: string;
  sourceKind: "silent" | "contradiction" | "ambiguity" | "manual";
  goNoGoImpact: boolean;
  order: number;
  sent: boolean;
  citation?: Citation;
}

export interface AppNotification {
  id: string;
  at: string;
  kind: "deadline" | "review" | "mention" | "system" | "export" | "amendment";
  title: string;
  body: string;
  read: boolean;
  analysisId?: string;
  href?: string;
}

export interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: Role;
  title: string;
  status: "active" | "invited" | "suspended";
  lastActive: string;
  initialsColor: string;
}

export type IntegrationId = "outlook" | "sharepoint" | "onedrive";

export interface FileNode {
  id: string;
  name: string;
  kind: "folder" | "file";
  size?: number;
  modified?: string;
  children?: FileNode[];
}

export interface Integration {
  id: IntegrationId;
  name: string;
  blurb: string;
  connected: boolean;
  account?: string;
  connectedAt?: string;
  scopes: string[];
  tree: FileNode[];
}

export interface Template {
  id: string;
  name: string;
  kind: "report" | "boilerplate" | "dpa";
  description: string;
  sections: string[];
  updatedAt: string;
  usageCount: number;
  format: "DOCX" | "PDF" | "MD";
}

export interface PastBid {
  id: string;
  title: string;
  agency: string;
  submittedAt: string;
  outcome: "won" | "lost" | "no-bid" | "pending";
  value: number;
  debrief: string;
  lessons: string[];
  incumbent?: string;
  scoreGap?: string;
}

export interface ExportRecord {
  id: string;
  at: string;
  analysisId: string;
  analysisTitle: string;
  templateName: string;
  format: "DOCX" | "PDF";
  size: number;
  destination: "download" | "onedrive" | "outlook";
  status: "ready" | "generating" | "failed";
}

export interface Prefs {
  appearance: Appearance;
  density: Density;
  defaultMode: AnalysisMode;
  shortcutsEnabled: boolean;
  reduceMotion: boolean;
  marginRailPinned: boolean;
  sidebarCollapsed: boolean;
  /** First-run desk note on the dashboard. */
  coachDismissed: boolean;
  notify: {
    deadlines: boolean;
    lowConfidence: boolean;
    mentions: boolean;
    amendments: boolean;
    weeklyDigest: boolean;
  };
}

export interface SessionUser {
  id: string;
  name: string;
  email: string;
  title: string;
  avatarTone: string;
  signature: string;
  timezone: string;
}

export interface Org {
  id: string;
  name: string;
  domain: string;
  plan: "Trial" | "Practice" | "Enterprise";
  seats: number;
  seatsUsed: number;
  duns: string;
  cage: string;
}
