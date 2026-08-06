#!/usr/bin/env python3
"""JARVIS CLI — Futuristic terminal interface.

Startup:
    +-------------------------+
    |       JARVIS            |
    +-------------------------+
    1. Text Mode
    2. Speech Mode
    3. Debug Mode

Features: Rich, prompt_toolkit, typing effect, debug overlay
"""

from __future__ import annotations

import os
import sys
import time
import asyncio
import threading
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
    from rich.table import Table
    from rich.layout import Layout
    from rich.live import Live
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.key_binding import KeyBindings
    PROMPT_AVAILABLE = True
except ImportError:
    PROMPT_AVAILABLE = False


console = Console() if RICH_AVAILABLE else None


def _enable_ansi() -> None:
    """Enable ANSI escape processing on Windows terminals."""
    if os.name == "nt":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:
            pass


def typing_effect(text: str, delay: float = 0.02) -> None:
    for char in text:
        print(char, end="", flush=True)
        time.sleep(delay)
    print()


def print_banner() -> None:
    banner = """
  +---------------------------------------------------+
  |                                                   |
  |              J A R V I S                          |
  |         CLI Terminal Interface                    |
  |                                                   |
  +---------------------------------------------------+

  1. Text Mode
  2. Speech Mode
  3. Debug Mode
  4. Exit
"""
    try:
        print(banner, flush=True)
    except Exception:
        pass  # Ignore print errors


class TextMode:
    def __init__(self, jarvis) -> None:
        self.jarvis = jarvis
        self._running = True

        if PROMPT_AVAILABLE:
            history_path = str(Path.home() / ".jarvis_history")
            self.session = PromptSession(
                history=FileHistory(history_path),
                auto_suggest=AutoSuggestFromHistory(),
            )

    def get_input(self) -> str:
        if PROMPT_AVAILABLE:
            try:
                return self.session.prompt("You: ")
            except (EOFError, KeyboardInterrupt):
                return ""
        else:
            try:
                return input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                return ""

    async def _handle_streaming(self, user_input: str) -> None:
        """Stream response token by token — thinking rendered in faded grey."""
        print("Jarvis: ", end="", flush=True)
        async for token in self.jarvis.handle_stream(user_input):
            if isinstance(token, str) and token.startswith("\x00"):
                # Thinking tokens: render faded/dim grey
                print(f"\033[2m{token[1:]}\033[0m", end="", flush=True)
            else:
                print(token, end="", flush=True)
        print()

    def run(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")
        _enable_ansi()
        if RICH_AVAILABLE:
            console.print(Panel("[cyan]JARVIS Text Mode[/]", subtitle="Type 'quit' to exit"), style="bold")
        else:
            print("JARVIS Text Mode — Type 'quit' to exit\n")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while self._running:
            try:
                user_input = self.get_input()
                if not user_input:
                    continue

                cmd = user_input.lower().strip()
                if cmd in ("quit", "exit", "q"):
                    self._running = False
                    loop.run_until_complete(self.jarvis.shutdown())
                    break
                if cmd == "debug":
                    if self.jarvis._debug_mode:
                        self.jarvis.disable_debug()
                        if RICH_AVAILABLE:
                            console.print("[yellow]Debug: OFF[/]")
                        else:
                            print("Debug mode OFF")
                    else:
                        self.jarvis.enable_debug()
                        if RICH_AVAILABLE:
                            console.print("[yellow]Debug: ON[/]")
                        else:
                            print("Debug mode ON")
                    continue
                if cmd == "health":
                    from interface.desktop import desktop
                    if RICH_AVAILABLE:
                        console.print(Panel(desktop.format_status(), title="System Status"))
                    else:
                        print(desktop.format_status())
                    continue
                if cmd == "tools":
                    from core.tools import tool_registry
                    tools = tool_registry.get_all()
                    if RICH_AVAILABLE:
                        table = Table(title=f"Tools ({len(tools)})")
                        table.add_column("Name", style="cyan")
                        table.add_column("Category", style="green")
                        table.add_column("Description")
                        for t in tools.values():
                            table.add_row(t["name"], t["category"].value, t["description"])
                        console.print(table)
                    else:
                        print(f"Tools ({len(tools)}):")
                        for name, t in tools.items():
                            print(f"  {name:25s} [{t['category'].value}] {t['description']}")
                    continue

                # Stream the response token by token
                loop.run_until_complete(self._handle_streaming(user_input))

            except KeyboardInterrupt:
                self._running = False
                loop.run_until_complete(self.jarvis.shutdown())
                break
        loop.close()


def boot_jarvis(debug: bool = False):
    from interface.app import JARVIS
    jarvis = JARVIS()
    if debug:
        jarvis.enable_debug()
    jarvis.boot()
    return jarvis


def main() -> None:
    debug = "--debug" in sys.argv
    text_mode = "--text" in sys.argv
    voice_mode = "--voice" in sys.argv
    health_only = "--health" in sys.argv

    if RICH_AVAILABLE:
        console.print("[cyan]Booting JARVIS...[/]")
    else:
        print("Booting JARVIS...")

    jarvis = boot_jarvis(debug=debug)

    if health_only:
        from interface.desktop import desktop
        if RICH_AVAILABLE:
            console.print(Panel(desktop.format_status(), title="System Status"))
        else:
            print(desktop.format_status())
        return

    if text_mode:
        TextMode(jarvis).run()
        return

    if voice_mode:
        print("Voice mode: Use 'python cli.py' and select option 2")
        TextMode(jarvis).run()
        return

    print_banner()
    try:
        choice = input("  Select (1/2/3/4): ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = "4"
    except Exception:
        choice = "4"

    if choice == "1":
        TextMode(jarvis).run()
    elif choice == "2":
        os.system("cls" if os.name == "nt" else "clear")
        if RICH_AVAILABLE:
            console.print(Panel("[cyan]JARVIS Speech Mode[/]", subtitle="Say 'quit' to exit"), style="bold")
        else:
            print("JARVIS Speech Mode — Say 'quit' to exit\n")
        try:
            from interface.speech import speech_engine
            avail = speech_engine.is_available()
            if not avail.get("stt"):
                console.print("[red]Speech-to-text not available. Falling back to text mode.[/]")
                TextMode(jarvis).run()
                return
        except Exception:
            console.print("[red]Speech engine unavailable. Falling back to text mode.[/]")
            TextMode(jarvis).run()
            return

        # Full-duplex conversation: mic always on, barge-in enabled.
        def _voice_handler(user_input: str) -> str:
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(jarvis.handle(user_input))
            finally:
                loop.close()
            if isinstance(result, dict):
                return result.get("response", "")
            return str(result)

        console.print("[dim]Full-duplex voice mode — speak anytime. Ctrl+C to stop.[/]")
        speech_engine.run_conversation(_voice_handler)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            speech_engine.stop()
    elif choice == "3":
        jarvis.enable_debug()
        TextMode(jarvis).run()
    else:
        # Shutdown is async, run it
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(jarvis.shutdown())
        except Exception as e:
            print(f"Shutdown error: {e}")
        finally:
            loop.close()
        print("Goodbye.")


if __name__ == "__main__":
    main()
