/**
 * GET /api/usage/metrics — real usage metrics for the authenticated user.
 *
 * Returns per-tenant API call counts (from DynamoDB users table) and
 * aggregate storage metrics (from CloudWatch + DynamoDB DescribeTable).
 */

import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, GetCommand } from "@aws-sdk/lib-dynamodb";
import { getStorageMetrics } from "@/lib/cloudwatch";

const USERS_TABLE = process.env.USERS_TABLE_NAME ?? "mnemora-users-dev";
const ddbClient = new DynamoDBClient({
  region: process.env.AWS_REGION ?? "us-east-1",
});
const docClient = DynamoDBDocumentClient.from(ddbClient);

export async function GET() {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const githubId = session.user.id;

  // Fetch per-tenant counters + storage in parallel
  const [userResult, storage] = await Promise.all([
    docClient
      .send(
        new GetCommand({
          TableName: USERS_TABLE,
          Key: { github_id: githubId },
          ProjectionExpression:
            "api_calls_today, api_calls_month, last_call_date, last_call_month, tier",
        })
      )
      .catch(() => null),
    getStorageMetrics(),
  ]);

  const item = userResult?.Item ?? {};

  // Check if counters need reset (date/month mismatch)
  const now = new Date();
  const today = now.toISOString().slice(0, 10); // YYYY-MM-DD
  const month = now.toISOString().slice(0, 7); // YYYY-MM

  let apiCallsToday = Number(item.api_calls_today ?? 0);
  let apiCallsMonth = Number(item.api_calls_month ?? 0);

  // If stored date doesn't match today, the counter hasn't been reset yet
  if (item.last_call_date && item.last_call_date !== today) {
    apiCallsToday = 0;
  }
  if (item.last_call_month && item.last_call_month !== month) {
    apiCallsMonth = 0;
  }

  return NextResponse.json({
    apiCallsToday,
    apiCallsMonth,
    storageUsedMB: storage.storageUsedMB,
    tier: item.tier ?? "free",
  });
}
