import type { Metadata } from "next";

import { DashboardView } from "@/components/views/dashboard";
import { ScrollPage } from "@/components/ui/page";

export const metadata: Metadata = {
  title: "Dashboard",
  description: "Where every bid stands today.",
};

export default function DashboardPage() {
  return (
    <ScrollPage>
      <DashboardView />
    </ScrollPage>
  );
}
