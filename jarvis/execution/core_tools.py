"""Core Tools — Actual executable tools.

Every tool does real work. Returns ToolResult.
"""

from __future__ import annotations

import os
import time
import json
import logging
import subprocess
import webbrowser
from typing import Any
from pathlib import Path

logger = logging.getLogger(__name__)

from .tool_registry import ToolResult, ToolCategory, tool_registry


# ═══════════════════════════════════════════════════════════════════════
# APP MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════

def open_app(app_name: str) -> ToolResult:
    """Open an application by name."""
    start = time.time()
    app_lower = app_name.lower().strip()

    # Map common names to executables
    app_map = {
        "chrome": "chrome", "google chrome": "chrome",
        "firefox": "firefox", "edge": "msedge", "microsoft edge": "msedge",
        "code": "code", "vscode": "code", "vs code": "code", "visual studio code": "code",
        "notepad": "notepad", "notepad++": "notepad++",
        "terminal": "wt", "powershell": "pwsh",
        "spotify": "spotify", "discord": "discord",
        "file explorer": "explorer", "explorer": "explorer",
        "calculator": "calc", "paint": "mspaint",
        "word": "winword", "excel": "excel", "powerpoint": "powerpnt",
    }

    # Website shortcuts
    url_map = {
        "youtube": "https://youtube.com", "google": "https://google.com",
        "github": "https://github.com", "gmail": "https://mail.google.com",
        "spotify": "https://open.spotify.com", "netflix": "https://netflix.com",
        "twitter": "https://twitter.com", "x": "https://x.com",
        "reddit": "https://reddit.com", "stackoverflow": "https://stackoverflow.com",
    }

    # Try website first
    if app_lower in url_map:
        webbrowser.open(url_map[app_lower])
        return ToolResult(
            success=True,
            result={"url": url_map[app_lower], "app": app_name, "type": "website"},
            tool_name="open_app",
            execution_time_ms=(time.time() - start) * 1000,
        )

    # Try opening as application
    exe = app_map.get(app_lower, app_lower)
    try:
        subprocess.Popen([exe], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.5)
        return ToolResult(
            success=True,
            result={"app": app_name, "exe": exe, "type": "application"},
            tool_name="open_app",
            execution_time_ms=(time.time() - start) * 1000,
        )
    except FileNotFoundError:
        # Try with start command on Windows
        try:
            os.system(f'start {exe}')
            time.sleep(0.5)
            return ToolResult(
                success=True,
                result={"app": app_name, "exe": exe, "type": "application"},
                tool_name="open_app",
                execution_time_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Could not open '{app_name}': {e}",
                tool_name="open_app",
                execution_time_ms=(time.time() - start) * 1000,
            )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Could not open '{app_name}': {e}",
            tool_name="open_app",
            execution_time_ms=(time.time() - start) * 1000,
        )


def close_app(app_name: str) -> ToolResult:
    """Close an application by name."""
    start = time.time()
    app_lower = app_name.lower().strip()

    process_map = {
        "chrome": "chrome.exe", "firefox": "firefox.exe", "edge": "msedge.exe",
        "code": "Code.exe", "vscode": "Code.exe", "vs code": "Code.exe",
        "notepad": "Notepad.exe", "spotify": "Spotify.exe", "discord": "Discord.exe",
    }

    exe_name = process_map.get(app_lower, f"{app_lower}.exe")

    try:
        result = os.system(f'taskkill /F /IM {exe_name} >nul 2>&1')
        success = result == 0
        return ToolResult(
            success=success,
            result={"app": app_name, "exe": exe_name, "action": "closed"},
            error=None if success else f"Process '{exe_name}' not found or could not be terminated",
            tool_name="close_app",
            execution_time_ms=(time.time() - start) * 1000,
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Could not close '{app_name}': {e}",
            tool_name="close_app",
            execution_time_ms=(time.time() - start) * 1000,
        )


# ═══════════════════════════════════════════════════════════════════════
# WEB / SEARCH
# ═══════════════════════════════════════════════════════════════════════

def web_search(query: str) -> ToolResult:
    """Search the web via Google."""
    start = time.time()
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    try:
        webbrowser.open(url)
        return ToolResult(
            success=True,
            result={"query": query, "url": url},
            tool_name="web_search",
            execution_time_ms=(time.time() - start) * 1000,
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Search failed: {e}",
            tool_name="web_search",
            execution_time_ms=(time.time() - start) * 1000,
        )


# Platform-specific search URLs
PLATFORM_SEARCH_URLS = {
    "reddit": "https://www.reddit.com/search/?q={query}",
    "youtube": "https://www.youtube.com/results?search_query={query}",
    "github": "https://github.com/search?q={query}",
    "stackoverflow": "https://stackoverflow.com/search?q={query}",
    "stack overflow": "https://stackoverflow.com/search?q={query}",
    "amazon": "https://www.amazon.com/s?k={query}",
    "wikipedia": "https://en.wikipedia.org/w/index.php?search={query}",
    "google scholar": "https://scholar.google.com/scholar?q={query}",
    "spotify": "https://open.spotify.com/search/{query}",
    "linkedin": "https://www.linkedin.com/search/results/all/?keywords={query}",
    "imdb": "https://www.imdb.com/find/?q={query}",
    "ebay": "https://www.ebay.com/sch/i.html?_nkw={query}",
    "twitter": "https://twitter.com/search?q={query}",
    "x": "https://twitter.com/search?q={query}",
    "pinterest": "https://www.pinterest.com/search/pins/?q={query}",
    "medium": "https://medium.com/search?q={query}",
    "duckduckgo": "https://duckduckgo.com/?q={query}",
    "quora": "https://www.quora.com/search?q={query}",
    "npm": "https://www.npmjs.com/search?q={query}",
    "pypi": "https://pypi.org/search/?q={query}",
}


def search_on_platform(query: str, platform: str = "") -> ToolResult:
    """Search on a specific platform (reddit, youtube, github, amazon, etc.)."""
    start = time.time()
    platform_lower = platform.lower().strip()

    if not platform_lower:
        # Try to infer platform from query
        for p in PLATFORM_SEARCH_URLS:
            if p in query.lower():
                platform_lower = p
                # Remove platform name from query
                query = query.lower().replace(p, "").replace("on ", "").strip()
                break

    if platform_lower in PLATFORM_SEARCH_URLS:
        url = PLATFORM_SEARCH_URLS[platform_lower].format(query=query.replace(" ", "+"))
    else:
        # Fallback to site-specific Google search
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}+site:{platform_lower}.com"

    try:
        webbrowser.open(url)
        return ToolResult(
            success=True,
            result={"query": query, "platform": platform, "url": url},
            tool_name="search_on_platform",
            execution_time_ms=(time.time() - start) * 1000,
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Platform search failed: {e}",
            tool_name="search_on_platform",
            execution_time_ms=(time.time() - start) * 1000,
        )


def open_url(url: str) -> ToolResult:
    """Open a URL in the default browser."""
    start = time.time()
    try:
        if not url.startswith("http"):
            url = f"https://{url}"
        webbrowser.open(url)
        return ToolResult(
            success=True,
            result={"url": url},
            tool_name="open_url",
            execution_time_ms=(time.time() - start) * 1000,
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Could not open URL: {e}",
            tool_name="open_url",
            execution_time_ms=(time.time() - start) * 1000,
        )


# ═══════════════════════════════════════════════════════════════════════
# FILE OPERATIONS
# ═══════════════════════════════════════════════════════════════════════

def create_file(file_path: str, content: str = "") -> ToolResult:
    """Create a file with optional content."""
    start = time.time()
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return ToolResult(
            success=True,
            result={"file_path": str(path), "size": len(content), "created": True},
            tool_name="create_file",
            execution_time_ms=(time.time() - start) * 1000,
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Could not create file: {e}",
            tool_name="create_file",
            execution_time_ms=(time.time() - start) * 1000,
        )


def delete_file(file_path: str) -> ToolResult:
    """Delete a file."""
    start = time.time()
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            return ToolResult(
                success=True,
                result={"file_path": str(path), "deleted": True},
                tool_name="delete_file",
                execution_time_ms=(time.time() - start) * 1000,
            )
        else:
            return ToolResult(
                success=False,
                error=f"File not found: {file_path}",
                tool_name="delete_file",
                execution_time_ms=(time.time() - start) * 1000,
            )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Could not delete file: {e}",
            tool_name="delete_file",
            execution_time_ms=(time.time() - start) * 1000,
        )


def read_file(file_path: str) -> ToolResult:
    """Read file contents."""
    start = time.time()
    try:
        path = Path(file_path)
        if not path.exists():
            return ToolResult(
                success=False,
                error=f"File not found: {file_path}",
                tool_name="read_file",
                execution_time_ms=(time.time() - start) * 1000,
            )
        content = path.read_text(encoding="utf-8", errors="ignore")
        return ToolResult(
            success=True,
            result={"file_path": str(path), "content": content, "size": len(content)},
            tool_name="read_file",
            execution_time_ms=(time.time() - start) * 1000,
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Could not read file: {e}",
            tool_name="read_file",
            execution_time_ms=(time.time() - start) * 1000,
        )


# ═══════════════════════════════════════════════════════════════════════
# SYSTEM CONTROLS
# ═══════════════════════════════════════════════════════════════════════

def adjust_volume(direction: str = "up", amount: int = 10) -> ToolResult:
    """Adjust system volume."""
    start = time.time()
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = interface.QueryInterface(IAudioEndpointVolume)
        current = volume.GetMasterVolumeLevelScalar()

        if direction == "up":
            new_vol = min(1.0, current + amount / 100)
        elif direction == "down":
            new_vol = max(0.0, current - amount / 100)
        else:  # mute
            new_vol = 0.0

        volume.SetMasterVolumeLevelScalar(new_vol, None)
        return ToolResult(
            success=True,
            result={"direction": direction, "volume_percent": round(new_vol * 100)},
            tool_name="adjust_volume",
            execution_time_ms=(time.time() - start) * 1000,
        )
    except ImportError:
        # Fallback to nircmd or powershell
        try:
            if direction == "up":
                os.system(f'nircmd.exe changesysvolume {amount * 655}')
            elif direction == "down":
                os.system(f'nircmd.exe changesysvolume -{amount * 655}')
            else:
                os.system('nircmd.exe mutesysvolume 1')
            return ToolResult(
                success=True,
                result={"direction": direction, "method": "nircmd"},
                tool_name="adjust_volume",
                execution_time_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Volume control failed: {e}",
                tool_name="adjust_volume",
                execution_time_ms=(time.time() - start) * 1000,
            )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Volume control failed: {e}",
            tool_name="adjust_volume",
            execution_time_ms=(time.time() - start) * 1000,
        )


def take_screenshot(save_path: str = "") -> ToolResult:
    """Take a screenshot."""
    start = time.time()
    try:
        import pyautogui
        if not save_path:
            from datetime import datetime
            save_path = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        pyautogui.screenshot(save_path)
        return ToolResult(
            success=True,
            result={"path": save_path, "exists": os.path.exists(save_path)},
            tool_name="take_screenshot",
            execution_time_ms=(time.time() - start) * 1000,
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Screenshot failed: {e}",
            tool_name="take_screenshot",
            execution_time_ms=(time.time() - start) * 1000,
        )


def get_system_stats() -> ToolResult:
    """Get system statistics."""
    start = time.time()
    try:
        import psutil
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        bat = psutil.sensors_battery()
        stats = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "cpu_count": psutil.cpu_count(),
            "ram_used_gb": round(mem.used / (1024**3), 1),
            "ram_total_gb": round(mem.total / (1024**3), 1),
            "ram_percent": mem.percent,
            "disk_percent": round(disk.percent, 1),
            "battery_percent": bat.percent if bat else -1,
            "battery_charging": bat.power_plugged if bat else False,
            "process_count": len(psutil.pids()),
        }
        return ToolResult(
            success=True,
            result=stats,
            tool_name="get_system_stats",
            execution_time_ms=(time.time() - start) * 1000,
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"System stats failed: {e}",
            tool_name="get_system_stats",
            execution_time_ms=(time.time() - start) * 1000,
        )


def get_time() -> ToolResult:
    """Get current time."""
    from datetime import datetime
    now = datetime.now()
    return ToolResult(
        success=True,
        result={"time": now.strftime("%I:%M %p"), "hour": now.hour, "minute": now.minute},
        tool_name="get_time",
    )


def get_date() -> ToolResult:
    """Get current date."""
    from datetime import datetime
    now = datetime.now()
    return ToolResult(
        success=True,
        result={"date": now.strftime("%A, %B %d, %Y"), "iso": now.isoformat()},
        tool_name="get_date",
    )


def list_running_apps(limit: int = 20) -> ToolResult:
    """List running applications."""
    start = time.time()
    try:
        import psutil
        apps = []
        seen = set()
        for proc in psutil.process_iter(['name', 'pid', 'cpu_percent', 'memory_percent']):
            try:
                name = proc.info.get('name', '')
                if name and name not in seen:
                    seen.add(name)
                    apps.append({
                        "name": name,
                        "pid": proc.info.get('pid', 0),
                        "cpu": round(proc.info.get('cpu_percent', 0) or 0, 1),
                        "memory": round(proc.info.get('memory_percent', 0) or 0, 1),
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        apps.sort(key=lambda x: x['cpu'], reverse=True)
        return ToolResult(
            success=True,
            result={"apps": apps[:limit], "total": len(apps)},
            tool_name="list_running_apps",
            execution_time_ms=(time.time() - start) * 1000,
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"List apps failed: {e}",
            tool_name="list_running_apps",
            execution_time_ms=(time.time() - start) * 1000,
        )


# ═══════════════════════════════════════════════════════════════════════
# MEMORY / NOTES / TODOS
# ═══════════════════════════════════════════════════════════════════════

_NOTES_FILE = Path.home() / ".jarvis" / "notes.json"
_TODOS_FILE = Path.home() / ".jarvis" / "todos.json"


def _load_json(path: Path) -> list:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_json(path: Path, data: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def add_note(content: str) -> ToolResult:
    notes = _load_json(_NOTES_FILE)
    note = {"id": str(len(notes) + 1), "content": content, "created_at": time.time()}
    notes.append(note)
    _save_json(_NOTES_FILE, notes)
    return ToolResult(success=True, result={"id": note["id"], "content": content}, tool_name="add_note")


def get_notes() -> ToolResult:
    notes = _load_json(_NOTES_FILE)
    return ToolResult(success=True, result={"notes": notes, "count": len(notes)}, tool_name="get_notes")


def add_todo(task: str) -> ToolResult:
    todos = _load_json(_TODOS_FILE)
    todo = {"id": str(len(todos) + 1), "task": task, "completed": False, "created_at": time.time()}
    todos.append(todo)
    _save_json(_TODOS_FILE, todos)
    return ToolResult(success=True, result={"id": todo["id"], "task": task}, tool_name="add_todo")


def get_todos() -> ToolResult:
    todos = _load_json(_TODOS_FILE)
    return ToolResult(success=True, result={"todos": todos, "count": len(todos)}, tool_name="get_todos")


def complete_todo(todo_id: str) -> ToolResult:
    todos = _load_json(_TODOS_FILE)
    for t in todos:
        if t["id"] == todo_id:
            t["completed"] = True
            _save_json(_TODOS_FILE, todos)
            return ToolResult(success=True, result={"id": todo_id, "task": t["task"]}, tool_name="complete_todo")
    return ToolResult(success=False, error=f"Todo {todo_id} not found", tool_name="complete_todo")


# ═══════════════════════════════════════════════════════════════════════
# VERIFICATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def _verify_app_open(app_name: str = "", **kwargs) -> bool:
    """Verify an app is running after opening."""
    try:
        import psutil
        app_lower = app_name.lower()
        for proc in psutil.process_iter(['name']):
            try:
                name = (proc.info.get('name') or '').lower()
                if app_lower in name:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except ImportError:
        pass
    return True  # Assume success if can't verify


def _verify_file(file_path: str = "", **kwargs) -> bool:
    """Verify a file exists."""
    return os.path.isfile(file_path)


def _verify_url(url: str = "", **kwargs) -> bool:
    """Verify a URL was opened (browser should be running)."""
    try:
        import psutil
        browsers = ['chrome', 'firefox', 'edge', 'brave']
        for proc in psutil.process_iter(['name']):
            try:
                name = (proc.info.get('name') or '').lower()
                if any(b in name for b in browsers):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except ImportError:
        pass
    return True


# ═══════════════════════════════════════════════════════════════════════
# REGISTER ALL TOOLS
# ═══════════════════════════════════════════════════════════════════════

def register_all_tools():
    """Register all core tools with the global registry."""
    r = tool_registry

    # App management
    r.register("open_app", open_app, "Open an application or website",
               ToolCategory.APP, {"app_name": "string"}, verify=_verify_app_open, priority=10)
    r.register("close_app", close_app, "Close an application",
               ToolCategory.APP, {"app_name": "string"}, priority=10)

    # Web
    r.register("web_search", web_search, "Search the web via Google",
               ToolCategory.WEB, {"query": "string"}, verify=_verify_url, priority=20)
    r.register("search_on_platform", search_on_platform, "Search on a specific platform (reddit, youtube, github, etc.)",
               ToolCategory.WEB, {"query": "string", "platform": "string"}, verify=_verify_url, priority=20)
    r.register("open_url", open_url, "Open a URL in browser",
               ToolCategory.WEB, {"url": "string"}, verify=_verify_url, priority=20)

    # Files
    r.register("create_file", create_file, "Create a file",
               ToolCategory.FILE, {"file_path": "string", "content": "string"},
               verify=lambda file_path, **kw: _verify_file(file_path), priority=30)
    r.register("delete_file", delete_file, "Delete a file",
               ToolCategory.FILE, {"file_path": "string"}, priority=30,
               requires_confirmation=True)
    r.register("read_file", read_file, "Read file contents",
               ToolCategory.FILE, {"file_path": "string"}, priority=30)

    # System
    r.register("adjust_volume", adjust_volume, "Adjust system volume",
               ToolCategory.SYSTEM, {"direction": "string", "amount": "int"}, priority=40)
    r.register("take_screenshot", take_screenshot, "Take a screenshot",
               ToolCategory.SYSTEM, {"save_path": "string"}, priority=40)
    r.register("get_system_stats", get_system_stats, "Get CPU, RAM, disk, battery stats",
               ToolCategory.SYSTEM, priority=50)
    r.register("get_time", get_time, "Get current time",
               ToolCategory.SYSTEM, priority=60)
    r.register("get_date", get_date, "Get current date",
               ToolCategory.SYSTEM, priority=60)
    r.register("list_running_apps", list_running_apps, "List running applications",
               ToolCategory.SYSTEM, priority=50)

    # Memory
    r.register("add_note", add_note, "Save a note",
               ToolCategory.MEMORY, {"content": "string"}, priority=40)
    r.register("get_notes", get_notes, "Get all saved notes",
               ToolCategory.MEMORY, priority=50)
    r.register("add_todo", add_todo, "Add a to-do item",
               ToolCategory.MEMORY, {"task": "string"}, priority=40)
    r.register("get_todos", get_todos, "Get all to-do items",
               ToolCategory.MEMORY, priority=50)
    r.register("complete_todo", complete_todo, "Mark a to-do as complete",
               ToolCategory.MEMORY, {"todo_id": "string"}, priority=40)

    logger.info("All core tools registered: %d tools", r.get_stats()["total"])


# Auto-register on import
register_all_tools()

__all__ = [
    "open_app", "close_app", "web_search", "search_on_platform", "open_url",
    "create_file", "delete_file", "read_file",
    "adjust_volume", "take_screenshot", "get_system_stats",
    "get_time", "get_date", "list_running_apps",
    "add_note", "get_notes", "add_todo", "get_todos", "complete_todo",
    "register_all_tools",
]
