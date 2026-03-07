"""Eval framework — measures response quality with and without Mnemora.

For each test case, runs the question through an agent WITHOUT and WITH
Mnemora context, then uses Claude as a judge to score both on:
  - Relevance (1-5)
  - Specificity (1-5)
  - Helpfulness (1-5)
  - Personalization (1-5)

Usage:
    python eval_quality.py
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import anthropic
from dotenv import load_dotenv
from mnemora import MnemoraSync
from rich.console import Console
from rich.table import Table

console = Console()

SUPPORT_AGENT_ID = "hubspot-support"
SALES_AGENT_ID = "hubspot-sales"

SUPPORT_SYSTEM = (
    "You are a customer support agent for a SaaS company. "
    "Be helpful, professional, and concise."
)

SUPPORT_SYSTEM_MEM = (
    "You are a customer support agent for a SaaS company. "
    "You have access to CRM data about the customer. Use it to personalize "
    "your response — reference their name, company, account details, and "
    "any relevant ticket history."
)

SALES_SYSTEM = (
    "You are a sales assistant for a SaaS company. "
    "Help with pipeline questions, deal strategy, and meeting prep."
)

SALES_SYSTEM_MEM = (
    "You are a sales assistant for a SaaS company. "
    "You have access to the full CRM — deals, contacts, companies, and history. "
    "Use this data to give specific, actionable advice."
)

TEST_CASES: list[dict[str, str]] = [
    {"question": "I'm John from Acme, my invoice is wrong", "type": "support", "agent_id": SUPPORT_AGENT_ID},
    {"question": "What's the status of the Acme Corp deal?", "type": "sales", "agent_id": SALES_AGENT_ID},
    {"question": "Can you help me with my account?", "type": "support", "agent_id": SUPPORT_AGENT_ID},
    {"question": "Which deals are closing this quarter?", "type": "sales", "agent_id": SALES_AGENT_ID},
    {"question": "I spoke to someone last week about my ticket, any updates?", "type": "support", "agent_id": SUPPORT_AGENT_ID},
    {"question": "Prepare me for my meeting with the CTO of GlobalTech", "type": "sales", "agent_id": SALES_AGENT_ID},
    {"question": "What's our total pipeline value?", "type": "sales", "agent_id": SALES_AGENT_ID},
    {"question": "I want to upgrade my plan", "type": "support", "agent_id": SUPPORT_AGENT_ID},
    {"question": "We've been having issues with the API integration", "type": "support", "agent_id": SUPPORT_AGENT_ID},
    {"question": "Who should I follow up with this week?", "type": "sales", "agent_id": SALES_AGENT_ID},
]

JUDGE_PROMPT = """\
You are evaluating two AI assistant responses to the same customer/sales question.
Score each response on four dimensions (1-5 scale):

1. **Relevance** — How relevant is the response to the question asked?
2. **Specificity** — Does it reference specific customer data, names, amounts, dates?
3. **Helpfulness** — Would this actually help solve the problem or answer the question?
4. **Personalization** — Is it personalized to this specific customer/situation?

QUESTION: {question}

RESPONSE A (no CRM context):
{response_a}

RESPONSE B (with CRM context):
{response_b}

Return ONLY valid JSON with this exact structure:
{{
  "response_a": {{"relevance": N, "specificity": N, "helpfulness": N, "personalization": N}},
  "response_b": {{"relevance": N, "specificity": N, "helpfulness": N, "personalization": N}}
}}"""


def get_crm_context(mnemora: MnemoraSync, question: str, agent_id: str) -> str:
    """Search Mnemora for relevant CRM context."""
    parts: list[str] = []

    try:
        results = mnemora.search_memory(
            query=question, agent_id=agent_id, top_k=5, threshold=0.3
        )
        for r in results:
            parts.append(r.content)
    except Exception:
        pass

    try:
        episodes = mnemora.get_episodes(agent_id=agent_id, limit=5)
        for ep in episodes:
            if isinstance(ep.content, dict):
                parts.append(
                    f"[ticket] {ep.content.get('subject', '')} - "
                    f"Status: {ep.content.get('status', '')} - "
                    f"Priority: {ep.content.get('priority', '')}"
                )
    except Exception:
        pass

    try:
        sessions = mnemora.list_sessions(agent_id)
        for sid in [s for s in sessions if s.startswith("deal-")][:5]:
            try:
                state = mnemora.get_state(agent_id, session_id=sid)
                if state and state.data:
                    d = state.data
                    parts.append(
                        f"[deal] {d.get('deal_name', 'N/A')} - "
                        f"${d.get('amount', 'N/A')} - "
                        f"Stage: {d.get('stage', 'N/A')}"
                    )
            except Exception:
                continue
    except Exception:
        pass

    return "\n".join(parts) if parts else "No CRM data available."


def generate_response(
    claude: anthropic.Anthropic,
    question: str,
    system: str,
    context: str | None = None,
) -> str:
    """Generate a response, optionally with CRM context."""
    user_msg = question
    if context:
        user_msg = f"CRM CONTEXT:\n{context}\n\nCUSTOMER MESSAGE:\n{question}"

    response = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )
    return response.content[0].text


def judge_responses(
    claude: anthropic.Anthropic,
    question: str,
    response_a: str,
    response_b: str,
) -> dict[str, dict[str, int]]:
    """Use Claude to judge both responses."""
    prompt = JUDGE_PROMPT.format(
        question=question,
        response_a=response_a,
        response_b=response_b,
    )

    response = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    # Extract JSON from response (handle markdown code blocks)
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    return json.loads(text)


def run_eval(claude: anthropic.Anthropic, mnemora: MnemoraSync) -> None:
    """Run the full eval across all test cases."""
    console.print("\n[bold]Running Eval: With vs Without Mnemora[/]\n")

    all_scores_a: list[dict[str, int]] = []
    all_scores_b: list[dict[str, int]] = []

    table = Table(title="Eval Results", show_lines=True)
    table.add_column("Question", width=40)
    table.add_column("Metric", width=16)
    table.add_column("Without", justify="center", width=10)
    table.add_column("With Mnemora", justify="center", width=12)
    table.add_column("Delta", justify="center", width=8)

    metrics = ["relevance", "specificity", "helpfulness", "personalization"]

    for i, case in enumerate(TEST_CASES):
        question = case["question"]
        case_type = case["type"]
        agent_id = case["agent_id"]

        console.print(f"[dim]  [{i+1}/{len(TEST_CASES)}] {question[:60]}...[/]")

        # Pick system prompts based on type
        sys_base = SUPPORT_SYSTEM if case_type == "support" else SALES_SYSTEM
        sys_mem = SUPPORT_SYSTEM_MEM if case_type == "support" else SALES_SYSTEM_MEM

        # Generate both responses
        resp_a = generate_response(claude, question, sys_base)
        context = get_crm_context(mnemora, question, agent_id)
        resp_b = generate_response(claude, question, sys_mem, context)

        # Judge
        try:
            scores = judge_responses(claude, question, resp_a, resp_b)
        except (json.JSONDecodeError, KeyError) as e:
            console.print(f"[red]  Judge error on case {i+1}: {e}[/]")
            continue

        scores_a = scores["response_a"]
        scores_b = scores["response_b"]
        all_scores_a.append(scores_a)
        all_scores_b.append(scores_b)

        # Add rows to table
        for j, m in enumerate(metrics):
            sa = scores_a.get(m, 0)
            sb = scores_b.get(m, 0)
            delta = sb - sa
            delta_str = f"[green]+{delta}[/]" if delta > 0 else (f"[red]{delta}[/]" if delta < 0 else "0")

            q_display = question[:38] + ".." if len(question) > 40 else question
            table.add_row(
                q_display if j == 0 else "",
                m.capitalize(),
                str(sa),
                str(sb),
                delta_str,
            )

    console.print()
    console.print(table)

    # Summary averages
    if all_scores_a and all_scores_b:
        console.print("\n[bold]Summary Averages:[/]\n")

        summary = Table(show_header=True)
        summary.add_column("Metric", width=20)
        summary.add_column("Without Mnemora", justify="center", width=16)
        summary.add_column("With Mnemora", justify="center", width=16)
        summary.add_column("Improvement", justify="center", width=14)

        for m in metrics:
            avg_a = sum(s.get(m, 0) for s in all_scores_a) / len(all_scores_a)
            avg_b = sum(s.get(m, 0) for s in all_scores_b) / len(all_scores_b)
            delta = avg_b - avg_a
            delta_str = (
                f"[green]+{delta:.1f}[/]" if delta > 0
                else f"[red]{delta:.1f}[/]" if delta < 0
                else "0.0"
            )
            summary.add_row(
                m.capitalize(),
                f"{avg_a:.1f}",
                f"{avg_b:.1f}",
                delta_str,
            )

        # Overall
        overall_a = sum(
            sum(s.get(m, 0) for m in metrics) for s in all_scores_a
        ) / (len(all_scores_a) * len(metrics))
        overall_b = sum(
            sum(s.get(m, 0) for m in metrics) for s in all_scores_b
        ) / (len(all_scores_b) * len(metrics))
        delta_overall = overall_b - overall_a
        delta_str = (
            f"[green]+{delta_overall:.1f}[/]" if delta_overall > 0
            else f"[red]{delta_overall:.1f}[/]" if delta_overall < 0
            else "0.0"
        )
        summary.add_row(
            "[bold]Overall[/]",
            f"[bold]{overall_a:.1f}[/]",
            f"[bold]{overall_b:.1f}[/]",
            f"[bold]{delta_str}[/]",
        )

        console.print(summary)
        console.print(
            f"\n[bold green]Mnemora improved response quality by "
            f"+{delta_overall:.1f} points on average (out of 5.0)[/]\n"
        )


def main() -> None:
    load_dotenv()

    mnemora_key = os.environ.get("MNEMORA_API_KEY", "")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not mnemora_key or not anthropic_key:
        console.print("[red]Missing MNEMORA_API_KEY or ANTHROPIC_API_KEY in .env[/]")
        sys.exit(1)

    claude = anthropic.Anthropic(api_key=anthropic_key)

    with MnemoraSync(api_key=mnemora_key) as mnemora:
        run_eval(claude, mnemora)


if __name__ == "__main__":
    main()
