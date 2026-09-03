import type { Metadata } from "next";

import { AnalysesBoardView } from "@/components/views/analyses-board";

export const metadata: Metadata = {
  title: "Analyses",
  description: "Every solicitation in flight, by stage.",
};

export default function AnalysesPage() {
  return <AnalysesBoardView />;
}
