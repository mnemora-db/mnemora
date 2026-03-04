import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { StatCard } from "@/components/stat-card";
import { ApiKeyManager } from "@/components/api-key-manager";
import { HealthIndicator } from "@/components/health-indicator";
import { CheckCircle2, AlertTriangle, Terminal } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { getHealth, getUsageStats, type HealthStatus } from "@/lib/mnemora-api";
import { CodeBlock } from "@/components/code-block";

const QUICKSTART_CODE = `pip install mnemora

from mnemora import MnemoraSync

client = MnemoraSync(api_key="mnm_...")
client.store_state("my-agent", {"task": "hello world"})
client.store_memory("my-agent", "User prefers concise replies.")
`;

function overallBadge(health: HealthStatus) {
  if (health.ok) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-green-500">
        <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
        All Systems Operational
      </div>
    );
  }
  return (
    <div className="flex items-center gap-1.5 text-xs text-amber-500">
      <AlertTriangle className="w-3.5 h-3.5" aria-hidden="true" />
      Issues Detected
    </div>
  );
}

function timeSince(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const secs = Math.floor(diffMs / 1000);
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  return `${mins}m ago`;
}

const QUICK_LINKS: Array<{ label: string; description: string; href: string }> =
  [
    {
      label: "Memory Browser",
      description: "Inspect and search stored memories",
      href: "/dashboard/agents",
    },
    {
      label: "Agents",
      description: "Manage your registered agents",
      href: "/dashboard/agents",
    },
    {
      label: "API Keys",
      description: "Create and rotate API keys",
      href: "/dashboard/api-keys",
    },
    {
      label: "Usage & Billing",
      description: "Track operations and storage costs",
      href: "/dashboard/usage",
    },
  ];

export default async function DashboardPage() {
  const session = await getServerSession(authOptions);
  const githubId = session?.user?.id ?? "";

  // Fetch real data in parallel
  const [health, stats] = await Promise.all([
    getHealth(),
    getUsageStats(githubId),
  ]);

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
      </div>

      {/* Quick stats */}
      <section aria-label="Quick stats">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard
            label="Active Agents"
            value={String(stats.activeAgents)}
            subLabel={
              stats.activeAgents === 0
                ? "Connect your first agent"
                : undefined
            }
          />
          <StatCard
            label="State Sessions"
            value={String(stats.totalSessions ?? 0)}
          />
          <StatCard
            label="API Calls Today"
            value={
              stats.apiCallsToday > 0
                ? stats.apiCallsToday.toLocaleString()
                : "—"
            }
            subLabel={
              stats.apiCallsToday === 0 ? "Metrics coming soon" : undefined
            }
          />
          <StatCard
            label="API Calls This Month"
            value={
              stats.apiCallsMonth > 0
                ? stats.apiCallsMonth.toLocaleString()
                : "—"
            }
            subLabel={
              stats.apiCallsMonth === 0 ? "Metrics coming soon" : undefined
            }
          />
        </div>
      </section>

      {/* Health + API Key row */}
      <section
        aria-label="System health and API key"
        className="grid grid-cols-1 gap-3 lg:grid-cols-2"
      >
        {/* Health card — real data from /v1/health */}
        <article
          className="rounded-md border border-[#27272A] bg-[#18181B] px-5 py-4"
          aria-label="System health"
        >
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs font-medium text-[#71717A] uppercase tracking-wide">
              API Health
            </p>
            {overallBadge(health)}
          </div>
          <ul className="space-y-2.5">
            {health.services.map((service) => (
              <li key={service.label}>
                <HealthIndicator
                  status={service.status}
                  label={service.label}
                  size="sm"
                />
              </li>
            ))}
          </ul>
          <p className="mt-4 text-xs text-[#52525B]">
            {health.ok
              ? `v${health.version} · Last checked ${timeSince(health.checkedAt)}`
              : `Last checked ${timeSince(health.checkedAt)}`}
          </p>
        </article>

        {/* API Key card — real data */}
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

      {/* Getting started — shown when no agents */}
      {stats.activeAgents === 0 && (
        <section aria-label="Getting started">
          <div className="rounded-md border border-[#27272A] bg-[#18181B] px-5 py-6">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-md bg-[#111114] border border-[#27272A] flex items-center justify-center shrink-0">
                <Terminal
                  className="w-5 h-5 text-[#2DD4BF]"
                  aria-hidden="true"
                />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-[#FAFAFA]">
                  Connect your first agent
                </h2>
                <p className="mt-1 text-sm text-[#71717A] max-w-lg">
                  Install the SDK and start storing agent memory in under 5
                  minutes. Generate an API key above, then:
                </p>
                <div className="mt-3">
                  <CodeBlock code={QUICKSTART_CODE} />
                </div>
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
