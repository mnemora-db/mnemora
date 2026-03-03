import { NextResponse } from "next/server";
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import {
  DynamoDBDocumentClient,
  PutCommand,
  ScanCommand,
  UpdateCommand,
} from "@aws-sdk/lib-dynamodb";
import crypto from "crypto";

const TABLE_NAME = process.env.FEEDBACK_TABLE_NAME ?? "mnemora-feedback-dev";
const GITHUB_TOKEN = process.env.GITHUB_TOKEN ?? "";
const GITHUB_REPO = "mnemora-db/mnemora";
const ADMIN_GITHUB_ID = "isaacgbc";

const ddbClient = new DynamoDBClient({
  region: process.env.AWS_REGION ?? "us-east-1",
});
const docClient = DynamoDBDocumentClient.from(ddbClient);

// ── Label mapping ───────────────────────────────────────────────────
const LABEL_MAP: Record<string, string[]> = {
  bug: ["bug"],
  feature: ["enhancement"],
  feedback: ["feedback"],
};

const SEVERITY_EMOJI: Record<string, string> = {
  critical: "\u{1F534}",
  major: "\u{1F7E0}",
  minor: "\u{1F7E2}",
};

// ── Helpers ─────────────────────────────────────────────────────────

function buildIssueTitle(type: string, title: string): string {
  const prefix =
    type === "bug" ? "[Bug]" : type === "feature" ? "[Feature]" : "[Feedback]";
  return `${prefix} ${title}`;
}

function buildIssueBody(data: Record<string, unknown>): string {
  const lines: string[] = [];

  if (data.type === "bug") {
    lines.push(`**Description**`);
    lines.push(String(data.description || "_No description provided._"));
    lines.push("");
    if (data.steps_to_reproduce) {
      lines.push(`**Steps to Reproduce**`);
      lines.push(String(data.steps_to_reproduce));
      lines.push("");
    }
    const sev = String(data.severity ?? "minor");
    lines.push(
      `**Severity:** ${SEVERITY_EMOJI[sev] ?? ""} ${sev}`
    );
  } else if (data.type === "feature") {
    lines.push(`**Description**`);
    lines.push(String(data.description || "_No description provided._"));
    lines.push("");
    if (data.use_case) {
      lines.push(`**Use Case**`);
      lines.push(String(data.use_case));
    }
  } else {
    lines.push(String(data.description || "_No feedback provided._"));
    if (data.rating) {
      const stars = "\u2B50".repeat(Number(data.rating));
      lines.push("");
      lines.push(`**Rating:** ${stars} (${data.rating}/5)`);
    }
  }

  lines.push("");
  lines.push("---");
  lines.push(
    `Submitted by **@${data.github_username ?? "unknown"}** | Tier: \`${data.tier ?? "free"}\``
  );

  return lines.join("\n");
}

async function createGitHubIssue(
  title: string,
  body: string,
  labels: string[]
): Promise<{ url: string; number: number } | null> {
  if (!GITHUB_TOKEN) return null;

  try {
    const res = await fetch(
      `https://api.github.com/repos/${GITHUB_REPO}/issues`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${GITHUB_TOKEN}`,
          Accept: "application/vnd.github+json",
          "Content-Type": "application/json",
          "X-GitHub-Api-Version": "2022-11-28",
        },
        body: JSON.stringify({ title, body, labels }),
      }
    );

    if (!res.ok) {
      console.error(
        "[feedback] GitHub issue creation failed:",
        res.status,
        await res.text()
      );
      return null;
    }

    const issue = await res.json();
    return { url: issue.html_url, number: issue.number };
  } catch (err) {
    console.error("[feedback] GitHub API error:", err);
    return null;
  }
}

// ── POST /api/feedback ──────────────────────────────────────────────

/**
 * Submit feedback.
 *
 * Creates a DynamoDB record and a GitHub issue, then links them.
 */
export async function POST(request: Request) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json();
  const { type, title, description, severity, rating, steps_to_reproduce, use_case } =
    body as Record<string, unknown>;

  if (!type || !["bug", "feature", "feedback"].includes(String(type))) {
    return NextResponse.json(
      { error: "Invalid feedback type" },
      { status: 400 }
    );
  }

  const feedbackId = crypto.randomUUID();
  const now = new Date().toISOString();
  const githubUsername = session.user.name ?? "unknown";

  // 1. Store in DynamoDB
  const item: Record<string, unknown> = {
    feedback_id: feedbackId,
    type: String(type),
    created_at: now,
    github_id: session.user.id,
    github_username: githubUsername,
    title: String(title ?? ""),
    description: String(description ?? ""),
    severity: severity ? String(severity) : null,
    rating: rating ? Number(rating) : null,
    steps_to_reproduce: steps_to_reproduce ? String(steps_to_reproduce) : null,
    use_case: use_case ? String(use_case) : null,
    tier: "free",
    github_issue_url: null,
    github_issue_number: null,
  };

  await docClient.send(
    new PutCommand({ TableName: TABLE_NAME, Item: item })
  );

  // 2. Create GitHub issue
  const issueTitle = buildIssueTitle(String(type), String(title ?? "General feedback"));
  const issueBody = buildIssueBody({ ...item, github_username: githubUsername });
  const labels = LABEL_MAP[String(type)] ?? ["feedback"];

  const issue = await createGitHubIssue(issueTitle, issueBody, labels);

  // 3. Update DynamoDB with issue link
  if (issue) {
    await docClient.send(
      new UpdateCommand({
        TableName: TABLE_NAME,
        Key: { feedback_id: feedbackId },
        UpdateExpression:
          "SET github_issue_url = :url, github_issue_number = :num",
        ExpressionAttributeValues: {
          ":url": issue.url,
          ":num": issue.number,
        },
      })
    );
  }

  return NextResponse.json({
    success: true,
    feedback_id: feedbackId,
    issue_url: issue?.url ?? null,
  });
}

// ── GET /api/feedback ───────────────────────────────────────────────

/**
 * List all feedback (admin only).
 */
export async function GET() {
  const session = await getServerSession(authOptions);
  if (!session?.user?.name || session.user.name !== ADMIN_GITHUB_ID) {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  const result = await docClient.send(
    new ScanCommand({ TableName: TABLE_NAME, Limit: 200 })
  );

  // Sort by created_at descending
  const items = (result.Items ?? []).sort((a, b) =>
    String(b.created_at ?? "").localeCompare(String(a.created_at ?? ""))
  );

  return NextResponse.json({ items });
}
