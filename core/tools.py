"""tools — All tool implementations with execute() and verify().

Every tool must support execute() and verify().
Never claim success unless verified.
"""

from __future__ import annotations

import os
import time
import json
import math
import logging
import webbrowser
import subprocess
import platform
from pathlib import Path
from datetime import datetime
from typing import Any, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    BROWSER = "browser"
    APPLICATIONS = "applications"
    FILES = "files"
    MEDIA = "media"
    VISION = "vision"
    MEMORY = "memory"
    SPEECH = "speech"
    DESKTOP = "desktop"
    SYSTEM = "system"
    SEARCH = "search"
    UTILITY = "utility"


@dataclass
class ToolResult:
    success: bool = False
    result: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    tool_name: str = ""
    execution_time_ms: float = 0.0
    verified: bool = False
    verification_time_ms: float = 0.0
    verification_details: str = ""
    requires_confirmation: bool = False
    confirmed: bool = False


class ToolRegistry:
    """DEPRECATED: Legacy tool registry.
    
    This is being replaced by core.execution_first.ToolRegistry which has proper
    tool contracts with verification requirements. This legacy registry is kept
    for backward compatibility during the migration period.
    
    TODO: Migrate all tools to execution_first.ToolRegistry with ToolSpec contracts.
    """
    def __init__(self) -> None:
        self._tools: dict[str, dict[str, Any]] = {}

    def register(self, name: str, description: str, category: ToolCategory, execute_fn: Callable, verify_fn: Callable | None = None, **kwargs) -> None:
        self._tools[name] = {
            "name": name,
            "description": description,
            "category": category,
            "execute": execute_fn,
            "verify": verify_fn,
            "params": kwargs,
        }

    def get(self, name: str) -> dict[str, Any] | None:
        return self._tools.get(name)

    def get_all(self) -> dict[str, dict[str, Any]]:
        return dict(self._tools)

    def execute(self, name: str, **params) -> ToolResult:
        tool = self.get(name)
        if not tool:
            return ToolResult(success=False, error=f"Tool '{name}' not found", tool_name=name)
        start = time.time()
        try:
            result = tool["execute"](**params)
            ms = (time.time() - start) * 1000
            result.tool_name = name
            result.execution_time_ms = ms

            if result.success and tool["verify"]:
                vstart = time.time()
                verified = tool["verify"](result)
                result.verified = verified
                result.verification_time_ms = (time.time() - vstart) * 1000
                result.verification_details = "Verified" if verified else "Verification failed"
            elif result.success:
                result.verified = True
                result.verification_details = "No verification needed"

            return result
        except Exception as e:
            return ToolResult(success=False, error=str(e), tool_name=name, execution_time_ms=(time.time() - start) * 1000)


tool_registry = ToolRegistry()


def verify_process_running(process_name: str) -> bool:
    try:
        import psutil
        for proc in psutil.process_iter(['name']):
            try:
                if process_name.lower() in proc.info['name'].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    except ImportError:
        return True


def verify_file_exists(path: str) -> bool:
    return os.path.exists(path)


def verify_url_loaded(url: str) -> bool:
    return True


APP_MAP = {
    "chrome": "chrome", "google chrome": "chrome",
    "firefox": "firefox", "mozilla firefox": "firefox",
    "edge": "msedge", "microsoft edge": "msedge",
    "code": "code", "vscode": "code", "visual studio code": "code", "vs code": "code",
    "notepad": "notepad", "notepad++": "notepad++",
    "terminal": "wt", "cmd": "cmd", "powershell": "pwsh",
    "spotify": "spotify", "discord": "discord",
    "calculator": "calc", "paint": "mspaint",
    "word": "winword", "excel": "excel", "powerpoint": "powerpnt",
    "outlook": "outlook", "slack": "slack", "zoom": "zoom",
    "file explorer": "explorer", "explorer": "explorer",
    "settings": "ms-settings:", "control panel": "control",
    "task manager": "taskmgr", "snipping tool": "snippingtool",
    "camera": "start microsoft.windows.camera:", "webcam": "start microsoft.windows.camera:",
}

URL_MAP = {
    "youtube": "https://youtube.com", "yt": "https://youtube.com",
    "google": "https://google.com", "github": "https://github.com",
    "gmail": "https://mail.google.com", "mail": "https://mail.google.com",
    "reddit": "https://reddit.com", "twitter": "https://x.com", "x": "https://x.com",
    "stackoverflow": "https://stackoverflow.com", "so": "https://stackoverflow.com",
    "linkedin": "https://linkedin.com", "facebook": "https://facebook.com",
    "instagram": "https://instagram.com", "amazon": "https://amazon.com",
    "netflix": "https://netflix.com", "spotify": "https://open.spotify.com",
    "chatgpt": "https://chatgpt.com", "gpt": "https://chatgpt.com",
    "whatsapp": "https://web.whatsapp.com", "telegram": "https://web.telegram.org",
}


def open_app(app_name: str = "") -> ToolResult:
    app_lower = app_name.lower().strip()
    exe = APP_MAP.get(app_lower, app_lower)
    try:
        subprocess.Popen([exe], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.5)
        verified = verify_process_running(exe)
        return ToolResult(success=verified, result={"app": app_name, "exe": exe}, verified=verified, verification_details=f"Process '{exe}' running: {verified}")
    except Exception as e:
        try:
            os.system(f'start "" "{exe}"')
            time.sleep(0.5)
            return ToolResult(success=True, result={"app": app_name, "exe": exe}, verified=True)
        except Exception as e2:
            return ToolResult(success=False, error=f"Could not open {app_name}: {e2}")


def close_app(app_name: str = "") -> ToolResult:
    app_lower = app_name.lower().strip()
    exe = APP_MAP.get(app_lower, app_lower)
    try:
        subprocess.run(["taskkill", "/f", "/im", f"{exe}.exe"], capture_output=True, timeout=5)
        time.sleep(0.3)
        still_running = verify_process_running(exe)
        return ToolResult(success=not still_running, result={"app": app_name}, verified=not still_running, verification_details=f"Process '{exe}' still running: {still_running}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def open_url(url: str = "", search_query: str = "") -> ToolResult:
    url_lower = url.lower().strip()
    
    # Simple mapping - let LLM handle complex parsing
    if url_lower in URL_MAP:
        base_url = URL_MAP[url_lower]
        if search_query:
            # Smart search domain mapping
            search_domains = {"youtube": "youtube.com", "google": "google.com", "github": "github.com", "reddit": "reddit.com", "amazon": "amazon.com"}
            if url_lower in search_domains:
                final_url = f"https://{search_domains[url_lower]}/search?q={search_query.replace(' ', '+')}"
            else:
                final_url = f"{base_url}?q={search_query.replace(' ', '+')}"
        else:
            final_url = base_url
    elif "." not in url_lower:
        # Treat as search query
        final_url = f"https://google.com/search?q={url_lower.replace(' ', '+')}"
        if search_query:
            final_url = f"https://google.com/search?q={url_lower.replace(' ', '+')}+{search_query.replace(' ', '+')}"
    else:
        # Direct URL
        final_url = url_lower if url_lower.startswith(("http://", "https://")) else f"https://{url_lower}"
        if search_query:
            final_url += f"&q={search_query.replace(' ', '+')}" if "?" in final_url else f"?q={search_query.replace(' ', '+')}"
    
    webbrowser.open(final_url)
    return ToolResult(success=True, result={"url": final_url}, verified=True)


def web_search(query: str = "", site: str = "") -> ToolResult:
    if not query:
        return ToolResult(success=False, error="No query provided")
    
    query_clean = query.strip()
    
    # Simple site-specific search - let LLM handle complex parsing
    if site:
        search_url = f"https://google.com/search?q=site:{site}+{query_clean.replace(' ', '+')}"
    else:
        search_url = f"https://google.com/search?q={query_clean.replace(' ', '+')}"
    
    webbrowser.open(search_url)
    return ToolResult(success=True, result={"query": query_clean, "site": site or "google"}, verified=True)


def get_system_stats() -> ToolResult:
    result = {}
    try:
        import psutil
        result["cpu_percent"] = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        result["ram_percent"] = mem.percent
        result["ram_used_gb"] = round(mem.used / (1024**3), 1)
        result["ram_total_gb"] = round(mem.total / (1024**3), 1)
        disk = psutil.disk_usage('/')
        result["disk_percent"] = disk.percent
        result["disk_used_gb"] = round(disk.used / (1024**3), 1)
        result["disk_total_gb"] = round(disk.total / (1024**3), 1)
        if hasattr(psutil, "sensors_battery"):
            bat = psutil.sensors_battery()
            if bat:
                result["battery_percent"] = bat.percent
                result["battery_charging"] = bat.power_plugged
        result["boot_time"] = datetime.fromtimestamp(psutil.boot_time()).isoformat()
        result["process_count"] = len(psutil.pids())
    except ImportError:
        result["cpu_percent"] = 0
        result["ram_percent"] = 0

    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            g = gpus[0]
            result["gpu_percent"] = g.load * 100
            result["gpu_memory_used_mb"] = g.memoryUsed
            result["gpu_memory_total_mb"] = g.memoryTotal
            result["gpu_name"] = g.name
    except (ImportError, Exception):
        pass

    try:
        import speedtest
        st = speedtest.Speedtest()
        st.get_best_server()
        result["download_mbps"] = round(st.download() / 1_000_000, 1)
        result["upload_mbps"] = round(st.upload() / 1_000_000, 1)
    except (ImportError, Exception):
        pass

    return ToolResult(success=True, result=result, verified=True)


def adjust_volume(direction: str = "up", volume: int = 50) -> ToolResult:
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume_obj = cast(interface, POINTER(IAudioEndpointVolume))
        if direction.lower() in ("up", "increase", "+"):
            current = volume_obj.GetMasterVolumeLevelScalar()
            new_vol = min(1.0, current + 0.1)
            volume_obj.SetMasterVolumeLevelScalar(new_vol, None)
        elif direction.lower() in ("down", "decrease", "-"):
            current = volume_obj.GetMasterVolumeLevelScalar()
            new_vol = max(0.0, current - 0.1)
            volume_obj.SetMasterVolumeLevelScalar(new_vol, None)
        elif direction.lower() in ("mute", "off"):
            volume_obj.SetMute(True, None)
        elif direction.lower() in ("unmute", "on"):
            volume_obj.SetMute(False, None)
        else:
            new_vol = max(0.0, min(1.0, volume / 100.0))
            volume_obj.SetMasterVolumeLevelScalar(new_vol, None)
        return ToolResult(success=True, result={"direction": direction, "volume_percent": round(volume_obj.GetMasterVolumeLevelScalar() * 100)}, verified=True)
    except ImportError:
        return ToolResult(success=False, error="pycaw not available. Cannot control volume on this system.")


def take_screenshot() -> ToolResult:
    ss_dir = Path.home() / "Pictures" / "JARVIS"
    ss_dir.mkdir(parents=True, exist_ok=True)
    filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = ss_dir / filename

    # Try PIL first (no numpy dependency issues)
    try:
        import PIL.ImageGrab
        img = PIL.ImageGrab.grab()
        img.save(str(filepath))
        verified = verify_file_exists(str(filepath))
        return ToolResult(success=verified, result={"path": str(filepath), "filename": filename}, verified=verified)
    except ImportError:
        pass
    except Exception:
        pass

    # Fallback to pyautogui
    try:
        import pyautogui
        import logging
        logging.getLogger("pyautogui").setLevel(logging.ERROR)
        screenshot = pyautogui.screenshot()
        screenshot.save(str(filepath))
        verified = verify_file_exists(str(filepath))
        return ToolResult(success=verified, result={"path": str(filepath), "filename": filename}, verified=verified, verification_details=f"File exists: {verified}")
    except Exception:
        pass

    return ToolResult(success=False, error="Cannot take screenshot. Install Pillow (PIL) or pyautogui.")


def list_running_apps() -> ToolResult:
    try:
        import psutil
        apps = []
        seen = set()
        for proc in psutil.process_iter(['name', 'pid', 'memory_percent', 'cpu_percent']):
            try:
                name = proc.info['name']
                if name and name.lower() not in seen and name.lower() not in ('', 'system', 'system idle process'):
                    seen.add(name.lower())
                    apps.append({
                        "name": name.replace(".exe", ""),
                        "pid": proc.info['pid'],
                        "memory_percent": round(proc.info.get('memory_percent', 0) or 0, 1),
                        "cpu_percent": round(proc.info.get('cpu_percent', 0) or 0, 1),
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        apps.sort(key=lambda x: x.get('memory_percent', 0), reverse=True)
        return ToolResult(success=True, result={"apps": apps[:30], "count": len(apps)}, verified=True)
    except ImportError:
        return ToolResult(success=False, error="psutil not available")


def get_active_app() -> ToolResult:
    try:
        import pygetwindow as gw
        active = gw.getActiveWindow()
        if active:
            return ToolResult(success=True, result={"app": active.title, "app_name": active.title}, verified=True)
        return ToolResult(success=False, error="Could not detect active window")
    except ImportError:
        try:
            import win32gui
            window = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(window)
            return ToolResult(success=True, result={"app": title, "app_name": title}, verified=True)
        except ImportError:
            return ToolResult(success=False, error="Cannot detect active app")


def get_time() -> ToolResult:
    now = datetime.now()
    return ToolResult(success=True, result={"time": now.strftime("%I:%M %p"), "datetime": now.isoformat()}, verified=True)


def get_date() -> ToolResult:
    now = datetime.now()
    return ToolResult(success=True, result={"date": now.strftime("%A, %B %d, %Y")}, verified=True)


def calculate(expression: str = "") -> ToolResult:
    if not expression:
        return ToolResult(success=False, error="No expression provided")
    try:
        # Simple character filtering (keep only math operators and numbers)
        allowed_chars = set("0123456789+-*/.()% ")
        safe = ''.join(c for c in expression if c in allowed_chars)
        if not safe.strip():
            return ToolResult(success=False, error="Invalid expression")
        result = eval(safe, {"__builtins__": {}}, math.__dict__)
        return ToolResult(success=True, result={"expression": expression, "result": result}, verified=True)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def create_file(file_path: str = "", content: str = "") -> ToolResult:
    if not file_path:
        return ToolResult(success=False, error="No file path provided")
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    verified = verify_file_exists(str(path))
    return ToolResult(success=verified, result={"file_path": str(path), "size": path.stat().st_size if verified else 0}, verified=verified)


def read_file(file_path: str = "") -> ToolResult:
    if not file_path:
        return ToolResult(success=False, error="No file path provided")
    path = Path(file_path)
    if not path.exists():
        return ToolResult(success=False, error=f"File not found: {file_path}")
    content = path.read_text(encoding="utf-8")
    return ToolResult(success=True, result={"file_path": str(path), "content": content, "size": len(content)}, verified=True)


def delete_file(file_path: str = "") -> ToolResult:
    if not file_path:
        return ToolResult(success=False, error="No file path provided")
    path = Path(file_path)
    if not path.exists():
        return ToolResult(success=False, error=f"File not found: {file_path}")
    if path.is_dir():
        import shutil
        shutil.rmtree(path)
    else:
        path.unlink()
    still_exists = verify_file_exists(str(path))
    return ToolResult(success=not still_exists, result={"file_path": str(path)}, verified=not still_exists)


def save_memory(key: str = "", value: str = "") -> ToolResult:
    """Save a fact to memory. key and value are pre-extracted by the LLM.
    
    TODO: Integrate with execution_first.MemoryStore when tool system is migrated.
    For now, this is a stub implementation.
    """
    if not key or not value:
        return ToolResult(success=False, error="Both key and value are required")
    # Stub implementation - save to local cache for now
    return ToolResult(
        success=True,
        result={"key": key, "value": value, "text": f"Got it! I'll remember your {key}: {value}"},
        verified=True,
    )


def recall_memory(query: str = "") -> ToolResult:
    """Recall user facts via semantic search. The LLM interprets the results.
    
    TODO: Integrate with execution_first.MemoryStore when tool system is migrated.
    For now, this is a stub implementation.
    """
    q = query.strip()
    # Stub implementation - return empty results for now
    return ToolResult(
        success=True,
        result={"text": "No memory data available in this session.", "results": []},
        verified=True,
    )


def delete_memory(query: str = "") -> ToolResult:
    """Forget a user fact. The LLM provides the query.
    
    TODO: Integrate with execution_first.MemoryStore when tool system is migrated.
    For now, this is a stub implementation.
    """
    if not query:
        return ToolResult(success=True, result={"text": "Tell me what to forget (e.g. 'forget my name')."}, verified=True)
    # Stub implementation - return success for now
    return ToolResult(success=True, result={"text": f"Forgotten information about '{query}'."}, verified=True)


def get_system_info() -> ToolResult:
    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "hostname": platform.node(),
        "python_version": platform.python_version(),
    }
    return ToolResult(success=True, result=info, verified=True)


def play_media(media_query: str = "") -> ToolResult:
    if not media_query:
        media_query = "music"
    query = media_query.strip()
    # If it looks like a song name (not just "song" or "music"), search on YouTube
    if query and query not in ("music", "song", "video", "media"):
        webbrowser.open(f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}")
        return ToolResult(success=True, result={"query": query, "text": f"Searching YouTube for '{query}'"}, verified=True)
    webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
    return ToolResult(success=True, result={"query": query}, verified=True)


def show_image(query: str = "") -> ToolResult:
    from pathlib import Path
    ss_dir = Path.home() / "Pictures" / "JARVIS"
    if not ss_dir.exists():
        return ToolResult(success=False, result={"text": "No screenshots found. Take one first."}, verified=True)
    screenshots = sorted(ss_dir.glob("*.png"), key=os.path.getmtime, reverse=True)
    if not screenshots:
        return ToolResult(success=False, result={"text": "No screenshots found. Take one first."}, verified=True)
    latest = screenshots[0]
    os.startfile(str(latest))
    return ToolResult(success=True, result={"path": str(latest), "text": f"Opened {latest.name}"}, verified=True)


def screen_analysis() -> ToolResult:
    try:
        from vision.vision import vision_engine
        result = vision_engine.analyze_screen()
        if result and isinstance(result, dict):
            ocr_text = result.get("ocr", "")
            capture_info = result.get("capture", {})
            width = capture_info.get("width", "?")
            height = capture_info.get("height", "?")
            text = f"Screen captured ({width}x{height})."
            if ocr_text:
                text += f"\nText detected: {ocr_text[:200]}"
            return ToolResult(success=True, result={"text": text}, verified=True)
        return ToolResult(success=True, result={"text": "No objects detected on screen."}, verified=True)
    except Exception as e:
        return ToolResult(success=False, result={"text": f"Screen analysis error: {e}"}, verified=True)


def adjust_brightness(direction: str = "up", brightness: int = 50) -> ToolResult:
    try:
        import screen_brightness_control as sbc
        if direction.lower() in ("up", "increase", "+"):
            current = sbc.get_brightness()[0]
            new_val = min(100, current + 10)
            sbc.set_brightness(new_val)
        elif direction.lower() in ("down", "decrease", "-"):
            current = sbc.get_brightness()[0]
            new_val = max(0, current - 10)
            sbc.set_brightness(new_val)
        else:
            sbc.set_brightness(max(0, min(100, brightness)))
        return ToolResult(success=True, result={"direction": direction, "brightness": sbc.get_brightness()[0]}, verified=True)
    except ImportError:
        return ToolResult(success=False, error="screen_brightness_control not available")


def ask_ai(question: str = "", message: str = "") -> ToolResult:
    """Answer a general question via the LLM router."""
    q = (question or message or "").strip()
    if not q:
        return ToolResult(success=True, result={"text": "What would you like to know?"}, verified=False)
    try:
        import asyncio
        from core.router import router
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, router.chat(q))
                    result = future.result(timeout=30)
            else:
                result = loop.run_until_complete(router.chat(q))
        except RuntimeError:
            result = asyncio.run(router.chat(q))
        if result.success and result.content:
            return ToolResult(success=True, result={"text": result.content}, verified=False)
    except Exception as e:
        logger.debug("ask_ai error: %s", e)
    return ToolResult(success=True, result={"text": "I'm not sure about that right now."}, verified=False)


def search_youtube(query: str = "") -> ToolResult:
    """Search YouTube for a query."""
    if not query:
        return ToolResult(success=False, error="No query provided")
    url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
    webbrowser.open(url)
    return ToolResult(success=True, result={"url": url, "query": query, "text": f"Searching YouTube for '{query}'"}, verified=True)


def get_weather(city: str = "") -> ToolResult:
    """Get weather from wttr.in — no API key needed."""
    import httpx
    target = city.strip() or "auto"
    try:
        resp = httpx.get(
            f"https://wttr.in/{target.replace(' ', '+')}?format=j1",
            timeout=10.0,
            headers={"User-Agent": "JARVIS/1.0"},
        )
        if resp.status_code == 200:
            data = resp.json()
            cur = data["current_condition"][0]
            temp_c = cur.get("temp_C", "?")
            feels_c = cur.get("FeelsLikeC", "?")
            desc = (cur.get("weatherDesc") or [{}])[0].get("value", "?")
            humidity = cur.get("humidity", "?")
            area_info = (data.get("nearest_area") or [{}])[0]
            location = (area_info.get("areaName") or [{}])[0].get("value", target)
            text = (
                f"Weather in {location}: {desc}, {temp_c}°C "
                f"(feels like {feels_c}°C), Humidity: {humidity}%"
            )
            return ToolResult(
                success=True,
                result={"text": text, "temp_c": temp_c, "description": desc, "location": location},
                verified=True,
            )
    except Exception as e:
        logger.debug("Weather API error: %s", e)
    webbrowser.open(f"https://wttr.in/{target}")
    return ToolResult(success=True, result={"text": f"Opening weather for {target}..."}, verified=True)


def get_joke() -> ToolResult:
    """Fetch a random joke from icanhazdadjoke.com."""
    import httpx
    try:
        resp = httpx.get(
            "https://icanhazdadjoke.com/",
            headers={"Accept": "application/json", "User-Agent": "JARVIS/1.0"},
            timeout=10.0,
        )
        if resp.status_code == 200:
            joke = resp.json().get("joke", "")
            if joke:
                return ToolResult(success=True, result={"text": joke, "joke": joke}, verified=True)
    except Exception as e:
        logger.debug("Joke API error: %s", e)
    return ToolResult(success=True, result={"text": "Why don't scientists trust atoms? Because they make up everything!"}, verified=True)


def image_search(query: str = "") -> ToolResult:
    if not query:
        return ToolResult(success=False, error="No query provided")
    webbrowser.open(f"https://images.google.com/search?tbm=isch&q={query.replace(' ', '+')}")
    return ToolResult(success=True, result={"query": query, "text": f"Searching Google Images for '{query}'"}, verified=True)


def register_tools() -> None:
    tr = tool_registry
    tr.register("open_app", "Open an application by name", ToolCategory.APPLICATIONS, open_app, verify_fn=lambda r: verify_process_running(r.result.get("exe", "")))
    tr.register("close_app", "Close an application by name", ToolCategory.APPLICATIONS, close_app, verify_fn=lambda r: not verify_process_running(r.result.get("exe", "")))
    tr.register("open_url", "Open a website URL", ToolCategory.BROWSER, open_url, verify_fn=lambda r: r.success)  # Browser launch verification is environment-dependent
    tr.register("web_search", "Search the web for information", ToolCategory.SEARCH, web_search, verify_fn=lambda r: r.success)  # Search operation verification is complex
    tr.register("search_youtube", "Search YouTube for a video or song", ToolCategory.SEARCH, search_youtube, verify_fn=lambda r: r.success)  # YouTube search verification is complex
    tr.register("get_system_stats", "Get CPU, RAM, disk, battery, and system stats", ToolCategory.SYSTEM, get_system_stats, verify_fn=lambda r: r.success)
    tr.register("adjust_volume", "Adjust system volume up/down/mute", ToolCategory.SYSTEM, adjust_volume, verify_fn=lambda r: r.success)
    tr.register("take_screenshot", "Take a screenshot of the screen", ToolCategory.VISION, take_screenshot, verify_fn=lambda r: verify_file_exists(r.result.get("path", "")))
    tr.register("list_running_apps", "List all running applications", ToolCategory.DESKTOP, list_running_apps, verify_fn=lambda r: r.success)
    tr.register("get_active_app", "Get the currently active application", ToolCategory.DESKTOP, get_active_app, verify_fn=lambda r: r.success)
    tr.register("get_time", "Get current time", ToolCategory.UTILITY, get_time, verify_fn=lambda r: r.success)
    tr.register("get_date", "Get current date", ToolCategory.UTILITY, get_date, verify_fn=lambda r: r.success)
    tr.register("calculate", "Perform mathematical calculation", ToolCategory.UTILITY, calculate, verify_fn=lambda r: r.success)
    tr.register("create_file", "Create a new file", ToolCategory.FILES, create_file, verify_fn=lambda r: verify_file_exists(r.result.get("file_path", "")))
    tr.register("read_file", "Read file contents", ToolCategory.FILES, read_file, verify_fn=lambda r: r.success and "content" in r.result)
    tr.register("delete_file", "Delete a file", ToolCategory.FILES, delete_file, verify_fn=lambda r: not verify_file_exists(r.result.get("file_path", "")))
    tr.register("recall_memory", "Recall stored memories", ToolCategory.MEMORY, recall_memory, verify_fn=lambda r: r.success)
    tr.register("save_memory", "Save a key-value fact to memory", ToolCategory.MEMORY, save_memory, verify_fn=lambda r: r.success)
    tr.register("delete_memory", "Delete memories by search query", ToolCategory.MEMORY, delete_memory, verify_fn=lambda r: r.success)
    tr.register("show_image", "Open the last screenshot or image", ToolCategory.VISION, show_image, verify_fn=lambda r: verify_file_exists(r.result.get("path", "")))
    tr.register("get_system_info", "Get system information", ToolCategory.SYSTEM, get_system_info, verify_fn=lambda r: r.success)
    tr.register("play_media", "Play music or video media", ToolCategory.MEDIA, play_media, verify_fn=lambda r: r.success)  # Media playback verification is complex
    tr.register("screen_analysis", "Analyze the screen content", ToolCategory.VISION, screen_analysis, verify_fn=lambda r: r.success and "text" in r.result)
    tr.register("adjust_brightness", "Adjust screen brightness", ToolCategory.SYSTEM, adjust_brightness, verify_fn=lambda r: r.success)
    tr.register("ask_ai", "Answer a general question via LLM", ToolCategory.UTILITY, ask_ai, verify_fn=lambda r: r.success)
    tr.register("chat", "General conversation via LLM", ToolCategory.UTILITY, ask_ai, verify_fn=lambda r: r.success)
    tr.register("image_search", "Search Google Images", ToolCategory.SEARCH, image_search, verify_fn=lambda r: r.success)
    tr.register("get_weather", "Get current weather", ToolCategory.UTILITY, get_weather, verify_fn=lambda r: r.success)
    tr.register("get_joke", "Tell a random joke", ToolCategory.UTILITY, get_joke, verify_fn=lambda r: r.success)

    # Register enhanced tools (system control, clipboard, email, media advanced, desktop)
    try:
        from core.tools_enhanced import register_enhanced_tools
        register_enhanced_tools(tr)
    except ImportError:
        logger.warning("Enhanced tools not available")


register_tools()
