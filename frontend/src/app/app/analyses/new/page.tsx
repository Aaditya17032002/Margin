import type { Metadata } from "next";

import { NewAnalysisView } from "@/components/views/new-analysis";
import { ScrollPage } from "@/components/ui/page";

export const metadata: Metadata = {
  title: "New analysis",
  description: "Upload or import a solicitation and choose how deeply Margin should read it.",
};

export default function NewAnalysisPage() {
  return (
    <ScrollPage>
      <NewAnalysisView />
    </ScrollPage>
  );
}
