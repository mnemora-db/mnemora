/**
 * Server-side admin data-fetching module.
 *
 * Aggregates cross-tenant data from DynamoDB, CloudWatch, Lambda, RDS, and S3
 * for the Mnemora admin dashboard. All functions are server-only — they use
 * AWS SDK clients directly and must never be imported from client components.
 *
 * Every async function is wrapped in try/catch with graceful fallbacks so the
 * admin page never crashes due to a single data-source failure.
 */

import {
  DynamoDBClient,
  ScanCommand,
  DescribeTableCommand,
  type AttributeValue,
  type ScanCommandOutput,
} from "@aws-sdk/client-dynamodb";
import { LambdaClient, InvokeCommand } from "@aws-sdk/client-lambda";
import {
  CloudWatchClient,
  GetMetricStatisticsCommand,
} from "@aws-sdk/client-cloudwatch";
import { RDSClient, DescribeDBClustersCommand } from "@aws-sdk/client-rds";

// ── AWS Clients ──────────────────────────────────────────────────────────────

const REGION = process.env.AWS_REGION ?? "us-east-1";

const ddb = new DynamoDBClient({ region: REGION });
const lambdaClient = new LambdaClient({ region: REGION });
const cw = new CloudWatchClient({ region: REGION });
const rds = new RDSClient({ region: REGION });

// ── Table / Resource Names ───────────────────────────────────────────────────

const USERS_TABLE = process.env.USERS_TABLE_NAME ?? "mnemora-users-dev";
const STATE_TABLE = process.env.STATE_TABLE_NAME ?? "mnemora-state-dev";
const FEEDBACK_TABLE = process.env.FEEDBACK_TABLE_NAME ?? "mnemora-feedback-dev";

const LAMBDA_FUNCTIONS = [
  { name: "mnemora-health-dev", display: "Health" },
  { name: "mnemora-auth-dev", display: "Auth" },
  { name: "mnemora-state-dev", display: "State" },
  { name: "mnemora-semantic-dev", display: "Semantic" },
  { name: "mnemora-episodic-dev", display: "Episodic" },
  { name: "mnemora-unified-dev", display: "Unified" },
  { name: "mnemora-warmer-dev", display: "Warmer" },
] as const;

// ── Types ────────────────────────────────────────────────────────────────────

export interface AdminUser {
  githubId: string;
  githubUsername: string;
  email: string;
  tier: string;
  apiCallsToday: number;
  apiCallsMonth: number;
  createdAt: string;
  lastLogin: string;
}

export interface RevenueStats {
  totalUsers: number;
  payingUsers: number;
  mrr: number;
  freePercent: number;
  tierCounts: Record<string, number>;
}

export interface ApiUsageStats {
  totalCallsToday: number;
  totalCallsMonth: number;
  totalVectors: number;
  totalStateItems: number;
}

export interface LambdaFunctionMetric {
  functionName: string;
  displayName: string;
  invocationsToday: number;
  errorsToday: number;
  avgDurationMs: number;
}

export interface AuroraStatus {
  status: string;
  engine: string;
  minACU: number;
  maxACU: number;
}

export interface DynamoTableStat {
  name: string;
  displayName: string;
  itemCount: number;
  sizeBytes: number;
}

export interface BugReport {
  date: string;
  username: string;
  title: string;
  description: string;
  severity: string | null;
  githubIssueUrl: string | null;
}

export interface CostEstimate {
  service: string;
  usage: string;
  estimatedCost: number;
}

export interface AdminData {
  users: AdminUser[];
  revenue: RevenueStats;
  apiUsage: ApiUsageStats;
  lambdaMetrics: LambdaFunctionMetric[];
  aurora: AuroraStatus;
  dynamoTables: DynamoTableStat[];
  recentBugs: BugReport[];
  costs: CostEstimate[];
}

// ── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Returns today's date in YYYY-MM-DD format (UTC).
 */
function todayUTC(): string {
  return new Date().toISOString().slice(0, 10);
}

/**
 * Returns the current month in YYYY-MM format (UTC).
 */
function currentMonthUTC(): string {
  return new Date().toISOString().slice(0, 7);
}

/**
 * Returns a Date set to midnight UTC today.
 */
function midnightUTC(): Date {
  const d = new Date();
  d.setUTCHours(0, 0, 0, 0);
  return d;
}

// ── getAdminUsers ─────────────────────────────────────────────────────────────

/**
 * Full-scan the users table and return every user as an AdminUser.
 *
 * Stale-counter detection:
 * - api_calls_today is zeroed out when last_call_date does not match today.
 * - api_calls_month is zeroed out when last_call_month does not match the
 *   current calendar month.
 *
 * Results are sorted by lastLogin descending (most recent first).
 */
export async function getAdminUsers(): Promise<AdminUser[]> {
  const today = todayUTC();
  const currentMonth = currentMonthUTC();

  try {
    const users: AdminUser[] = [];
    let lastKey: Record<string, AttributeValue> | undefined = undefined;

    do {
      const result: ScanCommandOutput = await ddb.send(
        new ScanCommand({
          TableName: USERS_TABLE,
          ExclusiveStartKey: lastKey,
        })
      );

      for (const item of result.Items ?? []) {
        // Only process items that represent user records (have github_id)
        const githubId = item.github_id?.S;
        if (!githubId) continue;

        const lastCallDate = item.last_call_date?.S ?? "";
        const lastCallMonth = item.last_call_month?.S ?? "";

        const rawCallsToday = Number(item.api_calls_today?.N ?? "0");
        const rawCallsMonth = Number(item.api_calls_month?.N ?? "0");

        users.push({
          githubId,
          githubUsername: item.github_username?.S ?? "",
          email: item.email?.S ?? "",
          tier: item.tier?.S ?? "free",
          apiCallsToday: lastCallDate === today ? rawCallsToday : 0,
          apiCallsMonth: lastCallMonth === currentMonth ? rawCallsMonth : 0,
          createdAt: item.created_at?.S ?? "",
          lastLogin: item.last_login?.S ?? "",
        });
      }

      lastKey = result.LastEvaluatedKey;
    } while (lastKey !== undefined);

    // Sort by lastLogin descending; empty strings sort to the end
    users.sort((a, b) => {
      if (a.lastLogin === b.lastLogin) return 0;
      if (a.lastLogin === "") return 1;
      if (b.lastLogin === "") return -1;
      return b.lastLogin.localeCompare(a.lastLogin);
    });

    return users;
  } catch (error) {
    console.error("[admin] getAdminUsers failed:", error);
    return [];
  }
}

// ── getRevenueStats ────────────────────────────────────────────────────────────

/**
 * Compute revenue stats from a pre-fetched user list.
 *
 * MRR = (starter * $29) + (pro * $49) + (scale * $99)
 * Enterprise customers are counted as paying but excluded from MRR because
 * pricing is negotiated individually.
 */
export function getRevenueStats(users: AdminUser[]): RevenueStats {
  const total = users.length;

  const tierCounts: Record<string, number> = {};
  for (const user of users) {
    const tier = user.tier || "free";
    tierCounts[tier] = (tierCounts[tier] ?? 0) + 1;
  }

  const freeCount = tierCounts["free"] ?? 0;
  const starterCount = tierCounts["starter"] ?? 0;
  const proCount = tierCounts["pro"] ?? 0;
  const scaleCount = tierCounts["scale"] ?? 0;

  const mrr = starterCount * 29 + proCount * 49 + scaleCount * 99;
  const payingUsers = total - freeCount;
  const freePercent = total > 0 ? Math.round((freeCount / total) * 100) : 0;

  return {
    totalUsers: total,
    payingUsers,
    mrr,
    freePercent,
    tierCounts,
  };
}

// ── getAggregateApiUsage ──────────────────────────────────────────────────────

/**
 * Aggregate API call counters across all users and fetch infrastructure totals.
 *
 * Vector count: invokes the semantic Lambda with an admin-scoped synthetic
 * event (same pattern as the per-tenant getVectorCount in mnemora-api.ts).
 *
 * State item count: reads DynamoDB TableItemCount via DescribeTable.
 */
export async function getAggregateApiUsage(
  users: AdminUser[]
): Promise<ApiUsageStats> {
  let totalCallsToday = 0;
  let totalCallsMonth = 0;
  for (const user of users) {
    totalCallsToday += user.apiCallsToday;
    totalCallsMonth += user.apiCallsMonth;
  }

  // Vector count — invoke semantic Lambda with an admin sentinel tenant ID
  let totalVectors = 0;
  try {
    const result = await lambdaClient.send(
      new InvokeCommand({
        FunctionName: "mnemora-semantic-dev",
        InvocationType: "RequestResponse",
        Payload: Buffer.from(
          JSON.stringify({
            requestContext: {
              http: { method: "GET", path: "/v1/usage/vectors" },
              requestId: `admin-vectors-${Date.now()}`,
              authorizer: { lambda: { tenantId: "__admin_global__" } },
            },
            rawPath: "/v1/usage/vectors",
            headers: {},
          })
        ),
      })
    );

    if (result.Payload) {
      const raw = JSON.parse(Buffer.from(result.Payload).toString()) as {
        statusCode?: number;
        body?: string;
      };
      if (raw.statusCode === 200 && raw.body) {
        const body = JSON.parse(raw.body) as {
          data?: { vector_count?: number };
        };
        totalVectors = Number(body.data?.vector_count ?? 0);
      }
    }
  } catch (error) {
    console.error("[admin] getAggregateApiUsage — vector count failed:", error);
  }

  // State item count via DescribeTable
  let totalStateItems = 0;
  try {
    const tableResult = await ddb.send(
      new DescribeTableCommand({ TableName: STATE_TABLE })
    );
    totalStateItems = Number(tableResult.Table?.ItemCount ?? 0);
  } catch (error) {
    console.error(
      "[admin] getAggregateApiUsage — DescribeTable (state) failed:",
      error
    );
  }

  return {
    totalCallsToday,
    totalCallsMonth,
    totalVectors,
    totalStateItems,
  };
}

// ── getLambdaMetrics ─────────────────────────────────────────────────────────

/**
 * Query CloudWatch for invocations, errors, and average duration for each
 * Lambda function over the current UTC day.
 *
 * All 21 metric queries (7 functions × 3 metrics) are issued in parallel.
 * Individual query failures return 0 values rather than propagating.
 */
export async function getLambdaMetrics(): Promise<LambdaFunctionMetric[]> {
  const startTime = midnightUTC();
  const endTime = new Date();
  const period = 86400; // 1 day in seconds

  /**
   * Fetch a single CloudWatch metric sum or average for a Lambda function.
   * Returns 0 on error or when no datapoints exist.
   */
  async function fetchMetric(
    functionName: string,
    metricName: string,
    statistic: "Sum" | "Average"
  ): Promise<number> {
    try {
      const result = await cw.send(
        new GetMetricStatisticsCommand({
          Namespace: "AWS/Lambda",
          MetricName: metricName,
          Dimensions: [{ Name: "FunctionName", Value: functionName }],
          StartTime: startTime,
          EndTime: endTime,
          Period: period,
          Statistics: [statistic],
        })
      );

      if (!result.Datapoints?.length) return 0;

      const sorted = result.Datapoints.slice().sort(
        (a, b) =>
          (b.Timestamp?.getTime() ?? 0) - (a.Timestamp?.getTime() ?? 0)
      );

      const point = sorted[0];
      return statistic === "Sum"
        ? (point?.Sum ?? 0)
        : (point?.Average ?? 0);
    } catch {
      return 0;
    }
  }

  // Build all 21 queries up front so Promise.all fires them together
  const queries = LAMBDA_FUNCTIONS.map((fn) => ({
    fn,
    invocations: fetchMetric(fn.name, "Invocations", "Sum"),
    errors: fetchMetric(fn.name, "Errors", "Sum"),
    duration: fetchMetric(fn.name, "Duration", "Average"),
  }));

  const results = await Promise.all(
    queries.map(async (q) => ({
      functionName: q.fn.name,
      displayName: q.fn.display,
      invocationsToday: await q.invocations,
      errorsToday: await q.errors,
      avgDurationMs: await q.duration,
    }))
  );

  // Sort by invocations descending
  results.sort((a, b) => b.invocationsToday - a.invocationsToday);

  return results;
}

// ── getAuroraStatus ──────────────────────────────────────────────────────────

/**
 * Describe the Aurora Serverless v2 cluster and return key status fields.
 *
 * Falls back to an "unknown" record on any error so the admin page always
 * has a value to display.
 */
export async function getAuroraStatus(): Promise<AuroraStatus> {
  const fallback: AuroraStatus = {
    status: "unknown",
    engine: "unknown",
    minACU: 0,
    maxACU: 0,
  };

  try {
    const result = await rds.send(
      new DescribeDBClustersCommand({
        DBClusterIdentifier: "mnemora-db-dev",
      })
    );

    const cluster = result.DBClusters?.[0];
    if (!cluster) return fallback;

    const engineVersion = cluster.EngineVersion
      ? `${cluster.Engine ?? "aurora-postgresql"} ${cluster.EngineVersion}`
      : (cluster.Engine ?? "unknown");

    return {
      status: cluster.Status ?? "unknown",
      engine: engineVersion,
      minACU: cluster.ServerlessV2ScalingConfiguration?.MinCapacity ?? 0,
      maxACU: cluster.ServerlessV2ScalingConfiguration?.MaxCapacity ?? 0,
    };
  } catch (error) {
    console.error("[admin] getAuroraStatus failed:", error);
    return fallback;
  }
}

// ── getDynamoTableStats ───────────────────────────────────────────────────────

/**
 * DescribeTable for each tracked DynamoDB table in parallel.
 *
 * ItemCount and TableSizeBytes are updated approximately every 6 hours
 * by DynamoDB; values are not real-time but are accurate enough for an
 * admin overview.
 */
export async function getDynamoTableStats(): Promise<DynamoTableStat[]> {
  const tables: Array<{ name: string; displayName: string }> = [
    { name: STATE_TABLE, displayName: "State" },
    { name: USERS_TABLE, displayName: "Users" },
    { name: FEEDBACK_TABLE, displayName: "Feedback" },
  ];

  const results = await Promise.all(
    tables.map(async ({ name, displayName }) => {
      try {
        const result = await ddb.send(
          new DescribeTableCommand({ TableName: name })
        );
        return {
          name,
          displayName,
          itemCount: Number(result.Table?.ItemCount ?? 0),
          sizeBytes: Number(result.Table?.TableSizeBytes ?? 0),
        };
      } catch (error) {
        console.error(
          `[admin] getDynamoTableStats — DescribeTable failed for ${name}:`,
          error
        );
        return { name, displayName, itemCount: 0, sizeBytes: 0 };
      }
    })
  );

  return results;
}

// ── getRecentBugs ─────────────────────────────────────────────────────────────

/**
 * Scan the feedback table for bug reports, sorted by creation date descending.
 * Returns the 10 most recent bugs.
 */
export async function getRecentBugs(): Promise<BugReport[]> {
  try {
    const bugs: BugReport[] = [];
    let lastKey: Record<string, AttributeValue> | undefined = undefined;

    do {
      const result: ScanCommandOutput = await ddb.send(
        new ScanCommand({
          TableName: FEEDBACK_TABLE,
          FilterExpression: "#t = :bug",
          ExpressionAttributeNames: { "#t": "type" },
          ExpressionAttributeValues: { ":bug": { S: "bug" } },
          ExclusiveStartKey: lastKey,
        })
      );

      for (const item of result.Items ?? []) {
        bugs.push({
          date: item.created_at?.S ?? "",
          username: item.github_username?.S ?? "",
          title: item.title?.S ?? "",
          description: item.description?.S ?? "",
          severity: item.severity?.S ?? null,
          githubIssueUrl: item.github_issue_url?.S ?? null,
        });
      }

      lastKey = result.LastEvaluatedKey;
    } while (lastKey !== undefined);

    // Sort by date descending; empty strings sort to the end
    bugs.sort((a, b) => {
      if (a.date === b.date) return 0;
      if (a.date === "") return 1;
      if (b.date === "") return -1;
      return b.date.localeCompare(a.date);
    });

    return bugs.slice(0, 10);
  } catch (error) {
    console.error("[admin] getRecentBugs failed:", error);
    return [];
  }
}

// ── getEstimatedCosts ─────────────────────────────────────────────────────────

/**
 * Estimate the current month's AWS bill from known usage figures.
 *
 * All figures are approximations using public AWS pricing for us-east-1.
 * They are not a substitute for the AWS Cost Explorer.
 *
 * Pricing references (2026):
 * - Lambda: $0.0000002 per invocation (free tier not subtracted here)
 * - API Gateway HTTP API: $1.00 per 1M requests = $0.000001 per call
 * - DynamoDB on-demand: ~$0.25 per GB-month (rough blended read/write estimate)
 * - Aurora Serverless v2: $0.12 per ACU-hour; baseline 0.5 ACU × 730 h/month
 * - S3 Standard: $0.023 per GB-month
 */
export function getEstimatedCosts(
  lambdaMetrics: LambdaFunctionMetric[],
  apiCallsMonth: number,
  dynamoTables: DynamoTableStat[],
  storageMB: number
): CostEstimate[] {
  // Lambda — sum all invocations across all functions
  const totalInvocations = lambdaMetrics.reduce(
    (sum, fn) => sum + fn.invocationsToday,
    0
  );
  const lambdaCost = totalInvocations * 0.0000002;

  // API Gateway
  const apiGatewayCost = apiCallsMonth * 0.000001;

  // DynamoDB — total storage across all tables, on-demand rough estimate
  const totalDynamoBytes = dynamoTables.reduce(
    (sum, t) => sum + t.sizeBytes,
    0
  );
  const totalDynamoGB = totalDynamoBytes / (1024 * 1024 * 1024);
  const dynamoCost = totalDynamoGB * 0.25;

  // Aurora Serverless v2 — 0.5 ACU minimum × 730 hours × $0.12 per ACU-hour
  const auroraCost = 0.5 * 730 * 0.12;

  // S3
  const s3GB = storageMB / 1024;
  const s3Cost = s3GB * 0.023;

  return [
    {
      service: "Lambda",
      usage: `${totalInvocations.toLocaleString()} invocations today`,
      estimatedCost: Math.round(lambdaCost * 10000) / 10000,
    },
    {
      service: "API Gateway",
      usage: `${apiCallsMonth.toLocaleString()} requests this month`,
      estimatedCost: Math.round(apiGatewayCost * 10000) / 10000,
    },
    {
      service: "DynamoDB",
      usage: `${(totalDynamoGB * 1024).toFixed(1)} MB total table size`,
      estimatedCost: Math.round(dynamoCost * 10000) / 10000,
    },
    {
      service: "Aurora Serverless v2",
      usage: "0.5 ACU baseline × 730 h/month",
      estimatedCost: Math.round(auroraCost * 100) / 100,
    },
    {
      service: "S3",
      usage: `${storageMB.toFixed(1)} MB episode storage`,
      estimatedCost: Math.round(s3Cost * 10000) / 10000,
    },
  ];
}

// ── getAdminData ──────────────────────────────────────────────────────────────

/**
 * Fetch the full AdminData bundle for the admin dashboard.
 *
 * Execution plan:
 *   Phase 1 — fetch users (required by revenue + apiUsage)
 *   Phase 2 — fire remaining data sources in parallel
 *   Phase 3 — compute cost estimates from phase-2 results
 *
 * Any individual failure returns a safe fallback and is logged to CloudWatch
 * via console.error. The page will always have a complete AdminData shape.
 */
export async function getAdminData(): Promise<AdminData> {
  // Phase 1: users — required as input to revenue and apiUsage
  const users = await getAdminUsers();

  // Phase 2: everything that can run in parallel
  const [revenue, apiUsage, lambdaMetrics, aurora, dynamoTables, recentBugs] =
    await Promise.all([
      Promise.resolve(getRevenueStats(users)),
      getAggregateApiUsage(users),
      getLambdaMetrics(),
      getAuroraStatus(),
      getDynamoTableStats(),
      getRecentBugs(),
    ]);

  // Phase 3: cost estimate (pure computation — no async needed)
  const costs = getEstimatedCosts(
    lambdaMetrics,
    apiUsage.totalCallsMonth,
    dynamoTables,
    0 // storageMB: caller can pass S3 bytes if available; default to 0
  );

  return {
    users,
    revenue,
    apiUsage,
    lambdaMetrics,
    aurora,
    dynamoTables,
    recentBugs,
    costs,
  };
}
