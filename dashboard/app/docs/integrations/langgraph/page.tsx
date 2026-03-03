import { MarkdownRenderer } from "@/components/docs/markdown-renderer";

const content = `# LangGraph Integration

Persist LangGraph graph state across invocations using Mnemora as the checkpoint backend.

## Prerequisites

- A Mnemora API key
- LangGraph 0.2+ installed

## Install

\`\`\`bash
pip install "mnemora[langgraph]"
\`\`\`

## How it works

\`MnemoraCheckpointSaver\` implements LangGraph's \`BaseCheckpointSaver\` interface. It maps each LangGraph \`thread_id\` to a Mnemora \`agent_id\`, and the checkpoint namespace to a Mnemora \`session_id\`.

| LangGraph concept | Mnemora concept |
|-------------------|-----------------|
| \`thread_id\` | \`agent_id\` (prefixed with \`"langgraph:"\`) |
| \`checkpoint_ns\` | \`session_id\` |
| Checkpoint payload | Working memory \`data\` field |
| Version counter | DynamoDB optimistic lock \`version\` |

## Basic usage

\`\`\`python
import asyncio
from mnemora import MnemoraClient
from mnemora.integrations.langgraph import MnemoraCheckpointSaver
from langgraph.graph import StateGraph, MessagesState, START, END

async def main():
    async with MnemoraClient(api_key="mnm_...") as client:
        saver = MnemoraCheckpointSaver(client=client)

        graph = StateGraph(MessagesState)
        graph.add_node("echo", lambda state: {"messages": state["messages"]})
        graph.add_edge(START, "echo")
        graph.add_edge("echo", END)

        app = graph.compile(checkpointer=saver)
        config = {"configurable": {"thread_id": "user-123"}}

        result = await app.ainvoke(
            {"messages": [{"role": "user", "content": "Hello"}]},
            config=config,
        )
        print(result["messages"][-1]["content"])

asyncio.run(main())
\`\`\`

## Custom namespace

\`\`\`python
saver = MnemoraCheckpointSaver(client=client, namespace="prod-chatbot")
\`\`\`

## Error handling

\`\`\`python
from mnemora import MnemoraConflictError, MnemoraAuthError

try:
    result = await app.ainvoke({"messages": [...]}, config=config)
except MnemoraConflictError:
    # Version mismatch — re-read and retry
    pass
except MnemoraAuthError:
    # API key is invalid or revoked
    pass
\`\`\`

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| \`ImportError\` | Package not installed | Run \`pip install "mnemora[langgraph]"\` |
| \`ValueError: config must contain thread_id\` | Missing thread config | Pass \`config={"configurable": {"thread_id": "..."}}\` |
| \`MnemoraConflictError\` | Concurrent writers | Re-read state and retry |
`;

export default function LangGraphIntegrationPage() {
  return <MarkdownRenderer content={content} />;
}
