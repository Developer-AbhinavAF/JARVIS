"""Window Manager — Detect and manage desktop windows.

Understand every window: title, application, state, size, position,
tabs, controls, and current activity.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

try:
    import pygetwindow as gw
    HAS_GW = True
except ImportError:
    HAS_GW = False

try:
    import win32gui
    import win32process
    import psutil
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


# ════════════════════════════════════════════════════════════════════
# WINDOW MODEL
# ════════════════════════════════════════════════════════════════════

@dataclass
class WindowInfo:
    """Information about a single window."""
    hwnd: int = 0
    title: str = ""
    app_name: str = ""
    process_name: str = ""
    process_id: int = 0

    # Geometry
    left: int = 0
    top: int = 0
    width: int = 0
    height: int = 0

    # State
    is_focused: bool = False
    is_minimized: bool = False
    is_maximized: bool = False
    is_visible: bool = True
    is_topmost: bool = False

    # Classification
    window_type: str = "normal"   # normal, dialog, popup, toolbar, tooltip
    category: str = "unknown"     # browser, editor, terminal, media, system, etc.
    confidence: float = 0.0       # Detection confidence (0-1)

    # Metadata
    class_name: str = ""
    executable: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "hwnd": self.hwnd,
            "title": self.title[:100],
            "app": self.app_name,
            "process": self.process_name,
            "pid": self.process_id,
            "size": f"{self.width}x{self.height}",
            "position": f"({self.left},{self.top})",
            "focused": self.is_focused,
            "minimized": self.is_minimized,
            "maximized": self.is_maximized,
            "visible": self.is_visible,
            "topmost": self.is_topmost,
            "type": self.window_type,
            "category": self.category,
            "confidence": round(self.confidence, 2),
            "class": self.class_name,
            "executable": self.executable,
        }


# ════════════════════════════════════════════════════════════════════
# APP CATEGORIES
# ════════════════════════════════════════════════════════════════════

_APP_CATEGORIES: dict[str, str] = {
    # Browsers
    "chrome": "browser", "firefox": "browser", "edge": "browser",
    "brave": "browser", "opera": "browser", "vivaldi": "browser",
    # Editors
    "code": "editor", "cursor": "editor", "sublime": "editor",
    "notepad++": "editor", "atom": "editor", "vim": "editor",
    "pycharm": "editor", "intellij": "editor", "android studio": "editor",
    "visual studio": "editor", "eclipse": "editor",
    # Terminals
    "terminal": "terminal", "cmd": "terminal", "powershell": "terminal",
    "wt": "terminal", "conhost": "terminal", "hyper": "terminal",
    "git bash": "terminal", "wsl": "terminal",
    # Media
    "spotify": "media", "vlc": "media", "itunes": "media",
    "youtube": "media", "discord": "media", "teamspeak": "media",
    # Communication
    "slack": "communication", "telegram": "communication",
    "whatsapp": "communication", "zoom": "communication",
    "teams": "communication", "skype": "communication",
    # System
    "explorer": "system", "file explorer": "system",
    "settings": "system", "task manager": "system",
    "control panel": "system", "registry": "system",
    # Development
    "docker": "development", "postman": "development",
    "git": "development", "github desktop": "development",
    # Gaming
    "steam": "gaming", "epic games": "gaming",
    "battle.net": "gaming", "origin": "gaming",
}

_WINDOW_TYPE_KEYWORDS: dict[str, list[str]] = {
    "dialog": ["dialog", "confirm", "alert", "save as", "open file", "browse"],
    "popup": ["popup", "notification", "toast", "reminder"],
    "toolbar": ["toolbar", "properties", "options", "preferences"],
    "tooltip": ["tooltip", "tip"],
}


# ════════════════════════════════════════════════════════════════════
# WINDOW MANAGER
# ════════════════════════════════════════════════════════════════════

class WindowManager:
    """Detects and manages all desktop windows.

    Builds a complete picture of the desktop environment.
    """

    def __init__(self) -> None:
        self._windows: list[WindowInfo] = []
        self._focused_window: WindowInfo | None = None
        self._scan_count: int = 0

    def scan(self) -> list[WindowInfo]:
        """Scan all visible windows and build window list."""
        t0 = time.perf_counter()
        self._windows.clear()

        if HAS_GW:
            try:
                all_windows = gw.getAllWindows()
                for w in all_windows:
                    if not w.title or not w.visible:
                        continue
                    # Try to get app from process name via win32
                    proc_name = ""
                    pid = 0
                    confidence = 0.5  # Default confidence
                    if HAS_WIN32:
                        try:
                            _, pid = win32gui.GetWindowThreadProcessId(w._hWnd) if hasattr(w, '_hWnd') else (0, 0)
                            if pid:
                                import psutil as _psutil
                                proc_name = _psutil.Process(pid).name().replace('.exe', '')
                                confidence = 0.9  # High confidence when we have process name
                        except Exception:
                            pass
                    else:
                        confidence = 0.6  # Medium confidence from title extraction

                    info = WindowInfo(
                        hwnd=w._hWnd if hasattr(w, '_hWnd') else 0,
                        title=w.title,
                        app_name=proc_name or self._extract_app_name(w.title),
                        process_name=proc_name,
                        process_id=pid,
                        left=w.left, top=w.top,
                        width=w.width, height=w.height,
                        is_focused=w.isActive if hasattr(w, 'isActive') else False,
                        is_minimized=w.isMinimized,
                        is_maximized=w.isMaximized,
                        is_visible=w.visible,
                        confidence=confidence,
                    )
                    info.category = self._match_category(info.app_name, info.title)
                    info.window_type = self._classify_window_type(w.title)
                    self._windows.append(info)

                    if info.is_focused:
                        self._focused_window = info

            except Exception as e:
                logger.debug("pygetwindow scan failed: %s", e)

        # Fallback to win32gui
        if not self._windows and HAS_WIN32:
            self._scan_win32()

        self._scan_count += 1
        return list(self._windows)

    @staticmethod
    def _match_category(app_name: str, title: str = "") -> str:
        """Match category from app name or title using multiple strategies."""
        # Direct match on process name
        cat = _APP_CATEGORIES.get(app_name.lower())
        if cat:
            return cat
        # Check if any category key is contained in the app name or title
        title_lower = title.lower()
        app_lower = app_name.lower()
        for key, category in _APP_CATEGORIES.items():
            if key in app_lower or key in title_lower:
                return category
        return "unknown"

    def get_focused_window(self) -> WindowInfo | None:
        """Get the currently focused window."""
        if HAS_WIN32:
            try:
                hwnd = win32gui.GetForegroundWindow()
                title = win32gui.GetWindowText(hwnd)
                if title:
                    for w in self._windows:
                        if w.hwnd == hwnd:
                            return w
                    # Create info for unknown window
                    info = WindowInfo(
                        hwnd=hwnd, title=title,
                        app_name=self._extract_app_name(title),
                        is_focused=True,
                    )
                    info.category = self._match_category(info.app_name, title)
                    return info
            except Exception:
                pass
        return self._focused_window

    def get_window_by_title(self, title: str) -> WindowInfo | None:
        """Find a window by title (partial match)."""
        title_lower = title.lower()
        for w in self._windows:
            if title_lower in w.title.lower():
                return w
        return None

    def get_windows_by_category(self, category: str) -> list[WindowInfo]:
        """Get all windows of a specific category."""
        return [w for w in self._windows if w.category == category]

    def get_windows_by_app(self, app_name: str) -> list[WindowInfo]:
        """Get all windows for a specific application."""
        return [w for w in self._windows if w.app_name.lower() == app_name.lower()]

    def get_window_count(self) -> int:
        return len(self._windows)

    def get_desktop_summary(self) -> dict[str, Any]:
        """Get a summary of the current desktop state."""
        focused = self.get_focused_window()
        categories: dict[str, int] = {}
        for w in self._windows:
            categories[w.category] = categories.get(w.category, 0) + 1

        return {
            "total_windows": len(self._windows),
            "focused": focused.title if focused else "None",
            "focused_app": focused.app_name if focused else "None",
            "categories": categories,
            "visible_windows": [w.title[:50] for w in self._windows if not w.is_minimized][:10],
        }

    def get_scene_graph(self) -> dict[str, Any]:
        """Build a structured scene graph of the desktop.

        Returns a hierarchical representation of the desktop environment
        with all windows, their states, and relationships.
        """
        focused = self.get_focused_window()
        categories: dict[str, list[dict]] = {}
        apps: dict[str, list[dict]] = {}

        for w in self._windows:
            w_dict = w.to_dict()
            # Group by category
            cat = w.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(w_dict)
            # Group by app
            app = w.app_name or "unknown"
            if app not in apps:
                apps[app] = []
            apps[app].append(w_dict)

        return {
            "focused_window": focused.to_dict() if focused else None,
            "total_windows": len(self._windows),
            "visible_windows": len([w for w in self._windows if w.is_visible and not w.is_minimized]),
            "minimized_windows": len([w for w in self._windows if w.is_minimized]),
            "categories": {cat: len(wins) for cat, wins in categories.items()},
            "apps": {app: len(wins) for app, wins in apps.items()},
            "category_details": categories,
            "app_details": apps,
            "z_order": [
                {"hwnd": w.hwnd, "title": w.title[:50], "app": w.app_name}
                for w in self._windows if w.is_visible
            ],
        }

    # ── Private Methods ──

    def _scan_win32(self) -> None:
        """Fallback scan using win32gui."""
        def enum_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    info = WindowInfo(
                        hwnd=hwnd, title=title,
                        app_name=self._extract_app_name(title),
                        is_focused=(hwnd == win32gui.GetForegroundWindow()),
                    )
                    info.category = self._match_category(info.app_name, title)
                    # Get window rect
                    try:
                        rect = win32gui.GetWindowRect(hwnd)
                        info.left, info.top = rect[0], rect[1]
                        info.width = rect[2] - rect[0]
                        info.height = rect[3] - rect[1]
                    except Exception:
                        pass
                    self._windows.append(info)
            return True

        try:
            win32gui.EnumWindows(enum_callback, None)
        except Exception as e:
            logger.debug("win32gui EnumWindows failed: %s", e)

    @staticmethod
    def _extract_app_name(title: str) -> str:
        """Extract application name from window title."""
        # Common patterns: "Page - App" or "App - Page" or "App"
        for sep in [" - ", " — ", " | ", " :: ", ": "]:
            if sep in title:
                parts = title.split(sep)
                # Usually the app name is the last or first part
                for part in [parts[-1], parts[0]]:
                    part = part.strip()
                    if len(part) < 40:
                        return part
        # Just use the full title if short
        if len(title) < 40:
            return title
        return title[:40]

    @staticmethod
    def _classify_window_type(title: str) -> str:
        title_lower = title.lower()
        for wtype, keywords in _WINDOW_TYPE_KEYWORDS.items():
            if any(kw in title_lower for kw in keywords):
                return wtype
        return "normal"

    def get_stats(self) -> dict[str, Any]:
        return {
            "scan_count": self._scan_count,
            "windows_found": len(self._windows),
            "has_pygetwindow": HAS_GW,
            "has_win32": HAS_WIN32,
        }


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

window_manager = WindowManager()
