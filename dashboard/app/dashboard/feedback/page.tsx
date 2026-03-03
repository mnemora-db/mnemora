import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { StatCard } from "@/components/stat-card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { ExternalLink, ShieldAlert } from "lucide-react";

const ADMIN_GITHUB_USERNAME = "isaacgbc";

interface FeedbackItem {
  feedback_id: string;
  type: "bug" | "feature" | "feedback";
  created_at: string;
  github_username: string;
  title: string;
  description: string;
  severity: string | null;
  rating: number | null;
  github_issue_url: string | null;
  github_issue_number: number | null;
  tier: string;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

const TYPE_BADGE: Record<
  string,
  { label: string; className: string }
> = {
  bug: {
    label: "Bug",
    className: "border-red-500/30 text-red-400 bg-red-500/5",
  },
  feature: {
    label: "Feature",
    className: "border-blue-500/30 text-blue-400 bg-blue-500/5",
  },
  feedback: {
    label: "Feedback",
    className: "border-purple-500/30 text-purple-400 bg-purple-500/5",
  },
};

const SEVERITY_BADGE: Record<string, string> = {
  critical: "border-red-500/30 text-red-400 bg-red-500/5",
  major: "border-amber-500/30 text-amber-400 bg-amber-500/5",
  minor: "border-[#3F3F46] text-[#A1A1AA] bg-transparent",
};

function starsDisplay(n: number | null): string {
  if (!n) return "—";
  return "\u2B50".repeat(n);
}

export default async function FeedbackPage() {
  const session = await getServerSession(authOptions);
  const username = session?.user?.name ?? "";

  // Gate: admin only
  if (username !== ADMIN_GITHUB_USERNAME) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <div className="w-12 h-12 rounded-lg bg-[#111114] border border-[#27272A] flex items-center justify-center">
          <ShieldAlert className="w-6 h-6 text-[#71717A]" aria-hidden="true" />
        </div>
        <h1 className="text-lg font-semibold text-[#FAFAFA]">Access Denied</h1>
        <p className="text-sm text-[#71717A]">
          This page is only available to administrators.
        </p>
      </div>
    );
  }

  // Fetch feedback from API route
  let items: FeedbackItem[] = [];
  try {
    const baseUrl = process.env.NEXTAUTH_URL ?? "http://localhost:3000";
    const res = await fetch(`${baseUrl}/api/feedback`, {
      headers: {
        cookie: "", // server component — session is resolved via getServerSession
      },
      cache: "no-store",
    });

    if (res.ok) {
      const data = await res.json();
      items = data.items ?? [];
    }
  } catch {
    // If API is unavailable, show empty state
  }

  // Compute stats
  const bugs = items.filter((i) => i.type === "bug").length;
  const features = items.filter((i) => i.type === "feature").length;
  const feedbacks = items.filter((i) => i.type === "feedback").length;
  const ratings = items
    .filter((i) => i.rating != null)
    .map((i) => i.rating as number);
  const avgRating =
    ratings.length > 0
      ? (ratings.reduce((a, b) => a + b, 0) / ratings.length).toFixed(1)
      : "—";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-[22px] font-semibold text-[#FAFAFA] tracking-tight">
          Feedback
        </h1>
        <p className="mt-0.5 text-sm text-[#71717A]">
          {items.length} submissions from users.
        </p>
      </div>

      {/* Stats */}
      <section aria-label="Feedback stats">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard label="Bug Reports" value={String(bugs)} />
          <StatCard label="Feature Requests" value={String(features)} />
          <StatCard label="General Feedback" value={String(feedbacks)} />
          <StatCard label="Avg Rating" value={String(avgRating)} />
        </div>
      </section>

      {/* Table */}
      <section aria-label="Feedback list">
        <div className="rounded-md border border-[#27272A] bg-[#18181B] overflow-hidden">
          <div className="px-5 py-4 border-b border-[#27272A]">
            <h2 className="text-sm font-medium text-[#FAFAFA]">
              All Submissions
            </h2>
          </div>

          {items.length === 0 ? (
            <div className="px-5 py-10 text-center">
              <p className="text-sm text-[#71717A]">
                No feedback yet. The widget is live on every dashboard page.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table
                className="w-full text-xs"
                aria-label="Feedback submissions"
              >
                <thead>
                  <tr className="border-b border-[#27272A]">
                    {["Date", "User", "Type", "Title", "Severity", "Rating", "Issue"].map(
                      (col) => (
                        <th
                          key={col}
                          scope="col"
                          className="px-5 py-2.5 text-left font-medium text-[#71717A] uppercase tracking-wide text-[10px]"
                        >
                          {col}
                        </th>
                      )
                    )}
                  </tr>
                </thead>
                <tbody>
                  {items.map((item, idx) => {
                    const typeBadge = TYPE_BADGE[item.type] ?? TYPE_BADGE.feedback;
                    return (
                      <tr
                        key={item.feedback_id}
                        className={cn(
                          "border-b border-[#27272A] last:border-0",
                          idx % 2 !== 0 && "bg-[#111114]/40"
                        )}
                      >
                        <td className="px-5 py-3 font-mono text-[#71717A] whitespace-nowrap">
                          {formatDate(item.created_at)}
                        </td>
                        <td className="px-5 py-3 text-[#A1A1AA] whitespace-nowrap">
                          @{item.github_username}
                        </td>
                        <td className="px-5 py-3 whitespace-nowrap">
                          <Badge
                            variant="outline"
                            className={cn("text-xs", typeBadge.className)}
                          >
                            {typeBadge.label}
                          </Badge>
                        </td>
                        <td className="px-5 py-3 text-[#FAFAFA] max-w-[240px] truncate">
                          {item.title}
                        </td>
                        <td className="px-5 py-3 whitespace-nowrap">
                          {item.severity ? (
                            <Badge
                              variant="outline"
                              className={cn(
                                "text-xs capitalize",
                                SEVERITY_BADGE[item.severity] ??
                                  SEVERITY_BADGE.minor
                              )}
                            >
                              {item.severity}
                            </Badge>
                          ) : (
                            <span className="text-[#52525B]">—</span>
                          )}
                        </td>
                        <td className="px-5 py-3 whitespace-nowrap">
                          {starsDisplay(item.rating)}
                        </td>
                        <td className="px-5 py-3 whitespace-nowrap">
                          {item.github_issue_url ? (
                            <a
                              href={item.github_issue_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-1 text-[#2DD4BF] hover:underline"
                            >
                              #{item.github_issue_number}
                              <ExternalLink
                                className="w-3 h-3"
                                aria-hidden="true"
                              />
                            </a>
                          ) : (
                            <span className="text-[#52525B]">—</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
