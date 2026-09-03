"use client";

import * as React from "react";
import Link from "next/link";
import { RotateCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Wordmark } from "@/components/domain/marks";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  React.useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-dvh flex-col bg-paper px-5 py-8 sm:px-10">
      <Link href="/" className="inline-flex w-fit rounded-sm" aria-label="Margin, home">
        <Wordmark />
      </Link>

      <main className="flex flex-1 items-center py-16">
        <div className="mx-auto w-full max-w-lg">
          <p className="eyebrow">Something went wrong</p>
          <h1 className="display-tight mt-2 text-3xl leading-tight text-ink">
            We could not finish rendering this page.
          </h1>
          <p className="mt-4 text-base leading-relaxed text-ink-soft">
            Your work is stored on this device and has not been lost. Try again — if the same thing happens, reload
            the page and the workspace will rebuild from your saved data.
          </p>

          {error.digest ? (
            <p className="mt-6 border-l-2 border-line-strong pl-3 font-mono text-2xs text-ink-faint">
              digest {error.digest}
            </p>
          ) : null}

          <div className="mt-8 flex flex-wrap items-center gap-2">
            <Button variant="primary" onClick={reset}>
              <RotateCw className="size-4" aria-hidden />
              Try again
            </Button>
            <Button asChild variant="ghost">
              <Link href="/app">Back to the dashboard</Link>
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}
