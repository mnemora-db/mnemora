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

import { DynamoDBClient, ScanCommand } from "@aws-sdk/client-dynamodb";
import type { Agent, UsageStat } from "./mock-data";

// ── Config ──────────────────────────────────────────────────────────
const MNEMORA_API_URL = process.env.MNEMORA_API_URL ?? "";
const STATE_TABLE = process.env.STATE_TABLE_NAME ?? "mnemora-state-dev";

const ddb = new DynamoDBClient({
  region: process.env.AWS_REGION ?? "us-east-1",
});

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
      next: { revalidate: 30 },
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
 * Scans for META items whose PK starts with `github:<githubId>#`.
 * Returns an empty array when no agents have been registered yet.
 */
export async function getAgents(githubId: string): Promise<Agent[]> {
  const tenantPrefix = `github:${githubId}#`;

  try {
    const result = await ddb.send(
      new ScanCommand({
        TableName: STATE_TABLE,
        FilterExpression: "begins_with(PK, :tp) AND SK = :meta",
        ExpressionAttributeValues: {
          ":tp": { S: tenantPrefix },
          ":meta": { S: "META" },
        },
        Limit: 100,
      })
    );

    if (!result.Items?.length) return [];

    return result.Items.map((item) => {
      const pk = item.PK?.S ?? "";
      const agentId = pk.slice(tenantPrefix.length);

      return {
        id: agentId,
        name: item.display_name?.S ?? item.name?.S ?? agentId,
        stateSessions: Number(item.state_sessions?.N ?? "0"),
        semanticCount: Number(item.semantic_count?.N ?? "0"),
        episodeCount: Number(item.episode_count?.N ?? "0"),
        lastActive:
          item.updated_at?.S ?? item.created_at?.S ?? new Date().toISOString(),
        createdAt: item.created_at?.S ?? new Date().toISOString(),
        framework: item.framework?.S ?? "Unknown",
      };
    });
  } catch (error) {
    console.error("[mnemora-api] Failed to fetch agents:", error);
    return [];
  }
}

// ── Usage Stats ─────────────────────────────────────────────────────

/**
 * Derive basic usage stats from DynamoDB data.
 *
 * API call counts, storage metrics, and cost breakdowns require
 * CloudWatch integration (planned). Returns zeros for those fields
 * until the metrics pipeline is wired up.
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
        FilterExpression: "begins_with(PK, :tp) AND begins_with(SK, :sess)",
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

  return {
    apiCallsToday: 0,
    apiCallsTodayDelta: 0,
    apiCallsMonth: 0,
    storageGb: 0,
    activeAgents: agents.length,
    totalSessions,
  };
}
