"""jarvis.main

Entry point and orchestrator for the JARVIS voice assistant.

Flow:
  1. Fast Path (ultra-fast, <10ms) - for common commands like "open youtube"
  2. Tool Router (regex-based, <1ms) - for any tool-able command
  3. LLM (slow path) - only for chat/conversation
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import time
from datetime import datetime

from jarvis.dashboard import SystemDashboard
from jarvis.llm import JarvisLLM
from jarvis.memory import memory
from jarvis.stt import STTEngine
from jarvis.tts import TTSEngine

from jarvis.fast_path import match_fast, is_trivial
from jarvis.tool_router import route_input, execute_tool, ToolAction
from jarvis.nlp_pipeline import nlp_pipeline
from jarvis.action_router import parse_action_line

from jarvis.task_manager import task_manager
from jarvis.youtube_learner import init_youtube_learner
from jarvis.web_browser import init_web_browser
from jarvis.shopping import init_shopping_assistant

logger = logging.getLogger(__name__)


# ── Performance timer ────────────────────────────────────
_PERF_LOG: list[dict] = []


def _perf(label: str, started: float) -> None:
    elapsed = (time.time() - started) * 1000
    _PERF_LOG.append({"label": label, "ms": elapsed})
    if elapsed > 100:
        logger.info("PERF SLOW [%s]: %.1fms", label, elapsed)
    elif elapsed > 10:
        logger.debug("PERF [%s]: %.1fms", label, elapsed)


def _log_perf(query: str) -> None:
    if not _PERF_LOG:
        return
    total = _PERF_LOG[-1]["ms"] if len(_PERF_LOG) > 1 else sum(p["ms"] for p in _PERF_LOG)
    details = " | ".join(f"{p['label']}:{p['ms']:.0f}ms" for p in _PERF_LOG)
    logger.info("PERF [%s] total=%.0fms %s", query[:30], total, details)
    _PERF_LOG.clear()


# ── Banner and display ───────────────────────────────────
def _print_banner() -> None:
    banner = r"""
     _   _   _   _   _   _   _   _
    | |_| |_| |_| |_| |_| |_| |_| |
    |   _J_A_R_V_I_S_            |
    |  [Your AI Assistant]       |
    |____________________________|
    """
    print(banner)


def _boxed_print(label: str, text: str) -> None:
    label = (label or "").strip() or "JARVIS"
    text = (text or "").strip()
    lines = text.splitlines() if text else [""]
    width = max(len(label) + 2, *(len(l) for l in lines))
    top = f"+{'-' * (width + 2)}+"
    mid = f"| {label.ljust(width)} |"
    print(top)
    print(mid)
    print(f"+{'-' * (width + 2)}+")
    for l in lines:
        print(f"| {l.ljust(width)} |")
    print(top)


# ── Multi-task parsing ───────────────────────────────────
def _parse_multi_tasks(query: str) -> list[str]:
    query = query.strip().lower()
    if not query:
        return []
    command_starters = [
        "open ", "close ", "launch ", "start ", "quit ", "kill ", "switch to ",
        "play ", "stop ", "pause ", "resume ", "skip ", "next ", "previous ",
        "move ", "click ", "double click ", "right click ", "drag ", "scroll ",
        "type ", "press ", "hold ", "release ",
        "set volume", "volume ", "mute", "unmute",
        "set brightness", "brightness ",
        "take ", "capture ", "save ", "delete ",
        "search ", "find ", "look up ", "google ", "youtube ", "web ",
        "what ", "when ", "where ", "who ", "why ", "how ", "tell me ", "show ",
        "get ", "check ", "list ", "status", "system ",
        "add ", "create ", "new ", "save ", "remember ", "note ", "write down ",
        "remove ", "delete ", "clear ", "erase ", "complete ", "finish ", "mark ",
        "show ", "read ", "tell ", "what's ", "what is ", "list ",
        "send ", "email ", "message ", "text ", "call ",
    ]
    split_markers = [" and ", " then ", " also ", " next ", " after that ", " followed by ", " & ", " + "]
    if query.startswith("open "):
        rest = query[5:]
        for marker in split_markers:
            if marker in rest:
                parts = rest.split(marker)
                if len(parts) > 1 and all(len(p.strip().split()) <= 2 for p in parts):
                    return [f"open {p.strip()}" for p in parts if p.strip()]
    if query.startswith("close "):
        rest = query[6:]
        for marker in split_markers:
            if marker in rest:
                parts = rest.split(marker)
                if len(parts) > 1 and all(len(p.strip().split()) <= 2 for p in parts):
                    return [f"close {p.strip()}" for p in parts if p.strip()]
    tasks = []
    remaining = query
    while remaining:
        earliest_split = None
        earliest_pos = len(remaining)
        for marker in split_markers:
            pos = remaining.find(marker)
            if pos != -1 and pos < earliest_pos:
                earliest_pos = pos
                earliest_split = marker
        if earliest_split is None:
            tasks.append(remaining.strip())
            break
        before = remaining[:earliest_pos].strip()
        after = remaining[earliest_pos + len(earliest_split):].strip()
        if before:
            tasks.append(before)
        is_new_command = any(after.startswith(starter.strip()) for starter in command_starters)
        if not is_new_command and after:
            if tasks:
                tasks[-1] = f"{tasks[-1]} {earliest_split.strip()} {after}"
                break
            else:
                tasks.append(after)
                break
        remaining = after
    cleaned_tasks = []
    for task in tasks:
        task = task.strip()
        for marker in split_markers:
            if task.endswith(marker.strip()):
                task = task[:-len(marker.strip())].strip()
        if task:
            cleaned_tasks.append(task)
    return cleaned_tasks if len(cleaned_tasks) > 1 else [query]


# ── Core routing logic ───────────────────────────────────
def _route_and_execute(query: str, tts: TTSEngine | None, dashboard: SystemDashboard) -> tuple[str, bool]:
    """Route query through: Fast Path → Tool Router → fallback to LLM-required.

    Returns:
        (response_text, was_handled) - if was_handled=False, caller should use LLM
    """
    t0 = time.time()

    cleaned = query.strip().lower()
    if not cleaned:
        return ("", True)

    # ── Meta commands (shutdown, clear, etc.) ──
    if any(p in cleaned for p in ["goodbye", "shut down", "shutdown", "exit", "quit"]):
        dashboard.stop_monitoring()
        if tts:
            tts.speak_sync("Goodbye.")
        sys.exit(0)

    if any(p in cleaned for p in ["clear memory", "forget", "reset", "new conversation"]):
        _perf("meta_cmd", t0)
        return ("MEMORY_CLEARED", True)

    if any(p in cleaned for p in ["stop talking", "be quiet", "silence", "shut up"]):
        if tts:
            tts.stop()
        return ("", True)

    # ── Trivial queries (hello, thanks, etc.) ──
    if is_trivial(cleaned):
        _perf("trivial", t0)
        return ("", True)

    # ── Fast Path (ultra-fast, <10ms) ──
    t1 = time.time()
    fast = match_fast(cleaned)
    _perf("fast_path", t1)
    if fast:
        _perf("fast_exec", t1)
        result = fast.execute()
        _log_perf(query)
        return (result, True)

    # ── Tool Router (regex-based, <1ms) ──
    t2 = time.time()
    action = route_input(cleaned)
    _perf("route_input", t2)
    if action:
        t3 = time.time()
        result = execute_tool(action)
        _perf("tool_exec", t3)
        _log_perf(query)
        return (result, True)

    # ── NLP pipeline (deterministic semantic fallback) ──
    t4 = time.time()
    nlp_result = nlp_pipeline.process(cleaned)
    _perf("nlp", t4)

    action_line = nlp_result.action
    if action_line:
        parsed_action = parse_action_line(action_line)
        if parsed_action:
            frontend_action = parsed_action.to_frontend_action()
            if frontend_action.get("tool") == "open_app":
                result = execute_tool(ToolAction("open app", "open_app", {"target": frontend_action["app"]}, 0.85))
                _log_perf(query)
                return (result, True)
            if frontend_action.get("tool") == "web_search":
                result = execute_tool(ToolAction("web search", "web_search", {"query": frontend_action["query"]}, 0.85))
                _log_perf(query)
                return (result, True)

    nlp_intent_map: dict[str, tuple[str, callable]] = {
        "system_status": ("get system stats", lambda n: ToolAction("system status", "get_system_stats", {}, n.confidence)),
        "daily_briefing": ("daily briefing", lambda n: ToolAction("daily briefing", "get_daily_briefing", {}, n.confidence)),
        "screenshot": ("take screenshot", lambda n: ToolAction("screenshot", "screenshot", {}, n.confidence)),
        "calculator": ("calculator", lambda n: ToolAction("calculator", "calculator", {"expression": n.entities.get("expression", n.normalized_text)}, n.confidence)),
        "weather": ("weather", lambda n: ToolAction("weather", "get_weather", {"city": n.entities.get("location", "Mumbai")}, n.confidence)),
        "joke": ("joke", lambda n: ToolAction("joke", "get_joke", {}, n.confidence)),
        "quote": ("quote", lambda n: ToolAction("quote", "get_quote", {}, n.confidence)),
        "remember": ("remember", lambda n: ToolAction("remember", "memory_save_permanent", {"info": query.strip(), "category": "user_important"}, n.confidence)),
    }

    mapped = nlp_intent_map.get(nlp_result.intent)
    if mapped and nlp_result.confidence >= 0.84:
        _, builder = mapped
        result = execute_tool(builder(nlp_result))
        _log_perf(query)
        return (result, True)

    # ── LLM required (fallback) ──
    return ("", False)


def _execute_task(query: str, tts: TTSEngine | None, llm: JarvisLLM, dashboard) -> str:
    result, handled = _route_and_execute(query, tts, dashboard)
    if handled:
        return result
    response = llm.chat(query)
    return response if isinstance(response, str) else response.get("text", str(response))


def _shutdown(tts: TTSEngine | None) -> None:
    if not tts:
        sys.exit(0)
    try:
        tts.speak_sync("Shutting down. Goodbye.")
    except Exception:
        logger.exception("Failed while speaking shutdown message")
    try:
        tts.shutdown()
    except Exception:
        logger.exception("Failed to shutdown TTS")
    sys.exit(0)


def _select_mode() -> str:
    import threading
    print("\n" + "="*50)
    print("  JARVIS MODE SELECTOR")
    print("="*50)
    print("  Press 'y' then Enter for FULL GUI MODE")
    print("    > Modern AI interface with visuals, music, themes")
    print("    > Voice control + Text input")
    print("    > All features with beautiful UI")
    print()
    print("  Press 'n' then Enter for SIMPLE CHAT MODE")
    print("    > ChatGPT-style text conversation")
    print("    > Clean terminal interface")
    print("    > No voice, pure text")
    print()
    print("  Waiting 10 seconds... (default: FULL GUI)")
    print("="*50)
    result = ['voice']
    def input_thread():
        try:
            user_input = input("\n  Your choice (y/n): ").strip().lower()
            if user_input == 'n':
                result[0] = 'text'
            elif user_input == 'y' or user_input == '':
                result[0] = 'voice'
        except:
            pass
    t = threading.Thread(target=input_thread)
    t.daemon = True
    t.start()
    t.join(timeout=60)
    mode = result[0]
    if mode == 'voice':
        print("\n  Selected: FULL MODERN GUI MODE")
    else:
        print("\n  Selected: SIMPLE CHAT MODE")
    print("="*50 + "\n")
    return mode


# ── Text interface ──────────────────────────────────────
class SimpleChatInterface:
    def __init__(self, llm: JarvisLLM, dashboard):
        self.llm = llm
        self.dashboard = dashboard
        self.chat_history: list[dict] = []

    def _print_chatgpt_header(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\n" + "═" * 60)
        print("  JARVIS AI - Simple Chat Mode")
        print("  Type 'exit' to quit")
        print("═" * 60 + "\n")

    def run(self) -> None:
        self._print_chatgpt_header()
        print("  JARVIS: Hello! I'm JARVIS, your AI assistant.\n")
        while True:
            try:
                user_input = input("  You: ").strip()
                if not user_input:
                    continue
                self.chat_history.append({"role": "user", "content": user_input, "time": datetime.now()})
                if user_input.lower() in ['exit', 'quit', 'goodbye', 'bye']:
                    print("\n  JARVIS: Goodbye!\n")
                    break
                print("  JARVIS: Thinking...", end="", flush=True)
                result, handled = _route_and_execute(user_input.lower(), None, self.dashboard)
                if not handled:
                    result = self.llm.chat(user_input)
                    if not isinstance(result, str):
                        result = result.get("text", str(result))
                else:
                    if result == "MEMORY_CLEARED":
                        self.llm.clear_history()
                        result = "Memory cleared."
                print("\r" + " " * 30 + "\r", end="")
                print(f"  JARVIS: {result}\n")
                self.chat_history.append({"role": "assistant", "content": result, "time": datetime.now()})
            except KeyboardInterrupt:
                print("\n\n  JARVIS: Goodbye!\n")
                break
            except Exception as e:
                logger.exception("Chat error")
                print(f"\n  Error: {str(e)}\n")


# ── Voice loop ──────────────────────────────────────────
def run_voice_loop(llm: JarvisLLM, dashboard, tts: TTSEngine | None) -> None:
    if not tts:
        print("  Switching to text mode...")
        text_interface = SimpleChatInterface(llm, dashboard)
        text_interface.run()
        return
    stt = STTEngine()
    tts.speak_sync("Voice mode active. Say hello to wake me.")
    while True:
        try:
            stt.wait_for_wake_word()
            tts.speak("Yes?")
            query = stt.capture_query()
            if not query:
                tts.speak("Didn't catch that.")
                continue
            tasks = _parse_multi_tasks(query)
            if len(tasks) == 0:
                continue
            elif len(tasks) == 1:
                result, handled = _route_and_execute(query, tts, dashboard)
                if not handled:
                    if result == "MEMORY_CLEARED":
                        llm.clear_history()
                        tts.speak("Memory cleared.")
                        continue
                    tts.speak("On it.")
                    response = llm.chat(query)
                    response = response if isinstance(response, str) else response.get("text", str(response))
                    _boxed_print("USER", query)
                    _boxed_print("JARVIS", response)
                    tts.speak(response)
            else:
                _boxed_print("USER", query)
                print(f"  Parsed {len(tasks)} tasks: {tasks}")
                tts.speak(f"Got it. Processing {len(tasks)} tasks.")
                for i, task in enumerate(tasks, 1):
                    try:
                        print(f"  Task {i}/{len(tasks)}: {task}")
                        if i > 1:
                            tts.speak(f"Task {i}.")
                        response, handled = _route_and_execute(task, tts, dashboard)
                        if not handled:
                            response = llm.chat(task)
                            response = response if isinstance(response, str) else response.get("text", str(response))
                        if response:
                            _boxed_print(f"JARVIS ({i}/{len(tasks)})", response)
                            if i == len(tasks) or len(tasks) <= 2:
                                tts.speak(response)
                            elif i % 2 == 0:
                                tts.speak(response)
                    except Exception as e:
                        logger.exception(f"Task {i} failed: {task}")
                        tts.speak(f"Task {i} failed.")
                        continue
                tts.speak(f"All {len(tasks)} tasks complete.")
        except Exception:
            logger.exception("Main loop error")
            try:
                tts.speak("Hit an error, still listening")
            except Exception:
                logger.exception("Failed to speak error message")
            time.sleep(1)


# ── Main entry point ────────────────────────────────────
def main() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')
    log_file = "jarvis_log.txt"
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"JARVIS Log - Started {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*50 + "\n\n")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.FileHandler(log_file, encoding='utf-8')]
    )
    _print_banner()
    mode = _select_mode()
    tts = None
    if mode == 'voice':
        try:
            tts = TTSEngine()
        except Exception as e:
            logger.warning(f"TTS initialization failed: {e}")
            print("  Warning: Voice output not available. Switching to text mode.")
            mode = 'text'
    def _sig_handler(_signum: int, _frame) -> None:
        if tts:
            _shutdown(tts)
        sys.exit(0)
    try:
        signal.signal(signal.SIGINT, _sig_handler)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _sig_handler)
    except Exception:
        logger.exception("Failed to register signal handlers")
    dashboard = SystemDashboard(alert_callback=lambda msg: tts.speak(msg) if tts else None)
    dashboard.start_monitoring()
    try:
        briefing = memory.get_daily_briefing()
        if "All clear" not in briefing:
            if tts and mode == 'voice':
                tts.speak(briefing)
            else:
                print(f"  Daily Briefing: {briefing}")
    except Exception:
        logger.exception("Failed to get daily briefing")
    llm = JarvisLLM()
    try:
        init_youtube_learner(openai_client=llm.client, memory=memory)
        logger.info("YouTube learner initialized")
    except Exception as e:
        logger.warning(f"YouTube learner initialization failed: {e}")
    try:
        init_web_browser(headless=True)
        logger.info("Web browser initialized")
    except Exception as e:
        logger.warning(f"Web browser initialization failed: {e}")
    try:
        init_shopping_assistant()
        logger.info("Shopping assistant initialized")
    except Exception as e:
        logger.warning(f"Shopping assistant initialization failed: {e}")
    logger.info("Task manager ready with {} workers".format(task_manager.max_workers))
    if mode == 'voice':
        print("  Launching modern GUI...")
        try:
            from jarvis.advanced_gui import launch_gui_with_core
            launch_gui_with_core(llm, dashboard, tts)
        except Exception as e:
            logger.exception("GUI launch failed")
            print(f"  Error launching GUI: {e}")
            print("  Falling back to terminal voice mode...")
            if tts:
                tts.speak_sync("JARVIS online. Systems nominal. Voice mode active.")
            run_voice_loop(llm, dashboard, tts)
    else:
        print("  Starting simple chat mode...")
        simple_chat = SimpleChatInterface(llm, dashboard)
        simple_chat.run()


if __name__ == "__main__":
    main()
