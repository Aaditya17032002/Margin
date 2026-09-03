import type { Metadata } from "next";

import { ForgotPasswordView } from "@/components/auth/recovery";

export const metadata: Metadata = {
  title: "Account recovery",
  description: "Send yourself a link to reset your Margin password.",
};

export default function ForgotPasswordPage() {
  return <ForgotPasswordView />;
}
