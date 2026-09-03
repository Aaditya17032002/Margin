import { offsetDays } from "@/lib/dates";
import { citationFactory } from "@/data/solicitations";
import type { Analysis, DocumentPage, MatrixRow, QAQuestion } from "@/types";

/* ------------------------------------------------------------------ */
/* Zero Trust task order — GSA / CISA                                   */
/* ------------------------------------------------------------------ */

const IT_ID = "an_cisa_zt";

const itPages: DocumentPage[] = [
  {
    page: 1,
    heading: "Task Order Request",
    lines: [
      "GENERAL SERVICES ADMINISTRATION — FEDERAL SYSTEMS INTEGRATION",
      "TASK ORDER REQUEST TOR-26-CISA-0088 under Alliant 2",
      "Zero Trust Network Modernization — Phase II",
      "Competition is limited to Alliant 2 Unrestricted contract holders.",
      "This task order will be issued on a firm fixed price basis with cost-reimbursable travel.",
      "Quotes are due within fourteen (14) calendar days of the release date.",
    ],
  },
  {
    page: 5,
    heading: "Performance Work Statement",
    lines: [
      "1.1 The Contractor shall implement identity-based microsegmentation across four enclaves.",
      "1.2 The architecture shall align to CISA Zero Trust Maturity Model version 2.0 at the Advanced stage.",
      "1.3 The Contractor shall achieve continuous diagnostics and mitigation integration within 120 days.",
      "1.4 Phase II builds directly on the Phase I baseline delivered by the incumbent.",
      "1.5 The Contractor shall provide monthly maturity assessments against the model.",
      "1.6 All work shall be performed by personnel holding an active Top Secret clearance.",
      "1.7 Facility clearance at the Top Secret level is required at time of quote.",
    ],
  },
  {
    page: 9,
    heading: "Evaluation",
    lines: [
      "2.1 Award will be made to the quoter representing the best value to the Government.",
      "2.2 Technical Approach — most important factor.",
      "2.3 Key Personnel and Clearance Posture — second most important.",
      "2.4 Price — evaluated for reasonableness, least important.",
      "2.5 A quoter without a Top Secret facility clearance will be found unacceptable without further evaluation.",
    ],
  },
];

const itCite = citationFactory(itPages);

export const itAnalysis: Analysis = {
  id: IT_ID,
  title: "Zero Trust Network Modernization — Phase II",
  solicitationNumber: "TOR-26-CISA-0088",
  agency: "GSA / DHS CISA",
  subAgency: "Alliant 2 Unrestricted",
  docType: "Task Order",
  mode: "quick-triage",
  stage: "triage",
  goNoGo: "undecided",
  createdAt: offsetDays(-1, 8, 15),
  updatedAt: offsetDays(-1, 8, 22),
  owner: "Marcus Bell",
  collaborators: [],
  naics: "541519 — Other Computer Related Services",
  setAside: "Alliant 2 Unrestricted holders only",
  placeOfPerformance: "Arlington, VA",
  estimatedValue: 8_900_000,
  pageCount: 34,
  fileName: "TOR-26-CISA-0088.pdf",
  fileSize: 2_310_000,
  source: "outlook",
  tags: ["IT", "Zero Trust", "TS facility clearance"],

  summary:
    "A fourteen-day turnaround Phase II task order under Alliant 2. Triage found one hard stop: a Top Secret facility clearance is required at time of quote, and ours is Secret. Everything else in the document is inside our capability.",

  identity: [
    { id: "f_it_1", label: "Instrument", value: "Task order under Alliant 2 Unrestricted, firm fixed price", confidence: 0.96, stakes: "informational", citation: itCite("c_it_1", 1, "§ TOR", 1), verified: true },
    { id: "f_it_2", label: "Vehicle eligibility", value: "Alliant 2 Unrestricted holders only — we hold the vehicle", confidence: 0.97, stakes: "disqualifying", citation: itCite("c_it_2", 1, "§ TOR", 3), verified: true },
    { id: "f_it_3", label: "Response window", value: "14 calendar days from release", detail: "Nine days remain. A full technical volume in nine days requires the reserve team.", confidence: 0.95, stakes: "scored", citation: itCite("c_it_3", 1, "§ TOR", 5), verified: true },
  ],
  scope: [
    { id: "f_it_10", label: "Core work", value: "Identity-based microsegmentation across four enclaves", confidence: 0.94, stakes: "scored", citation: itCite("c_it_10", 5, "§ 1.1", 0), verified: true },
    { id: "f_it_11", label: "Maturity target", value: "CISA Zero Trust Maturity Model v2.0, Advanced stage", confidence: 0.92, stakes: "scored", citation: itCite("c_it_11", 5, "§ 1.2", 1) },
    { id: "f_it_12", label: "Dependency", value: "Phase II builds on the incumbent's Phase I baseline", detail: "No baseline documentation is attached. The bidder inherits an undocumented environment.", confidence: 0.78, stakes: "disqualifying", citation: itCite("c_it_12", 5, "§ 1.4", 3), flagged: true },
  ],
  legal: [
    { id: "f_it_20", label: "Personnel clearance", value: "Active Top Secret required for all performing staff", confidence: 0.96, stakes: "disqualifying", citation: itCite("c_it_20", 5, "§ 1.6", 5), verified: true },
    { id: "f_it_21", label: "Facility clearance", value: "Top Secret facility clearance required at time of quote", detail: "Our facility clearance is Secret. This is a hard stop at submission, not at award.", confidence: 0.97, stakes: "disqualifying", citation: itCite("c_it_21", 5, "§ 1.7", 6), verified: true, flagged: true },
  ],
  eligibility: [
    { id: "f_it_30", label: "Facility clearance gate", value: "Unmet — quoters without TS FCL are unacceptable without further evaluation", confidence: 0.97, stakes: "disqualifying", citation: itCite("c_it_30", 9, "§ 2.5", 4), verified: true },
  ],
  pricing: [
    { id: "f_it_40", label: "Price treatment", value: "Reasonableness only; least important factor", confidence: 0.93, stakes: "informational", citation: itCite("c_it_40", 9, "§ 2.4", 3) },
  ],
  postAward: [
    { id: "f_it_50", label: "CDM integration", value: "Continuous diagnostics and mitigation integration within 120 days", confidence: 0.9, stakes: "scored", citation: itCite("c_it_50", 5, "§ 1.3", 2) },
  ],
  gates: [
    { id: "g_it_1", question: "Do we clear every hard eligibility gate?", answer: "No. A Top Secret facility clearance is required at time of quote; ours is Secret and sponsorship takes months.", met: false, weight: "hard", citation: itCite("c_it_g1", 5, "§ 1.7", 6) },
    { id: "g_it_2", question: "Is the timeline realistic?", answer: "Marginal. Nine of fourteen days remain and the Phase I baseline is undocumented.", met: false, weight: "hard", citation: itCite("c_it_g2", 1, "§ TOR", 5) },
    { id: "g_it_3", question: "Does the scope sit inside our practice?", answer: "Yes. Microsegmentation and ZTMM alignment are core to the federal security practice.", met: true, weight: "soft", citation: itCite("c_it_g3", 5, "§ 1.1", 0) },
    { id: "g_it_4", question: "Is the economics defensible?", answer: "Yes on paper — $8.9M firm fixed price with price as the least important factor.", met: true, weight: "hard", citation: itCite("c_it_g4", 9, "§ 2.4", 3) },
  ],
  evaluation: [
    { id: "e_it_1", name: "Technical Approach", weight: 50, method: "Adjectival", citation: itCite("c_it_e1", 9, "§ 2.2", 1) },
    { id: "e_it_2", name: "Key Personnel & Clearance Posture", weight: 35, method: "Adjectival", citation: itCite("c_it_e2", 9, "§ 2.3", 2) },
    { id: "e_it_3", name: "Price", weight: 15, method: "Reasonableness", citation: itCite("c_it_e3", 9, "§ 2.4", 3) },
  ],
  risks: [
    { id: "r_it_1", title: "Facility clearance is a hard stop at quote", narrative: "Paragraph 2.5 removes any evaluation path for a quoter without a Top Secret facility clearance. Sponsorship cannot be completed inside the response window.", severity: "critical", likelihood: "likely", mitigation: "Team as a subcontractor under a cleared prime, or decline.", citation: itCite("c_it_r1", 9, "§ 2.5", 4) },
    { id: "r_it_2", title: "Undocumented Phase I baseline", narrative: "1.4 makes Phase II dependent on work delivered by the incumbent, but no as-built documentation is attached to the request.", severity: "elevated", likelihood: "likely", mitigation: "Ask for the Phase I as-built package or a redacted architecture summary.", citation: itCite("c_it_r2", 5, "§ 1.4", 3) },
  ],
  silent: [
    { id: "s_it_1", topic: "Phase I as-built documentation", expectation: "A phased follow-on normally attaches the prior baseline.", consequence: "Technical approach must be written against assumptions." },
    { id: "s_it_2", topic: "Enclave inventory", expectation: "Four enclaves are named without size, population, or system counts.", consequence: "Level of effort is unpriceable." },
    { id: "s_it_3", topic: "Incumbent identity", expectation: "The Phase I contractor is never named.", consequence: "No read on the competitive field." },
  ],
  dates: [
    { id: "d_it_1", label: "Quote due", at: offsetDays(9, 21, 0), timezone: "America/New_York", kind: "proposal-due", citation: itCite("c_it_d1", 1, "§ TOR", 5) },
  ],
  clins: [
    { id: "cl_it_1", number: "0001", description: "Microsegmentation implementation", quantity: "4 enclaves", ceiling: 6_400_000 },
    { id: "cl_it_2", number: "0002", description: "CDM integration", quantity: "1 lot", ceiling: 1_900_000 },
    { id: "cl_it_3", number: "0003", description: "Travel (cost reimbursable)", quantity: "NTE", ceiling: 600_000 },
  ],
  amendments: [],
  pages: itPages,
  versions: [
    { id: "v_it_1", label: "Quick triage", at: offsetDays(-1, 8, 22), author: "Margin", note: "Triage pass. One hard gate unmet; escalated for a bid/no-bid call." },
  ],
};

export const itMatrix: MatrixRow[] = [
  { id: "m_it_1", analysisId: IT_ID, reference: "1.1", requirement: "Implement identity-based microsegmentation across four enclaves.", type: "shall", stakes: "scored", owner: "Marcus Bell", responseLocation: "Tech § 2", status: "assigned", citation: itCite("cm_it_1", 5, "§ 1.1", 0) },
  { id: "m_it_2", analysisId: IT_ID, reference: "1.2", requirement: "Align the architecture to CISA ZTMM v2.0 at the Advanced stage.", type: "shall", stakes: "scored", owner: null, responseLocation: "", status: "unassigned", citation: itCite("cm_it_2", 5, "§ 1.2", 1) },
  { id: "m_it_3", analysisId: IT_ID, reference: "1.3", requirement: "Achieve CDM integration within 120 days.", type: "shall", stakes: "scored", owner: null, responseLocation: "", status: "unassigned", citation: itCite("cm_it_3", 5, "§ 1.3", 2) },
  { id: "m_it_4", analysisId: IT_ID, reference: "1.6", requirement: "Staff all work with personnel holding an active Top Secret clearance.", type: "shall", stakes: "disqualifying", owner: "Marcus Bell", responseLocation: "Tech § 5", status: "in-review", citation: itCite("cm_it_4", 5, "§ 1.6", 5) },
  { id: "m_it_5", analysisId: IT_ID, reference: "1.7", requirement: "Hold a Top Secret facility clearance at time of quote.", type: "shall", stakes: "disqualifying", owner: "Marcus Bell", responseLocation: "Admin § 1", status: "in-review", citation: itCite("cm_it_5", 5, "§ 1.7", 6), note: "Currently unmet. Teaming is the only route." },
  { id: "m_it_6", analysisId: IT_ID, reference: "1.5", requirement: "Provide monthly maturity assessments against the model.", type: "shall", stakes: "informational", owner: null, responseLocation: "", status: "unassigned", citation: itCite("cm_it_6", 5, "§ 1.5", 4) },
];

export const itQuestions: QAQuestion[] = [
  { id: "q_it_1", analysisId: IT_ID, text: "Will the Government accept a quoter whose facility clearance is at the Secret level where all performing personnel hold active Top Secret clearances?", rationale: "Determines whether we can quote at all.", sourceKind: "ambiguity", goNoGoImpact: true, order: 0, sent: false, citation: itCite("cq_it_1", 5, "§ 1.7", 6) },
  { id: "q_it_2", analysisId: IT_ID, text: "Can the Government release the Phase I as-built architecture package, or a redacted summary, to quoters?", rationale: "Phase II is defined entirely by reference to a baseline that is not attached.", sourceKind: "silent", goNoGoImpact: true, order: 1, sent: false, citation: itCite("cq_it_2", 5, "§ 1.4", 3) },
  { id: "q_it_3", analysisId: IT_ID, text: "What is the system and user population of each of the four enclaves?", rationale: "Level of effort cannot be estimated from the enclave count alone.", sourceKind: "silent", goNoGoImpact: false, order: 2, sent: false, citation: itCite("cq_it_3", 5, "§ 1.1", 0) },
];

/* ------------------------------------------------------------------ */
/* Bridge deck rehabilitation — INDOT                                   */
/* ------------------------------------------------------------------ */

const PW_ID = "an_indot_bridge";

const pwPages: DocumentPage[] = [
  {
    page: 1,
    heading: "Invitation for Bids",
    lines: [
      "INDIANA DEPARTMENT OF TRANSPORTATION",
      "INVITATION FOR BIDS No. INDOT-R-42817",
      "Bridge Deck Rehabilitation — US-31 Corridor, Marion and Hamilton Counties",
      "Award will be made to the lowest responsive and responsible bidder.",
      "Bids shall be accompanied by a bid bond in the amount of five percent (5%) of the total bid.",
      "Bidders shall be prequalified by the Department in Work Type B-1 prior to bid opening.",
    ],
  },
  {
    page: 6,
    heading: "Special Provisions",
    lines: [
      "3.1 The Contractor shall complete all deck work within one hundred ten (110) calendar days.",
      "3.2 Lane closures are prohibited between 6:00 a.m. and 9:00 a.m. and between 3:30 p.m. and 6:30 p.m.",
      "3.3 Liquidated damages of $8,400 per calendar day shall apply to any overrun.",
      "3.4 The Contractor shall self-perform not less than thirty percent (30%) of the contract value.",
      "3.5 A Disadvantaged Business Enterprise goal of 9.0% applies to this contract.",
      "3.6 All structural steel shall comply with the Buy America requirements of 23 C.F.R. 635.410.",
    ],
  },
];

const pwCite = citationFactory(pwPages);

export const publicWorksAnalysis: Analysis = {
  id: PW_ID,
  title: "Bridge Deck Rehabilitation — US-31 Corridor",
  solicitationNumber: "INDOT-R-42817",
  agency: "Indiana Department of Transportation",
  docType: "IFB",
  mode: "standard",
  stage: "decided",
  goNoGo: "no-bid",
  decisionNote:
    "No-bid. Prequalification in Work Type B-1 is not held and cannot be obtained before bid opening. Referred to the teaming pipeline.",
  createdAt: offsetDays(-21, 9, 0),
  updatedAt: offsetDays(-16, 13, 45),
  owner: "Daniel Whitfield",
  collaborators: ["Marcus Bell"],
  naics: "237310 — Highway, Street, and Bridge Construction",
  setAside: "Open · DBE goal 9.0%",
  placeOfPerformance: "Marion & Hamilton Counties, IN",
  estimatedValue: 6_250_000,
  pageCount: 148,
  fileName: "INDOT-R-42817_IFB.pdf",
  fileSize: 11_800_000,
  source: "upload",
  tags: ["Public works", "Buy America", "DBE", "Sealed bid"],

  summary:
    "A sealed-bid deck rehabilitation with a 110-day clock and $8,400 per day in liquidated damages. Lowest responsive bidder wins, so there is no narrative to compete on. Department prequalification in Work Type B-1 is required before bid opening and we do not hold it.",

  identity: [
    { id: "f_pw_1", label: "Instrument", value: "Invitation for Bids — lowest responsive, responsible bidder", confidence: 0.98, stakes: "informational", citation: pwCite("c_pw_1", 1, "§ IFB", 3), verified: true },
    { id: "f_pw_2", label: "Bid security", value: "Bid bond at 5% of total bid", confidence: 0.96, stakes: "disqualifying", citation: pwCite("c_pw_2", 1, "§ IFB", 4), verified: true },
  ],
  scope: [
    { id: "f_pw_10", label: "Duration", value: "110 calendar days for all deck work", confidence: 0.95, stakes: "scored", citation: pwCite("c_pw_10", 6, "§ 3.1", 0), verified: true },
    { id: "f_pw_11", label: "Work window", value: "No lane closures 6:00–9:00 a.m. or 3:30–6:30 p.m.", detail: "Six and a half productive hours per weekday against a 110-day clock.", confidence: 0.93, stakes: "scored", citation: pwCite("c_pw_11", 6, "§ 3.2", 1), flagged: true },
  ],
  legal: [
    { id: "f_pw_20", label: "Buy America", value: "All structural steel under 23 C.F.R. 635.410", confidence: 0.95, stakes: "disqualifying", citation: pwCite("c_pw_20", 6, "§ 3.6", 5), verified: true },
    { id: "f_pw_21", label: "DBE goal", value: "9.0% contract goal", confidence: 0.94, stakes: "scored", citation: pwCite("c_pw_21", 6, "§ 3.5", 4) },
  ],
  eligibility: [
    { id: "f_pw_30", label: "Prequalification", value: "Work Type B-1 required before bid opening — not held", confidence: 0.97, stakes: "disqualifying", citation: pwCite("c_pw_30", 1, "§ IFB", 5), verified: true, flagged: true },
    { id: "f_pw_31", label: "Self-performance", value: "Not less than 30% of contract value", confidence: 0.93, stakes: "disqualifying", citation: pwCite("c_pw_31", 6, "§ 3.4", 3) },
  ],
  pricing: [
    { id: "f_pw_40", label: "Liquidated damages", value: "$8,400 per calendar day of overrun", confidence: 0.96, stakes: "disqualifying", citation: pwCite("c_pw_40", 6, "§ 3.3", 2), verified: true },
  ],
  postAward: [],
  gates: [
    { id: "g_pw_1", question: "Do we clear every hard eligibility gate?", answer: "No. Work Type B-1 prequalification is required before bid opening and is not held.", met: false, weight: "hard", citation: pwCite("c_pw_g1", 1, "§ IFB", 5) },
    { id: "g_pw_2", question: "Is the timeline realistic?", answer: "No. Peak-hour closure bans leave roughly six and a half productive hours a day against a 110-day clock.", met: false, weight: "hard", citation: pwCite("c_pw_g2", 6, "§ 3.2", 1) },
    { id: "g_pw_3", question: "Does the scope sit inside our practice?", answer: "Partially. Deck rehabilitation is adjacent to our structures work but not core.", met: null, weight: "soft", citation: pwCite("c_pw_g3", 6, "§ 3.1", 0) },
    { id: "g_pw_4", question: "Is the economics defensible?", answer: "No. Lowest-bid award with $8,400 daily damages against a constrained work window compresses margin to nothing.", met: false, weight: "hard", citation: pwCite("c_pw_g4", 6, "§ 3.3", 2) },
  ],
  evaluation: [{ id: "e_pw_1", name: "Total bid price", weight: 100, method: "Lowest responsive, responsible bid", citation: pwCite("c_pw_e1", 1, "§ IFB", 3) }],
  risks: [
    { id: "r_pw_1", title: "Prequalification cannot be obtained in time", narrative: "Departmental prequalification in Work Type B-1 must be in place before bid opening. The review cycle alone exceeds the time remaining.", severity: "critical", likelihood: "likely", mitigation: "Pursue prequalification for the next cycle and track the corridor's remaining segments.", citation: pwCite("c_pw_r1", 1, "§ IFB", 5) },
    { id: "r_pw_2", title: "Daily damages against a compressed work window", narrative: "Peak-hour lane closure prohibitions remove roughly five hours of every weekday while $8,400 per day accrues on any overrun.", severity: "critical", likelihood: "likely", mitigation: "Night work premium would need to be priced in, which is incompatible with a low-bid strategy.", citation: pwCite("c_pw_r2", 6, "§ 3.3", 2) },
  ],
  silent: [
    { id: "s_pw_1", topic: "Existing deck condition survey", expectation: "A rehabilitation IFB normally attaches a condition inspection report.", consequence: "Quantities carry unpriceable risk." },
    { id: "s_pw_2", topic: "Utility relocation responsibility", expectation: "Neither the Department nor the Contractor is assigned relocation duties.", consequence: "A schedule dependency with no owner." },
  ],
  dates: [
    { id: "d_pw_1", label: "Bid opening", at: offsetDays(-4, 15, 0), timezone: "America/Indiana/Indianapolis", kind: "proposal-due", citation: pwCite("c_pw_d1", 1, "§ IFB", 5) },
  ],
  clins: [
    { id: "cl_pw_1", number: "0001", description: "Deck removal and replacement", quantity: "18,400 SY", ceiling: 4_100_000 },
    { id: "cl_pw_2", number: "0002", description: "Maintenance of traffic", quantity: "1 lot", ceiling: 890_000 },
  ],
  amendments: [],
  pages: pwPages,
  versions: [
    { id: "v_pw_1", label: "Initial analysis", at: offsetDays(-21, 9, 30), author: "Margin", note: "Standard pass. Prequalification gate flagged immediately." },
    { id: "v_pw_2", label: "Decision recorded — No-bid", at: offsetDays(-16, 13, 45), author: "Daniel Whitfield", note: "No-bid confirmed at the gate review." },
  ],
};

export const publicWorksMatrix: MatrixRow[] = [
  { id: "m_pw_1", analysisId: PW_ID, reference: "3.1", requirement: "Complete all deck work within 110 calendar days.", type: "shall", stakes: "disqualifying", owner: "Daniel Whitfield", responseLocation: "Bid form", status: "complete", citation: pwCite("cm_pw_1", 6, "§ 3.1", 0) },
  { id: "m_pw_2", analysisId: PW_ID, reference: "3.4", requirement: "Self-perform not less than thirty percent of contract value.", type: "shall", stakes: "disqualifying", owner: "Marcus Bell", responseLocation: "Bid form", status: "complete", citation: pwCite("cm_pw_2", 6, "§ 3.4", 3) },
  { id: "m_pw_3", analysisId: PW_ID, reference: "3.5", requirement: "Meet a Disadvantaged Business Enterprise goal of 9.0%.", type: "shall", stakes: "disqualifying", owner: "Marcus Bell", responseLocation: "DBE forms", status: "assigned", citation: pwCite("cm_pw_3", 6, "§ 3.5", 4) },
  { id: "m_pw_4", analysisId: PW_ID, reference: "3.6", requirement: "Comply with Buy America for all structural steel.", type: "shall", stakes: "disqualifying", owner: "Daniel Whitfield", responseLocation: "Certifications", status: "complete", citation: pwCite("cm_pw_4", 6, "§ 3.6", 5) },
];

export const publicWorksQuestions: QAQuestion[] = [
  { id: "q_pw_1", analysisId: PW_ID, text: "Will the Department release the most recent deck condition inspection report for the structures in this contract?", rationale: "Quantities cannot be verified without it.", sourceKind: "silent", goNoGoImpact: true, order: 0, sent: false },
  { id: "q_pw_2", analysisId: PW_ID, text: "Which party is responsible for utility relocation within the work limits?", rationale: "The special provisions assign it to neither party.", sourceKind: "silent", goNoGoImpact: false, order: 1, sent: false },
];

/* ------------------------------------------------------------------ */
/* Rural broadband sources sought — USDA RUS                            */
/* ------------------------------------------------------------------ */

const SS_ID = "an_usda_broadband";

const ssPages: DocumentPage[] = [
  {
    page: 1,
    heading: "Sources Sought Notice",
    lines: [
      "UNITED STATES DEPARTMENT OF AGRICULTURE — RURAL UTILITIES SERVICE",
      "SOURCES SOUGHT NOTICE RUS-26-SS-0031",
      "Middle-Mile Broadband Deployment — Appalachian Counties",
      "This is a sources sought notice only. It is not a request for proposals.",
      "No contract will be awarded from this notice and no reimbursement will be made for responses.",
      "Responses shall not exceed eight (8) pages and shall address capability only.",
      "Respondents shall identify their business size under NAICS 237130.",
      "The Government is assessing whether a small business set-aside is appropriate.",
    ],
  },
  {
    page: 3,
    heading: "Capability Statement Content",
    lines: [
      "2.1 Respondents should describe experience deploying middle-mile fiber in mountainous terrain.",
      "2.2 Respondents should identify bonding capacity and available construction crews.",
      "2.3 Respondents should describe experience with National Environmental Policy Act reviews.",
      "2.4 Respondents may identify anticipated teaming arrangements.",
      "2.5 Responses received after the closing date may not be considered.",
    ],
  },
];

const ssCite = citationFactory(ssPages);

export const sourcesSoughtAnalysis: Analysis = {
  id: SS_ID,
  title: "Middle-Mile Broadband Deployment — Appalachian Counties",
  solicitationNumber: "RUS-26-SS-0031",
  agency: "USDA Rural Utilities Service",
  docType: "Sources Sought",
  mode: "quick-triage",
  stage: "triage",
  goNoGo: "watch",
  decisionNote: "Watch. Respond to shape the set-aside decision; no bid exists yet.",
  createdAt: offsetDays(-3, 11, 30),
  updatedAt: offsetDays(-3, 11, 44),
  owner: "Lena Ford",
  collaborators: [],
  naics: "237130 — Power and Communication Line Construction",
  setAside: "Undetermined — market research in progress",
  placeOfPerformance: "Appalachian counties, KY / WV / VA",
  estimatedValue: 0,
  pageCount: 12,
  fileName: "RUS-26-SS-0031.pdf",
  fileSize: 640_000,
  source: "onedrive",
  tags: ["Market research", "Broadband", "NEPA"],

  summary:
    "A capability request, not a solicitation. The value of responding is influence: the Government is deciding whether to set the eventual procurement aside for small business, and a strong capability statement shapes that determination.",

  identity: [
    { id: "f_ss_1", label: "Instrument", value: "Sources sought notice — no award will be made", confidence: 0.99, stakes: "informational", citation: ssCite("c_ss_1", 1, "§ SS", 3), verified: true },
    { id: "f_ss_2", label: "Purpose", value: "Determining whether a small business set-aside is appropriate", confidence: 0.96, stakes: "scored", citation: ssCite("c_ss_2", 1, "§ SS", 7), verified: true },
    { id: "f_ss_3", label: "Response limit", value: "Eight pages, capability only", confidence: 0.97, stakes: "disqualifying", citation: ssCite("c_ss_3", 1, "§ SS", 5), verified: true },
  ],
  scope: [
    { id: "f_ss_10", label: "Topic", value: "Middle-mile fiber deployment in mountainous terrain", confidence: 0.94, stakes: "scored", citation: ssCite("c_ss_10", 3, "§ 2.1", 0) },
    { id: "f_ss_11", label: "Environmental review", value: "NEPA experience is specifically requested", confidence: 0.9, stakes: "scored", citation: ssCite("c_ss_11", 3, "§ 2.3", 2) },
  ],
  legal: [],
  eligibility: [
    { id: "f_ss_30", label: "Size representation", value: "Business size under NAICS 237130 must be stated", confidence: 0.95, stakes: "disqualifying", citation: ssCite("c_ss_30", 1, "§ SS", 6), verified: true },
  ],
  pricing: [],
  postAward: [],
  gates: [
    { id: "g_ss_1", question: "Do we clear every hard eligibility gate?", answer: "Not applicable — a capability response carries no eligibility gate beyond the size representation.", met: true, weight: "hard", citation: ssCite("c_ss_g1", 1, "§ SS", 6) },
    { id: "g_ss_2", question: "Is the timeline realistic?", answer: "Yes. Eight pages of capability narrative is a two-day effort.", met: true, weight: "soft", citation: ssCite("c_ss_g2", 1, "§ SS", 5) },
    { id: "g_ss_3", question: "Does the scope sit inside our practice?", answer: "Adjacent. Middle-mile construction is a partner capability, not an in-house one.", met: null, weight: "soft", citation: ssCite("c_ss_g3", 3, "§ 2.1", 0) },
    { id: "g_ss_4", question: "Is the economics defensible?", answer: "No price exists yet. Responding is a positioning cost, not a bid.", met: null, weight: "soft", citation: ssCite("c_ss_g4", 1, "§ SS", 4) },
  ],
  evaluation: [],
  risks: [
    { id: "r_ss_1", title: "Responding may invite a set-aside we cannot meet alone", narrative: "A strong small business response increases the chance of a set-aside for which we would need a construction partner already under agreement.", severity: "moderate", likelihood: "possible", mitigation: "Secure the teaming letter before responding.", citation: ssCite("c_ss_r1", 1, "§ SS", 7) },
  ],
  silent: [
    { id: "s_ss_1", topic: "Route mileage", expectation: "No mileage, county list, or route map is provided.", consequence: "Capability claims cannot be scaled to the actual programme." },
    { id: "s_ss_2", topic: "Anticipated award timing", expectation: "No target date for the follow-on solicitation.", consequence: "Cannot sequence partner agreements." },
  ],
  dates: [
    { id: "d_ss_1", label: "Capability statement due", at: offsetDays(6, 22, 0), timezone: "America/New_York", kind: "proposal-due", citation: ssCite("c_ss_d1", 3, "§ 2.5", 4) },
  ],
  clins: [],
  amendments: [],
  pages: ssPages,
  versions: [{ id: "v_ss_1", label: "Quick triage", at: offsetDays(-3, 11, 44), author: "Margin", note: "Triage pass. Marked Watch." }],
};

export const sourcesSoughtMatrix: MatrixRow[] = [
  { id: "m_ss_1", analysisId: SS_ID, reference: "SS", requirement: "Limit the response to eight pages addressing capability only.", type: "shall", stakes: "disqualifying", owner: "Lena Ford", responseLocation: "Capability statement", status: "drafted", citation: ssCite("cm_ss_1", 1, "§ SS", 5) },
  { id: "m_ss_2", analysisId: SS_ID, reference: "SS", requirement: "Identify business size under NAICS 237130.", type: "shall", stakes: "disqualifying", owner: "Lena Ford", responseLocation: "Capability statement § 1", status: "complete", citation: ssCite("cm_ss_2", 1, "§ SS", 6) },
  { id: "m_ss_3", analysisId: SS_ID, reference: "2.1", requirement: "Describe experience deploying middle-mile fiber in mountainous terrain.", type: "should", stakes: "scored", owner: "Lena Ford", responseLocation: "Capability statement § 2", status: "drafted", citation: ssCite("cm_ss_3", 3, "§ 2.1", 0) },
  { id: "m_ss_4", analysisId: SS_ID, reference: "2.3", requirement: "Describe experience with National Environmental Policy Act reviews.", type: "should", stakes: "scored", owner: null, responseLocation: "", status: "unassigned", citation: ssCite("cm_ss_4", 3, "§ 2.3", 2) },
];

export const sourcesSoughtQuestions: QAQuestion[] = [
  { id: "q_ss_1", analysisId: SS_ID, text: "Can the Government indicate the anticipated route mileage and the counties in scope?", rationale: "Capability claims should be scaled to the programme.", sourceKind: "silent", goNoGoImpact: false, order: 0, sent: false },
];

/* ------------------------------------------------------------------ */
/* Sensor fusion BAA — ONR                                              */
/* ------------------------------------------------------------------ */

const BAA_ID = "an_onr_sensor";

const baaPages: DocumentPage[] = [
  {
    page: 1,
    heading: "Broad Agency Announcement",
    lines: [
      "OFFICE OF NAVAL RESEARCH",
      "BROAD AGENCY ANNOUNCEMENT N00014-26-S-B004",
      "Distributed Sensor Fusion for Contested Maritime Environments",
      "White papers are strongly encouraged prior to submission of a full proposal.",
      "This BAA remains open for twelve months from the date of publication.",
      "Awards may take the form of contracts, grants, or other transaction agreements.",
      "Cost sharing is not required but will be considered favorably where offered.",
    ],
  },
  {
    page: 7,
    heading: "Technical Areas and Submission",
    lines: [
      "3.1 Technical Area 1 addresses multi-modal fusion under intermittent communications.",
      "3.2 Technical Area 2 addresses on-platform inference within a 40-watt power envelope.",
      "3.3 White papers shall not exceed five (5) pages excluding the cover page.",
      "3.4 Full proposals are by invitation only following white paper review.",
      "3.5 Offerors shall identify any foreign national participation at the time of white paper submission.",
      "3.6 Proposals involving fundamental research shall state the applicable publication restrictions.",
      "3.7 Evaluation is by scientific merit, relevance to Navy needs, and cost realism, in that order.",
    ],
  },
];

const baaCite = citationFactory(baaPages);

export const baaAnalysis: Analysis = {
  id: BAA_ID,
  title: "Distributed Sensor Fusion for Contested Maritime Environments",
  solicitationNumber: "N00014-26-S-B004",
  agency: "Office of Naval Research",
  docType: "BAA",
  mode: "deep-research",
  stage: "analyzing",
  goNoGo: "undecided",
  createdAt: offsetDays(-9, 13, 0),
  updatedAt: offsetDays(-5, 17, 15),
  owner: "Amara Osei",
  collaborators: ["Lena Ford"],
  naics: "541715 — Research and Development",
  setAside: "Open",
  placeOfPerformance: "Contractor facility",
  estimatedValue: 3_400_000,
  pageCount: 58,
  fileName: "N00014-26-S-B004_BAA.pdf",
  fileSize: 4_400_000,
  source: "upload",
  tags: ["R&D", "Navy", "Export control", "White paper"],

  summary:
    "A twelve-month open BAA with a white paper gate before any full proposal. Scientific merit outranks cost, and the 40-watt inference envelope in Technical Area 2 is the only genuinely hard constraint. Foreign national participation must be declared at white paper stage.",

  identity: [
    { id: "f_b_1", label: "Instrument", value: "Broad Agency Announcement, open twelve months", confidence: 0.97, stakes: "informational", citation: baaCite("c_b_1", 1, "§ BAA", 4), verified: true },
    { id: "f_b_2", label: "Award vehicles", value: "Contracts, grants, or other transaction agreements", confidence: 0.94, stakes: "informational", citation: baaCite("c_b_2", 1, "§ BAA", 5) },
    { id: "f_b_3", label: "Entry point", value: "White paper first; full proposals by invitation only", confidence: 0.96, stakes: "disqualifying", citation: baaCite("c_b_3", 7, "§ 3.4", 3), verified: true },
  ],
  scope: [
    { id: "f_b_10", label: "Technical Area 1", value: "Multi-modal fusion under intermittent communications", confidence: 0.93, stakes: "scored", citation: baaCite("c_b_10", 7, "§ 3.1", 0) },
    { id: "f_b_11", label: "Technical Area 2", value: "On-platform inference inside a 40-watt power envelope", detail: "Our current edge stack draws 63 watts at the same throughput. This is the research question, not a delivery risk.", confidence: 0.82, stakes: "scored", citation: baaCite("c_b_11", 7, "§ 3.2", 1), flagged: true },
  ],
  legal: [
    { id: "f_b_20", label: "Foreign national disclosure", value: "Required at white paper submission, not at award", confidence: 0.91, stakes: "disqualifying", citation: baaCite("c_b_20", 7, "§ 3.5", 4), verified: true },
    { id: "f_b_21", label: "Publication restrictions", value: "Fundamental research proposals must state applicable restrictions", confidence: 0.85, stakes: "scored", citation: baaCite("c_b_21", 7, "§ 3.6", 5) },
  ],
  eligibility: [],
  pricing: [
    { id: "f_b_40", label: "Cost sharing", value: "Not required, considered favorably where offered", confidence: 0.9, stakes: "scored", citation: baaCite("c_b_40", 1, "§ BAA", 6) },
  ],
  postAward: [],
  gates: [
    { id: "g_b_1", question: "Do we clear every hard eligibility gate?", answer: "Yes. A BAA imposes no eligibility gate beyond the foreign national declaration.", met: true, weight: "hard", citation: baaCite("c_b_g1", 7, "§ 3.5", 4) },
    { id: "g_b_2", question: "Is the timeline realistic?", answer: "Yes. The BAA is open for twelve months and white papers are five pages.", met: true, weight: "soft", citation: baaCite("c_b_g2", 1, "§ BAA", 4) },
    { id: "g_b_3", question: "Does the scope sit inside our practice?", answer: "Yes for Area 1. Area 2's 40-watt envelope is a genuine research stretch.", met: true, weight: "soft", citation: baaCite("c_b_g3", 7, "§ 3.2", 1) },
    { id: "g_b_4", question: "Is the economics defensible?", answer: "Provisionally. Merit outranks cost, which suits a properly funded research bid.", met: null, weight: "hard", citation: baaCite("c_b_g4", 7, "§ 3.7", 6) },
  ],
  evaluation: [
    { id: "e_b_1", name: "Scientific & technical merit", weight: 50, method: "Peer review", citation: baaCite("c_b_e1", 7, "§ 3.7", 6) },
    { id: "e_b_2", name: "Relevance to Navy needs", weight: 30, method: "Programme officer assessment", citation: baaCite("c_b_e2", 7, "§ 3.7", 6) },
    { id: "e_b_3", name: "Cost realism", weight: 20, method: "Realism analysis", citation: baaCite("c_b_e3", 7, "§ 3.7", 6) },
  ],
  risks: [
    { id: "r_b_1", title: "40-watt envelope is 37% below our current draw", narrative: "Technical Area 2 constrains on-platform inference to forty watts. Our edge stack draws sixty-three watts at comparable throughput, so the white paper must propose a credible path rather than a demonstrated result.", severity: "elevated", likelihood: "likely", mitigation: "Lead with the quantisation and scheduling research line; do not claim a current capability.", citation: baaCite("c_b_r1", 7, "§ 3.2", 1) },
    { id: "r_b_2", title: "Foreign national declaration at white paper stage", narrative: "Two of the four proposed researchers are foreign nationals, which must be declared before the merit review rather than after.", severity: "moderate", likelihood: "likely", mitigation: "Confirm the export control posture with Legal before submission.", citation: baaCite("c_b_r2", 7, "§ 3.5", 4) },
  ],
  silent: [
    { id: "s_b_1", topic: "Expected award size", expectation: "A BAA usually indicates a typical award range per technical area.", consequence: "Cannot scope the research plan to the money." },
    { id: "s_b_2", topic: "Number of anticipated awards", expectation: "No indication of how many awards per area.", consequence: "No read on selection odds." },
    { id: "s_b_3", topic: "White paper review turnaround", expectation: "No stated review period before invitation.", consequence: "Cannot plan the follow-on proposal team." },
  ],
  dates: [
    { id: "d_b_1", label: "White paper — recommended submission", at: offsetDays(23, 21, 0), timezone: "America/New_York", kind: "proposal-due", citation: baaCite("c_b_d1", 1, "§ BAA", 3) },
    { id: "d_b_2", label: "BAA closes", at: offsetDays(196, 21, 0), timezone: "America/New_York", kind: "proposal-due", citation: baaCite("c_b_d2", 1, "§ BAA", 4) },
  ],
  clins: [],
  amendments: [],
  pages: baaPages,
  versions: [
    { id: "v_b_1", label: "Initial analysis", at: offsetDays(-9, 13, 30), author: "Margin", note: "Deep research pass across both technical areas." },
    { id: "v_b_2", label: "Reviewer pass — Lena Ford", at: offsetDays(-5, 17, 15), author: "Lena Ford", note: "Confirmed the power envelope gap against the lab bench numbers." },
  ],
};

export const baaMatrix: MatrixRow[] = [
  { id: "m_b_1", analysisId: BAA_ID, reference: "3.3", requirement: "Limit white papers to five pages excluding the cover page.", type: "shall", stakes: "disqualifying", owner: "Amara Osei", responseLocation: "White paper", status: "drafted", citation: baaCite("cm_b_1", 7, "§ 3.3", 2) },
  { id: "m_b_2", analysisId: BAA_ID, reference: "3.5", requirement: "Identify any foreign national participation at white paper submission.", type: "shall", stakes: "disqualifying", owner: "Lena Ford", responseLocation: "White paper cover", status: "in-review", citation: baaCite("cm_b_2", 7, "§ 3.5", 4) },
  { id: "m_b_3", analysisId: BAA_ID, reference: "3.6", requirement: "State applicable publication restrictions for fundamental research.", type: "shall", stakes: "scored", owner: null, responseLocation: "", status: "unassigned", citation: baaCite("cm_b_3", 7, "§ 3.6", 5) },
];

export const baaQuestions: QAQuestion[] = [
  { id: "q_b_1", analysisId: BAA_ID, text: "Can the programme office indicate a typical award range and the anticipated number of awards per technical area?", rationale: "The research plan should be scoped to the available funding.", sourceKind: "silent", goNoGoImpact: true, order: 0, sent: false },
  { id: "q_b_2", analysisId: BAA_ID, text: "What is the expected turnaround between white paper submission and an invitation decision?", rationale: "Determines when the full proposal team must be reserved.", sourceKind: "silent", goNoGoImpact: false, order: 1, sent: false, citation: baaCite("cq_b_2", 7, "§ 3.4", 3) },
];
