import { AgentCard } from "@/components/agent-card";
import { mockAgents } from "@/lib/mock-data";

export default function AgentsPage() {
  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-[22px] font-semibold text-[#FAFAFA] tracking-tight">
          Agents
        </h1>
        <p className="mt-0.5 text-sm text-[#71717A]">
          {mockAgents.length} agents in your workspace.
        </p>
      </div>

      {/* Agent grid */}
      <section aria-label="Agent list">
        <ul
          className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
          role="list"
        >
          {mockAgents.map((agent) => (
            <li key={agent.id}>
              <AgentCard agent={agent} />
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
