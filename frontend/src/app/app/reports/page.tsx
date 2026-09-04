import type { Metadata } from "next";

import { ReportsView } from "@/components/views/reports";
import { ScrollPage } from "@/components/ui/page";

export const metadata: Metadata = {
  title: "Reports",
  description: "Generate DOCX reports and review the export history.",
};

export default function ReportsPage() {
  return (
    <ScrollPage>
      <ReportsView />
    </ScrollPage>
  );
}
