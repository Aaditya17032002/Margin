import type { Metadata } from "next";

import { TemplatesView } from "@/components/views/templates";

export const metadata: Metadata = {
  title: "Templates",
  description: "Report templates and the boilerplate library.",
};

export default function TemplatesPage() {
  return <TemplatesView />;
}
