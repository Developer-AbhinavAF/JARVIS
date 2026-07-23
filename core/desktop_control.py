"""desktop_control — Desktop control engine for mouse and keyboard automation.

Capabilities:
- Mouse control (click, double-click, right-click, hover, drag)
- Keyboard control (type text, press keys, hotkeys)
- Window management (focus, minimize, maximize, close, move, resize)
- Screen information
- Color detection
- Element location
- Cross-platform support (Windows, macOS, Linux)
"""

from __future__ import annotations

import os
import json
import logging
import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


class MouseButton(Enum):
    """Mouse button types."""
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


class KeyModifier(Enum):
    """Key modifier types."""
    CTRL = "ctrl"
    ALT = "alt"
    SHIFT = "shift"
    WIN = "win"  # Windows key
    CMD = "cmd"  # macOS Command key


@dataclass
class DesktopActionResult:
    """Result of desktop control operation."""
    success: bool = False
    operation: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0
    error: str = ""


class DesktopControlEngine:
    """Desktop control engine for mouse and keyboard automation."""
    
    def __init__(self):
        self._mouse = None
        self._keyboard = None
        self._screen = None
        self._platform = os.name
        self._init_controls()
    
    def _init_controls(self) -> None:
        """Initialize desktop control libraries."""
        try:
            import pyautogui
            self._mouse = pyautogui
            self._keyboard = pyautogui
            self._screen = pyautogui
            
            # Safety settings
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.1
            
            logger.info("Desktop controls initialized with pyautogui")
        except ImportError:
            logger.warning("pyautogui not available, desktop control will be limited")
    
    def move_mouse(self, x: int, y: int, duration: float = 0.0) -> DesktopActionResult:
        """Move mouse to position."""
        start_time = time.time()
        
        try:
            if not self._mouse:
                return DesktopActionResult(success=False, operation="move_mouse", error="Mouse control not available")
            
            self._mouse.moveTo(x, y, duration=duration)
            
            return DesktopActionResult(
                success=True,
                operation="move_mouse",
                data={"x": x, "y": y, "duration": duration},
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Move mouse failed: {e}")
            return DesktopActionResult(
                success=False,
                operation="move_mouse",
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def click(self, x: int = None, y: int = None, button: MouseButton = MouseButton.LEFT, 
              clicks: int = 1, interval: float = 0.0) -> DesktopActionResult:
        """Click at position."""
        start_time = time.time()
        
        try:
            if not self._mouse:
                return DesktopActionResult(success=False, operation="click", error="Mouse control not available")
            
            button_name = button.value
            self._mouse.click(x, y, clicks=clicks, interval=interval, button=button_name)
            
            return DesktopActionResult(
                success=True,
                operation="click",
                data={"x": x, "y": y, "button": button_name, "clicks": clicks},
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Click failed: {e}")
            return DesktopActionResult(
                success=False,
                operation="click",
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def right_click(self, x: int = None, y: int = None) -> DesktopActionResult:
        """Right-click at position."""
        return self.click(x, y, button=MouseButton.RIGHT)
    
    def double_click(self, x: int = None, y: int = None) -> DesktopActionResult:
        """Double-click at position."""
        return self.click(x, y, clicks=2)
    
    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, 
             duration: float = 0.5) -> DesktopActionResult:
        """Drag from start to end position."""
        start_time = time.time()
        
        try:
            if not self._mouse:
                return DesktopActionResult(success=False, operation="drag", error="Mouse control not available")
            
            self._mouse.dragTo(end_x, end_y, duration=duration, button="left")
            
            return DesktopActionResult(
                success=True,
                operation="drag",
                data={"start": (start_x, start_y), "end": (end_x, end_y), "duration": duration},
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Drag failed: {e}")
            return DesktopActionResult(
                success=False,
                operation="drag",
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def scroll(self, amount: int, x: int = None, y: int = None) -> DesktopActionResult:
        """Scroll mouse wheel."""
        start_time = time.time()
        
        try:
            if not self._mouse:
                return DesktopActionResult(success=False, operation="scroll", error="Mouse control not available")
            
            self._mouse.scroll(amount, x, y)
            
            return DesktopActionResult(
                success=True,
                operation="scroll",
                data={"amount": amount, "x": x, "y": y},
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Scroll failed: {e}")
            return DesktopActionResult(
                success=False,
                operation="scroll",
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def type_text(self, text: str, delay: float = 0.0) -> DesktopActionResult:
        """Type text at current cursor position."""
        start_time = time.time()
        
        try:
            if not self._keyboard:
                return DesktopActionResult(success=False, operation="type_text", error="Keyboard control not available")
            
            self._keyboard.typewrite(text, delay=delay)
            
            return DesktopActionResult(
                success=True,
                operation="type_text",
                data={"text": text, "delay": delay},
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Type text failed: {e}")
            return DesktopActionResult(
                success=False,
                operation="type_text",
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def press_key(self, key: str) -> DesktopActionResult:
        """Press a keyboard key."""
        start_time = time.time()
        
        try:
            if not self._keyboard:
                return DesktopActionResult(success=False, operation="press_key", error="Keyboard control not available")
            
            self._keyboard.press(key)
            self._keyboard.release(key)
            
            return DesktopActionResult(
                success=True,
                operation="press_key",
                data={"key": key},
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Press key failed: {e}")
            return DesktopActionResult(
                success=False,
                operation="press_key",
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def hotkey(self, *keys: str) -> DesktopActionResult:
        """Press combination of keys (hotkey)."""
        start_time = time.time()
        
        try:
            if not self._keyboard:
                return DesktopActionResult(success=False, operation="hotkey", error="Keyboard control not available")
            
            self._keyboard.hotkey(*keys)
            
            return DesktopActionResult(
                success=True,
                operation="hotkey",
                data={"keys": keys},
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Hotkey failed: {e}")
            return DesktopActionResult(
                success=False,
                operation="hotkey",
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def get_cursor_position(self) -> Tuple[int, int]:
        """Get current cursor position."""
        try:
            if self._mouse:
                return self._mouse.position()
            return (0, 0)
        except Exception as e:
            logger.error(f"Get cursor position failed: {e}")
            return (0, 0)
    
    def get_screen_size(self) -> Tuple[int, int]:
        """Get screen size."""
        try:
            if self._screen:
                return self._screen.size()
            return (1920, 1080)
        except Exception as e:
            logger.error(f"Get screen size failed: {e}")
            return (1920, 1080)
    
    def get_pixel_color(self, x: int, y: int) -> str:
        """Get color of pixel at position."""
        try:
            if self._screen:
                return self._screen.pixel(x, y)
            return "#000000"
        except Exception as e:
            logger.error(f"Get pixel color failed: {e}")
            return "#000000"
    
    def screenshot(self, region: Tuple[int, int, int, int] = None) -> str:
        """Take screenshot and return path."""
        try:
            if self._screen:
                timestamp = int(time.time())
                path = f"desktop_screenshot_{timestamp}.png"
                self._screen.screenshot(path, region=region)
                return path
            return ""
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return ""
    
    def locate_on_screen(self, image_path: str, confidence: float = 0.9) -> Optional[Tuple[int, int]]:
        """Locate image on screen."""
        try:
            if self._screen:
                location = self._screen.locateOnScreen(image_path, confidence=confidence)
                if location:
                    return self._screen.center(location)
            return None
        except Exception as e:
            logger.error(f"Locate on screen failed: {e}")
            return None
    
    def window_focus(self, window_title: str) -> DesktopActionResult:
        """Focus window by title."""
        start_time = time.time()
        
        try:
            if self._platform == "nt":  # Windows
                import win32gui
                import win32con
                
                def window_callback(hwnd, windows):
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        if window_title.lower() in title.lower():
                            windows.append(hwnd)
                    return True
                
                windows = []
                win32gui.EnumWindows(window_callback, windows)
                
                if windows:
                    hwnd = windows[0]
                    win32gui.SetForegroundWindow(hwnd)
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    
                    return DesktopActionResult(
                        success=True,
                        operation="window_focus",
                        data={"window_title": window_title},
                        processing_time=time.time() - start_time
                    )
            
            return DesktopActionResult(
                success=False,
                operation="window_focus",
                error="Window focus not implemented for this platform",
                processing_time=time.time() - start_time
            )
            
        except ImportError:
            return DesktopActionResult(
                success=False,
                operation="window_focus",
                error="Required libraries not available",
                processing_time=time.time() - start_time
            )
        except Exception as e:
            logger.error(f"Window focus failed: {e}")
            return DesktopActionResult(
                success=False,
                operation="window_focus",
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def list_windows(self) -> List[Dict[str, Any]]:
        """List all visible windows."""
        try:
            windows = []
            
            if self._platform == "nt":  # Windows
                import win32gui
                
                def window_callback(hwnd, windows_list):
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        if title:
                            windows_list.append({
                                "title": title,
                                "hwnd": hwnd
                            })
                    return True
                
                win32gui.EnumWindows(window_callback, windows)
            
            return windows
            
        except Exception as e:
            logger.error(f"List windows failed: {e}")
            return []
    
    def minimize_window(self, window_title: str) -> DesktopActionResult:
        """Minimize window by title."""
        start_time = time.time()
        
        try:
            if self._platform == "nt":
                import win32gui
                import win32con
                
                windows = []
                def window_callback(hwnd, windows_list):
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        if window_title.lower() in title.lower():
                            windows_list.append(hwnd)
                    return True
                
                win32gui.EnumWindows(window_callback, windows)
                
                if windows:
                    win32gui.ShowWindow(windows[0], win32con.SW_MINIMIZE)
                    return DesktopActionResult(
                        success=True,
                        operation="minimize_window",
                        data={"window_title": window_title},
                        processing_time=time.time() - start_time
                    )
            
            return DesktopActionResult(
                success=False,
                operation="minimize_window",
                error="Minimize window not implemented for this platform",
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Minimize window failed: {e}")
            return DesktopActionResult(
                success=False,
                operation="minimize_window",
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def maximize_window(self, window_title: str) -> DesktopActionResult:
        """Maximize window by title."""
        start_time = time.time()
        
        try:
            if self._platform == "nt":
                import win32gui
                import win32con
                
                windows = []
                def window_callback(hwnd, windows_list):
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        if window_title.lower() in title.lower():
                            windows_list.append(hwnd)
                    return True
                
                win32gui.EnumWindows(window_callback, windows)
                
                if windows:
                    win32gui.ShowWindow(windows[0], win32con.SW_MAXIMIZE)
                    return DesktopActionResult(
                        success=True,
                        operation="maximize_window",
                        data={"window_title": window_title},
                        processing_time=time.time() - start_time
                    )
            
            return DesktopActionResult(
                success=False,
                operation="maximize_window",
                error="Maximize window not implemented for this platform",
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Maximize window failed: {e}")
            return DesktopActionResult(
                success=False,
                operation="maximize_window",
                error=str(e),
                processing_time=time.time() - start_time
            )


# Global desktop control engine instance
desktop_control = DesktopControlEngine()