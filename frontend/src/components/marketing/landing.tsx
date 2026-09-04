"use client";

import * as React from "react";
import Link from "next/link";
import { motion, useReducedMotion } from "motion/react";
import { ArrowRight, ShieldCheck } from "lucide-react";

import { cn } from "@/lib/utils";
import { AGENTS } from "@/data/agents";
import { Button } from "@/components/ui/button";
import { DemoStrip, ManuscriptDemo } from "./demo-strip";
import { PricingTable } from "./pricing-table";

/**
 * The landing page.
 *
 * One idea per screen, and the space to take it in. Every section is built
 * from the same three parts — an eyebrow, a single claim, and the evidence for
 * it — so the page has a rhythm you can feel before you have read a word of it.
 * The vertical scale here is deliberately much larger than the application's:
 * the workspace is dense because a capture lead is working, and this page is
 * open because a stranger is deciding.
 */

const ARTIFACTS = [
  {
    index: "01",
    title: "A compliance matrix that assigns itself",
    body: "Every shall, must, and will lifted into a row with its clause attached — ready to hand to an owner and point at a response location.",
  },
  {
    index: "02",
    title: "A go/no-go you can defend",
    body: "Eligibility gates, weighted. The gauge shows where the bid stands, and recording a decision stamps it with the reason you gave.",
  },
  {
    index: "03",
    title: "The SILENT ledger",
    body: "What the document never said — unnamed incumbents, absent ceilings, missing page limits. Each entry becomes an agency question in a click.",
  },
  {
    index: "04",
    title: "Deadlines in the agency's time zone",
    body: "Not yours. Countdowns tick against the zone the solicitation was written in, because that is the one that closes the window.",
  },
  {
    index: "05",
    title: "Amendments as a diff",
    body: "Re-read against a new amendment and see only what moved, with anything that invalidates assigned work flagged in red.",
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
      <Numbers />
      <MarginSection />
      <HowItReads />
      <Artifacts />
      <Proof />
      <PricingPreview />
      <FinalCta />
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Shared section scaffolding                                          */
/* ------------------------------------------------------------------ */

/** Every band on the page uses the same measure and the same generous rhythm. */
function Band({
  id,
  className,
  children,
  tone = "paper",
}: {
  id?: string;
  className?: string;
  children: React.ReactNode;
  tone?: "paper" | "raised" | "sunk";
}) {
  return (
    <section
      id={id}
      className={cn(
        "scroll-mt-20 px-6 py-24 sm:px-8 sm:py-32 lg:py-40",
        tone === "raised" && "bg-paper-raised",
        tone === "sunk" && "bg-paper-sunk",
        className,
      )}
    >
      <div className="mx-auto w-full max-w-[78rem]">{children}</div>
    </section>
  );
}

/** A heading block: eyebrow, claim, and at most one sentence under it. */
function Lede({
  eyebrow,
  title,
  body,
  align = "left",
  className,
}: {
  eyebrow?: string;
  title: React.ReactNode;
  body?: React.ReactNode;
  align?: "left" | "center";
  className?: string;
}) {
  return (
    <Reveal
      className={cn(
        "max-w-[42rem]",
        align === "center" && "mx-auto text-center",
        className,
      )}
    >
      {eyebrow ? <p className="eyebrow pb-5">{eyebrow}</p> : null}
      <h2 className="display-tight text-section text-ink">{title}</h2>
      {body ? <p className="mt-6 text-lead text-ink-soft">{body}</p> : null}
    </Reveal>
  );
}

/** Content arrives as you reach it — once, and never on the way back up. */
function Reveal({
  children,
  className,
  delay = 0,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      initial={reduce ? { opacity: 0 } : { opacity: 0, y: 22 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: reduce ? 0.2 : 0.7, delay, ease: [0.16, 1, 0.3, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/* Hero                                                                */
/* ------------------------------------------------------------------ */

function Hero() {
  const reduce = useReducedMotion();

  return (
    <section className="relative overflow-hidden px-6 pb-20 pt-20 sm:px-8 sm:pb-28 sm:pt-28 lg:pb-36 lg:pt-36">
      <div className="mx-auto w-full max-w-[78rem]">
        <div className="mx-auto max-w-[56rem] text-center">
          <motion.p
            initial={reduce ? { opacity: 0 } : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="eyebrow"
          >
            For teams who read solicitations for a living
          </motion.p>

          <motion.h1
            initial={reduce ? { opacity: 0 } : { opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.06, ease: [0.16, 1, 0.3, 1] }}
            className="display-tight mt-8 text-hero text-ink [text-wrap:balance]"
          >
            The solicitation already told you whether to bid.
          </motion.h1>

          <motion.p
            initial={reduce ? { opacity: 0 } : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.14, ease: [0.16, 1, 0.3, 1] }}
            className="mx-auto mt-8 max-w-[34rem] text-lead text-ink-soft"
          >
            Somebody has to read all 214 pages. Margin does, and every finding it
            returns carries the page, the section, and the line it stands on.
          </motion.p>

          <motion.div
            initial={reduce ? { opacity: 0 } : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.22, ease: [0.16, 1, 0.3, 1] }}
            className="mt-11 flex flex-wrap items-center justify-center gap-3"
          >
            <Button asChild variant="primary" size="lg">
              <Link href="/signup">
                Read your first solicitation
                <ArrowRight />
              </Link>
            </Button>
            <Button asChild variant="ghost" size="lg">
              <Link href="#margin">See how a citation works</Link>
            </Button>
          </motion.div>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.34 }}
            className="mt-7 flex items-center justify-center gap-2 text-sm text-ink-faint"
          >
            <ShieldCheck className="size-4 shrink-0" aria-hidden />
            Documents are read in place. Citations stay; the file does not.
          </motion.p>
        </div>

        <motion.div
          initial={reduce ? { opacity: 0 } : { opacity: 0, y: 40, scale: 0.985 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 1, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="mt-20 sm:mt-24"
        >
          <DemoStrip />
          <p className="mt-5 text-center text-sm text-ink-faint">
            A real fragment of the workspace. Point at a finding — the clause lights beside it.
          </p>
        </motion.div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* Numbers                                                             */
/* ------------------------------------------------------------------ */

function Numbers() {
  return (
    <section className="border-y border-line bg-paper-raised px-6 py-16 sm:px-8 sm:py-20">
      <dl className="mx-auto grid w-full max-w-[78rem] gap-12 sm:grid-cols-3 sm:gap-8">
        {NUMBERS.map((item, i) => (
          <Reveal key={item.label} delay={i * 0.08} className="text-center sm:text-left">
            <dd className="font-display text-5xl leading-none text-ink tabular">{item.value}</dd>
            <dt className="mt-3 text-base leading-relaxed text-ink-soft">{item.label}</dt>
          </Reveal>
        ))}
      </dl>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* The Margin                                                          */
/* ------------------------------------------------------------------ */

function MarginSection() {
  return (
    <Band id="margin">
      <div className="grid gap-16 lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)] lg:gap-20">
        <div className="lg:sticky lg:top-28 lg:self-start">
          <Lede
            eyebrow="The idea"
            title={
              <>
                Scholars have argued in the margin for eight hundred years.
              </>
            }
            body="The margin is where the reader answers the text — where they say it back, and where the disagreement lives. Margin puts the source there, next to the claim, so checking a finding costs a glance instead of a search."
          />
          <Reveal delay={0.1}>
            <Link
              href="/signup"
              className="mt-8 inline-flex items-center gap-2 text-base text-patina underline-offset-4 transition-colors hover:underline"
            >
              Open the workspace
              <ArrowRight className="size-4" aria-hidden />
            </Link>
          </Reveal>
        </div>

        <Reveal delay={0.08} className="min-w-0">
          <ManuscriptDemo />
          <p className="mt-5 text-sm text-ink-faint">
            Move a citation. The source moves with it — page, section, and the exact line.
          </p>
        </Reveal>
      </div>
    </Band>
  );
}

/* ------------------------------------------------------------------ */
/* How it reads                                                        */
/* ------------------------------------------------------------------ */

function HowItReads() {
  return (
    <Band id="how" tone="raised" className="border-y border-line">
      <Lede
        align="center"
        eyebrow="How it reads a document"
        title="Eight readers, in order, each refusing to leave until its part is cited."
        body="No spinner, no progress bar pretending to be busy — a roster of readers taking the floor one at a time, their reasoning streaming as they work."
      />

      <div className="mt-20 grid gap-x-10 gap-y-12 sm:grid-cols-2 lg:grid-cols-4">
        {AGENTS.map((agent, i) => (
          <Reveal key={agent.id} delay={(i % 4) * 0.06} className="min-w-0">
            <div className="flex items-baseline gap-3 pb-3">
              <span className="font-mono text-2xs text-ink-faint tabular">
                {String(i + 1).padStart(2, "0")}
              </span>
              <h3 className="text-lg leading-snug text-ink">{agent.name}</h3>
            </div>
            <p className="text-sm leading-relaxed text-ink-soft">{agent.duty}</p>
            <p className="mt-4 border-l-2 border-line pl-4 font-mono text-xs leading-relaxed text-ink-faint">
              {agent.lines[0]}
            </p>
          </Reveal>
        ))}
      </div>

      <Reveal delay={0.1} className="mt-20 text-center">
        <p className="text-base text-ink-soft">
          A standard pass over 214 pages takes about four minutes.
        </p>
      </Reveal>
    </Band>
  );
}

/* ------------------------------------------------------------------ */
/* What you get back                                                   */
/* ------------------------------------------------------------------ */

function Artifacts() {
  return (
    <Band>
      <div className="grid gap-16 lg:grid-cols-[minmax(0,24rem)_minmax(0,1fr)] lg:gap-20">
        <div className="lg:sticky lg:top-28 lg:self-start">
          <Lede
            eyebrow="What you get back"
            title="Not a summary. A working surface."
            body="A summary is something you have to trust. Every artefact below is something you can hand to a person and they can work on it the same hour."
          />
        </div>

        <ul className="min-w-0">
          {ARTIFACTS.map((item, i) => (
            <Reveal key={item.index} delay={i * 0.05}>
              <li className="grid gap-x-8 gap-y-3 border-t border-line py-10 first:border-t-0 first:pt-0 sm:grid-cols-[3rem_minmax(0,1fr)]">
                <span className="font-mono text-2xs text-ink-faint tabular">{item.index}</span>
                <div className="min-w-0">
                  <h3 className="text-xl leading-snug text-ink">{item.title}</h3>
                  <p className="mt-3 text-base leading-relaxed text-ink-soft">{item.body}</p>
                </div>
              </li>
            </Reveal>
          ))}
        </ul>
      </div>
    </Band>
  );
}

/* ------------------------------------------------------------------ */
/* Evidence                                                            */
/* ------------------------------------------------------------------ */

function Proof() {
  return (
    <Band id="evidence" tone="sunk" className="border-y border-line">
      <Lede
        eyebrow="Evidence"
        title="The people who read these documents for a living."
      />

      <Reveal delay={0.06} className="mt-16">
        <figure className="max-w-[46rem]">
          <blockquote className="display-tight text-2xl leading-[1.35] text-ink sm:text-3xl">
            “{PROOF[0].quote}”
          </blockquote>
          <figcaption className="mt-8 text-sm text-ink-soft">
            <span className="font-medium text-ink">{PROOF[0].name}</span>
            <span className="mx-2 text-ink-faint" aria-hidden>
              ·
            </span>
            {PROOF[0].title}
          </figcaption>
        </figure>
      </Reveal>

      <div className="mt-20 grid gap-12 border-t border-line pt-16 sm:grid-cols-2 sm:gap-16">
        {PROOF.slice(1).map((item, i) => (
          <Reveal key={item.name} delay={i * 0.08}>
            <figure>
              <blockquote className="text-lg leading-relaxed text-ink-soft">“{item.quote}”</blockquote>
              <figcaption className="mt-5 text-sm text-ink-faint">
                <span className="font-medium text-ink">{item.name}</span>
                <span className="mx-2" aria-hidden>
                  ·
                </span>
                {item.title}
              </figcaption>
            </figure>
          </Reveal>
        ))}
      </div>
    </Band>
  );
}

/* ------------------------------------------------------------------ */
/* Pricing                                                             */
/* ------------------------------------------------------------------ */

function PricingPreview() {
  return (
    <Band id="pricing">
      <Lede
        align="center"
        eyebrow="Pricing"
        title="Priced per seat, because that is who does the reading."
      />
      <Reveal delay={0.08} className="mt-16">
        <PricingTable />
      </Reveal>
    </Band>
  );
}

/* ------------------------------------------------------------------ */
/* Final call                                                          */
/* ------------------------------------------------------------------ */

function FinalCta() {
  return (
    <section className="border-t border-line bg-paper-raised px-6 py-28 sm:px-8 sm:py-36 lg:py-44">
      <Reveal className="mx-auto max-w-[42rem] text-center">
        <h2 className="display-tight text-section text-ink">
          The next one is 214 pages and due in eleven days.
        </h2>
        <p className="mt-7 text-lead text-ink-soft">
          Give it to Margin and have the compliance matrix, the gates, and the
          questions before lunch.
        </p>
        <div className="mt-11 flex flex-wrap items-center justify-center gap-3">
          <Button asChild variant="primary" size="lg">
            <Link href="/signup">
              Start reading
              <ArrowRight />
            </Link>
          </Button>
          <Button asChild variant="ghost" size="lg">
            <Link href="/pricing">Look at pricing</Link>
          </Button>
        </div>
        <p className="mt-7 text-sm text-ink-faint">
          No card. A new workspace starts empty and fills with what Margin reads.
        </p>
      </Reveal>
    </section>
  );
}
