"use client";

import * as React from "react";
import Link from "next/link";
import { RotateCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/feedback";

export default function AppError({
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
    <div className="mx-auto max-w-2xl py-10">
      <ErrorState
        title="This view could not be drawn."
        description={
          <>
            Nothing has been lost — your analyses live in this browser and are untouched. Try again, or step back to
            the dashboard and come at it from there.
            {error.digest ? (
              <span className="mt-3 block font-mono text-2xs text-ink-faint">digest {error.digest}</span>
            ) : null}
          </>
        }
        action={
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="primary" onClick={reset}>
              <RotateCw className="size-4" aria-hidden />
              Try again
            </Button>
            <Button asChild variant="ghost">
              <Link href="/app">Dashboard</Link>
            </Button>
          </div>
        }
      />
    </div>
  );
}
