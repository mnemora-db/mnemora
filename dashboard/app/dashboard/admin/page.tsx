export const dynamic = "force-dynamic";

import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { getAdminData } from "@/lib/admin";
import { StatCard } from "@/components/stat-card";
import { TIER_BADGE_COLORS } from "@/lib/tiers";
import { cn } from "@/lib/utils";
import { ShieldAlert, ExternalLink } from "lucide-react";

// ── Constants ────────────────────────────────────────────────────────

const ADMIN_GITHUB_USERNAME = "isaacgbc";

// ── Badge styles ────────────────────────────────────────────────────

const SEVERITY_BADGE: Record<string, string> = {
  critical: "bg-red-500/10 text-red-400 border-red-500/20",
  major: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  minor: "bg-[#27272A]/50 text-[#A1A1AA] border-[#3F3F46]",
};

const TYPE_BADGE: Record<string, string> = {
  bug: "bg-red-500/10 text-red-400 border-red-500/20",
  feature: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  feedback: "bg-blue-500/10 text-blue-400 border-blue-500/20",
};

// ── Helpers ──────────────────────────────────────────────────────────

/**
 * Format a byte count as KB (below 1 MB) or MB (1 MB and above).
 * Both are rounded to one decimal place.
 */
function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const mb = bytes / (1024 * 1024);
  if (mb < 1) {
    const kb = bytes / 1024;
    return `${kb.toFixed(1)} KB`;
  }
  return `${mb.toFixed(1)} MB`;
}

/**
 * Slice an ISO timestamp to YYYY-MM-DD.
 * Returns "—" for empty or malformed strings.
 */
function isoToDate(iso: string): string {
  if (!iso) return "—";
  return iso.slice(0, 10);
}

// ── Shared table wrapper ─────────────────────────────────────────────

function TableWrapper({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-[#27272A] overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">{children}</table>
      </div>
    </div>
  );
}

function Th({ children, right }: { children: React.ReactNode; right?: boolean }) {
  return (
    <th
      scope="col"
      className={cn(
        "px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#71717A]",
        right ? "text-right" : "text-left"
      )}
    >
      {children}
    </th>
  );
}

// ── Page ─────────────────────────────────────────────────────────────

export default async function AdminPage() {
  const session = await getServerSession(authOptions);
  const username = session?.user?.name ?? "";

  // Auth gate — admin only
  if (username !== ADMIN_GITHUB_USERNAME) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <div className="w-12 h-12 rounded-lg bg-[#111114] border border-[#27272A] flex items-center justify-center">
          <ShieldAlert className="w-6 h-6 text-[#71717A]" aria-hidden="true" />
        </div>
        <h1 className="text-lg font-semibold text-[#FAFAFA]">Access Denied</h1>
        <p className="text-sm text-[#71717A]">
          This page is only available to administrators.
        </p>
      </div>
    );
  }

  const { users, revenue, apiUsage, lambdaMetrics, aurora, dynamoTables, recentFeedback, costs } =
    await getAdminData();

  const totalCost = costs.reduce((sum, c) => sum + c.estimatedCost, 0);

  return (
    <div className="space-y-8">

      {/* ── Header ─────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-[22px] font-semibold text-[#FAFAFA] tracking-tight">
          Admin Dashboard
        </h1>
        <p className="mt-0.5 text-sm text-[#71717A]">
          Platform metrics and infrastructure status.
        </p>
      </div>

      {/* ── Section 1: Revenue ─────────────────────────────────────── */}
      <section aria-label="Revenue metrics">
        <h2 className="text-base font-semibold text-[#FAFAFA] mb-3">Revenue</h2>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard
            label="Total Users"
            value={String(revenue.totalUsers)}
            subLabel="across all tiers"
          />
          <StatCard
            label="Paying Users"
            value={String(revenue.payingUsers)}
            subLabel={
              revenue.totalUsers > 0
                ? `${Math.round((revenue.payingUsers / revenue.totalUsers) * 100)}% of total`
                : "0% of total"
            }
          />
          <StatCard
            label="MRR"
            value={`$${revenue.mrr}`}
            subLabel="monthly recurring"
          />
          <StatCard
            label="Free Tier"
            value={`${revenue.freePercent}%`}
            subLabel={`of ${revenue.totalUsers} total`}
          />
        </div>
      </section>

      {/* ── Section 2: Users Table ─────────────────────────────────── */}
      <section aria-label="Users table">
        <div className="flex items-center gap-2 mb-3">
          <h2 className="text-base font-semibold text-[#FAFAFA]">Users</h2>
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full border bg-[#27272A]/50 text-[#A1A1AA] border-[#3F3F46]">
            {revenue.totalUsers}
          </span>
        </div>

        {users.length === 0 ? (
          <div className="rounded-xl border border-[#27272A] px-5 py-10 text-center">
            <p className="text-sm text-[#71717A]">No users found.</p>
          </div>
        ) : (
          <TableWrapper>
            <thead>
              <tr className="bg-[#111114]">
                <Th>Username</Th>
                <Th>Email</Th>
                <Th>Tier</Th>
                <Th right>API Today</Th>
                <Th right>API Month</Th>
                <Th>Created</Th>
                <Th>Last Login</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#27272A]">
              {users.map((user) => {
                const badgeClass =
                  TIER_BADGE_COLORS[user.tier] ?? TIER_BADGE_COLORS.free;
                return (
                  <tr
                    key={user.githubId}
                    className="hover:bg-[#111114]/50 transition-colors duration-150"
                  >
                    <td className="px-4 py-3 text-[#FAFAFA] font-mono text-xs whitespace-nowrap">
                      @{user.githubUsername || user.githubId}
                    </td>
                    <td className="px-4 py-3 text-[#A1A1AA] text-xs max-w-[180px] truncate">
                      {user.email || "—"}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className={cn(
                          "text-[10px] font-semibold px-2 py-0.5 rounded-full border capitalize",
                          badgeClass
                        )}
                      >
                        {user.tier}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs text-[#FAFAFA] whitespace-nowrap">
                      {user.apiCallsToday.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs text-[#FAFAFA] whitespace-nowrap">
                      {user.apiCallsMonth.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-xs text-[#71717A] whitespace-nowrap font-mono">
                      {isoToDate(user.createdAt)}
                    </td>
                    <td className="px-4 py-3 text-xs text-[#71717A] whitespace-nowrap font-mono">
                      {isoToDate(user.lastLogin)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </TableWrapper>
        )}
      </section>

      {/* ── Section 3: API Usage ───────────────────────────────────── */}
      <section aria-label="API usage metrics">
        <h2 className="text-base font-semibold text-[#FAFAFA] mb-3">API Usage</h2>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard
            label="Calls Today"
            value={apiUsage.totalCallsToday.toLocaleString()}
            subLabel="platform-wide"
          />
          <StatCard
            label="Calls This Month"
            value={apiUsage.totalCallsMonth.toLocaleString()}
            subLabel="all tenants"
          />
          <StatCard
            label="Total Vectors"
            value={apiUsage.totalVectors.toLocaleString()}
            subLabel="in Aurora pgvector"
          />
          <StatCard
            label="State Items"
            value={apiUsage.totalStateItems.toLocaleString()}
            subLabel="in DynamoDB"
          />
        </div>
      </section>

      {/* ── Section 4: Infrastructure ─────────────────────────────── */}
      <section aria-label="Infrastructure status">
        <h2 className="text-base font-semibold text-[#FAFAFA] mb-3">
          Infrastructure
        </h2>

        <div className="space-y-4">

          {/* Lambda Functions */}
          <div>
            <p className="text-xs font-medium text-[#71717A] uppercase tracking-wider mb-2">
              Lambda Functions
            </p>
            <TableWrapper>
              <thead>
                <tr className="bg-[#111114]">
                  <Th>Function</Th>
                  <Th right>Invocations</Th>
                  <Th right>Errors</Th>
                  <Th right>Avg Duration</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#27272A]">
                {lambdaMetrics.map((fn) => (
                  <tr
                    key={fn.functionName}
                    className="hover:bg-[#111114]/50 transition-colors duration-150"
                  >
                    <td className="px-4 py-3 text-[#FAFAFA] text-sm">
                      {fn.displayName}
                      <span className="ml-2 font-mono text-[10px] text-[#52525B]">
                        {fn.functionName}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs text-[#A1A1AA] whitespace-nowrap">
                      {fn.invocationsToday.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs whitespace-nowrap">
                      <span
                        className={fn.errorsToday > 0 ? "text-red-400" : "text-[#A1A1AA]"}
                      >
                        {fn.errorsToday.toLocaleString()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs text-[#A1A1AA] whitespace-nowrap">
                      {fn.avgDurationMs > 0
                        ? `${Math.round(fn.avgDurationMs)}ms`
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </TableWrapper>
          </div>

          {/* Aurora Serverless */}
          <div>
            <p className="text-xs font-medium text-[#71717A] uppercase tracking-wider mb-2">
              Aurora Serverless v2
            </p>
            <div className="rounded-xl border border-[#27272A] bg-[#18181B] px-5 py-4">
              <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-[#71717A]">Status</span>
                  <span
                    className={cn(
                      "text-[10px] font-semibold px-2 py-0.5 rounded-full border",
                      aurora.status === "available"
                        ? "bg-green-500/10 text-green-400 border-green-500/20"
                        : "bg-amber-500/10 text-amber-400 border-amber-500/20"
                    )}
                  >
                    {aurora.status}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-[#71717A]">Engine</span>
                  <span className="text-xs font-mono text-[#A1A1AA]">
                    {aurora.engine}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-[#71717A]">ACU Range</span>
                  <span className="text-xs font-mono text-[#A1A1AA]">
                    {aurora.minACU} &ndash; {aurora.maxACU} ACU
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* DynamoDB Tables */}
          <div>
            <p className="text-xs font-medium text-[#71717A] uppercase tracking-wider mb-2">
              DynamoDB Tables
            </p>
            <TableWrapper>
              <thead>
                <tr className="bg-[#111114]">
                  <Th>Table</Th>
                  <Th right>Items</Th>
                  <Th right>Size</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#27272A]">
                {dynamoTables.map((table) => (
                  <tr
                    key={table.name}
                    className="hover:bg-[#111114]/50 transition-colors duration-150"
                  >
                    <td className="px-4 py-3 text-[#FAFAFA] text-sm">
                      {table.displayName}
                      <span className="ml-2 font-mono text-[10px] text-[#52525B]">
                        {table.name}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs text-[#A1A1AA] whitespace-nowrap">
                      {table.itemCount.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs text-[#A1A1AA] whitespace-nowrap">
                      {formatBytes(table.sizeBytes)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </TableWrapper>
          </div>
        </div>
      </section>

      {/* ── Section 5: Recent Feedback ──────────────────────────────── */}
      <section aria-label="Recent feedback">
        <h2 className="text-base font-semibold text-[#FAFAFA] mb-3">
          Recent Feedback
        </h2>

        {recentFeedback.length === 0 ? (
          <div className="rounded-xl border border-[#27272A] px-5 py-10 text-center">
            <p className="text-sm text-[#71717A]">No feedback yet.</p>
          </div>
        ) : (
          <TableWrapper>
            <thead>
              <tr className="bg-[#111114]">
                <Th>Date</Th>
                <Th>User</Th>
                <Th>Type</Th>
                <Th>Title</Th>
                <Th>Severity / Rating</Th>
                <Th>Issue</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#27272A]">
              {recentFeedback.map((item, idx) => {
                const typeKey = item.type?.toLowerCase() ?? "feedback";
                const typeClass =
                  TYPE_BADGE[typeKey] ?? TYPE_BADGE.feedback;
                const severityKey = item.severity?.toLowerCase() ?? "";
                const severityClass =
                  SEVERITY_BADGE[severityKey] ?? SEVERITY_BADGE.minor;
                return (
                  <tr
                    key={`${item.date}-${item.username}-${idx}`}
                    className="hover:bg-[#111114]/50 transition-colors duration-150"
                  >
                    <td className="px-4 py-3 font-mono text-xs text-[#71717A] whitespace-nowrap">
                      {isoToDate(item.date)}
                    </td>
                    <td className="px-4 py-3 text-xs text-[#A1A1AA] whitespace-nowrap">
                      @{item.username || "unknown"}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className={cn(
                          "text-[10px] font-semibold px-2 py-0.5 rounded-full border capitalize",
                          typeClass
                        )}
                      >
                        {item.type || "feedback"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-[#FAFAFA] max-w-[240px] truncate">
                      {item.title || "—"}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {item.type === "bug" && item.severity ? (
                        <span
                          className={cn(
                            "text-[10px] font-semibold px-2 py-0.5 rounded-full border capitalize",
                            severityClass
                          )}
                        >
                          {item.severity}
                        </span>
                      ) : item.rating != null ? (
                        <span className="text-xs font-mono text-[#A1A1AA]">
                          {item.rating}/5
                        </span>
                      ) : (
                        <span className="text-[#52525B] text-xs">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {item.githubIssueUrl ? (
                        <a
                          href={item.githubIssueUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 text-[#2DD4BF] hover:text-teal-300 transition-colors duration-150 text-xs"
                          aria-label={`Open GitHub issue for: ${item.title}`}
                        >
                          View
                          <ExternalLink className="w-3 h-3" aria-hidden="true" />
                        </a>
                      ) : (
                        <span className="text-[#52525B] text-xs">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </TableWrapper>
        )}
      </section>

      {/* ── Section 6: Estimated Costs ─────────────────────────────── */}
      <section aria-label="Estimated AWS costs">
        <h2 className="text-base font-semibold text-[#FAFAFA] mb-3">
          Estimated Costs
        </h2>
        <TableWrapper>
          <thead>
            <tr className="bg-[#111114]">
              <Th>Service</Th>
              <Th>Usage</Th>
              <Th right>Est. Cost</Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#27272A]">
            {costs.map((cost) => (
              <tr
                key={cost.service}
                className="hover:bg-[#111114]/50 transition-colors duration-150"
              >
                <td className="px-4 py-3 text-sm text-[#FAFAFA]">
                  {cost.service}
                </td>
                <td className="px-4 py-3 text-xs text-[#A1A1AA]">
                  {cost.usage}
                </td>
                <td className="px-4 py-3 text-right font-mono text-xs text-[#FAFAFA] whitespace-nowrap">
                  ${cost.estimatedCost.toFixed(2)}
                </td>
              </tr>
            ))}
            {/* Total row */}
            <tr className="bg-[#111114]">
              <td
                colSpan={2}
                className="px-4 py-3 text-sm font-semibold text-[#FAFAFA]"
              >
                Total (estimated)
              </td>
              <td className="px-4 py-3 text-right font-mono text-sm font-semibold text-[#FAFAFA] whitespace-nowrap">
                ${totalCost.toFixed(2)}
              </td>
            </tr>
          </tbody>
        </TableWrapper>
      </section>

    </div>
  );
}
