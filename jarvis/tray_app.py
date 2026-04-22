"""jarvis.tray_app

System tray integration with quick menu for JARVIS.
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from typing import Callable

logger = logging.getLogger(__name__)

# Try to import pystray, fallback if not available
try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False
    logger.warning("pystray not available, system tray will not work")


class TrayApp:
    """System tray application for JARVIS."""
    
    def __init__(self) -> None:
        self.icon: pystray.Icon | None = None
        self.status = "idle"
        self.menu_items: list[tuple[str, Callable[[], None]]] = [
            ("Show", self._show_window),
            ("Voice Mode", self._voice_mode),
            ("Text Mode", self._text_mode),
            ("Settings", self._open_settings),
            ("Exit", self._exit),
        ]
        self._callbacks: dict[str, Callable[[], None]] = {}
        
    def _create_image(self) -> Image.Image:
        """Create tray icon image."""
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), color='black')
        dc = ImageDraw.Draw(image)
        
        # Draw a simple J-like shape
        dc.rectangle([20, 10, 44, 54], outline='cyan', width=3)
        dc.line([32, 10, 32, 40], fill='cyan', width=3)
        dc.line([32, 40, 44, 40], fill='cyan', width=3)
        dc.line([44, 40, 44, 54], fill='cyan', width=3)
        
        return image
    
    def _show_window(self) -> None:
        """Callback to show main window."""
        if "show" in self._callbacks:
            self._callbacks["show"]()
    
    def _voice_mode(self) -> None:
        """Switch to voice mode."""
        if "voice" in self._callbacks:
            self._callbacks["voice"]()
    
    def _text_mode(self) -> None:
        """Switch to text mode."""
        if "text" in self._callbacks:
            self._callbacks["text"]()
    
    def _open_settings(self) -> None:
        """Open settings dialog."""
        if "settings" in self._callbacks:
            self._callbacks["settings"]()
    
    def _exit(self) -> None:
        """Exit application."""
        if "exit" in self._callbacks:
            self._callbacks["exit"]()
        self.stop()
    
    def register_callback(self, name: str, callback: Callable[[], None]) -> None:
        """Register a callback for menu actions."""
        self._callbacks[name] = callback
    
    def _build_menu(self) -> pystray.Menu:
        """Build the tray menu."""
        items = []
        for label, action in self.menu_items:
            items.append(pystray.MenuItem(label, action))
        return pystray.Menu(*items)
    
    def run(self) -> None:
        """Run the tray application."""
        if not HAS_PYSTRAY:
            logger.error("System tray not available - pystray not installed")
            return
        
        try:
            self.icon = pystray.Icon(
                "JARVIS",
                self._create_image(),
                "JARVIS AI Assistant",
                self._build_menu()
            )
            self.icon.run()
        except Exception as e:
            logger.exception(f"Tray app error: {e}")
    
    def run_detached(self) -> None:
        """Run tray in background thread."""
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
    
    def stop(self) -> None:
        """Stop the tray application."""
        if self.icon:
            self.icon.stop()
    
    def update_status(self, status: str) -> None:
        """Update tray tooltip status."""
        self.status = status
        if self.icon:
            self.icon.title = f"JARVIS - {status}"
    
    def notify(self, title: str, message: str) -> None:
        """Show a notification."""
        if self.icon and HAS_PYSTRAY:
            try:
                self.icon.notify(message, title)
            except Exception as e:
                logger.error(f"Notification failed: {e}")


class WindowsStartup:
    """Handle Windows startup integration."""
    
    @staticmethod
    def add_to_startup() -> bool:
        """Add JARVIS to Windows startup."""
        try:
            import winreg
            import sys
            
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            
            # Get the Python executable and script path
            python_exe = sys.executable
            script_path = "d:\\JARVIS\\jarvis\\main.py"
            command = f'"{python_exe}" "{script_path}" --minimized'
            
            winreg.SetValueEx(key, "JARVIS", 0, winreg.REG_SZ, command)
            winreg.CloseKey(key)
            
            logger.info("JARVIS added to Windows startup")
            return True
        except Exception as e:
            logger.error(f"Failed to add to startup: {e}")
            return False
    
    @staticmethod
    def remove_from_startup() -> bool:
        """Remove JARVIS from Windows startup."""
        try:
            import winreg
            
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            
            try:
                winreg.DeleteValue(key, "JARVIS")
            except FileNotFoundError:
                pass  # Already doesn't exist
            
            winreg.CloseKey(key)
            
            logger.info("JARVIS removed from Windows startup")
            return True
        except Exception as e:
            logger.error(f"Failed to remove from startup: {e}")
            return False
    
    @staticmethod
    def is_in_startup() -> bool:
        """Check if JARVIS is in Windows startup."""
        try:
            import winreg
            
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            
            try:
                value, _ = winreg.QueryValueEx(key, "JARVIS")
                winreg.CloseKey(key)
                return True
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except Exception as e:
            logger.error(f"Failed to check startup: {e}")
            return False


# Global tray app instance
tray_app = TrayApp()


def setup_tray(
    on_show: Callable[[], None] | None = None,
    on_voice: Callable[[], None] | None = None,
    on_text: Callable[[], None] | None = None,
    on_settings: Callable[[], None] | None = None,
    on_exit: Callable[[], None] | None = None,
) -> TrayApp:
    """Setup and start system tray."""
    if on_show:
        tray_app.register_callback("show", on_show)
    if on_voice:
        tray_app.register_callback("voice", on_voice)
    if on_text:
        tray_app.register_callback("text", on_text)
    if on_settings:
        tray_app.register_callback("settings", on_settings)
    if on_exit:
        tray_app.register_callback("exit", on_exit)
    
    tray_app.run_detached()
    return tray_app
