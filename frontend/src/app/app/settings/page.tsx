import { Suspense } from "react";
import type { Metadata } from "next";

import { SettingsView } from "@/components/views/settings";
import { SkeletonPanel } from "@/components/ui/feedback";

export const metadata: Metadata = {
  title: "Settings",
  description: "Account, organisation, appearance, and analysis defaults.",
};

export default function SettingsPage() {
  return (
    <Suspense fallback={<SkeletonPanel className="mx-auto max-w-[72rem]" />}>
      <SettingsView />
    </Suspense>
  );
}
