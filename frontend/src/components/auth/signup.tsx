"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AlertTriangle, ArrowRight, Check } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/controls";
import { notify } from "@/components/ui/toaster";
import { AuthFrame, GoogleGlyph, MicrosoftGlyph } from "./frame";
import { useSessionStore } from "@/stores/session";

const schema = z
  .object({
    name: z.string().min(2, "We need a name to put on the reports."),
    org: z.string().min(2, "Which organisation is this for?"),
    email: z
      .string()
      .min(1, "Enter your work email.")
      .email("That doesn't look like an email address.")
      .refine((value) => !/@(gmail|yahoo|hotmail|outlook)\./i.test(value), {
        message: "Use your work address — the domain becomes your workspace.",
      }),
    password: z
      .string()
      .min(10, "At least ten characters.")
      .regex(/[a-z]/, "Include a lower-case letter.")
      .regex(/[A-Z]/, "Include a capital letter.")
      .regex(/[0-9]/, "Include a number."),
    terms: z.literal(true, { message: "You'll need to accept the terms." }),
  })
  .strict();

type Values = z.infer<typeof schema>;

/** Four honest signals rather than a score out of a hundred. */
function strengthOf(password: string) {
  const checks = [
    { label: "Ten characters", met: password.length >= 10 },
    { label: "Upper and lower case", met: /[a-z]/.test(password) && /[A-Z]/.test(password) },
    { label: "A number", met: /[0-9]/.test(password) },
    { label: "A symbol", met: /[^A-Za-z0-9]/.test(password) },
  ];
  const met = checks.filter((c) => c.met).length;
  const label = ["Too short", "Weak", "Passable", "Strong", "Excellent"][met];
  const tone = met <= 1 ? "seal" : met === 2 ? "ochre" : met === 3 ? "patina" : "leaf";
  return { checks, met, label, tone };
}

export function SignupView() {
  const router = useRouter();
  const reduce = useReducedMotion();
  const signup = useSessionStore((s) => s.signup);
  const loginWithMicrosoft = useSessionStore((s) => s.loginWithMicrosoft);
  const [ssoPending, setSsoPending] = React.useState(false);
  const [succeeded, setSucceeded] = React.useState(false);
  const [password, setPassword] = React.useState("");
  const [accepted, setAccepted] = React.useState(false);
  const [serverError, setServerError] = React.useState<string | null>(null);

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    mode: "onBlur",
    defaultValues: { name: "", org: "", email: "", password: "", terms: false as unknown as true },
  });

  const strength = strengthOf(password);

  async function onSubmit(values: Values) {
    const ok = await signup({
      name: values.name,
      email: values.email,
      org: values.org,
      password: values.password,
    });
    if (!ok) {
      setServerError(useSessionStore.getState().error ?? "We couldn't create the workspace.");
      return;
    }
    setServerError(null);
    setSucceeded(true);
    notify.success("Workspace created.", { description: "Three short questions and you're reading." });
    window.setTimeout(() => router.push("/onboarding"), reduce ? 0 : 420);
  }

  async function sso() {
    setSsoPending(true);
    const ok = await loginWithMicrosoft();
    setSsoPending(false);
    if (!ok) {
      setServerError(useSessionStore.getState().error ?? "Microsoft sign-in failed.");
      return;
    }
    setServerError(null);
    notify.success("Signed in with Microsoft.");
    router.push("/onboarding");
  }

  return (
    <AuthFrame
      eyebrow="Create an account"
      title="Start reading properly"
      description="Fourteen days, no card. Your workspace starts empty — upload one solicitation and it fills with what Margin found."
      footer={
        <p>
          Already have an account?{" "}
          <Link href="/login" className="text-patina underline-offset-4 hover:underline">
            Sign in
          </Link>
        </p>
      }
    >
      <div className="space-y-3">
        <Button
          variant="secondary"
          size="lg"
          className="w-full justify-center"
          loading={ssoPending}
          onClick={sso}
        >
          <MicrosoftGlyph />
          Continue with Microsoft
        </Button>
        <Button variant="secondary" size="lg" className="w-full justify-center" onClick={sso}>
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
        {serverError ? (
          <p
            role="alert"
            className="flex items-start gap-2 rounded-md border border-line border-l-[3px] border-l-seal bg-[var(--seal-tint)] px-3 py-2.5 text-sm text-ink"
          >
            <AlertTriangle className="mt-0.5 size-4 shrink-0 text-seal" aria-hidden />
            {serverError}
          </p>
        ) : null}

        <Field label="Your name" htmlFor="name" required error={form.formState.errors.name?.message}>
          <Input
            id="name"
            autoComplete="name"
            placeholder="Amara Osei"
            aria-invalid={Boolean(form.formState.errors.name)}
            {...form.register("name")}
          />
        </Field>

        <Field label="Organisation" htmlFor="org" required error={form.formState.errors.org?.message}>
          <Input
            id="org"
            autoComplete="organization"
            placeholder="Thornfield & Co"
            aria-invalid={Boolean(form.formState.errors.org)}
            {...form.register("org")}
          />
        </Field>

        <Field
          label="Work email"
          htmlFor="email"
          required
          error={form.formState.errors.email?.message}
          hint="Becomes your workspace domain"
        >
          <Input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="name@company.com"
            aria-invalid={Boolean(form.formState.errors.email)}
            {...form.register("email")}
          />
        </Field>

        <Field label="Password" htmlFor="password" required error={form.formState.errors.password?.message}>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            aria-invalid={Boolean(form.formState.errors.password)}
            aria-describedby="password-strength"
            {...form.register("password", {
              onChange: (event) => setPassword(event.target.value),
            })}
          />
        </Field>

        <div id="password-strength" className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="flex flex-1 gap-1" aria-hidden>
              {[0, 1, 2, 3].map((i) => (
                <motion.span
                  key={i}
                  className="h-1 flex-1 rounded-full"
                  animate={{
                    backgroundColor:
                      i < strength.met ? `var(--${strength.tone})` : "var(--line-strong)",
                  }}
                  transition={{ duration: reduce ? 0 : 0.25 }}
                />
              ))}
            </div>
            <span
              className="font-mono text-2xs tabular"
              style={{ color: password ? `var(--${strength.tone})` : "var(--ink-faint)" }}
            >
              {password ? strength.label : "—"}
            </span>
          </div>
          <ul className="flex flex-wrap gap-x-4 gap-y-1">
            {strength.checks.map((check) => (
              <li
                key={check.label}
                className={cn(
                  "flex items-center gap-1.5 text-2xs transition-colors duration-200",
                  check.met ? "text-ink-soft" : "text-ink-faint",
                )}
              >
                <Check
                  className={cn(
                    "size-3 transition-opacity duration-200",
                    check.met ? "text-leaf opacity-100" : "opacity-30",
                  )}
                  aria-hidden
                />
                {check.label}
              </li>
            ))}
          </ul>
        </div>

        <div className="space-y-1.5">
          <label className="flex cursor-pointer items-start gap-2.5 text-sm text-ink-soft">
            <Checkbox
              className="mt-0.5"
              checked={accepted}
              onCheckedChange={(v) => {
                const next = Boolean(v);
                setAccepted(next);
                form.setValue("terms", next as true, { shouldValidate: true });
              }}
              aria-invalid={Boolean(form.formState.errors.terms)}
            />
            <span className="leading-relaxed">
              I accept the terms of service and the data processing addendum.
            </span>
          </label>
          {form.formState.errors.terms ? (
            <p role="alert" className="text-xs text-seal">
              {form.formState.errors.terms.message}
            </p>
          ) : null}
        </div>

        <Button
          type="submit"
          variant="primary"
          size="lg"
          className="w-full justify-center"
          loading={form.formState.isSubmitting}
        >
          {succeeded ? (
            <>
              <Check />
              Workspace created
            </>
          ) : (
            <>
              Create the workspace
              <ArrowRight />
            </>
          )}
        </Button>
      </form>
    </AuthFrame>
  );
}
