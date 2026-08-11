#!/usr/bin/env python3
"""JARVIS CLI — Intelligent live-logging terminal interface.

Uses TerminalRenderer for all display.  Supports both the new JarvisCore
(event-based) and the legacy JARVIS class (token-based) backends.
"""

from __future__ import annotations

import os
import sys
import time
import asyncio
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from interface.terminal_renderer import renderer, LogLevel

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    PROMPT_AVAILABLE = True
except ImportError:
    PROMPT_AVAILABLE = False


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


# ── Log level from env / CLI flags ──────────────────────────────────
def _resolve_log_level() -> LogLevel:
    env = os.getenv("JARVIS_LOG_LEVEL", "").upper()
    if env in ("QUIET", "Q"):
        return LogLevel.QUIET
    if env in ("VERBOSE", "V"):
        return LogLevel.VERBOSE
    if env in ("DEBUG", "D"):
        return LogLevel.DEBUG
    if "--quiet" in sys.argv:
        return LogLevel.QUIET
    if "--verbose" in sys.argv:
        return LogLevel.VERBOSE
    return LogLevel.NORMAL


class TextMode:
    def __init__(self, jarvis, log_level: LogLevel = LogLevel.NORMAL) -> None:
        self.jarvis = jarvis
        self._running = True
        self._log_level = log_level
        self._is_new_core = hasattr(jarvis, "process_stream")

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

    async def _handle_new_core(self, user_input: str) -> None:
        """Consume structured events from JarvisCore.process_stream()."""
        from core.events import (
            ThinkingEvent, PlannerEvent, MemoryEvent, ExecutionEvent,
            VerificationEvent, FinalResponseToken, FinalResponse,
            ImageResultEvent, ImageGalleryEvent, CodeExecutionEvent,
        )

        renderer.mark_request_start()
        full_text = ""
        streaming_started = False

        async for event in self.jarvis.process_stream(user_input):
            if isinstance(event, ThinkingEvent):
                # Show a short summary, never raw reasoning
                renderer.render_think("Processing...")
            elif isinstance(event, PlannerEvent):
                profile = getattr(event, "profile", "")
                steps = getattr(event, "steps", [])
                if profile:
                    renderer.render_plan(f"Profile: {profile}")
                if len(steps) > 1:
                    renderer.render_plan(f"{len(steps)}-step plan")
            elif isinstance(event, MemoryEvent):
                action = getattr(event, "action", "")
                key = getattr(event, "key", "")
                if action == "hit" and key:
                    renderer.render_memory(f"Recalled: {key}")
            elif isinstance(event, ExecutionEvent):
                renderer.mark_tool_start()
                target = getattr(event, "target_name", "")
                renderer.render_tool(target)
                renderer.render_exec(f"Running {target}...")
            elif isinstance(event, VerificationEvent):
                renderer.mark_tool_end()
                target = getattr(event, "target_name", "")
                verified = getattr(event, "verified", False)
                renderer.render_verify(
                    f"{target}: {'verified' if verified else 'unverified'}"
                )
            elif isinstance(event, FinalResponseToken):
                token = getattr(event, "token", "")
                if not streaming_started:
                    streaming_started = True
                    renderer.render_user_stream_start()
                renderer.render_token(token)
                full_text += token
            elif isinstance(event, ImageResultEvent):
                title = getattr(event, "title", "")
                url = getattr(event, "image_url", "")
                if title:
                    renderer.render_success(f"Image: {title}")
                if url:
                    renderer.render_info(f"URL: {url}")
            elif isinstance(event, ImageGalleryEvent):
                count = getattr(event, "count", 0)
                query = getattr(event, "query", "")
                renderer.render_success(f"Found {count} images for '{query}'")
            elif isinstance(event, CodeExecutionEvent):
                lang = getattr(event, "language", "")
                success = getattr(event, "success", False)
                stdout = getattr(event, "stdout", "")
                status = "success" if success else "failed"
                renderer.render_exec(f"Code ({lang}): {status}")
                if stdout:
                    renderer.render_info(stdout[:200])
            elif isinstance(event, FinalResponse):
                text = getattr(event, "text", "")
                if text and not streaming_started:
                    renderer.render_jarvis(text)

        # Finalize the JARVIS panel
        if streaming_started:
            renderer.render_stream_end()
        elif full_text:
            renderer.render_jarvis(full_text)
        else:
            renderer.render_jarvis("(no response)")

        renderer.render_final_performance()

    async def _handle_legacy(self, user_input: str) -> None:
        """Consume raw tokens from legacy JARVIS.handle_stream()."""
        renderer.mark_request_start()
        renderer.mark_llm_start()

        streaming_started = False
        full_text = ""

        try:
            async for token in self.jarvis.handle_stream(user_input):
                if isinstance(token, str) and token.startswith("\x00"):
                    continue  # thinking tokens — skip
                if not streaming_started:
                    streaming_started = True
                    renderer.render_user_stream_start()
                renderer.render_token(token)
                full_text += token
        except Exception as e:
            renderer.render_error(f"Streaming error: {e}")

        renderer.mark_llm_end()

        if streaming_started:
            renderer.render_stream_end()
        elif full_text:
            renderer.render_jarvis(full_text)
        else:
            renderer.render_jarvis("(no response)")

        renderer.render_final_performance()

    async def _handle_input(self, user_input: str) -> None:
        """Route user input through the appropriate handler."""
        renderer.render_user(user_input)

        if self._is_new_core:
            await self._handle_new_core(user_input)
        else:
            await self._handle_legacy(user_input)

    def run(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")
        _enable_ansi()

        renderer.render_info("Text mode active — Type 'quit' to exit")
        renderer._print()

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
                    if getattr(self.jarvis, "_debug_mode", False):
                        self.jarvis.disable_debug()
                        renderer.log_level = LogLevel.DEBUG
                        renderer.allow_debug_logs()
                        renderer.render_info("Debug: ON")
                    else:
                        self.jarvis.enable_debug()
                        renderer.log_level = LogLevel.DEBUG
                        renderer.allow_debug_logs()
                        renderer.render_info("Debug: ON")
                    continue
                if cmd == "quiet":
                    renderer.log_level = LogLevel.QUIET
                    renderer.render_info("Quiet mode")
                    continue
                if cmd == "verbose":
                    renderer.log_level = LogLevel.VERBOSE
                    renderer.render_info("Verbose mode")
                    continue
                if cmd == "normal":
                    renderer.log_level = LogLevel.NORMAL
                    renderer.suppress_noisy_logs()
                    renderer.render_info("Normal mode")
                    continue
                if cmd == "health":
                    try:
                        from interface.desktop import desktop
                        renderer.render_info(desktop.format_status())
                    except Exception as e:
                        renderer.render_error(f"Health check failed: {e}")
                    continue
                if cmd == "tools":
                    try:
                        from core.tools import tool_registry
                        tools = tool_registry.get_all()
                        renderer.render_info(f"Registered tools ({len(tools)}):")
                        for name, t in tools.items():
                            renderer.render_info(f"  {name:25s} [{t['category'].value}]")
                    except Exception as e:
                        renderer.render_error(f"Tool list failed: {e}")
                    continue

                loop.run_until_complete(self._handle_input(user_input))

            except KeyboardInterrupt:
                self._running = False
                loop.run_until_complete(self.jarvis.shutdown())
                break
        loop.close()


def boot_jarvis(debug: bool = False):
    """Boot JARVIS and render the startup sequence."""
    renderer.suppress_noisy_logs()
    renderer.render_boot_banner()
    renderer.render_info("Starting JARVIS...")

    try:
        from core.jarvis_core import JarvisCore
        core = JarvisCore()
        renderer.render_info("Loading core...")

        # Try to get model info before boot
        model_info = {}
        try:
            from core.brain_adapter import BrainAdapter
            adapter = BrainAdapter()
            provider = getattr(adapter, "_active_provider", "unknown")
            model = getattr(adapter, "_model", "unknown")
            model_info = {
                "Model": str(model),
                "Provider": str(provider),
                "Mode": "Streaming",
                "Tools": "READY",
                "Memory": "READY",
            }
        except Exception:
            model_info = {
                "Model": "unknown",
                "Provider": "unknown",
                "Mode": "Streaming",
                "Tools": "READY",
                "Memory": "READY",
            }

        core.boot()
        renderer.render_model_info(model_info)
        renderer.render_ready_line()
        return core

    except Exception as e:
        renderer.render_warn(f"Core init failed ({e}), trying legacy...")
        try:
            from interface.app import JARVIS
            jarvis = JARVIS()
            if debug:
                jarvis.enable_debug()
            jarvis.boot()
            renderer.render_ready_line()
            return jarvis
        except Exception as e2:
            renderer.render_error(f"Boot failed: {e2}")
            raise


def main() -> None:
    debug = "--debug" in sys.argv
    text_mode = "--text" in sys.argv
    voice_mode = "--voice" in sys.argv
    health_only = "--health" in sys.argv

    log_level = _resolve_log_level()
    renderer.log_level = log_level

    if debug:
        renderer.log_level = LogLevel.DEBUG
        renderer.allow_debug_logs()

    jarvis = boot_jarvis(debug=debug)

    if health_only:
        try:
            from interface.desktop import desktop
            renderer.render_info(desktop.format_status())
        except Exception as e:
            renderer.render_error(f"Health check failed: {e}")
        return

    if text_mode or voice_mode:
        if voice_mode:
            renderer.render_info("Voice mode — speak anytime. Ctrl+C to stop.")
        TextMode(jarvis, log_level=log_level).run()
        return

    # Interactive menu
    renderer._print()
    renderer.render_info("1. Text Mode")
    renderer.render_info("2. Speech Mode")
    renderer.render_info("3. Debug Mode")
    renderer.render_info("4. Exit")
    renderer._print()

    try:
        choice = input("  Select (1/2/3/4): ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = "4"
    except Exception:
        choice = "4"

    if choice == "1":
        TextMode(jarvis, log_level=log_level).run()
    elif choice == "2":
        os.system("cls" if os.name == "nt" else "clear")
        renderer.render_info("Speech mode — say 'quit' to exit")
        try:
            from interface.speech import speech_engine
            avail = speech_engine.is_available()
            if not avail.get("stt"):
                renderer.render_error("Speech-to-text not available. Falling back to text mode.")
                TextMode(jarvis, log_level=log_level).run()
                return
        except Exception:
            renderer.render_error("Speech engine unavailable. Falling back to text mode.")
            TextMode(jarvis, log_level=log_level).run()
            return

        def _voice_handler(user_input: str) -> str:
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(jarvis.handle(user_input))
            finally:
                loop.close()
            if isinstance(result, dict):
                return result.get("response", "")
            return str(result)

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
        renderer.log_level = LogLevel.DEBUG
        renderer.allow_debug_logs()
        TextMode(jarvis, log_level=LogLevel.DEBUG).run()
    else:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(jarvis.shutdown())
        except Exception as e:
            renderer.render_error(f"Shutdown error: {e}")
        finally:
            loop.close()
        renderer.render_info("Goodbye.")


if __name__ == "__main__":
    main()
