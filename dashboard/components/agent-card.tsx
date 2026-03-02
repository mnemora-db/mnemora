import Link from "next/link";
import { Bot, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { Agent } from "@/lib/mock-data";

interface AgentCardProps {
  agent: Agent;
}

function formatRelativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

const frameworkColors: Record<string, string> = {
  LangGraph: "border-teal-500/30 text-teal-400 bg-teal-500/5",
  LangChain: "border-blue-500/30 text-blue-400 bg-blue-500/5",
  CrewAI: "border-purple-500/30 text-purple-400 bg-purple-500/5",
  AutoGen: "border-amber-500/30 text-amber-400 bg-amber-500/5",
};

export function AgentCard({ agent }: AgentCardProps) {
  const frameworkClass =
    frameworkColors[agent.framework] ??
    "border-[#3F3F46] text-[#A1A1AA] bg-transparent";

  return (
    <Link
      href={`/dashboard/agents/${agent.id}`}
      className="block rounded-md border border-[#27272A] bg-[#18181B] px-5 py-4 hover:border-[#3F3F46] transition-colors duration-150 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-teal-400"
      aria-label={`View ${agent.name}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div
            className="w-8 h-8 rounded-md bg-[#111114] border border-[#27272A] flex items-center justify-center shrink-0"
            aria-hidden="true"
          >
            <Bot className="w-4 h-4 text-[#71717A]" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-[#FAFAFA] truncate">
              {agent.name}
            </p>
            <p className="text-xs font-mono text-[#71717A] truncate mt-0.5">
              {agent.id}
            </p>
          </div>
        </div>
        <Badge
          variant="outline"
          className={`text-xs shrink-0 ${frameworkClass}`}
        >
          {agent.framework}
        </Badge>
      </div>

      <div className="mt-4 flex items-center justify-between">
        <p className="text-xs text-[#71717A]">
          <span className="text-[#A1A1AA] font-medium">
            {agent.stateSessions}
          </span>{" "}
          states ·{" "}
          <span className="text-[#A1A1AA] font-medium">
            {agent.semanticCount}
          </span>{" "}
          semantic ·{" "}
          <span className="text-[#A1A1AA] font-medium">
            {agent.episodeCount}
          </span>{" "}
          episodes
        </p>
      </div>

      <div className="mt-3 flex items-center gap-1 text-xs text-[#71717A]">
        <Clock className="w-3 h-3" aria-hidden="true" />
        <span>Active {formatRelativeTime(agent.lastActive)}</span>
      </div>
    </Link>
  );
}
