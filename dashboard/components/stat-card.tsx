import { TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string;
  trend?: number;
  trendLabel?: string;
  subLabel?: string;
}

export function StatCard({
  label,
  value,
  trend,
  trendLabel,
  subLabel,
}: StatCardProps) {
  const isPositive = trend !== undefined && trend >= 0;

  return (
    <article
      className="rounded-md border border-[#27272A] bg-[#18181B] px-5 py-4"
      aria-label={label}
    >
      <p className="text-xs font-medium text-[#71717A] uppercase tracking-wide">
        {label}
      </p>
      <p className="mt-2 text-[28px] font-semibold font-mono text-[#FAFAFA] leading-none">
        {value}
      </p>
      <div className="mt-2 flex items-center gap-1.5">
        {trend !== undefined && (
          <span
            className={cn(
              "flex items-center gap-0.5 text-xs font-medium",
              isPositive ? "text-green-500" : "text-red-500"
            )}
            aria-label={`${isPositive ? "Up" : "Down"} ${Math.abs(trend)}%`}
          >
            {isPositive ? (
              <TrendingUp className="w-3.5 h-3.5" aria-hidden="true" />
            ) : (
              <TrendingDown className="w-3.5 h-3.5" aria-hidden="true" />
            )}
            {isPositive ? "+" : ""}
            {trend}%
          </span>
        )}
        {trendLabel && (
          <span className="text-xs text-[#71717A]">{trendLabel}</span>
        )}
        {subLabel && !trend && (
          <span className="text-xs text-[#71717A]">{subLabel}</span>
        )}
      </div>
    </article>
  );
}
