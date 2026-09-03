import { Suspense } from "react";
import type { Metadata } from "next";

import { LoginView } from "@/components/auth/login";

export const metadata: Metadata = {
  title: "Sign in",
  description: "Sign in to Margin.",
};

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-dvh bg-paper" />}>
      <LoginView />
    </Suspense>
  );
}
