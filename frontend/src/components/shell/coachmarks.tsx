"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";

import { Button } from "@/components/ui/button";
import { useHydrationStore } from "@/stores";
import { usePrefsStore } from "@/stores/workspace";
import { useSessionStore } from "@/stores/session";

const STEPS = [
  {
    id: "palette",
    kicker: "01",
    title: "Jump, don't hunt",
    body: "⌘K opens the palette. New analysis, a deadline, an export, a teammate — type the first few letters.",
  },
  {
    id: "rail",
    kicker: "02",
    title: "The Margin is the product",
    body: "Hover any citation and the clause arrives on the right, highlighted. → focuses the rail. Esc lets go.",
  },
  {
    id: "gauge",
    kicker: "03",
    title: "The gate tells the truth",
    body: "The go/no-go reading is the dashboard hero. A wax seal stamps if a hard gate is unmet. Decide from there.",
  },
] as const;

/**
 * A note left on the desk, not a modal tour. First visit to the dashboard only;
 * dismissed state persists. Settings → Appearance can put it back.
 */
export function Coachmarks() {
  const pathname = usePathname();
  const reduce = useReducedMotion();
  const hydrated = useHydrationStore((s) => s.hydrated);
  const onboarded = useSessionStore((s) => s.onboarded);
  const dismissed = usePrefsStore((s) => s.coachDismissed);
  const dismissCoach = usePrefsStore((s) => s.dismissCoach);
  const [step, setStep] = React.useState(0);
  // The note waits a beat before appearing so it reads as an aside rather than
  // as something the page threw at you. The timer is the only state the effect
  // sets — resetting on the way out is done by rendering nothing and letting
  // the timer be cleared, which avoids a synchronous setState in the body.
  const [armedFor, setArmedFor] = React.useState<string | null>(null);

  const eligible = hydrated && onboarded && !dismissed && pathname === "/app";
  const ready = eligible && armedFor === pathname;

  React.useEffect(() => {
    if (!eligible) return;
    const id = window.setTimeout(() => {
      setArmedFor(pathname);
      setStep(0);
    }, reduce ? 0 : 720);
    return () => window.clearTimeout(id);
  }, [eligible, reduce, pathname]);

  if (!ready) return null;

  const current = STEPS[step];
  const last = step === STEPS.length - 1;

  return (
    <AnimatePresence>
      <motion.aside
        role="dialog"
        aria-labelledby="coach-title"
        aria-describedby="coach-body"
        initial={reduce ? { opacity: 0 } : { opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        exit={reduce ? { opacity: 0 } : { opacity: 0, y: 8 }}
        transition={{ duration: 0.26, ease: [0.32, 0.72, 0, 1] }}
        className="fixed bottom-5 right-5 z-50 w-[min(22.5rem,calc(100vw-1.5rem))] rounded-lg border border-line bg-paper-raised p-5 shadow-[var(--shadow-float)]"
      >
        <p className="eyebrow">{current.kicker} of {String(STEPS.length).padStart(2, "0")}</p>
        <h2 id="coach-title" className="mt-2 font-display text-xl leading-snug text-ink">
          {current.title}
        </h2>
        <p id="coach-body" className="mt-2 text-sm leading-relaxed text-ink-soft">
          {current.body}
        </p>
        <div className="mt-4 flex items-center gap-2">
          <Button variant="quiet" size="sm" onClick={dismissCoach}>
            Skip
          </Button>
          <div className="ml-auto flex items-center gap-2">
            {step > 0 ? (
              <Button variant="ghost" size="sm" onClick={() => setStep((s) => s - 1)}>
                Back
              </Button>
            ) : null}
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                if (last) dismissCoach();
                else setStep((s) => s + 1);
              }}
            >
              {last ? "Start reading" : "Next"}
            </Button>
          </div>
        </div>
      </motion.aside>
    </AnimatePresence>
  );
}
