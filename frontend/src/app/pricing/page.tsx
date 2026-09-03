import type { Metadata } from "next";
import Link from "next/link";

import { MarketingFooter, MarketingHeader } from "@/components/marketing/chrome";
import { PricingTable } from "@/components/marketing/pricing-table";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/controls";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Pricing",
  description: "Per-seat pricing for teams who read solicitations for a living.",
};

const FAQ = [
  {
    q: "What counts as a document?",
    a: "One solicitation, however long it is, plus its attachments and every amendment issued against it. A 340-page RFP with nine attachments is one document, not ten.",
  },
  {
    q: "Can we change plans mid-year?",
    a: "Upward, at any time — the difference is prorated. Downward at renewal, so nobody loses access to an analysis in the middle of a live pursuit.",
  },
  {
    q: "Do you train on our solicitations?",
    a: "No. Documents are read in place and nothing from your tenant is used to train a model. Enterprise adds a private deployment if that needs to be contractual rather than a promise.",
  },
  {
    q: "What happens at the end of a trial?",
    a: "Nothing disappears. The workspace becomes read-only until a plan is chosen, so a pursuit that is mid-flight is never held hostage.",
  },
  {
    q: "Is there a minimum term?",
    a: "Monthly plans are month to month. Annual plans are twelve months and are the only ones that get the discount, because that is the only honest reason for a discount to exist.",
  },
];

export default function PricingPage() {
  return (
    <div className="min-h-dvh bg-paper">
      <MarketingHeader />
      <main id="main">
        <section className="border-b border-line py-16 lg:py-20">
          <div className="mx-auto max-w-[76rem] px-5 lg:px-8">
            <div className="max-w-2xl">
              <p className="eyebrow">Pricing</p>
              <h1 className="display-tight mt-3 text-4xl leading-tight text-ink sm:text-5xl">
                One price per person who reads.
              </h1>
              <p className="mt-5 text-lg leading-relaxed text-ink-soft">
                No per-page metering, no charge for the amendment that arrives the week before submission. The unit is
                a seat, because the thing being saved is somebody&rsquo;s afternoon.
              </p>
            </div>

            <PricingTable className="mt-12" />
          </div>
        </section>

        <section className="border-b border-line bg-paper-raised py-16 lg:py-20">
          <div className="mx-auto max-w-3xl px-5 lg:px-8">
            <h2 className="display-tight text-3xl text-ink">Questions before you commit</h2>
            <div className="mt-6">
              <Accordion type="single" collapsible>
                {FAQ.map((item) => (
                  <AccordionItem key={item.q} value={item.q}>
                    <AccordionTrigger>{item.q}</AccordionTrigger>
                    <AccordionContent>
                      <p className="pb-4 text-base leading-relaxed text-ink-soft">{item.a}</p>
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            </div>
          </div>
        </section>

        <section className="py-16 lg:py-20">
          <div className="mx-auto max-w-3xl px-5 text-center lg:px-8">
            <h2 className="display-tight text-3xl text-ink">Read one before you decide.</h2>
            <p className="mx-auto mt-4 max-w-lg text-base leading-relaxed text-ink-soft">
              Create a workspace and give Margin one solicitation. Every finding it returns points at the clause it
              came from, and you can check each one yourself.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <Button asChild variant="primary" size="lg">
                <Link href="/app">Open the workspace</Link>
              </Button>
              <Button asChild variant="secondary" size="lg">
                <Link href="/signup">Start a trial</Link>
              </Button>
            </div>
          </div>
        </section>
      </main>
      <MarketingFooter />
    </div>
  );
}
