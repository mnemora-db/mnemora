import type { NextAuthOptions } from "next-auth";
import type { Session } from "next-auth";
import type { JWT } from "next-auth/jwt";
import GitHubProvider from "next-auth/providers/github";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, UpdateCommand } from "@aws-sdk/lib-dynamodb";

// Extend the built-in session types to include user.id
declare module "next-auth" {
  interface Session {
    user: {
      id: string;
      name?: string | null;
      email?: string | null;
      image?: string | null;
    };
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    sub?: string;
  }
}

// ── DynamoDB client (lazy singleton) ────────────────────────────────
const USERS_TABLE = process.env.USERS_TABLE_NAME ?? "mnemora-users-dev";
const ddbClient = new DynamoDBClient({
  region: process.env.AWS_REGION ?? "us-east-1",
});
const docClient = DynamoDBDocumentClient.from(ddbClient);

/**
 * Upsert the user record in DynamoDB on every sign-in.
 *
 * Ensures that `email`, `github_username`, `display_name`, `avatar_url`,
 * and `last_login` are always up-to-date. Uses SET with if_not_exists
 * for `created_at` and `tier` so existing values are never overwritten.
 */
async function upsertUser(profile: {
  githubId: string;
  email: string;
  username: string;
  displayName: string;
  avatarUrl: string;
}): Promise<void> {
  const now = new Date().toISOString();
  try {
    await docClient.send(
      new UpdateCommand({
        TableName: USERS_TABLE,
        Key: { github_id: profile.githubId },
        UpdateExpression: `
          SET email = :email,
              github_username = :username,
              display_name = :displayName,
              avatar_url = :avatar,
              last_login = :now,
              updated_at = :now,
              created_at = if_not_exists(created_at, :now),
              tier = if_not_exists(tier, :freeTier)
        `,
        ExpressionAttributeValues: {
          ":email": profile.email,
          ":username": profile.username,
          ":displayName": profile.displayName,
          ":avatar": profile.avatarUrl,
          ":now": now,
          ":freeTier": "free",
        },
      })
    );
  } catch (err) {
    // Fire-and-forget: never block authentication
    console.error("[auth] Failed to upsert user record:", err);
  }
}

export const authOptions: NextAuthOptions = {
  providers: [
    GitHubProvider({
      clientId: process.env.GITHUB_ID ?? "",
      clientSecret: process.env.GITHUB_SECRET ?? "",
    }),
  ],
  session: {
    strategy: "jwt",
  },
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account && profile) {
        token.sub = String(account.providerAccountId);

        // Upsert user record with latest profile data from GitHub
        const ghProfile = profile as Record<string, unknown>;
        await upsertUser({
          githubId: String(account.providerAccountId),
          email: String(ghProfile.email ?? token.email ?? ""),
          username: String(ghProfile.login ?? ""),
          displayName: String(ghProfile.name ?? ghProfile.login ?? ""),
          avatarUrl: String(ghProfile.avatar_url ?? ""),
        });
      }
      return token;
    },
    session({ session, token }: { session: Session; token: JWT }) {
      if (session.user && token.sub) {
        session.user.id = token.sub;
      }
      return session;
    },
    redirect({ url, baseUrl }) {
      // After sign-in always land on /dashboard unless the caller
      // explicitly requested a different relative path.
      if (url.startsWith("/")) {
        return url === "/" ? `${baseUrl}/dashboard` : `${baseUrl}${url}`;
      }
      // Allow absolute URLs on the same origin.
      if (url.startsWith(baseUrl)) {
        return url;
      }
      return `${baseUrl}/dashboard`;
    },
  },
  pages: {
    signIn: "/",
  },
};
