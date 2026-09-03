import type { Metadata } from "next";

import { ResetPasswordView } from "@/components/auth/recovery";

export const metadata: Metadata = {
  title: "Choose a new password",
  description: "Set a new password for your Margin account.",
};

export default function ResetPasswordPage() {
  return <ResetPasswordView />;
}
