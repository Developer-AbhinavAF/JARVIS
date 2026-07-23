"""tools_enhanced — Enhanced tools with confirmation requirements and media playback.

Adds:
- System control with confirmation (sleep, shutdown, lock)
- File operations with safety checks
- Media playback (YouTube via Playwright/yt-dlp)
- Enhanced desktop control
"""

from __future__ import annotations

import os
import time
import logging
import subprocess
import platform
from pathlib import Path
from typing import Any
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


from core.tools import ToolResult, ToolCategory


class ConfirmationHandler:
    """Handle user confirmation for dangerous operations."""
    _pending: dict = {}

    @staticmethod
    def request_confirmation(action: str, details: str = "") -> bool:
        """Print a warning and ask the user to confirm via stdin."""
        msg = f"\n⚠  CONFIRMATION REQUIRED: {action}"
        if details:
            msg += f"\n   Details: {details}"
        msg += "\n   Proceed? (yes/no): "
        try:
            answer = input(msg).strip().lower()
            return answer in ("yes", "y", "haan", "ha", "ok", "okay")
        except Exception:
            return False


# --- System Control Tools ---

def system_sleep() -> ToolResult:
    """Put the system to sleep (requires confirmation)."""
    if not ConfirmationHandler.request_confirmation("System Sleep"):
        return ToolResult(success=False, error="User declined confirmation", requires_confirmation=True, confirmed=False)
    
    try:
        system = platform.system()
        if system == "Windows":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        elif system == "Darwin":  # macOS
            os.system("pmset sleepnow")
        elif system == "Linux":
            os.system("systemctl suspend")
        else:
            return ToolResult(success=False, error=f"Unsupported system: {system}")
        
        return ToolResult(success=True, result={"action": "sleep"}, verified=True, requires_confirmation=True, confirmed=True)
    except Exception as e:
        return ToolResult(success=False, error=str(e), requires_confirmation=True)


def system_shutdown() -> ToolResult:
    """Shutdown the system (requires confirmation)."""
    if not ConfirmationHandler.request_confirmation("System Shutdown"):
        return ToolResult(success=False, error="User declined confirmation", requires_confirmation=True, confirmed=False)
    
    try:
        system = platform.system()
        if system == "Windows":
            os.system("shutdown /s /t 1")
        elif system == "Darwin":  # macOS
            os.system("shutdown -h now")
        elif system == "Linux":
            os.system("shutdown -h now")
        else:
            return ToolResult(success=False, error=f"Unsupported system: {system}")
        
        return ToolResult(success=True, result={"action": "shutdown"}, verified=True, requires_confirmation=True, confirmed=True)
    except Exception as e:
        return ToolResult(success=False, error=str(e), requires_confirmation=True)


def system_lock() -> ToolResult:
    """Lock the system (requires confirmation)."""
    if not ConfirmationHandler.request_confirmation("System Lock"):
        return ToolResult(success=False, error="User declined confirmation", requires_confirmation=True, confirmed=False)
    
    try:
        system = platform.system()
        if system == "Windows":
            os.system("rundll32.exe user32.dll,LockWorkStation")
        elif system == "Darwin":  # macOS
            os.system("pmset displaysleepnow")
        elif system == "Linux":
            os.system("xdg-screensaver lock")
        else:
            return ToolResult(success=False, error=f"Unsupported system: {system}")
        
        return ToolResult(success=True, result={"action": "lock"}, verified=True, requires_confirmation=True, confirmed=True)
    except Exception as e:
        return ToolResult(success=False, error=str(e), requires_confirmation=True)


# --- Enhanced File Operations ---

def delete_file_safe(file_path: str) -> ToolResult:
    """Delete a file with confirmation requirement."""
    if not file_path:
        return ToolResult(success=False, error="No file path provided")
    
    path = Path(file_path)
    if not path.exists():
        return ToolResult(success=False, error=f"File not found: {file_path}")
    
    if not ConfirmationHandler.request_confirmation(f"Delete file: {file_path}"):
        return ToolResult(success=False, error="User declined confirmation", requires_confirmation=True, confirmed=False)
    
    try:
        if path.is_dir():
            import shutil
            shutil.rmtree(path)
        else:
            path.unlink()
        
        still_exists = path.exists()
        return ToolResult(
            success=not still_exists,
            result={"file_path": str(path)},
            verified=not still_exists,
            requires_confirmation=True,
            confirmed=True
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e), requires_confirmation=True)


def rename_file_safe(file_path: str, new_name: str) -> ToolResult:
    """Rename a file with confirmation."""
    if not file_path or not new_name:
        return ToolResult(success=False, error="File path and new name required")
    
    path = Path(file_path)
    if not path.exists():
        return ToolResult(success=False, error=f"File not found: {file_path}")
    
    new_path = path.parent / new_name
    
    if not ConfirmationHandler.request_confirmation(f"Rename {file_path} to {new_name}"):
        return ToolResult(success=False, error="User declined confirmation", requires_confirmation=True, confirmed=False)
    
    try:
        path.rename(new_path)
        return ToolResult(
            success=True,
            result={"old_path": str(path), "new_path": str(new_path)},
            verified=new_path.exists(),
            requires_confirmation=True,
            confirmed=True
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e), requires_confirmation=True)


def move_file_safe(file_path: str, destination: str) -> ToolResult:
    """Move a file with confirmation."""
    if not file_path or not destination:
        return ToolResult(success=False, error="File path and destination required")
    
    path = Path(file_path)
    dest_path = Path(destination)
    
    if not path.exists():
        return ToolResult(success=False, error=f"File not found: {file_path}")
    
    if not ConfirmationHandler.request_confirmation(f"Move {file_path} to {destination}"):
        return ToolResult(success=False, error="User declined confirmation", requires_confirmation=True, confirmed=False)
    
    try:
        import shutil
        shutil.move(str(path), str(dest_path))
        return ToolResult(
            success=True,
            result={"old_path": str(path), "new_path": str(dest_path)},
            verified=dest_path.exists(),
            requires_confirmation=True,
            confirmed=True
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e), requires_confirmation=True)


# --- Clipboard Tools ---

def copy_to_clipboard(text: str = "") -> ToolResult:
    """Copy text to clipboard."""
    if not text:
        return ToolResult(success=False, error="No text provided")
    
    try:
        import pyperclip
        pyperclip.copy(text)
        # Verify
        copied = pyperclip.paste()
        verified = copied == text
        return ToolResult(
            success=True,
            result={"text": text, "length": len(text)},
            verified=verified,
            verification_details="Clipboard content matches input" if verified else "Clipboard verification failed"
        )
    except ImportError:
        return ToolResult(success=False, error="pyperclip not installed")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def paste_from_clipboard() -> ToolResult:
    """Paste text from clipboard."""
    try:
        import pyperclip
        text = pyperclip.paste()
        return ToolResult(
            success=True,
            result={"text": text, "length": len(text)},
            verified=True
        )
    except ImportError:
        return ToolResult(success=False, error="pyperclip not installed")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# --- Email Tools ---

def send_email(to: str = "", subject: str = "", body: str = "") -> ToolResult:
    """Send an email (opens default email client)."""
    if not to:
        return ToolResult(success=False, error="Recipient email required")
    
    try:
        import webbrowser
        mailto_url = f"mailto:{to}"
        params = []
        if subject:
            params.append(f"subject={subject}")
        if body:
            params.append(f"body={body}")
        
        if params:
            mailto_url += "?" + "&".join(params)
        
        webbrowser.open(mailto_url)
        return ToolResult(
            success=True,
            result={"to": to, "subject": subject, "url": mailto_url},
            verified=True
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# --- Media Playback with Playwright/yt-dlp ---

def play_media_advanced(media_query: str = "") -> ToolResult:
    """Play media using YouTube search with yt-dlp for actual playback."""
    if not media_query:
        media_query = "music"
    
    query = media_query.strip()
    
    # If it's a song/video name, search and play
    if query and query not in ("music", "song", "video", "media"):
        try:
            # Try yt-dlp for direct playback
            import yt_dlp
            
            ydl_opts = {
                'format': 'best',
                'quiet': True,
                'no_warnings': True,
            }
            
            # Search YouTube
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                search_url = f"ytsearch:{query}"
                info = ydl.extract_info(search_url, download=False)
                
                if info and 'entries' in info:
                    first_result = info['entries'][0]
                    video_url = first_result.get('webpage_url', '')
                    title = first_result.get('title', 'Unknown')
                    
                    # Open in browser for playback
                    import webbrowser
                    webbrowser.open(video_url)
                    
                    return ToolResult(
                        success=True,
                        result={
                            "query": query,
                            "title": title,
                            "url": video_url,
                            "text": f"Playing '{title}' on YouTube"
                        },
                        verified=True
                    )
        except ImportError:
            logger.warning("yt-dlp not available, falling back to web search")
        except Exception as e:
            logger.warning(f"yt-dlp failed: {e}, falling back to web search")
    
    # Fallback to web search
    import webbrowser
    webbrowser.open(f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}")
    
    return ToolResult(
        success=True,
        result={"query": query, "text": f"Searching YouTube for '{query}'"},
        verified=True
    )


def open_first_result() -> ToolResult:
    """Open the first search result by re-triggering the last search URL."""
    import webbrowser
    try:
        from core.context_engine import context_engine
        context = context_engine.get_context()
        last_website = context.get("active_url", "")
        if last_website:
            url = last_website if last_website.startswith("http") else f"https://{last_website}"
            webbrowser.open(url)
            return ToolResult(
                success=True,
                result={"url": url, "text": f"Opening {url}"},
                verified=True,
            )
    except Exception:
        pass
    return ToolResult(
        success=False,
        error="No previous search to open. Try searching for something first.",
    )


# --- Enhanced Desktop Control ---

def click_at_coordinates(x: int, y: int) -> ToolResult:
    """Click at specific screen coordinates."""
    try:
        import pyautogui
        pyautogui.click(x, y)
        return ToolResult(success=True, result={"x": x, "y": y}, verified=True)
    except ImportError:
        return ToolResult(success=False, error="pyautogui not available")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def double_click_at_coordinates(x: int, y: int) -> ToolResult:
    """Double-click at specific screen coordinates."""
    try:
        import pyautogui
        pyautogui.doubleClick(x, y)
        return ToolResult(success=True, result={"x": x, "y": y}, verified=True)
    except ImportError:
        return ToolResult(success=False, error="pyautogui not available")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def type_text(text: str) -> ToolResult:
    """Type text at current cursor position."""
    try:
        import pyautogui
        pyautogui.typewrite(text)
        return ToolResult(success=True, result={"text": text}, verified=True)
    except ImportError:
        return ToolResult(success=False, error="pyautogui not available")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def press_key(key: str) -> ToolResult:
    """Press a specific key."""
    try:
        import pyautogui
        pyautogui.press(key)
        return ToolResult(success=True, result={"key": key}, verified=True)
    except ImportError:
        return ToolResult(success=False, error="pyautogui not available")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# --- Registration Helper ---

def register_enhanced_tools(tool_registry) -> None:
    """Register enhanced tools with the tool registry."""
    from core.tools import ToolCategory
    
    # System control
    tool_registry.register("system_sleep", "Put system to sleep (requires confirmation)", ToolCategory.SYSTEM, system_sleep)
    tool_registry.register("system_shutdown", "Shutdown system (requires confirmation)", ToolCategory.SYSTEM, system_shutdown)
    tool_registry.register("system_lock", "Lock system (requires confirmation)", ToolCategory.SYSTEM, system_lock)
    
    # Enhanced file operations
    tool_registry.register("delete_file_safe", "Delete file with confirmation", ToolCategory.FILES, delete_file_safe)
    tool_registry.register("rename_file_safe", "Rename file with confirmation", ToolCategory.FILES, rename_file_safe)
    tool_registry.register("move_file_safe", "Move file with confirmation", ToolCategory.FILES, move_file_safe)
    
    # Clipboard operations
    tool_registry.register("copy_to_clipboard", "Copy text to clipboard", ToolCategory.UTILITY, copy_to_clipboard)
    tool_registry.register("paste_from_clipboard", "Paste text from clipboard", ToolCategory.UTILITY, paste_from_clipboard)
    
    # Email operations
    tool_registry.register("send_email", "Send email via default email client", ToolCategory.UTILITY, send_email)
    
    # Media playback
    tool_registry.register("play_media_advanced", "Play media using yt-dlp", ToolCategory.MEDIA, play_media_advanced)
    tool_registry.register("open_first_result", "Open first search result", ToolCategory.BROWSER, open_first_result)
    
    # Desktop control
    tool_registry.register("click_at_coordinates", "Click at screen coordinates", ToolCategory.DESKTOP, click_at_coordinates)
    tool_registry.register("double_click_at_coordinates", "Double-click at screen coordinates", ToolCategory.DESKTOP, double_click_at_coordinates)
    tool_registry.register("type_text", "Type text at cursor", ToolCategory.DESKTOP, type_text)
    tool_registry.register("press_key", "Press keyboard key", ToolCategory.DESKTOP, press_key)
