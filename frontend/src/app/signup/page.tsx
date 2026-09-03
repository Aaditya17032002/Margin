import type { Metadata } from "next";

import { SignupView } from "@/components/auth/signup";

export const metadata: Metadata = {
  title: "Create an account",
  description: "Start reading solicitations properly. Fourteen days, no card.",
};

export default function SignupPage() {
  return <SignupView />;
}
