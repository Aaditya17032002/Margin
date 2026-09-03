import type { Metadata } from "next";

import { MarketingFooter, MarketingHeader } from "@/components/marketing/chrome";
import { StyleGuideView } from "@/components/marketing/style-guide";

export const metadata: Metadata = {
  title: "Style",
  description: "The Margin design system — paper, ink, patina, and the primitives built from them.",
  robots: { index: false, follow: false },
};

export default function StylePage() {
  return (
    <div className="min-h-dvh bg-paper">
      <MarketingHeader />
      <main id="main">
        <StyleGuideView />
      </main>
      <MarketingFooter />
    </div>
  );
}
