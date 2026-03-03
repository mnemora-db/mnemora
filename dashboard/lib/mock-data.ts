// Mock data for Mnemora dashboard. Replace with real API calls when backend is ready.

export interface Agent {
  id: string;
  name: string;
  stateSessions: number;
  semanticCount: number;
  episodeCount: number;
  lastActive: string;
  createdAt: string;
  framework: string;
}

export interface ApiCall {
  id: string;
  timestamp: string;
  method: "GET" | "POST" | "PUT" | "DELETE";
  path: string;
  status: number;
  latencyMs: number;
  agentId: string;
}

export interface UsageStat {
  apiCallsToday: number;
  apiCallsTodayDelta: number;
  apiCallsMonth: number;
  storageGb: number;
  activeAgents: number;
  totalSessions?: number;
}

export interface ChartDataPoint {
  date: string;
  calls: number;
}

export interface EndpointStat {
  endpoint: string;
  calls: number;
}

export interface StorageBreakdown {
  name: string;
  valueGb: number;
  percentage: number;
  color: string;
}

export interface CostEstimate {
  service: string;
  cost: number;
  detail: string;
}

export interface SemanticMemory {
  id: string;
  content: string;
  namespace: string;
  confidence: number;
  createdAt: string;
  metadata: Record<string, string>;
}

export interface Episode {
  id: string;
  type: "conversation" | "action" | "observation" | "tool_call";
  content: string;
  timestamp: string;
  sessionId: string;
}

export interface AgentState {
  version: number;
  updatedAt: string;
  sessionId: string;
  data: Record<string, unknown>;
}

// Agents
export const mockAgents: Agent[] = [
  {
    id: "agent-research-7f3a",
    name: "Research Agent",
    stateSessions: 3,
    semanticCount: 47,
    episodeCount: 128,
    lastActive: "2026-03-02T14:32:00Z",
    createdAt: "2026-02-10T09:00:00Z",
    framework: "LangGraph",
  },
  {
    id: "agent-support-2b1c",
    name: "Support Agent",
    stateSessions: 12,
    semanticCount: 203,
    episodeCount: 541,
    lastActive: "2026-03-02T14:28:00Z",
    createdAt: "2026-01-15T11:00:00Z",
    framework: "CrewAI",
  },
  {
    id: "agent-coder-9e4d",
    name: "Code Review Agent",
    stateSessions: 1,
    semanticCount: 19,
    episodeCount: 37,
    lastActive: "2026-03-01T22:10:00Z",
    createdAt: "2026-02-25T08:00:00Z",
    framework: "LangChain",
  },
  {
    id: "agent-analyst-5a8f",
    name: "Data Analyst Agent",
    stateSessions: 7,
    semanticCount: 88,
    episodeCount: 214,
    lastActive: "2026-03-02T12:00:00Z",
    createdAt: "2026-02-01T10:00:00Z",
    framework: "AutoGen",
  },
  {
    id: "agent-writer-3c6b",
    name: "Content Writer Agent",
    stateSessions: 2,
    semanticCount: 31,
    episodeCount: 74,
    lastActive: "2026-02-28T17:45:00Z",
    createdAt: "2026-02-18T14:00:00Z",
    framework: "LangGraph",
  },
  {
    id: "agent-monitor-8d2e",
    name: "System Monitor Agent",
    stateSessions: 1,
    semanticCount: 12,
    episodeCount: 892,
    lastActive: "2026-03-02T14:35:00Z",
    createdAt: "2026-01-01T00:00:00Z",
    framework: "LangChain",
  },
];

// Usage stats
export const mockUsageStats: UsageStat = {
  apiCallsToday: 1247,
  apiCallsTodayDelta: 12,
  apiCallsMonth: 38429,
  storageGb: 2.4,
  activeAgents: 12,
};

// Recent API call history
export const mockApiCalls: ApiCall[] = [
  {
    id: "req-001",
    timestamp: "2026-03-02T14:35:02Z",
    method: "POST",
    path: "/v1/memory/semantic/search",
    status: 200,
    latencyMs: 87,
    agentId: "agent-research-7f3a",
  },
  {
    id: "req-002",
    timestamp: "2026-03-02T14:34:58Z",
    method: "POST",
    path: "/v1/memory/episodic",
    status: 201,
    latencyMs: 43,
    agentId: "agent-support-2b1c",
  },
  {
    id: "req-003",
    timestamp: "2026-03-02T14:34:51Z",
    method: "GET",
    path: "/v1/state/agent-support-2b1c",
    status: 200,
    latencyMs: 12,
    agentId: "agent-support-2b1c",
  },
  {
    id: "req-004",
    timestamp: "2026-03-02T14:34:44Z",
    method: "POST",
    path: "/v1/memory/semantic",
    status: 201,
    latencyMs: 312,
    agentId: "agent-research-7f3a",
  },
  {
    id: "req-005",
    timestamp: "2026-03-02T14:34:30Z",
    method: "GET",
    path: "/v1/memory/agent-analyst-5a8f",
    status: 200,
    latencyMs: 156,
    agentId: "agent-analyst-5a8f",
  },
  {
    id: "req-006",
    timestamp: "2026-03-02T14:34:18Z",
    method: "PUT",
    path: "/v1/state/agent-coder-9e4d",
    status: 409,
    latencyMs: 24,
    agentId: "agent-coder-9e4d",
  },
  {
    id: "req-007",
    timestamp: "2026-03-02T14:34:01Z",
    method: "POST",
    path: "/v1/memory/search",
    status: 200,
    latencyMs: 203,
    agentId: "agent-writer-3c6b",
  },
  {
    id: "req-008",
    timestamp: "2026-03-02T14:33:47Z",
    method: "POST",
    path: "/v1/memory/semantic/search",
    status: 200,
    latencyMs: 91,
    agentId: "agent-monitor-8d2e",
  },
  {
    id: "req-009",
    timestamp: "2026-03-02T14:33:30Z",
    method: "DELETE",
    path: "/v1/memory/semantic/b2e4a1c3",
    status: 204,
    latencyMs: 38,
    agentId: "agent-research-7f3a",
  },
  {
    id: "req-010",
    timestamp: "2026-03-02T14:33:15Z",
    method: "POST",
    path: "/v1/state",
    status: 500,
    latencyMs: 2014,
    agentId: "agent-analyst-5a8f",
  },
];

// 30-day chart data
export const mockChartData: ChartDataPoint[] = Array.from(
  { length: 30 },
  (_, i) => {
    const date = new Date("2026-03-02");
    date.setDate(date.getDate() - (29 - i));
    const base = 900 + Math.floor(Math.random() * 800);
    return {
      date: date.toISOString().split("T")[0],
      calls: base,
    };
  }
);

// Override last few days for realism
mockChartData[27].calls = 1089;
mockChartData[28].calls = 1113;
mockChartData[29].calls = 1247;

// Endpoint stats
export const mockEndpointStats: EndpointStat[] = [
  { endpoint: "POST /v1/memory/semantic", calls: 12430 },
  { endpoint: "POST /v1/memory/semantic/search", calls: 8721 },
  { endpoint: "GET /v1/state/{agent_id}", calls: 6543 },
  { endpoint: "POST /v1/memory/episodic", calls: 4321 },
  { endpoint: "POST /v1/memory/search", calls: 3108 },
  { endpoint: "GET /v1/memory/{agent_id}", calls: 1987 },
  { endpoint: "Other", calls: 1319 },
];

// Storage breakdown
export const mockStorageBreakdown: StorageBreakdown[] = [
  { name: "Aurora", valueGb: 1.2, percentage: 50, color: "#2DD4BF" },
  { name: "DynamoDB", valueGb: 0.8, percentage: 33, color: "#A1A1AA" },
  { name: "S3", valueGb: 0.4, percentage: 17, color: "#52525B" },
];

// Cost estimates
export const mockCostEstimates: CostEstimate[] = [
  { service: "API Gateway", cost: 0.04, detail: "38K requests" },
  { service: "Lambda", cost: 0.12, detail: "compute time" },
  { service: "DynamoDB", cost: 2.5, detail: "on-demand R/W" },
  { service: "Aurora", cost: 8.2, detail: "ACU-hours" },
  { service: "Bedrock", cost: 0.77, detail: "Titan embeddings" },
];

// Semantic memories for agent detail
export const mockSemanticMemories: SemanticMemory[] = [
  {
    id: "sem-a1b2c3",
    content:
      "The Mnemora API uses AWS API Gateway HTTP API for 71% cost reduction versus REST API. All requests require Bearer token authentication derived from SHA-256 hashed API keys.",
    namespace: "architecture",
    confidence: 0.97,
    createdAt: "2026-03-01T10:15:00Z",
    metadata: { source: "documentation", tags: "aws,api" },
  },
  {
    id: "sem-d4e5f6",
    content:
      "Aurora Serverless v2 with pgvector extension stores 1024-dimensional embeddings from Bedrock Titan Text Embeddings v2. HNSW index parameters: m=16, ef_construction=200.",
    namespace: "architecture",
    confidence: 0.95,
    createdAt: "2026-03-01T09:30:00Z",
    metadata: { source: "code_review", tags: "aurora,pgvector" },
  },
  {
    id: "sem-g7h8i9",
    content:
      "LangGraph checkpoint compatibility requires implementing thread_id, checkpoint_ns, and checkpoint_id as primary key. TTL cleanup is a Mnemora-specific addition not in the standard schema.",
    namespace: "integrations",
    confidence: 0.91,
    createdAt: "2026-02-28T16:00:00Z",
    metadata: { source: "research", tags: "langgraph,checkpoints" },
  },
  {
    id: "sem-j1k2l3",
    content:
      "DynamoDB single-table design uses tenant_id#agent_id as partition key. Sort key patterns: SESSION#<id> for state, EPISODE#<timestamp>#<id> for episodic, META for agent metadata.",
    namespace: "database",
    confidence: 0.99,
    createdAt: "2026-02-27T14:22:00Z",
    metadata: { source: "schema", tags: "dynamodb,schema" },
  },
];

// Episodes for agent detail
export const mockEpisodes: Episode[] = [
  {
    id: "ep-001",
    type: "tool_call",
    content:
      'Called search_web with query "pgvector HNSW index tuning best practices". Returned 12 results.',
    timestamp: "2026-03-02T14:32:00Z",
    sessionId: "sess-alpha-1",
  },
  {
    id: "ep-002",
    type: "observation",
    content:
      "Search results indicate HNSW ef_construction=200 provides good recall/speed tradeoff for 1024-dim vectors at dataset sizes under 10M rows.",
    timestamp: "2026-03-02T14:31:45Z",
    sessionId: "sess-alpha-1",
  },
  {
    id: "ep-003",
    type: "action",
    content:
      "Stored semantic memory: HNSW tuning parameters with confidence 0.91. Deduplication check passed (cosine similarity < 0.95 with existing memories).",
    timestamp: "2026-03-02T14:31:30Z",
    sessionId: "sess-alpha-1",
  },
  {
    id: "ep-004",
    type: "conversation",
    content:
      'User: "Research optimal vector index parameters for our use case." Agent: "I will search for HNSW tuning recommendations and store findings."',
    timestamp: "2026-03-02T14:31:00Z",
    sessionId: "sess-alpha-1",
  },
  {
    id: "ep-005",
    type: "tool_call",
    content:
      'Called read_file with path "docs/architecture/pgvector.md". File read successfully, 847 tokens.',
    timestamp: "2026-03-01T10:20:00Z",
    sessionId: "sess-beta-2",
  },
  {
    id: "ep-006",
    type: "observation",
    content:
      "Documentation confirms pgvector supports cosine, L2, and inner product operators. Cosine similarity chosen for semantic search due to normalized embedding space.",
    timestamp: "2026-03-01T10:19:30Z",
    sessionId: "sess-beta-2",
  },
  {
    id: "ep-007",
    type: "conversation",
    content:
      'User: "What similarity metric does Mnemora use?" Agent: "Mnemora uses cosine similarity (vector_cosine_ops) for the HNSW index on semantic memory."',
    timestamp: "2026-03-01T10:15:00Z",
    sessionId: "sess-beta-2",
  },
];

// Agent state for agent detail
export const mockAgentState: AgentState = {
  version: 7,
  updatedAt: "2026-03-02T14:32:00Z",
  sessionId: "sess-alpha-1",
  data: {
    current_task: "research_vector_indexing",
    task_status: "in_progress",
    search_queries_executed: 3,
    memories_stored: 4,
    context_window_tokens: 12847,
    tools_available: ["search_web", "read_file", "store_memory", "query_memory"],
    last_tool_call: "search_web",
    iteration: 3,
  },
};
