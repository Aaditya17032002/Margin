"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AlertTriangle, ArrowRight, Check } from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";

import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/controls";
import { notify } from "@/components/ui/toaster";
import { AuthFrame, GoogleGlyph, MicrosoftGlyph } from "./frame";
import { useSessionStore } from "@/stores/session";

const schema = z.object({
  email: z.string().min(1, "Enter your work email.").email("That doesn't look like an email address."),
  password: z.string().min(6, "Passwords are at least six characters."),
  remember: z.boolean().optional(),
});

type Values = z.infer<typeof schema>;

export function LoginView() {
  const router = useRouter();
  const params = useSearchParams();
  const reduce = useReducedMotion();
  const login = useSessionStore((s) => s.login);
  const loginWithMicrosoft = useSessionStore((s) => s.loginWithMicrosoft);
  const onboarded = useSessionStore((s) => s.onboarded);

  const [serverError, setServerError] = React.useState<string | null>(null);
  const [succeeded, setSucceeded] = React.useState(false);
  const [ssoPending, setSsoPending] = React.useState<"microsoft" | "google" | null>(null);

  const [remember, setRemember] = React.useState(true);

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { email: "a.osei@thornfield.co", password: "margin2026", remember: true },
  });

  async function onSubmit(values: Values) {
    setServerError(null);
    const ok = await login(values.email, values.password);
    if (!ok) {
      setServerError(useSessionStore.getState().error ?? "We couldn't sign you in.");
      return;
    }
    finish();
  }

  async function sso(provider: "microsoft" | "google") {
    setServerError(null);
    setSsoPending(provider);
    await loginWithMicrosoft();
    setSsoPending(null);
    finish();
  }

  function finish() {
    setSucceeded(true);
    notify.success("Signed in.", { description: "Welcome back." });
    // Come back to whatever the person was reaching for, if anything.
    const next = params.get("next");
    const destination = !onboarded ? "/onboarding" : next && next.startsWith("/app") ? next : "/app";
    // A short beat so the confirmation is seen rather than merely rendered.
    window.setTimeout(() => router.push(destination), reduce ? 0 : 420);
  }

  const busy = form.formState.isSubmitting || ssoPending !== null || succeeded;

  return (
    <AuthFrame
      eyebrow="Welcome back"
      title="Sign in to Margin"
      description="Pick up wherever the reading stopped."
      footer={
        <p>
          New here?{" "}
          <Link href="/signup" className="text-patina underline-offset-4 hover:underline">
            Create an account
          </Link>
        </p>
      }
    >
      <div className="space-y-3">
        <Button
          variant="secondary"
          size="lg"
          className="w-full justify-center"
          loading={ssoPending === "microsoft"}
          disabled={busy && ssoPending !== "microsoft"}
          onClick={() => sso("microsoft")}
        >
          <MicrosoftGlyph />
          Continue with Microsoft
        </Button>
        <Button
          variant="secondary"
          size="lg"
          className="w-full justify-center"
          loading={ssoPending === "google"}
          disabled={busy && ssoPending !== "google"}
          onClick={() => sso("google")}
        >
          <GoogleGlyph />
          Continue with Google
        </Button>
      </div>

      <div className="my-6 flex items-center gap-4">
        <span className="h-px flex-1 bg-line" aria-hidden />
        <span className="font-mono text-2xs uppercase tracking-[0.13em] text-ink-faint">or</span>
        <span className="h-px flex-1 bg-line" aria-hidden />
      </div>

      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
        <Field label="Work email" htmlFor="email" error={form.formState.errors.email?.message}>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            aria-invalid={Boolean(form.formState.errors.email)}
            {...form.register("email")}
          />
        </Field>

        <Field
          label="Password"
          htmlFor="password"
          error={form.formState.errors.password?.message}
          hint={
            <Link href="/forgot-password" className="text-patina underline-offset-4 hover:underline">
              Forgotten?
            </Link>
          }
        >
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            aria-invalid={Boolean(form.formState.errors.password)}
            {...form.register("password")}
          />
        </Field>

        <label className="flex cursor-pointer items-center gap-2.5 text-sm text-ink-soft">
          <Checkbox
            checked={remember}
            onCheckedChange={(v) => {
              const next = Boolean(v);
              setRemember(next);
              form.setValue("remember", next);
            }}
          />
          Keep me signed in on this device
        </label>

        <AnimatePresence>
          {serverError ? (
            <motion.p
              role="alert"
              initial={reduce ? { opacity: 0 } : { opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="flex items-start gap-2 overflow-hidden rounded-md border border-line border-l-[3px] border-l-seal bg-[var(--seal-tint)] px-3 py-2.5 text-sm text-ink"
            >
              <AlertTriangle className="mt-0.5 size-4 shrink-0 text-seal" aria-hidden />
              {serverError}
            </motion.p>
          ) : null}
        </AnimatePresence>

        <Button
          type="submit"
          variant="primary"
          size="lg"
          className="w-full justify-center"
          loading={form.formState.isSubmitting}
          disabled={busy && !form.formState.isSubmitting}
        >
          {succeeded ? (
            <>
              <Check />
              Signed in
            </>
          ) : (
            <>
              Sign in
              <ArrowRight />
            </>
          )}
        </Button>
      </form>

      <p className="mt-5 text-xs leading-relaxed text-ink-faint">
        This is a demonstration. Any well-formed email and a password of six characters or more will get you in —
        the fields are pre-filled so you can simply continue.
      </p>
    </AuthFrame>
  );
}
