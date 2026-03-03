import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { StatCard } from "@/components/stat-card";
import { ApiKeyManager } from "@/components/api-key-manager";
import { HealthIndicator } from "@/components/health-indicator";
import { CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import Image from "next/image";
import Link from "next/link";
import {
  mockUsageStats,
  mockApiCalls,
  type ApiCall,
} from "@/lib/mock-data";

function formatTimestamp(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function statusColor(status: number): string {
  if (status >= 500) return "text-red-500";
  if (status >= 400) return "text-amber-500";
  return "text-green-500";
}

function methodColor(method: ApiCall["method"]): string {
  const colors: Record<ApiCall["method"], string> = {
    GET: "text-blue-400",
    POST: "text-green-400",
    PUT: "text-amber-400",
    DELETE: "text-red-400",
  };
  return colors[method];
}

const QUICK_LINKS: Array<{ label: string; description: string; href: string }> =
  [
    {
      label: "Memory Browser",
      description: "Inspect and search stored memories",
      href: "/dashboard/memory",
    },
    {
      label: "Agents",
      description: "Manage your registered agents",
      href: "/dashboard/agents",
    },
    {
      label: "API Keys",
      description: "Create and rotate API keys",
      href: "/dashboard/keys",
    },
    {
      label: "Usage & Billing",
      description: "Track operations and storage costs",
      href: "/dashboard/usage",
    },
  ];

export default async function DashboardPage() {
  const session = await getServerSession(authOptions);
  const stats = mockUsageStats;

  const userName = session?.user?.name ?? "there";
  const avatarUrl = session?.user?.image ?? null;

  return (
    <div className="space-y-6">
      {/* Welcome header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          {avatarUrl && (
            <Image
              src={avatarUrl}
              alt={userName}
              width={40}
              height={40}
              className="rounded-full border border-[#27272A] flex-shrink-0"
            />
          )}
          <div>
            <h1 className="text-[22px] font-semibold text-[#FAFAFA] tracking-tight">
              Welcome back, {userName}
            </h1>
            <p className="mt-0.5 text-sm text-[#71717A]">
              Overview of your Mnemora workspace.
            </p>
          </div>
        </div>

        {/* Create API Key — handled by ApiKeyManager card below */}
      </div>

      {/* Quick stats */}
      <section aria-label="Quick stats">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard
            label="API Calls Today"
            value={stats.apiCallsToday.toLocaleString()}
            trend={stats.apiCallsTodayDelta}
            trendLabel="vs yesterday"
          />
          <StatCard
            label="API Calls This Month"
            value={stats.apiCallsMonth.toLocaleString()}
          />
          <StatCard
            label="Storage Used"
            value={`${stats.storageGb} GB`}
            subLabel="DynamoDB · Aurora · S3"
          />
          <StatCard
            label="Active Agents"
            value={String(stats.activeAgents)}
          />
        </div>
      </section>

      {/* Health + API Key row */}
      <section
        aria-label="System health and API key"
        className="grid grid-cols-1 gap-3 lg:grid-cols-2"
      >
        {/* Health card */}
        <article
          className="rounded-md border border-[#27272A] bg-[#18181B] px-5 py-4"
          aria-label="System health"
        >
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs font-medium text-[#71717A] uppercase tracking-wide">
              API Health
            </p>
            <div className="flex items-center gap-1.5 text-xs text-green-500">
              <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
              All Systems Operational
            </div>
          </div>
          <ul className="space-y-2.5">
            {[
              { label: "API Gateway", status: "healthy" as const },
              { label: "DynamoDB", status: "healthy" as const },
              { label: "Aurora (pgvector)", status: "healthy" as const },
              { label: "S3", status: "healthy" as const },
            ].map((service) => (
              <li key={service.label}>
                <HealthIndicator
                  status={service.status}
                  label={service.label}
                  size="sm"
                />
              </li>
            ))}
          </ul>
          <p className="mt-4 text-xs text-[#52525B]">Last checked 30s ago</p>
        </article>

        {/* API Key card */}
        <ApiKeyManager />
      </section>

      {/* Quick links */}
      <section aria-label="Quick links">
        <h2 className="text-sm font-medium text-[#71717A] uppercase tracking-wide mb-3">
          Quick Links
        </h2>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {QUICK_LINKS.map(({ label, description, href }) => (
            <Link
              key={label}
              href={href}
              className="group rounded-md border border-[#27272A] bg-[#18181B] px-4 py-3.5 hover:border-[#3F3F46] hover:bg-[#1C1C1F] transition-all duration-150"
            >
              <p className="text-sm font-medium text-[#FAFAFA] group-hover:text-[#2DD4BF] transition-colors duration-150">
                {label}
              </p>
              <p className="mt-0.5 text-xs text-[#71717A]">{description}</p>
            </Link>
          ))}
        </div>
      </section>

      {/* Recent activity */}
      <section aria-label="Recent API activity">
        <div className="rounded-md border border-[#27272A] bg-[#18181B] overflow-hidden">
          <div className="px-5 py-4 border-b border-[#27272A]">
            <h2 className="text-sm font-medium text-[#FAFAFA]">
              Recent Activity
            </h2>
            <p className="text-xs text-[#71717A] mt-0.5">
              Last 10 API requests
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs" aria-label="Recent API calls">
              <thead>
                <tr className="border-b border-[#27272A]">
                  {["Time", "Method", "Path", "Status", "Latency"].map(
                    (col) => (
                      <th
                        key={col}
                        className="px-5 py-2.5 text-left font-medium text-[#71717A] uppercase tracking-wide text-[10px]"
                        scope="col"
                      >
                        {col}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {mockApiCalls.map((call, idx) => (
                  <tr
                    key={call.id}
                    className={cn(
                      "border-b border-[#27272A] last:border-0",
                      idx % 2 === 0 ? "" : "bg-[#111114]/40"
                    )}
                  >
                    <td className="px-5 py-3 font-mono text-[#71717A] whitespace-nowrap">
                      {formatTimestamp(call.timestamp)}
                    </td>
                    <td className="px-5 py-3 font-mono whitespace-nowrap">
                      <span
                        className={cn("font-semibold", methodColor(call.method))}
                      >
                        {call.method}
                      </span>
                    </td>
                    <td className="px-5 py-3 font-mono text-[#A1A1AA] whitespace-nowrap">
                      {call.path}
                    </td>
                    <td className="px-5 py-3 font-mono whitespace-nowrap">
                      <span className={statusColor(call.status)}>
                        {call.status}
                      </span>
                    </td>
                    <td className="px-5 py-3 font-mono text-[#A1A1AA] whitespace-nowrap">
                      {call.latencyMs}ms
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}
