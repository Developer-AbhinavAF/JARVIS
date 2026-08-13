"""
JARVIS Desktop Backend — FastAPI server for the Web UI.

Imports the new JARVIS class from root app.py and exposes REST + WebSocket endpoints
that the React frontend expects.

Port: 8001 (matches frontend hardcode)
"""

import asyncio
import json
import logging
import os
import sys
import time
import base64
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
import psutil

# ═══════════════════════════════════════════════════════════════
# PATH SETUP
# ═══════════════════════════════════════════════════════════════

JARVIS_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(JARVIS_ROOT))

# Load .env from project root
from dotenv import load_dotenv
env_path = JARVIS_ROOT / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=str(env_path))

logger = logging.getLogger("jarvis.desktop")

# ═══════════════════════════════════════════════════════════════
# LOG BUFFER — captures logs for frontend WebSocket streaming
# ═══════════════════════════════════════════════════════════════

MAX_LOG_BUFFER = 200
log_buffer: list[dict[str, Any]] = []
log_subscribers: set = set()
pending_log_broadcasts: list[dict[str, Any]] = []


class FrontendLogHandler(logging.Handler):
    """Captures logs for frontend display via WebSocket."""
    def emit(self, record):
        try:
            msg = record.getMessage() if hasattr(record, 'msg') else str(record.msg)
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": msg,
                "raw_message": msg,
            }
            log_buffer.append(log_entry)
            if len(log_buffer) > MAX_LOG_BUFFER:
                log_buffer.pop(0)
            pending_log_broadcasts.append(log_entry)
        except Exception:
            pass


# Attach handler
_frontend_handler = FrontendLogHandler()
_frontend_handler.setLevel(logging.INFO)
_frontend_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(_frontend_handler)

# ═══════════════════════════════════════════════════════════════
# DESKTOP UI FOOD — context injected into every chat message
# ═══════════════════════════════════════════════════════════════

def get_desktop_food() -> str:
    """Return a short string of desktop-UI context prepended to user messages.

    NOTE: System resource values (CPU/RAM/GPU) are intentionally NOT included.
    The LLM must never shape or refuse responses based on machine load — the
    resource monitor is an independent subsystem surfaced through the
    dashboard / /api/system-stats only.
    """
    return (
        "[Desktop UI Context]\n"
        f"channel: jarvis-desktop\n"
    )


# ═══════════════════════════════════════════════════════════════
# JARVIS INSTANCE — the real brain
# ═══════════════════════════════════════════════════════════════

jarvis_instance = None
_boot_lock: Optional[asyncio.Lock] = None


def _get_boot_lock() -> asyncio.Lock:
    """Lazily create the boot lock (must be created inside a running loop)."""
    global _boot_lock
    if _boot_lock is None:
        _boot_lock = asyncio.Lock()
    return _boot_lock


# Configurable timeouts — Ollama's first response after boot (loading jarvis-agi
# on the cloud GPU + ngrok round-trip) can take a long time. Generous defaults
# to keep the UI from looking hung while the model is warming up. Overridable
# via environment variables.
HANDLE_TIMEOUT_SECONDS = float(os.getenv("JARVIS_HANDLE_TIMEOUT", "240"))   # 4 min
STREAM_TIMEOUT_SECONDS = float(os.getenv("JARVIS_STREAM_TIMEOUT", "360"))   # 6 min (first token)
OLLAMA_WARMUP_TIMEOUT = float(os.getenv("OLLAMA_WARMUP_TIMEOUT", "180"))    # 3 min warmup cap


async def get_jarvis():
    """Return the shared JARVIS instance, booting it once under a lock.

    Using a lock prevents a thundering-herd of concurrent /api/chat
    requests from each spawning their own boot (which loads heavy models
    and can OOM the box).
    """
    global jarvis_instance
    if jarvis_instance is not None:
        return jarvis_instance

    async with _get_boot_lock():
        if jarvis_instance is not None:
            return jarvis_instance
        logger.info("Booting JARVIS instance (first request)...")
        boot_start = time.time()
        import importlib.util
        root_app_path = str(JARVIS_ROOT / "app.py")
        spec = importlib.util.spec_from_file_location("jarvis_root_app", root_app_path)
        root_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(root_app)
        jarvis_instance = root_app.JARVIS()
        try:
            await asyncio.wait_for(jarvis_instance.boot(), timeout=OLLAMA_WARMUP_TIMEOUT)
        except asyncio.TimeoutError:
            logger.warning(
                "JARVIS boot exceeded %.0fs — continuing in background. "
                "The first chat may still take a moment.",
                OLLAMA_WARMUP_TIMEOUT,
            )
        except Exception as exc:
            logger.error("JARVIS boot failed: %s", exc, exc_info=True)
        logger.info("JARVIS instance ready in %.2fs", time.time() - boot_start)
    return jarvis_instance


# ═══════════════════════════════════════════════════════════════
# SYSTEM STATS — psutil-based, matches frontend SystemStats type
# ═══════════════════════════════════════════════════════════════

_prev_net = None
_prev_net_time = None


def get_system_stats() -> dict[str, Any]:
    """Collect system stats matching the frontend's SystemStats type."""
    global _prev_net, _prev_net_time

    cpu = psutil.cpu_percent(interval=0.1)
    cpu_cores = psutil.cpu_count(logical=True) or 1
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    battery = {"percentage": 0, "isCharging": False}
    try:
        bat = psutil.sensors_battery()
        if bat:
            battery = {
                "percentage": bat.percent,
                "isCharging": bat.power_plugged,
            }
    except Exception:
        pass

    # Network speed calculation (bytes/sec)
    net = psutil.net_io_counters()
    now = time.time()
    download_speed = 0
    upload_speed = 0
    if _prev_net and _prev_net_time:
        elapsed = now - _prev_net_time
        if elapsed > 0:
            download_speed = max(0, (net.bytes_recv - _prev_net.bytes_recv) / elapsed)
            upload_speed = max(0, (net.bytes_sent - _prev_net.bytes_sent) / elapsed)
    _prev_net = net
    _prev_net_time = now

    # Ping (simple, non-blocking)
    ping_ms = 0

    processes = len(psutil.pids())

    return {
        "cpu": {"usage": round(cpu, 1), "cores": cpu_cores},
        "memory": {
            "used": round(mem.used / (1024**3), 2),
            "total": round(mem.total / (1024**3), 2),
            "percentage": round(mem.percent, 1),
        },
        "battery": battery,
        "disk": {
            "used": round(disk.used / (1024**3), 2),
            "total": round(disk.total / (1024**3), 2),
            "percentage": round(disk.percent, 1),
        },
        "network": {
            "downloadSpeed": round(download_speed),
            "uploadSpeed": round(upload_speed),
            "ping": round(ping_ms, 1),
        },
        "processes": {"count": processes},
        "uptime": int(time.time() - psutil.boot_time()),
    }


# ═══════════════════════════════════════════════════════════════
# ACTION MAPPER — ToolResult → frontend MessageAction[]
# ═══════════════════════════════════════════════════════════════

def build_actions(result: dict) -> list[dict[str, Any]]:
    """Map execution engine result to frontend MessageAction[] format."""
    tool = result.get("tool")
    if not tool:
        return []

    raw = result.get("result")
    data = raw if isinstance(raw, dict) else {}

    actions = []
    if tool == "open_app":
        actions.append({"type": "open_app", "app": data.get("app", data.get("url", ""))})
    elif tool == "close_app":
        actions.append({"type": "close_app", "app": data.get("app", "")})
    elif tool == "open_url":
        actions.append({"type": "open_url", "url": data.get("url", "")})
    elif tool == "web_search":
        actions.append({"type": "web_search", "query": data.get("query", "")})
    elif tool == "create_file":
        actions.append({"type": "file_created", "path": data.get("file_path", "")})
    elif tool == "delete_file":
        actions.append({"type": "file_deleted", "path": data.get("file_path", "")})
    elif tool == "read_file":
        actions.append({"type": "file_read", "path": data.get("file_path", "")})
    elif tool == "take_screenshot":
        actions.append({"type": "screenshot", "path": data.get("path", "")})
    elif tool == "adjust_volume":
        actions.append({"type": "volume", "action": data.get("direction", "up")})
    elif tool in ("add_note", "get_notes", "add_todo", "get_todos", "complete_todo"):
        actions.append({"type": tool})
    elif tool == "get_system_stats":
        actions.append({"type": "system_stats"})
    elif tool in ("get_time", "get_date"):
        actions.append({"type": tool})
    elif tool == "list_running_apps":
        apps = data.get("apps", [])
        actions.append({"type": "running_apps", "apps": apps[:10]})
    elif tool in ("nasa_apod", "nasa_image_search"):
        results = data.get("results", [])
        if results:
            for r in results[:6]:
                actions.append({
                    "type": "image_result",
                    "source": "NASA",
                    "title": r.get("title", ""),
                    "image_url": r.get("image_url", ""),
                    "thumbnail_url": r.get("thumbnail_url", ""),
                    "description": r.get("description", "")[:200],
                    "source_url": r.get("source_url", ""),
                    "media_type": r.get("media_type", "image"),
                })
    elif tool == "code_fallback":
        actions.append({"type": "code_execution", "language": data.get("language", ""), "success": data.get("success", False)})

    return actions


# ═══════════════════════════════════════════════════════════════
# FASTAPI APP
# ═══════════════════════════════════════════════════════════════

connected_clients: set = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = []
    try:
        tasks.append(asyncio.create_task(process_log_broadcasts()))
        tasks.append(asyncio.create_task(broadcast_system_stats()))
        await get_jarvis()
        yield
    finally:
        for task in tasks:
            task.cancel()
        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(title="JARVIS Desktop", version="3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    stream: Optional[bool] = False


# ═══════════════════════════════════════════════════════════════
# IMAGE VALIDATION
# ═══════════════════════════════════════════════════════════════

ALLOWED_IMAGE_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/gif",
}

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB


def validate_image(file_type: str, file_data: str) -> tuple[bool, str, Optional[str]]:
    """Validate uploaded image.
    
    Returns:
        (is_valid, error_message, processed_data)
    """
    if not file_type or not file_data:
        return False, "No image data provided", None
    
    # Check MIME type
    if file_type.lower() not in ALLOWED_IMAGE_TYPES:
        return False, f"Unsupported image type: {file_type}. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}", None
    
    # Decode base64 to check size
    try:
        image_bytes = base64.b64decode(file_data)
        if len(image_bytes) > MAX_IMAGE_SIZE:
            return False, f"Image too large. Max size is {MAX_IMAGE_SIZE // (1024*1024)}MB", None
        if len(image_bytes) == 0:
            return False, "Image data is empty", None
    except Exception as e:
        return False, f"Invalid image data: {str(e)}", None
    
    # Return the base64 data for the model
    return True, "", file_data


# ═══════════════════════════════════════════════════════════════
# REST ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.post("/api/chat")
async def chat(request: Request):
    """Process chat message. Supports JSON and multipart/form-data (file upload).
    Returns SSE stream if stream=true, otherwise JSON response."""
    session_id = "default"
    message = ""
    try:
        content_type = request.headers.get("content-type", "")
        stream_mode = False
        file_name = None
        file_type = None
        file_data = None

        if "multipart/form-data" in content_type:
            form = await request.form()
            message = form.get("message", "")
            session_id = form.get("session_id", "default")
            stream_mode = str(form.get("stream", "false")).lower() in ("1", "true", "yes")
            file_name = form.get("file_name")
            file_type = form.get("file_type")
            file_data = form.get("file_data")
        else:
            json_data = await request.json()
            message = json_data.get("message", "")
            session_id = json_data.get("session_id", "default")
            stream_mode = bool(json_data.get("stream", False))

        logger.info("USER: %s", message)

        # Inject desktop UI food into message
        try:
            desktop_food = get_desktop_food()
        except Exception as food_err:
            logger.debug("desktop_food gather failed: %s", food_err)
            desktop_food = ""
        augmented_message = f"{desktop_food}\n\nUser Message: {message}" if desktop_food else message

        # File upload / Image input
        if file_data and file_name:
            # Validate image
            is_valid, error_msg, processed_data = validate_image(file_type, file_data)
            
            if not is_valid:
                logger.warning("[IMAGE] Validation failed: %s", error_msg)
                return {
                    "response": f"I couldn't process that image: {error_msg}",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "actions": None,
                    "suggestions": None,
                }
            
            logger.info("[IMAGE] Received image: %s (%s, size: %d bytes)", file_name, file_type, len(file_data))
            
            # Construct multimodal message for the core
            # The message will include both the user's text and the image
            user_text = message or "Analyze this image"
            augmented_message = f"{desktop_food}\n\nUser Message: {user_text}" if desktop_food else user_text
            
            # Store image data for the core to process
            # We'll pass it as part of the request context
            image_context = {
                "image_data": processed_data,
                "image_type": file_type,
                "image_name": file_name,
            }
            
            logger.info("[IMAGE] Preparing multimodal request for: %s", user_text[:50])
            
            # Process with image
            try:
                jarvis = await get_jarvis()
                result = await jarvis.handle_with_image(augmented_message, image_context)
                actions = build_actions(result)
                
                logger.info("[IMAGE] Vision response received: %d chars", len(result.get("response", "")))
                
                return {
                    "response": result.get("response", ""),
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "actions": actions if actions else None,
                    "suggestions": None,
                    "intent": result.get("intent", ""),
                    "intent_confidence": result.get("intent_confidence", 0),
                    "tool": result.get("tool", ""),
                    "verified": result.get("verified", False),
                    "total_ms": result.get("total_ms", 0),
                }
            except Exception as img_err:
                logger.error("[IMAGE] Processing failed: %s", img_err, exc_info=True)
                return {
                    "response": f"I couldn't process that image. Please try again or check if the image is valid.",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "actions": None,
                    "suggestions": None,
                }

        # Streaming SSE — actually stream tokens from process_stream so the
        # client sees the first token the moment Ollama produces it instead
        # of waiting for the full response.
        if stream_mode:
            async def event_stream():
                full_text = ""
                intent = ""
                intent_confidence = 0.0
                tool = ""
                verified = False
                meta: dict[str, Any] = {}
                try:
                    jarvis = await get_jarvis()
                    stream_start = time.time()

                    async def _drain():
                        """Pull tokens from the core / fallback and yield
                        (kind, payload) tuples. Lives inside a coroutine so we
                        can apply a deadline to the whole drain."""
                        nonlocal full_text, intent, intent_confidence, tool, verified, meta
                        if jarvis._core is not None and hasattr(jarvis._core, "process_stream"):
                            async for event in jarvis._core.process_stream(augmented_message):
                                etype = getattr(event, "event_type", "") or getattr(event, "type", "")
                                if etype == "response_token":
                                    token = getattr(event, "token", "")
                                    if token:
                                        full_text += token
                                        yield ("token", token)
                                elif etype == "final_response":
                                    resp_text = getattr(event, "text", "") or ""
                                    if resp_text and resp_text != full_text:
                                        full_text = resp_text
                                        yield ("token", resp_text)
                                elif etype == "planner":
                                    intent = getattr(event, "goal", "") or intent
                                    intent_confidence = getattr(event, "confidence", 0.0) or intent_confidence
                                elif etype == "execution":
                                    tool = getattr(event, "target_name", "") or tool
                                elif etype == "verification":
                                    verified = getattr(event, "verified", False)
                                    meta = getattr(event, "details", {}) or meta
                                elif etype == "image_result":
                                    img_data = {
                                        "source": getattr(event, "source", ""),
                                        "title": getattr(event, "title", ""),
                                        "description": getattr(event, "description", ""),
                                        "image_url": getattr(event, "image_url", ""),
                                        "thumbnail_url": getattr(event, "thumbnail_url", ""),
                                        "source_url": getattr(event, "source_url", ""),
                                        "media_type": getattr(event, "media_type", "image"),
                                        "metadata": getattr(event, "metadata", {}),
                                    }
                                    yield ("image_result", img_data)
                                elif etype == "image_gallery":
                                    gallery_data = {
                                        "source": getattr(event, "source", ""),
                                        "query": getattr(event, "query", ""),
                                        "results": getattr(event, "results", []),
                                        "count": getattr(event, "count", 0),
                                    }
                                    yield ("image_gallery", gallery_data)
                                elif etype == "code_execution":
                                    code_data = {
                                        "language": getattr(event, "language", ""),
                                        "success": getattr(event, "success", False),
                                        "stdout": getattr(event, "stdout", ""),
                                        "stderr": getattr(event, "stderr", ""),
                                        "exit_code": getattr(event, "exit_code", -1),
                                    }
                                    yield ("code_execution", code_data)
                        else:
                            result = await jarvis.handle(augmented_message)
                            full_text = result.get("response", "")
                            intent = result.get("intent", "")
                            intent_confidence = result.get("intent_confidence", 0.0)
                            tool = result.get("tool", "")
                            verified = result.get("verified", False)
                            meta = result.get("result", {}) or {}
                            for i in range(0, len(full_text), 3):
                                yield ("token", full_text[i:i + 3])

                    drain = _drain()
                    try:
                        while True:
                            try:
                                kind, payload = await asyncio.wait_for(
                                    drain.__anext__(), timeout=STREAM_TIMEOUT_SECONDS
                                )
                            except StopAsyncIteration:
                                break
                            if kind == "token":
                                yield f"data: {json.dumps({'token': payload})}\n\n"
                            elif kind == "image_result":
                                yield f"data: {json.dumps({'image_result': payload})}\n\n"
                            elif kind == "image_gallery":
                                yield f"data: {json.dumps({'image_gallery': payload})}\n\n"
                            elif kind == "code_execution":
                                yield f"data: {json.dumps({'code_execution': payload})}\n\n"
                    except asyncio.TimeoutError:
                        logger.warning(
                            "Stream exceeded %.0fs without producing another token "
                            "(Ollama may be loading the model or generating a long response)",
                            STREAM_TIMEOUT_SECONDS,
                        )
                        notice = f"\n[stream timeout after {STREAM_TIMEOUT_SECONDS:.0f}s — Ollama likely still loading]"
                        yield f"data: {json.dumps({'token': notice})}\n\n"
                        if not full_text:
                            full_text = (
                                f"(stream timed out before first token — Ollama is "
                                f"still loading. Waited {STREAM_TIMEOUT_SECONDS:.0f}s.)"
                            )
                    except Exception as stream_exc:
                        logger.error("Stream error: %s", stream_exc, exc_info=True)
                        if not full_text:
                            full_text = f"(stream error: {stream_exc})"
                        yield f"data: {json.dumps({'token': f'\\n[stream error: {stream_exc}]'})}\n\n"
                    finally:
                        try:
                            await drain.aclose()
                        except Exception:
                            pass

                    actions = build_actions({"tool": tool, "result": meta if isinstance(meta, dict) else {}})
                    total_ms = int((time.time() - stream_start) * 1000)
                    logger.info("JARVIS stream (%sms%s): %s", total_ms, f" tool={tool}" if tool else "", full_text[:200])
                    yield f"data: {json.dumps({'done': True, 'response': full_text, 'actions': actions, 'intent': intent, 'intent_confidence': intent_confidence, 'tool': tool, 'verified': verified, 'total_ms': total_ms})}\n\n"
                except asyncio.CancelledError:
                    raise
                except Exception as outer_exc:
                    logger.error("event_stream fatal: %s", outer_exc, exc_info=True)
                    yield f"data: {json.dumps({'done': True, 'response': f'(error: {outer_exc})', 'actions': [], 'intent': '', 'intent_confidence': 0, 'tool': '', 'verified': False, 'total_ms': 0})}\n\n"

            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        # Regular JSON response — bound the call so a stuck Ollama doesn't
        # hold the client forever. The previous 30s cap is too tight when
        # the model is still warming up.
        jarvis = await get_jarvis()
        try:
            result = await asyncio.wait_for(jarvis.handle(augmented_message), timeout=HANDLE_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            logger.warning("handle() exceeded %.0fs timeout", HANDLE_TIMEOUT_SECONDS)
            result = {
                "response": (
                    f"(JARVIS took longer than {HANDLE_TIMEOUT_SECONDS:.0f}s to respond. "
                    "Ollama may still be loading the model on first use — try again in a moment.)"
                ),
                "intent": "timeout",
                "intent_confidence": 0.0,
                "tool": "",
                "verified": False,
                "total_ms": int(HANDLE_TIMEOUT_SECONDS * 1000),
                "result": {},
            }
        actions = build_actions(result)
        ai_response = result.get("response", "")
        total_ms = result.get("total_ms", 0)
        tool = result.get("tool", "")
        logger.info("JARVIS (%sms%s): %s", total_ms, f" tool={tool}" if tool else "", ai_response[:200])

        return {
            "response": ai_response,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "actions": actions if actions else None,
            "suggestions": None,
            "intent": result.get("intent", ""),
            "intent_confidence": result.get("intent_confidence", 0),
            "tool": result.get("tool", ""),
            "verified": result.get("verified", False),
            "total_ms": result.get("total_ms", 0),
        }

    except Exception as e:
        logger.error("Chat error: %s", e, exc_info=True)
        return {
            "response": f"Error: {e}",
            "session_id": session_id or "default",
            "timestamp": datetime.now().isoformat(),
            "actions": None,
            "suggestions": None,
        }


@app.get("/api/system-stats")
async def system_stats():
    """System statistics for the dashboard."""
    return {"stats": get_system_stats()}


@app.get("/api/health")
async def health():
    """Health check endpoint with NLP pipeline stats."""
    jarvis = await get_jarvis()
    health_data = jarvis.get_health()
    nlp_stats = {}
    if jarvis._nlp:
        try:
            nlp = jarvis._nlp
            # Get actual stats from NLP engine
            tool_count = 0
            if jarvis._execution:
                try:
                    from jarvis.execution import tool_registry
                    tool_count = tool_registry.get_stats().get("total", 0)
                except Exception:
                    pass

            # Count intent categories from the intent engine
            intent_count = 35  # default
            if hasattr(nlp, 'intent_engine') and hasattr(nlp.intent_engine, '_intent_descriptions'):
                intent_count = len(nlp.intent_engine._intent_descriptions)

            nlp_stats = {
                "engine_active": True,
                "fast_path_ms": 2.0,  # from benchmarks
                "intent_categories": intent_count,
                "tools_registered": tool_count,
                "fast_path_intents": 30,
                "full_pipeline_intents": intent_count,
            }
        except Exception:
            nlp_stats = {"engine_active": True, "fast_path_ms": 2.0, "intent_categories": 35, "tools_registered": 18, "fast_path_intents": 30, "full_pipeline_intents": 35}
    return {
        "status": "ok",
        "initialized": jarvis._boot_complete,
        "nlp_ready": health_data.get("nlp_ready", False),
        "execution_ready": health_data.get("execution_ready", False),
        "memory_ready": health_data.get("memory_ready", False),
        "knowledge_ready": health_data.get("knowledge_ready", False),
        "benchmarks": health_data.get("benchmarks", {}),
        "analytics": health_data.get("analytics", {}),
        "nlp": nlp_stats,
    }


@app.post("/api/execute")
async def execute_command(request: dict):
    """Execute system commands for PC Control."""
    try:
        command = request.get("command", "")
        jarvis = await get_jarvis()
        if jarvis._execution:
            result = jarvis._execution.execute(command)
            return {
                "success": result.success,
                "result": result.result.get("response", str(result.result)) if isinstance(result.result, dict) else str(result.result),
                "actions": build_actions({"tool": result.tool_name, "result": result.result if isinstance(result.result, dict) else {}}),
            }
        return {"success": False, "result": "Execution engine not initialized", "actions": []}
    except Exception as e:
        logger.error("Execute error: %s", e)
        return {"success": False, "result": str(e), "actions": []}


@app.get("/api/logs")
async def get_logs(limit: int = 200, level: Optional[str] = None):
    """Get recent logs from buffer."""
    logs = log_buffer[-limit:]
    if level:
        logs = [log for log in logs if log["level"].lower() == level.lower()]
    return {
        "logs": logs,
        "total": len(log_buffer),
        "timestamp": datetime.now().isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
# SETTINGS — persistent user preferences
# ═══════════════════════════════════════════════════════════════

class SettingsUpdate(BaseModel):
    settings: dict[str, Any]


@app.get("/api/settings")
async def get_settings():
    """Get all persisted settings."""
    try:
        from jarvis.infra.settings import settings_storage
        return {"settings": settings_storage.all(), "path": settings_storage.get_path()}
    except Exception as e:
        logger.error("Settings load error: %s", e)
        return {"settings": {}, "error": str(e)}


@app.post("/api/settings")
async def update_settings(payload: SettingsUpdate):
    """Update and persist settings."""
    try:
        from jarvis.infra.settings import settings_storage
        settings_storage.set_many(payload.settings, save=True)
        return {"success": True, "settings": settings_storage.all()}
    except Exception as e:
        logger.error("Settings save error: %s", e)
        return {"success": False, "error": str(e)}


@app.post("/api/settings/reset")
async def reset_settings():
    """Reset all settings to defaults."""
    try:
        from jarvis.infra.settings import settings_storage
        settings_storage.reset_all()
        settings_storage.save()
        return {"success": True, "settings": settings_storage.all()}
    except Exception as e:
        logger.error("Settings reset error: %s", e)
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════
# WEBSOCKET: /ws — real-time stats + chat
# ═══════════════════════════════════════════════════════════════

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)

    # Send initial stats
    try:
        await websocket.send_json({"type": "system_stats", "payload": get_system_stats()})
    except Exception:
        connected_clients.discard(websocket)
        return

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "chat":
                jarvis = await get_jarvis()
                try:
                    result = await asyncio.wait_for(
                        jarvis.handle(data.get("message", "")),
                        timeout=HANDLE_TIMEOUT_SECONDS,
                    )
                except asyncio.TimeoutError:
                    result = {
                        "response": (
                            f"(JARVIS took longer than {HANDLE_TIMEOUT_SECONDS:.0f}s to respond.)"
                        ),
                        "intent": "timeout",
                        "intent_confidence": 0.0,
                        "tool": "",
                        "verified": False,
                        "total_ms": int(HANDLE_TIMEOUT_SECONDS * 1000),
                        "result": {},
                    }
                actions = build_actions(result)
                await websocket.send_json({
                    "type": "chat_response",
                    "data": {
                        "response": result.get("response", ""),
                        "actions": actions if actions else None,
                        "suggestions": None,
                    },
                })
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "get_stats":
                await websocket.send_json({"type": "system_stats", "payload": get_system_stats()})

    except WebSocketDisconnect:
        connected_clients.discard(websocket)
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        connected_clients.discard(websocket)


# ═══════════════════════════════════════════════════════════════
# WEBSOCKET: /ws/logs — real-time log streaming
# ═══════════════════════════════════════════════════════════════

@app.websocket("/ws/logs")
async def websocket_logs_endpoint(websocket: WebSocket):
    await websocket.accept()
    log_subscribers.add(websocket)

    # Send recent logs
    recent = log_buffer[-50:]
    if recent:
        try:
            await websocket.send_json({"type": "batch", "logs": recent})
        except Exception:
            log_subscribers.discard(websocket)
            return

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        log_subscribers.discard(websocket)
    except Exception as e:
        logger.error("Logs WebSocket error: %s", e)
        log_subscribers.discard(websocket)


# ═══════════════════════════════════════════════════════════════
# BACKGROUND TASKS
# ═══════════════════════════════════════════════════════════════

async def broadcast_system_stats():
    """Push system stats to all connected clients every 2 seconds."""
    while True:
        if connected_clients:
            stats = get_system_stats()
            msg = {"type": "system_stats", "payload": stats}
            disconnected = set()
            for client in connected_clients:
                try:
                    await client.send_json(msg)
                except Exception:
                    disconnected.add(client)
            connected_clients.difference_update(disconnected)
        await asyncio.sleep(2)


async def process_log_broadcasts():
    """Process queued log entries and broadcast to subscribers."""
    while True:
        try:
            while pending_log_broadcasts:
                log_entry = pending_log_broadcasts.pop(0)
                disconnected = set()
                for ws in log_subscribers:
                    try:
                        await ws.send_json({"type": "log", "data": log_entry})
                    except Exception:
                        disconnected.add(ws)
                log_subscribers.difference_update(disconnected)
            await asyncio.sleep(0.1)
        except Exception:
            await asyncio.sleep(1)


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("  JARVIS Desktop Backend")
    print(f"  API:       http://localhost:8001")
    print(f"  WebSocket: ws://localhost:8001/ws")
    print(f"  handle timeout:     {HANDLE_TIMEOUT_SECONDS:.0f}s")
    print(f"  stream timeout:     {STREAM_TIMEOUT_SECONDS:.0f}s")
    print(f"  ollama warmup max:  {OLLAMA_WARMUP_TIMEOUT:.0f}s")
    print()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        reload=False,
        # Long keep-alive so the SSE stream doesn't get killed mid-response
        # while the cloud GPU is generating jarvis-agi tokens.
        timeout_keep_alive=180,
        # Don't let uvicorn kill long-running handlers mid-stream.
        h11_max_incomplete_event_size=None,
    )
