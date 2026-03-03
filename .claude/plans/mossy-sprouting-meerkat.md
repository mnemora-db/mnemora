# Plan: API Key Self-Service System

## Context
Users can sign in via GitHub OAuth but have no way to create or manage API keys. The dashboard shows hardcoded mock data. The Lambda authorizer validates keys from env vars only. We need: dashboard creates keys → hashes stored in DynamoDB → Lambda authorizer validates against DynamoDB.

**Constraint:** Do NOT touch existing Lambda functions, API Gateway, VPC, or security groups. Only add the new users table, new dashboard routes, and update the authorizer handler code.

## Changes

### 1. CDK: Add Users DynamoDB Table
**File:** `infra/lib/mnemora-stack.ts`

Add after existing `stateTable` GSI (line ~103), before Aurora section (line ~105):
- New `usersTable`: `mnemora-users-{stage}`, PK: `github_id` (STRING), no SK
- GSI `api-key-index` on `api_key_hash` (STRING) — for O(1) authorizer lookup
- PAY_PER_REQUEST, point-in-time recovery, same removal policy pattern
- Add `USERS_TABLE_NAME` to `commonEnv` (line ~192)
- Grant `authFn` read access to `usersTable` (after existing line 314: `this.stateTable.grantReadData(authFn)`)
- Add `usersTable` as public property + CfnOutputs

### 2. Install AWS SDK in Dashboard
```bash
cd dashboard && npm install @aws-sdk/client-dynamodb @aws-sdk/lib-dynamodb
```

### 3. Dashboard API Route
**New file:** `dashboard/app/api/keys/route.ts`

- **POST**: Generate `mnm_` + 16 random hex bytes, SHA-256 hash, store in users table (github_id, api_key_hash, api_key_prefix, tier=free, email, github_username, created_at). Return plaintext key once.
- **GET**: Query by github_id, return masked key + metadata. Never return hash.
- **DELETE**: Remove api_key_hash/api_key_prefix from user record. Return 204.

All routes check `getServerSession(authOptions)` first.

### 4. Dashboard UI Component
**New file:** `dashboard/components/api-key-manager.tsx`

Client component that:
- Fetches GET /api/keys on mount
- Shows "Create API Key" if no key exists
- On create: POST /api/keys → shows plaintext key with copy button + "won't be shown again" warning
- If key exists: shows masked key + "Revoke" button
- On revoke: DELETE /api/keys → resets state

### 5. Update Dashboard Page
**File:** `dashboard/app/dashboard/page.tsx`

Replace `<ApiKeyCard maskedKey="mnm_****...****7f3a" createdLabel="5 days ago" />` with `<ApiKeyManager />`.

### 6. Update Lambda Authorizer
**File:** `api/handlers/auth.py`

Update `_resolve_tenant()`:
1. Check env-var test keys first (existing behavior, fast)
2. If no match: query DynamoDB users table GSI `api-key-index` where `api_key_hash = SHA256(key)`
3. If found: return `github:<github_id>` as tenant_id
4. Add lazy-init boto3 client (only created on first DynamoDB lookup)

### 7. Update Authorizer Tests
**File:** `api/tests/test_authorizer.py`

- Add tests mocking boto3 DynamoDB for the new lookup path
- Existing tests must still pass (env-var fallback)

## Verification
1. `cd infra && npx tsc --noEmit` — TS check
2. `cd infra && npx cdk synth --quiet` — CDK synth
3. `cd api && python -m pytest tests/ -v` — auth tests pass
4. `cd dashboard && npm run build` — Next.js build
5. `cd infra && npx cdk deploy --require-approval never` — deploy users table
6. `vercel --prod --yes` — deploy dashboard
7. Git push
