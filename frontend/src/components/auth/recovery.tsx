"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AnimatePresence, motion } from "motion/react";
import { ArrowLeft, ArrowRight, Check, MailCheck } from "lucide-react";

import { cn, sleep } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { notify } from "@/components/ui/toaster";
import { AuthFrame } from "./frame";
import { WaxSeal } from "@/components/domain/marks";

/* ---------------------------------------------------------------- */
/* Forgot password                                                    */
/* ---------------------------------------------------------------- */

const emailSchema = z.object({
  email: z.string().min(1, "Enter your work email.").email("That doesn't look like an email address."),
});

export function ForgotPasswordView() {
  const [sentTo, setSentTo] = React.useState<string | null>(null);

  const form = useForm<z.infer<typeof emailSchema>>({
    resolver: zodResolver(emailSchema),
    defaultValues: { email: "" },
  });

  return (
    <AuthFrame
      eyebrow="Account recovery"
      title={sentTo ? "Check your inbox" : "Forgotten your password"}
      description={
        sentTo
          ? undefined
          : "Give us the address on the account and we will send a link that expires in an hour."
      }
      footer={
        <p>
          <Link href="/login" className="inline-flex items-center gap-1.5 text-patina underline-offset-4 hover:underline">
            <ArrowLeft className="size-3.5" />
            Back to sign in
          </Link>
        </p>
      }
    >
      <AnimatePresence mode="wait">
        {sentTo ? (
          <motion.div
            key="sent"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-5"
          >
            <div className="flex items-start gap-3 rounded-md border border-line border-l-[3px] border-l-leaf bg-[var(--leaf-tint)] px-4 py-3.5">
              <MailCheck className="mt-0.5 size-4 shrink-0 text-leaf" aria-hidden />
              <div className="space-y-1">
                <p className="text-sm font-medium text-ink">A link is on its way to {sentTo}</p>
                <p className="text-sm leading-relaxed text-ink-soft">
                  It expires in one hour. If it does not arrive, check whether your address uses a different
                  domain to your workspace.
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              <Button asChild variant="primary" className="flex-1 justify-center">
                <Link href="/reset-password">Open the link</Link>
              </Button>
              <Button variant="ghost" onClick={() => setSentTo(null)}>
                Use another address
              </Button>
            </div>
          </motion.div>
        ) : (
          <motion.form
            key="form"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            onSubmit={form.handleSubmit(async (values) => {
              await sleep(620);
              setSentTo(values.email);
              notify.success("Recovery link sent.");
            })}
            className="space-y-4"
            noValidate
          >
            <Field label="Work email" htmlFor="recovery-email" error={form.formState.errors.email?.message}>
              <Input
                id="recovery-email"
                type="email"
                autoComplete="email"
                placeholder="name@company.com"
                aria-invalid={Boolean(form.formState.errors.email)}
                {...form.register("email")}
              />
            </Field>
            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full justify-center"
              loading={form.formState.isSubmitting}
            >
              Send the link
              <ArrowRight />
            </Button>
          </motion.form>
        )}
      </AnimatePresence>
    </AuthFrame>
  );
}

/* ---------------------------------------------------------------- */
/* Reset password                                                     */
/* ---------------------------------------------------------------- */

const resetSchema = z
  .object({
    password: z
      .string()
      .min(10, "At least ten characters.")
      .regex(/[A-Z]/, "Include a capital letter.")
      .regex(/[0-9]/, "Include a number."),
    confirm: z.string(),
  })
  .refine((values) => values.password === values.confirm, {
    message: "The two passwords do not match.",
    path: ["confirm"],
  });

export function ResetPasswordView() {
  const router = useRouter();
  const [done, setDone] = React.useState(false);

  const form = useForm<z.infer<typeof resetSchema>>({
    resolver: zodResolver(resetSchema),
    defaultValues: { password: "", confirm: "" },
  });

  return (
    <AuthFrame
      eyebrow="Account recovery"
      title={done ? "That's done" : "Choose a new password"}
      description={
        done ? "You can sign in with it now." : "The link was valid. Pick something you have not used here before."
      }
      footer={
        <p>
          <Link href="/login" className="text-patina underline-offset-4 hover:underline">
            Back to sign in
          </Link>
        </p>
      }
    >
      {done ? (
        <div className="space-y-5">
          <div className="flex items-start gap-3 rounded-md border border-line border-l-[3px] border-l-leaf bg-[var(--leaf-tint)] px-4 py-3.5">
            <Check className="mt-0.5 size-4 shrink-0 text-leaf" aria-hidden />
            <p className="text-sm leading-relaxed text-ink-soft">
              Your password has been changed and every other session has been signed out.
            </p>
          </div>
          <Button variant="primary" size="lg" className="w-full justify-center" onClick={() => router.push("/login")}>
            Sign in
            <ArrowRight />
          </Button>
        </div>
      ) : (
        <form
          onSubmit={form.handleSubmit(async () => {
            await sleep(560);
            setDone(true);
            notify.success("Password updated.");
          })}
          className="space-y-4"
          noValidate
        >
          <Field label="New password" htmlFor="new-password" error={form.formState.errors.password?.message}>
            <Input
              id="new-password"
              type="password"
              autoComplete="new-password"
              aria-invalid={Boolean(form.formState.errors.password)}
              {...form.register("password")}
            />
          </Field>
          <Field label="Confirm it" htmlFor="confirm-password" error={form.formState.errors.confirm?.message}>
            <Input
              id="confirm-password"
              type="password"
              autoComplete="new-password"
              aria-invalid={Boolean(form.formState.errors.confirm)}
              {...form.register("confirm")}
            />
          </Field>
          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="w-full justify-center"
            loading={form.formState.isSubmitting}
          >
            Set the password
          </Button>
        </form>
      )}
    </AuthFrame>
  );
}

/* ---------------------------------------------------------------- */
/* Verify email                                                       */
/* ---------------------------------------------------------------- */

export function VerifyEmailView() {
  return (
    <AuthFrame
      eyebrow="One last thing"
      title="Your address is confirmed"
      description="The workspace is yours. Everything below is already switched on."
      footer={
        <p>
          Need something else?{" "}
          <Link href="/app/help" className="text-patina underline-offset-4 hover:underline">
            Read the help
          </Link>
        </p>
      }
      aside={
        <div className="flex flex-col items-center text-center">
          <motion.div
            initial={{ scale: 0.8, opacity: 0, rotate: -8 }}
            animate={{ scale: 1, opacity: 1, rotate: 0 }}
            transition={{ type: "spring", stiffness: 260, damping: 18 }}
          >
            <WaxSeal className="size-28" label="Verified" />
          </motion.div>
          <p className="display-tight mt-6 max-w-xs font-display text-2xl leading-snug text-ink">
            Sealed, and ready to read.
          </p>
        </div>
      }
    >
      <ul className="space-y-3">
        {[
          "Six live solicitations are waiting in the workspace",
          "Outlook, SharePoint and OneDrive are connected",
          "Report templates are installed",
        ].map((item) => (
          <li key={item} className="flex items-start gap-2.5 text-sm text-ink-soft">
            <Check className="mt-0.5 size-4 shrink-0 text-leaf" aria-hidden />
            <span className="leading-relaxed">{item}</span>
          </li>
        ))}
      </ul>
      <Button asChild variant="primary" size="lg" className={cn("mt-7 w-full justify-center")}>
        <Link href="/app">
          Open the workspace
          <ArrowRight />
        </Link>
      </Button>
    </AuthFrame>
  );
}
