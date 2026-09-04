import type { Metadata } from "next";

import { DeadlinesView } from "@/components/views/deadlines";
import { ScrollPage } from "@/components/ui/page";

export const metadata: Metadata = {
  title: "Deadlines",
  description: "Every date the documents named, with time-zone aware countdowns.",
};

export default function DeadlinesPage() {
  return (
    <ScrollPage>
      <DeadlinesView />
    </ScrollPage>
  );
}
