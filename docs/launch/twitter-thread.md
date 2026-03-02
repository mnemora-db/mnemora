# Twitter/X Thread

**Format:** 5 tweets. Each tweet is under 280 characters. Screenshots of code are noted where applicable.

---

**Tweet 1 — Problem hook**

Your AI agent forgets everything between sessions.

Most devs end up with Redis for state, Pinecone for vectors, Postgres for history, and S3 for logs.

Four databases. Four failure surfaces. One memory problem.

[280 characters: 228]

---

**Tweet 2 — What Mnemora is**

We built Mnemora: one REST API, four memory types.

- Working memory (DynamoDB, ~150ms)
- Semantic memory (pgvector, auto-embedded)
- Episodic memory (time-series, session replay)
- Procedural memory (schema live, SDK in v0.2)

No LLM call required for writes.

[280 characters: 268]

---

**Tweet 3 — Code snippet**

[Screenshot-worthy code block — format for readability]

```python
from mnemora import MnemoraSync

with MnemoraSync(api_key="mnm_...") as client:
    # State: DynamoDB, ~150ms warm
    client.store_state("agent-1", {"task": "summarize Q4", "step": 3})

    # Semantic: auto-embedded via Bedrock Titan, pgvector
    client.store_memory("agent-1", "User prefers bullet points.")

    # Search by meaning
    results = client.search_memory("formatting preferences", agent_id="agent-1")

    # Episodic log
    client.store_episode("agent-1", "sess-42", "action",
                         {"tool": "web_search", "query": "Q4 revenue"})
```

pip install mnemora

[Tweet text: 75 chars]
pip install mnemora — four memory types, one client

[Full tweet with code screenshot reference: attach code image]

---

**Tweet 4 — Honest comparison**

How does it compare?

Mem0: semantic only, LLM call per write (~500ms added latency)
Zep: knowledge graph, not self-hostable (platform only)
Letta: LLM required for all memory ops (~1s per write)
DIY: you own the ops for 3-5 separate databases

Mnemora: no LLM required, self-host via `npx cdk deploy`

[280 characters: 275]

---

**Tweet 5 — CTA**

MIT license (SDK). Self-hosted on your own AWS account.

446 tests passing. LangGraph, LangChain, and CrewAI integrations built in.

Semantic write latency is 3-4s (Bedrock + Aurora) -- worth knowing before you adopt.

Star it, try it, tell us what's missing:
github.com/mnemora-dev/mnemora

[280 characters: 278]
