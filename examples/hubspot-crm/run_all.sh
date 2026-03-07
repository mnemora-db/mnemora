#!/usr/bin/env bash
# End-to-end demo: seed HubSpot, sync to Mnemora, run agents, run eval.
#
# Usage:
#   ./run_all.sh          # run demos + eval (assumes data already synced)
#   ./run_all.sh --seed   # seed HubSpot first, then run everything

set -euo pipefail
cd "$(dirname "$0")"

# ── Check .env ──────────────────────────────────────────────────────
if [ ! -f .env ]; then
    echo "ERROR: .env file not found. Copy .env.example and fill in your keys:"
    echo "  cp .env.example .env"
    exit 1
fi

echo "=== Mnemora + HubSpot CRM Demo ==="
echo ""

# ── Seed HubSpot (optional) ────────────────────────────────────────
if [[ "${1:-}" == "--seed" ]]; then
    echo "--- Step 1: Seeding HubSpot with test data ---"
    python seed_hubspot_data.py
    echo ""
fi

# ── Sync HubSpot → Mnemora ─────────────────────────────────────────
echo "--- Step 2: Syncing HubSpot data to Mnemora ---"
python hubspot_sync.py
echo ""

# ── Support Agent (auto mode) ──────────────────────────────────────
echo "--- Step 3: Support Agent Demo ---"
python demo_support_agent.py --auto
echo ""

# ── Sales Agent (auto mode) ────────────────────────────────────────
echo "--- Step 4: Sales Agent Demo ---"
python demo_sales_agent.py --auto
echo ""

# ── Eval ────────────────────────────────────────────────────────────
echo "--- Step 5: Quality Eval ---"
python eval_quality.py
echo ""

echo "=== Demo Complete ==="
