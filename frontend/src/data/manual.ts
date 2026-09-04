import type { LucideIcon } from "lucide-react";
import {
  BookOpen,
  ClipboardCheck,
  Compass,
  FileSearch,
  Gavel,
  GitCompare,
  Layers,
  Lock,
  Route,
  Ruler,
  ScanLine,
  ShieldCheck,
  Users,
} from "lucide-react";

/**
 * The manual, as data.
 *
 * Written here rather than in a wiki for one reason: the vocabulary Margin
 * uses is load-bearing. "Unverifiable" is not a synonym for "failed",
 * "scanned" is not a synonym for "analysed", and a person who reads those as
 * synonyms will trust a number that does not mean what they think. A manual
 * that lives outside the product drifts from it within a release; one that
 * ships beside the code is at least edited by the people changing the words.
 *
 * Two rules for anything added here.
 *
 * **Say what it does not do.** The limits are the useful half. Every section
 * that can carries a `limits` list, because the failure people actually hit is
 * expecting a feature to have decided something it deliberately did not.
 *
 * **Never describe a behaviour that does not exist.** A manual is a promise. If
 * a paragraph here and the code disagree, the paragraph is the bug.
 */

export interface ManualTerm {
  term: string;
  meaning: string;
  /** The mistake this word invites, when there is one worth naming. */
  notThe?: string;
}

export interface ManualSection {
  id: string;
  title: string;
  /** One sentence, shown under the heading and searched. */
  summary: string;
  icon: LucideIcon;
  /** Prose. Each string is a paragraph. */
  body: string[];
  /** "How you actually use it", in order. */
  steps?: { label: string; detail: string }[];
  /** Vocabulary this section defines, rendered as a table. */
  terms?: ManualTerm[];
  /** What this deliberately does not do. */
  limits?: string[];
  /** Where in the product it lives. */
  where?: string;
  href?: string;
}

export interface ManualChapter {
  id: string;
  title: string;
  blurb: string;
  sections: ManualSection[];
}

export const MANUAL: ManualChapter[] = [
  {
    id: "start",
    title: "Start here",
    blurb: "What Margin is for, and the one idea everything else rests on.",
    sections: [
      {
        id: "what-margin-is",
        title: "What Margin is",
        summary:
          "It reads a solicitation package the way a compliance lead would, and shows its work.",
        icon: Compass,
        body: [
          "Margin reads a whole solicitation package — the base document, every attachment, and every amendment — and turns it into a ledger of requirements, a set of gates, a list of what the document did not say, and a record of who decided what. It is not a chatbot over a PDF and it does not write your proposal.",
          "The single idea underneath all of it: nothing is asserted without a citation. Every requirement, gate, risk and date carries the document, the page and the quoted line it came from. If Margin cannot point at the text, it says so rather than filling the gap.",
          "The second idea, which is the one that keeps the first honest: Margin distinguishes what it counted from what it judged. Counting is deterministic and repeatable. Judging is a model reading prose, and it is always presented as something a person still has to confirm.",
        ],
        limits: [
          "It does not write proposal content, and there is no win-theme generator. Persuasion is yours.",
          "It never clears a mandatory requirement on its own. A satisfied verdict on a disqualifying requirement is a recommendation waiting for a person.",
          "It reads text. Anything that is a property of the rendered file — actual fonts, actual margins, actual page counts in the PDF you will upload — is flagged for a person, never guessed.",
        ],
      },
      {
        id: "first-read",
        title: "Your first read, in five minutes",
        summary: "Upload a package, pick a mode, and go straight to what needs you.",
        icon: FileSearch,
        where: "Analyses → New analysis",
        href: "/app/analyses/new",
        body: [
          "A pursuit in Margin is one analysis. Everything — requirements, questions, reviews, the decision — hangs off it.",
          "Upload the base document first, then the attachments and any amendments. Amendments are not a separate feature to remember: attach them and Margin folds them into the package, pairs each change against the clause it changes, and proposes what now governs.",
        ],
        steps: [
          {
            label: "Create the analysis and attach the package",
            detail:
              "Base document, attachments, amendments. A document Margin cannot extract text from still counts toward coverage — it is reported as unreadable rather than quietly dropped.",
          },
          {
            label: "Pick a mode",
            detail:
              "Quick Triage to decide whether this is worth an hour. Standard for the full read. Matrix Only when you already know you are bidding and just need the requirements.",
          },
          {
            label: "Open Coverage before anything else",
            detail:
              "It tells you how much of the package was actually read. Every other number on the screen is a fraction of this one.",
          },
          {
            label: "Work Needs You",
            detail:
              "The queue of things only a person can settle, ordered by what it costs to get wrong rather than by what Margin is least sure about.",
          },
          {
            label: "Bind your draft response when you have one",
            detail:
              "From then on Margin checks the draft against the ledger and shows you the gap, requirement by requirement.",
          },
        ],
      },
    ],
  },
  {
    id: "reading",
    title: "How Margin reads",
    blurb: "Two passes, one coverage ledger, and a citation on everything.",
    sections: [
      {
        id: "two-passes",
        title: "The two passes",
        summary:
          "A deterministic sweep sets the floor; the specialists raise the ceiling. Agreement between them is the strongest signal there is.",
        icon: Layers,
        body: [
          "Every page of the package goes through a deterministic pattern sweep — obligations, limits, deadlines, forms, formats, prohibitions. It is repeatable, it needs no model, and it is the floor: whatever else happens, these are found.",
          "Then specialists read the retrieved passages for the things patterns cannot see: what is actually being bought, how the award will be scored, what could go wrong, what the document conspicuously does not say.",
          "The matrix labels which pass found each requirement. Corroborated means both found it — the strongest signal extraction produces. Model only means no pattern matched, and it is worth reading against the source before you rely on it.",
        ],
        terms: [
          {
            term: "Sweep",
            meaning:
              "The deterministic pass. Same input, same output, every time. Regression-tested on every change against a labelled corpus.",
          },
          {
            term: "Specialist",
            meaning:
              "A model reading retrieved passages for one thing — scope, evaluation, eligibility, risk, silence.",
          },
          {
            term: "Corroborated",
            meaning: "Both passes found it independently.",
            notThe: "Not a confidence score. It is agreement between two different methods.",
          },
        ],
      },
      {
        id: "coverage",
        title: "The coverage ledger",
        summary: "Two numbers, not one: how much was scanned, and how much was read in depth.",
        icon: ScanLine,
        where: "Workspace → Coverage",
        body: [
          "Reporting a single completeness number would overstate the reading. So coverage reports four states per page, and the honest headline is a pair: pages scanned, and of those, pages analysed in depth.",
          "The state that matters most is the unhappy one. A scanned PDF with no text layer produces nothing, and a product that hid that would let you believe a whole attachment had been read.",
        ],
        terms: [
          {
            term: "Analysed",
            meaning: "Read in depth by the specialists, not only pattern-swept.",
          },
          {
            term: "Scanned",
            meaning: "Extracted and swept for patterns, but not read in depth.",
            notThe: "Not the same as analysed. A high scanned figure with low analysed is a thin read.",
          },
          {
            term: "No text",
            meaning:
              "Extraction produced nothing — an image-only PDF, an empty upload. Nothing was read from these pages by anything.",
          },
          {
            term: "Unreached",
            meaning: "In the package, not processed. This should be zero; if it is not, say so before you rely on the read.",
          },
        ],
        limits: [
          "Coverage measures what was read, not whether the reading was right. Recall is measured separately against a labelled evaluation corpus.",
        ],
      },
      {
        id: "citations",
        title: "Citations and the Margin rail",
        summary: "Hover any finding and the clause opens beside it, highlighted.",
        icon: BookOpen,
        body: [
          "Every finding carries a document, a page, a section path and the quoted line. Hover the source block and the rail opens on the right with the clause in place.",
          "A quote that cannot be found in the package is treated as an extraction failure, not as evidence. When a response check cites a passage the checker cannot locate, the verdict is downgraded rather than accepted.",
        ],
      },
    ],
  },
  {
    id: "modes",
    title: "Modes",
    blurb: "What each read costs you, and what it deliberately leaves out.",
    sections: [
      {
        id: "choosing-a-mode",
        title: "Choosing a mode",
        summary: "Modes differ in which specialists run and how many passes they make.",
        icon: Route,
        body: [
          "A mode is not a quality setting. It is a choice about which questions you are asking now, and every mode uses the same deterministic sweep underneath — so the recall floor does not move between them.",
          "Quick Triage answers one question: is this worth a human hour? Standard is the full read. Deep Research adds external sources — statutes, prior awards, incumbent history — and attributes every one of them. Matrix Only, Q&A Only, Amendment Refresh and Re-compete Compare are each shaped around a task you already know you have.",
        ],
        limits: [
          "A faster mode does not read less carefully; it reads fewer things. Quick Triage skips the compliance matrix entirely rather than producing a rushed one.",
        ],
      },
    ],
  },
  {
    id: "matrix",
    title: "Requirements and the matrix",
    blurb: "The ledger everything else is measured against.",
    sections: [
      {
        id: "ledger",
        title: "The requirement ledger",
        summary:
          "Requirements have stable identities, so an amendment supersedes a clause instead of duplicating it.",
        icon: ClipboardCheck,
        where: "Workspace → Compliance Matrix",
        href: "/app/matrix",
        body: [
          "Each requirement gets an identity derived from its normalised text, so the same clause found twice is one row, and a re-run does not produce a second copy of work somebody has already assigned.",
          "Nothing is ever deleted by a re-read. A requirement that no longer appears is marked superseded or removed, with the history of how it got there, because a clause that quietly vanished between two runs is the thing nobody notices until debrief.",
        ],
        terms: [
          {
            term: "Type",
            meaning: "shall, should, may — the strength of the obligation as the document words it.",
          },
          {
            term: "Stakes",
            meaning:
              "Disqualifying, scored, or informational. Disqualifying means getting it wrong loses the bid regardless of how good the prose is.",
          },
          {
            term: "State",
            meaning: "Open, superseded, or removed. Superseded rows stay visible with what replaced them.",
          },
          {
            term: "Status",
            meaning: "Unassigned → assigned → drafted → in review → complete. Your team's progress, not Margin's.",
          },
        ],
        limits: [
          "Setting a disqualifying row to complete needs the authority to clear a mandatory requirement. That is a reviewer or admin decision by design.",
        ],
      },
      {
        id: "mechanical",
        title: "Counted, not judged",
        summary:
          "Page limits, fonts, margins, forms, file names and volume structure are decided in code — never by a model.",
        icon: Ruler,
        body: [
          "Roughly a fifth of a solicitation's requirements are arithmetic: a page limit, a word count, a font floor, a required form, a naming convention, a volume structure, a closing time. A model that reads those correctly nine times in ten is worse than useless, because the tenth loses the bid and nobody can tell which one it was.",
          "So Margin checks them by counting. Pages are counted, exclusions applied, forms located, file names matched against the stated template, volumes located by their titles. Each rule reports a verdict with the number it counted, and the rule that produced it.",
          "When a rule cannot be checked from extracted text — because it is a property of the rendered file, like actual point size or actual margins — it reports unverifiable and lands on the white-glove checklist. That is the honest answer, and it is why the production round exists.",
        ],
        terms: [
          {
            term: "Mechanical",
            meaning: "Decided by counting. Repeatable, and never handed to a model.",
          },
          {
            term: "Substantive",
            meaning:
              "Needs somebody to read it. A model can draft the assessment; it cannot settle it.",
          },
          {
            term: "Unverifiable",
            meaning: "Could not be determined from what was available.",
            notThe:
              "Not a failure. A failure means the rule was checked and not met; unverifiable means nobody has checked yet.",
          },
        ],
        limits: [
          "Mechanical rules read extracted text and file names. They cannot see the rendered PDF, so typography, margins, signatures, binding and copies are always routed to a person.",
        ],
      },
    ],
  },
  {
    id: "response",
    title: "Checking your response",
    blurb: "The gap between what the solicitation demands and what your draft says.",
    sections: [
      {
        id: "response-gap",
        title: "Response Gap",
        summary:
          "Every requirement traced to the passage in your draft that answers it — or the absence of one.",
        icon: GitCompare,
        where: "Workspace → Response Gap",
        body: [
          "Bind a draft and Margin reads it as its own corpus, then compares it to the ledger one requirement at a time. Mechanical requirements are counted. Substantive ones are read by a model that is instructed to say it does not know rather than to guess.",
          "The asymmetry is deliberate. A wrong 'satisfied' causes a disqualification nobody sees coming; a wrong 'unverifiable' costs a person five minutes. Every ambiguous case goes to unverifiable.",
        ],
        terms: [
          { term: "Satisfied", meaning: "A passage plainly and completely answers the requirement." },
          { term: "Partial", meaning: "Something addresses it, but not all of it." },
          { term: "Missing", meaning: "Nothing in the draft answers it." },
          { term: "Failed", meaning: "The draft answers it in a way that breaks the requirement." },
          {
            term: "Unverifiable",
            meaning: "Could not be told from the passages available. Sends a person to look.",
          },
        ],
        limits: [
          "A satisfied verdict on a mandatory requirement is never treated as cleared. It is recorded as needing confirmation and stays in the queue until a person signs it.",
          "With no model available, every substantive check comes back unverifiable with the reason attached. That is worse than a real check and much better than a guess.",
        ],
      },
      {
        id: "revisions",
        title: "What survives a new draft",
        summary:
          "Verdicts on passages that did not change carry forward. Verdicts on passages that did are dropped.",
        icon: Layers,
        body: [
          "Re-checking a revision from scratch throws away every signature and asks the team to re-verify a hundred requirements because two sections changed. Carrying verdicts forward wholesale asserts that somebody checked text they never saw.",
          "So each requirement's evidence is compared between drafts. Unchanged passages keep their verdict, marked as carried. Changed ones lose it and come back to the queue. The full chain — requirement, clause, response section, claim, evidence, verification — is frozen into each check, so it still describes what was actually checked after the requirement is amended and the response revised again.",
        ],
      },
    ],
  },
  {
    id: "judgement",
    title: "Where people decide",
    blurb: "The queue, the conflicts, the questions, and the record of who said what.",
    sections: [
      {
        id: "needs-you",
        title: "Needs You",
        summary: "Ordered by what it costs to get wrong, not by what Margin is least sure about.",
        icon: Gavel,
        where: "Workspace → Needs You",
        body: [
          "The queue holds everything only a person can settle: mandatory requirements reported as satisfied, unverifiable mechanical rules, open contradictions, questions whose answers change a requirement, and checks whose evidence moved in the latest draft.",
          "Blocking items come first — the ones that lose the bid. Then important, then routine. A queue sorted by model confidence would put a trivial uncertainty above a disqualifying gate.",
          "Confirming an item records who confirmed it, what they confirmed, what they based it on, when, and what the previous verdict was. That record is what makes a debrief answerable.",
        ],
      },
      {
        id: "conflicts",
        title: "Conflicts",
        summary:
          "Two clauses in the same package that cannot both be met. Margin proposes; it never applies.",
        icon: GitCompare,
        where: "Workspace → Conflicts",
        body: [
          "Section L says forty pages and Attachment J-3 says fifty. Both are live requirements, and a response check would judge your draft against whichever one it happened to be handed. This is the one class of problem where the reading is right and the document is wrong.",
          "Margin detects conflicts on dimensions where a solicitation states a single number — page limits, word limits, font size, margins, file size, deadlines, permissions — and shows both clauses with their citations. Which one governs is your decision, recorded with your reason. Nothing is silently applied.",
        ],
        limits: [
          "Detection is deliberately narrow. It looks for competing values on the same dimension in the same scope, not for prose that feels inconsistent.",
        ],
      },
      {
        id: "questions",
        title: "Questions to the agency",
        summary:
          "The SILENT ledger becomes a ranked question set, and an answer flows back into the requirements it changes.",
        icon: BookOpen,
        where: "Workspace → Q&A Builder",
        body: [
          "What a document does not say is often more expensive than what it does. Unstated page limits, unnamed incumbents, implied ceilings — each becomes a question in one click.",
          "When the answer arrives, it does not just sit in a thread. Margin walks the graph from the answer to the requirements it changes, to the response sections bound to them, to the verifications resting on those — and reopens only what the answer actually touched.",
        ],
      },
      {
        id: "decision",
        title: "The decision record",
        summary: "A person decides. Margin records what was known when they did.",
        icon: ClipboardCheck,
        body: [
          "Six months after a loss the question is never whether the machine was right. It is what you knew when you decided, and whether you looked at it.",
          "Recording a bid or no-bid freezes the evidence as it stood — the gates that failed, what was still unverified, the contradictions left open, the coverage you had. Deliberately the uncomfortable half. The outcome is recorded later against the same record, which is what makes it worth keeping.",
        ],
      },
    ],
  },
  {
    id: "reviews",
    title: "Colour-team reviews",
    blurb: "Pink, Red, Gold, White glove — and what a sign-off is worth.",
    sections: [
      {
        id: "rounds",
        title: "Rounds and charters",
        summary: "A round is opened against a version of the draft, and ends with a named person.",
        icon: Users,
        where: "Workspace → Reviews",
        body: [
          "Pink asks whether the approach and structure are worth writing into. Red reads it as the evaluator will score it — the most valuable round and the first one dropped when a deadline tightens. Gold asks whether this is a bid you are prepared to make. White glove is the production check against the rendered files.",
          "The charter is copied into the round when it opens, so a round from last quarter still says what it was for after the defaults change. A round with reviewers who disagree about its purpose produces findings nobody can act on.",
          "White glove is where every unverifiable mechanical rule lands: fonts, margins, spacing, signatures, copies, binding, file formats. Margin generates that checklist rather than pretending it checked them.",
        ],
        terms: [
          { term: "Must fix", meaning: "The round does not close cleanly while one is open." },
          { term: "Should fix", meaning: "Real, but it will not hold the round." },
          { term: "Consider", meaning: "Raised for the author's judgement." },
          {
            term: "Override",
            meaning:
              "A round closed over its own open must-fix findings, with a written reason. Recorded as an override, never as a pass.",
          },
        ],
        limits: [
          "Nobody signs off a round they opened. It is enforced separately from roles because it depends on who opened it — and admins are not exempt, since an admin can grant themselves any role.",
          "A finding cannot be rejected without a reason. One closed silently is one the next round raises again.",
        ],
      },
      {
        id: "round-on-round",
        title: "Round on round",
        summary:
          "Whether findings were fixed or merely accepted, what came back, and whether a sign-off still covers the draft.",
        icon: GitCompare,
        body: [
          "One round is a list of findings. Three rounds are an argument about whether the proposal is getting better, and no per-round view answers it.",
          "The comparison separates must-fix findings that were fixed from ones that were accepted — those are deferrals, and the next round meets them again. It flags anything raised, marked fixed, and raised again in a later round: the fix did not hold, which is the single most useful thing a review programme produces. It lists must-fix findings a closed round left open, where nobody looks. And it marks a sign-off against an older draft as stale, which is not the same as wrong.",
        ],
      },
    ],
  },
  {
    id: "governance",
    title: "Governance and data",
    blurb: "Roles, retention, personal data, and the record you can hand to somebody.",
    sections: [
      {
        id: "roles",
        title: "Roles and permissions",
        summary:
          "Permissions are named after the decision they govern, and a refusal tells you who has it.",
        icon: ShieldCheck,
        where: "Settings → Permissions",
        href: "/app/settings?tab=permissions",
        body: [
          "Four roles. Viewers read. Writers do the work — running analyses, working the matrix, binding drafts, drafting questions. Reviewers additionally clear mandatory requirements, resolve contradictions, sign off rounds and record decisions. Admins manage the workspace, its people and its retention.",
          "Signing off a review and resolving a contradiction are different authorities even though both write a row, so they are separate permissions rather than collapsed into 'write'. When you are refused something, the message names the roles that have it and what your own role is for — a message reading 'forbidden' just teaches people to file a ticket.",
          "The whole matrix is visible in Settings, including what you cannot do. A permission model people cannot see is one they work around, usually by sharing a login.",
        ],
      },
      {
        id: "pii",
        title: "Personal data and masking",
        summary:
          "Found by pattern, never by a model. Redaction happens on the way out and never edits the original.",
        icon: Lock,
        body: [
          "A solicitation package and a draft response are full of things that should not travel with an export: the contracting officer's mobile number, a reference's home address, the resumes in an appendix, an identifier somebody pasted into a form field.",
          "Margin finds what looks like personal data by pattern — Social Security numbers, EINs, email addresses, telephone numbers, passport numbers, dates of birth, routing and account numbers. Detection is deterministic for the same reason everything else countable is: a model that sometimes finds an SSN is worse than a regular expression that always finds that shape, because the failure mode is invisible.",
          "Nothing is removed from your documents. Redaction happens on the way out, on the copy you are exporting, and each replacement says what it was — '[redacted: email address]' rather than a black bar — because an auditor asking what you took out deserves better than 'something'. Values are never shown back to you in full: a list view shows a masked preview and the words either side.",
        ],
        steps: [
          {
            label: "See what is in the package",
            detail:
              "The personal-data panel on Versions & Activity lists what was found, in which file, and how much of each kind.",
          },
          {
            label: "Export the ordinary copy for the team",
            detail:
              "It keeps the citations intact. Redacting an officer's email out of a quoted clause would make the quote wrong, which is why masking is not the default.",
          },
          {
            label: "Export the redacted copy for anybody else",
            detail:
              "Same rows, personal data replaced cell by cell so the file still opens, with each replacement naming what it was.",
          },
        ],
        limits: [
          "Pattern detection finds shapes, not meaning. A name on its own is not detected, and a nine-digit number that could be a contract line item is deliberately not treated as an identifier.",
          "It is a review aid, not a compliance guarantee. Read the findings before you send anything to somebody outside the team.",
        ],
      },
      {
        id: "retention",
        title: "Retention and legal hold",
        summary: "Documents age out. The record of what was decided never does.",
        icon: Lock,
        where: "Settings → Data & retention",
        href: "/app/settings?tab=data",
        body: [
          "Most organisations satisfy a retention obligation with a folder nobody empties, and the reason is not laziness: deleting the wrong thing during a protest window is career-ending. The way out is being precise about what is being disposed of.",
          "Retention disposes of documents — the uploaded files, the extracted text, superseded drafts. It never disposes of the record: the requirement ledger, the verdicts, the sign-offs, the questions, the decision record and the audit trail are out of scope on any policy. What was decided and on what basis is the thing an auditor asks for, it is small, and no plausible obligation is served by destroying it.",
          "A pursuit that is still live is never eligible. The clock runs from the last thing that happened to a pursuit rather than from the day it opened. A minimum hold sits under every class so that a policy edited in a hurry cannot reach back into last month. And a legal hold — which needs a written reason — beats every timer.",
        ],
        limits: [
          "Nothing is disposed of automatically on a page load. Disposal is an explicit action, and it is refused if the number of items has changed since the preview you approved.",
          "Only admins can change retention or place a hold. Everybody else can see the policy and what it would dispose of.",
        ],
      },
      {
        id: "record",
        title: "The record",
        summary: "Assembled from the histories the product already keeps, and exportable as a file.",
        icon: BookOpen,
        where: "Workspace → Versions & Activity",
        body: [
          "The audit trail is derived, not stored separately. It is assembled on read from the append-only histories the ledger, the response checks, the Q&A and the runs already keep — because an audit log kept apart from the thing it describes is a second version of history, and the two eventually disagree.",
          "It exports as a spreadsheet, oldest first. A record that cannot leave the product cannot reach the person asking for it, which is the only situation an audit trail exists for.",
        ],
      },
    ],
  },
];

/** Flat list, for search and for the in-page navigation. */
export const MANUAL_SECTIONS = MANUAL.flatMap((chapter) =>
  chapter.sections.map((section) => ({ ...section, chapter: chapter.title, chapterId: chapter.id })),
);

/**
 * The words that carry weight, gathered from every section.
 *
 * Kept as one list because the mistake people make is reading two of these as
 * synonyms — "scanned" for "analysed", "unverifiable" for "failed" — and a
 * glossary split across eight pages never gets read side by side.
 *
 * A word defined in more than one chapter appears once. Where the definitions
 * differ in wording, the longer one wins: the same word listed twice with two
 * descriptions is how a reader concludes it means two different things.
 */
export const GLOSSARY: ManualTerm[] = Object.values(
  MANUAL_SECTIONS.flatMap((section) => section.terms ?? []).reduce<Record<string, ManualTerm>>(
    (out, term) => {
      const existing = out[term.term];
      if (!existing || term.meaning.length > existing.meaning.length) {
        out[term.term] = { ...existing, ...term };
      }
      return out;
    },
    {},
  ),
).sort((a, b) => a.term.localeCompare(b.term));
