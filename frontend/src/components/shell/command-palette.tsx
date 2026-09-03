"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import {
  ArrowRight,
  CalendarClock,
  Clock3,
  Download,
  FileText,
  Moon,
  Plug,
  Plus,
  Search,
  Sun,
  Table2,
  Contrast,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Kbd } from "@/components/ui/surface";
import { notify } from "@/components/ui/toaster";
import { ALL_NAV } from "./navigation";
import { useAnalysesStore } from "@/stores/analyses";
import { useIntegrationsStore, usePrefsStore } from "@/stores/workspace";
import { useUIStore } from "@/stores/ui";
import { DocTypeBadge } from "@/components/domain/primitives";

export function CommandPalette() {
  const router = useRouter();
  const open = useUIStore((s) => s.commandOpen);
  const setOpen = useUIStore((s) => s.setCommandOpen);
  const setShortcutsOpen = useUIStore((s) => s.setShortcutsOpen);
  const setImportOpen = useUIStore((s) => s.setImportOpen);
  const recent = useUIStore((s) => s.recentCommands);
  const remember = useUIStore((s) => s.rememberCommand);
  const analyses = useAnalysesStore((s) => s.analyses);
  const setAppearance = usePrefsStore((s) => s.setAppearance);
  const connect = useIntegrationsStore((s) => s.connect);
  const [query, setQuery] = React.useState("");

  React.useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key.toLowerCase() === "k" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        setOpen(!useUIStore.getState().commandOpen);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setOpen]);

  const run = React.useCallback(
    (id: string, action: () => void) => {
      remember(id);
      setOpen(false);
      setQuery("");
      // Let the palette finish closing before the route or overlay changes.
      window.setTimeout(action, 40);
    },
    [remember, setOpen],
  );

  const actions = React.useMemo(
    () => [
      {
        id: "new-analysis",
        label: "New analysis",
        hint: "Upload or import a solicitation",
        icon: Plus,
        run: () => router.push("/app/analyses/new"),
      },
      {
        id: "import",
        label: "Import from SharePoint or OneDrive",
        hint: "Browse the connected file tree",
        icon: Plug,
        run: () => setImportOpen(true),
      },
      {
        id: "deadlines",
        label: "Jump to the next deadline",
        hint: "Calendar and countdowns",
        icon: CalendarClock,
        run: () => router.push("/app/deadlines"),
      },
      {
        id: "matrix",
        label: "Go to the compliance matrix",
        icon: Table2,
        run: () => router.push("/app/matrix"),
      },
      {
        id: "export",
        label: "Export a report",
        hint: "DOCX from any template",
        icon: Download,
        run: () => router.push("/app/reports"),
      },
      {
        id: "connect-sharepoint",
        label: "Connect SharePoint",
        icon: Plug,
        run: () => {
          connect("sharepoint");
          notify.success("SharePoint connected.", { description: "Capture Library is available in the import picker." });
        },
      },
      {
        id: "shortcuts",
        label: "Show keyboard shortcuts",
        icon: Search,
        run: () => setShortcutsOpen(true),
      },
    ],
    [connect, router, setImportOpen, setShortcutsOpen],
  );

  const appearances = [
    { id: "paper", label: "Paper", icon: Sun },
    { id: "dusk", label: "Dusk", icon: Moon },
    { id: "contrast", label: "High contrast", icon: Contrast },
  ] as const;

  const recentActions = recent
    .map((id) => actions.find((a) => a.id === id))
    .filter((a): a is (typeof actions)[number] => Boolean(a));

  return (
    <DialogPrimitive.Root open={open} onOpenChange={setOpen}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-[color-mix(in_oklab,var(--ink)_36%,transparent)] backdrop-blur-[2px] data-[state=open]:animate-[fade_160ms_var(--ease-editorial)_both]" />
        <DialogPrimitive.Content
          className={cn(
            "fixed left-1/2 top-[12vh] z-50 w-[min(40rem,calc(100vw-2rem))] -translate-x-1/2",
            "overflow-hidden rounded-xl border border-line bg-paper-raised shadow-[var(--shadow-overlay)]",
            "data-[state=open]:animate-[rise_220ms_var(--ease-editorial)_both]",
          )}
        >
          <DialogPrimitive.Title className="sr-only">Command palette</DialogPrimitive.Title>
          <DialogPrimitive.Description className="sr-only">
            Search analyses, jump to a page, or run an action.
          </DialogPrimitive.Description>

          <Command
            loop
            filter={(value, search) => {
              if (!search) return 1;
              return value.toLowerCase().includes(search.toLowerCase()) ? 1 : 0;
            }}
          >
            <div className="flex items-center gap-3 border-b border-line px-4">
              <Search className="size-4 shrink-0 text-ink-faint" aria-hidden />
              <Command.Input
                value={query}
                onValueChange={setQuery}
                placeholder="Search analyses, jump to a page, run an action…"
                className="h-12 w-full bg-transparent text-base outline-none placeholder:text-ink-faint"
              />
              <Kbd>esc</Kbd>
            </div>

            <Command.List className="max-h-[52vh] overflow-y-auto p-2">
              <Command.Empty className="px-3 py-10 text-center text-sm text-ink-faint">
                Nothing matched “{query}”. Try a solicitation number or an agency.
              </Command.Empty>

              {!query && recentActions.length > 0 ? (
                <Group heading="Recent">
                  {recentActions.map((action) => (
                    <Item key={action.id} value={`recent ${action.label}`} onSelect={() => run(action.id, action.run)}>
                      <Clock3 className="size-4 text-ink-faint" aria-hidden />
                      {action.label}
                    </Item>
                  ))}
                </Group>
              ) : null}

              <Group heading="Actions">
                {actions.map((action) => (
                  <Item key={action.id} value={`${action.label} ${action.hint ?? ""}`} onSelect={() => run(action.id, action.run)}>
                    <action.icon className="size-4 text-ink-faint" aria-hidden />
                    <span className="flex-1">{action.label}</span>
                    {action.hint ? <span className="text-xs text-ink-faint">{action.hint}</span> : null}
                  </Item>
                ))}
              </Group>

              <Group heading="Analyses">
                {analyses.map((analysis) => (
                  <Item
                    key={analysis.id}
                    value={`${analysis.title} ${analysis.solicitationNumber} ${analysis.agency}`}
                    onSelect={() => run(`analysis-${analysis.id}`, () => router.push(`/app/analyses/${analysis.id}`))}
                  >
                    <FileText className="size-4 shrink-0 text-ink-faint" aria-hidden />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate">{analysis.title}</span>
                      <span className="block truncate font-mono text-2xs text-ink-faint">
                        {analysis.solicitationNumber} · {analysis.agency}
                      </span>
                    </span>
                    <DocTypeBadge docType={analysis.docType} />
                  </Item>
                ))}
              </Group>

              <Group heading="Go to">
                {ALL_NAV.map((item) => (
                  <Item
                    key={item.href}
                    value={`${item.label} ${item.description}`}
                    onSelect={() => run(`nav-${item.href}`, () => router.push(item.href))}
                  >
                    <item.icon className="size-4 text-ink-faint" aria-hidden />
                    <span className="flex-1">{item.label}</span>
                    <ArrowRight className="size-3.5 text-ink-faint/70" aria-hidden />
                  </Item>
                ))}
              </Group>

              <Group heading="Appearance">
                {appearances.map((option) => (
                  <Item
                    key={option.id}
                    value={`appearance ${option.label}`}
                    onSelect={() =>
                      run(`appearance-${option.id}`, () => {
                        setAppearance(option.id);
                        notify.success(`Appearance set to ${option.label}.`);
                      })
                    }
                  >
                    <option.icon className="size-4 text-ink-faint" aria-hidden />
                    {option.label}
                  </Item>
                ))}
              </Group>
            </Command.List>
          </Command>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

function Group({ heading, children }: { heading: string; children: React.ReactNode }) {
  return (
    <Command.Group
      heading={heading}
      className="[&_[cmdk-group-heading]]:px-2.5 [&_[cmdk-group-heading]]:pb-1 [&_[cmdk-group-heading]]:pt-3 [&_[cmdk-group-heading]]:font-mono [&_[cmdk-group-heading]]:text-2xs [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.13em] [&_[cmdk-group-heading]]:text-[var(--ink-faint)]"
    >
      {children}
    </Command.Group>
  );
}

function Item({
  value,
  onSelect,
  children,
}: {
  value: string;
  onSelect: () => void;
  children: React.ReactNode;
}) {
  return (
    <Command.Item
      value={value}
      onSelect={onSelect}
      className={cn(
        "flex cursor-default select-none items-center gap-3 rounded-md px-2.5 py-2 text-sm text-ink-soft",
        "transition-colors duration-100",
        "data-[selected=true]:bg-paper-sunk data-[selected=true]:text-ink",
      )}
    >
      {children}
    </Command.Item>
  );
}
