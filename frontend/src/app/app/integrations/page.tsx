import type { Metadata } from "next";

import { IntegrationsView } from "@/components/views/integrations";
import { ScrollPage } from "@/components/ui/page";

export const metadata: Metadata = {
  title: "Integrations",
  description: "Outlook, SharePoint, and OneDrive — read in place, export back.",
};

export default function IntegrationsPage() {
  return (
    <ScrollPage>
      <IntegrationsView />
    </ScrollPage>
  );
}
