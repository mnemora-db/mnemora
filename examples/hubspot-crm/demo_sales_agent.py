"""Sales pipeline assistant demo — side-by-side with/without Mnemora context.

Helps with pipeline management by searching Mnemora for deal context,
contact history, and company info, then feeding it to Claude for
informed sales advice.

Usage:
    python demo_sales_agent.py          # interactive mode
    python demo_sales_agent.py --auto   # runs pre-set questions
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import Any

import anthropic
from dotenv import load_dotenv
from mnemora import MnemoraSync
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from hubspot_sync import HubSpotSync

console = Console()

AGENT_ID = "hubspot-sales"

SYSTEM_PROMPT_BASE = (
    "You are a sales assistant for a SaaS company. "
    "Help the sales rep with pipeline questions, deal strategy, "
    "and meeting prep. Be specific and actionable."
)

SYSTEM_PROMPT_WITH_MEMORY = (
    "You are a sales assistant for a SaaS company. "
    "You have access to the full CRM — deals, contacts, companies, and history. "
    "Use this data to give specific, actionable advice. Reference deal names, "
    "amounts, stages, contact names, and company details. "
    "Do NOT say you looked things up — just present the info naturally."
)

AUTO_QUESTIONS = [
    "What's the status of the Acme Corp deal?",
    "Which deals are closing this month?",
    "Prepare me for my call with Jane at GlobalTech.",
]


def get_response_without_memory(
    client: anthropic.Anthropic, question: str
) -> str:
    """Get a Claude response with no CRM context."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        system=SYSTEM_PROMPT_BASE,
        messages=[{"role": "user", "content": question}],
    )
    return response.content[0].text


def get_response_with_memory(
    client: anthropic.Anthropic,
    mnemora: MnemoraSync,
    question: str,
) -> tuple[str, list[Any]]:
    """Get a Claude response augmented with CRM context from Mnemora."""
    # Search semantic memory for relevant CRM data
    results = mnemora.search_memory(
        query=question,
        agent_id=AGENT_ID,
        top_k=8,
        threshold=0.3,
    )

    context_parts: list[str] = []
    for r in results:
        score = f"{r.similarity_score:.2f}" if r.similarity_score else "N/A"
        context_parts.append(f"[similarity={score}] {r.content}")

    # Check deal state for pipeline summaries
    try:
        sessions = mnemora.list_sessions(AGENT_ID)
        deal_sessions = [s for s in sessions if s.startswith("deal-")]
        for session_id in deal_sessions[:10]:
            try:
                state = mnemora.get_state(AGENT_ID, session_id=session_id)
                if state and state.data:
                    d = state.data
                    context_parts.append(
                        f"[pipeline] Deal: {d.get('deal_name', 'N/A')}, "
                        f"Amount: ${d.get('amount', 'N/A')}, "
                        f"Stage: {d.get('stage', 'N/A')}, "
                        f"Close: {d.get('closedate', 'N/A')}"
                    )
            except Exception:
                continue
    except Exception:
        pass

    context_block = "\n".join(context_parts) if context_parts else "No CRM data found."

    augmented_prompt = (
        f"CRM CONTEXT (from memory search):\n{context_block}\n\n"
        f"SALES REP QUESTION:\n{question}"
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        system=SYSTEM_PROMPT_WITH_MEMORY,
        messages=[{"role": "user", "content": augmented_prompt}],
    )

    return response.content[0].text, results


def log_interaction(
    mnemora: MnemoraSync, question: str, response: str
) -> None:
    """Store the sales interaction as an episode in Mnemora."""
    mnemora.store_episode(
        agent_id=AGENT_ID,
        session_id=f"sales-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        type="conversation",
        content={
            "rep_question": question,
            "assistant_response": response,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


def display_comparison(question: str, without: str, with_mem: str) -> None:
    """Display side-by-side comparison using rich panels."""
    console.print(f"\n[bold yellow]Sales Rep:[/] {question}\n")

    left = Panel(
        Text(without, style="dim"),
        title="[red]WITHOUT Mnemora[/]",
        border_style="red",
        width=60,
        padding=(1, 2),
    )
    right = Panel(
        Text(with_mem),
        title="[green]WITH Mnemora[/]",
        border_style="green",
        width=60,
        padding=(1, 2),
    )

    console.print(Columns([left, right], padding=2))


def sync_if_needed(mnemora: MnemoraSync, hubspot_token: str) -> None:
    """Sync HubSpot data if no memories exist yet."""
    try:
        results = mnemora.search_memory(
            query="deal", agent_id=AGENT_ID, top_k=1
        )
        if results:
            console.print("[dim]CRM data already synced, skipping.[/]")
            return
    except Exception:
        pass

    console.print("[cyan]Syncing HubSpot data to Mnemora...[/]")
    sync = HubSpotSync(hubspot_token, mnemora)
    try:
        counts = sync.sync_all(agent_id=AGENT_ID)
        console.print(f"[green]Synced:[/] {counts}")
    finally:
        sync.close()


def run_interactive(
    claude: anthropic.Anthropic, mnemora: MnemoraSync
) -> None:
    """Interactive sales assistant loop."""
    console.print(
        "\n[bold]Sales Agent Demo[/] — type a sales question "
        "(or 'quit' to exit)\n"
    )

    while True:
        question = console.input("[bold cyan]Sales Rep > [/]").strip()
        if not question or question.lower() == "quit":
            break

        with console.status("[dim]Generating responses..."):
            without = get_response_without_memory(claude, question)
            with_mem, _ = get_response_with_memory(claude, mnemora, question)
            log_interaction(mnemora, question, with_mem)

        display_comparison(question, without, with_mem)


def run_auto(claude: anthropic.Anthropic, mnemora: MnemoraSync) -> None:
    """Run pre-set questions non-interactively."""
    console.print("\n[bold]Sales Agent Demo (auto mode)[/]\n")

    for question in AUTO_QUESTIONS:
        with console.status(f"[dim]Processing: {question[:50]}..."):
            without = get_response_without_memory(claude, question)
            with_mem, _ = get_response_with_memory(claude, mnemora, question)
            log_interaction(mnemora, question, with_mem)

        display_comparison(question, without, with_mem)
        console.print("[dim]" + "─" * 120 + "[/]")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Sales agent demo")
    parser.add_argument("--auto", action="store_true", help="Run pre-set questions")
    args = parser.parse_args()

    hubspot_token = os.environ.get("HUBSPOT_API_KEY", "")
    mnemora_key = os.environ.get("MNEMORA_API_KEY", "")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not mnemora_key or not anthropic_key:
        console.print("[red]Missing MNEMORA_API_KEY or ANTHROPIC_API_KEY in .env[/]")
        sys.exit(1)

    claude = anthropic.Anthropic(api_key=anthropic_key)

    with MnemoraSync(api_key=mnemora_key) as mnemora:
        if hubspot_token:
            sync_if_needed(mnemora, hubspot_token)
        else:
            console.print("[yellow]No HUBSPOT_API_KEY — skipping sync, using existing data.[/]")

        if args.auto:
            run_auto(claude, mnemora)
        else:
            run_interactive(claude, mnemora)

    console.print("\n[dim]Done.[/]")


if __name__ == "__main__":
    main()
