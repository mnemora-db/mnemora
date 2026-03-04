/**
 * Server-side Mnemora data client.
 *
 * Fetches live data for the dashboard by:
 *  1. Calling the Mnemora API health endpoint (no auth required).
 *  2. Querying DynamoDB directly for agent / state data (server-side AWS creds).
 *
 * Why not use the user's API key?
 * ───────────────────────────────
 * Plaintext API keys are shown exactly once at creation and never stored —
 * only the SHA-256 hash lives in DynamoDB. Dashboard server components
 * therefore query DynamoDB directly via the AWS SDK rather than
 * authenticating through the HTTP API Gateway.
 */

import {
  DynamoDBClient,
  ScanCommand,
  GetItemCommand,
} from "@aws-sdk/client-dynamodb";
import { LambdaClient, InvokeCommand } from "@aws-sdk/client-lambda";
import type { Agent, UsageStat } from "./mock-data";

// ── Config ──────────────────────────────────────────────────────────
const MNEMORA_API_URL = process.env.MNEMORA_API_URL ?? "";
const STATE_TABLE = process.env.STATE_TABLE_NAME ?? "mnemora-state-dev";
const USERS_TABLE = process.env.USERS_TABLE_NAME ?? "mnemora-users-dev";

const ddb = new DynamoDBClient({
  region: process.env.AWS_REGION ?? "us-east-1",
});
const lambdaClient = new LambdaClient({
  region: process.env.AWS_REGION ?? "us-east-1",
});
const SEMANTIC_FUNCTION =
  process.env.SEMANTIC_FUNCTION_NAME ?? "mnemora-semantic-dev";

// ── Types ───────────────────────────────────────────────────────────

export interface ServiceHealth {
  label: string;
  status: "healthy" | "degraded" | "down";
}

export interface HealthStatus {
  ok: boolean;
  version: string;
  timestamp: string;
  services: ServiceHealth[];
  checkedAt: string;
}

// ── Health ──────────────────────────────────────────────────────────

const DOWN_SERVICES: ServiceHealth[] = [
  { label: "API Gateway", status: "down" },
  { label: "DynamoDB", status: "down" },
  { label: "Aurora (pgvector)", status: "down" },
  { label: "S3", status: "down" },
];

const HEALTHY_SERVICES: ServiceHealth[] = [
  { label: "API Gateway", status: "healthy" },
  { label: "DynamoDB", status: "healthy" },
  { label: "Aurora (pgvector)", status: "healthy" },
  { label: "S3", status: "healthy" },
];

/**
 * Check Mnemora API health via GET /v1/health.
 * Falls back to "down" status if the endpoint is unreachable.
 */
export async function getHealth(): Promise<HealthStatus> {
  const checkedAt = new Date().toISOString();

  if (!MNEMORA_API_URL) {
    return {
      ok: false,
      version: "unknown",
      timestamp: checkedAt,
      services: DOWN_SERVICES,
      checkedAt,
    };
  }

  try {
    const res = await fetch(`${MNEMORA_API_URL}/v1/health`, {
      cache: "no-store",
    });

    if (!res.ok) {
      return {
        ok: false,
        version: "unknown",
        timestamp: checkedAt,
        services: [
          { label: "API Gateway", status: "degraded" },
          { label: "DynamoDB", status: "healthy" },
          { label: "Aurora (pgvector)", status: "healthy" },
          { label: "S3", status: "healthy" },
        ],
        checkedAt,
      };
    }

    const json = await res.json();
    const data = json.data ?? {};

    return {
      ok: data.status === "ok",
      version: data.version ?? "unknown",
      timestamp: data.timestamp ?? checkedAt,
      services: HEALTHY_SERVICES,
      checkedAt,
    };
  } catch {
    return {
      ok: false,
      version: "unknown",
      timestamp: checkedAt,
      services: DOWN_SERVICES,
      checkedAt,
    };
  }
}

// ── Agents ──────────────────────────────────────────────────────────

/**
 * Fetch agents for a GitHub user from the DynamoDB state table.
 *
 * Scans for SESSION items whose PK starts with `github:<githubId>#`
 * and groups them by agent_id to build the agent list.
 * No META items are required — agents are derived from actual usage.
 */
export async function getAgents(githubId: string): Promise<Agent[]> {
  const tenantPrefix = `github:${githubId}#`;

  try {
    const result = await ddb.send(
      new ScanCommand({
        TableName: STATE_TABLE,
        FilterExpression: "begins_with(pk, :tp) AND begins_with(sk, :sess)",
        ExpressionAttributeValues: {
          ":tp": { S: tenantPrefix },
          ":sess": { S: "SESSION#" },
        },
        Limit: 1000,
      })
    );

    if (!result.Items?.length) return [];

    // Group sessions by agent_id (derived from PK)
    const agentMap = new Map<
      string,
      { sessions: number; lastActive: string; createdAt: string }
    >();

    for (const item of result.Items) {
      const pk = item.pk?.S ?? "";
      const agentId = pk.slice(tenantPrefix.length);
      if (!agentId) continue;

      const updatedAt =
        item.updated_at?.S ?? item.created_at?.S ?? new Date().toISOString();
      const createdAt = item.created_at?.S ?? new Date().toISOString();

      const existing = agentMap.get(agentId);
      if (existing) {
        existing.sessions += 1;
        if (updatedAt > existing.lastActive) existing.lastActive = updatedAt;
        if (createdAt < existing.createdAt) existing.createdAt = createdAt;
      } else {
        agentMap.set(agentId, {
          sessions: 1,
          lastActive: updatedAt,
          createdAt,
        });
      }
    }

    return Array.from(agentMap.entries()).map(([agentId, data]) => ({
      id: agentId,
      name: agentId,
      stateSessions: data.sessions,
      semanticCount: 0,
      episodeCount: 0,
      lastActive: data.lastActive,
      createdAt: data.createdAt,
      framework: "Unknown",
    }));
  } catch (error) {
    console.error("[mnemora-api] Failed to fetch agents:", error);
    return [];
  }
}

// ── Usage Stats ─────────────────────────────────────────────────────

/**
 * Derive usage stats from DynamoDB data.
 *
 * Reads real per-tenant API call counters from the users table
 * (populated by the auth Lambda on each authenticated request)
 * and session counts from the state table.
 */
export async function getUsageStats(githubId: string): Promise<UsageStat> {
  const agents = await getAgents(githubId);

  // Count state sessions for the tenant
  const tenantPrefix = `github:${githubId}#`;
  let totalSessions = 0;

  try {
    const result = await ddb.send(
      new ScanCommand({
        TableName: STATE_TABLE,
        FilterExpression: "begins_with(pk, :tp) AND begins_with(sk, :sess)",
        ExpressionAttributeValues: {
          ":tp": { S: tenantPrefix },
          ":sess": { S: "SESSION#" },
        },
        Select: "COUNT",
        Limit: 1000,
      })
    );
    totalSessions = result.Count ?? 0;
  } catch {
    // Swallow — stats will show 0
  }

  // Read real API call counters from the users table
  let apiCallsToday = 0;
  let apiCallsMonth = 0;
  try {
    const userResult = await ddb.send(
      new GetItemCommand({
        TableName: USERS_TABLE,
        Key: { github_id: { S: githubId } },
        ProjectionExpression:
          "api_calls_today, api_calls_month, last_call_date, last_call_month",
      })
    );
    const item = userResult.Item;
    if (item) {
      const today = new Date().toISOString().slice(0, 10);
      const storedDate = item.last_call_date?.S ?? "";
      // Only show today's count if the stored date matches today
      if (storedDate === today) {
        apiCallsToday = Number(item.api_calls_today?.N ?? "0");
      }
      const currentMonth = today.slice(0, 7);
      const storedMonth = item.last_call_month?.S ?? "";
      if (storedMonth === currentMonth) {
        apiCallsMonth = Number(item.api_calls_month?.N ?? "0");
      }
    }
  } catch {
    // Swallow — counters will show 0
  }

  return {
    apiCallsToday,
    apiCallsTodayDelta: 0,
    apiCallsMonth,
    storageGb: 0,
    activeAgents: agents.length,
    totalSessions,
  };
}

// ── Vector Count ─────────────────────────────────────────────────────

/**
 * Fetch vector count for a tenant by invoking the semantic Lambda directly.
 *
 * The dashboard cannot reach Aurora (private VPC), so we invoke the
 * semantic Lambda with a synthetic API Gateway event containing the
 * tenant_id in the authorizer context — the same path the real API
 * Gateway + Lambda authorizer would take.
 */
export async function getVectorCount(githubId: string): Promise<number> {
  const tenantId = `github:${githubId}`;

  try {
    const result = await lambdaClient.send(
      new InvokeCommand({
        FunctionName: SEMANTIC_FUNCTION,
        InvocationType: "RequestResponse",
        Payload: Buffer.from(
          JSON.stringify({
            requestContext: {
              http: { method: "GET", path: "/v1/usage/vectors" },
              requestId: `dashboard-vectors-${Date.now()}`,
              authorizer: { lambda: { tenantId } },
            },
            rawPath: "/v1/usage/vectors",
            headers: {},
          })
        ),
      })
    );

    if (result.Payload) {
      const response = JSON.parse(Buffer.from(result.Payload).toString());
      if (response.statusCode === 200) {
        const body = JSON.parse(response.body);
        return Number(body.data?.vector_count ?? 0);
      }
    }
  } catch (error) {
    console.error("[mnemora-api] Failed to fetch vector count:", error);
  }

  return 0;
}
