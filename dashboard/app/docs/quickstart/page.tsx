import { MarkdownRenderer } from "@/components/docs/markdown-renderer";

const content = `# Quickstart

Store your first memory in under 5 minutes.

## Prerequisites

- Python 3.9+
- A Mnemora API key (get one from the [dashboard](/dashboard/api-keys))

## Install the SDK

\`\`\`bash
pip install mnemora
\`\`\`

## Store your first memory

\`\`\`python
from mnemora import MnemoraSync

with MnemoraSync(api_key="mnm_...") as client:
    client.store_memory("agent-1", "The user prefers concise replies.")
\`\`\`

## Search memories

\`\`\`python
from mnemora import MnemoraSync

with MnemoraSync(api_key="mnm_...") as client:
    results = client.search_memory("user preferences", agent_id="agent-1")
    for r in results:
        print(r.content, r.similarity_score)
\`\`\`

## Full working example

This script stores agent state, writes a semantic memory, logs a conversation episode, then searches across all memories.

\`\`\`python
from mnemora import MnemoraSync

with MnemoraSync(api_key="mnm_...") as client:
    # Working memory — fast key-value state
    client.store_state("agent-1", {"task": "summarize quarterly report"})

    # Semantic memory — auto-embedded, vector-searchable
    client.store_memory("agent-1", "The user prefers bullet points over paragraphs.")

    # Episodic memory — time-stamped event log
    client.store_episode(
        agent_id="agent-1",
        session_id="sess-001",
        type="conversation",
        content={"role": "user", "message": "Summarize the Q3 results."},
    )

    # Vector search
    results = client.search_memory("output format preferences", agent_id="agent-1")
    for r in results:
        print(f"[{r.similarity_score:.2f}] {r.content}")

    # Retrieve state
    state = client.get_state("agent-1")
    print(state.data)
\`\`\`

**Expected output:**

\`\`\`
[0.94] The user prefers bullet points over paragraphs.
{'task': 'summarize quarterly report'}
\`\`\`

## Environment variable

Set \`MNEMORA_API_URL\` to override the default API endpoint — useful for self-hosted or staging deployments.

\`\`\`bash
export MNEMORA_API_URL=https://your-custom-endpoint.example.com
\`\`\`

## Next steps

- [Core concepts](/docs/concepts) — understand the four memory types
- [API reference](/docs/api-reference) — all 19 endpoints
- [LangGraph integration](/docs/integrations/langgraph) — persistent graph checkpoints
- [LangChain integration](/docs/integrations/langchain) — chat message history
- [CrewAI integration](/docs/integrations/crewai) — agent storage backend
`;

export default function QuickstartPage() {
  return <MarkdownRenderer content={content} />;
}
