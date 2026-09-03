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

const GUIDES = [
  {
    title: "Reading your first solicitation",
    blurb: "Upload a document, choose a mode, and watch the read happen in the open.",
    minutes: "4 min",
    href: "/app/analyses/new",
  },
  {
    title: "Working the compliance matrix",
    blurb: "Assign owners, point each requirement at a response location, and export.",
    minutes: "6 min",
    href: "/app/matrix",
  },
  {
    title: "Deciding go or no-go",
    blurb: "How the four gates are scored, and what the gauge is actually telling you.",
    minutes: "5 min",
    href: "/app/analyses",
  },
  {
    title: "Sending questions to an agency",
    blurb: "Turn the SILENT ledger into a ranked question set and send it through Outlook.",
    minutes: "3 min",
    href: "/app/analyses",
  },
];

const FAQ = [
  {
    q: "Where does a finding come from?",
    a: "Every finding carries a citation — a page, a section, and the quoted line underneath. Hover that source block and the Margin rail opens on the right with the clause highlighted. Nothing is asserted without one.",
  },
  {
    q: "What does the confidence level mean?",
    a: "Confidence is drawn as ink saturation rather than a percentage badge. Anything below the review threshold is marked with a quill and lands in the review queue on the dashboard, because a person should confirm it before it reaches a proposal.",
  },
  {
    q: "What is the SILENT ledger?",
    a: "It is the record of what the document did not say. Missing page limits, unnamed incumbents, ceilings that are implied but never stated. Each entry converts into an agency question in one click.",
  },
  {
    q: "How is the go/no-go score calculated?",
    a: "Four gates are weighted: hard gates can fail the bid outright, soft gates shade the verdict. The gauge shows the resulting position, and recording a decision stamps it with the date, the person, and the note you wrote.",
  },
  {
    q: "Does Margin store our documents?",
    a: "No. Documents are read in place from SharePoint, OneDrive, or the upload you provide. What is stored is the analysis: findings, requirements, and the citations that point back at your copy.",
  },
  {
    q: "What happens when a solicitation is amended?",
    a: "Run an Amendment Refresh. Margin re-reads only what moved and shows a diff of added, changed, and removed language, flagging anything that invalidates work already assigned.",
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
        title="How Margin works"
        description="Short answers, the keyboard reference, and a way to reach a person."
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
          <PanelHeader title="Questions we get asked" />
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
          <Button asChild variant="ghost">
            <Link href="/style">Design system</Link>
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
