import type { Metadata } from "next";

import { TemplatesView } from "@/components/views/templates";
import { ScrollPage } from "@/components/ui/page";

export const metadata: Metadata = {
  title: "Templates",
  description: "Report templates and the boilerplate library.",
};

export default function TemplatesPage() {
  return (
    <ScrollPage>
      <TemplatesView />
    </ScrollPage>
  );
}
