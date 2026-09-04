"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Plug } from "lucide-react";

import { ApiError, integrationsApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Segmented } from "@/components/ui/controls";
import { EmptyState } from "@/components/ui/feedback";
import { notify } from "@/components/ui/toaster";
import { SourceBrowser } from "./source-browser";
import { useIntegrationsStore } from "@/stores/workspace";
import { useAnalysesStore } from "@/stores/analyses";
import { usePrefsStore } from "@/stores/workspace";
import { useUIStore } from "@/stores/ui";
import type { IntegrationId, RemoteEntry } from "@/types";

/**
 * Picking a solicitation out of a connected source.
 *
 * The import is a real one: the server fetches the bytes from Microsoft,
 * stores the extracted text, and queues the read. What this used to do was
 * create an analysis with only a filename on it, so the run had nothing to
 * read and every finding came back empty.
 */
export function ImportPicker() {
  const open = useUIStore((s) => s.importOpen);
  const setOpen = useUIStore((s) => s.setImportOpen);
  const integrations = useIntegrationsStore((s) => s.integrations);
  const loadAnalyses = useAnalysesStore((s) => s.load);
  const defaultMode = usePrefsStore((s) => s.defaultMode);
  const router = useRouter();

  const requested = useUIStore((s) => s.importSource);
  const [chosen, setChosen] = React.useState<IntegrationId | null>(null);
  const [busyId, setBusyId] = React.useState<string | null>(null);

  // Until someone picks a tab, land on a source that can actually be browsed.
  // Derived rather than corrected by an effect, so the first paint is right.
  const sourceId: IntegrationId =
    chosen ?? requested ?? integrations.find((i) => i.connected)?.id ?? "sharepoint";
  const source = integrations.find((i) => i.id === sourceId);

  function close() {
    setChosen(null);
    setOpen(false);
  }

  async function importEntry(entry: RemoteEntry) {
    setBusyId(entry.id);
    try {
      const result = await integrationsApi.import(sourceId, [entry.id]);
      const first = result.results.find((r) => r.analysisId);
      if (!first?.analysisId) {
        const reason = result.results.find((r) => r.error)?.error;
        notify.error("That document could not be imported.", { description: reason });
        return;
      }
      close();
      await loadAnalyses({ force: true });
      notify.success("Reading started.", {
        description: `${entry.name} · ${defaultMode.replace("-", " ")} pass`,
      });
      router.push(`/app/analyses/${first.analysisId}/run`);
    } catch (caught) {
      notify.error("That document could not be imported.", {
        description: caught instanceof ApiError ? caught.message : "Microsoft did not answer.",
      });
    } finally {
      setBusyId(null);
    }
  }

  return (
    <Sheet open={open} onOpenChange={(next) => (next ? setOpen(true) : close())}>
      <SheetContent
        title="Import a solicitation"
        description="Browse a connected source and start the read without downloading anything."
      >
        <div className="flex min-h-0 flex-1 flex-col gap-4">
          <Segmented
            ariaLabel="Import source"
            value={sourceId}
            onValueChange={(v) => setChosen(v as IntegrationId)}
            options={integrations.map((i) => ({ value: i.id, label: i.name }))}
            className="shrink-0"
          />

          {!source ? null : !source.connected ? (
            <EmptyState
              title={`${source.name} isn't connected`}
              description={source.blurb}
              action={
                <Button
                  variant="primary"
                  onClick={() => {
                    close();
                    router.push("/app/integrations");
                  }}
                >
                  <Plug />
                  Connect {source.name}
                </Button>
              }
            />
          ) : (
            <>
              {source.account ? (
                <p className="shrink-0 font-mono text-2xs uppercase tracking-[0.13em] text-ink-faint">
                  {source.account}
                </p>
              ) : null}
              <SourceBrowser
                // Remounting on a source change resets the walk without an
                // effect reaching in to clear it.
                key={source.id}
                provider={source.id}
                onPick={(entry) => void importEntry(entry)}
                busyId={busyId}
                className="min-h-0 flex-1"
              />
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
