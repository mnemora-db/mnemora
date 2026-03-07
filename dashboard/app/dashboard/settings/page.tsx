import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, GetCommand } from "@aws-sdk/lib-dynamodb";
import {
  TIER_LIMITS,
  TIER_BADGE_COLORS,
} from "@/lib/tiers";
import Image from "next/image";
import Link from "next/link";
import { KeyRound, AlertTriangle, User } from "lucide-react";

const USERS_TABLE = process.env.USERS_TABLE_NAME ?? "mnemora-users-dev";

const ddbClient = new DynamoDBClient({
  region: process.env.AWS_REGION ?? "us-east-1",
});
const docClient = DynamoDBDocumentClient.from(ddbClient);

async function getUserRecord(
  githubId: string
): Promise<Record<string, unknown> | null> {
  const result = await docClient.send(
    new GetCommand({
      TableName: USERS_TABLE,
      Key: { github_id: githubId },
      ProjectionExpression: "tier, email, github_username, created_at",
    })
  );
  return (result.Item as Record<string, unknown>) ?? null;
}

export default async function SettingsPage() {
  const session = await getServerSession(authOptions);
  const githubId = session?.user?.id ?? "";
  const userName = session?.user?.name ?? "Unknown";
  const userEmail = session?.user?.email ?? "";
  const avatarUrl = session?.user?.image ?? "";

  const userRecord = await getUserRecord(githubId);
  const currentTier = String(userRecord?.tier ?? "free");
  const tierInfo = TIER_LIMITS[currentTier] ?? TIER_LIMITS.free;
  const badgeColor =
    TIER_BADGE_COLORS[currentTier] ?? TIER_BADGE_COLORS.free;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-[22px] font-semibold text-[#FAFAFA] tracking-tight">
          Settings
        </h1>
        <p className="mt-0.5 text-sm text-[#71717A]">
          Manage your account and preferences.
        </p>
      </div>

      {/* Profile section */}
      <section aria-label="Profile">
        <div className="rounded-md border border-[#27272A] bg-[#18181B] px-5 py-5">
          <p className="text-xs font-medium text-[#71717A] uppercase tracking-wide mb-4">
            Profile
          </p>
          <div className="flex items-center gap-4">
            {avatarUrl ? (
              <Image
                src={avatarUrl}
                alt={userName}
                width={48}
                height={48}
                className="rounded-full border border-[#3F3F46]"
              />
            ) : (
              <div className="w-12 h-12 rounded-full bg-[#27272A] border border-[#3F3F46] flex items-center justify-center">
                <User className="w-6 h-6 text-[#71717A]" />
              </div>
            )}
            <div className="min-w-0">
              <p className="text-sm font-semibold text-[#FAFAFA] truncate">
                {userName}
              </p>
              <p className="text-xs text-[#A1A1AA] truncate">{userEmail}</p>
              <p className="text-xs text-[#71717A] truncate mt-0.5">
                GitHub ID: {githubId}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Current tier */}
      <section aria-label="Current tier">
        <div className="rounded-md border border-[#27272A] bg-[#18181B] px-5 py-5">
          <p className="text-xs font-medium text-[#71717A] uppercase tracking-wide mb-4">
            Current Plan
          </p>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-lg font-semibold text-[#FAFAFA]">
                {tierInfo.label}
              </p>
              <p className="text-xs text-[#71717A] mt-0.5">
                {tierInfo.apiCallsPerDay} API calls/day &middot;{" "}
                {tierInfo.storage} storage &middot; {tierInfo.agents} agent
                {tierInfo.agents === "1" ? "" : "s"}
              </p>
            </div>
            <span
              className={`px-2.5 py-1 rounded-md text-xs font-semibold uppercase tracking-wide border ${badgeColor}`}
            >
              {tierInfo.label}
            </span>
          </div>
          <Link
            href="/dashboard/billing"
            className="inline-block mt-4 text-xs font-medium text-[#2DD4BF] hover:text-[#2DD4BF]/80 transition-colors"
          >
            Manage billing &rarr;
          </Link>
        </div>
      </section>

      {/* API Keys */}
      <section aria-label="API keys">
        <div className="rounded-md border border-[#27272A] bg-[#18181B] px-5 py-5">
          <p className="text-xs font-medium text-[#71717A] uppercase tracking-wide mb-4">
            API Keys
          </p>
          <p className="text-sm text-[#A1A1AA]">
            Create and manage API keys for authenticating with the Mnemora API.
          </p>
          <Link
            href="/dashboard/api-keys"
            className="inline-flex items-center gap-2 mt-4 px-4 py-2 rounded-md border border-[#27272A] text-xs font-semibold text-[#A1A1AA] hover:text-[#FAFAFA] hover:border-[#3F3F46] transition-colors"
          >
            <KeyRound className="w-3.5 h-3.5" />
            Manage API Keys
          </Link>
        </div>
      </section>

      {/* Danger zone */}
      <section aria-label="Danger zone">
        <div className="rounded-md border border-red-500/20 bg-[#18181B] px-5 py-5">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <p className="text-xs font-medium text-red-400 uppercase tracking-wide">
              Danger Zone
            </p>
          </div>
          <p className="text-sm text-[#A1A1AA]">
            Permanently delete your account and all associated data. This action
            cannot be undone.
          </p>
          <button
            disabled
            className="inline-flex items-center gap-2 mt-4 px-4 py-2 rounded-md border border-red-500/20 text-xs font-semibold text-red-400/50 cursor-not-allowed"
          >
            Delete Account
          </button>
          <p className="mt-2 text-xs text-[#71717A]">
            To delete your account, contact{" "}
            <a
              href="mailto:isaacgbc@gmail.com"
              className="text-[#2DD4BF] hover:text-[#2DD4BF]/80 transition-colors"
            >
              isaacgbc@gmail.com
            </a>
          </p>
        </div>
      </section>
    </div>
  );
}
