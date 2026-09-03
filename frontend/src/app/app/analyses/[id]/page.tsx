import { Suspense } from "react";
import type { Metadata } from "next";

import { WorkspaceView } from "@/components/views/workspace";
import { SkeletonPanel } from "@/components/ui/feedback";

export const metadata: Metadata = {
  title: "Analysis workspace",
  description: "Findings, compliance matrix, risks, and questions — each traceable to its clause.",
};

export default async function AnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <Suspense fallback={<WorkspaceSkeleton />}>
      <WorkspaceView analysisId={id} />
    </Suspense>
  );
}

function WorkspaceSkeleton() {
  return (
    <div className="mx-auto max-w-[76rem] space-y-6">
      <SkeletonPanel />
      <div className="grid gap-6 lg:grid-cols-[13.5rem_1fr]">
        <SkeletonPanel />
        <SkeletonPanel />
      </div>
    </div>
  );
}
