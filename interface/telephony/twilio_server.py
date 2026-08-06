"""Twilio Voice webhook server — FastAPI application.

Endpoints:
  POST /voice          — Incoming call handler (returns TwiML)
  POST /voice/events   — Twilio status events
  POST /voice/status   — Call status updates
  WS   /voice/stream   — Twilio Media Stream WebSocket
  GET  /voice/health   — Health check
  WS   /ws/phone       — Web UI phone panel WebSocket
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import traceback
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
import uvicorn

from interface.telephony.config import telephony_config
from interface.telephony.call_manager import call_manager
from interface.telephony.session import AudioState
from interface.telephony.streaming import TwilioStreamHandler

logger = logging.getLogger("jarvis.telephony")

# ── Singleton JARVIS instance ───────────────────────────────────────
_jarvis_instance: Any = None
_jarvis_lock = asyncio.Lock()


async def _get_jarvis() -> Any:
    """Get or create the singleton JARVIS instance."""
    global _jarvis_instance
    async with _jarvis_lock:
        if _jarvis_instance is None:
            try:
                from app import JARVIS
                _jarvis_instance = JARVIS()
                logger.info("JARVIS instance created, booting...")
                await _jarvis_instance.boot()
                logger.info("JARVIS singleton booted successfully")
            except ImportError as e:
                logger.error("Failed to import JARVIS: %s", e, exc_info=True)
                raise RuntimeError(f"JARVIS import failed: {e}")
            except Exception as e:
                logger.error("Failed to boot JARVIS: %s", e, exc_info=True)
                # Don't raise - return a fallback handler instead
                _jarvis_instance = _FallbackJarvis()
                logger.warning("Using fallback JARVIS handler due to boot failure")
        return _jarvis_instance


class _FallbackJarvis:
    """Fallback handler when JARVIS fails to boot."""
    
    async def handle(self, text: str) -> dict:
        """Provide simple responses when JARVIS is unavailable."""
        logger.warning("Using fallback response for: %s", text[:50])
        return {
            "response": "I'm having trouble connecting to my brain right now. Please try again.",
            "tool": "",
            "result": {},
            "verified": False
        }


# ── WebSocket subscribers for Web UI ─────────────────────────────────
_ws_subscribers: set = set()


def create_voice_app() -> FastAPI:
    """Create and configure the Twilio Voice FastAPI application."""
    app = FastAPI(title="JARVIS Telephony", version="1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global exception handler — never return 500 ────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> PlainTextResponse:
        logger.error("Unhandled exception on %s: %s\n%s", request.url.path, exc, traceback.format_exc())
        # For POST /voice, return valid TwiML error message
        if request.url.path == "/voice":
            twiml = _build_twiml_with_stream(
                greeting="Sorry, I'm having a technical issue. Please try again later.",
                stream_url=telephony_config.voice_stream_url,
                call_sid="error",
            )
            return PlainTextResponse(content=twiml, media_type="application/xml", status_code=200)
        return PlainTextResponse(content="Internal Server Error", status_code=500)

    # ── Request validation middleware ───────────────────────────────
    @app.middleware("http")
    async def validate_twilio_request(request: Request, call_next):
        """Validate that Twilio requests are properly formatted."""
        if request.url.path in ("/voice", "/voice/events", "/voice/status"):
            # Log request details for debugging
            logger.debug("Twilio request: %s %s from %s", request.method, request.url.path, request.client.host if request.client else "unknown")
            
            # Check for required Twilio headers
            user_agent = request.headers.get("user-agent", "")
            if "Twilio" not in user_agent:
                logger.warning("Request from non-Twilio user-agent: %s", user_agent[:50])
            
            # Ensure request has content type for POST requests
            if request.method == "POST" and request.url.path == "/voice":
                content_type = request.headers.get("content-type", "")
                if not content_type:
                    logger.warning("POST request without content-type header")
        
        response = await call_next(request)
        return response

    # ── POST /voice — Incoming call webhook ─────────────────────────
    @app.post("/voice")
    async def voice_webhook(request: Request) -> PlainTextResponse:
        """Handle incoming Twilio call. Returns TwiML greeting."""
        call_sid = "unknown"
        try:
            # Log incoming request details
            logger.info("📞 Incoming request to /voice")
            
            form = await request.form()
            call_sid = form.get("CallSid", "unknown")
            caller = form.get("From", "unknown")
            called = form.get("To", telephony_config.phone_number)

            logger.info("📞 Incoming Call SID: %s Caller: %s Called: %s", call_sid, caller, called)

            # Validate configuration
            if not telephony_config.is_configured:
                logger.error("Twilio not configured properly - missing credentials")
                twiml = _build_twiml_with_stream(
                    greeting="Service is not configured. Please check the server configuration.",
                    stream_url=telephony_config.voice_stream_url,
                    call_sid=call_sid,
                )
                return PlainTextResponse(content=twiml, media_type="application/xml", status_code=200)

            # Create session
            session = call_manager.create_session(call_sid, caller)
            logger.info("📞 Session created for call %s", call_sid)

            # Get greeting from JARVIS with time-based greeting
            import datetime
            hour = datetime.datetime.now().hour
            if 5 <= hour < 12:
                time_greeting = "Good morning"
            elif 12 <= hour < 17:
                time_greeting = "Good afternoon"
            elif 17 <= hour < 21:
                time_greeting = "Good evening"
            else:
                time_greeting = "Good night"
            
            greeting = f"{time_greeting} Sir! I am Jarvis. How can I help you?"
            
            try:
                jarvis = await _get_jarvis()
                result = await asyncio.wait_for(
                    jarvis.handle("hello"),
                    timeout=30.0,
                )
                jarvis_greeting = result.get("response", "")
                if jarvis_greeting and "jarvis" not in jarvis_greeting.lower():
                    greeting = f"{time_greeting} Sir! {jarvis_greeting}"
                logger.info("Greeting: %s", greeting[:80])
            except asyncio.TimeoutError:
                logger.warning("Greeting timed out, using default greeting")
            except Exception as e:
                logger.warning("Greeting failed: %s", e)

            # Log the greeting
            log = call_manager.get_logger(call_sid)
            if log:
                log.log_assistant(greeting)

            # TwiML: speak greeting then connect Media Stream
            twiml = _build_twiml_with_stream(
                greeting=greeting,
                stream_url=telephony_config.voice_stream_url,
                call_sid=call_sid,
            )
            logger.info("📞 Returning TwiML for call %s (length: %d)", call_sid, len(twiml))
            logger.debug("TwiML content: %s", twiml[:300])
            
            return PlainTextResponse(content=twiml, media_type="application/xml", status_code=200)

        except Exception as e:
            logger.error("Voice webhook error: %s", e, exc_info=True)
            twiml = _build_twiml_with_stream(
                greeting="Sorry, I encountered an error. Please try again.",
                stream_url=telephony_config.voice_stream_url,
                call_sid=call_sid,
            )
            return PlainTextResponse(content=twiml, media_type="application/xml", status_code=200)

    # ── POST /voice/events — Twilio status events ──────────────────
    @app.post("/voice/events")
    async def voice_events(request: Request) -> PlainTextResponse:
        """Handle Twilio call status events."""
        try:
            form = await request.form()
            status = form.get("Status", "unknown")
            call_sid = form.get("CallSid", "unknown")
            call_status = form.get("CallStatus", "unknown")
            logger.info("📋 Call Event: %s → Status: %s, CallStatus: %s", call_sid, status, call_status)

            log = call_manager.get_logger(call_sid)
            if log:
                log.log_event(f"Status: {status}, CallStatus: {call_status}")

            if status in ("completed", "failed", "busy", "no-answer", "canceled") or call_status in ("completed", "failed", "busy", "no-answer", "canceled"):
                call_manager.end_session(call_sid)
                logger.info("📞 Call ended: %s (final status: %s)", call_sid, call_status)
        except Exception as e:
            logger.error("Events error: %s", e, exc_info=True)

        return PlainTextResponse(content="OK")

    # ── POST /voice/status — Call status callback ──────────────────
    @app.post("/voice/status")
    async def voice_status(request: Request) -> PlainTextResponse:
        """Handle Twilio call status callback."""
        try:
            form = await request.form()
            call_sid = form.get("CallSid", "unknown")
            status = form.get("CallStatus", "unknown")
            duration = form.get("CallDuration", "0")
            logger.info("📞 Call Status: %s → %s (duration: %ss)", call_sid, status, duration)

            if status in ("completed", "failed", "busy", "no-answer", "canceled"):
                call_manager.end_session(call_sid)
        except Exception as e:
            logger.error("Status error: %s", e)

        return PlainTextResponse(content="OK")

    # ── WS /voice/stream — Twilio Media Stream WebSocket ───────────
    @app.websocket("/voice/stream")
    async def voice_stream(websocket: WebSocket) -> None:
        """Handle Twilio Media Stream WebSocket connection."""
        await websocket.accept()
        logger.info("📞 WebSocket connection accepted")

        session = None
        handler = None
        call_sid = "unknown"

        try:
            # Wait for start event to get call SID
            logger.debug("Waiting for start event...")
            start_msg = await asyncio.wait_for(websocket.receive_text(), timeout=15.0)
            logger.debug("Received message: %s", start_msg[:100])
            start_data = json.loads(start_msg)

            if start_data.get("event") == "connected":
                logger.debug("Stream connected event received")
                start_msg = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
                start_data = json.loads(start_msg)

            if start_data.get("event") == "start":
                call_sid = start_data.get("start", {}).get("callSid", "unknown")
                stream_sid = start_data.get("start", {}).get("streamSid", "unknown")
                logger.info("📞 Stream start received - Call SID: %s, Stream SID: %s", call_sid, stream_sid)
                
                session = call_manager.get_session(call_sid)

                if not session:
                    caller = start_data.get("start", {}).get("customParameters", {}).get("caller", "unknown")
                    session = call_manager.create_session(call_sid, caller)
                    logger.info("📞 Created new session for call %s", call_sid)

                session.stream_sid = stream_sid
                session.websocket = websocket
                handler = TwilioStreamHandler(session, websocket)

                logger.info("📞 Media Stream connected: %s (stream: %s)", call_sid, stream_sid)

                await handler.start()
                logger.info("📞 Handler started, beginning conversation loop")
                await _conversation_loop(session, handler)
            else:
                logger.warning("Unexpected event: %s", start_data.get("event"))

        except asyncio.TimeoutError:
            logger.error("Stream start timeout for call %s after waiting 15s", call_sid)
        except WebSocketDisconnect as e:
            logger.info("WebSocket disconnected for call %s (code: %s)", call_sid, e.code)
        except json.JSONDecodeError as e:
            logger.error("JSON decode error for call %s: %s, message was: %s", call_sid, e, start_msg[:200] if 'start_msg' in locals() else "N/A")
        except Exception as e:
            logger.error("Stream error for call %s: %s", call_sid, e, exc_info=True)
        finally:
            logger.info("📞 Cleaning up stream for call %s", call_sid)
            if handler:
                try:
                    await handler.stop()
                except Exception as e:
                    logger.error("Error stopping handler for call %s: %s", call_sid, e)
            if session:
                call_manager.end_session(session.call_sid)
                logger.info("📞 Stream ended for call %s", session.call_sid)

    # ── WS /ws/phone — Web UI phone panel WebSocket ────────────────
    @app.websocket("/ws/phone")
    async def phone_panel_ws(websocket: WebSocket) -> None:
        """WebSocket for the Web UI phone panel to receive call state updates."""
        await websocket.accept()
        _ws_subscribers.add(websocket)
        try:
            await websocket.send_json({
                "type": "active_calls",
                "data": [s.to_dict() for s in call_manager.active_sessions],
            })
            while True:
                data = await websocket.receive_text()
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            _ws_subscribers.discard(websocket)

    # ── GET /voice/health — Health check ────────────────────────────
    @app.get("/voice/health")
    async def voice_health() -> dict[str, Any]:
        return {
            "status": "ok",
            "active_calls": call_manager.active_count,
            "configured": telephony_config.is_configured,
            "provider": telephony_config.stt_provider,
            "webhook_url": telephony_config.webhook_url,
        }

    return app


# ── Conversation Loop ────────────────────────────────────────────────

async def _conversation_loop(session: Any, handler: TwilioStreamHandler) -> None:
    """Main conversational loop for a phone call."""
    from interface.telephony.speech import get_recognizer

    recognizer = get_recognizer()
    silence_start = time.time()
    turn_count = 0

    logger.info("📞 Conversation started for call %s with STT provider: %s", session.call_sid, telephony_config.stt_provider)

    while handler._running:
        try:
            # Check call duration limit
            if session.duration_sec > telephony_config.max_call_duration_sec:
                logger.warning("Call %s exceeded max duration (%ds)", session.call_sid, telephony_config.max_call_duration_sec)
                break

            # Check silence timeout
            if session.audio_state == AudioState.IDLE:
                elapsed = time.time() - silence_start
                if elapsed > telephony_config.max_silence_sec:
                    logger.info("Silence timeout for call %s (%.1fs)", session.call_sid, elapsed)
                    break

            # Wait for audio chunks in the buffer
            await asyncio.sleep(0.05)

            # Check if we have speech to transcribe
            if handler._audio_buffer.is_silence_detected and handler._audio_buffer.has_speech:
                audio_data = handler._audio_buffer.get_audio()
                if len(audio_data) < 100:
                    continue

                session.set_audio_state(AudioState.THINKING)
                turn_count += 1

                # Transcribe
                stt_start = time.time()
                try:
                    result = await recognizer.transcribe(audio_data)
                    stt_ms = (time.time() - stt_start) * 1000
                    logger.debug("STT result: text='%s', provider=%s, confidence=%.2f", result.text[:50], result.provider, result.confidence)
                except Exception as e:
                    logger.error("STT transcription error: %s", e, exc_info=True)
                    result = type('STTResult', (), {'text': '', 'provider': 'error', 'confidence': 0.0, 'latency_ms': 0.0})()

                if not result.text or not result.text.strip():
                    logger.warning("Empty STT result, returning to listening state")
                    session.set_audio_state(AudioState.LISTENING)
                    continue

                user_text = result.text.strip()
                logger.info("🎤 USER [Turn %d]: %s", turn_count, user_text)

                log = call_manager.get_logger(session.call_sid)
                if log:
                    log.log_user(user_text)

                turn = session.start_turn(user_text)

                await _process_user_input(session, handler, turn, log, user_text, stt_ms)

                silence_start = time.time()
                session.set_audio_state(AudioState.LISTENING)
                await call_manager.broadcast_state(session.call_sid)

        except asyncio.CancelledError:
            logger.info("Conversation loop cancelled for call %s", session.call_sid)
            break
        except Exception as e:
            logger.error("Conversation loop error for call %s: %s", session.call_sid, e, exc_info=True)
            await asyncio.sleep(0.5)

    logger.info("📞 Conversation ended for call %s after %d turns", session.call_sid, turn_count)


async def _process_user_input(
    session: Any,
    handler: TwilioStreamHandler,
    turn: Any,
    log: Any,
    user_text: str,
    stt_ms: float,
) -> None:
    """Process user input through JARVIS brain and respond."""
    from interface.telephony.logger import LatencyRecord

    llm_ms = 0.0
    execution_ms = 0.0
    tts_ms = 0.0
    assistant_text = ""
    tool_name = ""
    tool_result = ""
    tool_success = False

    try:
        # ── JARVIS Brain Processing ────────────────────────────────
        session.set_audio_state(AudioState.THINKING)
        llm_start = time.time()

        jarvis = await _get_jarvis()
        result = await asyncio.wait_for(
            jarvis.handle(user_text),
            timeout=60.0,
        )

        llm_ms = (time.time() - llm_start) * 1000
        assistant_text = result.get("response", "I'm sorry, I didn't catch that.")
        tool_name = result.get("tool", "")
        tool_result_json = result.get("result", {})
        tool_success = result.get("verified", False)

        if tool_result_json and isinstance(tool_result_json, dict):
            tool_result = str(tool_result_json.get("output", tool_result_json))

        if tool_name and log:
            log.log_tool(tool_name, tool_result, tool_success)

        # ── TTS Response ───────────────────────────────────────────
        session.set_audio_state(AudioState.SPEAKING)
        tts_start = time.time()
        await handler.clear_speaker()
        tts_ms = await handler.synthesize_and_stream(assistant_text)
        tts_ms = (time.time() - tts_start) * 1000

        # ── Log Assistant Turn ─────────────────────────────────────
        latency = LatencyRecord(
            stt_ms=stt_ms,
            llm_ms=llm_ms,
            execution_ms=execution_ms,
            tts_ms=tts_ms,
        )
        if log:
            log.log_assistant(assistant_text, tool_name, tool_result, latency)

        # ── Finish Turn ────────────────────────────────────────────
        turn = session.finish_turn(
            assistant_text,
            tool_name=tool_name,
            tool_result=tool_result,
            tool_success=tool_success,
        )
        turn.latency_stt_ms = stt_ms
        turn.latency_llm_ms = llm_ms
        turn.latency_execution_ms = execution_ms
        turn.latency_tts_ms = tts_ms

        # ── Memory Integration ─────────────────────────────────────
        await _save_to_memory(session, user_text, assistant_text)

        logger.info(
            "⚡ LATENCY STT:%.0f LLM:%.0f TTS:%.0f Total:%.0f ms",
            stt_ms, llm_ms, tts_ms, stt_ms + llm_ms + tts_ms,
        )

    except asyncio.TimeoutError:
        logger.warning("JARVIS response timeout for call %s", session.call_sid)
        assistant_text = "I took too long to respond. Could you try again?"
        await handler.synthesize_and_stream(assistant_text)
        session.finish_turn(assistant_text)
    except Exception as e:
        logger.error("Brain processing error for call %s: %s", session.call_sid, e, exc_info=True)
        assistant_text = "Sorry, I encountered an error. Please try again."
        try:
            await handler.synthesize_and_stream(assistant_text)
        except Exception as tts_error:
            logger.error("TTS failed during error recovery: %s", tts_error)
        session.finish_turn(assistant_text)


async def _save_to_memory(session: Any, user_text: str, assistant_text: str) -> None:
    """Save phone conversation to the memory system."""
    try:
        from core.memory import unified_memory
        unified_memory.set_session_cache(
            f"phone_{session.call_sid}_{len(session.turns)}",
            {"user": user_text, "assistant": assistant_text},
        )
    except Exception as e:
        logger.debug("Memory save failed: %s", e)


# ── TwiML Builder ────────────────────────────────────────────────────

def _build_twiml_with_stream(greeting: str, stream_url: str, call_sid: str) -> str:
    """Build TwiML that speaks greeting then connects a Media Stream."""
    # Escape XML special characters in greeting
    safe_greeting = greeting.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")
    
    # Validate stream URL
    if not stream_url or not stream_url.startswith(("ws://", "wss://", "http://", "https://")):
        logger.error("Invalid stream URL: %s", stream_url)
        safe_greeting = "Service configuration error. Please contact support."
        stream_url = "wss://placeholder.invalid"
    
    # Build TwiML with proper structure
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Matthew" language="en-US">{safe_greeting}</Say>
    <Connect>
        <Stream url="{stream_url}">
            <Parameter name="callSid" value="{call_sid}" />
        </Stream>
    </Connect>
</Response>"""
    
    logger.debug("Generated TwiML for call %s: %s", call_sid, twiml[:200])
    return twiml


# ── Entry Point ──────────────────────────────────────────────────────

_app_instance: FastAPI | None = None


def get_voice_app() -> FastAPI:
    global _app_instance
    if _app_instance is None:
        _app_instance = create_voice_app()
    return _app_instance


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    app = create_voice_app()
    print("  JARVIS Telephony Server")
    print(f"  Voice Webhook: {telephony_config.voice_webhook_url}")
    print(f"  Media Stream:  {telephony_config.voice_stream_url}")
    print(f"  Health:        http://localhost:{telephony_config.port}/voice/health")
    print(f"  Phone Panel:   ws://localhost:{telephony_config.port}/ws/phone")
    print()
    uvicorn.run(app, host=telephony_config.host, port=telephony_config.port)
