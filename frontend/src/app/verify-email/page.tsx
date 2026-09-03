import type { Metadata } from "next";

import { VerifyEmailView } from "@/components/auth/recovery";

export const metadata: Metadata = {
  title: "Email confirmed",
  description: "Your Margin workspace is ready.",
};

export default function VerifyEmailPage() {
  return <VerifyEmailView />;
}
