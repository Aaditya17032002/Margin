import type { Metadata } from "next";

import { TeamView } from "@/components/views/team";
import { ScrollPage } from "@/components/ui/page";

export const metadata: Metadata = {
  title: "Team",
  description: "Members, roles, and invitations.",
};

export default function TeamPage() {
  return (
    <ScrollPage>
      <TeamView />
    </ScrollPage>
  );
}
