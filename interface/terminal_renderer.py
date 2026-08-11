"""interface/terminal_renderer.py — Centralized Terminal Renderer for JARVIS vNext++.

Pure presentation layer.  Renders USER/JARVIS panels, log events, tool
execution, streaming tokens, and performance lines using Rich.

No backend logic, no tool execution, no CPU polling, no network calls.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from enum import Enum
from typing import Any, Dict, Optional

# ── Rich imports (graceful fallback) ──────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.columns import Columns
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

logger = logging.getLogger(__name__)


# ── Log levels ────────────────────────────────────────────────────────
class LogLevel(Enum):
    QUIET = 0
    NORMAL = 1
    VERBOSE = 2
    DEBUG = 3


# ── Theme / style config ─────────────────────────────────────────────
# Colors are Rich markup strings.  Kept in one place so the whole CLI
# stays visually consistent.
class Theme:
    # Panels
    user_border = "cyan"
    user_style = "cyan"
    jarvis_border = "green"
    jarvis_style = "green"

    # Log tag styles  (tag_text, tag_style)
    TAG_STYLES: Dict[str, tuple[str, str]] = {
        "INFO":    ("INFO",    "dim white"),
        "READY":   ("READY",   "bold green"),
        "THINK":   ("THINK",   "yellow"),
        "PLAN":    ("PLAN",    "bright_blue"),
        "MEMORY":  ("MEMORY",  "magenta"),
        "RAG":     ("RAG",     "bright_magenta"),
        "TOOL":    ("TOOL",    "cyan"),
        "ARGS":    ("ARGS",    "dim cyan"),
        "EXEC":    ("EXEC",    "blue"),
        "VERIFY":  ("VERIFY",  "dim green"),
        "SPEECH":  ("SPEECH",  "bright_yellow"),
        "WARN":    ("WARN",    "yellow"),
        "ERROR":   ("ERROR",   "bold red"),
        "SUCCESS": ("SUCCESS", "bold green"),
        "PERF":    ("PERF",    "dim white"),
        "STEP":    ("STEP",    "bright_blue"),
        "DEBUG":   ("DEBUG",   "dim white"),
    }

    # Panel box styles
    user_box = box.ROUNDED if RICH_AVAILABLE else None
    jarvis_box = box.ROUNDED if RICH_AVAILABLE else None


# ── Sensitive value masking ──────────────────────────────────────────
_SENSITIVE_KEYS = frozenset({
    "api_key", "apikey", "api-key", "token", "secret",
    "password", "passwd", "auth", "bearer", "cookie",
    "credentials", "access_token", "refresh_token",
})


def _mask_value(key: str, value: str) -> str:
    """Return masked value for sensitive keys."""
    if key.lower() in _SENSITIVE_KEYS or any(s in key.lower() for s in _SENSITIVE_KEYS):
        if len(value) > 4:
            return value[:2] + "*" * (len(value) - 4) + value[-2:]
        return "****"
    return value


def _format_args(args: Dict[str, Any]) -> str:
    """Format tool arguments for display, masking sensitive values."""
    if not args:
        return ""
    parts = []
    for k, v in args.items():
        val = str(v)
        val = _mask_value(k, val)
        # Truncate very long values
        if len(val) > 60:
            val = val[:57] + "..."
        parts.append(f"{k}={val}")
    return " ".join(parts)


# ── TerminalRenderer ─────────────────────────────────────────────────
class TerminalRenderer:
    """Centralized renderer for JARVIS CLI output.

    All display logic lives here.  The rest of the codebase calls into
    this renderer rather than printing directly.
    """

    def __init__(self, log_level: LogLevel = LogLevel.NORMAL):
        self.log_level = log_level
        self._console: Optional[Console] = None
        self._request_start: float = 0.0
        self._llm_start: float = 0.0
        self._tool_start: float = 0.0
        self._tool_total: float = 0.0
        self._llm_total: float = 0.0
        self._has_rich = RICH_AVAILABLE

        if RICH_AVAILABLE:
            self._console = Console(highlight=False)

    # ── Internal helpers ──────────────────────────────────────────────

    def _print(self, *args, **kwargs) -> None:
        """Print via Rich if available, else builtins."""
        if self._console:
            self._console.print(*args, **kwargs)
        else:
            print(*args, **kwargs)

    def _print_plain(self, text: str) -> None:
        """Print raw text without Rich markup."""
        if self._console:
            self._console.print(text, highlight=False)
        else:
            print(text)

    def _rich_tag(self, tag: str) -> Text:
        """Build a styled tag like [TOOL]."""
        tag_text, tag_style = Theme.TAG_STYLES.get(tag, (tag, "white"))
        t = Text()
        t.append(f"[{tag_text}]  ", style=tag_style)
        return t

    def _print_tagged(self, tag: str, message: str) -> None:
        """Print a tagged log line: [TAG]  message."""
        if self.log_level == LogLevel.QUIET and tag not in ("ERROR",):
            return
        if self.log_level == LogLevel.NORMAL and tag in ("DEBUG",):
            return
        if self._console:
            t = self._rich_tag(tag)
            t.append(message)
            self._console.print(t, highlight=False)
        else:
            tag_text = Theme.TAG_STYLES.get(tag, (tag, ""))[0]
            print(f"[{tag_text}]  {message}")

    # ── USER / JARVIS panels ─────────────────────────────────────────

    def render_user(self, text: str) -> None:
        """Render the user's input in a cyan panel."""
        if self._console:
            self._print(
                Panel(
                    Text(text, style="bold"),
                    title="[bold cyan]USER[/]",
                    border_style=Theme.user_border,
                    box=Theme.user_box,
                    padding=(0, 1),
                )
            )
        else:
            print(f"\n╭─ USER {'─' * 50}╮")
            print(f"│ {text:<50}│")
            print(f"╰{'─' * 52}╯")

    def render_jarvis(self, text: str) -> None:
        """Render JARVIS's response in a green panel."""
        if self._console:
            self._print(
                Panel(
                    Text(text, style="bold"),
                    title="[bold green]JARVIS[/]",
                    border_style=Theme.jarvis_border,
                    box=Theme.jarvis_box,
                    padding=(0, 1),
                )
            )
        else:
            print(f"\n╭─ JARVIS {'─' * 48}╮")
            print(f"│ {text:<50}│")
            print(f"╰{'─' * 52}╯")

    def render_user_stream_start(self) -> None:
        """Begin a JARVIS streaming response (print the panel header)."""
        if self._console:
            # Use a Text object so we can append tokens incrementally
            self._stream_text = Text()
            self._stream_panel = None
        # For non-Rich, we just print the prefix

    def render_token(self, token: str) -> None:
        """Append a streaming token to the current response."""
        if self._console:
            if not hasattr(self, "_stream_text") or self._stream_text is None:
                self._stream_text = Text()
            self._stream_text.append(token)
        else:
            print(token, end="", flush=True)

    def render_stream_end(self) -> None:
        """Finalize the streaming response panel."""
        if self._console:
            text = self._stream_text if hasattr(self, "_stream_text") and self._stream_text else Text("")
            self._print(
                Panel(
                    text,
                    title="[bold green]JARVIS[/]",
                    border_style=Theme.jarvis_border,
                    box=Theme.jarvis_box,
                    padding=(0, 1),
                )
            )
            self._stream_text = None
        else:
            print()

    # ── Log events ────────────────────────────────────────────────────

    def render_info(self, message: str) -> None:
        self._print_tagged("INFO", message)

    def render_ready(self, message: str) -> None:
        self._print_tagged("READY", message)

    def render_think(self, message: str) -> None:
        if self.log_level.value >= LogLevel.NORMAL.value:
            self._print_tagged("THINK", message)

    def render_plan(self, message: str) -> None:
        if self.log_level.value >= LogLevel.NORMAL.value:
            self._print_tagged("PLAN", message)

    def render_memory(self, message: str) -> None:
        if self.log_level.value >= LogLevel.VERBOSE.value:
            self._print_tagged("MEMORY", message)

    def render_rag(self, message: str) -> None:
        if self.log_level.value >= LogLevel.VERBOSE.value:
            self._print_tagged("RAG", message)

    def render_tool(self, tool_name: str, args: Optional[Dict[str, Any]] = None) -> None:
        if self.log_level.value >= LogLevel.NORMAL.value:
            self._print_tagged("TOOL", tool_name)
            if args:
                self._print_tagged("ARGS", _format_args(args))

    def render_exec(self, message: str) -> None:
        if self.log_level.value >= LogLevel.NORMAL.value:
            self._print_tagged("EXEC", message)

    def render_verify(self, message: str) -> None:
        if self.log_level.value >= LogLevel.NORMAL.value:
            self._print_tagged("VERIFY", message)

    def render_speech(self, message: str) -> None:
        if self.log_level.value >= LogLevel.NORMAL.value:
            self._print_tagged("SPEECH", message)

    def render_warn(self, message: str) -> None:
        self._print_tagged("WARN", message)

    def render_error(self, message: str) -> None:
        self._print_tagged("ERROR", message)

    def render_success(self, message: str) -> None:
        if self.log_level.value >= LogLevel.NORMAL.value:
            self._print_tagged("SUCCESS", f"✓ {message}")

    def render_step(self, step_num: int, total: int, message: str) -> None:
        if self.log_level.value >= LogLevel.NORMAL.value:
            self._print_tagged("STEP", f"[{step_num}/{total}] {message}")

    def render_debug(self, message: str) -> None:
        if self.log_level.value >= LogLevel.DEBUG.value:
            self._print_tagged("DEBUG", message)

    # ── Performance ───────────────────────────────────────────────────

    def render_performance(self, total_ms: float, llm_ms: float = 0, tool_ms: float = 0) -> None:
        if self.log_level == LogLevel.QUIET:
            return
        if total_ms < 1000:
            label = f"{int(total_ms)}ms"
        else:
            label = f"{total_ms / 1000:.2f}s"
        parts = [label]
        if llm_ms > 0:
            parts.append(f"LLM {llm_ms / 1000:.2f}s" if llm_ms >= 1000 else f"LLM {int(llm_ms)}ms")
        if tool_ms > 0:
            parts.append(f"Tool {tool_ms / 1000:.2f}s" if tool_ms >= 1000 else f"Tool {int(tool_ms)}ms")
        self._print_tagged("PERF", " | ".join(parts))

    # ── Latency tracking ──────────────────────────────────────────────

    def mark_request_start(self) -> None:
        self._request_start = time.monotonic()

    def mark_llm_start(self) -> None:
        self._llm_start = time.monotonic()

    def mark_llm_end(self) -> None:
        if self._llm_start > 0:
            self._llm_total += (time.monotonic() - self._llm_start) * 1000
            self._llm_start = 0

    def mark_tool_start(self) -> None:
        self._tool_start = time.monotonic()

    def mark_tool_end(self) -> None:
        if self._tool_start > 0:
            self._tool_total += (time.monotonic() - self._tool_start) * 1000
            self._tool_start = 0

    def get_elapsed_ms(self) -> float:
        if self._request_start > 0:
            return (time.monotonic() - self._request_start) * 1000
        return 0

    def render_final_performance(self) -> None:
        """Render the performance summary after a request completes."""
        total = self.get_elapsed_ms()
        if total > 0:
            self.render_performance(total, self._llm_total, self._tool_total)
        # Reset counters
        self._request_start = 0
        self._llm_total = 0
        self._tool_total = 0

    # ── Boot / startup ────────────────────────────────────────────────

    def render_boot_banner(self) -> None:
        """Render the JARVIS startup banner with model info."""
        if self._console and RICH_AVAILABLE:
            self._print()
            self._print(Panel(
                Text("JARVIS AI CORE", style="bold cyan", justify="center"),
                border_style="cyan",
                box=box.DOUBLE,
            ))
        else:
            print()
            print("╭──────────────────────────────────────────────────────╮")
            print("│              JARVIS AI CORE                         │")
            print("╰──────────────────────────────────────────────────────╯")

    def render_model_info(self, info: Dict[str, Any]) -> None:
        """Render model/provider information table."""
        if self._console and RICH_AVAILABLE:
            lines = []
            for key, val in info.items():
                lines.append(f"  {key:<12} {val}")
            self._print(Panel(
                "\n".join(lines),
                border_style="cyan",
                box=box.ROUNDED,
            ))
        else:
            print("╭──────────────────────────────────────────────────────╮")
            for key, val in info.items():
                print(f"│  {key:<12} {val:<40} │")
            print("╰──────────────────────────────────────────────────────╯")

    def render_boot_step(self, label: str, success: bool, detail: str = "") -> None:
        """Render a single boot step."""
        status = "SUCCESS" if success else "WARN"
        msg = label
        if detail:
            msg += f" — {detail}"
        self._print_tagged(status, msg)

    def render_ready_line(self) -> None:
        self._print()
        self._print_tagged("READY", "JARVIS ONLINE")
        self._print()

    # ── HTTP log suppression ──────────────────────────────────────────

    @staticmethod
    def suppress_noisy_logs() -> None:
        """Downgrade third-party HTTP/transport loggers to WARNING."""
        noisy = [
            "httpx", "httpcore", "urllib3", "requests",
            "aiohttp", "asyncio", "openai", "anthropic",
        ]
        for name in noisy:
            logging.getLogger(name).setLevel(logging.WARNING)

    @staticmethod
    def allow_debug_logs() -> None:
        """Restore third-party loggers to DEBUG level."""
        noisy = [
            "httpx", "httpcore", "urllib3", "requests",
            "aiohttp", "asyncio", "openai", "anthropic",
        ]
        for name in noisy:
            logging.getLogger(name).setLevel(logging.DEBUG)


# ── Singleton ────────────────────────────────────────────────────────
renderer = TerminalRenderer()
