"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { ArrowLeft, ArrowRight, Check, CloudUpload, Contrast, FolderTree, Mail, Moon, Sun } from "lucide-react";

import { cn } from "@/lib/utils";
import { MODES } from "@/data/agents";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Segmented } from "@/components/ui/controls";
import { StepRail } from "@/components/ui/feedback";
import { notify } from "@/components/ui/toaster";
import { Wordmark, WaxSeal } from "@/components/domain/marks";
import { useSessionStore } from "@/stores/session";
import { useIntegrationsStore, usePrefsStore } from "@/stores/workspace";
import type { Appearance, IntegrationId } from "@/types";

const STEPS = [
  { id: "org", label: "Your organisation", hint: "So reports carry the right name" },
  { id: "appearance", label: "How it should look", hint: "Paper, dusk, or high contrast" },
  { id: "connect", label: "Where documents live", hint: "Outlook, SharePoint, OneDrive" },
  { id: "mode", label: "How deeply to read", hint: "The default for new analyses" },
  { id: "done", label: "Ready", hint: "" },
];

const APPEARANCES: { value: Appearance; label: string; icon: typeof Sun; hint: string }[] = [
  { value: "paper", label: "Paper", icon: Sun, hint: "Warm daylight stock" },
  { value: "dusk", label: "Dusk", icon: Moon, hint: "Low light, same ink" },
  { value: "contrast", label: "Contrast", icon: Contrast, hint: "Maximum legibility" },
];

const INTEGRATION_ICON: Record<IntegrationId, typeof Mail> = {
  outlook: Mail,
  sharepoint: FolderTree,
  onedrive: CloudUpload,
};

const SIZES = ["1–10 people", "11–50 people", "51–250 people", "250+ people"];

export function OnboardingView() {
  const router = useRouter();
  const reduce = useReducedMotion();
  const org = useSessionStore((s) => s.org);
  const user = useSessionStore((s) => s.user);
  const updateOrg = useSessionStore((s) => s.updateOrg);
  const completeOnboarding = useSessionStore((s) => s.completeOnboarding);
  const appearance = usePrefsStore((s) => s.appearance);
  const setAppearance = usePrefsStore((s) => s.setAppearance);
  const density = usePrefsStore((s) => s.density);
  const setDensity = usePrefsStore((s) => s.setDensity);
  const defaultMode = usePrefsStore((s) => s.defaultMode);
  const setDefaultMode = usePrefsStore((s) => s.setDefaultMode);
  const integrations = useIntegrationsStore((s) => s.integrations);
  const connect = useIntegrationsStore((s) => s.connect);
  const disconnect = useIntegrationsStore((s) => s.disconnect);

  const [step, setStep] = React.useState(0);
  const [size, setSize] = React.useState(SIZES[2]);
  const [orgName, setOrgName] = React.useState(org?.name ?? "");
  const [cage, setCage] = React.useState(org?.cage ?? "");
  const [connecting, setConnecting] = React.useState<IntegrationId | null>(null);

  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;

  function next() {
    if (step === 0 && orgName.trim()) updateOrg({ name: orgName.trim(), cage: cage.trim() });
    setStep((s) => Math.min(STEPS.length - 1, s + 1));
  }

  function finish() {
    completeOnboarding();
    notify.success("You're set up.", { description: "Upload a solicitation and Margin starts reading." });
    router.push("/app");
  }

  async function toggleIntegration(id: IntegrationId, connected: boolean) {
    if (connected) {
      disconnect(id);
      return;
    }
    setConnecting(id);
    await new Promise((r) => setTimeout(r, 780));
    connect(id, user?.email);
    setConnecting(null);
  }

  return (
    <div className="grid min-h-dvh bg-paper lg:grid-cols-[20rem_1fr]">
      <aside className="border-b border-line bg-paper-raised px-6 py-8 lg:border-b-0 lg:border-r lg:px-8 lg:py-10">
        <Link href="/" className="inline-flex rounded-sm" aria-label="Margin, home">
          <Wordmark />
        </Link>
        <p className="eyebrow mt-8 pb-4">Setting up</p>
        <StepRail steps={STEPS} current={step} />
        <p className="mt-8 max-w-56 text-xs leading-relaxed text-ink-faint">
          Everything here can be changed later in settings. Nothing is permanent except the reading.
        </p>
      </aside>

      <main id="main" className="flex flex-col px-5 py-8 sm:px-10 lg:px-16 lg:py-14">
        <div className="flex flex-1 items-center">
          <div className="w-full max-w-2xl">
            <AnimatePresence mode="wait">
              <motion.div
                key={current.id}
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.28, ease: [0.32, 0.72, 0, 1] }}
              >
                {current.id === "org" ? (
                  <section aria-labelledby="step-heading">
                    <p className="eyebrow">Step one</p>
                    <h1 id="step-heading" className="display-tight mt-2 text-3xl text-ink">
                      Who is doing the bidding?
                    </h1>
                    <p className="mt-3 max-w-lg text-base leading-relaxed text-ink-soft">
                      This name goes on every exported report and every question set that reaches an agency.
                    </p>

                    <div className="mt-8 grid max-w-lg gap-4 sm:grid-cols-2">
                      <Field label="Organisation name" htmlFor="ob-org" required className="sm:col-span-2">
                        <Input
                          id="ob-org"
                          value={orgName}
                          onChange={(e) => setOrgName(e.target.value)}
                          placeholder="Thornfield & Co"
                          autoFocus
                        />
                      </Field>
                      <Field label="CAGE code" htmlFor="ob-cage" hint="Optional">
                        <Input
                          id="ob-cage"
                          className="font-mono"
                          value={cage}
                          onChange={(e) => setCage(e.target.value)}
                          placeholder="7QK42"
                        />
                      </Field>
                      <Field label="Team size" htmlFor="ob-size">
                        <Select value={size} onValueChange={setSize}>
                          <SelectTrigger id="ob-size">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {SIZES.map((option) => (
                              <SelectItem key={option} value={option}>
                                {option}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </Field>
                    </div>
                  </section>
                ) : null}

                {current.id === "appearance" ? (
                  <section aria-labelledby="step-heading">
                    <p className="eyebrow">Step two</p>
                    <h1 id="step-heading" className="display-tight mt-2 text-3xl text-ink">
                      Pick your stock
                    </h1>
                    <p className="mt-3 max-w-lg text-base leading-relaxed text-ink-soft">
                      The type and the ink stay the same. Only the paper changes.
                    </p>

                    <div className="mt-8 grid max-w-2xl gap-3 sm:grid-cols-3">
                      {APPEARANCES.map((option) => {
                        const Icon = option.icon;
                        const active = appearance === option.value;
                        return (
                          <button
                            key={option.value}
                            type="button"
                            onClick={() => setAppearance(option.value)}
                            aria-pressed={active}
                            className={cn(
                              "flex flex-col gap-3 rounded-lg border p-4 text-left",
                              "transition-[border-color,background-color] duration-200 ease-[cubic-bezier(0.32,0.72,0,1)]",
                              active
                                ? "border-patina bg-patina-tint"
                                : "border-line-strong bg-paper-sunk hover:border-[var(--ink-faint)]",
                            )}
                          >
                            <span className="flex items-center justify-between">
                              <Icon className={cn("size-4", active ? "text-patina" : "text-ink-faint")} aria-hidden />
                              {active ? <Check className="size-4 text-patina" aria-hidden /> : null}
                            </span>
                            <span>
                              <span className="block text-sm font-medium text-ink">{option.label}</span>
                              <span className="block text-xs text-ink-faint">{option.hint}</span>
                            </span>
                          </button>
                        );
                      })}
                    </div>

                    <div className="mt-6 flex flex-wrap items-center gap-4 border-t border-line pt-5">
                      <p className="text-sm text-ink-soft">Density</p>
                      <Segmented
                        ariaLabel="Density"
                        value={density}
                        onValueChange={(v) => setDensity(v as "comfortable" | "compact")}
                        options={[
                          { value: "comfortable", label: "Comfortable" },
                          { value: "compact", label: "Compact" },
                        ]}
                      />
                    </div>
                  </section>
                ) : null}

                {current.id === "connect" ? (
                  <section aria-labelledby="step-heading">
                    <p className="eyebrow">Step three</p>
                    <h1 id="step-heading" className="display-tight mt-2 text-3xl text-ink">
                      Where do the documents live?
                    </h1>
                    <p className="mt-3 max-w-lg text-base leading-relaxed text-ink-soft">
                      Margin reads them in place. Connecting a source means never downloading a solicitation again —
                      and reports can travel back the same way.
                    </p>

                    <ul className="mt-8 max-w-lg space-y-3">
                      {integrations.map((integration) => {
                        const Icon = INTEGRATION_ICON[integration.id];
                        return (
                          <li
                            key={integration.id}
                            className={cn(
                              "flex items-center gap-4 rounded-lg border p-4",
                              integration.connected ? "border-patina/40 bg-patina-tint/50" : "border-line bg-paper-raised",
                            )}
                          >
                            <span
                              className={cn(
                                "inline-flex size-9 shrink-0 items-center justify-center rounded-md border",
                                integration.connected
                                  ? "border-patina/35 bg-paper-raised text-patina"
                                  : "border-line-strong bg-paper-sunk text-ink-faint",
                              )}
                            >
                              <Icon className="size-4" aria-hidden />
                            </span>
                            <div className="min-w-0 flex-1">
                              <p className="text-sm font-medium text-ink">{integration.name}</p>
                              <p className="truncate text-xs text-ink-faint">
                                {integration.connected ? integration.account : integration.blurb}
                              </p>
                            </div>
                            <Button
                              variant={integration.connected ? "ghost" : "secondary"}
                              size="sm"
                              loading={connecting === integration.id}
                              onClick={() => toggleIntegration(integration.id, integration.connected)}
                            >
                              {integration.connected ? (
                                <>
                                  <Check />
                                  Connected
                                </>
                              ) : (
                                "Connect"
                              )}
                            </Button>
                          </li>
                        );
                      })}
                    </ul>
                  </section>
                ) : null}

                {current.id === "mode" ? (
                  <section aria-labelledby="step-heading">
                    <p className="eyebrow">Step four</p>
                    <h1 id="step-heading" className="display-tight mt-2 text-3xl text-ink">
                      How deeply should it read by default?
                    </h1>
                    <p className="mt-3 max-w-lg text-base leading-relaxed text-ink-soft">
                      Any analysis can override this. Most teams start on Standard and reach for Quick Triage when
                      the pipeline gets loud.
                    </p>

                    <ul className="mt-8 grid max-w-2xl gap-2.5 sm:grid-cols-2">
                      {MODES.map((mode) => {
                        const active = defaultMode === mode.id;
                        return (
                          <li key={mode.id}>
                            <button
                              type="button"
                              onClick={() => setDefaultMode(mode.id)}
                              aria-pressed={active}
                              className={cn(
                                "flex h-full w-full flex-col gap-1 rounded-lg border p-4 text-left",
                                "transition-[border-color,background-color] duration-200 ease-[cubic-bezier(0.32,0.72,0,1)]",
                                active
                                  ? "border-patina bg-patina-tint"
                                  : "border-line-strong bg-paper-sunk hover:border-[var(--ink-faint)]",
                              )}
                            >
                              <span className="flex items-center justify-between gap-2">
                                <span className="text-sm font-medium text-ink">{mode.name}</span>
                                {active ? <Check className="size-3.5 shrink-0 text-patina" aria-hidden /> : null}
                              </span>
                              <span className="text-xs leading-relaxed text-ink-soft">{mode.blurb}</span>
                              <span className="mt-auto pt-1.5 font-mono text-2xs text-ink-faint">
                                {mode.minutes} · {mode.passes}
                              </span>
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  </section>
                ) : null}

                {current.id === "done" ? (
                  <section aria-labelledby="step-heading" className="text-center sm:text-left">
                    <motion.div
                      initial={reduce ? false : { scale: 0.82, opacity: 0, rotate: -10 }}
                      animate={{ scale: 1, opacity: 1, rotate: 0 }}
                      transition={{ type: "spring", stiffness: 240, damping: 17, delay: 0.05 }}
                      className="inline-flex"
                    >
                      <WaxSeal className="size-20" label="Ready" />
                    </motion.div>
                    <h1 id="step-heading" className="display-tight mt-6 text-3xl text-ink">
                      {orgName || org?.name || "Your workspace"} is ready.
                    </h1>
                    <p className="mt-3 max-w-lg text-base leading-relaxed text-ink-soft">
                      Six live solicitations are already in the board, one of them three days from its proposal
                      deadline. Start there, or give Margin something of your own to read.
                    </p>

                    <dl className="mt-8 grid max-w-lg gap-x-8 gap-y-4 sm:grid-cols-2">
                      <Summary label="Organisation" value={orgName || org?.name || "—"} />
                      <Summary label="Appearance" value={APPEARANCES.find((a) => a.value === appearance)?.label ?? "Paper"} />
                      <Summary
                        label="Connected"
                        value={
                          integrations
                            .filter((i) => i.connected)
                            .map((i) => i.name)
                            .join(", ") || "Nothing yet"
                        }
                      />
                      <Summary
                        label="Default read"
                        value={MODES.find((m) => m.id === defaultMode)?.name ?? "Standard"}
                      />
                    </dl>
                  </section>
                ) : null}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4 border-t border-line pt-6">
          <Button
            variant="ghost"
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            disabled={step === 0}
          >
            <ArrowLeft />
            Back
          </Button>

          <div className="flex items-center gap-2">
            {!isLast ? (
              <Button variant="quiet" onClick={finish}>
                Skip setup
              </Button>
            ) : null}
            <Button
              variant="primary"
              onClick={isLast ? finish : next}
              disabled={step === 0 && orgName.trim().length < 2}
            >
              {isLast ? "Open the workspace" : "Continue"}
              <ArrowRight />
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}

function Summary({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-l-2 border-line pl-3.5 text-left">
      <dt className="eyebrow">{label}</dt>
      <dd className="mt-0.5 text-sm text-ink">{value}</dd>
    </div>
  );
}
