import { Suspense } from "react";
import type { Metadata } from "next";

import { SearchView } from "@/components/views/search";
import { SkeletonPanel } from "@/components/ui/feedback";

export const metadata: Metadata = {
  title: "Search",
  description: "Search analyses, findings, and extracted requirements.",
};

export default function SearchPage() {
  return (
    <Suspense fallback={<SkeletonPanel className="mx-auto max-w-4xl" />}>
      <SearchView />
    </Suspense>
  );
}
