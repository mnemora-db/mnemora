export default function DashboardLoading() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Header skeleton */}
      <div>
        <div className="h-6 w-40 bg-[#27272A] rounded" />
        <div className="mt-2 h-4 w-64 bg-[#27272A]/60 rounded" />
      </div>

      {/* Stats grid skeleton */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="rounded-md bg-[#18181B] border border-[#27272A] px-3 py-4"
          >
            <div className="h-2.5 w-16 bg-[#27272A] rounded" />
            <div className="mt-3 h-5 w-12 bg-[#27272A]/60 rounded" />
          </div>
        ))}
      </div>

      {/* Content cards skeleton */}
      <div className="grid sm:grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="rounded-xl bg-[#18181B] border border-[#27272A] p-5 h-48"
          >
            <div className="h-4 w-20 bg-[#27272A] rounded" />
            <div className="mt-3 h-3 w-full bg-[#27272A]/40 rounded" />
            <div className="mt-2 h-3 w-3/4 bg-[#27272A]/40 rounded" />
            <div className="mt-2 h-3 w-1/2 bg-[#27272A]/40 rounded" />
          </div>
        ))}
      </div>

      {/* Bottom card skeleton */}
      <div className="rounded-md bg-[#18181B] border border-[#27272A] px-5 py-5 h-24">
        <div className="h-4 w-32 bg-[#27272A] rounded" />
        <div className="mt-3 h-3 w-64 bg-[#27272A]/40 rounded" />
      </div>
    </div>
  );
}
