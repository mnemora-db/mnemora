import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { AgentCard } from "@/components/agent-card";
import { getAgents } from "@/lib/mnemora-api";
import { Bot, Terminal } from "lucide-react";
import Link from "next/link";

export default async function AgentsPage() {
  const session = await getServerSession(authOptions);
  const githubId = session?.user?.id ?? "";
  const agents = await getAgents(githubId);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-[22px] font-semibold text-[#FAFAFA] tracking-tight">
          Agents
        </h1>
        <p className="mt-0.5 text-sm text-[#71717A]">
          {agents.length === 0
            ? "No agents connected yet."
            : `${agents.length} agent${agents.length === 1 ? "" : "s"} in your workspace.`}
        </p>
      </div>

      {/* Agent grid */}
      {agents.length > 0 ? (
        <section aria-label="Agent list">
          <ul
            className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
            role="list"
          >
            {agents.map((agent) => (
              <li key={agent.id}>
                <AgentCard agent={agent} />
              </li>
            ))}
          </ul>
        </section>
      ) : (
        /* Empty state */
        <section aria-label="Getting started with agents">
          <div className="rounded-md border border-dashed border-[#3F3F46] bg-[#18181B]/50 px-6 py-10 flex flex-col items-center text-center">
            <div className="w-12 h-12 rounded-lg bg-[#111114] border border-[#27272A] flex items-center justify-center mb-4">
              <Bot className="w-6 h-6 text-[#71717A]" aria-hidden="true" />
            </div>
            <h2 className="text-sm font-semibold text-[#FAFAFA]">
              No agents yet
            </h2>
            <p className="mt-1.5 text-sm text-[#71717A] max-w-sm">
              Agents appear here automatically when they store memory via the
              Mnemora API. Connect your first agent with the SDK.
            </p>
            <div className="mt-4 flex items-center gap-3">
              <Link
                href="/dashboard/api-keys"
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-md bg-[#2DD4BF] text-[#09090B] text-sm font-semibold hover:bg-[#2DD4BF]/90 transition-colors duration-150"
              >
                <Terminal className="w-3.5 h-3.5" aria-hidden="true" />
                Get API Key
              </Link>
            </div>
            <pre className="mt-5 px-4 py-3 bg-[#111114] border border-[#27272A] rounded-md text-xs font-mono text-[#A1A1AA] text-left max-w-md overflow-x-auto w-full">
              <code>{`pip install mnemora-sdk

from mnemora import Mnemora
client = Mnemora(api_key="mnm_...")
client.state.put(
    agent_id="my-agent",
    session_id="s1",
    data={"task": "research"}
)`}</code>
            </pre>
          </div>
        </section>
      )}
    </div>
  );
}
