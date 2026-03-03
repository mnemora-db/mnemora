import { MarkdownRenderer } from "@/components/docs/markdown-renderer";

const content = `# LangChain Integration

Persist chat message history in Mnemora episodic memory so conversations survive process restarts.

## Prerequisites

- A Mnemora API key
- LangChain 0.2+ (\`langchain-core\`)

## Install

\`\`\`bash
pip install "mnemora[langchain]"
\`\`\`

## How it works

\`MnemoraMemory\` extends LangChain's \`BaseChatMessageHistory\`. Each message is stored as an episodic memory episode of type \`"conversation"\`.

## Basic usage

\`\`\`python
from mnemora import MnemoraSync
from mnemora.integrations.langchain import MnemoraMemory

client = MnemoraSync(api_key="mnm_...")
memory = MnemoraMemory(client=client, agent_id="my-agent", session_id="sess-1")

memory.add_user_message("What is the capital of France?")
memory.add_ai_message("The capital of France is Paris.")

for msg in memory.messages:
    print(type(msg).__name__, ":", msg.content)
\`\`\`

## Use with RunnableWithMessageHistory

\`\`\`python
from mnemora import MnemoraSync
from mnemora.integrations.langchain import MnemoraMemory
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

client = MnemoraSync(api_key="mnm_...")
llm = ChatOpenAI(model="gpt-4o-mini")

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}"),
])

chain = prompt | llm

chain_with_history = RunnableWithMessageHistory(
    chain,
    lambda session_id: MnemoraMemory(
        client=client,
        agent_id="support-agent",
        session_id=session_id,
    ),
    input_messages_key="question",
    history_messages_key="history",
)

response = chain_with_history.invoke(
    {"question": "My order ID is 12345."},
    config={"configurable": {"session_id": "user-alice"}},
)
print(response.content)
\`\`\`

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| \`ImportError\` | Package not installed | Run \`pip install "mnemora[langchain]"\` |
| Messages empty on second run | Wrong \`session_id\` | Use a stable, deterministic \`session_id\` |
| \`clear()\` deleted more than expected | Purges all agent data | Use a dedicated \`agent_id\` per user |
`;

export default function LangChainIntegrationPage() {
  return <MarkdownRenderer content={content} />;
}
