"use client";

import * as React from "react";
import Link from "next/link";
import { motion } from "motion/react";
import { Check, Minus } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Segmented } from "@/components/ui/controls";

interface Plan {
  id: string;
  name: string;
  tagline: string;
  monthly: number | null;
  annual: number | null;
  cta: string;
  href: string;
  featured?: boolean;
  includes: string[];
}

const PLANS: Plan[] = [
  {
    id: "solo",
    name: "Solo",
    tagline: "One capture lead, reading everything themselves.",
    monthly: 59,
    annual: 49,
    cta: "Start a trial",
    href: "/signup",
    includes: [
      "20 documents a month",
      "Standard and Quick Triage reads",
      "Compliance matrix and Q&A builder",
      "DOCX export",
      "Outlook, SharePoint, OneDrive",
    ],
  },
  {
    id: "practice",
    name: "Practice",
    tagline: "A capture team that shares the work and the deadline.",
    monthly: 49,
    annual: 40,
    cta: "Start a trial",
    href: "/signup",
    featured: true,
    includes: [
      "Unlimited documents",
      "Every read mode, including Deep Research",
      "Shared matrix with owners and review states",
      "Institutional memory and templates",
      "Amendment diffs and re-compete compare",
      "Audit trail and role-based access",
    ],
  },
  {
    id: "enterprise",
    name: "Enterprise",
    tagline: "Multiple business units, one compliance standard.",
    monthly: null,
    annual: null,
    cta: "Talk to us",
    href: "/signup",
    includes: [
      "Everything in Practice",
      "Microsoft Entra SSO and SCIM",
      "Retention and residency controls",
      "Private model deployment",
      "Named implementation lead",
    ],
  },
];

const MATRIX: { feature: string; solo: string | boolean; practice: string | boolean; enterprise: string | boolean }[] = [
  { feature: "Documents per month", solo: "20", practice: "Unlimited", enterprise: "Unlimited" },
  { feature: "Seats included", solo: "1", practice: "5 minimum", enterprise: "Custom" },
  { feature: "Quick Triage & Standard reads", solo: true, practice: true, enterprise: true },
  { feature: "Deep Research pass", solo: false, practice: true, enterprise: true },
  { feature: "Compliance matrix", solo: true, practice: true, enterprise: true },
  { feature: "Shared ownership & review states", solo: false, practice: true, enterprise: true },
  { feature: "SILENT ledger & Q&A builder", solo: true, practice: true, enterprise: true },
  { feature: "Amendment diff", solo: false, practice: true, enterprise: true },
  { feature: "Re-compete compare", solo: false, practice: true, enterprise: true },
  { feature: "Institutional memory", solo: false, practice: true, enterprise: true },
  { feature: "Report templates", solo: "2 built-in", practice: "Unlimited", enterprise: "Unlimited" },
  { feature: "Outlook / SharePoint / OneDrive", solo: true, practice: true, enterprise: true },
  { feature: "Audit trail", solo: false, practice: true, enterprise: true },
  { feature: "SSO & SCIM", solo: false, practice: false, enterprise: true },
  { feature: "Retention controls", solo: false, practice: false, enterprise: true },
  { feature: "Support", solo: "Email", practice: "Same-day", enterprise: "Named lead" },
];

export function PricingTable({ className, compact = false }: { className?: string; compact?: boolean }) {
  const [cycle, setCycle] = React.useState<"annual" | "monthly">("annual");

  return (
    <div className={className}>
      <div className="flex justify-center pb-10">
        <Segmented
          ariaLabel="Billing cycle"
          value={cycle}
          onValueChange={(v) => setCycle(v as "annual" | "monthly")}
          options={[
            { value: "annual", label: "Annual — save 18%" },
            { value: "monthly", label: "Monthly" },
          ]}
        />
      </div>

      <ul className="grid gap-6 lg:grid-cols-3">
        {PLANS.map((plan, index) => {
          const price = cycle === "annual" ? plan.annual : plan.monthly;
          return (
            <motion.li
              key={plan.id}
              initial={{ opacity: 0, y: 14 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ delay: index * 0.06, duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
              className={cn(
                "flex flex-col rounded-xl border bg-paper-raised p-7 lg:p-8",
                plan.featured
                  ? "border-patina shadow-[var(--shadow-float)] ring-1 ring-[color-mix(in_oklab,var(--patina)_18%,transparent)]"
                  : "border-line",
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <h3 className="font-display text-xl text-ink">{plan.name}</h3>
                {plan.featured ? <Badge tone="patina">Most chosen</Badge> : null}
              </div>
              <p className="mt-2 text-sm leading-relaxed text-ink-soft">{plan.tagline}</p>

              <div className="mt-8 flex items-baseline gap-1.5">
                {price === null ? (
                  <span className="display-tight font-display text-3xl text-ink">Let&rsquo;s talk</span>
                ) : (
                  <>
                    <span className="display-tight font-display text-4xl text-ink tabular">${price}</span>
                    <span className="text-sm text-ink-faint">/ seat / month</span>
                  </>
                )}
              </div>
              <p className="mt-1 h-4 text-xs text-ink-faint">
                {price !== null && cycle === "annual" ? "billed annually" : price !== null ? "billed monthly" : ""}
              </p>

              <Button
                asChild
                variant={plan.featured ? "primary" : "secondary"}
                size="md"
                className="mt-7 w-full"
              >
                <Link href={plan.href}>{plan.cta}</Link>
              </Button>

              <ul className="mt-8 space-y-3 border-t border-line pt-6">
                {plan.includes.map((item) => (
                  <li key={item} className="flex items-start gap-2.5 text-sm text-ink-soft">
                    <Check className="mt-0.5 size-3.5 shrink-0 text-patina" aria-hidden />
                    <span className="leading-relaxed">{item}</span>
                  </li>
                ))}
              </ul>
            </motion.li>
          );
        })}
      </ul>

      {compact ? (
        <p className="mt-8 text-center text-sm text-ink-soft">
          <Link href="/pricing" className="text-patina underline-offset-4 hover:underline">
            Compare every plan side by side
          </Link>
        </p>
      ) : (
        <ComparisonTable />
      )}
    </div>
  );
}

function ComparisonTable() {
  return (
    <div className="mt-16">
      <h3 className="display-tight text-2xl text-ink">Every difference, in one place</h3>
      {/* `relative` is load-bearing: the visually-hidden cell labels are
          absolutely positioned, and without a positioned scroll container they
          take the page as their containing block and escape the clip — which
          is enough to make the whole document scroll sideways on a phone. */}
      <div className="scrollbar-none relative mt-6 overflow-x-auto rounded-lg border border-line bg-paper-raised">
        <table className="w-full min-w-[42rem] border-collapse text-sm">
          <caption className="sr-only">Feature comparison across the three plans</caption>
          <thead>
            <tr className="border-b border-line">
              <th scope="col" className="px-5 py-3 text-left font-medium text-ink-faint">
                Feature
              </th>
              {PLANS.map((plan) => (
                <th
                  key={plan.id}
                  scope="col"
                  className={cn(
                    "px-5 py-3 text-left font-medium",
                    plan.featured ? "text-patina" : "text-ink",
                  )}
                >
                  {plan.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {MATRIX.map((row) => (
              <tr key={row.feature} className="border-b border-line last:border-b-0">
                <th scope="row" className="px-5 py-3 text-left font-normal text-ink-soft">
                  {row.feature}
                </th>
                <Cell value={row.solo} />
                <Cell value={row.practice} featured />
                <Cell value={row.enterprise} />
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Cell({ value, featured }: { value: string | boolean; featured?: boolean }) {
  return (
    <td className={cn("px-5 py-3", featured && "bg-patina-tint/40")}>
      {typeof value === "string" ? (
        <span className="text-ink">{value}</span>
      ) : value ? (
        <>
          <Check className="size-4 text-patina" aria-hidden />
          <span className="sr-only">Included</span>
        </>
      ) : (
        <>
          <Minus className="size-4 text-ink-faint/60" aria-hidden />
          <span className="sr-only">Not included</span>
        </>
      )}
    </td>
  );
}
