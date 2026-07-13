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

from jarvis.execution_engine import ExecutionEngine
from jarvis.command_engine import CommandEngine
from jarvis.fast_path import is_trivial

from jarvis.task_manager import task_manager

logger = logging.getLogger(__name__)


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


_EXECUTION_ENGINE = ExecutionEngine()

_TRIVIAL: set[str] = {
    "hello", "hi", "hey", "thanks", "thank you", "ok", "okay", "yes", "no",
    "bye", "goodbye", "thankyou", "thx", "ty", "k", "kk", "cool", "nice",
    "great", "awesome", "good", "fine", "hello jarvis", "hey jarvis",
}


def _route_and_execute(query: str, tts: TTSEngine | None, dashboard: SystemDashboard) -> tuple[str, bool]:
    t0 = time.time()
    cleaned = query.strip().lower()
    if not cleaned:
        return ("", True)

    # Meta-commands (exit, clear memory, silence)
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

    # Trivial greetings - skip tool execution
    if cleaned in _TRIVIAL or is_trivial(cleaned):
        _perf("trivial", t0)
        return ("", True)

    # NEW: Use the unified execution engine (tool-first, LLM-last)
    def _llm_callable(q: str) -> str:
        """Wrapper to call the LLM from the execution engine."""
        # Import here to avoid circular imports
        from jarvis.llm import JarvisLLM
        # The LLM is created in main() and passed via closure
        return _llm_instance.chat(q) if _llm_instance else "LLM not initialized."

    result, handled = _EXECUTION_ENGINE.execute(query, llm_callable=_llm_callable)
    _log_perf(query)
    return (result, handled)


# Placeholder for LLM instance (set in main())
_llm_instance = None


def _execute_task(query: str, tts: TTSEngine | None, llm: JarvisLLM, dashboard) -> str:
    global _llm_instance
    _llm_instance = llm
    result, handled = _route_and_execute(query, tts, dashboard)
    return result


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


class SimpleChatInterface:
    def __init__(self, llm: JarvisLLM, dashboard):
        self.llm = llm
        self.dashboard = dashboard
        self.chat_history: list[dict] = []

    def _print_chatgpt_header(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\n" + "=" * 60)
        print("  JARVIS AI - Simple Chat Mode")
        print("  Type 'exit' to quit")
        print("=" * 60 + "\n")

    def run(self) -> None:
        global _llm_instance
        _llm_instance = self.llm
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


def run_voice_loop(llm: JarvisLLM, dashboard, tts: TTSEngine | None) -> None:
    global _llm_instance
    _llm_instance = llm
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
                    if result == "MEMORY_CLEARED":
                        llm.clear_history()
                        tts.speak("Memory cleared.")
                    elif result:
                        _boxed_print("USER", query)
                        _boxed_print("JARVIS", result)
                        tts.speak(result)
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
        from jarvis.router import get_router
        _router = get_router()
        init_youtube_learner(memory=memory, router_client=_router)
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


def init_web_browser(headless: bool = True):
    pass


def init_shopping_assistant():
    pass


if __name__ == "__main__":
    main()
