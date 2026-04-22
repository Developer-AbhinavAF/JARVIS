"""jarvis.system_control

PC control automation for JARVIS.

Mouse, keyboard, window management, volume, brightness, and system power controls.
Lightweight implementation using pyautogui and native Windows APIs.
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import threading
import time
from pathlib import Path
from typing import Literal

from jarvis import config

logger = logging.getLogger(__name__)

# Platform check
IS_WINDOWS = platform.system().lower() == "windows"
IS_LINUX = platform.system().lower() == "linux"

# Try to import pyautogui for mouse/keyboard control
try:
    import pyautogui

    pyautogui.FAILSAFE = True  # Move mouse to corner to abort
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False
    logger.warning("pyautogui not available - mouse/keyboard control disabled")

# Try to import keyboard for global hotkeys
try:
    import keyboard as keyboard_lib

    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False
    logger.warning("keyboard library not available - hotkey control disabled")

# Try to import psutil for process management
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# Try to import PIL for screenshots
try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def _ensure_pyautogui() -> bool:
    """Check if pyautogui is available."""
    if not HAS_PYAUTOGUI:
        return False
    return True


def mouse_control(action: str, x: int = 0, y: int = 0) -> str:
    """Control mouse movement and clicks.
    
    Args:
        action: move, click, double_click, right_click, drag
        x: X coordinate (screen pixels)
        y: Y coordinate (screen pixels)
    """
    if not _ensure_pyautogui():
        return "Mouse control not available - pyautogui not installed."

    try:
        action = action.lower().strip()

        if action == "move":
            pyautogui.moveTo(x, y, duration=config.MOUSE_SPEED)
            return f"Mouse moved to {x}, {y}."

        elif action == "click":
            pyautogui.click(x, y)
            return f"Clicked at {x}, {y}."

        elif action == "double_click":
            pyautogui.doubleClick(x, y)
            return f"Double-clicked at {x}, {y}."

        elif action == "right_click":
            pyautogui.rightClick(x, y)
            return f"Right-clicked at {x}, {y}."

        elif action == "drag":
            current_x, current_y = pyautogui.position()
            pyautogui.dragTo(x, y, duration=config.MOUSE_SPEED)
            return f"Dragged from {current_x}, {current_y} to {x}, {y}."

        elif action == "scroll_up":
            pyautogui.scroll(3, x, y)
            return "Scrolled up."

        elif action == "scroll_down":
            pyautogui.scroll(-3, x, y)
            return "Scrolled down."

        else:
            return f"Unknown mouse action: {action}"

    except Exception as e:
        logger.exception("Mouse control failed")
        return f"Mouse control error: {str(e)}"


def type_text(text: str) -> str:
    """Type text at current cursor position.
    
    Args:
        text: Text to type
    """
    if not _ensure_pyautogui():
        return "Typing not available - pyautogui not installed."

    if not text:
        return "No text provided."

    try:
        # Small delay to ensure window is focused
        import time
        time.sleep(0.1)
        
        # Type the text
        pyautogui.typewrite(text, interval=config.TYPING_INTERVAL)
        return f"Typed: {text[:50]}{'...' if len(text) > 50 else ''}"
    except Exception as e:
        logger.exception("Typing failed")
        return f"Typing error: {str(e)}"


def hotkey(keys: list[str]) -> str:
    """Press a hotkey combination.
    
    Args:
        keys: List of keys like ['ctrl', 'c'] or ['alt', 'tab']
    """
    if not _ensure_pyautogui():
        return "Hotkeys not available - pyautogui not installed."

    if not keys or len(keys) < 1:
        return "No keys provided."

    try:
        key_string = "+".join(keys)
        pyautogui.hotkey(*keys)
        return f"Pressed: {key_string}"
    except Exception as e:
        logger.exception("Hotkey failed")
        return f"Hotkey error: {str(e)}"


def press_key(key: str, presses: int = 1) -> str:
    """Press a single key multiple times.
    
    Args:
        key: Key name (e.g., 'enter', 'tab', 'space', 'f5')
        presses: Number of times to press
    """
    if not _ensure_pyautogui():
        return "Key presses not available - pyautogui not installed."

    try:
        pyautogui.press(key, presses=presses)
        return f"Pressed {key} {presses} time(s)."
    except Exception as e:
        logger.exception("Key press failed")
        return f"Key press error: {str(e)}"


def get_mouse_position() -> str:
    """Get current mouse position."""
    if not _ensure_pyautogui():
        return "Mouse position not available."

    try:
        x, y = pyautogui.position()
        return f"Mouse is at {x}, {y}. Screen size: {pyautogui.size()}."
    except Exception as e:
        logger.exception("Get mouse position failed")
        return f"Error: {str(e)}"


def screenshot(save_path: str | None = None, open_image: bool = True) -> str:
    """Take a screenshot, save it, and optionally open it.
    
    Args:
        save_path: Path to save screenshot (default: config.SCREENSHOT_PATH)
        open_image: Whether to open the screenshot after saving (default: True)
    """
    if not HAS_PIL:
        return "Screenshots not available - PIL not installed."

    if not _ensure_pyautogui():
        return "Screenshots not available - pyautogui not installed."

    try:
        path = save_path or config.SCREENSHOT_PATH
        screenshot_img = pyautogui.screenshot()
        screenshot_img.save(path)
        
        # Open the screenshot with default viewer
        if open_image and os.path.exists(path):
            try:
                os.startfile(path)
            except Exception:
                logger.debug("Could not open screenshot automatically")
        
        return f"Screenshot saved to {path}. Opening now..."
    except Exception as e:
        logger.exception("Screenshot failed")
        return f"Screenshot error: {str(e)}"


def volume_control(action: str, value: int | None = None) -> str:
    """Control system volume.
    
    Args:
        action: set, up, down, mute, unmute
        value: Volume level 0-100 (for 'set' action)
    """
    if not IS_WINDOWS:
        return "Volume control only supported on Windows currently."

    try:
        action = action.lower().strip()

        if action == "mute":
            # Use nircmd or PowerShell
            subprocess.run(["powershell", "-c", "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"], check=False)
            return "Volume muted."

        elif action == "unmute":
            subprocess.run(["powershell", "-c", "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"], check=False)
            return "Volume unmuted."

        elif action == "up":
            for _ in range(5):  # Increase by 5 steps
                subprocess.run(["powershell", "-c", "(New-Object -ComObject WScript.Shell).SendKeys([char]175)"], check=False)
                time.sleep(0.01)
            return "Volume increased."

        elif action == "down":
            for _ in range(5):  # Decrease by 5 steps
                subprocess.run(["powershell", "-c", "(New-Object -ComObject WScript.Shell).SendKeys([char]174)"], check=False)
                time.sleep(0.01)
            return "Volume decreased."

        elif action == "set":
            if value is None:
                return "Volume value required for 'set' action."
            # Use nircmd if available, otherwise use PowerShell approximation
            try:
                # Set volume using Windows CoreAudio API via PowerShell
                ps_script = f"""
                Add-Type -TypeDefinition @'
                using System;
                using System.Runtime.InteropServices;
                public class Volume {{
                    [DllImport("user32.dll")]
                    public static extern int SendMessageW(IntPtr hWnd, int Msg, IntPtr wParam, IntPtr lParam);
                }}
                '@
                # Approximate volume setting
                $shell = New-Object -ComObject WScript.Shell
                for ($i = 0; $i -lt 50; $i++) {{ $shell.SendKeys([char]174) }}
                for ($i = 0; $i -lt {value // 2}; $i++) {{ $shell.SendKeys([char]175) }}
                """
                subprocess.run(["powershell", "-c", ps_script], check=False, capture_output=True)
                return f"Volume set to approximately {value}%."
            except Exception:
                return "Volume setting requires nircmd.exe (install and add to PATH for precise control)."

        else:
            return f"Unknown volume action: {action}"

    except Exception as e:
        logger.exception("Volume control failed")
        return f"Volume control error: {str(e)}"


def brightness_control(action: str, value: int | None = None) -> str:
    """Control screen brightness (Windows only).
    
    Args:
        action: set, up, down
        value: Brightness level 0-100 (for 'set' action)
    """
    if not IS_WINDOWS:
        return "Brightness control only supported on Windows currently."

    try:
        action = action.lower().strip()

        if action == "up":
            subprocess.run(["powershell", "-c", "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness + 10)"], check=False, capture_output=True)
            return "Brightness increased."

        elif action == "down":
            subprocess.run(["powershell", "-c", "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness - 10)"], check=False, capture_output=True)
            return "Brightness decreased."

        elif action == "set" and value is not None:
            subprocess.run(["powershell", "-c", f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {value})"], check=False, capture_output=True)
            return f"Brightness set to {value}%."

        else:
            return f"Unknown brightness action: {action}"

    except Exception as e:
        logger.exception("Brightness control failed")
        return f"Brightness control error: {str(e)} (may require admin privileges)"


def window_control(action: str, title: str | None = None) -> str:
    """Control application windows.
    
    Args:
        action: minimize, maximize, close, focus, list, switch
        title: Window title (for focus/switch action)
    """
    if not IS_WINDOWS:
        return "Window control only supported on Windows currently."

    try:
        action = action.lower().strip()

        if action == "minimize":
            pyautogui.keyDown('win')
            pyautogui.keyDown('down')
            pyautogui.keyUp('down')
            pyautogui.keyUp('win')
            return "Window minimized."

        elif action == "maximize":
            pyautogui.keyDown('win')
            pyautogui.keyDown('up')
            pyautogui.keyUp('up')
            pyautogui.keyUp('win')
            return "Window maximized."

        elif action == "restore":
            pyautogui.keyDown('win')
            pyautogui.keyDown('down')
            pyautogui.keyUp('down')
            pyautogui.keyUp('win')
            return "Window restored."

        elif action == "close":
            pyautogui.keyDown('alt')
            pyautogui.keyDown('f4')
            pyautogui.keyUp('f4')
            pyautogui.keyUp('alt')
            return "Window closed."

        elif action in ["focus", "switch"]:
            if not title:
                # Alt+Tab to switch between windows
                pyautogui.keyDown('alt')
                pyautogui.keyDown('tab')
                pyautogui.keyUp('tab')
                pyautogui.keyUp('alt')
                return "Switched to next window."
            
            # Try to find and focus specific window
            try:
                import ctypes
                from ctypes import wintypes
                
                user32 = ctypes.WinDLL('user32', use_last_error=True)
                
                # EnumWindows callback
                def enum_windows_callback(hwnd, extra):
                    if user32.IsWindowVisible(hwnd):
                        length = user32.GetWindowTextLengthW(hwnd)
                        if length > 0:
                            buffer = ctypes.create_unicode_buffer(length + 1)
                            user32.GetWindowTextW(hwnd, buffer, length + 1)
                            window_title = buffer.value.lower()
                            if title.lower() in window_title:
                                extra.append((hwnd, buffer.value))
                    return True
                
                EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
                callback = EnumWindowsProc(enum_windows_callback)
                
                matching_windows = []
                user32.EnumWindows(callback, ctypes.cast(ctypes.pointer(ctypes.c_int(0)), wintypes.LPARAM))
                
                # Find matching windows by iterating all
                def find_windows():
                    result = []
                    def cb(hwnd, _):
                        if user32.IsWindowVisible(hwnd):
                            length = user32.GetWindowTextLengthW(hwnd)
                            if length > 0:
                                buff = ctypes.create_unicode_buffer(length + 1)
                                user32.GetWindowTextW(hwnd, buff, length + 1)
                                if title.lower() in buff.value.lower():
                                    result.append((hwnd, buff.value))
                        return True
                    EnumWindowsProc(cb)(0, 0)
                    return result
                
                # PowerShell approach as fallback
                script = f'''
                $windows = Get-Process | Where-Object {{ $_.MainWindowTitle -match "{title}" -and $_.MainWindowHandle -ne 0 }} | Select-Object -First 1
                if ($windows) {{
                    $hwnd = $windows.MainWindowHandle
                    Add-Type @"
                    using System;
                    using System.Runtime.InteropServices;
                    public class Win32 {{
                        [DllImport("user32.dll")]
                        public static extern bool SetForegroundWindow(IntPtr hWnd);
                        [DllImport("user32.dll")]
                        public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
                        [DllImport("user32.dll")]
                        public static extern bool IsIconic(IntPtr hWnd);
                    }}
                    "@
                    if ([Win32]::IsIconic($hwnd)) {{
                        [Win32]::ShowWindow($hwnd, 9) | Out-Null
                    }}
                    [Win32]::SetForegroundWindow($hwnd) | Out-Null
                    "Switched to: $($windows.MainWindowTitle)"
                }} else {{
                    "Window not found"
                }}
                '''
                result = subprocess.run(["powershell", "-c", script], capture_output=True, text=True, timeout=5)
                output = result.stdout.strip()
                
                if "Switched to" in output:
                    return output
                else:
                    # Try Alt+Tab if window not found by name
                    return f"Window '{title}' not found. Use 'list windows' to see available windows."
                    
            except Exception as e:
                logger.exception("Window focus failed")
                return f"Could not focus window: {str(e)}"

        elif action == "list":
            script = '''
            Get-Process | Where-Object { $_.MainWindowTitle -ne "" } | 
            Select-Object -First 15 ProcessName, MainWindowTitle | 
            ForEach-Object { "$($_.ProcessName): $($_.MainWindowTitle)" }
            '''
            result = subprocess.run(["powershell", "-c", script], capture_output=True, text=True, timeout=5)
            windows = result.stdout.strip()
            if windows:
                return f"Active windows:\n{windows}"
            else:
                return "No active windows found."

        elif action == "next":
            # Alt+Tab to next window
            pyautogui.keyDown('alt')
            pyautogui.keyDown('tab')
            pyautogui.keyUp('tab')
            pyautogui.keyUp('alt')
            return "Switched to next window."

        elif action == "previous" or action == "back":
            # Alt+Shift+Tab to previous window
            pyautogui.keyDown('alt')
            pyautogui.keyDown('shift')
            pyautogui.keyDown('tab')
            pyautogui.keyUp('tab')
            pyautogui.keyUp('shift')
            pyautogui.keyUp('alt')
            return "Switched to previous window."

        else:
            return f"Unknown window action: {action}. Try: minimize, maximize, restore, close, focus, switch, list, next"

    except Exception as e:
        logger.exception("Window control failed")
        return f"Window control error: {str(e)}"

def system_power(action: str) -> str:
    """Control system power state.
    
    Args:
        action: shutdown, restart, sleep, lock, logout
    """
    if not IS_WINDOWS:
        return "System power control only supported on Windows currently."

    try:
        action = action.lower().strip()

        if action == "shutdown":
            subprocess.Popen("shutdown /s /t 60", shell=True)
            return "System will shutdown in 60 seconds. Say 'cancel shutdown' to abort."

        elif action == "restart":
            subprocess.Popen("shutdown /r /t 60", shell=True)
            return "System will restart in 60 seconds. Say 'cancel shutdown' to abort."

        elif action == "sleep":
            subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True, check=False)
            return "System going to sleep."

        elif action == "lock":
            subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True, check=False)
            return "Workstation locked."

        elif action == "logout":
            subprocess.run("shutdown /l", shell=True, check=False)
            return "Logging out."

        elif action == "cancel":
            subprocess.run("shutdown /a", shell=True, check=False)
            return "Shutdown/restart aborted."

        else:
            return f"Unknown power action: {action}"

    except Exception as e:
        logger.exception("System power control failed")
        return f"Power control error: {str(e)}"


def clipboard_manager(action: str, text: str | None = None) -> str:
    """Manage clipboard operations.
    
    Args:
        action: copy, paste, clear, get
        text: Text to copy (for 'copy' action)
    """
    try:
        import pyperclip
    except ImportError:
        return "Clipboard operations require pyperclip (pip install pyperclip)."

    try:
        action = action.lower().strip()

        if action == "copy" and text:
            pyperclip.copy(text)
            return f"Copied to clipboard: {text[:50]}{'...' if len(text) > 50 else ''}"

        elif action == "paste":
            content = pyperclip.paste()
            return f"Clipboard content: {content[:200]}{'...' if len(content) > 200 else ''}"

        elif action == "clear":
            pyperclip.copy("")
            return "Clipboard cleared."

        elif action == "get":
            content = pyperclip.paste()
            return f"Clipboard: {content[:500]}{'...' if len(content) > 500 else ''}"

        else:
            return f"Unknown clipboard action: {action}"

    except Exception as e:
        logger.exception("Clipboard operation failed")
        return f"Clipboard error: {str(e)}"


def get_screen_info() -> str:
    """Get screen resolution and info."""
    if not _ensure_pyautogui():
        return "Screen info not available."

    try:
        width, height = pyautogui.size()
        mouse_x, mouse_y = pyautogui.position()
        return f"Screen: {width}x{height}. Mouse at: {mouse_x},{mouse_y}."
    except Exception as e:
        logger.exception("Get screen info failed")
        return f"Error: {str(e)}"


# Registry of all system control functions
SYSTEM_CONTROL_REGISTRY = {
    "mouse_control": mouse_control,
    "type_text": type_text,
    "hotkey": hotkey,
    "press_key": press_key,
    "screenshot": screenshot,
    "volume_control": volume_control,
    "brightness_control": brightness_control,
    "window_control": window_control,
    "system_power": system_power,
    "clipboard_manager": clipboard_manager,
    "get_mouse_position": get_mouse_position,
    "get_screen_info": get_screen_info,
}
