import { NextResponse } from "next/server";
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import {
  DynamoDBDocumentClient,
  GetCommand,
  PutCommand,
  UpdateCommand,
} from "@aws-sdk/lib-dynamodb";
import crypto from "crypto";

const TABLE_NAME = process.env.USERS_TABLE_NAME ?? "mnemora-users-dev";

const ddbClient = new DynamoDBClient({
  region: process.env.AWS_REGION ?? "us-east-1",
});
const docClient = DynamoDBDocumentClient.from(ddbClient);

/**
 * POST /api/keys — Generate a new API key.
 *
 * Creates `mnm_` + 32 hex chars, SHA-256 hashes the full key, stores the
 * hash in DynamoDB under the user's github_id. Returns the plaintext key
 * exactly once — it is never stored.
 */
export async function POST() {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const githubId = session.user.id;

  // Generate key: mnm_ + 32 random hex chars (16 bytes)
  const rawKey = `mnm_${crypto.randomBytes(16).toString("hex")}`;
  const keyHash = crypto.createHash("sha256").update(rawKey).digest("hex");
  const keyPrefix = rawKey.slice(0, 8); // "mnm_xxxx"

  const now = new Date().toISOString();

  await docClient.send(
    new PutCommand({
      TableName: TABLE_NAME,
      Item: {
        github_id: githubId,
        email: session.user.email ?? "",
        github_username: session.user.name ?? "",
        display_name: session.user.name ?? "",
        avatar_url: session.user.image ?? "",
        api_key_hash: keyHash,
        api_key_prefix: keyPrefix,
        tier: "free",
        created_at: now,
        updated_at: now,
        last_login: now,
      },
    })
  );

  return NextResponse.json({
    key: rawKey,
    prefix: keyPrefix,
    tier: "free",
    created_at: now,
  });
}

/**
 * GET /api/keys — Get current API key metadata (masked).
 *
 * Returns the key prefix, tier, and creation date. Never returns the hash.
 */
export async function GET() {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const result = await docClient.send(
    new GetCommand({
      TableName: TABLE_NAME,
      Key: { github_id: session.user.id },
    })
  );

  if (!result.Item || !result.Item.api_key_hash) {
    return NextResponse.json({ has_key: false });
  }

  return NextResponse.json({
    has_key: true,
    prefix: result.Item.api_key_prefix ?? "mnm_****",
    tier: result.Item.tier ?? "free",
    created_at: result.Item.created_at ?? "",
  });
}

/**
 * DELETE /api/keys — Revoke the current API key.
 *
 * Removes the api_key_hash and api_key_prefix from the user record.
 */
export async function DELETE() {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  await docClient.send(
    new UpdateCommand({
      TableName: TABLE_NAME,
      Key: { github_id: session.user.id },
      UpdateExpression:
        "REMOVE api_key_hash, api_key_prefix SET updated_at = :now",
      ExpressionAttributeValues: {
        ":now": new Date().toISOString(),
      },
    })
  );

  return new NextResponse(null, { status: 204 });
}
