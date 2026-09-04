import { Suspense } from "react";
import type { Metadata } from "next";

import { ManualView } from "@/components/views/manual";
import { ScrollPage } from "@/components/ui/page";
import { SkeletonPanel } from "@/components/ui/feedback";

export const metadata: Metadata = {
  title: "Manual",
  description:
    "How Margin reads a solicitation, what every status means, and what each feature deliberately leaves to you.",
};

export default function ManualPage() {
  return (
    <ScrollPage>
      <Suspense fallback={<SkeletonPanel className="mx-auto max-w-[76rem]" />}>
        <ManualView />
      </Suspense>
    </ScrollPage>
  );
}
