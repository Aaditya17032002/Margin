import type { Metadata } from "next";

import { NewAnalysisView } from "@/components/views/new-analysis";

export const metadata: Metadata = {
  title: "New analysis",
  description: "Upload or import a solicitation and choose how deeply Margin should read it.",
};

export default function NewAnalysisPage() {
  return <NewAnalysisView />;
}
