"""JARVIS — Unified Application Entry Point.

Pipeline: User Input → NLP → Intent → Tool Selection → Execute → Verify → Respond
Every action is EXECUTED, VERIFIED, then reported.
"""

from __future__ import annotations

import os
import sys
import time
import asyncio
import logging
from typing import Any, AsyncGenerator

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO), format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger("jarvis")


STARTUP_MESSAGE = """
  +-----------------------------------------------+
  |              J A R V I S                      |
  |   Execution Engine + AI Router                |
  |   Tool-First. Verified. Real.                 |
  +-----------------------------------------------+
"""


class JARVIS:
    def __init__(self) -> None:
        self._boot_start = time.time()
        self._boot_complete = False
        self._debug_mode = os.getenv("JARVIS_DEBUG", "false").lower() in ("true", "1", "yes")

        self._nlp = None
        self._execution = None
        self._memory = None
        self._router = None
        self._knowledge = None
        self._speech = None
        self._vision = None
        self._desktop = None

    async def boot(self) -> None:
        print(STARTUP_MESSAGE)
        checks = {"passed": 0, "total": 0, "critical_failures": []}

        def ok(name: str) -> None:
            checks["total"] += 1
            checks["passed"] += 1
            print(f"  [+] {name:.<40s} PASS")

        def fail(name: str, reason: str, critical: bool = False) -> None:
            checks["total"] += 1
            print(f"  [-] {name:.<40s} FAIL: {reason}")
            if critical:
                checks["critical_failures"].append(name)

        # QWEN3 Brain (New Architecture)
        try:
            from core.qwen3_brain import qwen3_brain
            self._brain = qwen3_brain
            ok("QWEN3 Brain (LLM-based)")
        except Exception as e:
            fail("QWEN3 Brain", str(e), critical=True)

        # Execution Engine
        try:
            from core.execution import execution_engine
            self._execution = execution_engine
            self._execution.debug_mode = self._debug_mode
            ok("Execution Engine")
        except Exception as e:
            fail("Execution Engine", str(e), critical=True)

        # Memory (JSON-based)
        try:
            from core.memory_json import json_memory
            self._memory = json_memory
            ok("Memory (JSON-based)")
        except Exception as e:
            fail("Memory", str(e))

        # AI Router
        try:
            from core.router import router
            self._router = router
            ok(f"AI Router ({router.provider_count} providers)")
        except Exception as e:
            fail("AI Router", str(e))

        # Knowledge
        try:
            from core.knowledge_semantic import semantic_knowledge
            self._knowledge = semantic_knowledge
            ok("Knowledge Engine (Semantic)")
        except Exception as e:
            fail("Knowledge Engine", str(e))

        # Speech
        try:
            from interface.speech import speech_engine
            self._speech = speech_engine
            avail = speech_engine.is_available()
            if isinstance(avail, dict):
                tts_ok = "TTS" if avail.get("tts") else ""
                stt_ok = "STT" if avail.get("stt") else ""
                status = " + ".join(filter(None, [tts_ok, stt_ok])) or "not available"
            else:
                status = "TTS Available" if avail else "not available"
            ok(f"Speech Engine ({status})")
        except Exception as e:
            fail("Speech Engine", str(e))

        # Vision
        try:
            from vision.vision import vision_engine
            self._vision = vision_engine
            ok("Vision Engine")
        except Exception as e:
            fail("Vision Engine", str(e))

        # Desktop Intelligence
        try:
            from interface.desktop import desktop
            self._desktop = desktop
            ok("Desktop Intelligence")
        except Exception as e:
            fail("Desktop Intelligence", str(e))

        # Tool Registry
        try:
            from core.tools import tool_registry
            tools_count = len(tool_registry.get_all())
            ok(f"Tool Registry ({tools_count} tools)")
        except Exception as e:
            fail("Tool Registry", str(e))

        # Ready
        self._boot_complete = True
        elapsed = time.time() - self._boot_start
        status = "READY" if not checks["critical_failures"] else "DEGRADED"
        print(f"\n  {checks['passed']}/{checks['total']} Checks Passed — {status}")
        print(f"  Boot time: {elapsed:.1f}s\n")
        if checks["critical_failures"]:
            print(f"  Critical: {', '.join(checks['critical_failures'])}\n")

    async def handle(self, user_input: str) -> dict[str, Any]:
        start = time.time()
        reply = ""
        verified = False
        tool_name = ""
        
        # Use QWEN3 brain for processing
        if self._brain:
            try:
                brain_response = await self._brain.generate_complete(user_input)
                
                if brain_response.success and brain_response.content:
                    content = brain_response.content.strip()
                    
                    # Check for JSON tool call
                    if content.startswith("{") and content.endswith("}"):
                        import json as json_mod
                        tool_data = json_mod.loads(content)
                        tool_name = tool_data.get("tool", "")
                        params = tool_data.get("params", {})
                        llm_response = tool_data.get("response", "")
                        
                        if tool_name:
                            # Execute tool
                            tool_call = {"tool": tool_name, "params": params, "response": llm_response}
                            tool_result = await self._execution.execute_with_llm(
                                user_input, tool_call
                            )
                            
                            result_success = tool_result.success
                            reply = llm_response or (
                                f"Done! {tool_name.replace('_', ' ')} completed."
                                if result_success
                                else f"Failed to {tool_name.replace('_', ' ')}."
                            )
                            verified = tool_result.verified
                            trace = self._execution.get_last_trace()
                        else:
                            reply = llm_response
                            verified = True
                            trace = None
                    else:
                        reply = content
                        verified = True
                        trace = None
                else:
                    reply = "I'm having trouble processing that right now."
            except Exception as e:
                logger.error(f"Brain error: {e}")
                reply = f"Processing error: {str(e)}"
        else:
            reply = "Brain not available."
        
        total_ms = round((time.time() - start) * 1000, 1)
        
        # AI Fallback if no reply
        if not reply and self._router:
            try:
                fallback = await self._router.chat(user_input)
                if fallback.success and fallback.content:
                    return {
                        "response": fallback.content,
                        "success": True, "verified": False,
                        "tool": "ai", "intent": "ai_fallback",
                        "intent_confidence": 0.5, "total_ms": total_ms,
                    }
            except Exception as e:
                logger.error("Router fallback error: %s", e)
        
        return {
            "response": reply,
            "success": bool(reply),
            "verified": verified,
            "tool": tool_name,
            "intent": "llm",
            "intent_confidence": 1.0,
            "total_ms": total_ms,
        }
    
    async def handle_stream(self, user_input: str) -> AsyncGenerator[str, None]:
        """Handle user input with token-by-token streaming response.
        
        Streams tokens as they arrive from the LLM, then executes any
        tool call embedded in the response. The raw JSON tool call is
        NOT displayed to the user — only the natural language response.
        """
        if not self._brain:
            if self._router:
                async for token in self._router.chat_stream(user_input):
                    yield token
            else:
                yield "No AI available."
            return

        try:
            collected: list[str] = []
            async for token in self._brain.generate(user_input):
                if token.startswith("\x00"):
                    yield token
                else:
                    collected.append(token)
                    yield token

            full = "".join(collected).strip()
            if not full:
                return

            if full.startswith("{") and full.endswith("}"):
                import json as _j
                try:
                    data = _j.loads(full)
                    tool_name = data.get("tool", "")
                    params = data.get("params", {})
                    llm_text = data.get("response", "")

                    if tool_name:
                        tool_call = {
                            "tool": tool_name,
                            "params": params,
                            "response": llm_text,
                        }
                        result = await self._execution.execute_with_llm(
                            user_input, tool_call
                        )
                        if not result.success:
                            yield f" (Error: {result.error})"
                    # For JSON tool calls, only yield the natural response
                    # (already streamed), no duplicate
                except _j.JSONDecodeError:
                    pass  # already streamed as tokens
            # For plain text, it's already been streamed — no duplicate

        except Exception as e:
            logger.error("Stream error: %s", e)
            yield f"Error: {str(e)}"

    def enable_debug(self) -> None:
        self._debug_mode = True
        if self._execution:
            self._execution.debug_mode = True

    def disable_debug(self) -> None:
        self._debug_mode = False
        if self._execution:
            self._execution.debug_mode = False

    async def shutdown(self) -> None:
        print("  Goodbye.\n")


async def interactive_mode(jarvis: JARVIS) -> None:
    print("  Commands: health, tools, debug, quit")
    print()
    while True:
        try:
            user_input = input("  You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            await jarvis.shutdown()
            break
        if not user_input:
            continue

        cmd = user_input.lower()

        if cmd in ("quit", "exit", "q"):
            await jarvis.shutdown()
            break
        if cmd == "health":
            from interface.desktop import desktop
            print()
            print(desktop.format_status())
            print()
            continue
        if cmd == "tools":
            from core.tools import tool_registry
            tools = tool_registry.get_all()
            print(f"\n  Tools ({len(tools)}):")
            for name, t in tools.items():
                print(f"    {name:25s} [{t['category'].value}] {t['description']}")
            print()
            continue
        if cmd == "debug":
            if jarvis._debug_mode:
                jarvis.disable_debug()
                print("  Debug mode OFF")
            else:
                jarvis.enable_debug()
                print("  Debug mode ON")
            continue
            
        if cmd == "current voice":
            from speech.settings import settings
            print(f"\n  Current Voice: {settings.get('voice').capitalize()} (Permanent)")
            print(f"  Provider: {settings.get('provider').capitalize()}\n")
            continue
            
        if cmd == "current mood":
            if jarvis._speech:
                try:
                    mood = jarvis._speech._engine.mood_engine.get_current_mood()
                    print(f"\n  Current Mood: {mood.capitalize()}\n")
                except: pass
            continue
            
        if cmd == "voice stats":
            if jarvis._speech:
                try:
                    from speech.generate_agi_audio import _lazy_load
                    avail = _lazy_load()
                    print(f"\n  Kokoro-ONNX Available: {avail}")
                    print(f"  Cache Enabled: {jarvis._speech._engine.settings.get('cache')}\n")
                except: pass
            continue
            
        if cmd in ("mute", "unmute"):
            if jarvis._speech:
                from speech.settings import settings
                is_speech = cmd == "unmute"
                settings.set("speech", is_speech)
                print(f"\n  Speech Output: {'ON' if is_speech else 'OFF'}\n")
            continue
            
        if cmd == "stop speaking":
            if jarvis._speech:
                jarvis._speech._engine.stop_speaking()
                print("\n  Stopped speech.\n")
            continue
            
        if cmd == "benchmark tts":
            from speech.benchmark import run_benchmark
            run_benchmark()
            continue
            
        if cmd in ("restart speech", "reload speech"):
            if jarvis._speech:
                print("\n  Reloading speech settings...")
                jarvis._speech._engine.settings.load()
            continue

        result = await jarvis.handle(user_input)
        print(f"\n  {result['response']}\n")
        verified = "[OK] verified" if result.get("verified") else "[FAIL] unverified"
        tool = result.get("tool") or "llm"
        ms = result.get("total_ms", 0)
        intent = result.get("intent", "?")
        conf = result.get("intent_confidence", 0)
        
        # Display logs as a markdown dropdown menu
        log_menu = f"""  <details>
  <summary>System Logs [{tool}]</summary>
  <ul>
    <li><b>Status</b>: {verified}</li>
    <li><b>Intent</b>: {intent} (conf: {conf:.2f})</li>
    <li><b>Latency</b>: {ms}ms</li>
  </ul>
  </details>"""
        print(log_menu)


async def main() -> None:
    jarvis = JARVIS()
    if "--debug" in sys.argv:
        jarvis.enable_debug()
        sys.argv.remove("--debug")
    try:
        await jarvis.boot()
        if len(sys.argv) > 1:
            text = " ".join(sys.argv[1:])
            if text == "health":
                from interface.desktop import desktop
                print(desktop.format_status())
            elif text == "tools":
                from core.tools import tool_registry
                for name, t in tool_registry.get_all().items():
                    print(f"  {name:25s} [{t['category'].value}]")
            else:
                result = await jarvis.handle(text)
                print(result["response"])
        else:
            await interactive_mode(jarvis)
    except KeyboardInterrupt:
        pass
    finally:
        await jarvis.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
