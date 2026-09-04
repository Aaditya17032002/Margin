import { Skeleton, SkeletonPanel } from "@/components/ui/feedback";

export default function AppLoading() {
  return (
    <div className="mx-auto max-w-[80rem] space-y-8" role="status" aria-busy aria-label="Loading">
      <div className="space-y-2.5">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-8 w-72" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-lg border border-line bg-paper-raised p-5">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="mt-3.5 h-8 w-16" />
          </div>
        ))}
      </div>
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <SkeletonPanel className="h-72" />
        <SkeletonPanel className="h-72" />
      </div>
      <span className="sr-only">Loading the workspace.</span>
    </div>
  );
}
