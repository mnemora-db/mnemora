import { NextResponse } from "next/server";
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, UpdateCommand } from "@aws-sdk/lib-dynamodb";
import { VALID_TIERS } from "@/lib/tiers";

// ── Config ──────────────────────────────────────────────────────────

const TABLE_NAME = process.env.USERS_TABLE_NAME ?? "mnemora-users-dev";
const ADMIN_GITHUB_ID = "isaacgbc";

const ddbClient = new DynamoDBClient({
  region: process.env.AWS_REGION ?? "us-east-1",
});
const docClient = DynamoDBDocumentClient.from(ddbClient);

// ── POST /api/admin/upgrade ─────────────────────────────────────────

/**
 * Admin-only endpoint for manually setting a user's tier.
 *
 * Body: { github_id: string, tier: string }
 *
 * Use this as a fallback when the Creala webhook doesn't fire
 * or when granting enterprise access manually.
 */
export async function POST(request: Request) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.name || session.user.name !== ADMIN_GITHUB_ID) {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  const body = await request.json();
  const { github_id, tier } = body as { github_id?: string; tier?: string };

  if (!github_id || typeof github_id !== "string") {
    return NextResponse.json(
      { error: "Missing or invalid github_id" },
      { status: 400 }
    );
  }

  if (!tier || !VALID_TIERS.includes(tier)) {
    return NextResponse.json(
      { error: `Invalid tier. Must be one of: ${VALID_TIERS.join(", ")}` },
      { status: 400 }
    );
  }

  const now = new Date().toISOString();

  await docClient.send(
    new UpdateCommand({
      TableName: TABLE_NAME,
      Key: { github_id },
      UpdateExpression:
        "SET tier = :tier, tier_updated_at = :now, updated_at = :now",
      ExpressionAttributeValues: {
        ":tier": tier,
        ":now": now,
      },
    })
  );

  return NextResponse.json({ success: true, github_id, tier });
}
