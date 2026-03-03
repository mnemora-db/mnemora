import { MarkdownRenderer } from "@/components/docs/markdown-renderer";

const content = `# Pricing

## Plans

| | Free | Starter | Pro | Scale |
|---|---|---|---|---|
| **Price** | $0/mo | $19/mo | $79/mo | $299/mo |
| **API calls/day** | 1,000 | 10,000 | 100,000 | 1,000,000 |
| **Storage** | 100 MB | 1 GB | 10 GB | 100 GB |
| **Vectors** | 10,000 | 100,000 | 1,000,000 | 10,000,000 |
| **Memory types** | All 4 | All 4 | All 4 | All 4 |
| **LangGraph checkpoints** | Yes | Yes | Yes | Yes |
| **LangChain integration** | Yes | Yes | Yes | Yes |
| **CrewAI integration** | Yes | Yes | Yes | Yes |
| **Support** | Community | Email | Email + SLA | Dedicated |

All plans include access to the four memory types (working, semantic, episodic, procedural), all SDK integrations, and the dashboard.

---

## What counts as an API call

One API call is one HTTP request to any \`/v1/\` endpoint. This includes reads, writes, searches, and deletes.

Embedding generation (triggered by \`POST /v1/memory/semantic\`) counts as one API call. The Bedrock Titan embedding cost is included in your plan — there is no separate per-embedding charge.

---

## Storage calculation

| Tier | What is measured |
|------|-----------------|
| DynamoDB | Total bytes across all items in \`mnemora-state\` for your tenant |
| Aurora (pgvector) | Total bytes for \`semantic_memory\` and \`procedural_memory\` rows for your tenant |
| S3 | Total bytes for episodic cold-tier objects under your tenant prefix |

Storage is measured at the end of each billing period. You are not charged mid-month for storage spikes that resolve before billing runs.

---

## FAQ

**What happens when I exceed my daily API call limit?**

Requests return \`429 Too Many Requests\`. The SDK retries automatically with exponential back-off, but sustained usage above your limit will continue to return \`429\`. Upgrade your plan or contact support for a temporary increase.

**What happens when I exceed my storage limit?**

Write operations (\`POST\`, \`PUT\`) return \`413 Payload Too Large\` or \`507 Insufficient Storage\`. Read and delete operations continue to work. Purge old data with \`DELETE /v1/memory/{agent_id}\` or upgrade your plan.

**What happens when I exceed my vector limit?**

\`POST /v1/memory/semantic\` returns \`429\` with code \`VECTOR_LIMIT_EXCEEDED\`. Existing vectors remain searchable. Soft-delete old memories with \`DELETE /v1/memory/semantic/{id}\` to free up capacity.

**When does the billing period reset?**

The billing period resets on the same day each month that you subscribed. API call counters reset at midnight UTC on that date. Storage is measured at the time of billing.

**Are overage charges applied automatically?**

No. Mnemora does not bill overages automatically. When you hit a limit, requests fail with a clear error code. You must upgrade your plan to restore service.

**Is the Free plan time-limited?**

No. The Free plan is available indefinitely for personal projects and development. There is no trial expiry.

**Is there an enterprise plan?**

Yes. For requirements beyond the Scale plan — custom limits, VPC peering, dedicated infrastructure, or custom data residency — contact enterprise@mnemora.dev.

**Can I switch plans mid-month?**

Yes. Upgrades take effect immediately. Downgrades take effect at the start of the next billing period.
`;

export default function PricingPage() {
  return <MarkdownRenderer content={content} />;
}
