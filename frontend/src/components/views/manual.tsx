"use client";

import * as React from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowUpRight, BookOpen, Info, Keyboard } from "lucide-react";

import { cn } from "@/lib/utils";
import { governanceApi } from "@/lib/api";
import { MANUAL, MANUAL_SECTIONS, GLOSSARY, type ManualSection } from "@/data/manual";
import { MODES } from "@/data/agents";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Callout, EmptyState } from "@/components/ui/feedback";
import { SearchField } from "@/components/ui/input";
import { PageHeader, Panel, PanelHeader, Well } from "@/components/ui/surface";
import type { PermissionModel } from "@/types";

/**
 * The manual.
 *
 * Not a marketing tour and not a FAQ. The thing a person needs on their second
 * day is a reference: what each word means, what each surface decides, and —
 * the half most product documentation leaves out — what each feature
 * deliberately does not do. Nearly every support question about a product like
 * this is somebody expecting a feature to have decided something it did not.
 *
 * Content lives in `@/data/manual` as structured data so it can be searched,
 * linked and kept beside the code that implements it. Two things are read live
 * rather than written down: the modes, from the same descriptors the new-analysis
 * screen uses, and the permission model, from the API — a manual that describes
 * a permission table by hand is one that will eventually describe the wrong one.
 */

export function ManualView() {
  const params = useSearchParams();
  const requested = params.get("s");
  const [query, setQuery] = React.useState("");
  const [active, setActive] = React.useState<string>(
    requested && MANUAL_SECTIONS.some((section) => section.id === requested)
      ? requested
      : MANUAL[0].sections[0].id,
  );

  // Deep links land on a section rather than at the top. The manual is long
  // enough that "see the manual" is useless without one, and every place that
  // links here already knows which paragraph it means.
  React.useEffect(() => {
    if (!requested) return;
    document
      .getElementById(`manual-${requested}`)
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [requested]);

  const q = query.trim().toLowerCase();
  const matches = React.useMemo(() => {
    if (!q) return null;
    return new Set(
      MANUAL_SECTIONS.filter((section) =>
        [
          section.title,
          section.summary,
          section.chapter,
          ...section.body,
          ...(section.limits ?? []),
          ...(section.steps ?? []).flatMap((step) => [step.label, step.detail]),
          ...(section.terms ?? []).flatMap((term) => [term.term, term.meaning, term.notThe ?? ""]),
        ]
          .join(" ")
          .toLowerCase()
          .includes(q),
      ).map((section) => section.id),
    );
  }, [q]);

  const chapters = MANUAL.map((chapter) => ({
    ...chapter,
    sections: chapter.sections.filter((section) => !matches || matches.has(section.id)),
  })).filter((chapter) => chapter.sections.length > 0);

  function go(id: string) {
    setActive(id);
    document.getElementById(`manual-${id}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className="mx-auto max-w-[76rem] space-y-6">
      <PageHeader
        eyebrow="Manual"
        title="How Margin works"
        description="What each surface decides, what every word means, and what each feature deliberately leaves to you."
        actions={
          <Button asChild variant="secondary" size="sm">
            <Link href="/app/help">
              <Keyboard />
              Shortcuts & support
            </Link>
          </Button>
        }
      />

      <SearchField
        value={query}
        onValueChange={setQuery}
        placeholder="Search the manual — try “unverifiable”, “retention”, “redacted”…"
        className="max-w-xl"
      />

      {chapters.length === 0 ? (
        <EmptyState
          illustration={<BookOpen className="size-7 text-patina" aria-hidden />}
          title="Nothing in the manual matches that"
          description="Try a word the product uses on screen — a status, a role, or the name of a tab."
        />
      ) : (
        <div className="grid gap-8 lg:grid-cols-[15rem_minmax(0,1fr)]">
          <nav aria-label="Manual contents" className="lg:sticky lg:top-4 lg:self-start">
            <ul className="scrollbar-none flex gap-4 overflow-x-auto border-b border-line pb-3 lg:block lg:space-y-4 lg:border-b-0 lg:pb-0">
              {chapters.map((chapter) => (
                <li key={chapter.id} className="shrink-0 lg:shrink">
                  <p className="eyebrow pb-1.5">{chapter.title}</p>
                  <ul className="space-y-0.5">
                    {chapter.sections.map((section) => (
                      <li key={section.id}>
                        <button
                          type="button"
                          onClick={() => go(section.id)}
                          aria-current={active === section.id ? "true" : undefined}
                          className={cn(
                            "w-full whitespace-nowrap rounded-md px-2 py-1 text-left text-sm transition-colors duration-150 lg:whitespace-normal",
                            active === section.id
                              ? "bg-patina-tint text-ink"
                              : "text-ink-soft hover:bg-paper-sunk hover:text-ink",
                          )}
                        >
                          {section.title}
                        </button>
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          </nav>

          <div className="min-w-0 space-y-10">
            {chapters.map((chapter) => (
              <section key={chapter.id} className="space-y-5">
                <header>
                  <h2 className="text-lg text-ink">{chapter.title}</h2>
                  <p className="text-sm text-ink-soft">{chapter.blurb}</p>
                </header>

                {chapter.sections.map((section) => (
                  <Section key={section.id} section={section} />
                ))}

                {chapter.id === "modes" && !q ? <ModeReference /> : null}
                {chapter.id === "governance" && !q ? <YourRole /> : null}
              </section>
            ))}

            {!q ? <Glossary /> : null}
          </div>
        </div>
      )}
    </div>
  );
}

function Section({ section }: { section: ManualSection }) {
  const Icon = section.icon;
  return (
    <Panel id={`manual-${section.id}`} className="scroll-mt-[9.5rem]">
      <PanelHeader
        title={
          <span className="flex items-center gap-2">
            <Icon className="size-4 text-patina" aria-hidden />
            {section.title}
          </span>
        }
        description={section.summary}
        actions={
          section.href ? (
            <Button asChild variant="quiet" size="sm">
              <Link href={section.href}>
                Open
                <ArrowUpRight />
              </Link>
            </Button>
          ) : undefined
        }
      />

      <div className="space-y-4 px-5 pb-5">
        {section.where ? (
          <p className="font-mono text-2xs uppercase tracking-[0.12em] text-ink-faint">
            {section.where}
          </p>
        ) : null}

        {section.body.map((paragraph) => (
          <p key={paragraph.slice(0, 40)} className="max-w-3xl text-sm leading-relaxed text-ink-soft">
            {paragraph}
          </p>
        ))}

        {section.steps ? (
          <ol className="space-y-2.5">
            {section.steps.map((step, index) => (
              <li key={step.label} className="flex gap-3">
                <span
                  aria-hidden
                  className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-paper-sunk font-mono text-2xs text-ink-faint"
                >
                  {index + 1}
                </span>
                <div className="min-w-0">
                  <p className="text-sm text-ink">{step.label}</p>
                  <p className="text-sm leading-relaxed text-ink-soft">{step.detail}</p>
                </div>
              </li>
            ))}
          </ol>
        ) : null}

        {section.terms ? (
          <dl className="divide-y divide-line border-y border-line">
            {section.terms.map((term) => (
              <div key={term.term} className="grid gap-1 py-2.5 sm:grid-cols-[10rem_minmax(0,1fr)] sm:gap-4">
                <dt className="text-sm text-ink">{term.term}</dt>
                <dd className="text-sm leading-relaxed text-ink-soft">
                  {term.meaning}
                  {term.notThe ? (
                    <span className="mt-0.5 block text-ink-faint">{term.notThe}</span>
                  ) : null}
                </dd>
              </div>
            ))}
          </dl>
        ) : null}

        {section.limits ? (
          <Callout tone="slate" title="What this does not do">
            <ul className="space-y-1">
              {section.limits.map((limit) => (
                <li key={limit}>{limit}</li>
              ))}
            </ul>
          </Callout>
        ) : null}
      </div>
    </Panel>
  );
}

/**
 * The modes, read from the same descriptors the new-analysis screen uses.
 *
 * Written out by hand they would be wrong within a release, and a manual that
 * lists a mode the product no longer offers is worse than one that omits it.
 */
function ModeReference() {
  return (
    <Panel>
      <PanelHeader
        title="Every mode"
        description="Same recall floor underneath all of them. What changes is which questions are asked."
      />
      <div className="grid gap-3 px-5 pb-5 sm:grid-cols-2">
        {MODES.map((mode) => (
          <Well key={mode.id}>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm text-ink">{mode.name}</span>
              <Badge tone="neutral" shape="mono">
                {mode.minutes}
              </Badge>
              <Badge tone="neutral" shape="mono">
                {mode.passes}
              </Badge>
            </div>
            <p className="mt-1 text-sm leading-relaxed text-ink-soft">{mode.blurb}</p>
            <p className="mt-1.5 font-mono text-2xs uppercase tracking-[0.12em] text-ink-faint">
              {mode.agents.join(" · ")}
            </p>
          </Well>
        ))}
      </div>
    </Panel>
  );
}

/**
 * What the person reading the manual can actually do, from the live model.
 *
 * A manual that describes a permission table by hand eventually describes the
 * wrong one — and the question somebody has while reading this section is
 * never "what can a reviewer do", it is "why was I just refused".
 */
function YourRole() {
  const [model, setModel] = React.useState<PermissionModel | null>(null);

  React.useEffect(() => {
    let live = true;
    governanceApi
      .permissions()
      .then((result) => {
        if (live) setModel(result);
      })
      .catch(() => {
        if (live) setModel(null);
      });
    return () => {
      live = false;
    };
  }, []);

  if (!model) return null;

  return (
    <Panel>
      <PanelHeader
        title="What you can do here"
        description={`Read from the live permission model, not from this page.`}
        actions={<Badge tone="neutral">{model.you.role}</Badge>}
      />
      <div className="space-y-3 px-5 pb-5">
        <p className="text-sm leading-relaxed text-ink-soft">
          You are a {model.you.role}, which {model.you.purpose}.
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          <Well>
            <p className="text-xs font-medium text-ink">You can</p>
            <ul className="mt-1 space-y-0.5 text-xs text-ink-soft">
              {model.permissions
                .filter((permission) => model.you.can.includes(permission.name))
                .map((permission) => (
                  <li key={permission.name}>{permission.describes}</li>
                ))}
            </ul>
          </Well>
          {model.you.cannot.length > 0 ? (
            <Well>
              <p className="text-xs font-medium text-ink">You cannot</p>
              <ul className="mt-1 space-y-0.5 text-xs text-ink-soft">
                {model.permissions
                  .filter((permission) => model.you.cannot.includes(permission.name))
                  .map((permission) => (
                    <li key={permission.name}>
                      {permission.describes} — {permission.roles.join(" or ")}
                    </li>
                  ))}
              </ul>
            </Well>
          ) : null}
        </div>
        <Button asChild variant="quiet" size="sm">
          <Link href="/app/settings?tab=permissions">
            See the whole matrix
            <ArrowUpRight />
          </Link>
        </Button>
      </div>
    </Panel>
  );
}

/**
 * Every load-bearing word in one place.
 *
 * The mistake this exists to prevent is reading two of them as synonyms —
 * "scanned" for "analysed", "unverifiable" for "failed". A glossary split
 * across eight pages never gets read side by side, which is the only way that
 * mistake becomes visible.
 */
function Glossary() {
  return (
    <Panel id="manual-glossary" className="scroll-mt-[9.5rem]">
      <PanelHeader
        title="Glossary"
        description="The words that carry weight. Two of these are not synonyms, however much they read like it."
      />
      <div className="px-5 pb-5">
        <Callout tone="slate" title="Read these next to each other">
          <p>
            Scanned is not analysed, and unverifiable is not failed. A number read through the
            wrong one of those pairs looks like reassurance and is not.
          </p>
        </Callout>
        <dl className="mt-4 divide-y divide-line border-y border-line">
          {GLOSSARY.map((term) => (
            <div key={term.term} className="grid gap-1 py-2.5 sm:grid-cols-[10rem_minmax(0,1fr)] sm:gap-4">
              <dt className="text-sm text-ink">{term.term}</dt>
              <dd className="text-sm leading-relaxed text-ink-soft">
                {term.meaning}
                {term.notThe ? (
                  <span className="mt-0.5 flex items-start gap-1.5 text-ink-faint">
                    <Info className="mt-0.5 size-3 shrink-0" aria-hidden />
                    {term.notThe}
                  </span>
                ) : null}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </Panel>
  );
}
