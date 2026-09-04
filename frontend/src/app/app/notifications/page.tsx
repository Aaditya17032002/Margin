import type { Metadata } from "next";

import { NotificationsView } from "@/components/views/notifications";
import { ScrollPage } from "@/components/ui/page";

export const metadata: Metadata = {
  title: "Notifications",
  description: "Deadlines, review flags, mentions, and amendments.",
};

export default function NotificationsPage() {
  return (
    <ScrollPage>
      <NotificationsView />
    </ScrollPage>
  );
}
