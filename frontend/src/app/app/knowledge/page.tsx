import type { Metadata } from "next";

import { KnowledgeView } from "@/components/views/knowledge";

export const metadata: Metadata = {
  title: "Institutional memory",
  description: "Past bids, debriefs, and the lessons that should shape the next pursuit.",
};

export default function KnowledgePage() {
  return <KnowledgeView />;
}
