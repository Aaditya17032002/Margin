import type { Metadata } from "next";

import { MarketingFooter, MarketingHeader } from "@/components/marketing/chrome";
import { LandingView } from "@/components/marketing/landing";

export const metadata: Metadata = {
  title: "Margin — read the solicitation properly",
  description:
    "Margin reads government solicitations the way a senior capture lead does, and every finding carries the page, section, and line it came from.",
};

export default function HomePage() {
  return (
    <div className="min-h-dvh bg-paper">
      <MarketingHeader />
      <main id="main">
        <LandingView />
      </main>
      <MarketingFooter />
    </div>
  );
}
