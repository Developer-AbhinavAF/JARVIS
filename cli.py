#!/usr/bin/env python3
"""JARVIS CLI — Entry point.

Boots JARVIS, shows startup menu, dispatches to text or voice mode.

Usage:
    python cli.py              # Interactive menu
    python cli.py --text       # Skip menu, go to text mode
    python cli.py --voice      # Skip menu, go to voice mode
    python cli.py --debug      # Enable debug mode
    python cli.py --health     # Show health and exit
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def boot_jarvis(debug: bool = False) -> "JARVIS":
    """Boot JARVIS and return the instance."""
    from app import JARVIS

    jarvis = JARVIS()
    if debug:
        jarvis.enable_debug()

    boot_start = time.time()
    asyncio.run(jarvis.boot())
    boot_time = time.time() - boot_start

    return jarvis, boot_time


def show_startup_menu():
    """Display the startup screen."""
    os.system("cls" if os.name == "nt" else "clear")
    print()
    print("  ╔═══════════════════════════════════════════════════╗")
    print("  ║                                                   ║")
    print("  ║              J A R V I S                          ║")
    print("  ║         CLI Terminal Interface                    ║")
    print("  ║                                                   ║")
    print("  ╚═══════════════════════════════════════════════════╝")
    print()
    print("  1. Text Mode")
    print("  2. Voice Mode")
    print("  3. Exit")
    print()


def get_choice() -> str:
    """Get user menu choice."""
    try:
        choice = input("  Select (1/2/3): ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = "3"
    return choice


async def show_health(jarvis):
    """Show health info and exit."""
    import json
    health = jarvis.get_health()
    print(json.dumps(health, indent=2, default=str))
    await jarvis.shutdown()


def main():
    """CLI entry point."""
    # Parse flags
    debug = "--debug" in sys.argv
    text_mode = "--text" in sys.argv
    voice_mode = "--voice" in sys.argv
    health_only = "--health" in sys.argv

    # Boot
    print("  Booting JARVIS...")
    try:
        jarvis, boot_time = boot_jarvis(debug=debug)
    except Exception as e:
        print(f"\n  Boot failed: {e}")
        sys.exit(1)

    print(f"  Ready ({boot_time:.1f}s)\n")

    # Health check mode
    if health_only:
        asyncio.run(show_health(jarvis))
        return

    # Direct mode selection
    if text_mode:
        from cli_ui import TextMode
        TextMode(jarvis).run()
        return

    if voice_mode:
        from cli_speech import VoiceMode
        VoiceMode(jarvis).run()
        return

    # Interactive menu
    show_startup_menu()
    choice = get_choice()

    if choice == "1":
        from cli_ui import TextMode
        TextMode(jarvis).run()
    elif choice == "2":
        from cli_speech import VoiceMode
        VoiceMode(jarvis).run()
    else:
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(jarvis.shutdown())
            loop.close()
        except Exception:
            pass
        print("  Goodbye.\n")


if __name__ == "__main__":
    main()
