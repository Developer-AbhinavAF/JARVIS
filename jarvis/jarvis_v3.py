"""JARVIS V3 — Cognitive AI Operating System.

Modern entry point that wires together:
  - V3 Semantic NLP Pipeline (35 phases)
  - Speech Engine (ElevenLabs streaming TTS + Whisper STT)
  - Vision Engine (screen capture, OCR, UI detection, visual reasoning)
  - Cognitive Architecture (perception, attention, decision, reflection)
  - Planning Engine (task decomposition, dependency graphs, scheduling)
  - Tool Intelligence (platform routing, recovery, learning)

Usage:
  python -m jarvis.jarvis_v3              # Interactive mode selector
  python -m jarvis.jarvis_v3 --voice      # Force voice mode
  python -m jarvis.jarvis_v3 --text       # Force text mode
  python -m jarvis.jarvis_v3 --test       # Run system self-test
"""

from __future__ import annotations

import os
import sys
import time
import signal
import logging
import argparse
import threading
from datetime import datetime

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# BANNER
# ════════════════════════════════════════════════════════════════════

BANNER = r"""
     _   _   _   _   _   _   _   _
    | |_| |_| |_| |_| |_| |_| |_| |
    |   _J_A_R_V_I_S_   V 3      |
    |  Cognitive AI Operating System|
    |____________________________|

    NLP Pipeline:   35 phases (~10ms)
    Speech:         ElevenLabs streaming + Whisper STT
    Vision:         Screen capture, OCR, UI detection
    Cognitive:      Perception -> Decision -> Reflection
    Planning:       Task decomposition, dependency graphs
    Tools:          Platform-aware routing + recovery
"""


# ════════════════════════════════════════════════════════════════════
# SYSTEM INITIALIZATION
# ════════════════════════════════════════════════════════════════════

def _init_logging() -> None:
    log_file = "jarvis_v3_log.txt"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"JARVIS V3 Log — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8")],
    )


def _load_env() -> None:
    from pathlib import Path
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
        except ImportError:
            pass


# ════════════════════════════════════════════════════════════════════
# SYSTEM HEALTH CHECK
# ════════════════════════════════════════════════════════════════════

class SystemHealth:
    """Checks all subsystems at startup."""

    def __init__(self) -> None:
        self.results: dict[str, dict] = {}

    def check_all(self) -> dict[str, dict]:
        self._check_nlp()
        self._check_speech()
        self._check_vision()
        self._check_cognitive()
        self._check_planner()
        self._check_tools()
        self._check_agents()
        self._check_knowledge()
        self._check_learning()
        self._check_llm()
        return self.results

    def _check_nlp(self) -> None:
        try:
            from jarvis.nlp import SemanticNLPEngine, nlp_engine
            t0 = time.perf_counter()
            result = nlp_engine.process("hello")
            ms = (time.perf_counter() - t0) * 1000
            self.results["nlp"] = {
                "status": "ok",
                "latency_ms": round(ms, 1),
                "intent": result.intent if hasattr(result, "intent") else "unknown",
            }
        except Exception as e:
            self.results["nlp"] = {"status": "error", "error": str(e)}

    def _check_speech(self) -> None:
        try:
            from jarvis.speech import speech_engine
            caps = speech_engine.get_capabilities()
            self.results["speech"] = {
                "status": "ok",
                "tts_available": caps.get("tts_available", False),
                "stt_engine": caps.get("stt_engine", "none"),
            }
        except Exception as e:
            self.results["speech"] = {"status": "error", "error": str(e)}

    def _check_vision(self) -> None:
        try:
            from jarvis.vision import VisionEngine
            engine = VisionEngine()
            caps = engine.capability_detector.detect("hello") if hasattr(engine, "capability_detector") else {}
            self.results["vision"] = {
                "status": "ok",
                "capabilities": len(caps) if isinstance(caps, dict) else 0,
            }
        except Exception as e:
            self.results["vision"] = {"status": "error", "error": str(e)}

    def _check_cognitive(self) -> None:
        try:
            from jarvis.cognitive import CognitiveEngine
            engine = CognitiveEngine()
            self.results["cognitive"] = {"status": "ok"}
        except Exception as e:
            self.results["cognitive"] = {"status": "error", "error": str(e)}

    def _check_planner(self) -> None:
        try:
            from jarvis.planner import PlanningEngine
            engine = PlanningEngine()
            self.results["planner"] = {"status": "ok"}
        except Exception as e:
            self.results["planner"] = {"status": "error", "error": str(e)}

    def _check_tools(self) -> None:
        try:
            from jarvis.tool_intelligence import ToolIntelligenceEngine
            engine = ToolIntelligenceEngine()
            self.results["tools"] = {"status": "ok"}
        except Exception as e:
            self.results["tools"] = {"status": "error", "error": str(e)}

    def _check_agents(self) -> None:
        try:
            from jarvis.agents import get_orchestrator
            orch = get_orchestrator()
            health = orch.get_all_health()
            healthy = sum(1 for h in health.values() if h["status"] in ("idle", "busy"))
            self.results["agents"] = {
                "status": "ok",
                "count": len(health),
                "healthy": healthy,
            }
        except Exception as e:
            self.results["agents"] = {"status": "error", "error": str(e)}

    def _check_knowledge(self) -> None:
        try:
            from jarvis.knowledge import knowledge_engine
            stats = knowledge_engine.get_stats()
            self.results["knowledge"] = {
                "status": "ok",
                "entities": stats.get("graph", {}).get("entity_count", 0),
                "relationships": stats.get("graph", {}).get("relationship_count", 0),
                "embeddings": stats.get("embeddings", {}).get("stored_embeddings", 0),
            }
        except Exception as e:
            self.results["knowledge"] = {"status": "error", "error": str(e)}

    def _check_learning(self) -> None:
        try:
            from jarvis.learning import learning_engine
            stats = learning_engine.get_stats()
            self.results["learning"] = {
                "status": "ok",
                "interactions": stats.get("interactions", 0),
                "experiences": stats.get("experiences", {}).get("total", 0),
            }
        except Exception as e:
            self.results["learning"] = {"status": "error", "error": str(e)}

    def _check_llm(self) -> None:
        try:
            from jarvis import config
            has_key = bool(config.AI_API_KEY)
            has_model = bool(config.AI_MODEL)
            self.results["llm"] = {
                "status": "ok",
                "api_key_set": has_key,
                "model_set": has_model,
            }
        except Exception as e:
            self.results["llm"] = {"status": "error", "error": str(e)}

    def print_report(self) -> None:
        print("\n" + "=" * 60)
        print("  JARVIS V3 SYSTEM HEALTH CHECK")
        print("=" * 60)
        for name, info in self.results.items():
            status = info.get("status", "unknown")
            icon = "  [OK]  " if status == "ok" else " [FAIL]"
            details = {k: v for k, v in info.items() if k != "status"}
            detail_str = f" — {details}" if details else ""
            print(f"  {icon} {name.upper():12s}{detail_str}")
        print("=" * 60)
        ok_count = sum(1 for r in self.results.values() if r.get("status") == "ok")
        total = len(self.results)
        print(f"  Result: {ok_count}/{total} systems operational")
        print("=" * 60 + "\n")


# ════════════════════════════════════════════════════════════════════
# TEXT INTERFACE
# ════════════════════════════════════════════════════════════════════

class TextInterface:
    """ChatGPT-style text conversation using V3 NLP + Multi-Agent + Knowledge + Learning."""

    def __init__(self) -> None:
        from jarvis.nlp import SemanticNLPEngine
        from jarvis.llm import JarvisLLM
        from jarvis.agents import get_orchestrator
        from jarvis.knowledge import knowledge_engine
        from jarvis.learning import learning_engine

        self.nlp = SemanticNLPEngine()
        self.llm = JarvisLLM()
        self.orch = get_orchestrator()
        self.knowledge = knowledge_engine
        self.learning = learning_engine
        self.history: list[dict] = []

    def run(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")
        print("\n" + "=" * 60)
        print("  JARVIS V3 — Text Mode (Multi-Agent + Knowledge + Learning)")
        print("  15 agents | NLP: 35 phases | Vision | Cognitive | Knowledge | Learning")
        print("  Type 'exit' to quit, 'stats' for performance, 'agents' for agent health")
        print("  Type 'learn <text>' to teach, 'search <query>' to search knowledge")
        print("  Type 'habits', 'prefs', 'errors' for learning insights")
        print("=" * 60 + "\n")
        print("  JARVIS: Hello! I'm JARVIS V3 — I learn from every interaction.\n")

        while True:
            try:
                user_input = input("  You: ").strip()
                if not user_input:
                    continue

                if user_input.lower() in ("exit", "quit", "goodbye", "bye"):
                    print("\n  JARVIS: Goodbye!\n")
                    break

                if user_input.lower() == "stats":
                    self._show_stats()
                    continue

                if user_input.lower() == "agents":
                    self._show_agents()
                    continue

                if user_input.lower().startswith("learn "):
                    self._handle_learn(user_input[6:].strip())
                    continue

                if user_input.lower().startswith("search "):
                    self._handle_search(user_input[7:].strip())
                    continue

                if user_input.lower() == "habits":
                    self._show_habits()
                    continue

                if user_input.lower() == "prefs":
                    self._show_preferences()
                    continue

                if user_input.lower() == "errors":
                    self._show_errors()
                    continue

                self.history.append({"role": "user", "content": user_input})

                # NLP processing
                t0 = time.perf_counter()
                nlp_result = self.nlp.process(user_input)
                nlp_ms = (time.perf_counter() - t0) * 1000

                # Multi-agent execution
                t1 = time.perf_counter()
                agent_result = self.orch.execute(
                    user_input,
                    intent=nlp_result.intent,
                    entities=nlp_result.entities,
                )
                agent_ms = (time.perf_counter() - t1) * 1000

                total_ms = (time.perf_counter() - t0) * 1000

                # Build response: prefer agent result, fallback to NLP/LLM
                response = agent_result.get("response", "")
                if not response:
                    response = self._nlp_response(nlp_result, user_input)

                agents_used = agent_result.get("agents_used", [])
                agent_str = "+".join(agents_used) if agents_used else "none"

                print(f"\n  JARVIS: {response}\n")
                print(f"  [{total_ms:.0f}ms | nlp={nlp_ms:.0f}ms agent={agent_ms:.0f}ms | intent={nlp_result.intent} | agents={agent_str}]\n")

                self.history.append({"role": "assistant", "content": response})

                # Learn from this interaction
                self.learning.learn_from_interaction(
                    user_input=user_input,
                    response=response,
                    intent=nlp_result.intent,
                    entities=nlp_result.entities,
                    tool_used=agent_result.get("tool", ""),
                    tool_success=bool(agent_result.get("response")),
                    latency_ms=total_ms,
                    emotion=nlp_result.emotion if hasattr(nlp_result, "emotion") else "",
                )

            except KeyboardInterrupt:
                print("\n\n  JARVIS: Goodbye!\n")
                break
            except Exception as e:
                logger.exception("Chat error")
                print(f"\n  Error: {e}\n")

    def _nlp_response(self, result, user_input: str) -> str:
        from jarvis.nlp.utils import NLPOutput
        if not isinstance(result, NLPOutput):
            return str(result) if result else ""
        if result.response_text:
            return result.response_text
        return self.llm.chat(user_input)

    def _show_stats(self) -> None:
        stats = self.orch.get_stats()
        print(f"\n  --- V3 Stats ---")
        print(f"  History: {len(self.history)} turns")
        print(f"  Agents: {stats['agent_count']}")
        print(f"  Tasks executed: {stats['total_tasks']}")
        print(f"  Avg latency: {stats['avg_latency_ms']}ms")
        print()

    def _show_agents(self) -> None:
        health = self.orch.get_all_health()
        print("\n  --- Agent Health ---")
        for name, h in health.items():
            icon = "[OK] " if h["status"] in ("idle", "busy") else "[FAIL]"
            print(f"  {icon} {name:15s} {h['status']:8s} rate={h['success_rate']:.2f} latency={h['latency_ms']:.1f}ms")
        print()

    def _handle_learn(self, text: str) -> None:
        """Teach JARVIS new information."""
        if not text:
            print("  Usage: learn <text to teach>")
            return
        result = self.knowledge.learn(text)
        print(f"\n  Learned: {result.get('entities', 0)} entities, {result.get('relationships', 0)} relationships ({result.get('latency_ms', 0):.1f}ms)\n")

    def _handle_search(self, query: str) -> None:
        """Search the knowledge base."""
        if not query:
            print("  Usage: search <query>")
            return
        results = self.knowledge.search(query, limit=5)
        if results:
            print(f"\n  Found {len(results)} results:")
            for e in results:
                print(f"    - {e['name']} ({e['entity_type']}): {e['description'][:80]}")
        else:
            print("\n  No results found. Try 'learn <text>' to add knowledge.\n")

    def _show_habits(self) -> None:
        """Show detected user habits."""
        habits = self.learning.habits.get_habits(min_confidence=0.0)
        if habits:
            print("\n  --- Detected Habits ---")
            for h in habits[:10]:
                print(f"    {h['name']} (confidence={h['confidence']:.2f}, freq={h['frequency']})")
        else:
            print("\n  No habits detected yet. I'm still learning your patterns.\n")

    def _show_preferences(self) -> None:
        """Show learned preferences."""
        prefs = self.learning.preferences.get_all()
        if prefs:
            print("\n  --- Learned Preferences ---")
            for p in prefs[:10]:
                print(f"    {p['category']}:{p['key']} = {p['value']} (score={p['score']:.2f})")
        else:
            print("\n  No preferences learned yet.\n")

    def _show_errors(self) -> None:
        """Show learned error patterns."""
        errors = self.learning.errors.get_errors(limit=10)
        if errors:
            print("\n  --- Known Errors ---")
            for e in errors:
                print(f"    {e['error_type']}: {e['error_message'][:50]} (occurrences={e['occurrences']})")
                if e['fix']:
                    print(f"      Fix: {e['fix']}")
        else:
            print("\n  No errors recorded.\n")


# ════════════════════════════════════════════════════════════════════
# VOICE INTERFACE
# ════════════════════════════════════════════════════════════════════

class VoiceInterface:
    """Full voice conversation using V3 NLP + Speech Engine."""

    def __init__(self) -> None:
        from jarvis.speech import SpeechEngine
        from jarvis.nlp import SemanticNLPEngine

        self.nlp = SemanticNLPEngine()
        self.speech = SpeechEngine()
        self.speech.configure_nlp(self.nlp.process)
        self.is_running = False

    def run(self) -> None:
        caps = self.speech.get_capabilities()
        if not caps.get("tts_available"):
            print("  ElevenLabs TTS not available — switching to text mode.")
            TextInterface().run()
            return

        print("\n  JARVIS V3 Voice Mode")
        print("  Say something to begin. Press Ctrl+C to stop.\n")

        self.is_running = True
        self.speech.start()

        try:
            while self.is_running:
                result = self.speech.listen_once(timeout=5.0)
                if not result.text:
                    continue

                print(f"  You: {result.text}")

                turn = self.speech.loop.process_single(result.text)
                if turn.response:
                    print(f"  JARVIS: {turn.response}")
                    self.speech.speak(turn.response, emotion=turn.emotion, blocking=True)

        except KeyboardInterrupt:
            print("\n  Stopping voice mode...")
        finally:
            self.speech.stop()
            print("  Voice mode stopped.\n")


# ════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ════════════════════════════════════════════════════════════════════

def main() -> None:
    _init_logging()
    _load_env()

    parser = argparse.ArgumentParser(description="JARVIS V3 — Cognitive AI Operating System")
    parser.add_argument("--voice", action="store_true", help="Force voice mode")
    parser.add_argument("--text", action="store_true", help="Force text mode")
    parser.add_argument("--test", action="store_true", help="Run system self-test")
    args = parser.parse_args()

    print(BANNER)

    if args.test:
        health = SystemHealth()
        health.check_all()
        health.print_report()
        return

    if args.voice:
        VoiceInterface().run()
        return

    if args.text:
        TextInterface().run()
        return

    print("  Select mode:")
    print("    [1] Text mode  (keyboard input)")
    print("    [2] Voice mode (ElevenLabs + Whisper)")
    print("    [3] System health check")
    print()

    try:
        choice = input("  Choice (1/2/3, default=1): ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = "1"

    if choice == "2":
        VoiceInterface().run()
    elif choice == "3":
        health = SystemHealth()
        health.check_all()
        health.print_report()
    else:
        TextInterface().run()


if __name__ == "__main__":
    main()
