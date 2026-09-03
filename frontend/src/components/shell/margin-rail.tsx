"use client";

import * as React from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { Pin, PinOff, X } from "lucide-react";

import { cn } from "@/lib/utils";
import { railVariants } from "@/lib/motion";
import { Button } from "@/components/ui/button";
import { Tooltip } from "@/components/ui/overlay";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { SourceViewer } from "@/components/domain/source-viewer";
import { useAnalysesStore } from "@/stores/analyses";
import { usePrefsStore } from "@/stores/workspace";
import { useUIStore } from "@/stores/ui";

/**
 * The Margin. A rail that holds the source for whatever the eye is on, so
 * verifying a claim costs a glance instead of a navigation. Pinned, it stays;
 * unpinned, it follows attention and clears when attention leaves.
 */
export function MarginRail({ hint = false }: { hint?: boolean }) {
  const reduce = useReducedMotion();
  const { source, pinned, railOpen, setPinned, closeRail, setRailFocused } = useUIStore();
  const analyses = useAnalysesStore((s) => s.analyses);
  const railPinnedPref = usePrefsStore((s) => s.marginRailPinned);
  const setRailPinned = usePrefsStore((s) => s.setRailPinned);
  const railRef = React.useRef<HTMLElement>(null);
  const [isNarrow, setIsNarrow] = React.useState(false);

  React.useEffect(() => {
    const mq = window.matchMedia("(max-width: 1279px)");
    const sync = () => setIsNarrow(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);

  // → moves focus into the rail, Esc releases it. Verification without a mouse.
  React.useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const typing =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.isContentEditable;

      if (event.key === "ArrowRight" && !typing && source) {
        event.preventDefault();
        railRef.current?.focus();
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
  const open = railOpen && Boolean(source) && Boolean(analysis);

  const body =
    source && analysis ? (
      <>
        <div className="space-y-1">
          <p className="eyebrow">{source.origin ?? "Cited source"}</p>
          <h2 className="text-lg leading-snug text-ink">{source.label}</h2>
          <p className="truncate text-xs text-ink-faint">
            {analysis.solicitationNumber} · {analysis.agency}
          </p>
        </div>
        <SourceViewer analysis={analysis} citation={source.citation} className="mt-4" />
      </>
    ) : null;

  if (isNarrow) {
    return (
      <Sheet
        open={open}
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

  // On screens that hold findings the rail keeps its column even when empty, so
  // the page does not reflow the moment somebody points at a citation.
  if (!open && hint) return <MarginRailHint />;

  return (
    <AnimatePresence mode="wait">
      {open ? (
        <motion.aside
          ref={railRef}
          key="margin-rail"
          tabIndex={-1}
          aria-label="The Margin — cited source"
          variants={reduce ? undefined : railVariants}
          initial={reduce ? { opacity: 0 } : "hidden"}
          animate={reduce ? { opacity: 1 } : "visible"}
          exit={reduce ? { opacity: 0 } : "exit"}
          onFocus={() => setRailFocused(true)}
          onBlur={() => setRailFocused(false)}
          className={cn(
            "sticky top-14 hidden h-[calc(100dvh-3.5rem)] w-[24rem] shrink-0 border-l border-line bg-paper-raised xl:block",
            "focus-visible:outline-none",
          )}
        >
          <div className="flex h-full flex-col">
            <div className="flex items-center justify-between gap-2 border-b border-line px-4 py-2.5">
              <p className="font-mono text-2xs uppercase tracking-[0.14em] text-ink-faint">The Margin</p>
              <div className="flex items-center gap-0.5">
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
                <Tooltip content="Close the Margin" shortcut="Esc">
                  <Button variant="quiet" size="iconSm" aria-label="Close the Margin" onClick={closeRail}>
                    <X />
                  </Button>
                </Tooltip>
              </div>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">{body}</div>
          </div>
        </motion.aside>
      ) : null}
    </AnimatePresence>
  );
}

/** Shown when nothing is being pointed at, so the rail's purpose is discoverable. */
export function MarginRailHint() {
  return (
    <aside
      data-coach="rail"
      className="sticky top-14 hidden h-[calc(100dvh-3.5rem)] w-[24rem] shrink-0 border-l border-line bg-paper-raised xl:block"
    >
      <div className="flex h-full flex-col">
        <div className="border-b border-line px-4 py-2.5">
          <p className="font-mono text-2xs uppercase tracking-[0.14em] text-ink-faint">The Margin</p>
        </div>
        <div className="flex flex-1 flex-col justify-center gap-4 px-6 text-center">
          <svg viewBox="0 0 120 88" className="mx-auto h-24 w-auto" fill="none" aria-hidden>
            <rect x="6.5" y="8.5" width="60" height="71" rx="3" fill="var(--paper-sunk)" stroke="var(--line-strong)" />
            <path d="M18 8.5v71" stroke="color-mix(in oklab, var(--seal) 26%, transparent)" />
            <path d="M25 24h33M25 34h33M25 54h20" stroke="var(--line-strong)" strokeLinecap="round" />
            <rect x="24" y="40" width="35" height="7" rx="1.5" fill="var(--gold-highlight)" stroke="var(--gold-highlight-edge)" />
            <path d="M74 44h30" stroke="var(--patina)" strokeLinecap="round" strokeDasharray="3 4" />
            <path d="M99 39l5 5-5 5" stroke="var(--patina)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <div className="space-y-1.5">
            <p className="text-sm font-medium text-ink">Point at any finding</p>
            <p className="text-sm leading-relaxed text-ink-soft">
              The clause it came from arrives here, with the page and the exact line marked. Press{" "}
              <span className="font-mono text-xs">→</span> to move into the rail.
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
