import type { Metadata } from "next";

import { TeamView } from "@/components/views/team";

export const metadata: Metadata = {
  title: "Team",
  description: "Members, roles, and invitations.",
};

export default function TeamPage() {
  return <TeamView />;
}
