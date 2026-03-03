import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, GetCommand } from "@aws-sdk/lib-dynamodb";
import {
  TIER_LIMITS,
  TIER_BADGE_COLORS,
  CREALA_LINKS,
} from "@/lib/tiers";
import { Check, ArrowUpRight, Mail } from "lucide-react";

// ── Config ──────────────────────────────────────────────────────────

const USERS_TABLE = process.env.USERS_TABLE_NAME ?? "mnemora-users-dev";

const ddbClient = new DynamoDBClient({
  region: process.env.AWS_REGION ?? "us-east-1",
});
const docClient = DynamoDBDocumentClient.from(ddbClient);

// ── Helpers ─────────────────────────────────────────────────────────

async function getUserRecord(
  githubId: string
): Promise<Record<string, unknown> | null> {
  const result = await docClient.send(
    new GetCommand({
      TableName: USERS_TABLE,
      Key: { github_id: githubId },
      ProjectionExpression:
        "tier, tier_updated_at, email, github_username, creala_customer_email",
    })
  );
  return (result.Item as Record<string, unknown>) ?? null;
}

const TIER_INDEX: Record<string, number> = {
  free: 0,
  starter: 1,
  pro: 2,
  scale: 3,
  enterprise: 4,
};

// ── Page ────────────────────────────────────────────────────────────

export default async function BillingPage() {
  const session = await getServerSession(authOptions);
  const githubId = session?.user?.id ?? "";

  const userRecord = await getUserRecord(githubId);
  const currentTier = String(userRecord?.tier ?? "free");
  const tierInfo = TIER_LIMITS[currentTier] ?? TIER_LIMITS.free;
  const badgeColor =
    TIER_BADGE_COLORS[currentTier] ?? TIER_BADGE_COLORS.free;
  const tierUpdatedAt = userRecord?.tier_updated_at
    ? new Date(String(userRecord.tier_updated_at)).toLocaleDateString(
        "en-US",
        { year: "numeric", month: "long", day: "numeric" }
      )
    : null;

  const currentIndex = TIER_INDEX[currentTier] ?? 0;

  const paidPlans = (["starter", "pro", "scale"] as const).map((key) => ({
    key,
    ...TIER_LIMITS[key],
    link: CREALA_LINKS[key],
    index: TIER_INDEX[key],
  }));

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-[22px] font-semibold text-[#FAFAFA] tracking-tight">
          Billing
        </h1>
        <p className="mt-0.5 text-sm text-[#71717A]">
          Manage your subscription and usage limits.
        </p>
      </div>

      {/* Current plan card */}
      <section aria-label="Current plan">
        <div className="rounded-md border border-[#27272A] bg-[#18181B] px-5 py-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-xs font-medium text-[#71717A] uppercase tracking-wide">
                Current Plan
              </p>
              <p className="mt-1 text-xl font-semibold text-[#FAFAFA]">
                {tierInfo.label}
              </p>
              {tierUpdatedAt && currentTier !== "free" && (
                <p className="mt-0.5 text-xs text-[#71717A]">
                  Active since {tierUpdatedAt}
                </p>
              )}
            </div>
            <span
              className={`px-2.5 py-1 rounded-md text-xs font-semibold uppercase tracking-wide border ${badgeColor}`}
            >
              {tierInfo.label}
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            {[
              { label: "API calls/day", value: tierInfo.apiCallsPerDay },
              { label: "Storage", value: tierInfo.storage },
              { label: "Vectors", value: tierInfo.vectors },
              { label: "Agents", value: tierInfo.agents },
              { label: "Support", value: tierInfo.support },
            ].map((stat) => (
              <div
                key={stat.label}
                className="rounded-md bg-[#111114] border border-[#27272A] px-3 py-2.5"
              >
                <p className="text-[10px] font-medium text-[#71717A] uppercase tracking-wide">
                  {stat.label}
                </p>
                <p className="mt-0.5 text-sm font-semibold text-[#FAFAFA]">
                  {stat.value}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Plan comparison */}
      <section aria-label="Available plans">
        <h2 className="text-sm font-medium text-[#FAFAFA] mb-3">
          {currentTier === "free" ? "Upgrade your plan" : "Available plans"}
        </h2>
        <div className="grid sm:grid-cols-3 gap-4">
          {paidPlans.map((plan) => {
            const isCurrent = plan.key === currentTier;
            const isUpgrade = plan.index > currentIndex;
            const isDowngrade = plan.index < currentIndex;

            return (
              <div
                key={plan.key}
                className={`relative rounded-xl p-px ${
                  plan.key === "pro"
                    ? "bg-gradient-to-b from-[#2DD4BF]/30 via-[#27272A] to-[#A78BFA]/20"
                    : "bg-gradient-to-b from-[#27272A] to-[#27272A]"
                }`}
              >
                <div className="rounded-[11px] bg-[#111114] p-5 flex flex-col h-full">
                  {plan.key === "pro" && (
                    <div className="absolute -top-px left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-b-md bg-[#2DD4BF] text-[#09090B] text-[10px] font-bold">
                      Most popular
                    </div>
                  )}

                  <div className="mb-4 mt-1">
                    <h3 className="text-sm font-semibold text-[#FAFAFA]">
                      {plan.label}
                    </h3>
                    <div className="flex items-baseline gap-1 mt-1">
                      <span className="text-2xl font-bold text-[#FAFAFA]">
                        ${plan.price}
                      </span>
                      <span className="text-xs text-[#52525B]">/month</span>
                    </div>
                  </div>

                  <ul className="space-y-2 mb-5 flex-1">
                    {[
                      `${plan.apiCallsPerDay} API calls/day`,
                      `${plan.agents} agents`,
                      `${plan.storage} storage`,
                      `${plan.vectors} vectors`,
                      `${plan.support} support`,
                    ].map((f) => (
                      <li
                        key={f}
                        className="flex items-start gap-2 text-xs text-[#A1A1AA]"
                      >
                        <Check className="w-3.5 h-3.5 text-[#2DD4BF] shrink-0 mt-0.5" />
                        {f}
                      </li>
                    ))}
                  </ul>

                  {isCurrent ? (
                    <span className="w-full text-center py-2 rounded-lg text-xs font-semibold bg-[#27272A] text-[#71717A] border border-[#3F3F46]">
                      Current plan
                    </span>
                  ) : isUpgrade ? (
                    <a
                      href={plan.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={`w-full text-center py-2 rounded-lg text-xs font-semibold transition-all duration-150 flex items-center justify-center gap-1.5 ${
                        plan.key === "pro"
                          ? "bg-[#2DD4BF] text-[#09090B] hover:bg-[#2DD4BF]/90"
                          : "border border-[#2DD4BF]/30 text-[#2DD4BF] hover:bg-[#2DD4BF]/10"
                      }`}
                    >
                      Upgrade
                      <ArrowUpRight className="w-3 h-3" />
                    </a>
                  ) : isDowngrade ? (
                    <span className="w-full text-center py-2 rounded-lg text-xs text-[#52525B]">
                      Downgrade takes effect next billing period
                    </span>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Enterprise callout */}
      <section aria-label="Enterprise plan">
        <div className="rounded-md border border-[#27272A] bg-[#18181B] px-5 py-5">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h3 className="text-sm font-semibold text-[#FAFAFA]">
                Need more?
              </h3>
              <p className="mt-1 text-xs text-[#71717A] max-w-md">
                Enterprise plans include unlimited everything, custom SLA,
                SSO/SAML, VPC peering, and dedicated infrastructure.
              </p>
            </div>
            <a
              href="mailto:isaacgbc@gmail.com"
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-[#27272A] text-xs font-semibold text-[#A1A1AA] hover:text-[#FAFAFA] hover:border-[#3F3F46] transition-colors whitespace-nowrap"
            >
              <Mail className="w-3.5 h-3.5" />
              Contact us
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}
