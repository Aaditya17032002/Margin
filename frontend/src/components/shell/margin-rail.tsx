"use client";

import * as React from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { Pin, PinOff, X } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Tooltip } from "@/components/ui/overlay";
import { Pane, PaneTitle } from "@/components/ui/page";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { SourceViewer } from "@/components/domain/source-viewer";
import { useAnalysesStore } from "@/stores/analyses";
import { usePrefsStore } from "@/stores/workspace";
import { useUIStore } from "@/stores/ui";

/**
 * The Margin.
 *
 * A column that holds the source for whatever the eye is on, so checking a
 * claim costs a glance rather than a navigation. It is a permanent pane, not a
 * popover: the column is always there, and what changes is whether it is
 * holding a clause or telling you how to fill it. Nothing on screen moves when
 * a citation is pointed at — only the contents of this column change.
 */
export function MarginPane() {
  const reduce = useReducedMotion();
  const { source, pinned, setPinned, closeRail, setRailFocused } = useUIStore();
  const analyses = useAnalysesStore((s) => s.analyses);
  const railPinnedPref = usePrefsStore((s) => s.marginRailPinned);
  const setRailPinned = usePrefsStore((s) => s.setRailPinned);
  const paneRef = React.useRef<HTMLDivElement>(null);

  // → moves focus into the Margin, Esc releases it. Verification without a mouse.
  React.useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const typing =
        target?.tagName === "INPUT" || target?.tagName === "TEXTAREA" || target?.isContentEditable;

      if (event.key === "ArrowRight" && !typing && source) {
        event.preventDefault();
        paneRef.current?.focus();
        setRailFocused(true);
      }
      if (event.key === "Escape" && !typing) {
        const state = useUIStore.getState();
        if (state.pinned) {
          setPinned(false);
          setRailPinned(false);
        } else if (state.railOpen) {
          closeRail();
        }
        setRailFocused(false);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [source, setPinned, setRailFocused, setRailPinned, closeRail]);

  const analysis = source ? analyses.find((a) => a.id === source.analysisId) : undefined;
  const showing = Boolean(source && analysis);

  return (
    <div
      ref={paneRef}
      tabIndex={-1}
      aria-label="The Margin — cited source"
      onFocus={() => setRailFocused(true)}
      onBlur={() => setRailFocused(false)}
      className="flex min-h-0 flex-1 flex-col bg-paper-raised focus-visible:outline-none"
    >
      <Pane
        header={
          <PaneTitle
            actions={
              showing ? (
                <>
                  <Tooltip content={pinned ? "Unpin — follow attention again" : "Pin this source open"} shortcut="P">
                    <Button
                      variant="quiet"
                      size="iconSm"
                      aria-pressed={pinned}
                      aria-label={pinned ? "Unpin source" : "Pin source"}
                      onClick={() => {
                        setPinned(!pinned);
                        setRailPinned(!railPinnedPref);
                      }}
                      className={cn(pinned && "text-patina")}
                    >
                      {pinned ? <PinOff /> : <Pin />}
                    </Button>
                  </Tooltip>
                  <Tooltip content="Clear the Margin" shortcut="Esc">
                    <Button variant="quiet" size="iconSm" aria-label="Clear the Margin" onClick={closeRail}>
                      <X />
                    </Button>
                  </Tooltip>
                </>
              ) : null
            }
          >
            The Margin
          </PaneTitle>
        }
        bodyClassName="px-4 py-4"
      >
        <AnimatePresence mode="wait" initial={false}>
          {source && analysis ? (
            <motion.div
              key={source.citation.id}
              initial={reduce ? { opacity: 0 } : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduce ? { opacity: 0 } : { opacity: 0, y: -6 }}
              transition={{ duration: 0.22, ease: [0.32, 0.72, 0, 1] }}
              className="space-y-4"
            >
              <div className="space-y-1.5">
                <p className="eyebrow">{source.origin ?? "Cited source"}</p>
                <h2 className="text-lg leading-snug text-ink">{source.label}</h2>
                <p className="truncate text-xs text-ink-faint">
                  {analysis.solicitationNumber} · {analysis.agency}
                </p>
              </div>
              <SourceViewer analysis={analysis} citation={source.citation} />
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              initial={reduce ? { opacity: 0 } : { opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <MarginEmpty />
            </motion.div>
          )}
        </AnimatePresence>
      </Pane>
    </div>
  );
}

/** Below the split breakpoint the Margin arrives as a sheet instead. */
export function MarginSheet() {
  const { source, railOpen, closeRail } = useUIStore();
  const analyses = useAnalysesStore((s) => s.analyses);
  const [isNarrow, setIsNarrow] = React.useState(false);

  React.useEffect(() => {
    const mq = window.matchMedia("(max-width: 1279px)");
    const sync = () => setIsNarrow(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);

  const analysis = source ? analyses.find((a) => a.id === source.analysisId) : undefined;

  return (
    <Sheet
      open={isNarrow && railOpen && Boolean(source && analysis)}
      onOpenChange={(next) => {
        if (!next) closeRail();
      }}
    >
      <SheetContent direction="bottom" title={source?.label ?? "Source"} description={analysis?.solicitationNumber}>
        {source && analysis ? <SourceViewer analysis={analysis} citation={source.citation} /> : null}
      </SheetContent>
    </Sheet>
  );
}

/** Shown when nothing is being pointed at, so the column's purpose is legible. */
function MarginEmpty() {
  return (
    <div data-coach="rail" className="flex h-full flex-col justify-center gap-5 py-10 text-center">
      <svg viewBox="0 0 120 88" className="mx-auto h-24 w-auto" fill="none" aria-hidden>
        <rect x="6.5" y="8.5" width="60" height="71" rx="3" fill="var(--paper-sunk)" stroke="var(--line-strong)" />
        <path d="M18 8.5v71" stroke="color-mix(in oklab, var(--seal) 26%, transparent)" />
        <path d="M25 24h33M25 34h33M25 54h20" stroke="var(--line-strong)" strokeLinecap="round" />
        <rect
          x="24"
          y="40"
          width="35"
          height="7"
          rx="1.5"
          fill="var(--gold-highlight)"
          stroke="var(--gold-highlight-edge)"
        />
        <path d="M74 44h30" stroke="var(--patina)" strokeLinecap="round" strokeDasharray="3 4" />
        <path d="M99 39l5 5-5 5" stroke="var(--patina)" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <div className="space-y-2 px-2">
        <p className="text-sm font-medium text-ink">Point at any finding</p>
        <p className="text-sm leading-relaxed text-ink-soft">
          The clause it came from arrives here, with the page and the exact line marked. Press{" "}
          <span className="font-mono text-xs">→</span> to move into the Margin.
        </p>
      </div>
    </div>
  );
}
