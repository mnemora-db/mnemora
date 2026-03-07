# Mnemora + HubSpot CRM Integration

Two AI agents (support + sales) that use Mnemora to remember CRM context from HubSpot, producing dramatically better responses than a context-free LLM.

## What's in here

| File | Description |
|------|-------------|
| `hubspot_sync.py` | Pulls contacts, companies, deals, and tickets from HubSpot REST API into Mnemora memory |
| `demo_support_agent.py` | Customer support agent — side-by-side comparison with/without Mnemora context |
| `demo_sales_agent.py` | Sales pipeline assistant — same side-by-side comparison |
| `eval_quality.py` | LLM-as-judge eval scoring relevance, specificity, helpfulness, and personalization |
| `seed_hubspot_data.py` | Seeds HubSpot with realistic test data (10 contacts, 5 companies, 8 deals, 6 tickets) |
| `run_all.sh` | End-to-end demo script |

## Setup

### 1. Install dependencies

```bash
cd examples/hubspot-crm
pip install -r requirements.txt
```

### 2. Create API keys

You need three keys:

- **HubSpot**: Settings > Integrations > Private Apps > Create. Grant scopes: `crm.objects.contacts.read`, `crm.objects.contacts.write`, `crm.objects.companies.read`, `crm.objects.companies.write`, `crm.objects.deals.read`, `crm.objects.deals.write`, `tickets`.
- **Mnemora**: Sign up at [mnemora.dev](https://mnemora.dev) and generate an API key from the dashboard.
- **Anthropic**: Get a key from [console.anthropic.com](https://console.anthropic.com).

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your actual keys
```

### 4. Seed test data (optional)

If your HubSpot account is empty, populate it with realistic test data:

```bash
python seed_hubspot_data.py
```

To clean up seeded data later:

```bash
python seed_hubspot_data.py --clean
```

## Running the demos

### Full end-to-end

```bash
chmod +x run_all.sh
./run_all.sh          # runs everything non-interactively
./run_all.sh --seed   # seeds HubSpot first, then runs demos
```

### Individual scripts

**Support agent** (interactive mode):

```bash
python demo_support_agent.py
# Type customer messages, see responses with/without Mnemora
# Type "quit" to exit
```

**Support agent** (non-interactive, pre-set questions):

```bash
python demo_support_agent.py --auto
```

**Sales agent**:

```bash
python demo_sales_agent.py          # interactive
python demo_sales_agent.py --auto   # non-interactive
```

**Eval only**:

```bash
python eval_quality.py
```

## How it works

```
HubSpot CRM ──REST API──> hubspot_sync.py ──SDK──> Mnemora
                                                      │
User query ──> Agent ──search_memory()──────────────> │
                │                                      │
                │ <──── CRM context (contacts, deals, tickets)
                │
                └──> Claude API (with context) ──> Response
                └──> store_episode() ──────────────> Mnemora
```

1. `hubspot_sync.py` pulls CRM data and stores it in Mnemora:
   - Contacts and companies → **semantic memory** (vector-searchable)
   - Deals → **semantic memory** + **state memory** (pipeline tracking)
   - Tickets → **episodic memory** (time-series events)

2. When a user asks a question, the agent searches Mnemora for relevant CRM context using natural language — no exact-match queries needed.

3. Claude receives the user's question plus the CRM context, producing a response that references specific customer data.

4. Each interaction is logged as an episode in Mnemora, building a history over time.

## Architecture notes

- Uses HubSpot REST API directly (no MCP server required)
- Mnemora SDK (`MnemoraSync`) for all memory operations
- Claude API (`anthropic` SDK) for reasoning
- All data flows: HubSpot → Mnemora → Agent — HubSpot is never queried at inference time
