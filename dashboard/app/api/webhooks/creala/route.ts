import { NextResponse } from "next/server";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import {
  DynamoDBDocumentClient,
  QueryCommand,
  UpdateCommand,
} from "@aws-sdk/lib-dynamodb";
import crypto from "crypto";

// ── Config ──────────────────────────────────────────────────────────

const TABLE_NAME = process.env.USERS_TABLE_NAME ?? "mnemora-users-dev";
const WEBHOOK_SECRET = process.env.CREALA_WEBHOOK_SECRET ?? "";

const ddbClient = new DynamoDBClient({
  region: process.env.AWS_REGION ?? "us-east-1",
});
const docClient = DynamoDBDocumentClient.from(ddbClient);

// ── Product → tier mapping ──────────────────────────────────────────

const PRODUCT_TIER_MAP: Record<string, string> = {
  "starter-mnemora": "starter",
  "pro-mnemora": "pro",
  "scale-mnemora": "scale",
};

/**
 * Derive tier from a product name/slug.
 * Matches if the product name contains "starter", "pro", or "scale".
 */
function deriveTier(productName: string): string {
  const lower = productName.toLowerCase();

  // Exact slug match first
  if (PRODUCT_TIER_MAP[lower]) return PRODUCT_TIER_MAP[lower];

  // Substring match
  if (lower.includes("starter")) return "starter";
  if (lower.includes("scale")) return "scale";
  if (lower.includes("pro")) return "pro";

  return "free";
}

// ── Signature verification ──────────────────────────────────────────

/**
 * Verify HMAC-SHA256 signature from Creala webhook.
 */
function verifySignature(body: string, signature: string): boolean {
  if (!WEBHOOK_SECRET || !signature) return false;

  const expected = crypto
    .createHmac("sha256", WEBHOOK_SECRET)
    .update(body)
    .digest("hex");

  try {
    return crypto.timingSafeEqual(
      Buffer.from(expected, "hex"),
      Buffer.from(signature, "hex")
    );
  } catch {
    return false;
  }
}

// ── Helpers ─────────────────────────────────────────────────────────

/**
 * Find a user record by email using the email-index GSI.
 */
async function findUserByEmail(
  email: string
): Promise<Record<string, unknown> | null> {
  const result = await docClient.send(
    new QueryCommand({
      TableName: TABLE_NAME,
      IndexName: "email-index",
      KeyConditionExpression: "email = :email",
      ExpressionAttributeValues: { ":email": email },
      Limit: 1,
    })
  );
  return (result.Items?.[0] as Record<string, unknown>) ?? null;
}

// ── POST /api/webhooks/creala ───────────────────────────────────────

/**
 * Receive Creala webhook events for subscription lifecycle.
 *
 * Events handled:
 * - new_subscription: activate paid tier
 * - subscription_renewal: confirm tier stays active
 * - subscription_cancellation: downgrade to free
 * - payment_failed: downgrade to free
 */
export async function POST(request: Request) {
  const rawBody = await request.text();
  const signature = request.headers.get("x-webhook-signature") ?? "";

  // 1. Verify HMAC signature
  if (!verifySignature(rawBody, signature)) {
    console.error("[creala-webhook] Invalid signature");
    return NextResponse.json({ error: "Invalid signature" }, { status: 401 });
  }

  // 2. Parse payload
  let payload: Record<string, unknown>;
  try {
    payload = JSON.parse(rawBody);
  } catch {
    console.error("[creala-webhook] Malformed JSON body");
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const event = String(payload.event ?? payload.type ?? "unknown");
  const data = (payload.data ?? payload) as Record<string, unknown>;

  // Extract fields — handle various Creala payload shapes
  const email = String(
    data.email ?? data.customerEmail ?? data.customer_email ?? ""
  );
  const productName = String(
    data.productName ??
      data.product_name ??
      data.productSlug ??
      data.product_slug ??
      ""
  );
  const saleId = String(data.saleId ?? data.sale_id ?? data.id ?? "");

  console.log(
    `[creala-webhook] event=${event} email=${email} product=${productName} saleId=${saleId}`
  );

  if (!email) {
    console.warn("[creala-webhook] No customer email in payload");
    return NextResponse.json({ received: true, matched: false });
  }

  // 3. Find user by email
  const user = await findUserByEmail(email);
  if (!user) {
    console.warn(
      `[creala-webhook] No user found for email: ${email}`
    );
    return NextResponse.json({ received: true, matched: false });
  }

  const githubId = String(user.github_id);

  // 4. Determine new tier
  let newTier: string;
  if (
    event === "subscription_cancellation" ||
    event === "cancellation"
  ) {
    newTier = "free";
  } else if (event === "payment_failed") {
    newTier = "free";
    console.warn(
      `[creala-webhook] Payment failed for user ${githubId}, downgrading to free`
    );
  } else {
    // new_subscription, subscription_renewal, or other purchase events
    newTier = deriveTier(productName);
  }

  // 5. Update user record (idempotent via ConditionExpression)
  const now = new Date().toISOString();
  try {
    await docClient.send(
      new UpdateCommand({
        TableName: TABLE_NAME,
        Key: { github_id: githubId },
        UpdateExpression:
          "SET tier = :tier, last_sale_id = :sid, creala_customer_email = :ce, tier_updated_at = :now, updated_at = :now",
        ConditionExpression:
          "attribute_not_exists(last_sale_id) OR last_sale_id <> :sid",
        ExpressionAttributeValues: {
          ":tier": newTier,
          ":sid": saleId,
          ":ce": email,
          ":now": now,
        },
      })
    );
  } catch (err: unknown) {
    const error = err as { name?: string };
    if (error.name === "ConditionalCheckFailedException") {
      console.log(
        `[creala-webhook] Duplicate saleId ${saleId} for user ${githubId}, skipping`
      );
      return NextResponse.json({ received: true, duplicate: true });
    }
    throw err;
  }

  console.log(
    `[creala-webhook] Updated user ${githubId} to tier "${newTier}" (event: ${event})`
  );

  return NextResponse.json({ received: true, tier: newTier });
}
