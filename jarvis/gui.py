"""jarvis.gui

Modern GUI interface with PyQt/Tkinter, chat-style interface, themes.
"""

from __future__ import annotations

import logging
import queue
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Try importing PyQt first, fallback to Tkinter
try:
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
    from PyQt6.QtGui import QColor, QFont, QIcon, QPalette
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QTextEdit, QLineEdit, QPushButton, QLabel, QComboBox,
        QCheckBox, QSlider, QTabWidget, QFrame, QScrollArea,
        QFileDialog, QMessageBox, QSystemTrayIcon, QMenu, QStyleFactory
    )
    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False
    logger.warning("PyQt6 not available, using Tkinter")

try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox, filedialog
    from tkinter.font import Font
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False


@dataclass
class Message:
    """Chat message."""
    sender: str  # "user", "jarvis", "system"
    text: str
    timestamp: float


class ChatHistory:
    """Manage chat history."""
    
    def __init__(self, max_messages: int = 100) -> None:
        self.messages: list[Message] = []
        self.max_messages = max_messages
    
    def add(self, sender: str, text: str) -> None:
        """Add a message."""
        self.messages.append(Message(sender, text, time.time()))
        # Trim old messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def clear(self) -> None:
        """Clear history."""
        self.messages.clear()
    
    def get_formatted(self) -> str:
        """Get formatted chat history."""
        lines = []
        for msg in self.messages:
            time_str = time.strftime("%H:%M", time.localtime(msg.timestamp))
            if msg.sender == "user":
                lines.append(f"[{time_str}] You: {msg.text}")
            elif msg.sender == "jarvis":
                lines.append(f"[{time_str}] JARVIS: {msg.text}")
            else:
                lines.append(f"[{time_str}] {msg.text}")
        return "\n".join(lines)


if HAS_PYQT:
    class JARVISMainWindow(QMainWindow):
        """Main GUI window with PyQt."""
        
        message_received = pyqtSignal(str, str)  # sender, text
        
        def __init__(
            self,
            on_message: Callable[[str], None] | None = None,
            on_voice_toggle: Callable[[], None] | None = None,
        ) -> None:
            super().__init__()
            self.on_message = on_message
            self.on_voice_toggle = on_voice_toggle
            self.chat_history = ChatHistory()
            self.dark_mode = True
            self.is_listening = False
            self.is_speaking = False
            
            self._setup_ui()
            self._apply_theme()
        
        def _setup_ui(self) -> None:
            """Setup UI components."""
            self.setWindowTitle("JARVIS AI Assistant")
            self.setMinimumSize(900, 700)
            
            # Central widget
            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)
            layout.setSpacing(10)
            layout.setContentsMargins(15, 15, 15, 15)
            
            # Status bar
            status_layout = QHBoxLayout()
            self.status_label = QLabel("Status: Ready")
            self.status_label.setStyleSheet("font-weight: bold; padding: 5px;")
            status_layout.addWidget(self.status_label)
            
            # Voice visualizer (simple)
            self.viz_label = QLabel("🔴")
            self.viz_label.setStyleSheet("font-size: 20px;")
            status_layout.addWidget(self.viz_label)
            
            status_layout.addStretch()
            
            # Theme toggle
            self.theme_btn = QPushButton("🌙 Dark")
            self.theme_btn.clicked.connect(self._toggle_theme)
            status_layout.addWidget(self.theme_btn)
            
            layout.addLayout(status_layout)
            
            # Chat display
            self.chat_display = QTextEdit()
            self.chat_display.setReadOnly(True)
            self.chat_display.setFont(QFont("Segoe UI", 11))
            layout.addWidget(self.chat_display)
            
            # Input area
            input_layout = QHBoxLayout()
            
            self.input_field = QLineEdit()
            self.input_field.setPlaceholderText("Type your message or command...")
            self.input_field.setFont(QFont("Segoe UI", 11))
            self.input_field.returnPressed.connect(self._send_message)
            input_layout.addWidget(self.input_field, stretch=1)
            
            # Send button
            send_btn = QPushButton("Send")
            send_btn.setStyleSheet("padding: 8px 20px;")
            send_btn.clicked.connect(self._send_message)
            input_layout.addWidget(send_btn)
            
            # Voice button
            voice_btn = QPushButton("🎤 Voice")
            voice_btn.setStyleSheet("padding: 8px 15px;")
            voice_btn.clicked.connect(self._toggle_voice)
            input_layout.addWidget(voice_btn)
            
            layout.addLayout(input_layout)
            
            # Quick commands
            quick_layout = QHBoxLayout()
            quick_layout.addWidget(QLabel("Quick:"))
            
            quick_cmds = [
                ("System Status", "system status"),
                ("Weather", "what's the weather"),
                ("Open Chrome", "open chrome"),
                ("Timer", "set timer 5 minutes"),
                ("Screenshot", "take screenshot"),
            ]
            
            for label, cmd in quick_cmds:
                btn = QPushButton(label)
                btn.clicked.connect(lambda checked, c=cmd: self._quick_command(c))
                quick_layout.addWidget(btn)
            
            quick_layout.addStretch()
            layout.addLayout(quick_layout)
            
            # Connect signals
            self.message_received.connect(self._on_message_received)
        
        def _apply_theme(self) -> None:
            """Apply dark or light theme."""
            if self.dark_mode:
                self.setStyleSheet("""
                    QMainWindow {
                        background-color: #1a1a2e;
                    }
                    QTextEdit, QLineEdit {
                        background-color: #16213e;
                        color: #eaeaea;
                        border: 1px solid #0f3460;
                        border-radius: 5px;
                        padding: 8px;
                    }
                    QPushButton {
                        background-color: #0f3460;
                        color: #eaeaea;
                        border: none;
                        border-radius: 5px;
                        padding: 8px 15px;
                    }
                    QPushButton:hover {
                        background-color: #e94560;
                    }
                    QLabel {
                        color: #eaeaea;
                    }
                """)
                self.theme_btn.setText("☀️ Light")
            else:
                self.setStyleSheet("""
                    QMainWindow {
                        background-color: #f0f0f0;
                    }
                    QTextEdit, QLineEdit {
                        background-color: #ffffff;
                        color: #333333;
                        border: 1px solid #cccccc;
                        border-radius: 5px;
                        padding: 8px;
                    }
                    QPushButton {
                        background-color: #4a90d9;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        padding: 8px 15px;
                    }
                    QPushButton:hover {
                        background-color: #357abd;
                    }
                    QLabel {
                        color: #333333;
                    }
                """)
                self.theme_btn.setText("🌙 Dark")
        
        def _toggle_theme(self) -> None:
            """Toggle dark/light theme."""
            self.dark_mode = not self.dark_mode
            self._apply_theme()
        
        def _send_message(self) -> None:
            """Send message."""
            text = self.input_field.text().strip()
            if text:
                self._add_message("user", text)
                self.input_field.clear()
                
                if self.on_message:
                    # Run in thread to not block UI
                    threading.Thread(target=self._process_message, args=(text,), daemon=True).start()
        
        def _process_message(self, text: str) -> None:
            """Process message in background."""
            if self.on_message:
                self.on_message(text)
        
        def _quick_command(self, cmd: str) -> None:
            """Execute quick command."""
            self.input_field.setText(cmd)
            self._send_message()
        
        def _toggle_voice(self) -> None:
            """Toggle voice mode."""
            if self.on_voice_toggle:
                self.on_voice_toggle()
        
        def _on_message_received(self, sender: str, text: str) -> None:
            """Handle received message."""
            self._add_message(sender, text)
        
        def _add_message(self, sender: str, text: str) -> None:
            """Add message to chat."""
            self.chat_history.add(sender, text)
            
            # Format with colors
            if sender == "user":
                formatted = f'<span style="color: #4a90d9;"><b>You:</b></span> {text}'
            elif sender == "jarvis":
                formatted = f'<span style="color: #e94560;"><b>JARVIS:</b></span> {text}'
            else:
                formatted = f'<span style="color: #888888;"><i>{text}</i></span>'
            
            self.chat_display.append(formatted)
        
        def add_jarvis_message(self, text: str) -> None:
            """Add message from JARVIS."""
            self.message_received.emit("jarvis", text)
        
        def set_status(self, status: str) -> None:
            """Update status."""
            self.status_label.setText(f"Status: {status}")
            
            # Update visualizer
            if "listening" in status.lower():
                self.viz_label.setText("🟢 Listening...")
            elif "speaking" in status.lower():
                self.viz_label.setText("🔊 Speaking...")
            elif "thinking" in status.lower():
                self.viz_label.setText("🧠 Thinking...")
            else:
                self.viz_label.setText("🔴")
        
        def closeEvent(self, event) -> None:
            """Handle window close."""
            # Minimize to tray instead of closing
            event.ignore()
            self.hide()


    class JARVISGUI:
        """Main GUI controller."""
        
        def __init__(self) -> None:
            self.app: QApplication | None = None
            self.window: JARVISMainWindow | None = None
            self.on_message: Callable[[str], None] | None = None
            self.on_voice: Callable[[], None] | None = None
        
        def setup(
            self,
            on_message: Callable[[str], None],
            on_voice: Callable[[], None] | None = None,
        ) -> None:
            """Setup GUI."""
            self.on_message = on_message
            self.on_voice = on_voice
        
        def run(self) -> None:
            """Run GUI event loop."""
            self.app = QApplication(sys.argv)
            self.window = JARVISMainWindow(self.on_message, self.on_voice)
            self.window.show()
            self.app.exec()
        
        def show_message(self, text: str) -> None:
            """Show message from JARVIS."""
            if self.window:
                self.window.add_jarvis_message(text)
        
        def set_status(self, status: str) -> None:
            """Update status."""
            if self.window:
                self.window.set_status(status)


elif HAS_TKINTER:
    # Tkinter fallback implementation
    class JARVISGUI:
        """GUI with Tkinter."""
        
        def __init__(self) -> None:
            self.root: tk.Tk | None = None
            self.chat_display: scrolledtext.ScrolledText | None = None
            self.input_field: ttk.Entry | None = None
            self.on_message: Callable[[str], None] | None = None
        
        def setup(
            self,
            on_message: Callable[[str], None],
            on_voice: Callable[[], None] | None = None,
        ) -> None:
            """Setup GUI."""
            self.on_message = on_message
        
        def run(self) -> None:
            """Run GUI."""
            self.root = tk.Tk()
            self.root.title("JARVIS AI Assistant")
            self.root.geometry("800x600")
            
            # Dark theme colors
            bg_color = "#1a1a2e"
            fg_color = "#eaeaea"
            accent_color = "#e94560"
            
            self.root.configure(bg=bg_color)
            
            # Chat display
            self.chat_display = scrolledtext.ScrolledText(
                self.root,
                wrap=tk.WORD,
                width=80,
                height=25,
                bg="#16213e",
                fg=fg_color,
                font=("Segoe UI", 11),
            )
            self.chat_display.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
            self.chat_display.config(state=tk.DISABLED)
            
            # Input frame
            input_frame = ttk.Frame(self.root)
            input_frame.pack(padx=10, pady=5, fill=tk.X)
            
            self.input_field = ttk.Entry(input_frame, width=60)
            self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            self.input_field.bind("<Return>", self._send_message)
            
            send_btn = ttk.Button(input_frame, text="Send", command=self._send_message)
            send_btn.pack(side=tk.RIGHT, padx=5)
            
            self.root.mainloop()
        
        def _send_message(self, event: Any = None) -> None:
            """Send message."""
            if self.input_field and self.on_message:
                text = self.input_field.get().strip()
                if text:
                    self._add_message("You", text)
                    self.input_field.delete(0, tk.END)
                    threading.Thread(target=self.on_message, args=(text,), daemon=True).start()
        
        def _add_message(self, sender: str, text: str) -> None:
            """Add message."""
            if self.chat_display:
                self.chat_display.config(state=tk.NORMAL)
                self.chat_display.insert(tk.END, f"{sender}: {text}\n\n")
                self.chat_display.see(tk.END)
                self.chat_display.config(state=tk.DISABLED)
        
        def show_message(self, text: str) -> None:
            """Show message."""
            self._add_message("JARVIS", text)
        
        def set_status(self, status: str) -> None:
            """Update status."""
            pass  # Simplified for Tkinter


else:
    # No GUI available
    class JARVISGUI:
        """Fallback when no GUI library available."""
        
        def __init__(self) -> None:
            logger.error("No GUI library available (PyQt6 or Tkinter)")
        
        def setup(self, **kwargs: Any) -> None:
            pass
        
        def run(self) -> None:
            logger.error("Cannot run GUI - no GUI library available")
        
        def show_message(self, text: str) -> None:
            print(f"JARVIS: {text}")
        
        def set_status(self, status: str) -> None:
            pass


# Global GUI instance
gui = JARVISGUI()
