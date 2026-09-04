"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowUpRight, BookOpen, LifeBuoy, MessageSquare } from "lucide-react";

import { Button } from "@/components/ui/button";
import { PageHeader, Panel, PanelHeader, Kbd, Well } from "@/components/ui/surface";
import { SearchField } from "@/components/ui/input";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/controls";
import { EmptyState } from "@/components/ui/feedback";
import { notify } from "@/components/ui/toaster";
import { SHORTCUT_GROUPS } from "@/components/shell/shortcuts";
import { useUIStore } from "@/stores/ui";

/**
 * Entry points into the manual, not a separate set of documents.
 *
 * The previous list pointed at product screens and called them guides, which
 * meant the answer to "how does this work" was "here is the thing you already
 * could not understand". Each of these lands on the paragraph that explains it.
 */
const GUIDES = [
  {
    title: "Reading your first solicitation",
    blurb: "Attach the package, choose a mode, and know which two screens to open first.",
    minutes: "4 min",
    href: "/app/manual?s=first-read",
  },
  {
    title: "What Margin counts, and what it judges",
    blurb:
      "Page limits and fonts are decided in code. Everything else is a draft assessment waiting for a person.",
    minutes: "5 min",
    href: "/app/manual?s=mechanical",
  },
  {
    title: "Checking a draft response",
    blurb: "Bind a draft, read the gap, and understand why so much comes back unverifiable.",
    minutes: "5 min",
    href: "/app/manual?s=response-gap",
  },
  {
    title: "Personal data and redacted exports",
    blurb: "What is detected, what masking does, and why it is not the default.",
    minutes: "3 min",
    href: "/app/manual?s=pii",
  },
];

const FAQ = [
  {
    q: "Where does a finding come from?",
    a: "Every finding carries a citation — a document, a page, a section and the quoted line. Hover the source block and the Margin rail opens on the right with the clause highlighted. Nothing is asserted without one, and a quote that cannot be found in the package is treated as an extraction failure rather than as evidence.",
  },
  {
    q: "What is the difference between scanned and analysed?",
    a: "Scanned means a page was extracted and pattern-swept. Analysed means the specialists read it in depth. Coverage reports both because a single completeness number would overstate the reading — and it separately reports pages nothing could be read from at all, such as an image-only PDF.",
  },
  {
    q: "Why does so much come back “unverifiable”?",
    a: "Unverifiable means nobody has been able to check it yet — not that it failed. A wrong “satisfied” on a mandatory requirement loses a bid nobody saw coming; a wrong “unverifiable” costs somebody five minutes. Given that asymmetry, every ambiguous case is pushed to unverifiable on purpose.",
  },
  {
    q: "Will Margin ever mark a mandatory requirement as done?",
    a: "No. A satisfied result on a disqualifying requirement is recorded as a recommendation that needs confirmation, and it stays in the Needs You queue until a person with the authority to clear it signs it off — with their name, the basis, and the verdict it replaced.",
  },
  {
    q: "What is the SILENT ledger?",
    a: "The record of what the document did not say: missing page limits, unnamed incumbents, ceilings that are implied but never stated. Each entry converts into an agency question in one click, and when the answer comes back it reopens only the requirements and response sections that answer actually touched.",
  },
  {
    q: "Does Margin store our documents?",
    a: "Yes — the uploaded file and the text extracted from it are stored with the analysis, because a run must not depend on the system that delivered the bytes still holding them. How long they are kept is a workspace retention policy an admin sets, and disposal never touches the record of what was decided: the ledger, verdicts, sign-offs and audit trail are out of scope on any policy.",
  },
  {
    q: "Can Margin redact personal data before we send something out?",
    a: "It finds what looks like personal data by pattern — identifiers, email addresses, phone numbers, dates of birth, bank details — and can export a redacted copy of the matrix with each replacement naming what it was. It never edits your documents, and masking is not the default because redacting an address out of a quoted clause would make the quote wrong.",
  },
  {
    q: "What happens when a solicitation is amended?",
    a: "Attach the amendment. Margin folds it into the package, pairs each change against the clause it changes, and proposes what now governs — proposes, never applies. Work already assigned against a superseded clause is flagged rather than silently rewritten.",
  },
  {
    q: "Why was I refused an action?",
    a: "Permissions are named after the decision they govern, so signing off a review and resolving a contradiction are separate authorities. The refusal names the roles that have it and what your own role is for. The whole matrix is in Settings → Permissions, including what you cannot do.",
  },
];

export function HelpView() {
  const setShortcutsOpen = useUIStore((s) => s.setShortcutsOpen);
  const setCommandOpen = useUIStore((s) => s.setCommandOpen);
  const [query, setQuery] = React.useState("");

  const q = query.trim().toLowerCase();
  const guides = GUIDES.filter((g) => !q || `${g.title} ${g.blurb}`.toLowerCase().includes(q));
  const faqs = FAQ.filter((f) => !q || `${f.q} ${f.a}`.toLowerCase().includes(q));
  const shortcuts = SHORTCUT_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => !q || item.label.toLowerCase().includes(q)),
  })).filter((group) => group.items.length > 0);

  const nothing = guides.length === 0 && faqs.length === 0 && shortcuts.length === 0;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        eyebrow="Help"
        title="Help & shortcuts"
        description="Short answers, the keyboard reference, and a way to reach a person. The long form is in the manual."
      />

      <SearchField
        value={query}
        onValueChange={setQuery}
        placeholder="Search help…"
        className="max-w-lg"
      />

      {nothing ? (
        <EmptyState
          illustration={<LifeBuoy className="size-7 text-patina" aria-hidden />}
          title="No answer here"
          description="Nothing matched that. Ask us directly and a human will reply the same day."
          action={
            <Button variant="primary" onClick={() => notify.success("Message sent. We reply within a day.")}>
              <MessageSquare />
              Ask a question
            </Button>
          }
        />
      ) : null}

      {guides.length > 0 ? (
        <section className="space-y-3">
          <h2 className="text-lg text-ink">Guides</h2>
          <ul className="grid gap-3 sm:grid-cols-2">
            {guides.map((guide) => (
              <li key={guide.title}>
                <Link href={guide.href} className="group block h-full">
                  <Panel className="flex h-full flex-col p-5 transition-colors duration-200 group-hover:border-patina/40">
                    <p className="font-mono text-2xs uppercase tracking-[0.12em] text-ink-faint">
                      {guide.minutes} read
                    </p>
                    <h3 className="mt-3 flex items-start gap-1.5 text-base text-ink">
                      {guide.title}
                      <ArrowUpRight className="mt-0.5 size-3.5 shrink-0 text-ink-faint opacity-0 transition-opacity duration-200 group-hover:opacity-100" />
                    </h3>
                    <p className="mt-1 flex-1 text-sm leading-relaxed text-ink-soft">{guide.blurb}</p>
                  </Panel>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {faqs.length > 0 ? (
        <Panel>
          <PanelHeader
            title="Questions we get asked"
            description="Longer answers, and the vocabulary behind them, are in the manual."
          />
          <div className="px-5">
            <Accordion type="single" collapsible>
              {faqs.map((item) => (
                <AccordionItem key={item.q} value={item.q}>
                  <AccordionTrigger>{item.q}</AccordionTrigger>
                  <AccordionContent>
                    <p className="max-w-2xl pb-4 text-sm leading-relaxed text-ink-soft">{item.a}</p>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </div>
        </Panel>
      ) : null}

      {shortcuts.length > 0 ? (
        <Panel>
          <PanelHeader
            title="Keyboard reference"
            description="Press ? anywhere to open this as a dialog."
            actions={
              <Button variant="secondary" size="sm" onClick={() => setShortcutsOpen(true)}>
                Open dialog
              </Button>
            }
          />
          <div className="grid gap-x-10 gap-y-6 p-5 sm:grid-cols-2">
            {shortcuts.map((group) => (
              <div key={group.group}>
                <p className="eyebrow pb-2">{group.group}</p>
                <dl>
                  {group.items.map((item) => (
                    <div
                      key={item.label}
                      className="flex items-center justify-between gap-4 border-b border-line py-2 last:border-b-0"
                    >
                      <dt className="text-sm text-ink-soft">{item.label}</dt>
                      <dd className="flex shrink-0 items-center gap-1">
                        {item.keys.map((key, i) =>
                          key === "then" ? (
                            <span key={i} className="px-0.5 text-2xs text-ink-faint">
                              then
                            </span>
                          ) : (
                            <Kbd key={i}>{key}</Kbd>
                          ),
                        )}
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>
            ))}
          </div>
        </Panel>
      ) : null}

      <Well className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm font-medium text-ink">Still stuck?</p>
          <p className="text-sm text-ink-soft">
            A person answers within one business day — usually much sooner.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setCommandOpen(true)}>
            <BookOpen />
            Command palette
          </Button>
          <Button asChild variant="secondary">
            <Link href="/app/manual">
              <BookOpen />
              Read the manual
            </Link>
          </Button>
          <Button variant="primary" onClick={() => notify.success("Message sent. We reply within a day.")}>
            <MessageSquare />
            Contact support
          </Button>
        </div>
      </Well>
    </div>
  );
}
