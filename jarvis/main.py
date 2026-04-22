"""jarvis.main

Entry point and orchestrator for the JARVIS voice assistant.

This module wires together STT (wake word + query capture), TTS (threaded), and
LLM (Groq + tools). The main loop is defensive and must never permanently crash.
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

logger = logging.getLogger(__name__)


def _print_banner() -> None:
    """Print an ASCII banner on startup."""

    banner = r"""
     __    ___    ____ _    __  _____
    / /   /   |  / __ \ |  / / / ___/
   / /   / /| | / /_/ / | / /  \__ \
  / /___/ ___ |/ _, _/| |/ /  ___/ /
 /_____/_/  |_/_/ |_| |___/  /____/

    """
    print(banner)


def _boxed_print(label: str, text: str) -> None:
    """Print a simple terminal box for visibility/debugging."""

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
    """Parse compound commands into multiple individual tasks.
    
    Smart parser that recognizes command boundaries for mixed commands like:
        'play shape of you and open calculator' -> ['play shape of you', 'open calculator']
        'open calculator notepad and chrome' -> ['open calculator', 'open notepad', 'open chrome']
        'close notepad and chrome' -> ['close notepad', 'close chrome']
    """
    query = query.strip().lower()
    if not query:
        return []

    # List of command starters (verbs that indicate a new command)
    command_starters = [
        # Apps/Windows
        "open ", "close ", "launch ", "start ", "quit ", "kill ", "switch to ",
        # Media
        "play ", "stop ", "pause ", "resume ", "skip ", "next ", "previous ",
        # System
        "move ", "click ", "double click ", "right click ", "drag ", "scroll ",
        "type ", "press ", "hold ", "release ",
        "set volume", "volume ", "mute", "unmute",
        "set brightness", "brightness ",
        "take ", "capture ", "save ", "delete ",
        # Search/Web
        "search ", "find ", "look up ", "google ", "youtube ", "web ",
        # Info
        "what ", "when ", "where ", "who ", "why ", "how ", "tell me ", "show ",
        "get ", "check ", "list ", "status", "system ",
        # Memory
        "add ", "create ", "new ", "save ", "remember ", "note ", "write down ",
        "remove ", "delete ", "clear ", "erase ", "complete ", "finish ", "mark ",
        "show ", "read ", "tell ", "what's ", "what is ", "list ",
        # Communication
        "send ", "email ", "message ", "text ", "call ",
    ]

    # Split markers that separate commands
    split_markers = [" and ", " then ", " also ", " next ", " after that ", " followed by ", " & ", " + "]

    # First, check if this is a simple same-verb command like "open X, Y and Z"
    # These can be split by the noun, not by the verb
    if query.startswith("open "):
        rest = query[5:]  # Remove "open "
        # Check if there are multiple items separated by connectors
        for marker in split_markers:
            if marker in rest:
                parts = rest.split(marker)
                if len(parts) > 1 and all(len(p.strip().split()) <= 2 for p in parts):
                    # Simple items like "calculator" or "notepad"
                    return [f"open {p.strip()}" for p in parts if p.strip()]

    if query.startswith("close "):
        rest = query[6:]  # Remove "close "
        for marker in split_markers:
            if marker in rest:
                parts = rest.split(marker)
                if len(parts) > 1 and all(len(p.strip().split()) <= 2 for p in parts):
                    return [f"close {p.strip()}" for p in parts if p.strip()]

    # For mixed commands with different verbs, find command boundaries
    tasks = []
    remaining = query

    while remaining:
        # Find the earliest split marker
        earliest_split = None
        earliest_pos = len(remaining)
        
        for marker in split_markers:
            pos = remaining.find(marker)
            if pos != -1 and pos < earliest_pos:
                earliest_pos = pos
                earliest_split = marker
        
        if earliest_split is None:
            # No more splits, remaining is the last task
            tasks.append(remaining.strip())
            break
        
        # Split at the marker
        before = remaining[:earliest_pos].strip()
        after = remaining[earliest_pos + len(earliest_split):].strip()
        
        if before:
            tasks.append(before)
        
        # Check if 'after' starts with a new command
        is_new_command = any(after.startswith(starter.strip()) for starter in command_starters)
        
        if not is_new_command and after:
            # This might be a continuation, append to last task
            if tasks:
                tasks[-1] = f"{tasks[-1]} {earliest_split.strip()} {after}"
                break
            else:
                tasks.append(after)
                break
        
        remaining = after
    
    # Clean up and validate tasks
    cleaned_tasks = []
    for task in tasks:
        task = task.strip()
        # Remove trailing connectors
        for marker in split_markers:
            if task.endswith(marker.strip()):
                task = task[:-len(marker.strip())].strip()
        if task:
            cleaned_tasks.append(task)
    
    return cleaned_tasks if len(cleaned_tasks) > 1 else [query]


def _execute_task(query: str, tts: TTSEngine | None, llm: JarvisLLM, dashboard) -> str:
    """Execute a single task and return result.
    
    Returns:
        Result message or empty string if handled internally
    """
    # Check built-in commands first
    if _handle_built_in_command(query, tts, llm, dashboard):
        return ""

    # Use LLM for complex queries
    response = llm.chat(query)
    return response


def _shutdown(tts: TTSEngine | None) -> None:
    """Graceful shutdown handler."""
    
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


def _handle_built_in_command(query: str, tts: TTSEngine | None, llm: JarvisLLM, dashboard: SystemDashboard) -> bool:
    """Handle built-in commands without calling the LLM."""

    q = (query or "").strip().lower()

    if any(p in q for p in ["goodbye", "shut down", "shutdown", "exit", "quit"]):
        dashboard.stop_monitoring()
        if tts:
            tts.speak_sync("Goodbye.")
        sys.exit(0)

    if any(p in q for p in ["clear memory", "forget", "reset", "new conversation"]):
        llm.clear_history()
        if tts:
            tts.speak("Memory cleared.")
        return True

    if any(p in q for p in ["stop talking", "be quiet", "silence", "shut up"]):
        if tts:
            tts.stop()
        return True

    if any(p in q for p in ["daily briefing", "what's on my schedule", "what do i have today"]):
        briefing = memory.get_daily_briefing()
        if tts:
            tts.speak(briefing)
        else:
            print(f"  Daily Briefing: {briefing}")
        return True

    if any(p in q for p in ["system status", "how's my computer", "check system"]):
        status = dashboard.get_quick_status()
        if tts:
            tts.speak(status)
        else:
            print(f"  System Status: {status}")
        return True

    if any(p in q for p in ["list apps", "what apps are running", "show running apps"]):
        from jarvis.tools import list_running_apps
        apps = list_running_apps(limit=20)
        if tts:
            tts.speak(apps.replace("\n", ". "))
        else:
            print(f"  Running Apps:\n{apps}")
        return True

    if q.startswith("close "):
        app_name = q.replace("close ", "").strip()
        if app_name:
            from jarvis.tools import close_app
            result = close_app(app_name)
            if tts:
                tts.speak(result)
            else:
                print(f"  {result}")
            return True

    if any(p in q for p in ["what did we talk about", "what was our conversation", "remember what we discussed", "show past conversations"]):
        conversations = memory.get_recent_conversations(limit=5)
        if conversations:
            lines = [f"{i+1}. {c['summary'][:60]}..." for i, c in enumerate(conversations)]
            response = "Recent conversations:\n" + "\n".join(lines)
        else:
            response = "No conversations found in memory yet."
        if tts:
            tts.speak(response.replace("\n", ". "))
        else:
            print(f"  {response}")
        return True

    # Export memory to readable file
    if any(p in q for p in ["export memory", "save memory to file", "show memory file"]):
        result = memory.export_to_readable()
        if tts:
            tts.speak(result)
        else:
            print(f"  {result}")
        # Try to open the exported file
        try:
            os.startfile("jarvis_memory_export.txt")
        except:
            pass
        return True

    # Save permanent info command
    if q.startswith(("save this in your memory", "save this to your memory", "remember this", "save that in your memory", "save info")):
        # Extract the info to save
        info = q
        for prefix in ["save this in your memory", "save this to your memory", "remember this", "save that in your memory", "save info"]:
            if info.startswith(prefix):
                info = info[len(prefix):].strip()
                break
        if info:
            result = memory.save_permanent_info(info, category="user_important")
            if tts:
                tts.speak(result)
            else:
                print(f"  {result}")
        else:
            response = "What would you like me to save?"
            if tts:
                tts.speak(response)
            else:
                print(f"  {response}")
        return True

    # Web search - built-in for instant response
    search_prefixes = [
        "search web for ", "search for ", "web search ", "google ", 
        "look up ", "find ", "search ", "what is ", "who is ", "how to ",
        "what are ", "where is ", "when is ", "why is ", "tell me about ",
        "information about ", "news about "
    ]
    
    for prefix in search_prefixes:
        if q.startswith(prefix):
            search_query = q[len(prefix):].strip()
            if search_query:
                if tts:
                    tts.speak(f"Searching for: {search_query}")
                else:
                    print(f"  Searching for: {search_query}")
                from jarvis.tools import web_search
                result = web_search(search_query)
                # Truncate if too long for speech
                if len(result) > 300:
                    result = result[:300] + "... Search results truncated."
                if tts:
                    tts.speak(result.replace("\n", ". "))
                else:
                    print(f"  Result: {result}")
                return True

    # YouTube commands - built-in for instant response
    # Note: These only trigger on single-task commands or already-split tasks
    if q.startswith(("play song ", "play video ", "play music ")):
        from jarvis.tools import play_youtube, play_music
        
        # Extract query - handle specific prefixes
        if q.startswith("play song "):
            song_query = q[10:].strip()  # Remove "play song "
        elif q.startswith("play video "):
            song_query = q[11:].strip()  # Remove "play video "
        elif q.startswith("play music "):
            song_query = q[11:].strip()  # Remove "play music "
        else:
            song_query = q[5:].strip() if q.startswith("play ") else q  # Remove "play "
        
        if song_query:
            if tts:
                tts.speak(f"Searching YouTube for: {song_query}")
            else:
                print(f"  Searching YouTube for: {song_query}")
            
            # Use play_music for songs, play_youtube for general videos
            if "song" in q or "music" in q:
                result = play_music(song_query)
            else:
                result = play_youtube(song_query)
            
            if tts:
                tts.speak(result)
            else:
                print(f"  {result}")
            return True
    
    # Handle simple "play X" where X is a known app (not YouTube)
    if q.startswith("play "):
        rest = q[5:].strip().lower()
        # Check if it's trying to play a local media player
        media_players = ["spotify", "vlc", "media player", "itunes", "music"]
        if rest in media_players or any(rest.startswith(mp) for mp in media_players):
            from jarvis.tools import open_app
            result = open_app(rest)
            if tts:
                tts.speak(result)
            else:
                print(f"  {result}")
            return True

    if q.startswith(("search youtube ", "youtube search ", "find on youtube ")):
        from jarvis.tools import search_youtube
        
        query = q.replace("search youtube ", "").replace("youtube search ", "").replace("find on youtube ", "").strip()
        if query:
            if tts:
                tts.speak(f"Searching YouTube for: {query}")
            else:
                print(f"  Searching YouTube for: {query}")
            result = search_youtube(query, max_results=5)
            if tts:
                tts.speak(result.replace("\n", ". "))
            else:
                print(f"  {result}")
            return True

    return False


def _select_mode() -> str:
    """Ask user to select voice or text mode with 10 second timeout.
    
    Returns:
        'voice' or 'text'
    """
    import threading
    import sys
    from select import select
    
    print("\n" + "="*50)
    print("  JARVIS MODE SELECTOR")
    print("="*50)
    print("  Press 'y' then Enter for VOICE mode (speech to speech)")
    print("  Press 'n' then Enter for TEXT mode (text to text, NO speech)")
    print("  Waiting 10 seconds...")
    print("="*50)
    
    result = ['voice']  # Default
    
    def input_thread():
        try:
            user_input = input("\n  Your choice (y/n): ").strip().lower()
            if user_input == 'n':
                result[0] = 'text'
            elif user_input == 'y' or user_input == '':
                result[0] = 'voice'
        except:
            pass
    
    # Start input thread
    t = threading.Thread(target=input_thread)
    t.daemon = True
    t.start()
    t.join(timeout=10)
    
    mode = result[0]
    print(f"\n  Selected mode: {mode.upper()}")
    print("="*50 + "\n")
    
    return mode


class TextInterface:
    """Pure text-based interface for JARVIS - NO speech at all."""
    
    def __init__(self, llm: JarvisLLM, dashboard):
        self.llm = llm
        self.dashboard = dashboard
        # NO TTS - pure text mode
        
    def run(self) -> None:
        """Run pure text-based command loop."""
        print("\n" + "="*50)
        print("  JARVIS TEXT MODE")
        print("  Pure text-to-text communication")
        print("="*50)
        print("  Commands: 'exit', 'quit', 'voice' (switch to voice)")
        print("-" * 50 + "\n")
        
        while True:
            try:
                user_input = input("  You: ").strip()
                if not user_input:
                    continue
                    
                if user_input.lower() in ['exit', 'quit', 'goodbye', 'bye']:
                    print("\n  JARVIS: Shutting down. Goodbye.")
                    print("="*50)
                    break
                    
                if user_input.lower() == 'voice':
                    print("\n  JARVIS: Switching to voice mode...")
                    print("="*50 + "\n")
                    # Initialize TTS for voice mode
                    try:
                        tts = TTSEngine()
                        run_voice_loop(self.llm, self.dashboard, tts)
                    except Exception as e:
                        print(f"  Error: Could not start voice mode: {e}")
                        print("  Staying in text mode.")
                    break
                
                # Process command - NO TTS at all
                print("  JARVIS: Processing...")
                
                # Check for built-in commands (pass None for tts = pure text)
                if _handle_built_in_command(user_input.lower(), None, self.llm, self.dashboard):
                    print()  # Empty line for readability
                    continue
                
                # Use LLM for other queries
                response = self.llm.chat(user_input)
                print(f"\n  JARVIS: {response}\n")
                    
            except KeyboardInterrupt:
                print("\n\n  JARVIS: Interrupted. Goodbye.")
                print("="*50)
                break
            except Exception as e:
                logger.exception("Text mode error")
                print(f"  Error: {str(e)}")


def run_voice_loop(llm: JarvisLLM, dashboard, tts: TTSEngine | None) -> None:
    """Run the voice-based event loop."""
    
    if not tts:
        print("  Error: Voice mode requires TTS but it's not available.")
        print("  Switching to text mode...")
        text_interface = TextInterface(llm, dashboard, None)
        text_interface.run()
        return
    
    # Mic calibration happens during STT initialization
    stt = STTEngine()
    
    tts.speak_sync("Voice mode active. Say hello to wake me.")
    
    while True:
        try:
            stt.wait_for_wake_word()
            tts.speak("Yes?")  # immediate audio feedback

            query = stt.capture_query()
            if not query:
                tts.speak("Didn't catch that.")
                continue

            # Parse multi-task commands
            tasks = _parse_multi_tasks(query)
            
            if len(tasks) == 0:
                continue
            elif len(tasks) == 1:
                # Single task - normal flow
                if _handle_built_in_command(query, tts, llm, dashboard):
                    continue
                
                tts.speak("On it.")
                response = llm.chat(query)
                
                _boxed_print("USER", query)
                _boxed_print("JARVIS", response)
                tts.speak(response)
            else:
                # Multiple tasks - execute sequentially
                _boxed_print("USER", query)
                print(f"  → Parsed {len(tasks)} tasks: {tasks}")
                
                tts.speak(f"Got it. Processing {len(tasks)} tasks.")
                
                for i, task in enumerate(tasks, 1):
                    try:
                        print(f"  → Task {i}/{len(tasks)}: {task}")
                        
                        # Quick feedback for each task
                        if i > 1:  # Don't repeat "On it" for first task
                            tts.speak(f"Task {i}.")
                        
                        response = _execute_task(task, tts, llm, dashboard)
                        
                        if response:  # Empty string means handled internally
                            _boxed_print(f"JARVIS ({i}/{len(tasks)})", response)
                            
                            # Only speak key results to avoid too much talking
                            if i == len(tasks) or len(tasks) <= 2:
                                tts.speak(response)
                            elif i % 2 == 0:  # Speak every other task for long lists
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
    """Run the JARVIS event loop."""

    # Clear terminal for clean startup
    os.system('cls' if os.name == 'nt' else 'clear')

    # Setup logging to file only (not terminal)
    log_file = "jarvis_log.txt"
    # Clear log file on each run
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"JARVIS Log - Started {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*50 + "\n\n")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
        ]
    )

    _print_banner()

    # Select mode (voice or text)
    mode = _select_mode()

    # Initialize components based on mode
    tts = None
    
    # Only initialize TTS for voice mode
    if mode == 'voice':
        try:
            tts = TTSEngine()
        except Exception as e:
            logger.warning(f"TTS initialization failed: {e}")
            print("  Warning: Voice output not available. Switching to text mode.")
            mode = 'text'

    def _sig_handler(_signum: int, _frame) -> None:  # type: ignore[no-untyped-def]
        if tts:
            _shutdown(tts)
        sys.exit(0)

    try:
        signal.signal(signal.SIGINT, _sig_handler)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _sig_handler)
    except Exception:
        logger.exception("Failed to register signal handlers")

    # Initialize dashboard (with TTS alerts only in voice mode)
    dashboard = SystemDashboard(alert_callback=lambda msg: tts.speak(msg) if tts else None)
    dashboard.start_monitoring()

    # Get daily briefing (only speak in voice mode, print in text mode)
    try:
        briefing = memory.get_daily_briefing()
        if "All clear" not in briefing:
            if tts and mode == 'voice':
                tts.speak(briefing)
            else:
                print(f"  Daily Briefing: {briefing}")
    except Exception:
        logger.exception("Failed to get daily briefing")

    # Initialize LLM
    llm = JarvisLLM()

    # Run appropriate mode
    if mode == 'text':
        # Pure text mode - NO TTS at all
        text_interface = TextInterface(llm, dashboard)
        text_interface.run()
    else:
        # Voice mode - with TTS
        if tts:
            tts.speak_sync("JARVIS online. Systems nominal. Voice mode active.")
        run_voice_loop(llm, dashboard, tts)


if __name__ == "__main__":
    main()
