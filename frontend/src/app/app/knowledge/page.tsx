import type { Metadata } from "next";

import { KnowledgeView } from "@/components/views/knowledge";
import { ScrollPage } from "@/components/ui/page";

export const metadata: Metadata = {
  title: "Institutional memory",
  description: "Past bids, debriefs, and the lessons that should shape the next pursuit.",
};

export default function KnowledgePage() {
  return (
    <ScrollPage>
      <KnowledgeView />
    </ScrollPage>
  );
}
