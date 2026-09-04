"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Callout, EmptyState } from "@/components/ui/feedback";
import { Field, Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/controls";
import { BronzeGate, QuillMark, WaxSeal } from "@/components/domain/marks";
import { CitationChip, CitationMeta, StakesBadge } from "@/components/domain/primitives";
import type { Citation } from "@/types";

const SWATCHES = [
  { name: "Paper", token: "--paper" },
  { name: "Raised", token: "--paper-raised" },
  { name: "Sunk", token: "--paper-sunk" },
  { name: "Ink", token: "--ink" },
  { name: "Ink soft", token: "--ink-soft" },
  { name: "Ink faint", token: "--ink-faint" },
  { name: "Patina", token: "--patina" },
  { name: "Patina tint", token: "--patina-tint" },
  { name: "Seal", token: "--seal" },
  { name: "Ochre", token: "--ochre" },
  { name: "Leaf", token: "--leaf" },
  { name: "Slate", token: "--slate" },
] as const;

const SAMPLE_CITATION: Citation = {
  id: "style-cite",
  page: 47,
  section: "§ L.3.1",
  quote: "Volume I, Technical, shall not exceed forty (40) pages, excluding resumes, letters of commitment, and the cross-reference matrix.",
  bbox: { x: 0.11, y: 0.22, w: 0.78, h: 0.08 },
};

export function StyleGuideView() {
  const [toggle, setToggle] = React.useState(true);

  return (
    <div className="mx-auto max-w-[76rem] space-y-20 px-5 py-16 lg:px-8 lg:py-24">
      <header className="max-w-2xl">
        <p className="eyebrow">Design system</p>
        <h1 className="display-tight mt-3 text-4xl leading-tight text-ink sm:text-5xl">
          Fine paper, ink, and the patina of bronze.
        </h1>
        <p className="mt-5 text-lg leading-relaxed text-ink-soft">
          The primitives Margin is built from. Restyled past the defaults; nothing here is shipped as shadcn left it.
        </p>
      </header>

      <Section kicker="Colour" title="Warm civic, never neon.">
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {SWATCHES.map((swatch) => (
            <li key={swatch.token} className="space-y-2">
              <div
                className="h-16 rounded-md border border-line"
                style={{ background: `var(${swatch.token})` }}
              />
              <p className="text-xs font-medium text-ink">{swatch.name}</p>
              <p className="font-mono text-2xs text-ink-faint">{swatch.token}</p>
            </li>
          ))}
        </ul>
      </Section>

      <Section kicker="Type" title="An editorial trio.">
        <div className="space-y-8">
          <div>
            <p className="eyebrow">Display · Fraunces</p>
            <p className="display-tight mt-2 font-display text-4xl leading-tight text-ink sm:text-5xl">
              The solicitation already told you whether to bid.
            </p>
          </div>
          <div>
            <p className="eyebrow">Body · Geist Sans</p>
            <p className="mt-2 max-w-xl text-base leading-relaxed text-ink-soft">
              Margin reads it the way a senior capture lead does — start to finish, in order, taking notes in the
              margin. Every finding it gives you carries the page, the section, and the line it came from.
            </p>
          </div>
          <div>
            <p className="eyebrow">Data · Geist Mono</p>
            <p className="mt-2 font-mono text-sm text-ink">TEA-2026-DLP-114 · p.47 §L.3.1 · 214 pages</p>
          </div>
        </div>
      </Section>

      <Section kicker="Controls" title="Keys, not toys.">
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="primary">Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="quiet">Quiet</Button>
          <Button variant="danger">Danger</Button>
          <Button variant="outlineDanger">Outline danger</Button>
          <Button variant="primary" loading>
            Working
          </Button>
        </div>
        <div className="mt-8 grid max-w-sm gap-4">
          <Field label="Work email" htmlFor="sg-email" hint="Becomes the workspace domain">
            <Input id="sg-email" defaultValue="a.osei@thornfield.co" />
          </Field>
          <div className="flex items-center gap-3">
            <Switch checked={toggle} onCheckedChange={setToggle} aria-label="Sample switch" />
            <span className="text-sm text-ink-soft">A switch that reads as a latch, not a toy.</span>
          </div>
        </div>
      </Section>

      <Section kicker="Marks" title="Stakes, confidence, citation.">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="patina">Practice plan</Badge>
          <StakesBadge stakes="disqualifying" />
          <StakesBadge stakes="scored" />
          <StakesBadge stakes="informational" />
          <CitationChip citation={SAMPLE_CITATION} analysisId="style" label="Page limit" origin="Style" />
          <QuillMark />
        </div>
        <article className="mt-8 max-w-2xl space-y-3 border-t border-line py-5">
          <div className="grid gap-x-6 gap-y-2 sm:grid-cols-[11rem_minmax(0,1fr)]">
            <div className="space-y-1.5">
              <h4 className="text-sm font-medium text-ink-soft">Page limit</h4>
              <StakesBadge stakes="disqualifying" />
            </div>
            <p className="text-sm leading-relaxed text-ink">
              Volume I is capped at 40 pages, excluding resumes and the cross-reference matrix.
            </p>
          </div>
          <CitationMeta citation={SAMPLE_CITATION} analysisId="style" label="Page limit" origin="Style" />
        </article>
      </Section>

      <Section kicker="Motifs" title="Wax, quill, bronze gate.">
        <div className="grid items-end gap-10 sm:grid-cols-3">
          <div className="space-y-3">
            <WaxSeal className="size-20" label="A hard gate is unmet" />
            <p className="text-sm text-ink-soft">Wax seal — stamps on an unmet hard gate.</p>
          </div>
          <div className="space-y-3">
            <BronzeGate open={0.62} className="max-w-48" />
            <p className="text-sm text-ink-soft">Bronze gate — opens with the go/no-go reading.</p>
          </div>
          <div className="space-y-3">
            <p className="font-mono text-2xs uppercase tracking-[0.13em] text-ink-faint">Needs review</p>
            <QuillMark className="size-8 text-ochre" />
            <p className="text-sm text-ink-soft">Quill mark — a finding below the confidence threshold.</p>
          </div>
        </div>
      </Section>

      <Section kicker="Feedback" title="The same object, a different mark in the margin.">
        <div className="space-y-3">
          <Callout tone="seal" title="A hard gate is unmet">
            Transition-in dropped from 90 to 45 days. The bid cannot proceed until this is resolved or the decision is
            No-bid.
          </Callout>
          <Callout tone="ochre" title="Six findings need review">
            Confidence fell below the threshold. A person should confirm them before they reach a proposal.
          </Callout>
          <Callout tone="leaf" title="Matrix assignment sweep complete">
            Thirty-four rows assigned across four owners.
          </Callout>
          <Callout tone="slate" title="SharePoint sync completed">
            Capture Library indexed. 148 documents.
          </Callout>
        </div>
        <div className="mt-8">
          <EmptyState
            title="Nothing in flight"
            description="Upload a solicitation and Margin will read it end to end, then tell you what it found and what it could not find."
            action={<Button variant="primary">Start an analysis</Button>}
          />
        </div>
      </Section>
    </div>
  );
}

function Section({
  kicker,
  title,
  children,
}: {
  kicker: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-t border-line pt-12">
      <p className="eyebrow">{kicker}</p>
      <h2 className="display-tight mt-2 text-2xl text-ink sm:text-3xl">{title}</h2>
      <div className="mt-8">{children}</div>
    </section>
  );
}
