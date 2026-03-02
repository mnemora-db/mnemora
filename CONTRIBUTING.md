# Contributing to Mnemora

Thanks for considering a contribution. This guide covers environment setup, testing, and the PR process.

## Development Environment

### Prerequisites

- Python 3.12+
- Node.js 18+ (for CDK and dashboard)
- AWS CLI configured with credentials (for integration tests only)
- Git

### Clone and install

```bash
git clone https://github.com/mnemora-dev/mnemora.git
cd mnemora
```

### API handlers (Python)

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### SDK (Python)

```bash
cd sdk
pip install -e ".[dev]"
```

### Infrastructure (TypeScript CDK)

```bash
cd infra
npm install
```

### Dashboard (Next.js)

```bash
cd dashboard
npm install
```

### Environment variables

Copy the example and fill in your values:

```bash
cp .env.example .env
```

For unit tests, the only required variable is automatically set by the test fixtures:

```
MNEMORA_TEST_API_KEY=test-key-for-unit-tests
MNEMORA_TEST_TENANT=test-tenant
```

Integration tests require a deployed stack. See `docs/deployment-outputs.md` for the values CDK outputs after deploy.

## Running Tests

### Unit tests (no AWS required)

```bash
# API handlers — 330 tests
cd api && python3 -m pytest tests/ -v

# SDK — 116 tests
cd sdk && python3 -m pytest tests/ -v
```

### Linting

```bash
# Python — ruff for linting and formatting
cd api && ruff check . && ruff format --check .
cd sdk && ruff check . && ruff format --check .

# TypeScript — strict mode type checking
cd infra && npx tsc --noEmit
cd dashboard && npx tsc --noEmit
```

### Dashboard build

```bash
cd dashboard && npm run build
```

### Integration tests (requires deployed stack)

Set `MNEMORA_API_URL` and `MNEMORA_API_KEY` in your environment, then run the integration test scripts in `api/tests/`.

## Code Style

### Python

- **Linter/formatter:** [ruff](https://docs.astral.sh/ruff/) (configured in `pyproject.toml`)
- **Type hints:** Required on all function signatures
- **Models:** Pydantic v2 for all request/response validation
- **Docstrings:** Required on all public functions (Google style)
- **Imports:** `from __future__ import annotations` at the top of every module

### TypeScript

- **Strict mode** enabled (`"strict": true` in `tsconfig.json`)
- **No `any` types** — use proper typing
- **CDK constructs** follow L2 construct patterns

### General

- All API responses follow: `{ "data": ..., "meta": { "request_id": "...", "latency_ms": N } }`
- All errors follow: `{ "error": { "code": "...", "message": "..." }, "meta": { ... } }`
- Use parameterized queries for all database operations — never string interpolation
- Never log API keys, memory content, or PII

## Pull Request Process

### Before opening a PR

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes, following the code style above.

3. Run the full check suite:
   ```bash
   # Python
   cd api && ruff check . && ruff format --check . && python3 -m pytest tests/ -v
   cd sdk && ruff check . && ruff format --check . && python3 -m pytest tests/ -v

   # TypeScript
   cd infra && npx tsc --noEmit
   cd dashboard && npx tsc --noEmit
   ```

4. All checks must pass before submitting.

### PR checklist

- [ ] Tests added or updated for the change
- [ ] `ruff check` passes with no errors
- [ ] `pytest` passes with no failures
- [ ] `tsc --noEmit` passes (if TypeScript was changed)
- [ ] No hardcoded secrets, API keys, or account IDs
- [ ] Docstrings added for new public functions
- [ ] Type hints on all function signatures

### Review process

1. Open a PR against `main` with a clear description of the change.
2. At least one maintainer review is required.
3. CI must pass (lint, test, type-check).
4. Squash-merge is preferred for feature branches.

## Reporting Issues

Use the [GitHub issue templates](.github/ISSUE_TEMPLATE/) for:
- **Bug reports** — include reproduction steps and expected vs actual behavior
- **Feature requests** — describe the use case, not just the solution

## License

By contributing, you agree that your contributions will be licensed under:
- **SDK (`sdk/`):** MIT License
- **Infrastructure (`infra/`, `api/`):** Business Source License 1.1
- **Dashboard (`dashboard/`):** MIT License
