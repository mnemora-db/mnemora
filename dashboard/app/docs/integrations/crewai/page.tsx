import { MarkdownRenderer } from "@/components/docs/markdown-renderer";

const content = `# CrewAI Integration

Use Mnemora as the storage backend for CrewAI agents.

## Prerequisites

- A Mnemora API key
- CrewAI installed

## Install

\`\`\`bash
pip install "mnemora[crewai]"
\`\`\`

## How it works

\`MnemoraCrewStorage\` implements CrewAI's \`Storage\` interface. It maps each CrewAI storage key to a Mnemora \`session_id\` under a fixed \`agent_id\`.

| CrewAI concept | Mnemora concept |
|----------------|-----------------|
| Storage key | \`session_id\` |
| Storage value | Working memory \`data\` dict |
| \`agent_id\` param | Namespace for all keys |

## Basic usage

\`\`\`python
from mnemora import MnemoraSync
from mnemora.integrations.crewai import MnemoraCrewStorage

client = MnemoraSync(api_key="mnm_...")
storage = MnemoraCrewStorage(client=client, agent_id="crew-researcher")

storage.save("research-plan", {"steps": ["search", "read", "summarize"]})

plan = storage.load("research-plan")
print(plan)
# {'steps': ['search', 'read', 'summarize']}

keys = storage.list_keys()
print(keys)  # ['research-plan']

storage.delete("research-plan")
storage.reset()
\`\`\`

## Isolating multiple crews

\`\`\`python
from mnemora import MnemoraSync
from mnemora.integrations.crewai import MnemoraCrewStorage

client = MnemoraSync(api_key="mnm_...")

research_storage = MnemoraCrewStorage(client=client, agent_id="crew-research")
writing_storage = MnemoraCrewStorage(client=client, agent_id="crew-writing")

# Each storage instance sees only its own keys
print(research_storage.list_keys())  # ['findings']
print(writing_storage.list_keys())   # ['draft']
\`\`\`

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| \`load()\` returns \`None\` | Key never saved or deleted | Check \`list_keys()\` |
| Scalar wrapped in \`{"value": ...}\` | Non-dict values auto-wrapped | Access \`data["value"]\` |
| \`MnemoraAuthError\` | Invalid API key | Verify key in the dashboard |
`;

export default function CrewAIIntegrationPage() {
  return <MarkdownRenderer content={content} />;
}
