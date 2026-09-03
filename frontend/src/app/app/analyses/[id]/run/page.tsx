import type { Metadata } from "next";

import { RunAnalysisView } from "@/components/views/run-analysis";

export const metadata: Metadata = {
  title: "Reading room",
  description: "Watch Margin read the solicitation, agent by agent.",
};

export default async function RunAnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <RunAnalysisView analysisId={id} />;
}
