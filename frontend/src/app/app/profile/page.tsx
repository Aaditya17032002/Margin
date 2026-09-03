import type { Metadata } from "next";

import { ProfileView } from "@/components/views/profile";

export const metadata: Metadata = {
  title: "Profile",
  description: "Your details, signature block, and current workload.",
};

export default function ProfilePage() {
  return <ProfileView />;
}
