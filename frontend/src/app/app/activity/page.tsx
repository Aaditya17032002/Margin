import type { Metadata } from "next";

import { ActivityView } from "@/components/views/activity";
import { ScrollPage } from "@/components/ui/page";

export const metadata: Metadata = {
  title: "Activity",
  description: "The full audit trail, in the order it happened.",
};

export default function ActivityPage() {
  return (
    <ScrollPage>
      <ActivityView />
    </ScrollPage>
  );
}
