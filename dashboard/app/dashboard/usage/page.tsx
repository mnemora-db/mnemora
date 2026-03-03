import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { getUsageStats } from "@/lib/mnemora-api";
import { StatCard } from "@/components/stat-card";
import { BarChart3, ArrowRight } from "lucide-react";
import {
  mockCostEstimates,
} from "@/lib/mock-data";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, GetCommand } from "@aws-sdk/lib-dynamodb";
import { TIER_LIMITS, TIER_BADGE_COLORS } from "@/lib/tiers";
import Link from "next/link";

const USERS_TABLE = process.env.USERS_TABLE_NAME ?? "mnemora-users-dev";
const usageDdb = new DynamoDBClient({ region: process.env.AWS_REGION ?? "us-east-1" });
const usageDocClient = DynamoDBDocumentClient.from(usageDdb);

function totalCost(costs: { cost: number }[]): number {
  return costs.reduce((sum, c) => sum + c.cost, 0);
}

export default async function UsagePage() {
  const session = await getServerSession(authOptions);
  const githubId = session?.user?.id ?? "";
  const stats = await getUsageStats(githubId);
  const total = totalCost(mockCostEstimates);

  // Fetch user tier from DynamoDB
  let userTier = "free";
  try {
    const userResult = await usageDocClient.send(
      new GetCommand({
        TableName: USERS_TABLE,
        Key: { github_id: githubId },
        ProjectionExpression: "tier",
      })
    );
    userTier = String(userResult.Item?.tier ?? "free");
  } catch {
    // Fallback to free
  }
  const tierInfo = TIER_LIMITS[userTier] ?? TIER_LIMITS.free;
  const badgeColor = TIER_BADGE_COLORS[userTier] ?? TIER_BADGE_COLORS.free;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-[22px] font-semibold text-[#FAFAFA] tracking-tight">
          Usage
        </h1>
        <p className="mt-0.5 text-sm text-[#71717A]">
          Current billing period: March 1–31, 2026.
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
            label="Storage Used"
            value={
              stats.storageGb > 0 ? `${stats.storageGb} GB` : "—"
            }
            subLabel={
              stats.storageGb === 0 ? "Metrics coming soon" : undefined
            }
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

      {/* Charts placeholder — requires CloudWatch integration */}
      <section aria-label="API call history">
        <div className="rounded-md border border-dashed border-[#3F3F46] bg-[#18181B]/50 px-6 py-10 flex flex-col items-center text-center">
          <div className="w-12 h-12 rounded-lg bg-[#111114] border border-[#27272A] flex items-center justify-center mb-4">
            <BarChart3
              className="w-6 h-6 text-[#71717A]"
              aria-hidden="true"
            />
          </div>
          <h2 className="text-sm font-semibold text-[#FAFAFA]">
            Usage charts coming soon
          </h2>
          <p className="mt-1.5 text-sm text-[#71717A] max-w-sm">
            Detailed API call volume, endpoint distribution, and storage
            breakdown charts will appear here once the CloudWatch metrics
            pipeline is connected.
          </p>
        </div>
      </section>

      {/* Cost estimate — estimated based on AWS pricing */}
      <section aria-label="Cost estimate">
        <div className="rounded-md border border-[#27272A] bg-[#18181B]">
          <div className="px-5 py-4 border-b border-[#27272A]">
            <h2 className="text-sm font-medium text-[#FAFAFA]">
              Cost Estimate
            </h2>
            <p className="text-xs text-[#71717A] mt-0.5">
              Estimated based on current usage and AWS pricing.
            </p>
          </div>

          <div className="overflow-x-auto">
            <table
              className="w-full text-sm"
              aria-label="Cost estimates by service"
            >
              <thead>
                <tr className="border-b border-[#27272A]">
                  <th
                    scope="col"
                    className="px-5 py-3 text-left text-[10px] font-medium text-[#71717A] uppercase tracking-wide"
                  >
                    Service
                  </th>
                  <th
                    scope="col"
                    className="px-5 py-3 text-left text-[10px] font-medium text-[#71717A] uppercase tracking-wide"
                  >
                    Detail
                  </th>
                  <th
                    scope="col"
                    className="px-5 py-3 text-right text-[10px] font-medium text-[#71717A] uppercase tracking-wide"
                  >
                    Estimated Cost
                  </th>
                </tr>
              </thead>
              <tbody>
                {mockCostEstimates.map((item) => (
                  <tr
                    key={item.service}
                    className="border-b border-[#27272A] last:border-0"
                  >
                    <td className="px-5 py-3 text-[#FAFAFA] font-medium">
                      {item.service}
                    </td>
                    <td className="px-5 py-3 text-[#71717A] text-xs">
                      {item.detail}
                    </td>
                    <td className="px-5 py-3 text-right font-mono text-[#A1A1AA]">
                      ~${item.cost.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t border-[#3F3F46]">
                  <td
                    colSpan={2}
                    className="px-5 py-3 text-sm font-semibold text-[#FAFAFA]"
                  >
                    Total
                  </td>
                  <td className="px-5 py-3 text-right font-mono font-semibold text-[#FAFAFA]">
                    ~${total.toFixed(2)}/month
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}
