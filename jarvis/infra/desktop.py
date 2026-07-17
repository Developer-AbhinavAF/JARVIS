"""Desktop Intelligence — Understands what the user is doing.

Detects coding sessions, study sessions, gaming, research, meetings, etc.
from active window titles and application combinations.
"""

from __future__ import annotations

import re
import time
import logging
import threading
from typing import Any
from dataclasses import dataclass, field
from enum import Enum

from .events import EventBus, EventType, event_bus

logger = logging.getLogger(__name__)


class SessionType(Enum):
    CODING = "coding"
    STUDY = "study"
    GAMING = "gaming"
    RESEARCH = "research"
    MEETING = "meeting"
    BROWSING = "browsing"
    MOVIE = "movie"
    MUSIC = "music"
    WRITING = "writing"
    DESIGN = "design"
    TERMINAL = "terminal"
    COMMUNICATION = "communication"
    UNKNOWN = "unknown"


@dataclass
class ActiveWindow:
    """Information about the currently active window."""
    title: str = ""
    app_name: str = ""
    process_name: str = ""
    timestamp: float = field(default_factory=time.time)

    @property
    def is_empty(self) -> bool:
        return not self.title and not self.app_name


@dataclass
class DesktopSession:
    """Detected user session."""
    session_type: SessionType = SessionType.UNKNOWN
    confidence: float = 0.0
    active_windows: list[ActiveWindow] = field(default_factory=list)
    applications: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    started_at: float = field(default_factory=time.time)


# Application → Session type mapping
_APP_SESSION_MAP: dict[str, SessionType] = {
    # Coding
    "code": SessionType.CODING, "visual studio code": SessionType.CODING,
    "pycharm": SessionType.CODING, "intellij": SessionType.CODING,
    "sublime text": SessionType.CODING, "vim": SessionType.CODING,
    "neovim": SessionType.CODING, "android studio": SessionType.CODING,
    "cursor": SessionType.CODING, "webstorm": SessionType.CODING,
    # Terminal
    "terminal": SessionType.TERMINAL, "powershell": SessionType.TERMINAL,
    "cmd": SessionType.TERMINAL, "wt": SessionType.TERMINAL,
    "iterm": SessionType.TERMINAL, "alacritty": SessionType.TERMINAL,
    "hyper": SessionType.TERMINAL, "git bash": SessionType.TERMINAL,
    # Study
    "notion": SessionType.STUDY, "obsidian": SessionType.STUDY,
    "anki": SessionType.STUDY, "zotero": SessionType.STUDY,
    "mendeley": SessionType.STUDY, "evernote": SessionType.STUDY,
    "onenote": SessionType.STUDY,
    # Research/Browsing
    "chrome": SessionType.BROWSING, "firefox": SessionType.BROWSING,
    "edge": SessionType.BROWSING, "brave": SessionType.BROWSING,
    "safari": SessionType.BROWSING, "opera": SessionType.BROWSING,
    "arc": SessionType.BROWSING,
    # Gaming
    "steam": SessionType.GAMING, "epic games": SessionType.GAMING,
    "discord": SessionType.COMMUNICATION, "battle.net": SessionType.GAMING,
    "gog": SessionType.GAMING,
    # Communication
    "slack": SessionType.COMMUNICATION, "teams": SessionType.MEETING,
    "zoom": SessionType.MEETING, "meet": SessionType.MEETING,
    "whatsapp": SessionType.COMMUNICATION, "telegram": SessionType.COMMUNICATION,
    "signal": SessionType.COMMUNICATION,
    # Media
    "spotify": SessionType.MUSIC, "vlc": SessionType.MOVIE,
    "netflix": SessionType.MOVIE, "youtube": SessionType.MOVIE,
    "prime video": SessionType.MOVIE, "potplayer": SessionType.MOVIE,
    # Writing
    "word": SessionType.WRITING, "pages": SessionType.WRITING,
    "typora": SessionType.WRITING, "剪映": SessionType.DESIGN,
    # Design
    "figma": SessionType.DESIGN, "photoshop": SessionType.DESIGN,
    "illustrator": SessionType.DESIGN, "blender": SessionType.DESIGN,
    "canva": SessionType.DESIGN, "sketch": SessionType.DESIGN,
}

# Title keyword patterns for more specific detection
_TITLE_PATTERNS: dict[re.Pattern, SessionType] = {
    re.compile(r'\bgithub\.com\b|\bgit\b.*\bcommit\b|\bpull request\b'): SessionType.CODING,
    re.compile(r'\bstackoverflow\b|\bdocs\.\b|\bapi\s*ref\b|\bman\s*page\b'): SessionType.RESEARCH,
    re.compile(r'\blecture\b|\bchapter\b|\bsyllabus\b|\bexam\b|\bncert\b'): SessionType.STUDY,
    re.compile(r'\bmeeting\b|\bstandup\b|\bsprint\b|\bretro\b'): SessionType.MEETING,
    re.compile(r'\bgitHub\b|\bpull request\b|\bmerge\b'): SessionType.CODING,
}

# Session combinations
_COMBO_RULES: list[tuple[set[str], SessionType]] = [
    ({"code", "terminal", "github"}, SessionType.CODING),
    ({"chrome", "notion"}, SessionType.STUDY),
    ({"steam", "discord"}, SessionType.GAMING),
    ({"chrome", "vscode"}, SessionType.CODING),
    ({"chrome", "github"}, SessionType.CODING),
]


class DesktopIntelligence:
    """Detects user sessions from active windows.

    Usage:
        di = DesktopIntelligence()
        di.start()
        session = di.current_session()
        print(session.session_type)  # SessionType.CODING
    """

    def __init__(self, bus: EventBus | None = None, poll_interval: float = 3.0):
        self._bus = bus or event_bus
        self._poll_interval = poll_interval
        self._running = False
        self._thread: threading.Thread | None = None
        self._current = DesktopSession()
        self._history: list[DesktopSession] = []
        self._lock = threading.Lock()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="desktop-intel")
        self._thread.start()
        self._detect_once()
        logger.info("DesktopIntelligence started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)

    def current_session(self) -> DesktopSession:
        with self._lock:
            return self._current

    def get_history(self, limit: int = 10) -> list[DesktopSession]:
        with self._lock:
            return list(self._history[-limit:])

    def get_active_windows(self) -> list[ActiveWindow]:
        windows = self._get_windows()
        return windows

    def _poll_loop(self):
        while self._running:
            self._detect_once()
            time.sleep(self._poll_interval)

    def _detect_once(self):
        windows = self._get_windows()
        apps = list({w.app_name.lower() for w in windows if w.app_name})

        session_type, confidence = self._classify(apps, windows)

        new_session = DesktopSession(
            session_type=session_type,
            confidence=confidence,
            active_windows=windows,
            applications=apps,
        )

        with self._lock:
            old_type = self._current.session_type
            self._current = new_session

            if session_type != old_type:
                self._history.append(new_session)
                if len(self._history) > 100:
                    self._history = self._history[-100:]
                self._bus.emit(EventType.SESSION_CHANGED, source="desktop", data={
                    "session_type": session_type.value,
                    "applications": apps,
                })

    def _classify(self, apps: list[str], windows: list[ActiveWindow]) -> tuple[SessionType, float]:
        if not apps:
            return SessionType.UNKNOWN, 0.0

        # Score each session type
        scores: dict[SessionType, float] = {}

        # App-based scoring
        for app in apps:
            for pattern, stype in _APP_SESSION_MAP.items():
                if pattern in app:
                    scores[stype] = scores.get(stype, 0) + 0.6

        # Title-based scoring
        for win in windows:
            for pattern, stype in _TITLE_PATTERNS.items():
                if pattern.search(win.title):
                    scores[stype] = scores.get(stype, 0) + 0.3

        # Combo scoring
        app_set = set(apps)
        for combo, stype in _COMBO_RULES:
            if combo.issubset(app_set):
                scores[stype] = scores.get(stype, 0) + 0.5

        if not scores:
            return SessionType.UNKNOWN, 0.0

        best = max(scores.items(), key=lambda x: x[1])
        return best[0], min(best[1], 1.0)

    def _get_windows(self) -> list[ActiveWindow]:
        """Get active window information using platform APIs."""
        windows: list[ActiveWindow] = []

        # Try pygetwindow first (cross-platform, simpler)
        try:
            import pygetwindow as gw
            for w in gw.getAllWindows():
                if w.visible and w.title:
                    app_name = w.title.split(" - ")[-1].split(" — ")[-1].strip()
                    if len(app_name) > 40:
                        app_name = app_name[:40]
                    windows.append(ActiveWindow(
                        title=w.title,
                        app_name=app_name,
                        process_name=app_name.lower(),
                    ))
            if windows:
                return windows
        except ImportError:
            pass
        except Exception:
            logger.debug("pygetwindow enumeration failed")

        # Fallback: win32gui
        try:
            import win32gui
            import win32process
            import psutil

            def enum_callback(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title:
                        # Get process name from PID
                        process_name = ""
                        try:
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            proc = psutil.Process(pid)
                            process_name = proc.name()
                        except Exception:
                            pass
                        app_name = title.split(" - ")[-1].split(" — ")[-1].strip()
                        if len(app_name) > 40:
                            app_name = app_name[:40]
                        windows.append(ActiveWindow(
                            title=title,
                            app_name=app_name,
                            process_name=process_name,
                        ))
                return True

            win32gui.EnumWindows(enum_callback, None)
        except ImportError:
            pass
        except Exception:
            logger.debug("win32gui EnumWindows failed")

        return windows


# Global instance
desktop_intelligence = DesktopIntelligence()

__all__ = ["DesktopIntelligence", "DesktopSession", "SessionType", "ActiveWindow", "desktop_intelligence"]
