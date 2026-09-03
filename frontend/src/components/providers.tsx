"use client";

import * as React from "react";
import { MotionConfig } from "motion/react";

import { TooltipProvider } from "@/components/ui/overlay";
import { Toaster } from "@/components/ui/toaster";
import { rehydrateAll, useHydrationStore } from "@/stores";
import { usePrefsStore } from "@/stores/workspace";

/**
 * Persisted stores are rehydrated after mount rather than during store creation,
 * so the first client paint matches the server and localStorage still survives a
 * refresh. Appearance is applied to <html> from the same pass.
 */
export function Providers({ children }: { children: React.ReactNode }) {
  const hydrated = useHydrationStore((s) => s.hydrated);
  const appearance = usePrefsStore((s) => s.appearance);
  const reduceMotion = usePrefsStore((s) => s.reduceMotion);

  React.useEffect(() => {
    void rehydrateAll();
  }, []);

  React.useEffect(() => {
    if (!hydrated) return;
    document.documentElement.dataset.appearance = appearance;
  }, [appearance, hydrated]);

  React.useEffect(() => {
    if (!hydrated) return;
    document.documentElement.dataset.reduceMotion = reduceMotion ? "true" : "false";
  }, [reduceMotion, hydrated]);

  return (
    /*
     * Reduction is handled here rather than by branching `initial` props per
     * component: the media query is not knowable during the server pass, so any
     * component that branched on it would hydrate against different markup.
     * "user" keeps opacity but snaps transforms, which is the behaviour the
     * preference actually asks for.
     */
    <MotionConfig reducedMotion={reduceMotion ? "always" : "user"}>
      <TooltipProvider delayDuration={240} skipDelayDuration={420}>
        {children}
        <Toaster />
      </TooltipProvider>
    </MotionConfig>
  );
}
