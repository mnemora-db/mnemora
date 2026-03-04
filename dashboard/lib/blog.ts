export interface BlogPost {
  slug: string;
  title: string;
  excerpt: string;
  date: string;
  author: string;
  readingTime: string;
  tags: string[];
  keywords: string[];
  content: string;
}

const post1: BlogPost = {
  slug: "how-to-give-your-ai-agent-persistent-memory",
  title: "How to Give Your AI Agent Persistent Memory in 5 Minutes",
  excerpt:
    "AI agents forget everything between invocations. Here's how to add persistent memory to any Python agent in under 5 minutes with 4 types of memory.",
  date: "2025-03-03",
  author: "Isaac Benitez Candia",
  readingTime: "6 min",
  tags: ["tutorial", "python", "getting-started"],
  keywords: [
    "AI agent memory",
    "LangGraph persistent memory",
    "agent state management",
    "python AI agent tutorial",
  ],
  content: `## The Problem: Agents Are Stateless

Every time your AI agent runs, it starts from scratch. It doesn't know what it did five minutes ago, what the user told it yesterday, or which tools worked best last time. The context window gives the illusion of memory, but it's temporary — once the session ends, everything evaporates.

This is a fundamental problem. Agents that can't remember can't improve. They repeat mistakes, ask the same clarifying questions, and lose track of multi-step workflows the moment they restart.

You need actual persistent memory. Not a bigger context window. Not a longer system prompt. A real database that stores and retrieves agent state, knowledge, and history across sessions.

Here's how to add that to any Python agent in under 5 minutes.

## Step 1: Install the SDK

\`\`\`bash
pip install mnemora
\`\`\`

That's it. The SDK ships with both async and sync clients. We'll use the sync client here for simplicity.

## Step 2: Store Semantic Memory

Semantic memory is your agent's knowledge base — facts, preferences, and learned information that persist across sessions. When you store text, Mnemora automatically embeds it using AWS Bedrock Titan (1024 dimensions) and deduplicates against existing memories.

\`\`\`python
from mnemora import MnemoraSync

with MnemoraSync(api_key="mnm_your_key_here") as client:
    # Store facts your agent has learned
    client.store_memory("research-agent", "The user prefers concise summaries under 200 words.")
    client.store_memory("research-agent", "Primary data source is the SEC EDGAR API.")
    client.store_memory(
        "research-agent",
        "Quarterly earnings reports should focus on revenue growth and margins.",
        metadata={"category": "report-style", "confidence": 0.95},
    )
\`\`\`

Every call to \`store_memory\` embeds the text and stores it in Aurora pgvector. If a near-duplicate already exists (cosine similarity > 0.95), Mnemora merges the metadata instead of creating a duplicate entry.

## Step 3: Search Memory

Before your agent acts, it should retrieve relevant knowledge. Vector search finds semantically similar memories even when the wording is different.

\`\`\`python
with MnemoraSync(api_key="mnm_your_key_here") as client:
    results = client.search_memory(
        "What format does the user want for reports?",
        agent_id="research-agent",
        top_k=3,
    )

    for result in results:
        print(f"[{result.similarity:.2f}] {result.content}")
        # [0.89] Quarterly earnings reports should focus on revenue growth and margins.
        # [0.82] The user prefers concise summaries under 200 words.
\`\`\`

The \`threshold\` parameter (default 0.1) controls the minimum similarity score. Set it higher for stricter matches.

## Step 4: Store Working State

Working memory is your agent's scratchpad — the current task, intermediate results, and session-specific data. It's backed by DynamoDB for sub-10ms reads.

\`\`\`python
with MnemoraSync(api_key="mnm_your_key_here") as client:
    # Save current task state
    client.store_state("research-agent", {
        "current_task": "Analyze Q3 earnings for AAPL",
        "step": 3,
        "total_steps": 7,
        "intermediate_results": {
            "revenue": "89.5B",
            "yoy_growth": "2.1%",
        },
    })

    # Later — retrieve it (even after a restart)
    state = client.get_state("research-agent")
    print(state.data["current_task"])
    # "Analyze Q3 earnings for AAPL"
    print(state.data["step"])
    # 3
\`\`\`

Working state supports optimistic locking via a \`version\` field, so concurrent agents won't silently overwrite each other's progress.

## Step 5: Log Episodes

Episodic memory records what happened — conversations, tool calls, decisions, and outcomes. Think of it as your agent's activity log, stored in time-series order.

\`\`\`python
with MnemoraSync(api_key="mnm_your_key_here") as client:
    # Log a conversation turn
    client.store_episode(
        agent_id="research-agent",
        session_id="sess-2025-03-03",
        type="conversation",
        content={"role": "user", "message": "Analyze Apple's Q3 earnings"},
    )

    # Log a tool call
    client.store_episode(
        agent_id="research-agent",
        session_id="sess-2025-03-03",
        type="tool_call",
        content={"tool": "sec_edgar_api", "query": "AAPL 10-Q 2024-Q3"},
        metadata={"latency_ms": 342, "status": "success"},
    )

    # Replay the session later
    episodes = client.get_episodes("research-agent", session_id="sess-2025-03-03")
    for ep in episodes:
        print(f"[{ep.type}] {ep.content}")
\`\`\`

Hot episodes live in DynamoDB for fast access. Older episodes are automatically tiered to S3 for cost-effective long-term storage.

## Full Working Example

Here's a complete agent loop that uses all four memory types together:

\`\`\`python
from mnemora import MnemoraSync

AGENT_ID = "research-agent"
SESSION_ID = "sess-2025-03-03"

with MnemoraSync(api_key="mnm_your_key_here") as client:
    # 1. Restore working state (or start fresh)
    try:
        state = client.get_state(AGENT_ID)
        print(f"Resuming from step {state.data['step']}")
    except Exception:
        client.store_state(AGENT_ID, {"step": 1, "task": "earnings-analysis"})
        print("Starting new task")

    # 2. Retrieve relevant knowledge
    memories = client.search_memory("earnings report format preferences", agent_id=AGENT_ID)
    context = "\\n".join(m.content for m in memories)

    # 3. Do work (your agent logic here)
    result = f"Analysis complete. Context used: {len(memories)} memories."

    # 4. Store what the agent learned
    client.store_memory(AGENT_ID, "AAPL Q3 2024 revenue was $89.5B, up 2.1% YoY.")

    # 5. Log what happened
    client.store_episode(
        agent_id=AGENT_ID,
        session_id=SESSION_ID,
        type="action",
        content={"action": "earnings_analysis", "result": result},
    )

    # 6. Update working state
    client.store_state(AGENT_ID, {"step": 2, "task": "earnings-analysis", "status": "complete"})
\`\`\`

## What's Next

You now have an agent with four types of persistent memory, backed by DynamoDB, Aurora pgvector, and S3 — all through a single API key. No infrastructure to manage, no vector database to configure, no embedding pipeline to build.

To go further:

- Explore the [LangGraph integration](/blog/building-a-langgraph-agent-with-persistent-memory) to drop Mnemora into an existing LangGraph agent
- Read about the [4 types of agent memory](/blog/why-your-ai-agent-forgets-everything) and when to use each
- Check the [SDK documentation](/docs/sdk) for the full method reference

Get your API key at [mnemora.dev/dashboard](https://mnemora.dev/dashboard) and start building agents that remember.`,
};

const post2: BlogPost = {
  slug: "mnemora-vs-mem0-vs-zep-vs-letta",
  title: "Mnemora vs Mem0 vs Zep vs Letta: AI Agent Memory Compared (2025)",
  excerpt:
    "An honest comparison of the four leading AI agent memory solutions — architecture, pricing, performance, and when to use each.",
  date: "2025-02-28",
  author: "Isaac Benitez Candia",
  readingTime: "8 min",
  tags: ["comparison", "architecture"],
  keywords: [
    "Mem0 alternative",
    "Zep alternative",
    "Letta comparison",
    "AI memory database",
    "vector memory for agents",
  ],
  content: `## The Agent Memory Landscape

AI agents need memory. The context window isn't enough — it's temporary, expensive to fill, and grows linearly with history. The question isn't whether your agent needs a memory layer, but which one to use.

Four products lead the space: **Mem0**, **Zep/Graphiti**, **Letta (MemGPT)**, and **Mnemora**. Each takes a fundamentally different architectural approach. This post compares them honestly — including where each one falls short.

## Comparison at a Glance

| Criteria | Mem0 | Zep / Graphiti | Letta (MemGPT) | Mnemora |
|---|---|---|---|---|
| **Memory Types** | Key-value + vector | Temporal knowledge graph | Tiered blocks (core + archival) | 4 types (working, semantic, episodic, procedural) |
| **LLM Required for CRUD** | Yes (every operation) | No | Yes (memory self-editing) | No |
| **Self-Hosted Option** | Yes (OSS SDK) | Graphiti only (Zep is closed) | Yes | No (managed only) |
| **Serverless** | Managed platform only | No | No | Yes (AWS Lambda + Aurora Serverless) |
| **Multi-Tenant** | Platform-level | No | No | Yes (API-key scoped isolation) |
| **Checkpoint Support** | No | No | No | Yes (LangGraph compatible) |
| **Pricing Model** | Per-request + storage | Seat-based | Self-hosted (infra cost) | Tiered plans ($0-$99/mo) |
| **Vector Search** | Yes | Yes (within graph) | Yes (archival memory) | Yes (pgvector, 1024-dim) |

## Mem0: The Popular Choice

**GitHub stars:** 43K+ | **Architecture:** Managed platform + OSS SDK

Mem0 has the strongest brand awareness in the agent memory space, and for good reason. Their managed platform offers a clean API, and the open-source SDK lets you self-host with your own vector database.

**Strengths:**
- Large community and ecosystem. Extensive documentation and examples.
- The managed platform handles infrastructure entirely. You get a hosted API with no ops.
- Strong integrations with LangChain, LlamaIndex, and other popular frameworks.
- The OSS SDK is genuinely usable for self-hosting.

**Weaknesses:**
- Every CRUD operation calls an LLM. Storing a simple key-value pair triggers an LLM call to extract and categorize the memory. This adds 500ms+ latency and token cost to every write.
- No built-in working memory or state management. You get vector search, but not session state.
- No checkpoint support for agent frameworks like LangGraph.
- Multi-tenancy requires the managed platform — the OSS SDK is single-tenant.
- Cost can escalate quickly. Each memory operation burns LLM tokens on top of storage and API fees.

**Best for:** Teams that want a managed, battle-tested memory platform and are comfortable with per-operation LLM costs. Strong choice if you're already using their ecosystem.

## Zep / Graphiti: The Knowledge Graph Approach

**Architecture:** Temporal knowledge graph (bi-temporal data model)

Zep takes a fundamentally different approach — instead of a vector database, it builds a temporal knowledge graph where facts have valid-time and transaction-time dimensions. The open-source component, Graphiti, provides the graph engine.

**Strengths:**
- The bi-temporal model is genuinely innovative. Facts can be valid for specific time ranges, making it natural to handle corrections and temporal queries.
- Sub-200ms retrieval performance is impressive for graph-based queries.
- No LLM required in the read path — graph traversal is deterministic and fast.
- Excellent for conversational agents that need to track evolving facts about users.

**Weaknesses:**
- The Zep platform is closed-source. Only Graphiti (the graph engine) is OSS.
- Steeper learning curve. The bi-temporal model is powerful but requires understanding graph concepts.
- No serverless option. You need to run and manage the graph database infrastructure.
- Limited to the knowledge graph paradigm. If you need simple key-value state or time-series episode logs, you'll need additional infrastructure.
- No multi-tenant isolation out of the box.

**Best for:** Applications where temporal reasoning about facts is critical — conversational assistants that need to know "the user moved to London in January" and handle corrections gracefully.

## Letta (MemGPT): The Self-Editing Memory

**GitHub stars:** 42K+ | **Architecture:** LLM-managed memory blocks

Letta, originally MemGPT, pioneered the concept of agents that manage their own memory. The architecture splits memory into core memory (always in context) and archival memory (vector-searchable), and the LLM itself decides what to remember and forget.

**Strengths:**
- The self-editing memory concept is elegant. The agent autonomously decides what's important enough to persist.
- Core memory stays in the context window, so retrieval latency is zero for frequently-accessed data.
- Active open-source project with 42K+ stars and strong community.
- Built-in conversation management and multi-step tool use.
- The agent framework is comprehensive — not just memory, but a full agent runtime.

**Weaknesses:**
- Heavy server requirement. Letta runs as a server process, not as a serverless function. This means always-on infrastructure costs.
- Every memory operation involves an LLM call, since the LLM decides what to store. This adds cost and latency.
- Tightly coupled to the Letta agent framework. Using just the memory layer independently is difficult.
- Scaling to multi-tenant SaaS use cases requires significant custom work.
- No LangGraph checkpoint compatibility.

**Best for:** Teams building agents on the Letta framework who want the agent to autonomously manage its own memory. Less suitable if you just need a memory database for an existing agent.

## Mnemora: Serverless Unified Memory

**Architecture:** AWS-native (DynamoDB + Aurora pgvector + S3 + Lambda)

Mnemora takes a different angle: instead of building a new database engine, it composes existing AWS services into a unified memory API. Four memory types — working, semantic, episodic, and procedural — are exposed through a single REST API.

**Strengths:**
- No LLM in the CRUD path. Storing state is a DynamoDB write (sub-10ms). Vector search embeds on write, not on read. This means predictable latency and no token costs for basic operations.
- Truly serverless. Scales to zero when idle (about $1/month), scales up automatically under load. No servers to manage.
- Multi-tenant by design. Every API key maps to an isolated tenant with partition-level isolation in DynamoDB and row-level security in Aurora.
- LangGraph checkpoint compatibility via \`MnemoraCheckpointSaver\`. Drop-in replacement for the default \`MemorySaver\`.
- Four memory types through one API means you don't need to stitch together separate databases.

**Weaknesses:**
- No self-hosted option. Mnemora is a managed service running on AWS — you can't run it on your own infrastructure.
- Newer project with a smaller community compared to Mem0 or Letta.
- AWS-only. If your stack is on GCP or Azure, the latency to Mnemora's us-east-1 deployment adds overhead.
- No temporal knowledge graph. If you need bi-temporal fact tracking, Zep/Graphiti is better suited.
- The procedural memory type is less mature than the other three.

**Best for:** Teams building on AWS who want a single memory API for multiple memory types, especially those using LangGraph and needing multi-tenant isolation for SaaS applications.

## When to Choose Each

**Choose Mem0 when:**
- You want a battle-tested managed platform with the largest community
- Per-operation LLM cost is acceptable for your use case
- You need the open-source self-hosting option as a fallback

**Choose Zep/Graphiti when:**
- Temporal reasoning about facts is a core requirement
- You need sub-200ms graph-based retrieval
- You're willing to manage graph database infrastructure

**Choose Letta when:**
- You want agents that autonomously manage their own memory
- You're building on the Letta agent framework end-to-end
- Self-editing memory blocks fit your agent architecture

**Choose Mnemora when:**
- You need multiple memory types (state + vectors + episodes) in one API
- Serverless scale-to-zero pricing matters for your workload
- You're building multi-tenant SaaS features with agent memory
- You use LangGraph and need a persistent checkpointer

## Conclusion

There is no single best agent memory solution. The right choice depends on your architecture, scale requirements, and whether you prioritize autonomous memory management (Letta), temporal knowledge graphs (Zep), community ecosystem (Mem0), or unified serverless simplicity (Mnemora).

If you're evaluating options, start with the question: does your agent need to call an LLM just to read and write memory? If the answer is no, your choice narrows to Zep and Mnemora. From there, it comes down to whether you need a knowledge graph or a unified multi-type memory API.`,
};

const post3: BlogPost = {
  slug: "why-your-ai-agent-forgets-everything",
  title: "Why Your AI Agent Forgets Everything (And How to Fix It)",
  excerpt:
    "Your agent processes a 50-step research task, delivers results, then forgets everything. Here's why — and the architecture that fixes it.",
  date: "2025-02-25",
  author: "Isaac Benitez Candia",
  readingTime: "5 min",
  tags: ["architecture", "concepts"],
  keywords: [
    "AI agent forgets",
    "stateless AI agents",
    "agent memory architecture",
    "4 types of agent memory",
  ],
  content: `## The Stateless Problem

Your agent just finished a 50-step research workflow. It searched the web, read 12 documents, synthesized findings, and delivered a polished report. Impressive.

Now ask it to refine paragraph three. It has no idea what you're talking about.

This is the stateless problem. Most AI agents are functions: input goes in, output comes out, nothing persists. The LLM doesn't have a hard drive. When the process ends, everything the agent learned, decided, and produced during that session vanishes.

Developers work around this by stuffing conversation history into the context window. That works until it doesn't.

## Why Context Windows Are Not Memory

It's tempting to treat the context window as memory. Just keep appending messages, and the model "remembers" everything, right?

Three problems:

**Context is temporary.** When the session ends or the process restarts, the context window is gone. There's no persistence. An agent that ran yesterday has zero access to what it learned.

**Context grows linearly.** Every message, tool result, and system prompt competes for the same finite window. A 128K-token window sounds large until your agent processes a few long documents. Once you hit the limit, you start dropping older messages — which means your agent forgets the beginning of the conversation.

**Context has no retrieval.** All tokens in the window are equally weighted. The model can't efficiently search for a specific fact from 50 turns ago. It has to re-read everything sequentially. There's no index, no query, no selective recall.

Real memory is different. It's persistent, searchable, and selective. You don't remember everything that ever happened to you — you remember what was important, and you can retrieve specific facts on demand.

Agents need the same thing.

## The 4 Types of Agent Memory

Cognitive science identifies different memory systems in the human brain. The same taxonomy applies to AI agents, and building the right type of memory for each use case is the key to agents that actually improve over time.

### Working Memory: Your Agent's Desk

Working memory is the agent's scratchpad — the current task, intermediate results, and session-specific variables. It's what the agent is actively thinking about.

**Real-world analogy:** Your physical desk. It holds the documents and notes for whatever you're working on right now. When you switch tasks, you clear the desk and bring out different materials.

**Agent use cases:**
- Current step in a multi-step workflow
- Intermediate calculation results
- Active session state (user preferences for this conversation)
- Tool execution progress

**Technical requirements:** Sub-10ms reads and writes, key-value access pattern, optimistic locking for concurrent updates.

In Mnemora, working memory is backed by DynamoDB on-demand. Each agent has a state object keyed by agent ID and session ID, with automatic version tracking for safe concurrent access.

### Semantic Memory: Your Agent's Textbook

Semantic memory stores facts, knowledge, and learned information. It's not tied to a specific event or time — it's general knowledge the agent can draw on whenever relevant.

**Real-world analogy:** A textbook or reference manual. It contains facts and concepts, organized for retrieval by topic rather than by when you learned them.

**Agent use cases:**
- User preferences ("prefers bullet points over paragraphs")
- Domain knowledge ("the SEC EDGAR API rate limit is 10 requests per second")
- Learned patterns ("this customer usually asks about pricing on Mondays")
- Project context ("the codebase uses TypeScript with strict mode")

**Technical requirements:** Vector embedding for semantic search, deduplication, metadata filtering, namespace isolation.

In Mnemora, semantic memory is backed by Aurora Serverless v2 with pgvector. Text is automatically embedded via AWS Bedrock Titan (1024 dimensions) on write, and similarity search uses cosine distance with HNSW indexing.

### Episodic Memory: Your Agent's Diary

Episodic memory records events — what happened, when it happened, and in what context. It's your agent's activity log, stored in chronological order.

**Real-world analogy:** A diary or journal. Each entry records a specific event at a specific time, preserving the sequence and context of what occurred.

**Agent use cases:**
- Conversation history across sessions
- Tool call logs with latency and success/failure
- Decision audit trails
- Session replay for debugging

**Technical requirements:** Time-series storage, range queries by timestamp, session grouping, cost-effective tiering for historical data.

In Mnemora, hot episodes live in DynamoDB for fast access to recent events. Older episodes are automatically tiered to S3 for long-term storage at a fraction of the cost.

### Procedural Memory: Your Agent's Muscle Memory

Procedural memory stores how to do things — tool definitions, schemas, prompt templates, and business rules. It's the agent's learned procedures and capabilities.

**Real-world analogy:** Muscle memory. You don't consciously think about how to ride a bike — the procedure is stored and executed automatically. Similarly, an agent's tool definitions and workflow rules should be stored, versioned, and retrieved without manual configuration.

**Agent use cases:**
- Tool definitions with input/output schemas
- Prompt templates for specific tasks
- Business rules ("always check compliance before submitting")
- Workflow step definitions

**Technical requirements:** Relational storage with versioning, schema validation, active/inactive toggling.

In Mnemora, procedural memory is backed by PostgreSQL (via Aurora) with a dedicated table that supports versioned tool definitions, type-checked schemas, and active/inactive lifecycle management.

## How It All Fits Together

The four memory types aren't independent — they work together. When an agent starts a task:

1. **Working memory** loads the current state — where it left off, what step it's on.
2. **Semantic memory** retrieves relevant knowledge — what it knows about the topic, user preferences, domain facts.
3. **Episodic memory** provides history — what happened in previous sessions, what worked and what failed.
4. **Procedural memory** supplies the tools and rules — which tools to use, what templates to follow.

This is how human cognition works, and it's the architecture that produces agents capable of genuine improvement over time.

## Getting Started

If your agent forgets everything between sessions, the fix isn't a bigger context window. It's persistent memory, designed for the specific access patterns agents need.

Mnemora gives you all four memory types through a single API. Install the SDK, get an API key, and your agent starts remembering:

\`\`\`bash
pip install mnemora
\`\`\`

Read the [5-minute tutorial](/blog/how-to-give-your-ai-agent-persistent-memory) to add persistent memory to your existing Python agent.`,
};

const post4: BlogPost = {
  slug: "building-a-langgraph-agent-with-persistent-memory",
  title: "Building a LangGraph Agent with Persistent Memory",
  excerpt:
    "Add persistent memory to your LangGraph agent with a single line change — drop in MnemoraCheckpointSaver and your agent remembers across sessions.",
  date: "2025-02-20",
  author: "Isaac Benitez Candia",
  readingTime: "7 min",
  tags: ["tutorial", "langgraph", "integration"],
  keywords: [
    "LangGraph checkpointer",
    "LangGraph persistent state",
    "LangGraph memory tutorial",
    "MnemoraCheckpointSaver",
  ],
  content: `## What Is LangGraph?

LangGraph is a framework for building AI agents as graphs. Instead of a linear chain of LLM calls, you define nodes (functions) and edges (transitions) that form a state machine. This makes it straightforward to build agents with loops, branching logic, tool use, and human-in-the-loop steps.

At the core of LangGraph is **state** — a typed dictionary that flows through the graph. Each node reads from and writes to this shared state. When the graph finishes, the final state contains the result.

But here's the problem: by default, that state lives only in memory. When the process ends, it's gone.

## The Checkpointer Pattern

LangGraph solves persistence through **checkpointers**. A checkpointer is an object that saves and restores graph state at each step. Every time a node runs, the checkpointer serializes the current state to storage. If the agent crashes, restarts, or needs to resume later, the checkpointer loads the last saved state and continues from where it left off.

LangGraph ships with a built-in checkpointer called \`MemorySaver\`:

\`\`\`python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState

# Build a simple chatbot graph
graph = StateGraph(MessagesState)
graph.add_node("chatbot", chatbot_node)
graph.set_entry_point("chatbot")

# Compile with in-memory checkpointer
app = graph.compile(checkpointer=MemorySaver())
\`\`\`

This works for development. The problem is obvious: \`MemorySaver\` stores everything in a Python dictionary. Restart the process and every conversation, every thread, every checkpoint is lost.

For production agents, you need a checkpointer backed by a real database.

## MnemoraCheckpointSaver: Drop-In Replacement

Mnemora provides a LangGraph-compatible checkpointer that stores state in DynamoDB and Aurora. It implements the same \`BaseCheckpointSaver\` interface, so switching from \`MemorySaver\` is a single line change.

Install the SDK with the LangGraph extra:

\`\`\`bash
pip install "mnemora[langgraph]"
\`\`\`

Then swap your checkpointer:

\`\`\`python
from mnemora import MnemoraClient
from mnemora.integrations.langgraph import MnemoraCheckpointSaver

# Create the Mnemora checkpointer
client = MnemoraClient(api_key="mnm_your_key_here")
checkpointer = MnemoraCheckpointSaver(client=client)
\`\`\`

That's it. Your graph state now persists across process restarts.

## Full Working Example

Here's a complete tool-calling agent with persistent memory. The agent can search the web and remember conversations across sessions.

\`\`\`python
import asyncio
from typing import Annotated

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from mnemora import MnemoraClient
from mnemora.integrations.langgraph import MnemoraCheckpointSaver


# Define a simple tool
def search_web(query: str) -> str:
    """Search the web for information."""
    return f"Search results for: {query}"


# Set up the LLM with tools
llm = ChatOpenAI(model="gpt-4o-mini")
tools = [search_web]
llm_with_tools = llm.bind_tools(tools)


# Define the chatbot node
def chatbot(state: MessagesState) -> dict:
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


# Build the graph
graph = StateGraph(MessagesState)
graph.add_node("chatbot", chatbot)
graph.add_node("tools", ToolNode(tools))
graph.set_entry_point("chatbot")
graph.add_conditional_edges("chatbot", tools_condition)
graph.add_edge("tools", "chatbot")


async def main():
    # Compile with Mnemora checkpointer
    client = MnemoraClient(api_key="mnm_your_key_here")
    checkpointer = MnemoraCheckpointSaver(client=client)
    app = graph.compile(checkpointer=checkpointer)

    # First conversation — thread "user-123"
    config = {"configurable": {"thread_id": "user-123"}}

    result = await app.ainvoke(
        {"messages": [HumanMessage(content="What is LangGraph?")]},
        config=config,
    )
    print(result["messages"][-1].content)

    # Second invocation on the SAME thread — the agent remembers the first message
    result = await app.ainvoke(
        {"messages": [HumanMessage(content="Can you elaborate on the graph part?")]},
        config=config,
    )
    print(result["messages"][-1].content)

    await client.close()


asyncio.run(main())
\`\`\`

When you run this, the first invocation creates a checkpoint in Mnemora. The second invocation loads the checkpoint, so the agent sees the full conversation history and can respond in context. Even if you stop the process and restart it, the agent picks up where it left off.

## Multi-Session Support with thread_id

LangGraph uses \`thread_id\` to isolate conversations. Each thread is an independent state machine with its own checkpoint history. Mnemora maps \`thread_id\` to an agent ID and stores checkpoints per-thread.

\`\`\`python
# Thread for user Alice
alice_config = {"configurable": {"thread_id": "alice-session-1"}}
await app.ainvoke({"messages": [HumanMessage(content="Hello")]}, config=alice_config)

# Thread for user Bob — completely isolated state
bob_config = {"configurable": {"thread_id": "bob-session-1"}}
await app.ainvoke({"messages": [HumanMessage(content="Hi there")]}, config=bob_config)
\`\`\`

Alice's conversation history never leaks into Bob's thread. Each thread has its own checkpoint stream stored in Mnemora.

## Querying Saved State

You can inspect checkpoints directly through the Mnemora SDK, outside of LangGraph:

\`\`\`python
from mnemora import MnemoraSync

with MnemoraSync(api_key="mnm_your_key_here") as client:
    # Get the latest state for a thread
    state = client.get_state("user-123")
    print(state.data)

    # List all sessions (threads) for an agent
    sessions = client.list_sessions("user-123")
    print(sessions)
\`\`\`

This is useful for building admin dashboards, debugging agent behavior, or auditing conversation history.

## Benefits Over MemorySaver

Switching to MnemoraCheckpointSaver gives you:

- **Persistence across restarts.** State survives process crashes, deployments, and server reboots.
- **TTL cleanup.** Set time-to-live on checkpoints so old threads are automatically cleaned up. No manual garbage collection.
- **Multi-tenant isolation.** Each API key scopes to a tenant. Different customers' agent threads are isolated at the database level.
- **Serverless scaling.** Mnemora's DynamoDB backend scales automatically. No capacity planning for checkpoint storage.
- **Cross-service access.** Multiple services can read and write to the same checkpoint store. A web server can inspect agent state that a background worker created.

## Getting Started

1. Install the SDK: \`pip install "mnemora[langgraph]"\`
2. Get an API key at [mnemora.dev/dashboard](https://mnemora.dev/dashboard)
3. Replace \`MemorySaver()\` with \`MnemoraCheckpointSaver(client=client)\`
4. Your LangGraph agent now has persistent memory

The full SDK reference is available in the [documentation](/docs/sdk). For questions, open an issue on [GitHub](https://github.com/mnemora-db/mnemora).`,
};

const post5: BlogPost = {
  slug: "serverless-memory-architecture-for-ai-agents",
  title: "Designing a Serverless Memory Architecture for AI Agents",
  excerpt:
    "How we built a memory database that costs ~$1/month at idle and scales to millions of operations — without putting an LLM in every read path.",
  date: "2025-02-15",
  author: "Isaac Benitez Candia",
  readingTime: "7 min",
  tags: ["architecture", "aws", "deep-dive"],
  keywords: [
    "serverless AI architecture",
    "AWS AI agent infrastructure",
    "DynamoDB AI agents",
    "pgvector serverless",
  ],
  content: `## Why Serverless Matters for Agent Memory

Most agent memory solutions require always-on infrastructure. A Postgres instance, a Redis cluster, a vector database process. These services cost money even when nobody's using them, and they require capacity planning, patching, and monitoring.

For agent memory, the usage pattern is spiky. A SaaS product with 100 tenants might have 5 agents running right now and 95 idle. Tomorrow those numbers flip. Traditional databases charge you for peak capacity 24/7.

Serverless flips this model. You pay for what you use. At idle, costs approach zero. Under load, the system scales automatically. No capacity planning. No 3 AM pages because the database ran out of connections.

This is why we built Mnemora on AWS serverless primitives. Here's how the architecture works.

## The Stack

Mnemora composes four AWS services, each chosen for a specific memory access pattern:

### DynamoDB On-Demand: Working Memory

Working memory is key-value state — the current task, session variables, intermediate results. The access pattern is simple: write a JSON blob keyed by agent ID and session ID, read it back later.

DynamoDB on-demand is ideal for this. Sub-10ms single-item reads and writes. No provisioned capacity — you pay per request ($1.25 per million writes, $0.25 per million reads). At zero traffic, it costs nothing.

The partition key is \`tenant_id#agent_id\` and the sort key encodes the entity type (\`SESSION#<id>\`, \`EPISODE#<timestamp>#<id>\`, etc.). This single-table design means one DynamoDB table serves working memory and hot episodic storage.

Optimistic locking uses a \`version\` integer field. Every update includes the expected version number. If another process updated the item first, DynamoDB's \`ConditionExpression\` rejects the write with a 409 Conflict — no distributed locks needed.

### Aurora Serverless v2 + pgvector: Semantic Memory

Semantic memory requires vector similarity search. You store text, it gets embedded into a 1024-dimensional vector, and later you search by meaning rather than by exact keywords.

Aurora Serverless v2 with the pgvector extension handles this. Aurora Serverless v2 scales in 0.5 ACU increments, from a minimum of 0.5 ACU up to whatever ceiling you set. At minimum capacity, it runs on about $0.12/hour (roughly $87/month for 0.5 ACU).

This is the one component that isn't truly scale-to-zero — Aurora Serverless v2 doesn't pause to zero like the original Aurora Serverless v1 did. The minimum 0.5 ACU is the floor. For the capability it provides (full Postgres with vector search, relational queries, and row-level security), we consider this an acceptable trade-off.

The pgvector extension stores embeddings as a native \`vector(1024)\` column type. We use HNSW indexing (\`hnsw (embedding vector_cosine_ops)\`) for approximate nearest neighbor search, configured with \`m = 16\` and \`ef_construction = 200\` for a good balance of recall and speed.

### S3: Cold Episodic Storage

Recent episodes live in DynamoDB for fast access. But episodic data grows linearly — every agent action, every conversation turn generates an episode. Storing months of history in DynamoDB gets expensive.

S3 provides cost-effective cold storage. Old episodes are tiered from DynamoDB to S3 with a prefix structure: \`s3://mnemora-episodes-dev/<tenant_id>/<agent_id>/<date>/\`. S3 storage costs $0.023 per GB/month. For episodic data that's rarely accessed, this is orders of magnitude cheaper than keeping it in DynamoDB.

### Lambda ARM64: Compute

All six Lambda functions run on ARM64 (Graviton2), which is 20% cheaper than x86 for the same compute. Functions use Python 3.12 and include the AWS SDK, psycopg3 for Aurora connections, and Pydantic for request validation.

Lambda pricing is straightforward: $0.20 per million invocations plus duration charges. At low traffic, the cost is negligible. At high traffic, Lambda's concurrency model handles thousands of parallel requests without any capacity planning.

## Why No LLM in the CRUD Path

This is Mnemora's most important architectural decision: basic memory operations — store, read, update, delete — never call an LLM.

Competitors like Mem0 route every operation through an LLM. When you store a memory, the LLM extracts key information, categorizes it, and decides how to merge it with existing knowledge. This is powerful but has real costs:

- **Latency:** An LLM call adds 500ms-2000ms to every operation. Mnemora's DynamoDB writes complete in under 10ms.
- **Token cost:** Every memory operation burns input and output tokens. At scale, this dominates your bill.
- **Unpredictability:** LLM outputs are non-deterministic. The same store operation might produce different results on retry.
- **Dependency:** If the LLM provider has an outage, your memory layer goes down too.

Mnemora uses an LLM only for one thing: generating vector embeddings on write. When you store semantic memory, Bedrock Titan embeds the text into a 1024-dim vector. This is a deterministic operation (same input always produces the same embedding) that takes about 50ms and costs $0.02 per million tokens.

Reads never touch an LLM. Semantic search computes cosine similarity against the stored vectors using pgvector — pure math, no token cost, deterministic results.

## Cost Analysis

What does this actually cost in practice?

### At Idle (~$1/month)

| Service | Idle Cost |
|---|---|
| Aurora Serverless v2 (0.5 ACU) | ~$87/month |
| DynamoDB (on-demand, 0 requests) | $0 |
| Lambda (0 invocations) | $0 |
| S3 (minimal storage) | < $0.10 |
| API Gateway (0 requests) | $0 |

The honest minimum is around $87/month due to Aurora's 0.5 ACU floor. We state "~$1/month at idle" for the non-Aurora components. If you're building a new project and testing with minimal traffic, the Aurora cost is the dominant factor.

### At 10K Requests/Day

| Service | Cost |
|---|---|
| Aurora Serverless v2 (0.5-1 ACU) | ~$87-175/month |
| DynamoDB (300K requests/month) | ~$0.50 |
| Lambda (300K invocations) | ~$0.10 |
| Bedrock Titan embeddings | ~$2-5 |
| API Gateway | ~$0.30 |
| S3 | < $1 |
| **Total** | **~$90-180/month** |

The cost scales primarily with Aurora ACU usage and embedding volume. DynamoDB, Lambda, and API Gateway costs remain negligible even at moderate traffic.

## Scaling Patterns

### DynamoDB Partitioning

The \`tenant_id#agent_id\` partition key distributes load across DynamoDB partitions naturally. Each tenant's data is isolated in its own partition space. Hot partitions are automatically split by DynamoDB's adaptive capacity.

### Aurora ACU Auto-Scaling

Aurora Serverless v2 scales in 0.5 ACU increments based on CPU and memory utilization. A connection spike from a burst of semantic searches automatically scales the cluster up. When traffic subsides, it scales back down. The scaling takes seconds, not minutes.

### Lambda Concurrency

Lambda functions scale to hundreds of concurrent executions instantly. Each invocation gets its own compute environment, so there's no shared state to contend over. The only bottleneck is Aurora connection pooling — we use RDS Proxy to manage database connections and prevent connection exhaustion under high concurrency.

## Multi-Tenancy

Tenant isolation is entirely logical, not physical. Every tenant shares the same infrastructure, but data is strictly separated:

- **DynamoDB:** The partition key prefix \`tenant_id#\` ensures that queries never cross tenant boundaries. DynamoDB's access model makes it physically impossible to read another tenant's partition without knowing their key.
- **Aurora:** Every query includes a parameterized \`WHERE tenant_id = $1\` clause. Row-level security (RLS) policies provide defense-in-depth — even if application code has a bug, the database enforces isolation.
- **S3:** Object prefixes \`tenant_id/\` combined with IAM policies ensure bucket-level isolation.
- **Lambda authorizer:** The API key is resolved to a \`tenant_id\` in the authorizer function. Downstream handlers receive the tenant ID from the authorizer context — never from the client request. The client cannot impersonate another tenant.

This shared infrastructure model is what makes serverless cost-effective. Each tenant pays only for their usage, and idle tenants cost nothing.

## The Trade-Offs

This architecture isn't perfect for every use case:

- **Aurora's minimum cost** means you always pay for 0.5 ACU, even at zero traffic. For hobby projects, this might be more than you want to spend.
- **No self-hosting.** The tight integration with AWS services means Mnemora can't run on arbitrary infrastructure.
- **Cold starts.** Lambda functions have cold start latency of 200-500ms after periods of inactivity. For latency-sensitive applications, provisioned concurrency adds cost.
- **Regional.** Mnemora runs in us-east-1. Multi-region deployments would require significant additional infrastructure.

For teams building production agent systems on AWS, these trade-offs are usually acceptable. The combination of pay-per-use pricing, automatic scaling, and zero operational overhead makes serverless a strong fit for the spiky, multi-tenant workloads that agent memory systems serve.`,
};

const post6: BlogPost = {
  slug: "multi-tenant-agent-memory-for-saas",
  title: "Multi-Tenant Agent Memory: Building AI Features for SaaS",
  excerpt:
    "When you add AI agents to your SaaS product, every customer's data must stay isolated. Here's the memory architecture that makes it safe and simple.",
  date: "2025-02-10",
  author: "Isaac Benitez Candia",
  readingTime: "5 min",
  tags: ["saas", "multi-tenant", "architecture"],
  keywords: [
    "multi-tenant AI",
    "SaaS AI features",
    "AI agent for SaaS",
    "tenant isolation AI",
  ],
  content: `## The Multi-Tenant Challenge

You're building a SaaS product and you want to add AI agent features. Maybe a support agent that answers customer questions, or a data analyst that generates reports, or a workflow assistant that automates tasks.

The problem: when you have 500 customers using AI agents, every customer's data must be completely isolated. Customer A's agent can never see customer B's conversations, knowledge, or state. A single data leak is a security incident, a compliance violation, and a trust-destroying event.

Multi-tenancy in traditional databases is well understood. But agent memory introduces new challenges: vector embeddings in shared indexes, episodic logs spanning multiple storage tiers, and real-time state that needs sub-10ms access. You need isolation at every layer, without sacrificing performance.

## API Key Scoping

The foundation of Mnemora's multi-tenant isolation is the API key. Every API key maps to exactly one \`tenant_id\`. This mapping is stored in DynamoDB with the key SHA-256 hashed (Mnemora never stores API keys in plaintext).

When a request arrives at the API Gateway, the Lambda authorizer:

1. Hashes the bearer token from the \`Authorization\` header
2. Looks up the hash in the \`mnemora-users-dev\` DynamoDB table
3. Extracts the \`tenant_id\`, tier, and rate limits from the item
4. Injects the \`tenant_id\` into the Lambda authorizer context
5. Downstream handlers read the tenant ID from context — never from the request body

This means the client cannot supply or override their tenant ID. Even if a malicious client sends \`"tenant_id": "someone-else"\` in the request body, the handler ignores it and uses the authorizer-derived value.

\`\`\`python
# Inside every Lambda handler
tenant_id = event["requestContext"]["authorizer"]["tenant_id"]
# NOT from the request body — ever
\`\`\`

## Isolation at the Database Level

### DynamoDB: Partition Key Prefix

Every item in DynamoDB uses a composite partition key: \`tenant_id#agent_id\`. This isn't just a convention — it's a physical isolation boundary.

DynamoDB partitions data by the partition key. A query for \`PK = "github:12345#support-agent"\` physically cannot return items from \`PK = "github:67890#support-agent"\`. The database engine doesn't even scan the other tenant's data.

\`\`\`
# Tenant A's data
PK: github:12345#support-agent   SK: SESSION#default
PK: github:12345#support-agent   SK: EPISODE#2025-02-10T10:30:00Z#ep-001

# Tenant B's data — completely separate partitions
PK: github:67890#support-agent   SK: SESSION#default
PK: github:67890#support-agent   SK: EPISODE#2025-02-10T10:30:00Z#ep-002
\`\`\`

There is no \`SCAN\` operation in Mnemora's codebase. Every DynamoDB access is a \`GetItem\` or \`Query\` with the full partition key specified, which means cross-tenant data access is structurally impossible.

### Aurora: Parameterized Queries + Row-Level Security

Semantic memory lives in Aurora PostgreSQL with pgvector. Every query includes the tenant_id as a parameterized condition:

\`\`\`sql
SELECT id, content, embedding <=> $1::vector AS distance
FROM semantic_memory
WHERE tenant_id = $2 AND agent_id = $3
ORDER BY embedding <=> $1::vector
LIMIT $4;
\`\`\`

The \`$2\` parameter is always the authorizer-derived tenant ID. SQL injection attacks against the content or metadata fields cannot escape the tenant filter because the query is parameterized — the tenant ID is never interpolated into the SQL string.

For defense-in-depth, Aurora row-level security (RLS) policies enforce isolation at the database level:

\`\`\`sql
ALTER TABLE semantic_memory ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON semantic_memory
    USING (tenant_id = current_setting('app.tenant_id'));
\`\`\`

Even if a handler bug bypasses the \`WHERE\` clause, the RLS policy prevents cross-tenant reads.

### S3: Prefix Isolation

Episodic memory tiers cold data to S3 with a prefix structure:

\`\`\`
s3://mnemora-episodes-dev-993952121255/
  github:12345/                    # Tenant A
    support-agent/
      2025-02-10/ep-001.json
  github:67890/                    # Tenant B
    support-agent/
      2025-02-10/ep-002.json
\`\`\`

Lambda functions construct S3 paths using the authorizer-derived tenant ID. The function's IAM role restricts access to the bucket, and the key prefix ensures tenants can't read each other's objects.

## Example: Support Agent Per Customer

Here's how a SaaS platform would create an isolated support agent for each customer:

\`\`\`python
from mnemora import MnemoraSync

def handle_customer_message(customer_api_key: str, message: str):
    """Each customer uses their own API key, which scopes to their tenant."""

    with MnemoraSync(api_key=customer_api_key) as client:
        # Search this customer's knowledge base only
        relevant_docs = client.search_memory(
            message,
            agent_id="support-agent",
            top_k=5,
        )

        # Build context from customer-specific memories
        context = "\\n".join(doc.content for doc in relevant_docs)

        # Your LLM call here, using the customer-specific context
        response = call_llm(message=message, context=context)

        # Log the interaction to this customer's episodic memory
        client.store_episode(
            agent_id="support-agent",
            session_id=f"ticket-{generate_ticket_id()}",
            type="conversation",
            content={"role": "user", "message": message},
        )

        # Store any new knowledge the agent learned
        if should_store_knowledge(response):
            client.store_memory(
                "support-agent",
                extract_knowledge(response),
                metadata={"source": "conversation"},
            )

        return response
\`\`\`

Each customer's API key routes all operations to their tenant's isolated data partition. Customer A's support agent knowledge base, conversation history, and state are invisible to customer B — guaranteed at the database level.

## Billing Per Tenant

Mnemora tracks usage per API key. Every API call increments a counter in the \`mnemora-users-dev\` DynamoDB table:

- \`api_calls_today\`: resets daily, enforced against tier limits
- \`vectors_stored\`: total semantic memory count
- \`storage_bytes\`: total data across all memory types

This per-key tracking means you can bill each customer for their actual agent memory usage. The tier system (Free: 500 calls/day, Starter: 5K, Pro: 25K, Scale: 50K) enforces limits per-key at the authorizer level, before the request reaches any handler.

## Why Shared-Nothing Isolation Matters

The shared-nothing model — where each tenant's data is logically separated at every layer — provides several guarantees:

**Security:** A vulnerability in one tenant's agent logic cannot expose another tenant's data. The isolation is enforced at the database level, not the application level.

**Compliance:** SOC 2, HIPAA, and GDPR audits require demonstrable data isolation. Partition key isolation in DynamoDB and RLS in Aurora provide auditable, enforceable boundaries.

**Data portability:** Need to export a tenant's data? Query everything with their partition key prefix. Need to delete it? A single \`purge_agent\` call removes all data across all memory types — DynamoDB items, Aurora rows, and S3 objects.

\`\`\`python
# GDPR right-to-deletion: one API call
with MnemoraSync(api_key=customer_api_key) as client:
    result = client.purge_agent("support-agent")
    print(result)
    # PurgeResponse(state_deleted=15, semantic_deleted=234, episodes_deleted=1891)
\`\`\`

**Performance isolation:** DynamoDB's partition-based architecture means one tenant's heavy workload doesn't affect another's read latency. Each tenant's data lives in its own partition space with independent throughput.

## Getting Started

If you're adding AI agent features to a SaaS product, multi-tenant memory isolation isn't optional — it's a requirement. Mnemora provides this isolation by default, at every layer, without requiring you to build custom partitioning logic.

1. Generate API keys per customer at [mnemora.dev/dashboard](https://mnemora.dev/dashboard)
2. Use each customer's key in their agent's SDK instance
3. All data is automatically isolated by tenant

Read the [architecture deep dive](/blog/serverless-memory-architecture-for-ai-agents) for more on how the isolation layers work, or jump into the [5-minute tutorial](/blog/how-to-give-your-ai-agent-persistent-memory) to start building.`,
};

export const BLOG_POSTS: BlogPost[] = [
  post1,
  post2,
  post3,
  post4,
  post5,
  post6,
].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

export function getAllPosts(): BlogPost[] {
  return BLOG_POSTS;
}

export function getPost(slug: string): BlogPost | undefined {
  return BLOG_POSTS.find((post) => post.slug === slug);
}
