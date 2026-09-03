"use client";

import * as React from "react";
import { usePathname, useRouter } from "next/navigation";

import { Wordmark } from "@/components/domain/marks";
import { useSessionStore } from "@/stores/session";
import { useHydrationStore } from "@/stores";

/**
 * The workspace waits for localStorage to replay before deciding anything —
 * bouncing a signed-in person to the login screen for one frame is worse than
 * a brief, honest hold.
 */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const hydrated = useHydrationStore((s) => s.hydrated);
  const authed = useSessionStore((s) => s.isAuthenticated);

  React.useEffect(() => {
    if (hydrated && !authed) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [hydrated, authed, router, pathname]);

  if (!hydrated || !authed) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-paper">
        <div className="flex flex-col items-center gap-3">
          <Wordmark />
          <p className="font-mono text-2xs uppercase tracking-[0.16em] text-ink-faint">
            {hydrated ? "signing you in" : "opening the workspace"}
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
