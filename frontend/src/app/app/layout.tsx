import type { Metadata } from "next";

import { AppShell } from "@/components/shell/app-shell";
import { AuthGate } from "@/components/shell/auth-gate";

export const metadata: Metadata = {
  title: {
    default: "Workspace",
    template: "%s · Margin",
  },
};

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGate>
      <AppShell>{children}</AppShell>
    </AuthGate>
  );
}
