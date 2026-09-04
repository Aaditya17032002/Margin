import type { Metadata } from "next";

import { ProfileView } from "@/components/views/profile";
import { ScrollPage } from "@/components/ui/page";

export const metadata: Metadata = {
  title: "Profile",
  description: "Your details, signature block, and current workload.",
};

export default function ProfilePage() {
  return (
    <ScrollPage>
      <ProfileView />
    </ScrollPage>
  );
}
