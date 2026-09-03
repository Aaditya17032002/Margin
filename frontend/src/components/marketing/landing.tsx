"use client";

import * as React from "react";
import Link from "next/link";
import { motion } from "motion/react";
import { ArrowRight, ShieldCheck } from "lucide-react";

import { AGENTS } from "@/data/agents";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { BronzeGate, WaxSeal } from "@/components/domain/marks";
import { DemoStrip, ManuscriptDemo } from "./demo-strip";
import { PricingTable } from "./pricing-table";

const FEATURES = [
  {
    title: "A compliance matrix that assigns itself",
    body: "Every shall, must, and will lifted into a row with its clause attached, ready to hand to an owner and point at a response location.",
  },
  {
    title: "A go/no-go you can defend",
    body: "Four gates, weighted. The gauge shows where the bid stands, and recording a decision stamps it with the reason you gave.",
  },
  {
    title: "The SILENT ledger",
    body: "What the document never said — unnamed incumbents, absent ceilings, missing page limits. Each entry becomes an agency question in a click.",
  },
  {
    title: "Deadlines in the agency's time zone",
    body: "Not yours. Countdowns tick against the zone the solicitation was written in, because that is the one that closes the window.",
  },
  {
    title: "Amendments as a diff",
    body: "Re-read against a new amendment and see only what moved, with anything that invalidates assigned work flagged in red.",
  },
  {
    title: "Questions ranked by consequence",
    body: "Agencies answer in order and rarely answer everything. The ones that move the decision float to the top of the set.",
  },
];

const PROOF = [
  {
    quote:
      "We used to lose a day to the first read and still miss the page limit. Now the limit is the first thing on the screen, with the clause beside it.",
    name: "Renée Alvarado",
    title: "Director of Capture, 340-person integrator",
  },
  {
    quote:
      "The SILENT ledger is the part nobody else does. It told us the incumbent was never named, which turned into the question that won us the re-compete.",
    name: "Marcus Hale",
    title: "Proposal Manager, health IT",
  },
  {
    quote:
      "I don't trust summaries. I trust the citation. Margin is the only tool where I can click a claim and land on the line.",
    name: "Priya Raghunathan",
    title: "Compliance Lead, civil works",
  },
];

const NUMBERS = [
  { value: "214", label: "pages read in four minutes" },
  { value: "186", label: "requirements extracted, each cited" },
  { value: "0", label: "claims without a source" },
];

export function LandingView() {
  return (
    <>
      <Hero />
      <MarginSection />
      <HowItReads />
      <Features />
      <Proof />
      <PricingPreview />
      <FinalCta />
    </>
  );
}

function Hero() {
  return (
    <section className="border-b border-line">
      <div className="mx-auto grid max-w-[76rem] items-start lg:grid-cols-[minmax(0,22.5rem)_minmax(0,1fr)]">
        <div className="border-b border-line px-5 py-6 lg:border-b-0 lg:border-r lg:px-8 lg:py-7">
          <Badge tone="patina">For teams who read solicitations for a living</Badge>
          <h1 className="display-tight mt-4 text-[1.85rem] leading-[1.12] text-ink sm:text-[2.125rem]">
            The solicitation already told you whether to bid.
            <span className="block text-ink-faint">Somebody has to read all 214 pages.</span>
          </h1>
          <p className="mt-3 text-[0.9375rem] leading-relaxed text-ink-soft">
            Every finding carries the page, the section, and the line it came from. Hover a finding — the clause lights
            beside it.
          </p>
          <div className="mt-5 flex flex-wrap items-center gap-2.5">
            <Button asChild variant="primary">
              <Link href="/signup">
                Read your first solicitation
                <ArrowRight />
              </Link>
            </Button>
            <Button asChild variant="secondary">
              <Link href="/app">See a finished analysis</Link>
            </Button>
          </div>
          <p className="mt-3 flex items-center gap-2 text-xs text-ink-faint">
            <ShieldCheck className="size-3.5 shrink-0" aria-hidden />
            Documents are read in place. Citations stay; the file does not.
          </p>
        </div>

        <div className="min-w-0 px-5 py-6 lg:px-8 lg:py-7">
          <DemoStrip />
        </div>
      </div>

      <dl className="mx-auto grid max-w-[76rem] border-t border-line sm:grid-cols-3">
        {NUMBERS.map((item) => (
          <div
            key={item.label}
            className="flex items-baseline gap-4 border-t border-line px-5 py-4 sm:border-t-0 sm:border-l sm:first:border-l-0 lg:px-8"
          >
            <dt className="sr-only">{item.label}</dt>
            <dd className="flex items-baseline gap-3">
              <span className="font-display text-2xl leading-none text-ink tabular">{item.value}</span>
              <span className="text-sm text-ink-soft">{item.label}</span>
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function MarginSection() {
  return (
    <section id="margin" className="scroll-mt-16 border-b border-line">
      <div className="mx-auto grid max-w-[76rem] items-start lg:grid-cols-[minmax(0,22.5rem)_minmax(0,1fr)]">
        <div className="border-b border-line px-5 py-6 lg:border-b-0 lg:border-r lg:px-8 lg:py-7">
          <p className="eyebrow">The idea</p>
          <h2 className="display-tight mt-3 text-2xl leading-snug text-ink sm:text-[1.75rem]">
            Scholars have argued in the margin for eight hundred years.
          </h2>
          <div className="mt-4 space-y-3 text-sm leading-relaxed text-ink-soft">
            <p>
              The margin is where the reader answers the text — <em>where does it say that</em>, and where the answer
              belongs.
            </p>
            <p className="text-ink">
              Touch a citation. The document opens on that line, in the author&rsquo;s words.
            </p>
          </div>
          <Button asChild variant="link" size="sm" className="mt-5 px-0">
            <Link href="/app">
              Open the workspace
              <ArrowRight />
            </Link>
          </Button>
        </div>

        <figure className="min-w-0 px-5 py-6 lg:px-8 lg:py-7">
          <ManuscriptDemo />
          <figcaption className="mt-2.5 font-mono text-2xs text-ink-faint">
            Hover a citation. The source moves with you.
          </figcaption>
        </figure>
      </div>
    </section>
  );
}

function HowItReads() {
  return (
    <section id="how" className="scroll-mt-16 border-b border-line bg-paper-raised py-10 lg:py-12">
      <div className="mx-auto max-w-[76rem] px-5 lg:px-8">
        <div className="max-w-2xl">
          <p className="eyebrow">How it reads a document</p>
          <h2 className="display-tight mt-3 text-3xl leading-tight text-ink sm:text-4xl">
            Eight readers, in order, each refusing to leave until its part is cited.
          </h2>
          <p className="mt-5 text-base leading-relaxed text-ink-soft">
            You watch it happen. No spinner, no progress bar pretending to be busy — a roster of readers taking the
            floor one at a time, their reasoning streaming as they work, findings settling into the page as each one
            is confirmed against the clause it came from.
          </p>
        </div>

        <ol className="mt-8 grid gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-2 lg:grid-cols-4">
          {AGENTS.map((agent, index) => (
            <motion.li
              key={agent.id}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ delay: Math.min(index * 0.04, 0.3), duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
              className="bg-paper-raised p-5"
            >
              <div className="flex items-baseline gap-2.5">
                <span className="font-mono text-2xs text-ink-faint tabular">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <h3 className="text-base text-ink">{agent.name}</h3>
              </div>
              <p className="mt-2 text-sm leading-relaxed text-ink-soft">{agent.duty}</p>
              <p className="mt-3 border-t border-line pt-3 font-mono text-2xs leading-relaxed text-ink-faint">
                “{agent.lines[1]}”
              </p>
            </motion.li>
          ))}
        </ol>

        <div className="mt-8 flex flex-wrap items-center gap-3">
          <Button asChild variant="secondary">
            <Link href="/app/analyses/new">
              Watch it read one
              <ArrowRight />
            </Link>
          </Button>
          <p className="text-sm text-ink-faint">A standard pass over 214 pages takes about four minutes.</p>
        </div>
      </div>
    </section>
  );
}

function Features() {
  return (
    <section className="border-b border-line py-20 lg:py-28">
      <div className="mx-auto max-w-[76rem] px-5 lg:px-8">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div className="max-w-xl">
            <p className="eyebrow">What you get back</p>
            <h2 className="display-tight mt-3 text-3xl leading-tight text-ink sm:text-4xl">
              Not a summary. A working surface.
            </h2>
          </div>
          <p className="max-w-sm text-sm leading-relaxed text-ink-soft">
            A summary is something you have to check. Every artefact below is something you can hand to a person and
            they can start work on it the same hour.
          </p>
        </div>

        <ol className="relative mt-12">
          <span
            aria-hidden
            className="pointer-events-none absolute inset-y-0 left-[1.15rem] hidden w-px bg-[color-mix(in_oklab,var(--seal)_20%,transparent)] sm:block"
          />
          {FEATURES.map((feature, index) => (
            <motion.li
              key={feature.title}
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ delay: Math.min(index * 0.04, 0.24), duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
              className="grid gap-2 border-t border-line py-8 sm:grid-cols-[4.5rem_minmax(0,18rem)_1fr] sm:gap-10"
            >
              <span className="font-mono text-2xs tabular text-ink-faint">
                {String(index + 1).padStart(2, "0")}
              </span>
              <h3 className="font-display text-xl leading-snug text-ink">{feature.title}</h3>
              <p className="max-w-xl text-sm leading-relaxed text-ink-soft sm:pt-1">{feature.body}</p>
            </motion.li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function Proof() {
  return (
    <section id="evidence" className="scroll-mt-20 border-b border-line bg-paper-raised py-20 lg:py-28">
      <div className="mx-auto max-w-[76rem] px-5 lg:px-8">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div className="max-w-xl">
            <p className="eyebrow">Evidence</p>
            <h2 className="display-tight mt-3 text-3xl leading-tight text-ink sm:text-4xl">
              The people who read these documents for a living.
            </h2>
          </div>
          <div className="flex items-center gap-4 text-ink-faint">
            <WaxSeal className="size-9" label="" />
            <p className="max-w-40 text-xs leading-relaxed">
              Every quotation below is fictional, as is every solicitation in the demo.
            </p>
          </div>
        </div>

        <ul className="mt-14 grid gap-x-12 gap-y-12 lg:grid-cols-12">
          {PROOF.map((item, index) => (
            <motion.li
              key={item.name}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ delay: index * 0.06, duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
              className={index === 0 ? "border-t border-line pt-8 lg:col-span-12" : "border-t border-line pt-8 lg:col-span-6"}
            >
              <blockquote
                className={
                  index === 0
                    ? "max-w-3xl font-display text-2xl leading-snug text-ink sm:text-3xl"
                    : "max-w-xl text-base leading-relaxed text-ink"
                }
              >
                {item.quote}
              </blockquote>
              <p className="mt-5 text-sm text-ink">
                {item.name}
                <span className="text-ink-faint"> · {item.title}</span>
              </p>
            </motion.li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function PricingPreview() {
  return (
    <section className="border-b border-line py-20 lg:py-28">
      <div className="mx-auto max-w-[76rem] px-5 lg:px-8">
        <div className="max-w-xl">
          <p className="eyebrow">Pricing</p>
          <h2 className="display-tight mt-3 text-3xl leading-tight text-ink sm:text-4xl">
            Priced per seat, because that is who does the reading.
          </h2>
        </div>
        <PricingTable className="mt-12" compact />
      </div>
    </section>
  );
}

function FinalCta() {
  return (
    <section className="relative overflow-hidden py-20 lg:py-28">
      <div className="mx-auto max-w-[76rem] px-5 lg:px-8">
        <div className="relative overflow-hidden rounded-xl border border-line bg-paper-raised px-6 py-14 text-center shadow-[var(--shadow-raised)] sm:px-12">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="mx-auto max-w-xl"
          >
            <BronzeGate open={0.72} className="mx-auto max-w-40 opacity-80" />
            <h2 className="display-tight mt-6 text-3xl leading-tight text-ink sm:text-4xl">
              The next one is 214 pages and due in eleven days.
            </h2>
            <p className="mt-4 text-base leading-relaxed text-ink-soft">
              Give it to Margin and have the compliance matrix, the gates, and the questions before lunch.
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <Button asChild variant="primary" size="lg">
                <Link href="/signup">
                  Start reading
                  <ArrowRight />
                </Link>
              </Button>
              <Button asChild variant="ghost" size="lg">
                <Link href="/app">Look around first</Link>
              </Button>
            </div>
            <p className="mt-5 text-xs text-ink-faint">
              No card. Upload one solicitation and the whole workspace fills from it.
            </p>
          </motion.div>
        </div>
      </div>
    </section>
  );
}