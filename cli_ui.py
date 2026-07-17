"""JARVIS CLI — Rich terminal interface.

All output goes through Rich. All input goes through prompt_toolkit.
No business logic — everything delegates to app.py JARVIS class.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
import time
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML

if TYPE_CHECKING:
    from app import JARVIS

console = Console()

PROMPT_STYLE = Style.from_dict({
    "prompt": "#ff6ec7 bold",
})

COMMANDS = [
    "health", "tools", "traces", "debug", "debug on", "debug off",
    "settings", "memory", "show memories", "remember", "forget",
    "ollama", "stats", "clear", "help", "exit", "quit",
    "vision", "screen", "desktop",
]

completer = WordCompleter(COMMANDS, ignore_case=True)


class TypingEffect:
    """Stream text character-by-character with interruption."""

    def __init__(self, spd: float = 0.008):
        self._speed = spd
        self._interrupted = False

    def print(self, text: str, style: str = ""):
        self._interrupted = False
        chars = list(text)
        buf = ""
        for char in chars:
            if self._interrupted:
                buf += "".join(chars[chars.index(char):])
                break
            buf += char
            console.print(char, end="", style=style or None, highlight=False)
            time.sleep(self._speed)
        if not self._interrupted:
            console.print()
        else:
            remaining = text[len(buf):]
            if remaining:
                console.print(remaining, style=style or None)
            else:
                console.print()

    def interrupt(self):
        self._interrupted = True


class TextMode:
    """Rich terminal interface for JARVIS.

    Wraps app.py JARVIS.handle() with Rich formatting,
    prompt_toolkit input, and typing effect.
    """

    def __init__(self, jarvis: JARVIS):
        self._jarvis = jarvis
        self._typing = TypingEffect()
        self._session = PromptSession(
            history=InMemoryHistory(),
            completer=completer,
            style=PROMPT_STYLE,
        )
        self._debug_mode = False

    def run(self):
        self._print_banner()
        while True:
            try:
                user_input = self._session.prompt(
                    HTML("<ansimagenta>[</ansimagenta><ansibold>JARVIS</ansibold><ansimagenta>] > </ansimagenta>"),
                    completer=completer,
                ).strip()
            except (EOFError, KeyboardInterrupt):
                console.print()
                self._shutdown()
                break

            if not user_input:
                continue

            cmd = user_input.lower()

            if cmd in ("exit", "quit", "q", "bye"):
                self._shutdown()
                break

            if self._handle_command(cmd, user_input):
                continue

            self._process_input(user_input)

    def _print_banner(self):
        os.system("cls" if os.name == "nt" else "clear")
        banner = Text()
        banner.append("  ╔═══════════════════════════════════════════════════╗\n", style="bold #ff6ec7")
        banner.append("  ║                                                   ║\n", style="bold #ff6ec7")
        banner.append("  ║          ", style="bold #ff6ec7")
        banner.append("J A R V I S", style="bold white")
        banner.append("                          ║\n", style="bold #ff6ec7")
        banner.append("  ║          ", style="bold #ff6ec7")
        banner.append("CLI Terminal", style="dim white")
        banner.append("                           ║\n", style="bold #ff6ec7")
        banner.append("  ║                                                   ║\n", style="bold #ff6ec7")
        banner.append("  ╚═══════════════════════════════════════════════════╝\n", style="bold #ff6ec7")
        console.print(banner)

        health = self._jarvis.get_health()
        status = Table(show_header=False, box=None, padding=(0, 2))
        status.add_column("key", style="dim")
        status.add_column("value")
        for key, ready in [
            ("NLP", health.get("nlp_ready")),
            ("Execution", health.get("execution_ready")),
            ("Router", health.get("router_ready")),
            ("Memory", health.get("memory_ready")),
            ("Knowledge", health.get("knowledge_ready")),
        ]:
            icon = "[green]ON[/green]" if ready else "[red]OFF[/red]"
            status.add_row(f"  {key}", icon)
        console.print(status)
        console.print()
        console.print(
            "  [dim]Type [bold]help[/bold] for commands, [bold]exit[/bold] to quit[/dim]\n"
        )

    def _handle_command(self, cmd: str, raw: str) -> bool:
        if cmd == "help":
            self._show_help()
            return True
        if cmd == "clear":
            os.system("cls" if os.name == "nt" else "clear")
            return True
        if cmd == "health":
            self._show_health()
            return True
        if cmd == "tools":
            self._show_tools()
            return True
        if cmd == "traces":
            self._show_traces()
            return True
        if cmd in ("debug", "debug on"):
            self._debug_mode = True
            self._jarvis.enable_debug()
            console.print("  [green]Debug mode ON[/green]")
            return True
        if cmd == "debug off":
            self._debug_mode = False
            self._jarvis.disable_debug()
            console.print("  [yellow]Debug mode OFF[/yellow]")
            return True
        if cmd == "settings":
            self._show_settings()
            return True
        if cmd in ("memory", "show memories"):
            self._show_memories()
            return True
        if cmd.startswith("remember "):
            content = raw[9:].strip()
            if content:
                self._remember(content)
            else:
                console.print("  [yellow]Usage: remember <text>[/yellow]")
            return True
        if cmd.startswith("forget "):
            query = raw[7:].strip()
            if query:
                self._forget(query)
            else:
                console.print("  [yellow]Usage: forget <query>[/yellow]")
            return True
        if cmd == "ollama":
            self._show_ollama()
            return True
        if cmd == "stats":
            self._show_stats()
            return True
        if cmd in ("vision", "screen", "desktop"):
            self._process_input("what's on my screen")
            return True
        return False

    def _show_help(self):
        table = Table(
            title="Commands", show_header=True,
            header_style="bold #ff6ec7", border_style="dim",
        )
        table.add_column("Command", style="bold")
        table.add_column("Description")
        for cmd, desc in [
            ("help", "Show this help"),
            ("health", "System health status"),
            ("tools", "List registered tools"),
            ("traces", "Recent execution traces"),
            ("debug on/off", "Toggle debug mode"),
            ("settings", "Show all settings"),
            ("memory", "Show stored memories"),
            ("remember <text>", "Store a memory"),
            ("forget <query>", "Delete matching memories"),
            ("ollama", "Check Ollama status"),
            ("stats", "Performance statistics"),
            ("vision / screen", "Describe what's on screen"),
            ("clear", "Clear terminal"),
            ("exit / quit", "Shutdown JARVIS"),
        ]:
            table.add_row(cmd, desc)
        console.print(table)
        console.print()

    def _show_health(self):
        health = self._jarvis.get_health()
        table = Table(
            title="System Health", show_header=True,
            header_style="bold #ff6ec7", border_style="dim",
        )
        table.add_column("Subsystem", style="bold")
        table.add_column("Status")
        table.add_column("Details", style="dim")
        for key in ["nlp_ready", "execution_ready", "router_ready", "memory_ready", "knowledge_ready"]:
            ready = health.get(key, False)
            status = "[green]READY[/green]" if ready else "[red]NOT READY[/red]"
            table.add_row(key.replace("_ready", "").title(), status, "")
        if "execution" in health:
            ex = health["execution"]
            table.add_row("Execution", "", f"Tools: {ex.get('total_tools', '?')}, Traces: {ex.get('total_traces', '?')}")
        if "router" in health:
            rt = health["router"]
            table.add_row("Router", "", f"Providers: {rt.get('total_providers', '?')}, Enabled: {rt.get('enabled_providers', '?')}")
        console.print(table)
        console.print()

    def _show_tools(self):
        tools = self._jarvis.tools.get_all()
        stats = self._jarvis.tools.get_stats()
        table = Table(
            title=f"Registered Tools ({stats['total']})", show_header=True,
            header_style="bold #ff6ec7", border_style="dim",
        )
        table.add_column("Name", style="bold")
        table.add_column("Category")
        table.add_column("Description", max_width=50)
        for name, tool in tools.items():
            table.add_row(name, tool.category.value, tool.description[:50])
        console.print(table)
        console.print()

    def _show_traces(self):
        if not self._jarvis._execution:
            console.print("  [red]Execution engine not initialized[/red]")
            return
        traces = self._jarvis._execution.get_traces(limit=5)
        if not traces:
            console.print("  [dim]No traces yet[/dim]")
            return
        for t in traces:
            console.print(Panel(t.format_debug(), title="Trace", border_style="dim"))
        console.print()

    def _show_settings(self):
        settings = self._jarvis.settings.all()
        table = Table(
            title="Settings", show_header=True,
            header_style="bold #ff6ec7", border_style="dim",
        )
        table.add_column("Key", style="bold")
        table.add_column("Value")
        for k, v in settings.items():
            table.add_row(k, str(v))
        console.print(table)
        console.print()

    def _show_memories(self):
        if not self._jarvis._memory:
            console.print("  [red]Memory not initialized[/red]")
            return
        convos = self._jarvis._memory.get_recent_conversations(limit=10)
        notes = self._jarvis._memory.get_notes(limit=5)
        todos = self._jarvis._memory.get_todos(completed=False)
        if not convos and not notes and not todos:
            console.print("  [dim]No memories stored yet. Use 'remember <text>' to store one.[/dim]")
            return
        if convos:
            console.print("\n  [bold]Recent Conversations:[/bold]")
            for c in convos:
                ts = c.get("timestamp", "")[:16]
                summary = c.get("summary", "")
                console.print(f"    [dim]{ts}[/dim] {summary[:80]}")
        if notes:
            console.print("\n  [bold]Notes:[/bold]")
            for n in notes:
                console.print(f"    [bold]{n.get('title', 'Untitled')}[/bold]: {n.get('content', '')[:60]}")
        if todos:
            console.print("\n  [bold]To-Dos:[/bold]")
            for t in todos:
                console.print(f"    [ ] {t.get('task', '')}")
        console.print()

    def _remember(self, content: str):
        if not self._jarvis._memory:
            console.print("  [red]Memory not initialized[/red]")
            return
        success = self._jarvis._memory.store(content)
        if success:
            console.print(f"  [green]Remembered:[/green] {content[:80]}")
        else:
            console.print("  [red]Failed to store memory[/red]")

    def _forget(self, query: str):
        if not self._jarvis._memory:
            console.print("  [red]Memory not initialized[/red]")
            return
        count = self._jarvis._memory.forget(query)
        if count > 0:
            console.print(f"  [yellow]Forgot {count} item(s) matching '{query}'[/yellow]")
        else:
            console.print(f"  [dim]Nothing found matching '{query}'[/dim]")

    def _show_ollama(self):
        try:
            import httpx
            resp = httpx.get("http://localhost:11434/api/tags", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])
                table = Table(
                    title="Ollama Models", show_header=True,
                    header_style="bold #ff6ec7", border_style="dim",
                )
                table.add_column("Model", style="bold")
                table.add_column("Size")
                table.add_column("Modified")
                for m in models:
                    size_gb = m.get("size", 0) / (1024**3)
                    table.add_row(m.get("name", "?"), f"{size_gb:.1f} GB", m.get("modified_at", "?")[:16])
                console.print(table)
            else:
                console.print("  [red]Ollama responded with error[/red]")
        except Exception:
            console.print("  [red]Ollama not running on localhost:11434[/red]")
        console.print()

    def _show_stats(self):
        health = self._jarvis.get_health()
        bm = health.get("benchmarks", {})
        an = health.get("analytics", {})
        console.print(Panel(
            f"  Benchmarks: {json.dumps(bm, indent=2, default=str)}\n\n"
            f"  Analytics: {json.dumps(an, indent=2, default=str)}",
            title="Performance Stats", border_style="dim",
        ))
        console.print()

    def _process_input(self, user_input: str):
        with console.status("[bold #ff6ec7]Processing...", spinner="dots"):
            try:
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(self._jarvis.handle(user_input))
                loop.close()
            except Exception as e:
                console.print(f"  [red]Error: {e}[/red]")
                return

        response_text = result.get("response", "No response")
        tool = result.get("tool", "llm")
        verified = result.get("verified", False)
        intent = result.get("intent", "?")
        conf = result.get("intent_confidence", 0)
        elapsed_ms = result.get("total_ms", 0)

        style = "bold white" if result.get("success") else "dim"
        self._typing.print(response_text, style=style)

        verified_str = "[green]verified[/green]" if verified else "[dim]unverified[/dim]"
        console.print(
            f"  [dim][{tool} | {verified_str} | "
            f"intent={intent} conf={conf:.2f} | {elapsed_ms:.0f}ms][/dim]"
        )

        if self._debug_mode and result.get("trace"):
            console.print(Panel(result["trace"], title="Debug Trace", border_style="dim"))
        console.print()

    def _shutdown(self):
        console.print("\n  [dim]Shutting down JARVIS...[/dim]")
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(self._jarvis.shutdown())
            loop.close()
        except Exception:
            pass
        console.print("  [green]Goodbye.[/green]\n")
