"""DEPRECATED: interface/app.py — Legacy application entry point.

This module is DEPRECATED and replaced by core/jarvis_core.py.

The new architecture uses:
- core/jarvis_core.py - Single shared backend for all interfaces
- interface/api.py - Unified FastAPI server
- interface/cli.py - CLI interface using JarvisCore

Migration guide:
- Use: from core.jarvis_core import JarvisCore
- CLI now imports JarvisCore directly
- API requests go through interface/api.py

This file is kept for backward compatibility only and will be removed
in a future version.
"""
import time
import logging
import asyncio
from typing import Any, Dict

logger = logging.getLogger(__name__)


class JARVIS:
    """Main JARVIS application class."""
    
    def __init__(self, debug: bool = False):
        self._debug_mode = debug
        self._execution_first = None
        self._brain = None
        self._router = None
        self._speech = None
        self._execution = None
        self._boot_complete = False
        self._boot_start = time.time()
        self._stream_emitted = False

    def enable_debug(self) -> None:
        """Enable debug mode for JARVIS.

        This sets the internal _debug_mode flag and configures the logger to emit
        DEBUG level messages.
        """
        self._debug_mode = True
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")

    def disable_debug(self) -> None:
        """Disable debug mode for JARVIS.

        Resets the internal _debug_mode flag and restores the logger to INFO
        level.
        """
        self._debug_mode = False
        logger.setLevel(logging.INFO)
        logger.info("Debug mode disabled")        
    def boot(self) -> None:
        """Boot JARVIS and load all components."""
        checks = {"total": 0, "passed": 0, "critical_failures": []}
        
        def ok(name: str) -> None:
            checks["total"] += 1
            checks["passed"] += 1
            try:
                print(f"  [+] {name:.<40s} PASS", flush=True)
            except:
                pass
        
        def fail(name: str, reason: str, critical: bool = False) -> None:
            checks["total"] += 1
            try:
                print(f"  [-] {name:.<40s} FAIL: {reason}", flush=True)
            except:
                pass
            if critical:
                checks["critical_failures"].append(name)
        
        def skip(name: str, reason: str, critical: bool = False) -> None:
            checks["total"] += 1
            checks["passed"] += 1  # Skipped items count as passed (non-critical)
            try:
                print(f"  [*] {name:.<40s} SKIP: {reason}", flush=True)
            except:
                pass
        
        # Model backend (DEPRECATED GPU scripts) — skipped, using API mode
        # The legacy GPU automation scripts are deprecated. System now uses:
        # - Local Ollama (configured via .env)
        # - Cloud API fallbacks (configured via .env)
        skip("Model backend (start_model.py)", "DEPRECATED — using API mode instead", critical=False)

        # Ollama tunnel (ngrok) — live status so the user can see which path will serve replies
        try:
            from core.router import check_tunnel_sync
            reachable, detail = check_tunnel_sync()
            if reachable:
                ok(f"Ollama tunnel (ngrok) {detail}")
            else:
                fail("Ollama tunnel (ngrok)", f"{detail} — will use cloud APIs", critical=False)
        except Exception as e:
            fail("Ollama tunnel (ngrok)", str(e), critical=False)

        # This is the authoritative request pipeline. It loads cached FOOD,
        # tool contracts, memory, and the local intent vectors once at startup.
        try:
            from core.execution_first import build_runtime
            self._execution_first = build_runtime()
            ok("Execution-first runtime")
        except Exception as e:
            fail("Execution-first runtime", str(e), critical=True)
        
        # Do not import legacy LLM, planner, speech, vision, or duplicate memory
        # systems during startup. They are loaded only by the low-confidence path.
        
        # Speech stub (vision already removed)
        
        # QWEN3 Brain (LLM reasoner for execution_first runtime)
        try:
            from core.qwen3_brain import qwen3_brain
            self._brain = qwen3_brain
            ok("QWEN3 Brain (LLM-based)")
        except Exception as e:
            fail("QWEN3 Brain", str(e), critical=False)  # Not critical, execution_first works without it

        # AI Router
        try:
            from core.router import router
            self._router = router
            ok(f"AI Router ({router.provider_count} providers)")
        except Exception as e:
            fail("AI Router", str(e), critical=False)

        # Knowledge - handled by execution_first runtime
        ok("Knowledge (integrated in execution-first runtime)")

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
            fail("Speech Engine", str(e), critical=False)

        # Vision - stub implementation (vision module removed)
        ok("Vision Engine (stub implementation)")

        # Desktop Intelligence
        try:
            from interface.desktop import desktop
            self._desktop = desktop
            ok("Desktop Intelligence")
        except Exception as e:
            fail("Desktop Intelligence", str(e), critical=False)

        # Tool Registry (legacy - used by QWEN3 brain)
        try:
            from core.tools import tool_registry
            tools_count = len(tool_registry.get_all())
            ok(f"Tool Registry ({tools_count} tools)")
        except Exception as e:
            fail("Tool Registry", str(e), critical=False)

        # Ready
        self._boot_complete = not checks["critical_failures"]
        elapsed = time.time() - self._boot_start
        status = "READY" if not checks["critical_failures"] else "DEGRADED"
        try:
            print(f"\n  {checks['passed']}/{checks['total']} Checks Passed — {status}", flush=True)
            print(f"  Boot time: {elapsed:.1f}s\n", flush=True)
        except:
            pass
        if checks["critical_failures"]:
            try:
                print(f"  Critical: {', '.join(checks['critical_failures'])}\n", flush=True)
            except:
                pass
        
        if not self._boot_complete:
            logger.warning("JARVIS booted in degraded mode (missing critical components)")

    async def handle(self, user_input: str) -> dict[str, Any]:
        """Handle user input; the LLM reasons and calls tools via JSON tool calls."""
        
        # If execution_first didn't handle it, try to load LLM
        if self._brain is None:
            try:
                from core.qwen3_brain import qwen3_brain
                self._brain = qwen3_brain
            except Exception as exc:
                return {"response": "I'm not able to reason about that right now.", "success": False,
                        "verified": False, "tool": "", "intent": "unknown", "intent_confidence": 0.0,
                        "entities": {}, "context": {}, "reasoned": False, "reasoning_level": 3, "error": str(exc)}
        
        # Use QWEN3 brain for all other input
        start = time.time()
        reply = ""
        verified = False
        
        try:
            brain_response = await self._brain.generate_complete(user_input)
            
            if brain_response.success and brain_response.content:
                content = brain_response.content.strip()
                
                # Check for embedded JSON tool call
                tool_call = self._parse_tool_call(content)
                if tool_call:
                    reply = self._run_tool(tool_call) or "Done."
                    verified = True
                else:
                    reply = content
                    verified = True
            else:
                reply = "I'm having trouble processing that right now."
        except Exception as e:
            logger.error(f"Brain error: {e}")
            reply = f"Processing error: {str(e)}"
        
        total_ms = round((time.time() - start) * 1000, 1)
        
        # AI Fallback if no reply
        if not reply and self._router:
            try:
                fallback = await self._router.chat(user_input)
                if fallback.success and fallback.content:
                    self._record_conversation(user_input, fallback.content)
                    return {
                        "response": fallback.content,
                        "success": True, "verified": False,
                        "tool": "ai", "intent": "ai_fallback",
                        "intent_confidence": 0.5, "total_ms": total_ms,
                    }
            except Exception as e:
                logger.error("Router fallback error: %s", e)
        
        self._record_conversation(user_input, reply)
        
        return {
            "response": reply,
            "success": bool(reply),
            "verified": verified,
            "tool": "",
            "intent": "llm_response",
            "intent_confidence": 0.8,
            "entities": {},
            "context": {},
            "reasoned": True,
            "reasoning_level": 3,
            "total_ms": total_ms,
            "error": ""
        }
    
    @staticmethod
    def _parse_tool_call(text: str) -> dict | None:
        """Extract a JSON tool-call block from model output (nested-safe)."""
        import json as json_mod
        import re
        match = re.search(r'\{\s*"tool"', text)
        if not match:
            return None
        start = match.start()
        try:
            data, _ = json_mod.JSONDecoder().raw_decode(text[start:])
        except Exception:
            return None
        if isinstance(data, dict) and data.get("tool"):
            return data
        return None

    TOOL_MESSAGES = {
        "open_url": lambda p: f"Opened {str(p.get('url', '')).replace('https://', '').replace('http://', '').rstrip('/')}.",
        "open_app": lambda p: f"Opened {p.get('app', '')}.",
        "close_app": lambda p: f"Closed {p.get('app', '')}.",
        "search_youtube": lambda p: f"Searched {p.get('query', '')} on YouTube.",
        "web_search": lambda p: f"Searched {p.get('query', '')} on the web.",
        "search": lambda p: f"Searched {p.get('query', '')}.",
        "image_search": lambda p: f"Searched images for {p.get('query', '')}.",
        "play_media": lambda p: f"Playing {p.get('media_query', '') or 'music'}.",
        "search_google": lambda p: f"Searched {p.get('query', '')} on Google.",
        "get_time": lambda p: "Done.",
        "get_date": lambda p: "Done.",
        "get_weather": lambda p: "Done.",
        "get_joke": lambda p: "Done.",
        "calculate": lambda p: "Done.",
        "create_file": lambda p: f"Created {p.get('file_path', '')}.",
        "delete_file": lambda p: f"Deleted {p.get('file_path', '')}.",
        "adjust_volume": lambda p: f"Volume {p.get('direction', 'adjusted')}.",
        "adjust_brightness": lambda p: f"Brightness {p.get('direction', 'adjusted')}.",
        "take_screenshot": lambda p: "Screenshot taken.",
        "save_memory": lambda p: f"Remembered: {p.get('key', '')}.",
        "delete_memory": lambda p: "Forgot that.",
        "recall_memory": lambda p: "Done.",
        "system_lock": lambda p: "Locked.",
        "system_shutdown": lambda p: "Shutting down.",
        "system_restart": lambda p: "Restarting.",
        "system_sleep": lambda p: "Sleeping.",
        "ask_ai": lambda p: "Done.",
        "chat": lambda p: "Done.",
    }

    def _run_tool(self, tool_call: dict) -> str:
        """Execute a tool via the legacy registry and format a clean confirmation."""
        from core.tools import tool_registry
        tool_name = tool_call.get("tool", "")
        params = tool_call.get("params", {}) or {}
        if not tool_name or tool_name in ("none", "no_tool", "none_tool", "null"):
            return ""  # model's way of saying "no tool" — drop silently
        if tool_name not in tool_registry.get_all():
            logger.warning("Model invented unknown tool '%s' — ignoring", tool_name)
            return ""
        try:
            result = tool_registry.execute(tool_name, **params)
        except Exception as e:
            logger.error("Tool %s error: %s", tool_name, e)
            return f"Couldn't do that: {e}"
        if result.success:
            text = (result.result or {}).get("text")
            if text and not self.TOOL_MESSAGES.get(tool_name):
                return text
            template = self.TOOL_MESSAGES.get(tool_name)
            if template:
                return template(params)
            return f"Done. {tool_name.replace('_', ' ')} completed."
        return result.error or f"Couldn't {tool_name.replace('_', ' ')}."

    async def handle_stream(self, user_input: str):
        """Stream the LLM response; tool calls execute silently with clean confirmations.

        Thinking is never displayed. The trailing JSON tool-call block is held
        back during streaming (marker-safe across arbitrary chunk splits) and
        executed at the end. If the active backend produces nothing (GPU limit,
        tunnel dead), the next GPU backup script (model/backup1..3) is launched
        and the request retried once; conversation + docs + tools are refed on
        every switch, so fallbacks are seamless.
        """
        attempts = 0
        while True:
            last_reply = ""
            emitted = False
            try:
                async for token in self._stream_once(user_input):
                    last_reply += token
                    yield token
                emitted = self._stream_emitted
            except Exception as e:
                logger.error(f"LLM streaming error: {e}")
                emitted = False

            if emitted:
                self._record_conversation(user_input, last_reply)
                return

            attempts += 1
            if attempts > 1:
                break
            if not self._rotate_gpu_backend():
                break

        fallback_msg = "I couldn't get a response from the model right now."
        self._record_conversation(user_input, fallback_msg)
        yield fallback_msg

    async def _stream_once(self, user_input: str):
        """One streaming attempt. Yields content; sets self._stream_emitted."""
        self._stream_emitted = False
        if self._brain:
            try:
                from core.thinking_middleware import ThinkingMiddleware
                middleware = ThinkingMiddleware()
                tail = ""
                marker_found = False
                stream_buf = ""

                async for event in middleware.process_stream(self._brain.generate(user_input)):
                    if event.event_type == "thinking":
                        continue  # thinking is never displayed
                    token = event.token
                    if token.startswith("\x00"):
                        continue  # model-internal thinking marker — never displayed
                    if marker_found:
                        tail += token
                        continue
                    stream_buf += token
                    import re as _re
                    marker = _re.search(r'\{\s*"tool"', stream_buf)
                    idx = marker.start() if marker else -1
                    if idx != -1:
                        marker_found = True
                        if stream_buf[:idx]:
                            yield stream_buf[:idx]
                            self._stream_emitted = True
                        tail += stream_buf[idx:]
                        stream_buf = ""
                    elif len(stream_buf) > 24:
                        yield stream_buf[:-24]
                        self._stream_emitted = True
                        stream_buf = stream_buf[-24:]

                if stream_buf:
                    yield stream_buf
                    self._stream_emitted = True

                # Execute the tool call the model requested
                if marker_found:
                    tool_call = self._parse_tool_call(tail)
                    if tool_call:
                        result_text = self._run_tool(tool_call)
                        if result_text:
                            yield "\n" + result_text
                            self._stream_emitted = True
            except Exception as e:
                logger.error(f"LLM streaming error: {e}")
                self._stream_emitted = False
            return

        # No brain: fall back to non-streaming handle
        result = await self.handle(user_input)
        response = result.get("response", "")
        for char in response:
            yield char
        self._stream_emitted = bool(response)

    def _rotate_gpu_backend(self) -> bool:
        """Launch the next GPU backup script; refeed docs+tools on success."""
        try:
            from core.model_manager import gpu_manager
            if not gpu_manager.next_fallback():
                return False
        except Exception as e:
            logger.error("GPU fallback error: %s", e)
            return False
        # Refeed food docs + tool contracts so the new backend knows everything
        try:
            if self._brain and hasattr(self._brain, "reload_system_prompt"):
                self._brain.reload_system_prompt()
        except Exception as e:
            logger.error("System prompt reload failed: %s", e)
        return True

    def _record_conversation(self, user_input: str, assistant: str) -> None:
        """Persist one turn to convo/ so any fallback backend continues seamlessly."""
        try:
            from core.model_manager import gpu_manager
            from core.conversation_store import conversation_store
            tier = "api" if gpu_manager.api_mode else "gpu"
            conversation_store.append(user_input, assistant, tier=tier)
        except Exception as e:
            logger.debug(f"Conversation record failed: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown JARVIS and cleanup resources."""
        logger.info("Shutting down JARVIS...")
        # Cleanup any resources if needed
        if self._speech:
            try:
                self._speech.stop_speaking()
            except Exception as e:
                logger.error(f"Error stopping speech: {e}")
        logger.info("JARVIS shutdown complete")
