import type { Metadata } from "next";

import { IntegrationsView } from "@/components/views/integrations";

export const metadata: Metadata = {
  title: "Integrations",
  description: "Outlook, SharePoint, and OneDrive — read in place, export back.",
};

export default function IntegrationsPage() {
  return <IntegrationsView />;
}
