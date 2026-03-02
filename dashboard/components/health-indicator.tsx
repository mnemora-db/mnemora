import { cn } from "@/lib/utils";

type HealthStatus = "healthy" | "degraded" | "down";

interface HealthIndicatorProps {
  status: HealthStatus;
  label: string;
  size?: "sm" | "md";
}

const statusConfig: Record<
  HealthStatus,
  { color: string; label: string; dot: string }
> = {
  healthy: {
    color: "text-green-500",
    label: "Healthy",
    dot: "bg-green-500",
  },
  degraded: {
    color: "text-amber-500",
    label: "Degraded",
    dot: "bg-amber-500",
  },
  down: {
    color: "text-red-500",
    label: "Down",
    dot: "bg-red-500",
  },
};

export function HealthIndicator({
  status,
  label,
  size = "md",
}: HealthIndicatorProps) {
  const config = statusConfig[status];

  return (
    <div
      className="flex items-center gap-2"
      role="status"
      aria-label={`${label}: ${config.label}`}
    >
      <span
        className={cn(
          "rounded-full shrink-0",
          config.dot,
          size === "sm" ? "w-1.5 h-1.5" : "w-2 h-2"
        )}
        aria-hidden="true"
      />
      <span
        className={cn(
          "font-medium",
          size === "sm" ? "text-xs text-[#A1A1AA]" : "text-sm text-[#FAFAFA]"
        )}
      >
        {label}
      </span>
    </div>
  );
}
