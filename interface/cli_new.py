"""interface/cli_new.py — Event-Driven Terminal UI for JARVIS vNext++.

Thin I/O interface layer.
Receives typed BaseEvent objects from Jarvis Core.
Renders ThinkingEvent with dimmed text styling and FinalResponse tokens cleanly.
"""

from __future__ import annotations

import os
import sys
import asyncio
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from rich.console import Console
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    PROMPT_AVAILABLE = True
except ImportError:
    PROMPT_AVAILABLE = False

from core.jarvis_core import jarvis_core
from core.events import (
    ThinkingEvent,
    PlannerEvent,
    ExecutionEvent,
    VerificationEvent,
    FinalResponseToken,
    FinalResponse,
)

console = Console() if RICH_AVAILABLE else None


def print_banner() -> None:
    banner = """
  +---------------------------------------------------+
  |                                                   |
  |              J A R V I S                          |
  |         vNext++ AGI Operating System              |
  |                                                   |
  +---------------------------------------------------+

  Type 'quit' to exit
"""
    print(banner, flush=True)


class CLI:
    def __init__(self):
        self._running = True
        if PROMPT_AVAILABLE:
            history_path = str(Path.home() / ".jarvis_history")
            self._session = PromptSession(
                history=FileHistory(history_path),
                auto_suggest=AutoSuggestFromHistory(),
            )
        else:
            self._session = None

    def get_input(self) -> str:
        if PROMPT_AVAILABLE:
            try:
                return self._session.prompt("You: ")
            except (EOFError, KeyboardInterrupt):
                return ""
        else:
            try:
                return input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                return ""

    async def handle_streaming(self, user_input: str) -> None:
        """Stream events from Jarvis Core."""
        print("Jarvis: ", end="", flush=True)

        async for event in jarvis_core.process_stream(user_input):
            if isinstance(event, ThinkingEvent):
                # Render thinking tokens as dimmed text
                if RICH_AVAILABLE:
                    console.print(f"[dim]{event.text}[/dim]", end="", flush=True)
                else:
                    print(f"({event.text})", end="", flush=True)

            elif isinstance(event, FinalResponseToken):
                print(event.token, end="", flush=True)

            elif isinstance(event, FinalResponse):
                if not event.text:
                    print()

        print()

    async def run(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")
        print_banner()
        jarvis_core.boot()

        while self._running:
            try:
                user_input = self.get_input()
                if not user_input:
                    continue

                if user_input.lower().strip() in ("quit", "exit", "q"):
                    self._running = False
                    await jarvis_core.shutdown()
                    break

                await self.handle_streaming(user_input)

            except KeyboardInterrupt:
                self._running = False
                await jarvis_core.shutdown()
                break


def main() -> None:
    cli = CLI()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(cli.run())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
