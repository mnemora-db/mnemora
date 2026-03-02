# **MNEMORA — Execution Plan v2.0**

**The Memory Infrastructure for AI Agents** **7-Day MVP Build Plan \+ Strategic Roadmap**

Confidential | March 2026 | Version 2.0 Solo Founder Execution Plan — Claude Code Assisted

---

## **Executive Summary**

Mnemora is an AWS-native, serverless database purpose-built for AI agent memory. It unifies four memory types (working, procedural, semantic, episodic) into a single API, eliminating the need for developers to stitch together 3-5 separate databases when building agent-powered applications.

**Core Thesis:** The database user is no longer a human developer. It is an AI agent. Mnemora is the first database designed for this new user.

**Target MVP Date:** Day 7 \= GitHub open-source launch \+ HackerNews post

**Target ICP:** Solo developers and small teams (2-10 devs) building AI-native applications with LangChain, CrewAI, or AutoGen

**Revenue Model:** Usage-based SaaS. Free / $19 / $79 / $299 tiers. 70%+ gross margins.

**AWS Stack:** DynamoDB \+ Aurora Serverless v2 (pgvector) \+ S3 \+ Lambda \+ HTTP API Gateway \+ Bedrock Titan Embeddings

**Build Method:** Claude Code with 9 specialized subagents, AWS plugins (zxkane/aws-skills, awslabs/agent-plugins), and obra/superpowers workflow plugins. Every build step has a copy-paste prompt and a verification test.

---

## **Architecture Overview**

| Memory Type | AWS Service | Access Pattern | Latency Target |
| ----- | ----- | ----- | ----- |
| Working Memory (state/scratchpad) | DynamoDB | Key-value get/put by agent\_id \+ session\_id | \< 10ms |
| Semantic Memory (embeddings/knowledge) | Aurora Serverless v2 \+ pgvector | Vector similarity search (cosine, L2, inner product) | \< 50ms |
| Episodic Memory (conversation logs) | S3 \+ DynamoDB metadata index | Time-range queries with metadata filtering | \< 100ms |
| Procedural Memory (tools/logic/schema) | Aurora Serverless v2 (Postgres) | Relational queries with foreign keys | \< 30ms |
| Embedding Generation | Bedrock Titan Text Embeddings v2 | Batch \+ real-time embedding creation | \< 200ms |

**Multi-Tenancy Model:** All tenants share infrastructure. DynamoDB uses composite keys (tenant\_id\#agent\_id). Aurora uses row-level tenant\_id filtering. S3 uses prefix-based isolation (s3://mnemora-data/{tenant\_id}/). API keys map to tenant\_id at the Lambda authorizer layer.

**Cost Floor:** \~$46/month total infrastructure baseline. First 50-100 free tier users can be served on this single shared cluster.

---

## **Pre-Sprint: Development Environment (COMPLETED)**

This section documents the Claude Code setup already completed. Skip to Day 1 if starting the build.

**What was installed:**

* Claude Code CLI (global)  
* Plugins: aws-common, aws-cdk, aws-cost-ops, serverless-eda (zxkane/aws-skills), awslabs/agent-plugins, obra/superpowers  
* 9 specialized subagents in .claude/agents/  
* CLAUDE.md project brain with routing table

**Agents available for delegation:**

| Agent | Directory | Model | Use For |
| ----- | ----- | ----- | ----- |
| infra-architect | engineering/ | sonnet | CDK stacks, AWS infrastructure |
| python-api-developer | engineering/ | sonnet | Lambda handlers, API code |
| sdk-developer | engineering/ | sonnet | Python SDK, framework integrations |
| database-engineer | engineering/ | opus | pgvector, DynamoDB, schema, migrations |
| api-tester | testing/ | sonnet | pytest, moto, coverage |
| ci-cd-engineer | devops/ | haiku | GitHub Actions, deploy pipelines |
| technical-writer | docs/ | sonnet | API docs, quickstarts, README |
| dashboard-developer | design/ | sonnet | Next.js dashboard UI |
| launch-strategist | marketing/ | sonnet | HN, PH, Reddit, Twitter launch |

**First commit:** `5a8e2f4` — CLAUDE.md, brand system, architecture docs, execution plan.

---

## **How to Use This Plan**

Every build step follows this pattern:

1. **PROMPT** — Copy-paste into Claude Code exactly as written  
2. **WAIT** — Let Claude Code execute (auto-accept recommended)  
3. **CHECKPOINT** — Run the test command. Green \= next prompt. Red \= run the debug prompt  
4. **DEBUG PROMPT** — Only if checkpoint failed

**Convention:**

* 🟢 \= checkpoint passed, continue  
* 🔴 \= checkpoint failed, run debug prompt  
* 📊 \= metrics/observability checkpoint (non-blocking but important)

---

## **Day 1: Foundation \+ AWS Infrastructure**

**Objective:** Deploy the entire AWS infrastructure as code (CDK) with a working API skeleton that returns health checks.

**Status: PARTIALLY COMPLETE** — CDK stack with VPC, DynamoDB, Aurora, S3, Lambda functions, API Gateway, and authorizer already synthesizes clean. What remains: Python handler code and deploy.

---

### **Prompt 1.1 — Review Current State**

Read the entire infra/ directory. Tell me: (1) which CDK resources are already defined, (2) which Lambda functions exist and what they do, (3) what's missing vs the Day 1 plan in docs/mnemora-execution-plan.docx. Be specific — list every resource by logical ID.

**Checkpoint:** Claude Code should list \~40+ CloudFormation resources including VPC, subnets, Aurora cluster, DynamoDB table, S3 bucket, 6 Lambda functions, HTTP API Gateway, authorizer, and routes. If it says "no infra directory found," the project structure is wrong.

---

### **Prompt 1.2 — Create Python Lambda Handlers**

Use @python-api-developer to create all Python Lambda handler files. We need:

1\. api/handlers/health.py — Returns {"status": "ok", "version": "0.1.0", "timestamp": "\<iso\>"}

2\. api/handlers/authorizer.py — Validates API key from x-api-key header, extracts tenant\_id. For now, use a hardcoded test key "mnemora-test-key-001" mapping to tenant "test-tenant". Return SimpleAuthorizerResult format.

3\. api/handlers/state.py — Stub handler for working memory CRUD. Returns {"message": "state endpoint", "method": "\<method\>"} for now.

4\. api/handlers/semantic.py — Stub handler for semantic memory. Returns {"message": "semantic endpoint", "method": "\<method\>"}.

5\. api/handlers/episodic.py — Stub handler for episodic memory. Returns {"message": "episodic endpoint", "method": "\<method\>"}.

6\. api/handlers/unified.py — Stub handler for unified memory API. Returns {"message": "unified endpoint", "method": "\<method\>"}.

7\. api/lib/\_\_init\_\_.py — Empty init file.

8\. api/lib/responses.py — Utility module with success\_response(body, status=200) and error\_response(message, status, error\_code) that return properly formatted API Gateway responses with CORS headers.

9\. api/requirements.txt — boto3, psycopg\[binary\], pydantic\>=2.0, mangum

Every handler must: use type hints, import mangum for Lambda adaptation, include request\_id in every response, log with structured JSON (request\_id, timestamp, path, method). NEVER log API keys or memory content.

Run ruff check after creating all files.

**Checkpoint:**

ls api/handlers/\*.py api/lib/\*.py | wc \-l

Expected: 8 files. Then:

cd api && pip install ruff \--break-system-packages && ruff check . && echo "PASSED"

Expected: "PASSED" with no errors or only warnings.

**Debug prompt (if ruff fails):**

Fix all ruff errors in api/. Run ruff check \--fix . then ruff format . then ruff check . again. Show me the final output.

---

### **Prompt 1.3 — Unit Tests for Handlers**

Use @api-tester to create unit tests for all Day 1 handlers:

1\. api/tests/test\_health.py — Test health endpoint returns 200, correct JSON structure, version is "0.1.0", timestamp is valid ISO format

2\. api/tests/test\_authorizer.py — Test valid key returns isAuthorized=True with tenant\_id in context. Test missing key returns isAuthorized=False. Test invalid key returns isAuthorized=False.

3\. api/tests/test\_responses.py — Test success\_response returns correct status and CORS headers. Test error\_response returns correct error structure.

4\. api/tests/conftest.py — Shared fixtures: mock\_event (API Gateway v2 event), mock\_context (Lambda context)

Use pytest. Use AAA pattern (Arrange-Act-Assert) with clear comments. Every test function name must describe what it tests: test\_health\_returns\_200, test\_auth\_rejects\_missing\_key, etc.

Run all tests and show results.

**Checkpoint:**

cd api && python \-m pytest tests/ \-v \--tb=short 2\>&1 | tail \-20

Expected: All tests pass (minimum 8 tests). Look for a line like `8 passed in 0.XXs`.

**Debug prompt:**

The tests are failing. Read the error output carefully. Fix the handler or test code — do NOT just delete failing tests. Run pytest \-v again and show me all passing.

---

### **Prompt 1.4 — CDK Deploy (DRY RUN)**

Before deploying, I need to verify costs. Use @infra-architect to:

1\. Run npx cdk diff and show me what will be created

2\. Estimate monthly cost at minimum usage (0 API calls, just infrastructure running) using the aws-cost-ops plugin

3\. Estimate monthly cost at 1000 API calls/day

4\. List any resources that will incur cost even when idle

5\. Confirm Aurora min ACU is 0.5 (not higher)

6\. Confirm all Lambda functions are ARM64

DO NOT deploy yet. Just show me the analysis.

**Checkpoint:** Review the cost estimate. Aurora Serverless v2 at 0.5 ACU minimum should be \~$43-48/month. If it shows \>$100/month at idle, something is wrong (probably NAT Gateway — consider removing for MVP).

📊 **Save this cost baseline** — you'll compare against actual AWS bills weekly.

---

### **Prompt 1.5 — Deploy Stack**

Deploy the Mnemora stack to AWS. Run: npx cdk deploy \--require-approval broadening

Show me all outputs after deployment (API URL, table names, cluster endpoint, bucket name). Save these outputs to a file at docs/deployment-outputs.md so we can reference them later.

**Checkpoint:** After deploy succeeds, test the live endpoint:

curl \-s https://\<API\_URL\>/health | python \-m json.tool

Expected:

{

    "status": "ok",

    "version": "0.1.0",

    "timestamp": "2026-03-XX..."

}

Then test auth rejection:

curl \-s \-o /dev/null \-w "%{http\_code}" https://\<API\_URL\>/v1/state

Expected: `401`

Then test auth acceptance:

curl \-s \-H "x-api-key: mnemora-test-key-001" https://\<API\_URL\>/v1/state

Expected: `200` with stub response.

**Debug prompt:**

The deployment failed. Read the CloudFormation error from the output. Common issues: (1) Aurora needs a VPC with isolated subnets, (2) Lambda needs VPC config to reach Aurora, (3) security group ingress rules missing. Fix the issue in the CDK stack, run cdk synth to validate, then try cdk deploy again.

---

### **Prompt 1.6 — Observability Baseline**

Use @infra-architect to add CloudWatch observability to the stack:

1\. Create a CloudWatch Dashboard called "MnemoraHealth" with these widgets:

   \- Lambda invocation count (all functions, 5-min periods)

   \- Lambda error count (all functions)

   \- Lambda duration p50/p95/p99 (all functions)

   \- API Gateway 4xx and 5xx error rates

   \- API Gateway request count

   \- API Gateway latency p50/p95/p99

   \- DynamoDB consumed read/write capacity

   \- Aurora ServerlessDatabaseCapacity (ACU usage)

   \- Aurora DatabaseConnections count

2\. Create CloudWatch Alarms:

   \- Lambda error rate \> 5% for 5 minutes → SNS topic "mnemora-alerts"

   \- API Gateway 5xx \> 10 in 5 minutes → SNS topic

   \- Aurora ACU \> 2 for 15 minutes → SNS topic (cost protection)

   \- DynamoDB throttled requests \> 0 → SNS topic

3\. Add the SNS topic email subscription — use a placeholder email that I'll update before deploy.

Run cdk synth to validate.

**Checkpoint:**

npx cdk synth \--quiet && echo "SYNTH OK"

Expected: "SYNTH OK". Then verify dashboard exists in the template:

npx cdk synth | grep \-c "AWS::CloudWatch"

Expected: At least 5 CloudWatch resources (1 dashboard \+ 4 alarms).

---

### **Day 1 Final Verification**

Run all of these. Every line should pass:

cd infra && npx tsc \--noEmit && echo "✅ TypeScript OK"

cd infra && npx cdk synth \--quiet && echo "✅ CDK Synth OK"

cd api && ruff check . && echo "✅ Lint OK"

cd api && python \-m pytest tests/ \-v && echo "✅ Tests OK"

curl \-s https://\<API\_URL\>/health | grep \-q "ok" && echo "✅ Health OK"

curl \-s \-o /dev/null \-w "%{http\_code}" https://\<API\_URL\>/v1/state | grep \-q "401" && echo "✅ Auth rejection OK"

**Expected:** 6/6 green checkmarks. If any fail, run:

The Day 1 verification has failures. Here are the results: \<paste output\>. Fix each failure. Do not skip any test — fix the root cause.

---

## **Day 2: Working Memory (Key-Value State Store)**

**Objective:** Implement the working memory layer on DynamoDB with full CRUD, TTL-based expiration, and session isolation.

---

### **Prompt 2.1 — State CRUD Implementation**

Use @python-api-developer to implement the full working memory API in api/handlers/state.py and api/lib/dynamo.py:

STATE API ENDPOINTS:

\- POST /v1/state — Store agent state (JSON blob, up to 400KB)

\- GET /v1/state/{agent\_id} — Retrieve current state

\- GET /v1/state/{agent\_id}/sessions — List all sessions

\- PUT /v1/state/{agent\_id} — Update state with optimistic locking (version field)

\- DELETE /v1/state/{agent\_id}/{session\_id} — Delete specific session

REQUIREMENTS:

1\. api/lib/dynamo.py — DynamoDB client module:

   \- Use boto3 resource (not client) for cleaner API

   \- Table name from DYNAMODB\_TABLE\_NAME env var

   \- Composite key: PK \= tenant\_id\#agent\_id, SK \= session\#{session\_id}

   \- Optimistic locking: version field, ConditionExpression on update

   \- TTL field: expires\_at (Unix timestamp), configurable per-tenant (default 24h)

   \- All operations include tenant\_id in key (multi-tenant isolation)

   \- NEVER expose internal DynamoDB structure in API responses

2\. api/handlers/state.py — Route handler:

   \- Extract tenant\_id from event requestContext authorizer

   \- Extract agent\_id and session\_id from path parameters

   \- Validate payload with Pydantic models

   \- Return proper error codes: 400 (validation), 404 (not found), 409 (version conflict), 413 (payload too large)

   \- Include request\_id and latency\_ms in every response

3\. api/lib/models.py — Pydantic v2 models:

   \- StateCreateRequest: agent\_id, session\_id (optional, auto-generate UUID), data (dict), ttl\_hours (optional)

   \- StateUpdateRequest: data (dict), version (int, required for optimistic lock)

   \- StateResponse: agent\_id, session\_id, data, version, created\_at, updated\_at, expires\_at

Run ruff check after all changes.

**Checkpoint:**

cd api && ruff check . && python \-c "from lib.models import StateCreateRequest; print('Models OK')" && echo "✅ PASSED"

---

### **Prompt 2.2 — State Tests (Comprehensive)**

Use @api-tester to create comprehensive tests for the state API. File: api/tests/test\_state.py

Use moto to mock DynamoDB. Create a fixture that sets up a mocked DynamoDB table with the correct schema.

REQUIRED TESTS (minimum 15):

Basic CRUD:

\- test\_create\_state\_returns\_201 — store state, verify response has version=1

\- test\_get\_state\_returns\_stored\_data — store then retrieve, exact JSON match

\- test\_get\_state\_not\_found\_returns\_404 — get non-existent agent

\- test\_list\_sessions\_returns\_all — store 3 sessions, list returns 3

\- test\_delete\_session\_returns\_204 — delete existing session succeeds

\- test\_delete\_nonexistent\_returns\_404 — delete missing session fails

Optimistic Locking:

\- test\_update\_with\_correct\_version\_succeeds — update with version=1 after create

\- test\_update\_with\_wrong\_version\_returns\_409 — send stale version, get conflict

\- test\_concurrent\_updates\_one\_wins — simulate 2 parallel updates, one gets 409

TTL:

\- test\_ttl\_sets\_expires\_at — create with ttl\_hours=1, verify expires\_at is \~1h from now

\- test\_default\_ttl\_is\_24h — create without ttl, verify expires\_at is \~24h from now

Tenant Isolation:

\- test\_tenant\_a\_cannot\_read\_tenant\_b — store as tenant A, query as tenant B, get 404

\- test\_tenant\_a\_cannot\_delete\_tenant\_b — same for delete

Validation:

\- test\_payload\_over\_400kb\_returns\_413 — send 401KB payload

\- test\_missing\_agent\_id\_returns\_400 — omit required field

Run all tests and show the full output with pass/fail counts.

**Checkpoint:**

cd api && python \-m pytest tests/test\_state.py \-v \--tb=short 2\>&1 | tail \-25

Expected: 15+ tests, all passing.

**Debug prompt:**

State tests are failing. Here's the output: \<paste\>. Fix the issues. Common problems: (1) moto mock not matching actual table schema, (2) tenant\_id not being extracted correctly from mock event, (3) version field type mismatch. Fix root causes, don't delete tests.

---

### **Prompt 2.3 — Deploy and Load Test**

Deploy the updated stack with the state handler changes:

1\. Run cd infra && npx cdk deploy \--require-approval broadening

2\. After deploy, run this integration test sequence against the live API:

TEST\_KEY="mnemora-test-key-001"

API\_URL="\<read from docs/deployment-outputs.md\>"

\# Create state

curl \-s \-X POST \-H "x-api-key: $TEST\_KEY" \-H "Content-Type: application/json" \\

  \-d '{"agent\_id": "agent-1", "session\_id": "sess-1", "data": {"task": "research", "step": 3}}' \\

  $API\_URL/v1/state

\# Retrieve state

curl \-s \-H "x-api-key: $TEST\_KEY" $API\_URL/v1/state/agent-1

\# Update state (use version from create response)

curl \-s \-X PUT \-H "x-api-key: $TEST\_KEY" \-H "Content-Type: application/json" \\

  \-d '{"data": {"task": "research", "step": 4}, "version": 1}' \\

  $API\_URL/v1/state/agent-1

\# List sessions

curl \-s \-H "x-api-key: $TEST\_KEY" $API\_URL/v1/state/agent-1/sessions

\# Delete session

curl \-s \-X DELETE \-H "x-api-key: $TEST\_KEY" $API\_URL/v1/state/agent-1/sess-1

Show me the response for each call. If any fail, debug and fix.

**Checkpoint:** All 5 operations return expected status codes (201, 200, 200, 200, 204).

---

### **Prompt 2.4 — Latency Benchmark**

Create a Python script at api/tests/benchmark\_state.py that:

1\. Sends 100 sequential POST requests to create state entries (different agent\_ids)

2\. Sends 100 sequential GET requests to retrieve them

3\. Sends 100 sequential PUT requests to update them

4\. Measures latency for each request (time.perf\_counter)

5\. Calculates and prints: p50, p95, p99, min, max, mean for each operation

6\. Prints results in a clean table format

Use the live API URL and test API key. Run it and show me the results.

ALSO: Check the CloudWatch MnemoraHealth dashboard — show me the Lambda duration metrics for the state function. Compare dashboard numbers vs benchmark numbers.

📊 **Checkpoint — Save these baseline numbers:**

| Operation | p50 target | p95 target | p99 target |
| ----- | ----- | ----- | ----- |
| POST /v1/state | \< 15ms | \< 30ms | \< 50ms |
| GET /v1/state | \< 10ms | \< 20ms | \< 30ms |
| PUT /v1/state | \< 15ms | \< 30ms | \< 50ms |

Note: First requests will be slower due to Lambda cold starts. The benchmark should exclude the first 5 requests as warmup.

If p99 exceeds targets by more than 2x, run:

The state API latency is too high. p99 for GET is \<X\>ms (target: 30ms). Diagnose: (1) check if it's cold start, (2) check DynamoDB consumed capacity in CloudWatch, (3) check if Lambda is in VPC (adds latency), (4) check Lambda memory allocation. Report findings and fix.

---

### **Day 2 Final Verification**

\# Run full test suite

cd api && python \-m pytest tests/ \-v \--tb=short

\# Verify live endpoints

curl \-s \-X POST \-H "x-api-key: mnemora-test-key-001" \-H "Content-Type: application/json" \\

  \-d '{"agent\_id": "verify-agent", "data": {"test": true}}' \\

  https://\<API\_URL\>/v1/state | python \-m json.tool

\# Check CloudWatch (in AWS Console)

\# Go to CloudWatch \> Dashboards \> MnemoraHealth

\# Verify: Lambda invocations showing, no errors, latency within targets

**Expected:** All unit tests pass. Live CRUD works. CloudWatch dashboard shows metrics.

---

## **Day 3: Semantic Memory (Vector Search \+ Embeddings)**

**Objective:** Implement semantic memory with pgvector on Aurora, integrated with Bedrock Titan for automatic embedding generation.

---

### **Prompt 3.1 — Database Schema and pgvector Setup**

Use @database-engineer to create the Aurora database schema:

1\. Create file api/lib/migrations/001\_initial\_schema.sql with:

   \- CREATE EXTENSION IF NOT EXISTS vector;

   \- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

   \- CREATE TABLE semantic\_memory (

       id UUID PRIMARY KEY DEFAULT uuid\_generate\_v4(),

       tenant\_id TEXT NOT NULL,

       agent\_id TEXT NOT NULL,

       namespace TEXT NOT NULL DEFAULT 'default',

       content TEXT NOT NULL,

       embedding vector(1024),

       metadata JSONB DEFAULT '{}',

       is\_deleted BOOLEAN DEFAULT FALSE,

       created\_at TIMESTAMPTZ DEFAULT NOW(),

       updated\_at TIMESTAMPTZ DEFAULT NOW()

     );

   \- CREATE INDEX idx\_semantic\_tenant\_agent ON semantic\_memory(tenant\_id, agent\_id) WHERE NOT is\_deleted;

   \- CREATE INDEX idx\_semantic\_embedding ON semantic\_memory USING hnsw (embedding vector\_cosine\_ops) WITH (m \= 16, ef\_construction \= 200);

   \- CREATE INDEX idx\_semantic\_metadata ON semantic\_memory USING gin (metadata);

   \- CREATE INDEX idx\_semantic\_namespace ON semantic\_memory(tenant\_id, namespace) WHERE NOT is\_deleted;

   \- Row-level security: CREATE POLICY tenant\_isolation ON semantic\_memory USING (tenant\_id \= current\_setting('app.tenant\_id'));

2\. Create file api/lib/aurora.py — Database connection module:

   \- Connection pool using psycopg pool (not psycopg2)

   \- Get credentials from Secrets Manager (cached for Lambda warm starts)

   \- Connection reuse at module level for Lambda

   \- set\_tenant\_context(conn, tenant\_id) function that runs SET app.tenant\_id \= %s

   \- ALWAYS use parameterized queries, NEVER string interpolation

   \- Include connection health check

3\. Create file api/lib/migrations/run\_migration.py — Simple migration runner that:

   \- Connects to Aurora

   \- Reads SQL files in order

   \- Executes them

   \- Logs which migrations ran

Run ruff check after creating all files.

**Checkpoint:**

cd api && ruff check lib/migrations/ lib/aurora.py && echo "✅ Lint OK"

python \-c "import ast; ast.parse(open('lib/aurora.py').read()); print('✅ Syntax OK')"

grep \-c "parameterized\\|%s\\|\\$1" lib/aurora.py  \# Should be \> 0, meaning parameterized queries

grep \-c "f'" lib/aurora.py lib/migrations/\*.py  \# Should be 0, no f-strings in SQL

---

### **Prompt 3.2 — Semantic Memory Handler**

Use @python-api-developer to implement the semantic memory API:

1\. api/handlers/semantic.py — Full handler:

   \- POST /v1/memory/semantic — Store memory, auto-generate embedding via Bedrock

   \- POST /v1/memory/semantic/search — Vector similarity search with filters

   \- GET /v1/memory/semantic/{id} — Get specific memory

   \- DELETE /v1/memory/semantic/{id} — Soft delete (set is\_deleted=true)

2\. api/lib/embeddings.py — Bedrock Titan integration:

   \- generate\_embedding(text: str) \-\> list\[float\] using Bedrock Titan v2

   \- Model ID: amazon.titan-embed-text-v2:0

   \- Output: 1024-dimension vector

   \- Handle chunking: if text \> 8000 tokens, chunk into 512-token pieces with 50-token overlap, generate embedding for each chunk, store as separate rows linked by parent\_id

   \- Include retry logic with exponential backoff (3 retries)

3\. api/lib/models.py — Add Pydantic models:

   \- SemanticCreateRequest: agent\_id, content (str), namespace (optional), metadata (optional dict)

   \- SemanticSearchRequest: query (str), agent\_id (optional), namespace (optional), top\_k (default 10, max 100), threshold (default 0.7), metadata\_filter (optional dict)

   \- SemanticResponse: id, agent\_id, content, metadata, similarity\_score (only in search), created\_at

SEARCH IMPLEMENTATION:

The search query should:

\- Generate embedding for the query text

\- SELECT \*, 1 \- (embedding \<=\> query\_embedding) AS similarity FROM semantic\_memory WHERE tenant\_id \= %s AND NOT is\_deleted AND (1 \- (embedding \<=\> query\_embedding)) \> threshold ORDER BY similarity DESC LIMIT top\_k

\- If metadata\_filter provided, add: AND metadata @\> %s

\- If agent\_id provided, add: AND agent\_id \= %s

\- If namespace provided, add: AND namespace \= %s

DEDUPLICATION:

Before inserting, check if any existing memory has cosine similarity \> 0.95 with the new embedding. If so, update that row instead of inserting a new one. Return the updated row with a "deduplicated": true flag.

Run ruff check after all changes.

**Checkpoint:**

cd api && ruff check . && echo "✅ Lint OK"

python \-c "from lib.models import SemanticCreateRequest, SemanticSearchRequest; print('✅ Models OK')"

python \-c "from lib.embeddings import generate\_embedding; print('✅ Embeddings module OK')"

---

### **Prompt 3.3 — Semantic Memory Tests**

Use @api-tester to create tests in api/tests/test\_semantic.py:

Mock Aurora using a real PostgreSQL test instance OR mock psycopg at the connection level. Mock Bedrock with a deterministic fake embedding generator (return a fixed 1024-dim vector based on hash of input text, so same text \= same vector).

REQUIRED TESTS (minimum 12):

Storage:

\- test\_store\_memory\_returns\_201\_with\_id

\- test\_store\_memory\_generates\_embedding — verify embedding is 1024 dims

\- test\_store\_memory\_with\_metadata — verify metadata stored correctly

\- test\_store\_memory\_with\_namespace — verify namespace isolation

Search:

\- test\_search\_returns\_relevant\_results — store 5 memories on different topics, search for one topic, verify top result is correct

\- test\_search\_respects\_threshold — set threshold=0.99, verify fewer results

\- test\_search\_respects\_top\_k — set top\_k=2, verify max 2 results

\- test\_search\_filters\_by\_metadata — store with tags, filter by tag

\- test\_search\_filters\_by\_namespace — only returns results from specified namespace

Deduplication:

\- test\_duplicate\_content\_updates\_existing — store same content twice, verify single row

\- test\_similar\_content\_deduplicates — store nearly identical content, verify single row with updated timestamp

Tenant Isolation:

\- test\_tenant\_isolation\_on\_search — tenant A's memories not visible to tenant B

Run all tests and show results.

**Checkpoint:**

cd api && python \-m pytest tests/test\_semantic.py \-v \--tb=short 2\>&1 | tail \-20

Expected: 12+ tests passing.

---

### **Prompt 3.4 — Run Migration and Integration Test**

1\. Run the database migration against the live Aurora cluster:

   cd api && python \-m lib.migrations.run\_migration

2\. After migration succeeds, run this integration test against the live API:

TEST\_KEY="mnemora-test-key-001"

API\_URL="\<from deployment-outputs.md\>"

\# Store a semantic memory

curl \-s \-X POST \-H "x-api-key: $TEST\_KEY" \-H "Content-Type: application/json" \\

  \-d '{"agent\_id": "agent-1", "content": "Machine learning is a subset of artificial intelligence that enables systems to learn from data", "namespace": "knowledge", "metadata": {"topic": "AI", "source": "test"}}' \\

  $API\_URL/v1/memory/semantic

\# Store another memory

curl \-s \-X POST \-H "x-api-key: $TEST\_KEY" \-H "Content-Type: application/json" \\

  \-d '{"agent\_id": "agent-1", "content": "PostgreSQL is an advanced open-source relational database", "namespace": "knowledge", "metadata": {"topic": "databases", "source": "test"}}' \\

  $API\_URL/v1/memory/semantic

\# Search for AI-related content

curl \-s \-X POST \-H "x-api-key: $TEST\_KEY" \-H "Content-Type: application/json" \\

  \-d '{"query": "How do neural networks learn?", "top\_k": 5, "threshold": 0.5}' \\

  $API\_URL/v1/memory/semantic/search

Show me the search results. The ML memory should rank higher than the PostgreSQL memory.

3\. Check Bedrock costs in CloudWatch: how much did 3 embedding calls cost?

📊 **Checkpoint — Save these numbers:**

| Metric | Value | Target |
| ----- | ----- | ----- |
| Embedding generation latency | \_\_\_ms | \< 200ms |
| Search latency (2 vectors) | \_\_\_ms | \< 50ms |
| Bedrock cost per 1000 embeddings | $\_\_\_ | \< $0.01 |
| Relevance of top result | \_\_\_score | \> 0.7 |

---

### **Day 3 Final Verification**

cd api && python \-m pytest tests/ \-v \--tb=short  \# All tests including Day 1 \+ Day 2 \+ Day 3

\# Verify live search works

\# Check CloudWatch dashboard: Aurora connections, Lambda durations, no errors

---

## **Day 4: Episodic Memory (Logs \+ Time-Series)**

**Objective:** Implement episodic memory for conversation logs and action traces with hot/cold storage tiering.

---

### **Prompt 4.1 — Episodic Storage Implementation**

Use @python-api-developer to implement the episodic memory API:

1\. api/handlers/episodic.py — Full handler:

   \- POST /v1/memory/episodic — Store episode (conversation turn, action, observation, tool\_call)

   \- GET /v1/memory/episodic/{agent\_id} — Query episodes with time range and filters

     Query params: from (ISO timestamp), to (ISO timestamp), type (conversation|action|observation|tool\_call), session\_id, limit (default 50, max 500\)

   \- GET /v1/memory/episodic/{agent\_id}/sessions/{session\_id} — Full session replay (all episodes in order)

   \- POST /v1/memory/episodic/{agent\_id}/summarize — Trigger summarization of recent episodes

2\. api/lib/episodes.py — Episode storage module:

   \- Store hot episodes in DynamoDB (last 24h):

     PK \= tenant\_id\#agent\_id, SK \= episode\#{timestamp}\#{episode\_id}

     GSI: session-index with PK \= tenant\_id\#session\_id, SK \= timestamp

   \- Cold storage: episodes older than 24h archived to S3

     Path: s3://mnemora-episodes/{tenant\_id}/{agent\_id}/{date}/{episode\_id}.json.gz

   \- Archive function: compress with gzip, upload to S3, delete from DynamoDB

   \- DynamoDB TTL: set to 48h (gives buffer beyond 24h archive window)

3\. api/lib/models.py — Add models:

   \- EpisodeCreateRequest: agent\_id, session\_id, type (enum), content (str or dict), metadata (optional)

   \- EpisodeResponse: id, agent\_id, session\_id, type, content, metadata, timestamp

   \- EpisodeSummaryRequest: agent\_id, num\_episodes (default 50), target\_length (default 500 words)

4\. api/lib/summarizer.py — Summarization module:

   \- Takes last N episodes for an agent

   \- Calls Bedrock Claude Haiku to generate a summary

   \- Stores the summary as a semantic memory with metadata: {"source": "episodic\_summary", "episode\_count": N, "time\_range": {"from": ..., "to": ...}}

   \- This creates a bridge between episodic and semantic memory

NOTE: The DynamoDB table needs a GSI for session queries. Use @infra-architect to add the GSI to the CDK stack if it's not already there.

Run ruff check after all changes.

**Checkpoint:**

cd api && ruff check . && echo "✅ Lint OK"

python \-c "from lib.episodes import store\_episode, query\_episodes; print('✅ Episodes module OK')"

python \-c "from lib.summarizer import summarize\_episodes; print('✅ Summarizer module OK')"

---

### **Prompt 4.2 — Episodic Tests**

Use @api-tester to create api/tests/test\_episodic.py:

Use moto for DynamoDB mocking and unittest.mock for S3 and Bedrock.

REQUIRED TESTS (minimum 12):

Storage & Retrieval:

\- test\_store\_episode\_returns\_201

\- test\_store\_episode\_with\_all\_types — test each type: conversation, action, observation, tool\_call

\- test\_get\_episodes\_by\_time\_range — store 10 episodes across 3 hours, query 1-hour window

\- test\_get\_episodes\_by\_type\_filter — store mixed types, filter returns only matching

\- test\_get\_episodes\_respects\_limit — store 100, query with limit=10, get 10

\- test\_session\_replay\_returns\_chronological — store 20 episodes in random order, replay returns sorted

Session Isolation:

\- test\_different\_sessions\_isolated — store in sess-1 and sess-2, replay each returns only its own

Tenant Isolation:

\- test\_tenant\_isolation\_on\_episodes — tenant A stores, tenant B queries, gets empty

Summarization:

\- test\_summarize\_calls\_bedrock — mock Bedrock, verify it's called with episode content

\- test\_summarize\_stores\_as\_semantic\_memory — verify summary lands in semantic\_memory table

\- test\_summarize\_includes\_metadata — verify source, episode\_count, time\_range in metadata

Archive:

\- test\_archive\_moves\_to\_s3 — archive old episode, verify S3 put and DynamoDB delete

Run all tests.

**Checkpoint:**

cd api && python \-m pytest tests/test\_episodic.py \-v \--tb=short 2\>&1 | tail \-20

Expected: 12+ tests passing.

---

### **Prompt 4.3 — Deploy and Integration Test**

Deploy updated stack (the GSI addition requires a CDK deploy):

cd infra && npx cdk deploy \--require-approval broadening

Then run this integration test:

TEST\_KEY="mnemora-test-key-001"

API\_URL="\<from deployment-outputs.md\>"

\# Store a conversation episode

curl \-s \-X POST \-H "x-api-key: $TEST\_KEY" \-H "Content-Type: application/json" \\

  \-d '{"agent\_id": "agent-1", "session\_id": "sess-001", "type": "conversation", "content": "User asked about machine learning basics", "metadata": {"role": "user"}}' \\

  $API\_URL/v1/memory/episodic

\# Store an action episode

curl \-s \-X POST \-H "x-api-key: $TEST\_KEY" \-H "Content-Type: application/json" \\

  \-d '{"agent\_id": "agent-1", "session\_id": "sess-001", "type": "action", "content": "Agent searched knowledge base for ML articles", "metadata": {"tool": "search"}}' \\

  $API\_URL/v1/memory/episodic

\# Store a response episode

curl \-s \-X POST \-H "x-api-key: $TEST\_KEY" \-H "Content-Type: application/json" \\

  \-d '{"agent\_id": "agent-1", "session\_id": "sess-001", "type": "conversation", "content": "Machine learning is a method of data analysis that automates analytical model building", "metadata": {"role": "assistant"}}' \\

  $API\_URL/v1/memory/episodic

\# Query session replay

curl \-s \-H "x-api-key: $TEST\_KEY" $API\_URL/v1/memory/episodic/agent-1/sessions/sess-001

\# Trigger summarization

curl \-s \-X POST \-H "x-api-key: $TEST\_KEY" \-H "Content-Type: application/json" \\

  \-d '{"num\_episodes": 3}' \\

  $API\_URL/v1/memory/episodic/agent-1/summarize

Show all responses. Verify session replay returns 3 episodes in order.

---

### **Day 4 Final Verification**

cd api && python \-m pytest tests/ \-v \--tb=short  \# ALL tests: Day 1-4

\# Count total tests — should be 40+

cd api && python \-m pytest tests/ \-v 2\>&1 | grep \-c "PASSED"

📊 **Running test count by day:**

| Day | New Tests | Cumulative | Minimum Target |
| ----- | ----- | ----- | ----- |
| Day 1 | 8 | 8 | 8 |
| Day 2 | 15 | 23 | 20 |
| Day 3 | 12 | 35 | 30 |
| Day 4 | 12 | 47 | 40 |

---

## **Day 5: Framework Integrations \+ Unified API**

**Objective:** Build the unified /v1/memory endpoint, Python SDK, and LangGraph/LangChain/CrewAI integrations.

---

### **Prompt 5.1 — Unified Memory API**

Use @python-api-developer to implement the unified memory endpoint:

1\. api/handlers/unified.py — Full implementation:

   \- POST /v1/memory — Auto-detect memory type from payload and route:

     \- If payload has "data" (dict) and "session\_id" → route to state (working memory)

     \- If payload has "content" (str) and no "type" → route to semantic memory

     \- If payload has "content" and "type" in (conversation, action, observation, tool\_call) → route to episodic

     \- Return 400 if can't determine type, with helpful error message

   \- GET /v1/memory/{agent\_id} — Returns combined view: latest state \+ top 5 semantic \+ last 10 episodes

   \- POST /v1/memory/search — Cross-memory search:

     \- Search semantic memory for query

     \- Search episodic memory for matching content (text search, not vector)

     \- Merge results, sort by relevance/recency

     \- Return with memory\_type field on each result

   \- DELETE /v1/memory/{agent\_id} — GDPR purge: delete ALL data for agent across all stores

     \- Delete from DynamoDB (state \+ episodes)

     \- Delete from Aurora (semantic memories)

     \- Delete from S3 (archived episodes)

     \- Return count of deleted items per store

   \- GET /v1/usage — Returns usage stats for current tenant:

     \- api\_calls\_today, api\_calls\_month

     \- storage\_bytes (DynamoDB \+ Aurora \+ S3)

     \- embeddings\_generated\_month

     \- agents\_count, sessions\_count

2\. api/lib/usage.py — Usage tracking module:

   \- Increment counters in DynamoDB on each API call

   \- PK \= tenant\_id\#usage, SK \= date\#{YYYY-MM-DD}

   \- Track: api\_calls, embeddings, storage\_delta

Run ruff check.

**Checkpoint:**

cd api && ruff check . && echo "✅ Lint OK"

python \-c "from handlers.unified import handler; print('✅ Handler OK')"

---

### **Prompt 5.2 — Python SDK**

Use @sdk-developer to create the Mnemora Python SDK:

Directory: sdk/mnemora/

Files to create:

1\. sdk/mnemora/\_\_init\_\_.py — Export MnemoraClient

2\. sdk/mnemora/client.py — Main async client:

   \- MnemoraClient(api\_key: str, base\_url: str \= "https://api.mnemora.dev")

   \- Async context manager (\_\_aenter\_\_, \_\_aexit\_\_)

   \- Uses httpx.AsyncClient internally

   \- Methods:

     \- store\_state(agent\_id, data, session\_id=None, ttl\_hours=None) \-\> StateResponse

     \- get\_state(agent\_id) \-\> StateResponse

     \- update\_state(agent\_id, data, version) \-\> StateResponse

     \- store\_memory(agent\_id, content, namespace=None, metadata=None) \-\> SemanticResponse

     \- search\_memory(query, agent\_id=None, top\_k=10, threshold=0.7) \-\> list\[SemanticResponse\]

     \- store\_episode(agent\_id, session\_id, type, content, metadata=None) \-\> EpisodeResponse

     \- get\_episodes(agent\_id, session\_id=None, from\_ts=None, to\_ts=None) \-\> list\[EpisodeResponse\]

     \- purge\_agent(agent\_id) \-\> PurgeResponse

     \- get\_usage() \-\> UsageResponse

   \- All methods handle errors: raise MnemoraError, MnemoraAuthError, MnemoraNotFoundError, MnemoraConflictError, MnemoraRateLimitError

   \- Include retry logic: 3 retries with exponential backoff for 429 and 5xx

3\. sdk/mnemora/models.py — Response models (Pydantic)

4\. sdk/mnemora/exceptions.py — Exception hierarchy

5\. sdk/mnemora/sync\_client.py — Synchronous wrapper using asyncio.run()

6\. sdk/pyproject.toml — Package config:

   \- name: mnemora

   \- version: 0.1.0

   \- dependencies: httpx\>=0.24, pydantic\>=2.0

   \- python: \>=3.9

7\. sdk/tests/test\_client.py — Tests using httpx mock transport:

   \- test\_store\_state, test\_get\_state, test\_search\_memory

   \- test\_auth\_error\_raises\_exception

   \- test\_retry\_on\_429

   \- test\_context\_manager\_closes\_client

Run ruff check on sdk/ and run the tests.

**Checkpoint:**

cd sdk && ruff check . && python \-m pytest tests/ \-v \--tb=short && echo "✅ SDK OK"

---

### **Prompt 5.3 — LangGraph Integration**

Use @sdk-developer to create the LangGraph checkpoint integration:

File: sdk/mnemora/integrations/langgraph.py

Implement MnemoraCheckpointSaver that extends langgraph.checkpoint.base.BaseCheckpointSaver:

\- \_\_init\_\_(self, client: MnemoraClient, namespace: str \= "langgraph")

\- async def aget(self, config: RunnableConfig) \-\> Optional\[Checkpoint\]:

  \- Extract thread\_id from config

  \- Call client.get\_state(agent\_id=thread\_id)

  \- Deserialize state data back to Checkpoint

\- async def aput(self, config: RunnableConfig, checkpoint: Checkpoint, metadata: CheckpointMetadata) \-\> RunnableConfig:

  \- Extract thread\_id from config

  \- Serialize checkpoint to dict

  \- Call client.store\_state or client.update\_state

  \- Return updated config with version

\- async def alist(self, config: Optional\[RunnableConfig\], \*, filter=None, before=None, limit=10) \-\> AsyncIterator\[CheckpointTuple\]:

  \- List state history for the thread

Also create:

\- sdk/mnemora/integrations/\_\_init\_\_.py

\- sdk/mnemora/integrations/langchain.py — MnemoraMemory extending BaseChatMessageHistory

\- sdk/mnemora/integrations/crewai.py — MnemoraCrewStorage extending CrewAI's Storage interface

Each integration should be importable as:

  from mnemora.integrations.langgraph import MnemoraCheckpointSaver

  from mnemora.integrations.langchain import MnemoraMemory

  from mnemora.integrations.crewai import MnemoraCrewStorage

Write tests for each integration. Use mocks — don't require the actual frameworks as test dependencies (use try/except imports).

Run ruff check and tests.

**Checkpoint:**

cd sdk && ruff check . && python \-m pytest tests/ \-v \--tb=short && echo "✅ Integrations OK"

---

### **Prompt 5.4 — OpenAPI Spec**

Use @technical-writer to create the OpenAPI 3.1 specification:

File: docs/openapi.yaml

Cover ALL endpoints built in Days 1-5:

\- GET /health

\- POST /v1/state, GET /v1/state/{agent\_id}, PUT /v1/state/{agent\_id}, DELETE /v1/state/{agent\_id}/{session\_id}, GET /v1/state/{agent\_id}/sessions

\- POST /v1/memory/semantic, POST /v1/memory/semantic/search, GET /v1/memory/semantic/{id}, DELETE /v1/memory/semantic/{id}

\- POST /v1/memory/episodic, GET /v1/memory/episodic/{agent\_id}, GET /v1/memory/episodic/{agent\_id}/sessions/{session\_id}, POST /v1/memory/episodic/{agent\_id}/summarize

\- POST /v1/memory, GET /v1/memory/{agent\_id}, POST /v1/memory/search, DELETE /v1/memory/{agent\_id}

\- GET /v1/usage

Include: security scheme (x-api-key header), request/response schemas matching Pydantic models, example values for every endpoint, error response schemas.

Validate the spec: pip install openapi-spec-validator && python \-m openapi\_spec\_validator docs/openapi.yaml

**Checkpoint:**

python \-m openapi\_spec\_validator docs/openapi.yaml && echo "✅ OpenAPI Valid"

---

### **Day 5 Final Verification**

\# Full test suite

cd api && python \-m pytest tests/ \-v \--tb=short

cd sdk && python \-m pytest tests/ \-v \--tb=short

\# Count all tests

echo "API tests: $(cd api && python \-m pytest tests/ \-v 2\>&1 | grep \-c PASSED)"

echo "SDK tests: $(cd sdk && python \-m pytest tests/ \-v 2\>&1 | grep \-c PASSED)"

\# Live integration: store via SDK, retrieve via curl

python \-c "

from mnemora.sync\_client import MnemoraClient

client \= MnemoraClient(api\_key='mnemora-test-key-001', base\_url='https://\<API\_URL\>')

result \= client.store\_memory('sdk-test-agent', 'Testing the Python SDK')

print(f'Stored memory: {result.id}')

results \= client.search\_memory('SDK testing')

print(f'Search returned {len(results)} results')

"

📊 **Cumulative test count:**

| Component | Tests | Target |
| ----- | ----- | ----- |
| API handlers | 50+ | 45 minimum |
| SDK | 15+ | 12 minimum |
| Total | 65+ | 57 minimum |

---

## **Day 6: Dashboard, Docs, and Developer Experience**

**Objective:** Build the developer dashboard and documentation site.

---

### **Prompt 6.1 — Next.js Dashboard Setup**

Use @dashboard-developer to create the Mnemora developer dashboard:

Directory: dashboard/

Setup:

\- Next.js 14 with App Router

\- Tailwind CSS with Mnemora design system (dark-first, teal accent \#2DD4BF, Geist fonts)

\- shadcn/ui components

Pages to create:

1\. app/page.tsx — Landing/login page with "Sign in with GitHub" button

2\. app/dashboard/page.tsx — Main dashboard:

   \- API key management card: show masked key, copy button, create new, revoke

   \- Usage overview card: API calls today/month, storage used, embeddings generated

   \- Quick health check: green/yellow/red indicator for API status

3\. app/dashboard/agents/page.tsx — Agent explorer:

   \- List all agents with memory counts (state, semantic, episodic)

   \- Click agent to see details

4\. app/dashboard/agents/\[agentId\]/page.tsx — Agent detail:

   \- Memory browser: tabs for State, Semantic, Episodic

   \- Search bar for semantic memory

   \- Episode timeline view

5\. app/dashboard/usage/page.tsx — Usage analytics:

   \- Line chart: API calls over time (daily)

   \- Bar chart: calls by endpoint

   \- Storage breakdown pie chart

   \- Cost estimate based on usage

6\. app/layout.tsx — Dark theme layout with sidebar nav

Use the Mnemora brand system:

\- Background: \#0A0A0A

\- Surface: \#141414

\- Border: \#262626

\- Text primary: \#FAFAFA

\- Text secondary: \#A1A1AA

\- Accent: \#2DD4BF (teal, used sparingly)

\- Font: Geist Sans / Geist Mono

\- NEVER use accent color on large surfaces

For now, use mock data — we'll connect to the real API in a later step.

Run: npx tsc \--noEmit && npm run build

**Checkpoint:**

cd dashboard && npx tsc \--noEmit && npm run build && echo "✅ Dashboard builds"

---

### **Prompt 6.2 — Documentation Site**

Use @technical-writer to create documentation:

Directory: docs/site/

Create these markdown files for a documentation site (we'll use Mintlify or Docusaurus later, for now just the content):

1\. docs/site/quickstart.md — 5-minute quickstart:

   \- Install SDK: pip install mnemora

   \- Get API key from dashboard

   \- Store first memory (3 lines of code)

   \- Search memories (3 lines of code)

   \- Full working example (10 lines)

2\. docs/site/concepts.md — Core concepts:

   \- Four memory types explained with real-world analogies

   \- When to use each type

   \- Multi-tenancy model

   \- Embedding and vector search basics

3\. docs/site/integrations/langgraph.md — LangGraph integration guide with full example

4\. docs/site/integrations/langchain.md — LangChain integration guide

5\. docs/site/integrations/crewai.md — CrewAI integration guide

6\. docs/site/api-reference.md — API reference (generated from OpenAPI spec summary, link to full spec)

7\. docs/site/pricing.md — Pricing page:

   \- Free: 1,000 calls/day, 100MB storage, 10K vectors

   \- Starter $19/mo: 10K calls/day, 1GB storage, 100K vectors

   \- Pro $79/mo: 100K calls/day, 10GB storage, 1M vectors

   \- Scale $299/mo: 1M calls/day, 100GB storage, 10M vectors

RULES: Every code example must use actual Mnemora SDK methods. No placeholder APIs. No marketing language — direct, technical, second person. Every example must include imports.

**Checkpoint:**

ls docs/site/\*.md docs/site/integrations/\*.md | wc \-l

Expected: 7+ files.

\# Verify all code examples have imports

grep \-L "import\\|from " docs/site/quickstart.md docs/site/integrations/\*.md

Expected: No files listed (all have imports).

---

### **Prompt 6.3 — README for GitHub**

Use @technical-writer and @launch-strategist to create the main README.md:

This is the first thing developers see on GitHub. It must be exceptional.

Structure:

1\. One-line description \+ badges (build, coverage, PyPI version, license)

2\. "The Problem" — 3 sentences on why AI agents need purpose-built memory

3\. "The Solution" — What Mnemora does in one paragraph

4\. Architecture diagram (mermaid code block)

5\. Quickstart — pip install, 10 lines to working memory

6\. Feature comparison table: Mnemora vs Mem0 vs Zep vs Letta vs DIY

   Columns: Feature, Mnemora, Mem0, Zep, Letta

   Rows: Memory types, Vector search, AWS native, Multi-tenant, Framework integrations, Self-hostable, Latency

7\. Framework integrations section with code snippets for LangGraph, LangChain, CrewAI

8\. API overview with endpoint table

9\. Self-hosting section (link to CDK deploy guide)

10\. Contributing section (link to CONTRIBUTING.md)

11\. License (MIT for SDK, BSL for infrastructure)

TONE: Direct, confident, technical. No hype. Let the code speak. Every claim must be backed by a code example or a metric.

**Checkpoint:** Read the README manually. Does it make you want to try Mnemora? Is every code example using real SDK methods?

---

### **Day 6 Final Verification**

cd dashboard && npm run build && echo "✅ Dashboard"

ls docs/site/\*.md | wc \-l  \# Should be 4+

ls docs/site/integrations/\*.md | wc \-l  \# Should be 3

cat README.md | head \-5  \# Should show Mnemora branding

cd api && python \-m pytest tests/ \-v  \# All API tests still pass

cd sdk && python \-m pytest tests/ \-v  \# All SDK tests still pass

---

## **Day 7: Launch Day**

**Objective:** Open-source the core, post to HackerNews/Reddit/Twitter, acquire first 10 users.

---

### **Prompt 7.1 — Pre-Launch Cleanup**

Prepare the repository for open source:

1\. Create .env.example with all required env vars (no actual values)

2\. Audit every file for hardcoded secrets — grep for "mnemora-test-key", AWS account IDs, endpoints. Replace with env vars.

3\. Create CONTRIBUTING.md:

   \- How to set up development environment

   \- How to run tests

   \- PR process

   \- Code style (ruff, black)

4\. Create LICENSE files:

   \- LICENSE-MIT for sdk/ directory

   \- LICENSE-BSL for infra/ directory

5\. Create .github/ISSUE\_TEMPLATE/ with templates for: bug report, feature request

6\. Create .github/pull\_request\_template.md

7\. Update .gitignore: \_\_pycache\_\_, .env, node\_modules, cdk.out, .pytest\_cache, dist/

Run a full test suite to make sure nothing is broken.

**Checkpoint:**

grep \-r "mnemora-test-key\\|AKIA\\|us-east-1" \--include="\*.py" \--include="\*.ts" api/ sdk/ infra/ | grep \-v ".env.example" | grep \-v "test\_"

Expected: No results (no hardcoded secrets outside test files).

---

### **Prompt 7.2 — CI/CD Pipeline**

Use @ci-cd-engineer to create GitHub Actions workflows:

1\. .github/workflows/ci.yml — Runs on every PR:

   \- Lint: ruff check api/ sdk/

   \- Type check: cd infra && npx tsc \--noEmit

   \- API tests: cd api && python \-m pytest tests/ \-v

   \- SDK tests: cd sdk && python \-m pytest tests/ \-v

   \- CDK synth: cd infra && npx cdk synth \--quiet

   \- Coverage: pytest \--cov=api \--cov=sdk \--cov-report=xml

   \- Upload coverage to Codecov

2\. .github/workflows/deploy.yml — Runs on merge to main:

   \- Run all CI checks first

   \- CDK deploy to staging (if we have staging)

   \- CDK deploy to production with \--require-approval broadening

Use OIDC for AWS auth (no long-lived keys). Python 3.12, Node 20, ARM64 runners if available.

**Checkpoint:**

cat .github/workflows/ci.yml | head \-5  \# Should start with name:

\# If actionlint is available:

actionlint .github/workflows/\*.yml && echo "✅ Workflows valid"

---

### **Prompt 7.3 — Launch Content**

Use @launch-strategist to create all launch content:

1\. docs/launch/hackernews-post.md — HackerNews Show HN post:

   \- Title: "Show HN: Mnemora – Open-source memory infrastructure for AI agents"

   \- Body: 200-300 words. Problem → solution → how it works → link. No hype.

2\. docs/launch/reddit-post.md — For r/MachineLearning, r/LangChain:

   \- Slightly different angle per subreddit

   \- Include architecture diagram link

3\. docs/launch/twitter-thread.md — 5-tweet thread:

   \- Tweet 1: Problem statement \+ hook

   \- Tweet 2: What Mnemora does

   \- Tweet 3: Code snippet (screenshot-worthy)

   \- Tweet 4: Comparison vs alternatives

   \- Tweet 5: Link \+ CTA

4\. docs/launch/email-outreach.md — Template for emailing AI agent developers:

   \- Short, personal, value-first

   \- Ask for feedback, not just signup

RULES: NEVER claim features we haven't built. NEVER use "revolutionary", "game-changing", etc. Lead with the problem, not the solution. Be specific about technical details (latency numbers, AWS services, supported frameworks).

**Checkpoint:** Read each piece. Does every claim map to something we actually built? Remove anything that doesn't.

---

### **Prompt 7.4 — Final Health Check**

Run the complete health check sequence. This is our go/no-go for launch:

1\. INFRASTRUCTURE:

   curl \-s https://\<API\_URL\>/health | python \-m json.tool

   \# Must return status: ok

2\. STATE API:

   curl \-s \-X POST \-H "x-api-key: \<key\>" \-H "Content-Type: application/json" \\

     \-d '{"agent\_id":"launch-test","data":{"ready":true}}' https://\<API\_URL\>/v1/state

   \# Must return 201

3\. SEMANTIC API:

   curl \-s \-X POST \-H "x-api-key: \<key\>" \-H "Content-Type: application/json" \\

     \-d '{"agent\_id":"launch-test","content":"Launch readiness test"}' https://\<API\_URL\>/v1/memory/semantic

   \# Must return 201

4\. SEARCH:

   curl \-s \-X POST \-H "x-api-key: \<key\>" \-H "Content-Type: application/json" \\

     \-d '{"query":"launch ready","top\_k":5}' https://\<API\_URL\>/v1/memory/semantic/search

   \# Must return results with similarity \> 0.7

5\. EPISODIC API:

   curl \-s \-X POST \-H "x-api-key: \<key\>" \-H "Content-Type: application/json" \\

     \-d '{"agent\_id":"launch-test","session\_id":"s1","type":"action","content":"Pre-launch test"}' https://\<API\_URL\>/v1/memory/episodic

   \# Must return 201

6\. SDK:

   pip install \-e sdk/ && python \-c "from mnemora import MnemoraClient; print('SDK OK')"

7\. TESTS:

   cd api && python \-m pytest tests/ \-v \--tb=short

   cd sdk && python \-m pytest tests/ \-v \--tb=short

8\. CLOUDWATCH:

   Check dashboard — all metrics green, no errors, latency within targets

Report: For each check, tell me PASS or FAIL. If any fail, do NOT proceed to launch — fix first.

**Checkpoint:** 8/8 PASS required for launch.

---

### **Day 7 Launch Metrics to Track**

| Metric | Target (24h) | How to Check |
| ----- | ----- | ----- |
| GitHub stars | 50+ | GitHub repo page |
| Signups (dashboard users) | 25+ | DynamoDB user table count |
| HN post visible | Yes | Check /newest then /show |
| First external API call | Yes | CloudWatch — filter by non-test tenant\_id |
| Critical bugs reported | 0 | GitHub issues |
| PyPI installs | 10+ | PyPI stats (delayed) |

---

## **Observability & Diagnostics Guide**

**This section is for you, Isaac — non-technical diagnostics.**

### **Your Daily Health Check (2 minutes)**

Go to AWS Console → CloudWatch → Dashboards → MnemoraHealth.

**What to look for:**

| Widget | Green | Yellow | Red |
| ----- | ----- | ----- | ----- |
| Lambda Errors | 0 errors | 1-5 errors | 5+ errors |
| API 5xx | 0 | 1-3 | 3+ |
| API 4xx | Low, stable | Spike (someone hitting bad endpoints) | Sustained spike (possible attack) |
| Lambda Duration p99 | \< 100ms | 100-500ms | \> 500ms |
| Aurora ACU | 0.5-1.0 | 1.0-2.0 | \> 2.0 (cost alert) |
| DynamoDB Throttles | 0 | Any | Sustained |

### **Common Problems and Fix Prompts**

**Problem: High Lambda latency (p99 \> 500ms)**

Lambda latency is high — p99 is over 500ms. Diagnose: (1) Check CloudWatch Logs for the slow function — is it cold starts or actual slow execution? (2) Check if Lambda is making multiple sequential AWS calls that could be parallelized. (3) Check Aurora connection time. (4) Check if Lambda memory is sufficient. Report findings and recommend fix.

**Problem: Aurora ACU climbing above 2**

Aurora ServerlessDatabaseCapacity is at \<X\> ACU. This is above our cost target. Investigate: (1) Check active queries — are there full table scans? (2) Check missing indexes with pg\_stat\_user\_tables. (3) Check connection count — are we leaking connections? (4) Consider adding connection pooling. Report findings and fix.

**Problem: API returning 5xx errors**

We're seeing 5xx errors in the API. Check CloudWatch Logs for the affected Lambda functions. Find the error messages, identify root cause. Common causes: (1) Aurora connection timeout, (2) DynamoDB capacity exceeded, (3) Bedrock API throttling, (4) Lambda timeout. Fix the issue and add a test to prevent regression.

**Problem: Users reporting slow search**

Semantic search is slow for users. Benchmark: (1) Run EXPLAIN ANALYZE on a typical search query. (2) Check if HNSW index is being used (should show "Index Scan using idx\_semantic\_embedding"). (3) Check table size — how many rows? (4) Check ef\_search parameter. (5) If \>100K rows, consider increasing HNSW m parameter. Report findings with query plan output.

**Problem: AWS bill higher than expected**

Run a full cost analysis: (1) Check AWS Cost Explorer for top 5 cost drivers. (2) Compare Aurora ACU-hours this month vs last. (3) Check Bedrock embedding costs. (4) Check NAT Gateway data transfer costs. (5) Check DynamoDB on-demand costs. Create a cost report with optimization recommendations prioritized by savings.

### **Weekly Metrics Review (Prompt)**

Run this every Monday:

Generate a weekly Mnemora health report:

1\. API METRICS (from CloudWatch):

   \- Total API calls this week

   \- Error rate (4xx \+ 5xx / total)

   \- Average latency by endpoint

   \- Peak concurrent Lambda invocations

2\. INFRASTRUCTURE:

   \- Aurora ACU-hours consumed

   \- DynamoDB read/write consumed

   \- S3 storage total

   \- Estimated AWS cost this week

3\. PRODUCT METRICS:

   \- New signups this week

   \- Weekly active users (made API call)

   \- Total memories stored (by type)

   \- Total embeddings generated

   \- Most active agents

4\. HEALTH:

   \- Any downtime incidents?

   \- Any alarms triggered?

   \- Test suite status (all passing?)

Format as a clean table I can share with advisors.

---

## **Short-Term Plan: Days 8-30**

### **Week 2 (Days 8-14): Feedback-Driven Iteration**

Run 10 user feedback calls (30 min each). Fix top 5 pain points. Then:

Implement procedural memory — the 4th memory type. This stores tool definitions, learned workflows, and structured schemas. Use Aurora (relational, not vector). Schema: id, tenant\_id, agent\_id, name, type (tool|workflow|schema), definition (JSONB), version (int), is\_active (bool), created\_at, updated\_at. Endpoints: POST /v1/memory/procedural, GET /v1/memory/procedural/{agent\_id}, PUT /v1/memory/procedural/{id}, DELETE /v1/memory/procedural/{id}. Include versioning so agents can update their tools over time. Write tests.

Implement memory decay: add a confidence field (float, 0-1) to semantic memories. New memories start at 1.0. Every day, run a scheduled Lambda that decreases confidence by a configurable decay\_rate (default 0.01/day). Search results multiply similarity score by confidence. Memories below 0.1 confidence are auto-archived. This prevents stale knowledge from dominating search results. Write tests.

### **Week 3 (Days 15-21): Framework Integration Depth**

Create 5 complete example agents in examples/ directory:

1\. examples/rag-chatbot/ — LangChain RAG chatbot that stores conversation history in Mnemora episodic memory and knowledge in semantic memory

2\. examples/research-agent/ — CrewAI multi-agent research team where agents share findings via Mnemora semantic memory

3\. examples/langgraph-workflow/ — LangGraph stateful workflow using MnemoraCheckpointSaver for persistence

4\. examples/customer-support/ — Support agent that learns from past tickets (episodic → semantic summarization)

5\. examples/coding-agent/ — Agent that stores tool definitions in procedural memory and learned patterns in semantic memory

Each example must: have a README, install in under 2 minutes, be runnable with just an API key, demonstrate at least 2 memory types.

### **Week 4 (Days 22-30): Content \+ Growth Engine**

Use @launch-strategist to create a content calendar for Days 22-30:

Blog posts (publish on blog.mnemora.dev or dev.to):

1\. "Why AI Agents Need a New Kind of Database" — problem-first, include architecture diagram, target 10K reads

2\. "Building a Multi-Agent Research System with Mnemora \+ CrewAI" — tutorial with full code

3\. "How We Built Sub-10ms Agent State on DynamoDB" — technical deep-dive for HN audience

For each post, create the full draft in docs/blog/. Use Mnemora voice: direct, technical, no fluff.

### **30-Day Success Metrics**

| Metric | Day 14 Target | Day 30 Target |
| ----- | ----- | ----- |
| GitHub Stars | 200 | 500 |
| Registered Users | 100 | 300 |
| Weekly Active Users (API calls \> 0\) | 30 | 100 |
| Monthly API Calls (total) | 100K | 500K |
| Framework Integrations Shipped | 3 | 5 |
| Published Blog Posts | 1 | 3 |
| Discord Members | 50 | 150 |
| Paid Conversions ($19+) | 0 | 5-10 |
| NPS Score | N/A | \> 40 |
| Test Coverage | 70% | 80% |
| Total Test Count | 80+ | 120+ |

---

## **Medium-Term Plan: Days 31-90**

### **Month 2 (Days 31-60): Product-Market Fit Sprint**

* Multi-agent coordination: shared memory spaces where multiple agents can read/write  
* Memory graph: relationships between memories (agent A's output is agent B's input)  
* Temporal versioning: full history of every memory change with point-in-time recovery  
* Audit logging for EU AI Act compliance (10-year retention, immutable logs)  
* Stripe billing integration: enforce tier limits, usage-based overage billing  
* Launch paid tiers: $19 Starter, $79 Pro, $299 Scale  
* **Target: first $1K MRR**

### **Month 3 (Days 61-90): Scale or Fundraise Decision**

Analyze:

* Cohort retention: are Week 1 users still active?  
* Conversion funnel: free → starter → pro rates  
* Unit economics: actual AWS cost per user vs projected  
* Sean Ellis test: 40%+ "very disappointed" \= PMF

**If PMF strong:** Raise $500K-1M pre-seed or stay bootstrapped **If PMF weak:** Pivot positioning (database → SDK, agent devs → AI app builders)

### **90-Day Success Metrics**

| Metric | Day 60 Target | Day 90 Target |
| ----- | ----- | ----- |
| GitHub Stars | 1,000 | 2,000 |
| Registered Users | 700 | 1,500 |
| Weekly Active Users | 200 | 400 |
| Monthly API Calls | 2M | 5M |
| MRR | $1,000 | $3,000-5,000 |
| Paid Customers | 20-30 | 50-75 |
| Free-to-Paid Conversion | 3-5% | 5-7% |
| Sean Ellis PMF Score | 30%+ | 40%+ |
| Test Coverage | 85% | 90% |
| Total Test Count | 150+ | 200+ |

---

## **Long-Term Plan: Months 4-12**

### **Months 4-6: Growth Acceleration**

* Hire first engineer (full-stack, strong AWS)  
* Launch Mnemora Cloud managed service  
* Implement database branching for testing/staging  
* Build MCP server: Mnemora as native MCP tool for Claude, ChatGPT  
* Launch "Mnemora for Teams": shared workspaces, team billing  
* **Target: $15K-20K MRR**

### **Months 7-9: Enterprise Readiness**

* SOC 2 Type II compliance  
* SSO/SAML integration  
* VPC peering and private link  
* Multi-region replication (US-East, EU-West, AP-Southeast)  
* Hire second engineer \+ first DevRel  
* Land 3-5 enterprise design partners  
* **Target: $30K-40K MRR**

### **Months 10-12: Market Position**

* Raise Seed round ($2-4M) if trajectory supports  
* Launch Mnemora Analytics: agent behavior patterns, memory utilization, cost optimization  
* Build marketplace for pre-built memory templates  
* Strategic partnerships (AWS Partner Network)  
* **Target: $50K+ MRR, 10K+ users, 5K+ GitHub stars**

### **12-Month Milestone Table**

| Metric | Month 6 | Month 9 | Month 12 |
| ----- | ----- | ----- | ----- |
| MRR | $15-20K | $30-40K | $50K+ |
| Registered Users | 5,000 | 8,000 | 12,000+ |
| Weekly Active Users | 1,000 | 2,000 | 3,500+ |
| GitHub Stars | 4,000 | 6,000 | 8,000+ |
| Team Size | 2 | 4 | 6-8 |
| Paid Customers | 200 | 400 | 700+ |
| Enterprise ($299+) | 10 | 30 | 50+ |
| Monthly API Calls | 20M | 50M | 100M+ |
| Funding Raised | Pre-seed $500K-1M | Preparing Seed | Seed $2-4M |
| ARR Run Rate | $180-240K | $360-480K | $600K+ |

---

## **Risk Mitigation**

| Risk | Severity | Mitigation |
| ----- | ----- | ----- |
| AWS builds competing service | Critical | Move fast on integrations. AWS builds primitives, we build DX. |
| Mem0 adds database features | High | Differentiate on AWS-native (lower cost for AWS shops). |
| Solo founder burnout | High | Timebox 10-12h/day. Automate with AI agents. Seek co-founder Month 2\. |
| Aurora cost spikes | Medium | Monitor ACU daily. Set max ACU limit. Evaluate Neon/Turso if needed. |
| No PMF | Critical | Kill criteria at Day 90\. Do not zombie. |
| Security breach | Critical | Encrypt at rest (KMS) \+ in transit (TLS 1.3). Pen test by Month 3\. |

---

## **Kill Criteria**

**Continue if (by Day 90):** 100+ WAU, 5+ paying customers, 40%+ Sean Ellis, 2+ framework integrations in production, organic growth beyond founder outreach.

**Pivot if (by Day 90):** 50-99 WAU, 1-4 paying customers, different primary use case emerging.

**Shut down if (by Day 90):** \<50 WAU, 0 paying customers, no organic growth, consistent "nice to have" feedback. Archive repo, write post-mortem, move on.

---

## **Summary**

| Timeframe | North Star | Revenue | Key Milestone |
| ----- | ----- | ----- | ----- |
| Day 7 | 25+ signups | $0 | Open source launch |
| Day 30 | 100 WAU | $0-190 | 5 framework integrations |
| Day 90 | 400 WAU | $3-5K MRR | PMF validated |
| Month 6 | 1,000 WAU | $15-20K MRR | First hire |
| Month 12 | 3,500+ WAU | $50K+ MRR | Seed round raised |

---

Eso es todo. Cada prompt está diseñado para copy-paste directo en Claude Code. La secuencia es: prompt → checkpoint → next prompt (o debug prompt si falló). Los prompts de observability y el Weekly Health Report te dan los diagnósticos sin necesidad de ser técnico.

Cuando el sandbox vuelva lo convierto a .docx profesional. Por ahora, copiá esto a un doc y tenés tu playbook operativo.

