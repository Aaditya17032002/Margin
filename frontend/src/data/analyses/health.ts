import { offsetDays } from "@/lib/dates";
import { citationFactory } from "@/data/solicitations";
import type { Analysis, DocumentPage, MatrixRow, QAQuestion } from "@/types";

const ID = "an_samhsa_crisis";

const pages: DocumentPage[] = [
  {
    page: 1,
    heading: "Cover Sheet",
    lines: [
      "U.S. DEPARTMENT OF HEALTH AND HUMAN SERVICES",
      "Substance Abuse and Mental Health Services Administration",
      "REQUEST FOR PROPOSALS No. SAMHSA-26-RFP-0417",
      "Behavioral Health Crisis Response Data Exchange",
      "This acquisition is set aside one hundred percent for small business concerns.",
      "The applicable NAICS code is 541512 with a size standard of $34.0 million.",
      "Offers are due at the date and time specified in Section L of this solicitation.",
      "The Government intends to award a single indefinite-delivery, indefinite-quantity contract.",
    ],
  },
  {
    page: 9,
    heading: "Section C — Statement of Work",
    lines: [
      "C.1 The Contractor shall design and operate a national crisis response data exchange.",
      "C.2 The exchange shall interoperate with the 988 Suicide and Crisis Lifeline network.",
      "C.3 The Contractor shall support HL7 FHIR Release 4 resources for all clinical exchange.",
      "C.4 The Contractor shall onboard not fewer than 210 crisis centers during the base period.",
      "C.5 The Contractor shall achieve an authority to operate at the FedRAMP Moderate baseline.",
      "C.6 The authority to operate shall be obtained within one hundred eighty (180) days of award.",
      "C.7 The Contractor shall provide a 24x7x365 operations center staffed within the United States.",
      "C.8 All personnel with access to protected health information shall hold a favorable Tier 2 investigation.",
    ],
  },
  {
    page: 16,
    heading: "Section H — Special Contract Requirements",
    lines: [
      "H.1 The Contractor is a business associate under 45 C.F.R. Parts 160 and 164.",
      "H.2 A Business Associate Agreement shall be executed within ten (10) days of award.",
      "H.3 The Contractor shall comply with 42 C.F.R. Part 2 for substance use disorder records.",
      "H.4 Part 2 records shall be segregated from general protected health information at rest.",
      "H.5 The Contractor shall report any breach affecting more than 500 individuals within 24 hours.",
      "H.6 Section 508 conformance is required for all public-facing and staff-facing interfaces.",
      "H.7 The Contractor shall not subcontract more than fifty percent of the total contract value.",
    ],
  },
  {
    page: 24,
    heading: "Section L — Instructions to Offerors",
    lines: [
      "L.1 Proposals shall be submitted electronically through the designated portal.",
      "L.2 The technical volume shall not exceed thirty (30) pages, single spaced.",
      "L.3 Offerors shall submit three (3) past performance references of similar scope and complexity.",
      "L.4 Similar scope means a federal health information exchange valued at $5 million or greater.",
      "L.5 Questions shall be submitted in writing not later than the date stated in the schedule.",
      "L.6 Oral presentations are required of all offerors found to be in the competitive range.",
      "L.7 The small business subcontracting plan does not apply to this set-aside acquisition.",
    ],
  },
  {
    page: 29,
    heading: "Section M — Evaluation Factors for Award",
    lines: [
      "M.1 Award will be made on a best value tradeoff basis.",
      "M.2 Technical Approach is significantly more important than Price.",
      "M.3 Factor 1 — Technical Approach and Interoperability.",
      "M.4 Factor 2 — Security, Privacy, and FedRAMP Path.",
      "M.5 Factor 3 — Management Approach and Key Personnel.",
      "M.6 Factor 4 — Past Performance, rated rather than scored.",
      "M.7 Price will be evaluated for reasonableness and realism but not scored.",
      "M.8 An offeror rated Unacceptable in any technical factor is ineligible for award.",
    ],
  },
];

const cite = citationFactory(pages);

export const healthAnalysis: Analysis = {
  id: ID,
  title: "Behavioral Health Crisis Response Data Exchange",
  solicitationNumber: "SAMHSA-26-RFP-0417",
  agency: "Health & Human Services",
  subAgency: "SAMHSA",
  docType: "RFP",
  mode: "standard",
  stage: "review",
  goNoGo: "bid",
  decisionNote:
    "Bid. Set-aside fits, the FHIR work is squarely in the practice, and the FedRAMP path is already underway with the Ohio ATO package.",
  createdAt: offsetDays(-14, 10, 5),
  updatedAt: offsetDays(-2, 16, 22),
  owner: "Priya Raman",
  collaborators: ["Amara Osei", "Lena Ford"],
  naics: "541512 — Computer Systems Design Services",
  setAside: "100% Small Business",
  placeOfPerformance: "Rockville, MD & remote",
  estimatedValue: 12_400_000,
  pageCount: 96,
  fileName: "SAMHSA-26-RFP-0417.pdf",
  fileSize: 7_120_000,
  source: "outlook",
  tags: ["Health", "HIPAA", "42 CFR Part 2", "FedRAMP"],

  summary:
    "A single-award IDIQ to build and run a national crisis data exchange interoperating with the 988 Lifeline. Small business set-aside, best value with price unscored. The binding constraint is a FedRAMP Moderate ATO within 180 days of award, and 42 C.F.R. Part 2 segregation sits on top of ordinary HIPAA obligations.",

  identity: [
    {
      id: "f_h_1",
      label: "Instrument",
      value: "Single-award IDIQ, 100% small business set-aside",
      confidence: 0.97,
      stakes: "informational",
      citation: cite("c_h_1", 1, "§ Cover", 7),
      verified: true,
    },
    {
      id: "f_h_2",
      label: "Size standard",
      value: "NAICS 541512 — $34.0M three-year average receipts",
      detail: "Our trailing three-year average is $28.6M. Headroom, but not much beyond this award.",
      confidence: 0.96,
      stakes: "disqualifying",
      citation: cite("c_h_2", 1, "§ Cover", 5),
      verified: true,
    },
    {
      id: "f_h_3",
      label: "Award basis",
      value: "Best value tradeoff; technical significantly more important than price",
      confidence: 0.95,
      stakes: "scored",
      citation: cite("c_h_3", 29, "§ M.1–M.2", 0, 2),
      verified: true,
    },
  ],

  scope: [
    {
      id: "f_h_10",
      label: "Core deliverable",
      value: "National crisis response data exchange interoperating with the 988 Lifeline",
      confidence: 0.96,
      stakes: "scored",
      citation: cite("c_h_10", 9, "§ C.1–C.2", 0, 2),
      verified: true,
    },
    {
      id: "f_h_11",
      label: "Interoperability standard",
      value: "HL7 FHIR Release 4 for all clinical exchange",
      confidence: 0.94,
      stakes: "disqualifying",
      citation: cite("c_h_11", 9, "§ C.3", 2),
      verified: true,
    },
    {
      id: "f_h_12",
      label: "Onboarding volume",
      value: "Not fewer than 210 crisis centers in the base period",
      detail: "No cohorting or readiness criteria given — see the SILENT ledger.",
      confidence: 0.89,
      stakes: "scored",
      citation: cite("c_h_12", 9, "§ C.4", 3),
    },
    {
      id: "f_h_13",
      label: "Operations centre",
      value: "24x7x365, staffed within the United States",
      confidence: 0.95,
      stakes: "scored",
      citation: cite("c_h_13", 9, "§ C.7", 6),
      verified: true,
    },
  ],

  legal: [
    {
      id: "f_h_20",
      label: "HIPAA posture",
      value: "Business associate under 45 C.F.R. Parts 160 and 164; BAA within 10 days of award",
      confidence: 0.97,
      stakes: "disqualifying",
      citation: cite("c_h_20", 16, "§ H.1–H.2", 0, 2),
      verified: true,
    },
    {
      id: "f_h_21",
      label: "42 C.F.R. Part 2",
      value: "SUD records must be segregated from general PHI at rest",
      detail:
        "Segregation at rest is a stronger requirement than the usual access-control framing, and it constrains the data model rather than the application layer.",
      confidence: 0.86,
      stakes: "disqualifying",
      citation: cite("c_h_21", 16, "§ H.3–H.4", 2, 2),
      flagged: true,
    },
    {
      id: "f_h_22",
      label: "Breach reporting",
      value: "24 hours for any breach affecting more than 500 individuals",
      confidence: 0.93,
      stakes: "disqualifying",
      citation: cite("c_h_22", 16, "§ H.5", 4),
      verified: true,
    },
    {
      id: "f_h_23",
      label: "Section 508",
      value: "Required for public-facing and staff-facing interfaces alike",
      confidence: 0.94,
      stakes: "scored",
      citation: cite("c_h_23", 16, "§ H.6", 5),
    },
    {
      id: "f_h_24",
      label: "Limitation on subcontracting",
      value: "No more than 50% of total contract value may be subcontracted",
      confidence: 0.92,
      stakes: "disqualifying",
      citation: cite("c_h_24", 16, "§ H.7", 6),
      verified: true,
    },
  ],

  eligibility: [
    {
      id: "f_h_30",
      label: "Set-aside eligibility",
      value: "Small business under NAICS 541512 — we qualify",
      confidence: 0.96,
      stakes: "disqualifying",
      citation: cite("c_h_30", 1, "§ Cover", 4),
      verified: true,
    },
    {
      id: "f_h_31",
      label: "Personnel clearance",
      value: "Favorable Tier 2 investigation for anyone touching PHI",
      detail: "Fourteen of nineteen proposed staff are already adjudicated; five need sponsorship.",
      confidence: 0.9,
      stakes: "disqualifying",
      citation: cite("c_h_31", 9, "§ C.8", 7),
      flagged: true,
    },
    {
      id: "f_h_32",
      label: "Past performance threshold",
      value: "Three references, each a federal health exchange of $5M or greater",
      detail: "We have two that clearly qualify and a third at $4.6M that does not.",
      confidence: 0.88,
      stakes: "disqualifying",
      citation: cite("c_h_32", 24, "§ L.3–L.4", 2, 2),
      flagged: true,
    },
  ],

  pricing: [
    {
      id: "f_h_40",
      label: "Price treatment",
      value: "Evaluated for reasonableness and realism — not scored",
      detail: "Realism analysis means an underbid reads as a technical risk, not a discount.",
      confidence: 0.93,
      stakes: "scored",
      citation: cite("c_h_40", 29, "§ M.7", 6),
      verified: true,
    },
  ],

  postAward: [
    {
      id: "f_h_50",
      label: "FedRAMP milestone",
      value: "Moderate baseline ATO within 180 days of award",
      confidence: 0.95,
      stakes: "disqualifying",
      citation: cite("c_h_50", 9, "§ C.5–C.6", 4, 2),
      verified: true,
    },
  ],

  gates: [
    {
      id: "g_h_1",
      question: "Do we clear every hard eligibility gate?",
      answer:
        "Yes, with one repair. Set-aside and size standard are clear; the third past performance reference needs to be swapped for a qualifying engagement.",
      met: true,
      weight: "hard",
      citation: cite("c_h_g1", 24, "§ L.4", 3),
    },
    {
      id: "g_h_2",
      question: "Is the timeline realistic?",
      answer:
        "Yes. 180 days to a Moderate ATO is aggressive but the Ohio package reuses 71% of the control set.",
      met: true,
      weight: "hard",
      citation: cite("c_h_g2", 9, "§ C.6", 5),
    },
    {
      id: "g_h_3",
      question: "Does the scope sit inside our practice?",
      answer: "Squarely. FHIR R4 exchange and 24x7 operations are the core of the health practice.",
      met: true,
      weight: "soft",
      citation: cite("c_h_g3", 9, "§ C.3", 2),
    },
    {
      id: "g_h_4",
      question: "Is the economics defensible?",
      answer:
        "Yes. Price is unscored and evaluated for realism, which favours a properly staffed bid over a thin one.",
      met: true,
      weight: "hard",
      citation: cite("c_h_g4", 29, "§ M.7", 6),
    },
  ],

  evaluation: [
    { id: "e_h_1", name: "Technical Approach & Interoperability", weight: 40, method: "Adjectival", citation: cite("c_h_e1", 29, "§ M.3", 2) },
    { id: "e_h_2", name: "Security, Privacy & FedRAMP Path", weight: 30, method: "Adjectival", citation: cite("c_h_e2", 29, "§ M.4", 3) },
    { id: "e_h_3", name: "Management & Key Personnel", weight: 20, method: "Adjectival", citation: cite("c_h_e3", 29, "§ M.5", 4) },
    { id: "e_h_4", name: "Past Performance", weight: 10, method: "Confidence rating", citation: cite("c_h_e4", 29, "§ M.6", 5) },
  ],

  risks: [
    {
      id: "r_h_1",
      title: "Part 2 segregation constrains the data model, not just access control",
      narrative:
        "H.4 requires substance use disorder records to be segregated from general PHI at rest. Our reference architecture separates logically within a single store, which satisfies access control but arguably not segregation at rest.",
      severity: "critical",
      likelihood: "possible",
      mitigation:
        "Confirm whether logical separation with independent key material satisfies H.4, or budget for a physically separate store.",
      citation: cite("c_h_r1", 16, "§ H.4", 3),
    },
    {
      id: "r_h_2",
      title: "Third past performance reference falls below the $5M floor",
      narrative:
        "L.4 defines similar scope as a federal health information exchange of $5 million or greater. Our third-strongest reference is $4.6M, which risks a reference being disregarded entirely.",
      severity: "elevated",
      likelihood: "likely",
      mitigation: "Substitute the state HIE engagement at $6.1M and re-check recency.",
      citation: cite("c_h_r2", 24, "§ L.4", 3),
    },
    {
      id: "r_h_3",
      title: "Five key staff require Tier 2 sponsorship",
      narrative:
        "C.8 requires a favorable Tier 2 investigation for PHI access. Five proposed staff are unadjudicated, and sponsorship timelines have run 90–140 days.",
      severity: "moderate",
      likelihood: "likely",
      mitigation: "Name adjudicated alternates as key personnel and hold the five for post-ATO roles.",
      citation: cite("c_h_r3", 9, "§ C.8", 7),
    },
    {
      id: "r_h_4",
      title: "Unacceptable in any factor ends the bid",
      narrative:
        "M.8 makes any single Unacceptable technical rating fatal, which removes the usual tradeoff cushion from a strong overall proposal.",
      severity: "moderate",
      likelihood: "unlikely",
      mitigation: "Run a colour-team review scored factor by factor rather than in aggregate.",
      citation: cite("c_h_r4", 29, "§ M.8", 7),
    },
  ],

  silent: [
    {
      id: "s_h_1",
      topic: "Crisis center onboarding sequence",
      expectation: "210 centers are required with no cohorts, priority order, or readiness criteria.",
      consequence: "The onboarding plan must assume the worst-case simultaneous ramp.",
    },
    {
      id: "s_h_2",
      topic: "Existing 988 network interfaces",
      expectation: "C.2 requires interoperation but no interface specification or version is named.",
      consequence: "Integration effort cannot be estimated with confidence.",
    },
    {
      id: "s_h_3",
      topic: "Expected transaction volume",
      expectation: "A national exchange normally states peak and sustained message volumes.",
      consequence: "Capacity, and therefore price realism, rests on our own assumptions.",
    },
    {
      id: "s_h_4",
      topic: "IDIQ ceiling and minimum guarantee",
      expectation: "An IDIQ ordinarily states both a ceiling and a guaranteed minimum.",
      consequence: "Revenue floor is unknown; the bid must be justifiable at the minimum.",
    },
  ],

  dates: [
    {
      id: "d_h_1",
      label: "Questions due",
      at: offsetDays(-2, 21, 0),
      timezone: "America/New_York",
      kind: "questions-due",
      citation: cite("c_h_d1", 24, "§ L.5", 4),
    },
    {
      id: "d_h_2",
      label: "Proposal due",
      at: offsetDays(9, 21, 0),
      timezone: "America/New_York",
      kind: "proposal-due",
      citation: cite("c_h_d2", 24, "§ L.1", 0),
    },
    {
      id: "d_h_3",
      label: "Oral presentations (competitive range)",
      at: offsetDays(31, 14, 0),
      timezone: "America/New_York",
      kind: "site-visit",
      citation: cite("c_h_d3", 24, "§ L.6", 5),
    },
  ],

  clins: [
    { id: "cl_h_1", number: "0001", description: "Exchange design & build", quantity: "1 lot", ceiling: 4_200_000 },
    { id: "cl_h_2", number: "0002", description: "Crisis center onboarding", quantity: "210 sites", ceiling: 3_100_000 },
    { id: "cl_h_3", number: "0003", description: "24x7 operations centre", quantity: "12 months", ceiling: 2_800_000 },
    { id: "cl_h_4", number: "0004", description: "FedRAMP Moderate authorisation support", quantity: "1 lot", ceiling: 1_150_000 },
  ],

  amendments: [],
  pages,

  versions: [
    { id: "v_h_1", label: "Initial analysis", at: offsetDays(-14, 10, 40), author: "Margin", note: "Standard pass. 94 requirements extracted." },
    { id: "v_h_2", label: "Reviewer pass — Lena Ford", at: offsetDays(-9, 15, 5), author: "Lena Ford", note: "Verified the privacy section; flagged Part 2 segregation." },
    { id: "v_h_3", label: "Decision recorded — Bid", at: offsetDays(-2, 16, 22), author: "Priya Raman", note: "Bid approved at the capture review." },
  ],
};

export const healthMatrix: MatrixRow[] = [
  { id: "m_h_1", analysisId: ID, reference: "C.3", requirement: "Support HL7 FHIR Release 4 resources for all clinical exchange.", type: "shall", stakes: "disqualifying", owner: "Priya Raman", responseLocation: "Tech Vol § 2.2", status: "complete", citation: cite("cm_h_1", 9, "§ C.3", 2) },
  { id: "m_h_2", analysisId: ID, reference: "C.4", requirement: "Onboard not fewer than 210 crisis centers during the base period.", type: "shall", stakes: "scored", owner: "Lena Ford", responseLocation: "Tech Vol § 4.1", status: "drafted", citation: cite("cm_h_2", 9, "§ C.4", 3) },
  { id: "m_h_3", analysisId: ID, reference: "C.5", requirement: "Achieve an authority to operate at the FedRAMP Moderate baseline.", type: "shall", stakes: "disqualifying", owner: "Amara Osei", responseLocation: "Tech Vol § 3.1", status: "in-review", citation: cite("cm_h_3", 9, "§ C.5", 4) },
  { id: "m_h_4", analysisId: ID, reference: "C.6", requirement: "Obtain the authority to operate within 180 days of award.", type: "shall", stakes: "disqualifying", owner: "Amara Osei", responseLocation: "Tech Vol § 3.2", status: "in-review", citation: cite("cm_h_4", 9, "§ C.6", 5) },
  { id: "m_h_5", analysisId: ID, reference: "C.7", requirement: "Provide a 24x7x365 operations center staffed within the United States.", type: "shall", stakes: "scored", owner: "Lena Ford", responseLocation: "Tech Vol § 5.1", status: "drafted", citation: cite("cm_h_5", 9, "§ C.7", 6) },
  { id: "m_h_6", analysisId: ID, reference: "C.8", requirement: "Ensure all personnel with PHI access hold a favorable Tier 2 investigation.", type: "shall", stakes: "disqualifying", owner: "Amara Osei", responseLocation: "Tech Vol § 6.3", status: "assigned", citation: cite("cm_h_6", 9, "§ C.8", 7) },
  { id: "m_h_7", analysisId: ID, reference: "H.2", requirement: "Execute a Business Associate Agreement within ten days of award.", type: "shall", stakes: "disqualifying", owner: "Priya Raman", responseLocation: "Admin Vol § 1.2", status: "complete", citation: cite("cm_h_7", 16, "§ H.2", 1) },
  { id: "m_h_8", analysisId: ID, reference: "H.4", requirement: "Segregate 42 C.F.R. Part 2 records from general PHI at rest.", type: "shall", stakes: "disqualifying", owner: "Priya Raman", responseLocation: "Tech Vol § 3.6", status: "in-review", citation: cite("cm_h_8", 16, "§ H.4", 3), note: "Architecture decision pending — see Q-01." },
  { id: "m_h_9", analysisId: ID, reference: "H.5", requirement: "Report any breach affecting more than 500 individuals within 24 hours.", type: "shall", stakes: "disqualifying", owner: "Lena Ford", responseLocation: "Tech Vol § 3.8", status: "drafted", citation: cite("cm_h_9", 16, "§ H.5", 4) },
  { id: "m_h_10", analysisId: ID, reference: "H.6", requirement: "Conform all public-facing and staff-facing interfaces to Section 508.", type: "shall", stakes: "scored", owner: null, responseLocation: "", status: "unassigned", citation: cite("cm_h_10", 16, "§ H.6", 5) },
  { id: "m_h_11", analysisId: ID, reference: "H.7", requirement: "Subcontract no more than fifty percent of total contract value.", type: "shall", stakes: "disqualifying", owner: "Amara Osei", responseLocation: "Admin Vol § 2.1", status: "complete", citation: cite("cm_h_11", 16, "§ H.7", 6) },
  { id: "m_h_12", analysisId: ID, reference: "L.2", requirement: "Limit the technical volume to thirty pages, single spaced.", type: "shall", stakes: "disqualifying", owner: "Lena Ford", responseLocation: "Production checklist", status: "assigned", citation: cite("cm_h_12", 24, "§ L.2", 1) },
  { id: "m_h_13", analysisId: ID, reference: "L.3", requirement: "Submit three past performance references of similar scope and complexity.", type: "shall", stakes: "disqualifying", owner: "Priya Raman", responseLocation: "PP Vol § 1", status: "in-review", citation: cite("cm_h_13", 24, "§ L.3", 2) },
  { id: "m_h_14", analysisId: ID, reference: "L.6", requirement: "Oral presentations are required of all offerors in the competitive range.", type: "shall", stakes: "scored", owner: "Priya Raman", responseLocation: "Capture plan", status: "assigned", citation: cite("cm_h_14", 24, "§ L.6", 5) },
  { id: "m_h_15", analysisId: ID, reference: "M.8", requirement: "Avoid an Unacceptable rating in any technical factor.", type: "shall", stakes: "disqualifying", owner: "Priya Raman", responseLocation: "Review plan", status: "assigned", citation: cite("cm_h_15", 29, "§ M.8", 7) },
];

export const healthQuestions: QAQuestion[] = [
  {
    id: "q_h_1",
    analysisId: ID,
    text: "Does segregation of 42 C.F.R. Part 2 records at rest under H.4 permit logical separation within a single data store using independent key material, or is a physically separate store required?",
    rationale: "Determines whether the reference architecture can be reused or must be rebuilt.",
    sourceKind: "ambiguity",
    goNoGoImpact: true,
    order: 0,
    sent: true,
    citation: cite("cq_h_1", 16, "§ H.4", 3),
  },
  {
    id: "q_h_2",
    analysisId: ID,
    text: "Will the Government state the IDIQ ceiling and the guaranteed minimum for this acquisition?",
    rationale: "Price realism cannot be assessed without a revenue floor.",
    sourceKind: "silent",
    goNoGoImpact: true,
    order: 1,
    sent: true,
  },
  {
    id: "q_h_3",
    analysisId: ID,
    text: "Can the Government provide the interface specification and version currently in use by the 988 Lifeline network?",
    rationale: "C.2 requires interoperation without naming the interface.",
    sourceKind: "silent",
    goNoGoImpact: false,
    order: 2,
    sent: true,
    citation: cite("cq_h_3", 9, "§ C.2", 1),
  },
  {
    id: "q_h_4",
    analysisId: ID,
    text: "What peak and sustained message volumes should offerors assume for capacity planning?",
    rationale: "Capacity assumptions drive both the technical approach and price realism.",
    sourceKind: "silent",
    goNoGoImpact: false,
    order: 3,
    sent: true,
  },
  {
    id: "q_h_5",
    analysisId: ID,
    text: "Will the Government sponsor Tier 2 investigations for contractor personnel, and if so, at what point in the schedule?",
    rationale: "Five proposed staff are unadjudicated and sponsorship has historically run 90–140 days.",
    sourceKind: "ambiguity",
    goNoGoImpact: false,
    order: 4,
    sent: true,
    citation: cite("cq_h_5", 9, "§ C.8", 7),
  },
];
