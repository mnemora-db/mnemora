"use client";

import { useState } from "react";
import { Search } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { EpisodeTimeline } from "@/components/episode-timeline";
import type {
  SemanticMemory,
  Episode,
  AgentState,
} from "@/lib/mock-data";

interface MemoryBrowserProps {
  semanticMemories: SemanticMemory[];
  episodes: Episode[];
  agentState: AgentState;
}

function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function StateTab({ state }: { state: AgentState }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 text-xs text-[#71717A]">
        <span>
          Version{" "}
          <span className="font-mono text-[#A1A1AA]">v{state.version}</span>
        </span>
        <span>·</span>
        <span>
          Updated{" "}
          <span className="text-[#A1A1AA]">{formatDate(state.updatedAt)}</span>
        </span>
        <span>·</span>
        <span>
          Session{" "}
          <span className="font-mono text-[#A1A1AA]">{state.sessionId}</span>
        </span>
      </div>
      <pre
        className="rounded-md border border-[#27272A] bg-[#111114] p-4 text-xs font-mono text-[#A1A1AA] overflow-x-auto leading-relaxed"
        aria-label="Agent state JSON"
      >
        {JSON.stringify(state.data, null, 2)}
      </pre>
    </div>
  );
}

function SemanticTab({ memories }: { memories: SemanticMemory[] }) {
  const [query, setQuery] = useState("");

  const filtered = memories.filter(
    (m) =>
      m.content.toLowerCase().includes(query.toLowerCase()) ||
      m.namespace.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="space-y-4">
      <div className="relative">
        <Search
          className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#71717A]"
          aria-hidden="true"
        />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search semantic memories..."
          aria-label="Search semantic memories"
          className="pl-9 bg-[#111114] border-[#27272A] text-[#FAFAFA] placeholder:text-[#71717A] focus-visible:ring-teal-400 focus-visible:border-teal-400/50"
        />
      </div>

      {filtered.length === 0 ? (
        <p className="text-sm text-[#71717A] py-8 text-center">
          No memories match your search.
        </p>
      ) : (
        <ul className="space-y-2" aria-label="Semantic memories">
          {filtered.map((memory) => (
            <li
              key={memory.id}
              className="rounded-md border border-[#27272A] bg-[#111114] px-4 py-3 space-y-2"
            >
              <div className="flex items-center gap-2 flex-wrap">
                <Badge
                  variant="outline"
                  className="text-xs border-[#3F3F46] text-[#A1A1AA]"
                >
                  {memory.namespace}
                </Badge>
                <span className="text-xs text-[#71717A]">
                  confidence:{" "}
                  <span className="font-mono text-teal-400">
                    {memory.confidence.toFixed(2)}
                  </span>
                </span>
                <span className="text-xs text-[#71717A] ml-auto">
                  {formatDate(memory.createdAt)}
                </span>
              </div>
              <p className="text-sm text-[#A1A1AA] line-clamp-2 leading-relaxed">
                {memory.content}
              </p>
              {Object.keys(memory.metadata).length > 0 && (
                <div className="flex items-center gap-2 text-xs text-[#52525B]">
                  {Object.entries(memory.metadata).map(([k, v]) => (
                    <span key={k} className="font-mono">
                      {k}: {v}
                    </span>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function MemoryBrowser({
  semanticMemories,
  episodes,
  agentState,
}: MemoryBrowserProps) {
  return (
    <Tabs defaultValue="state">
      <TabsList className="bg-[#111114] border border-[#27272A] rounded-md p-0.5">
        <TabsTrigger
          value="state"
          className="text-xs data-[state=active]:bg-[#18181B] data-[state=active]:text-[#FAFAFA] text-[#71717A] rounded-sm px-4 py-1.5 transition-colors duration-150"
        >
          State
        </TabsTrigger>
        <TabsTrigger
          value="semantic"
          className="text-xs data-[state=active]:bg-[#18181B] data-[state=active]:text-[#FAFAFA] text-[#71717A] rounded-sm px-4 py-1.5 transition-colors duration-150"
        >
          Semantic
        </TabsTrigger>
        <TabsTrigger
          value="episodic"
          className="text-xs data-[state=active]:bg-[#18181B] data-[state=active]:text-[#FAFAFA] text-[#71717A] rounded-sm px-4 py-1.5 transition-colors duration-150"
        >
          Episodic
        </TabsTrigger>
      </TabsList>

      <TabsContent value="state" className="mt-4">
        <StateTab state={agentState} />
      </TabsContent>

      <TabsContent value="semantic" className="mt-4">
        <SemanticTab memories={semanticMemories} />
      </TabsContent>

      <TabsContent value="episodic" className="mt-4">
        <EpisodeTimeline episodes={episodes} />
      </TabsContent>
    </Tabs>
  );
}
