import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { getUsageStats, getVectorCount } from "@/lib/mnemora-api";
import { StatCard } from "@/components/stat-card";
import { ArrowRight } from "lucide-react";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, GetCommand } from "@aws-sdk/lib-dynamodb";
import { TIER_LIMITS, TIER_BADGE_COLORS, TIER_NUMERIC } from "@/lib/tiers";
import { getStorageMetrics } from "@/lib/cloudwatch";
import Link from "next/link";

const USERS_TABLE = process.env.USERS_TABLE_NAME ?? "mnemora-users-dev";
const usageDdb = new DynamoDBClient({ region: process.env.AWS_REGION ?? "us-east-1" });
const usageDocClient = DynamoDBDocumentClient.from(usageDdb);

// ── Progress bar component ──────────────────────────────────────────

function UsageMeter({
  label,
  current,
  limit,
  unit,
}: {
  label: string;
  current: number;
  limit: number;
  unit?: string;
}) {
  const isUnlimited = !isFinite(limit);
  const pct = isUnlimited ? 0 : limit > 0 ? Math.min((current / limit) * 100, 100) : 0;

  // Color thresholds: green <70%, amber 70-90%, red ≥90%
  let barColor = "bg-[#2DD4BF]"; // teal
  let textColor = "text-[#2DD4BF]";
  if (!isUnlimited && pct >= 90) {
    barColor = "bg-red-500";
    textColor = "text-red-500";
  } else if (!isUnlimited && pct >= 70) {
    barColor = "bg-amber-500";
    textColor = "text-amber-500";
  }

  const formatNum = (n: number) => {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(n >= 10_000 ? 0 : 1)}K`;
    return n.toLocaleString();
  };

  const currentStr = unit ? `${current} ${unit}` : formatNum(current);
  const limitStr = isUnlimited
    ? "Unlimited"
    : unit
      ? `${formatNum(limit)} ${unit}`
      : formatNum(limit);

  return (
    <div className="rounded-md border border-[#27272A] bg-[#18181B] px-5 py-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-[#71717A] uppercase tracking-wide">
          {label}
        </span>
        <span className={`text-xs font-mono ${textColor}`}>
          {currentStr} / {limitStr}
        </span>
      </div>
      <div className="h-2 rounded-full bg-[#27272A] overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${isUnlimited ? 0 : pct}%` }}
        />
      </div>
      {!isUnlimited && pct > 0 && (
        <p className="mt-1.5 text-[10px] text-[#52525B] text-right">
          {Math.round(pct)}% used
        </p>
      )}
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────

export default async function UsagePage() {
  const session = await getServerSession(authOptions);
  const githubId = session?.user?.id ?? "";
  const stats = await getUsageStats(githubId);

  // Fetch user record (tier + per-tenant API call counters)
  let userTier = "free";
  let apiCallsToday = 0;
  let apiCallsMonth = 0;
  try {
    const userResult = await usageDocClient.send(
      new GetCommand({
        TableName: USERS_TABLE,
        Key: { github_id: githubId },
        ProjectionExpression:
          "tier, api_calls_today, api_calls_month, last_call_date, last_call_month",
      })
    );
    const item = userResult.Item ?? {};
    userTier = String(item.tier ?? "free");

    // Read counters — reset if stale
    const now = new Date();
    const today = now.toISOString().slice(0, 10);
    const month = now.toISOString().slice(0, 7);

    apiCallsToday = Number(item.api_calls_today ?? 0);
    apiCallsMonth = Number(item.api_calls_month ?? 0);

    if (item.last_call_date && item.last_call_date !== today) {
      apiCallsToday = 0;
    }
    if (item.last_call_month && item.last_call_month !== month) {
      apiCallsMonth = 0;
    }
  } catch {
    // Fallback to free / zeros
  }

  // Fetch storage metrics + vector count in parallel
  let storageUsedMB = 0;
  let vectorCount = 0;
  try {
    const [storage, vectors] = await Promise.all([
      getStorageMetrics(),
      getVectorCount(githubId),
    ]);
    storageUsedMB = storage.storageUsedMB;
    vectorCount = vectors;
  } catch {
    // Fallback to 0
  }

  const tierInfo = TIER_LIMITS[userTier] ?? TIER_LIMITS.free;
  const tierNumeric = TIER_NUMERIC[userTier] ?? TIER_NUMERIC.free;
  const badgeColor = TIER_BADGE_COLORS[userTier] ?? TIER_BADGE_COLORS.free;

  // Billing period label
  const now = new Date();
  const monthName = now.toLocaleString("en-US", { month: "long" });
  const year = now.getFullYear();
  const daysInMonth = new Date(year, now.getMonth() + 1, 0).getDate();

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-[22px] font-semibold text-[#FAFAFA] tracking-tight">
          Usage
        </h1>
        <p className="mt-0.5 text-sm text-[#71717A]">
          Current billing period: {monthName} 1&ndash;{daysInMonth}, {year}.
        </p>
      </div>

      {/* Live stats */}
      <section aria-label="Live usage stats">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard
            label="Active Agents"
            value={String(stats.activeAgents)}
          />
          <StatCard
            label="State Sessions"
            value={String(stats.totalSessions ?? 0)}
          />
          <StatCard
            label="API Calls Today"
            value={apiCallsToday > 0 ? apiCallsToday.toLocaleString() : "0"}
          />
          <StatCard
            label="API Calls This Month"
            value={apiCallsMonth > 0 ? apiCallsMonth.toLocaleString() : "0"}
          />
        </div>
      </section>

      {/* Tier info */}
      <section aria-label="Current tier">
        <div className="rounded-md border border-[#27272A] bg-[#18181B] px-5 py-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-[#71717A] uppercase tracking-wide">
                Current Tier
              </p>
              <p className="mt-1 text-lg font-semibold text-[#FAFAFA]">
                {tierInfo.label}
              </p>
              <p className="mt-0.5 text-xs text-[#71717A]">
                {tierInfo.apiCallsPerDay} API calls/day · {tierInfo.storage} storage · {tierInfo.agents} agent{tierInfo.agents === "1" ? "" : "s"}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span
                className={`px-2.5 py-1 rounded-md text-xs font-semibold uppercase tracking-wide border ${badgeColor}`}
              >
                {tierInfo.label}
              </span>
              <Link
                href="/dashboard/billing"
                className="flex items-center gap-1 text-xs text-[#71717A] hover:text-[#2DD4BF] transition-colors"
              >
                Manage plan
                <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Usage vs Limits — progress bars */}
      <section aria-label="Usage vs limits">
        <div className="space-y-1.5 mb-3">
          <h2 className="text-sm font-medium text-[#FAFAFA]">
            Usage vs Limits
          </h2>
          <p className="text-xs text-[#71717A]">
            Real-time usage against your {tierInfo.label} tier limits.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 gap-3">
          <UsageMeter
            label="API Calls Today"
            current={apiCallsToday}
            limit={tierNumeric.apiCallsPerDay}
          />
          <UsageMeter
            label="Storage Used"
            current={storageUsedMB}
            limit={tierNumeric.storageMB}
            unit="MB"
          />
          <UsageMeter
            label="Vectors Stored"
            current={vectorCount}
            limit={tierNumeric.vectors}
          />
          <UsageMeter
            label="Active Agents"
            current={stats.activeAgents}
            limit={tierNumeric.agents}
          />
        </div>
      </section>
    </div>
  );
}
