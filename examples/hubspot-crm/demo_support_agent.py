"""Support agent demo — side-by-side comparison with/without Mnemora context.

Handles customer inquiries by searching Mnemora for CRM context (contacts,
tickets, companies) and feeding it to Claude alongside the user's message.
Shows the difference between a context-free response and a memory-augmented one.

Usage:
    python demo_support_agent.py          # interactive mode
    python demo_support_agent.py --auto   # runs pre-set questions
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

AGENT_ID = "hubspot-support"

SYSTEM_PROMPT_BASE = (
    "You are a customer support agent for a SaaS company. "
    "Be helpful, professional, and concise. "
    "If you don't have enough information, ask clarifying questions."
)

SYSTEM_PROMPT_WITH_MEMORY = (
    "You are a customer support agent for a SaaS company. "
    "Be helpful, professional, and concise. "
    "You have access to CRM data about the customer. Use it to personalize "
    "your response — reference their name, company, account details, and "
    "any relevant ticket history. Do NOT mention that you looked up their data "
    "in a database — just use the knowledge naturally, as if you know them."
)

AUTO_QUESTIONS = [
    "Hi, I'm John from Acme Corp. My invoice #4521 is wrong.",
    "I spoke to someone last week about my API integration issue, any updates?",
    "Can you help me with my account? I want to upgrade my plan.",
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
    """Get a Claude response augmented with CRM context from Mnemora.

    Returns:
        Tuple of (response_text, search_results_used).
    """
    # Search across all memory types for relevant CRM context
    results = mnemora.search_memory(
        query=question,
        agent_id=AGENT_ID,
        top_k=5,
        threshold=0.3,
    )

    # Build context block from search results
    context_parts: list[str] = []
    for r in results:
        score = f"{r.similarity_score:.2f}" if r.similarity_score else "N/A"
        context_parts.append(f"[similarity={score}] {r.content}")

    # Also check for recent episodes (ticket history)
    try:
        episodes = mnemora.get_episodes(
            agent_id=AGENT_ID,
            type="observation",
            limit=5,
        )
        for ep in episodes:
            if isinstance(ep.content, dict):
                subj = ep.content.get("subject", "")
                status = ep.content.get("status", "")
                priority = ep.content.get("priority", "")
                context_parts.append(
                    f"[ticket] Subject: {subj}, Status: {status}, Priority: {priority}"
                )
    except Exception:
        pass  # Episodes might not exist yet

    context_block = "\n".join(context_parts) if context_parts else "No CRM data found."

    augmented_prompt = (
        f"CRM CONTEXT (from memory search):\n{context_block}\n\n"
        f"CUSTOMER MESSAGE:\n{question}"
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
    """Store the support interaction as an episode in Mnemora."""
    mnemora.store_episode(
        agent_id=AGENT_ID,
        session_id=f"support-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        type="conversation",
        content={
            "customer_message": question,
            "agent_response": response,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


def display_comparison(question: str, without: str, with_mem: str) -> None:
    """Display side-by-side comparison using rich panels."""
    console.print(f"\n[bold yellow]Customer:[/] {question}\n")

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
            query="contact", agent_id=AGENT_ID, top_k=1
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
    """Interactive support agent loop."""
    console.print(
        "\n[bold]Support Agent Demo[/] — type a customer message "
        "(or 'quit' to exit)\n"
    )

    while True:
        question = console.input("[bold cyan]Customer > [/]").strip()
        if not question or question.lower() == "quit":
            break

        with console.status("[dim]Generating responses..."):
            without = get_response_without_memory(claude, question)
            with_mem, _ = get_response_with_memory(claude, mnemora, question)
            log_interaction(mnemora, question, with_mem)

        display_comparison(question, without, with_mem)


def run_auto(claude: anthropic.Anthropic, mnemora: MnemoraSync) -> None:
    """Run pre-set questions non-interactively."""
    console.print("\n[bold]Support Agent Demo (auto mode)[/]\n")

    for question in AUTO_QUESTIONS:
        with console.status(f"[dim]Processing: {question[:50]}..."):
            without = get_response_without_memory(claude, question)
            with_mem, _ = get_response_with_memory(claude, mnemora, question)
            log_interaction(mnemora, question, with_mem)

        display_comparison(question, without, with_mem)
        console.print("[dim]" + "─" * 120 + "[/]")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Support agent demo")
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
