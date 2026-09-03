import {
  Activity,
  BookMarked,
  CalendarClock,
  FileStack,
  FileText,
  Gauge,
  HelpCircle,
  LayoutGrid,
  LifeBuoy,
  Plug,
  Settings,
  Table2,
  Users,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: typeof Gauge;
  description: string;
  exact?: boolean;
}

export const PRIMARY_NAV: { group: string; items: NavItem[] }[] = [
  {
    group: "Capture",
    items: [
      { href: "/app", label: "Dashboard", icon: Gauge, description: "Where every bid stands today", exact: true },
      { href: "/app/analyses", label: "Analyses", icon: LayoutGrid, description: "Every solicitation in flight" },
      { href: "/app/deadlines", label: "Deadlines", icon: CalendarClock, description: "Calendar and countdowns" },
      { href: "/app/matrix", label: "Compliance matrix", icon: Table2, description: "Requirements across all bids" },
    ],
  },
  {
    group: "Library",
    items: [
      { href: "/app/knowledge", label: "Institutional memory", icon: BookMarked, description: "Past bids, debriefs, lessons" },
      { href: "/app/templates", label: "Templates", icon: FileStack, description: "Report and boilerplate library" },
      { href: "/app/reports", label: "Reports", icon: FileText, description: "Generate and download exports" },
    ],
  },
  {
    group: "Workspace",
    items: [
      { href: "/app/integrations", label: "Integrations", icon: Plug, description: "Outlook, SharePoint, OneDrive" },
      { href: "/app/team", label: "Team", icon: Users, description: "Members, roles, invitations" },
      { href: "/app/activity", label: "Activity", icon: Activity, description: "Full audit trail" },
    ],
  },
];

export const SECONDARY_NAV: NavItem[] = [
  { href: "/app/settings", label: "Settings", icon: Settings, description: "Account and organisation" },
  { href: "/app/help", label: "Help & shortcuts", icon: HelpCircle, description: "Docs and keyboard reference" },
];

export const ALL_NAV = [...PRIMARY_NAV.flatMap((g) => g.items), ...SECONDARY_NAV];

export const HELP_ICON = LifeBuoy;
