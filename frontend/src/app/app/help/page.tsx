import type { Metadata } from "next";

import { HelpView } from "@/components/views/help";

export const metadata: Metadata = {
  title: "Help & shortcuts",
  description: "Guides, answers, and the full keyboard reference.",
};

export default function HelpPage() {
  return <HelpView />;
}
