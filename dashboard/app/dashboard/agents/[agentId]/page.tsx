import Link from "next/link";
import { ChevronLeft, Clock, Calendar } from "lucide-react";
import { MemoryBrowser } from "@/components/memory-browser";
import {
  mockAgents,
  mockSemanticMemories,
  mockEpisodes,
  mockAgentState,
} from "@/lib/mock-data";
import { notFound } from "next/navigation";

interface AgentDetailPageProps {
  params: { agentId: string };
}

function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
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

export default function AgentDetailPage({ params }: AgentDetailPageProps) {
  const agent = mockAgents.find((a) => a.id === params.agentId);

  if (!agent) {
    notFound();
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav aria-label="Breadcrumb">
        <Link
          href="/dashboard/agents"
          className="inline-flex items-center gap-1.5 text-sm text-[#71717A] hover:text-[#FAFAFA] transition-colors duration-150"
        >
          <ChevronLeft className="w-4 h-4" aria-hidden="true" />
          Agents
        </Link>
      </nav>

      {/* Agent header */}
      <div className="rounded-md border border-[#27272A] bg-[#18181B] px-5 py-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-[22px] font-semibold text-[#FAFAFA] tracking-tight">
              {agent.name}
            </h1>
            <p className="mt-1 font-mono text-sm text-[#71717A]">{agent.id}</p>
          </div>
          <div className="flex flex-col items-end gap-1.5 text-xs text-[#71717A]">
            <div className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Active {formatRelativeTime(agent.lastActive)}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Created {formatDate(agent.createdAt)}</span>
            </div>
          </div>
        </div>

        {/* Memory summary */}
        <div className="mt-4 flex items-center gap-6 text-sm">
          <div>
            <span className="text-[28px] font-mono font-semibold text-[#FAFAFA]">
              {agent.stateSessions}
            </span>
            <p className="text-xs text-[#71717A] mt-0.5">State sessions</p>
          </div>
          <div className="h-8 w-px bg-[#27272A]" aria-hidden="true" />
          <div>
            <span className="text-[28px] font-mono font-semibold text-[#FAFAFA]">
              {agent.semanticCount}
            </span>
            <p className="text-xs text-[#71717A] mt-0.5">Semantic memories</p>
          </div>
          <div className="h-8 w-px bg-[#27272A]" aria-hidden="true" />
          <div>
            <span className="text-[28px] font-mono font-semibold text-[#FAFAFA]">
              {agent.episodeCount}
            </span>
            <p className="text-xs text-[#71717A] mt-0.5">Episodes</p>
          </div>
        </div>
      </div>

      {/* Memory browser */}
      <div className="rounded-md border border-[#27272A] bg-[#18181B] px-5 py-5">
        <MemoryBrowser
          semanticMemories={mockSemanticMemories}
          episodes={mockEpisodes}
          agentState={mockAgentState}
        />
      </div>
    </div>
  );
}

export function generateStaticParams() {
  return [{ agentId: "agent-research-7f3a" }];
}
