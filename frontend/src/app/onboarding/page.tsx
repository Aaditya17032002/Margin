import type { Metadata } from "next";

import { OnboardingView } from "@/components/auth/onboarding";

export const metadata: Metadata = {
  title: "Set up your workspace",
  description: "Four short questions and Margin is ready to read.",
};

export default function OnboardingPage() {
  return <OnboardingView />;
}
