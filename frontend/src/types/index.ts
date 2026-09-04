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

/** One page a deep-research pass actually read on the open web. */
export interface ResearchSource {
  url: string;
  title: string;
  /** The host, e.g. `acquisition.gov`. Whose site it is carries most of the weight. */
  site: string;
}

/**
 * What the open web said, which is never the same kind of thing as what the
 * document says. It has no page, no clause, and no citation — only sources.
 */
/** One paragraph of the research report and the pages that back it. */
export interface ResearchClaim {
  text: string;
  /** URLs into `ExternalResearch.sources`. Empty means nothing was cited. */
  sources: string[];
}

export interface ExternalResearch {
  status:
    | "not_requested"
    | "completed"
    | "rate_limited"
    | "timeout"
    | "skipped"
    | "failed";
  detail: string;
  query: string;
  summary: string;
  sources: ResearchSource[];
  /** The report split into paragraphs, each carrying its own attribution. */
  claims?: ResearchClaim[];
  at?: string | null;
}

/** One row in the source browser, whatever the provider calls it underneath. */
export interface RemoteEntry {
  /** Opaque token: hand it back to browse into this entry, or to import it. */
  id: string;
  name: string;
  kind: "site" | "drive" | "folder" | "message" | "file";
  size: number;
  modified: string;
  /** Second line — who sent the mail, who last touched the file, the site URL. */
  subtitle: string;
  /** True when Margin can read it. Everything else is a container you open. */
  importable: boolean;
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

/**
 * What was read, and what was not.
 *
 * Two numbers rather than one. `pagesScanned` is everything the deterministic
 * sweep visited; `pagesAnalysed` is the narrower set a specialist actually
 * reasoned over. A single "100% analysed" figure would be a claim the product
 * cannot support, so the shape keeps them apart.
 */
export interface CoverageTotals {
  documents: number;
  emptyDocuments: number;
  pages: number;
  pagesScanned: number;
  pagesAnalysed: number;
  chunks: number;
  chunksAnalysed: number;
  chunksScanned: number;
  chunksUnreached: number;
}

export type CoverageState = "analysed" | "scanned" | "no_text" | "unreached";

export interface CoverageDocument {
  documentId: string;
  name: string;
  kind: "base" | "attachment" | "amendment" | "response" | string;
  pages: number;
  /** The document's worst case, not its average. */
  state: CoverageState;
  pagesAnalysed: number;
  chunks: number;
  chunksAnalysed: number;
  chunksUnreached: number;
  /** Contiguous page runs no pass reached, as [start, end] pairs. */
  unreachedPages: [number, number][];
  note?: string;
}

export interface Coverage {
  at?: string | null;
  totals: CoverageTotals;
  documents: CoverageDocument[];
  /** Specialist id → how many passages it had in context. */
  byAgent: Record<string, number>;
  /** Every passage reached and every document readable. */
  complete: boolean;
}

/**
 * What the last run changed in the Requirement Ledger.
 *
 * `removedWithWork` is the field that matters: requirements somebody had
 * already assigned or drafted against, that the newest read of the package no
 * longer finds. That is a question for a person, not a number on a dashboard.
 */
export interface LedgerDelta {
  added: number;
  updated: number;
  unchanged: number;
  removed: number;
  removedWithWork: string[];
  /** Answers written against wording an amendment has since replaced. */
  invalidated?: string[];
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
  /** The reading ledger for the last run. Absent on an analysis that has not run. */
  coverage?: Coverage;
  /** What the last run added to, changed in, or stopped finding in the ledger. */
  ledger?: LedgerDelta;
  /** The draft response bound to this solicitation, if one has been. */
  response?: ResponseBinding;
  /** Only a deep-research pass fills this in; other modes leave it empty. */
  research?: ExternalResearch;
}

/** How a requirement can be checked. */
export type Verification = "mechanical" | "substantive";

/** Where a requirement stands in the ledger. Nothing is ever deleted. */
export type RequirementState = "open" | "superseded" | "removed";

/**
 * One requirement, shown as a matrix row.
 *
 * The matrix is a projection of the Requirement Ledger, not a separate list.
 * `key` is the requirement's identity — derived from its own words — which is
 * what lets an owner and a status survive a re-read of the package.
 */
export interface MatrixRow {
  id: string;
  analysisId: string;
  /** Stable across runs and re-parses. */
  key?: string;
  reference: string;
  requirement: string;
  type: RequirementType;
  stakes: Stakes;
  /** The extraction category: obligation, instruction, limit, form, certification, volume. */
  kind?: string;
  /** `mechanical` rules are counted, never judged by a model. */
  verification?: Verification;
  state?: RequirementState;
  /** Which passes found it: sweep, model, manual. */
  sources?: string[];
  owner: string | null;
  responseLocation: string;
  status: MatrixStatus;
  citation: Citation;
  note?: string;
  /** Who cleared it. A mandatory requirement is never satisfied without a name. */
  confirmedBy?: string | null;
  confirmedAt?: string | null;
  /** The team's internal date for answering this, not the solicitation's. */
  dueAt?: string | null;
  history?: { at: string; event: string; detail: string }[];
}

/** How a response check came out. */
export type CheckStatus = "satisfied" | "partial" | "failed" | "not_found" | "unverifiable";

/** What kind of thing made the claim. */
export type DecidedBy = "rule" | "model" | "human";

/**
 * One row of the trace: a solicitation clause, and what the response does
 * about it.
 *
 * `decidedBy` is the field that keeps the row honest. A page count that was
 * counted and a model's reading of a narrative section are not the same kind
 * of claim, and a view that shows them identically invites a reader to trust
 * them equally.
 */
export interface ResponseCheck {
  id: string;
  analysisId: string;
  requirementId: string;
  responseVersion: number;

  /* The solicitation half. */
  reference: string;
  requirement: string;
  stakes: Stakes;
  citation: Citation;

  /* The response half. */
  status: CheckStatus;
  verification: Verification;
  decidedBy: DecidedBy;
  /** Which mechanical rule fired, when one did. */
  rule: string;
  detail: string;
  /** What is missing, in a sentence. Empty when nothing is. */
  gap: string;
  risk: "low" | "medium" | "high";
  owner: string | null;
  /** Where in the response it was answered. `located: false` means the quote could not be found. */
  evidence: {
    documentId?: string;
    documentName?: string;
    page?: number;
    section?: string;
    quote?: string;
    located?: boolean;
  };
  /** A mandatory requirement is never cleared without a person's name on it. */
  needsConfirmation: boolean;
  confirmedBy?: string | null;
  confirmedAt?: string | null;
  note?: string | null;
  history?: { at: string; event: string; detail: string }[];
}

/** The draft response bound to a solicitation, and the last check of it. */
export interface ResponseBinding {
  documentId?: string;
  fileName?: string;
  label?: string;
  version?: number;
  boundAt?: string;
  at?: string | null;
  summary?: {
    total: number;
    counts: Partial<Record<CheckStatus, number>>;
    /** Satisfied *and* signed off. Deliberately smaller than the satisfied count. */
    cleared: number;
    awaitingConfirmation: number;
    blocking: number;
    blockingReferences: string[];
  };
}

/**
 * One thing in an analysis that a machine could not settle.
 *
 * Margin produces several kinds of doubt and they used to live wherever they
 * were produced — an unlocated citation on a findings tab, an unreached page in
 * the coverage ledger, an unsigned mandatory requirement in the response trace.
 * A capture manager with four days left does not tour six tabs looking for
 * them, so they are collected into one list ordered by what it costs to be
 * wrong.
 */
export interface VerificationItem {
  id: string;
  kind: "coverage" | "ledger" | "amendment" | "gate" | "citation" | "requirement" | "response";
  severity: "blocking" | "important" | "routine";
  title: string;
  /** Why a rule or a model could not settle it. */
  why: string;
  /** What happens if nobody does anything. */
  consequence: string;
  /** Which workspace tab settles it. */
  tab: string;
  reference: string;
  citation?: Citation | null;
  owner?: string | null;
  detail: string;
}

export interface VerificationQueue {
  summary: { total: number; blocking: number; important: number; routine: number };
  items: VerificationItem[];
}

/**
 * A question is not finished when it is sent.
 *
 * The answer is the point, and an answer that never reaches the requirement it
 * was about has changed nothing — which is why a question can name the clause
 * it concerns.
 */
export type QuestionStatus = "draft" | "submitted" | "answered" | "withdrawn";

export interface QAQuestion {
  id: string;
  analysisId: string;
  text: string;
  rationale: string;
  sourceKind: "silent" | "contradiction" | "ambiguity" | "manual";
  goNoGoImpact: boolean;
  order: number;
  /** Kept in step with `status`; the lifecycle is the truth. */
  sent: boolean;
  citation?: Citation;

  status?: QuestionStatus;
  submittedAt?: string | null;
  answeredAt?: string | null;
  /** What the agency said, verbatim — never a paraphrase. */
  answer?: string | null;
  answerSource?: string;
  /** The requirement this question is about, when it is about one. */
  requirementId?: string | null;
  history?: { at: string; event: string; detail: string }[];
}

/** One person's outstanding work, across every live pursuit. */
export interface WorkItem {
  requirementId: string;
  analysisId: string;
  analysisTitle: string;
  solicitationNumber: string;
  reference: string;
  requirement: string;
  stakes: Stakes;
  verification: Verification;
  owner: string | null;
  status: MatrixStatus;
  dueAt: string | null;
  overdue: boolean;
  responseLocation: string;
}

/** One thing that happened to an analysis, and who did it. */
export interface AuditEntry {
  at: string;
  scope: "run" | "amendment" | "requirement" | "response" | "question";
  subject: string;
  event: string;
  detail: string;
  actor: string;
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
  format: "DOCX" | "PDF" | "MD";
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
