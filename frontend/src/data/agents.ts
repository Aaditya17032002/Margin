import type { AgentDescriptor, AgentId, AnalysisMode, ModeDescriptor } from "@/types";

export const AGENTS: AgentDescriptor[] = [
  {
    id: "intake",
    name: "Intake",
    duty: "Splits the file, reads the cover sheet, fixes the identity",
    lines: [
      "Opening the file — 214 pages, no OCR layer needed.",
      "Cover sheet reads Request for Proposal, not RFI.",
      "Solicitation number matches the SAM.gov posting.",
      "Attachments J-1 through J-9 detected and indexed.",
      "Amendment 0002 is folded into the body text.",
    ],
  },
  {
    id: "scope",
    name: "Scope",
    duty: "Separates what is actually being bought from the background",
    lines: [
      "Section C runs to 41 pages — reading the performance work statement.",
      "Three task areas; the third is optional and unpriced.",
      "Transition-in is 30 days, not the 60 the background section implies.",
      "Counting deliverables: 47 named artifacts across the base year.",
      "Period of performance: base year plus four options.",
    ],
  },
  {
    id: "compliance",
    name: "Compliance",
    duty: "Extracts every shall, must and will into a matrix",
    lines: [
      "Pulling obligations — 186 candidate requirements so far.",
      "Deduplicating restatements between Section C and Section L.",
      "Section L page limit is 40 pages excluding resumes.",
      "Font floor is 12pt Times New Roman; tables may drop to 10pt.",
      "Volume II must be submitted as a separate, unlinked file.",
    ],
  },
  {
    id: "eligibility",
    name: "Eligibility",
    duty: "Finds the gates that disqualify before anyone reads your prose",
    lines: [
      "Checking set-aside status against the NAICS size standard.",
      "SAM registration must be active at time of award.",
      "State facility licence required at proposal submission, not award.",
      "Joint ventures permitted only under an approved mentor-protégé.",
      "One gate is unmet on the current profile.",
    ],
  },
  {
    id: "evaluation",
    name: "Evaluation",
    duty: "Reconstructs how the award will actually be scored",
    lines: [
      "Section M declares best value tradeoff, not lowest price.",
      "Technical is significantly more important than price.",
      "Weighting the four non-price factors against each other.",
      "Past performance is rated, not scored — recency window is three years.",
      "Small business participation carries a pass/fail floor.",
    ],
  },
  {
    id: "risk",
    name: "Risk",
    duty: "Names what could go wrong while there is still time to act",
    lines: [
      "Cross-checking the delivery schedule against the transition window.",
      "Data rights clause conflicts with the commercial licence assumption.",
      "Liquidated damages are specified but the ceiling is not.",
      "Key personnel substitution requires contracting officer consent.",
      "Flagging three items for human review.",
    ],
  },
  {
    id: "verifier",
    name: "Verifier",
    duty: "Refuses to let a claim through without its clause",
    lines: [
      "Re-reading each finding against its cited line.",
      "Two findings cite a superseded paragraph — repointing.",
      "Confidence lowered on the ceiling value; the figure is inferred.",
      "Every retained finding now resolves to a page and a section.",
      "Verification pass complete.",
    ],
  },
  {
    id: "qa",
    name: "Q&A",
    duty: "Turns silence and contradiction into questions worth asking",
    lines: [
      "Collecting what the document never said.",
      "Incumbent is not named — that is a question.",
      "Section L and Section M disagree on volume count.",
      "Drafting eleven questions, four of which move the go/no-go.",
      "Ordering by impact.",
    ],
  },
];

export const AGENT_BY_ID = Object.fromEntries(AGENTS.map((a) => [a.id, a])) as Record<
  AgentId,
  AgentDescriptor
>;

export const MODES: ModeDescriptor[] = [
  {
    id: "quick-triage",
    name: "Quick Triage",
    blurb: "Is this worth a human hour? Identity, dates, and the hard gates only.",
    minutes: "≈ 40 seconds",
    passes: "One pass",
    agents: ["intake", "eligibility", "verifier"],
  },
  {
    id: "standard",
    name: "Standard",
    blurb: "The full read. Every section, the compliance matrix, risks, and questions.",
    minutes: "≈ 4 minutes",
    passes: "Two passes",
    agents: ["intake", "scope", "compliance", "eligibility", "evaluation", "risk", "verifier", "qa"],
  },
  {
    id: "deep-research",
    name: "Deep Research",
    blurb: "Standard, plus cross-referenced statutes, prior awards, and incumbent history.",
    minutes: "≈ 11 minutes",
    passes: "Four passes",
    agents: ["intake", "scope", "compliance", "eligibility", "evaluation", "risk", "verifier", "qa"],
  },
  {
    id: "matrix-only",
    name: "Matrix Only",
    blurb: "Every shall, must and will, cited and ready to assign. Nothing else.",
    minutes: "≈ 2 minutes",
    passes: "One pass",
    agents: ["intake", "compliance", "verifier"],
  },
  {
    id: "qa-only",
    name: "Q&A Only",
    blurb: "Silence, contradictions, and ambiguity — compiled into questions.",
    minutes: "≈ 2 minutes",
    passes: "One pass",
    agents: ["intake", "scope", "qa", "verifier"],
  },
  {
    id: "amendment-refresh",
    name: "Amendment Refresh",
    blurb: "Re-read against a new amendment and surface only what moved.",
    minutes: "≈ 90 seconds",
    passes: "Differential",
    agents: ["intake", "compliance", "evaluation", "verifier"],
  },
  {
    id: "recompete-compare",
    name: "Re-compete Compare",
    blurb: "Line the solicitation up against the prior award and your last proposal.",
    minutes: "≈ 6 minutes",
    passes: "Three passes",
    agents: ["intake", "scope", "compliance", "evaluation", "risk", "verifier"],
  },
];

export const MODE_BY_ID = Object.fromEntries(MODES.map((m) => [m.id, m])) as Record<
  AnalysisMode,
  ModeDescriptor
>;
