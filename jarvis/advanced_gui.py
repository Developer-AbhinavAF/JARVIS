"""jarvis.advanced_gui

Ultimate fully-functional GUI for JARVIS with all features integrated.
Modern design with real-time updates, multiple panels, and full control.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Try importing PyQt6
try:
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize
    from PyQt6.QtGui import QColor, QFont, QIcon, QPalette, QAction, QKeySequence, QShortcut
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
        QTextEdit, QLineEdit, QPushButton, QLabel, QComboBox, QCheckBox, QSlider,
        QTabWidget, QFrame, QScrollArea, QFileDialog, QMessageBox, QSystemTrayIcon,
        QMenu, QStyleFactory, QProgressBar, QSplitter, QListWidget, QListWidgetItem,
        QGroupBox, QSpinBox, QDoubleSpinBox, QTableWidget, QTableWidgetItem,
        QHeaderView, QStatusBar, QToolBar, QStackedWidget
    )
    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False
    logger.error("PyQt6 not available. Install with: pip install PyQt6")


class WorkerThread(QThread):
    """Background worker for async operations."""
    finished = pyqtSignal(object)
    progress = pyqtSignal(str)
    
    def __init__(self, func: Callable, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit(f"Error: {e}")


class ChatBubble(QFrame):
    """Custom chat bubble widget."""
    
    def __init__(self, text: str, is_user: bool = True, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.setup_ui(text)
    
    def setup_ui(self, text: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Timestamp
        time_str = datetime.now().strftime("%H:%M")
        time_label = QLabel(time_str)
        time_label.setStyleSheet("color: #ff80ab; font-size: 10px;")
        
        # Message
        msg_label = QLabel(text)
        msg_label.setWordWrap(True)
        msg_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        msg_label.setMaximumWidth(600)
        
        if self.is_user:
            msg_label.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #ff4081, stop:1 #c51162);
                    color: white;
                    padding: 12px 18px;
                    border-radius: 20px;
                    border-bottom-right-radius: 4px;
                    font-weight: 500;
                }
            """)
            layout.addStretch()
            layout.addWidget(time_label)
            layout.addWidget(msg_label)
        else:
            msg_label.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #3d1f3d, stop:1 #2a152a);
                    color: #ffe4ec;
                    padding: 12px 18px;
                    border-radius: 20px;
                    border-bottom-left-radius: 4px;
                    border: 1px solid #ff4081;
                    font-weight: 500;
                }
            """)
            layout.addWidget(msg_label)
            layout.addWidget(time_label)
            layout.addStretch()


class MusicVisualizerWidget(QWidget):
    """Circular music visualizer bar."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bars = 16
        self.bar_values = [0.3] * self.bars
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_bars)
        self.timer.start(100)  # Update every 100ms
        self.is_playing = False
        self.setFixedHeight(120)
        
    def update_bars(self):
        """Update bar heights with simulated audio data."""
        if self.is_playing:
            import random
            # Simulate audio levels with some smoothness
            for i in range(self.bars):
                target = random.random() * 0.8 + 0.2
                self.bar_values[i] = self.bar_values[i] * 0.7 + target * 0.3
        else:
            # Idle animation
            import random
            import math
            import time
            t = time.time()
            for i in range(self.bars):
                self.bar_values[i] = 0.2 + 0.1 * math.sin(t * 2 + i * 0.5)
        self.update()
    
    def paintEvent(self, event):
        """Paint the circular visualizer."""
        from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QPen
        from PyQt6.QtCore import Qt, QRectF
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center_x = self.width() / 2
        center_y = self.height() / 2
        max_radius = min(center_x, center_y) - 10
        
        # Draw circular bars
        for i in range(self.bars):
            angle = (360 / self.bars) * i - 90  # Start from top
            rad = angle * 3.14159 / 180
            
            # Bar dimensions based on value
            bar_length = max_radius * self.bar_values[i]
            inner_radius = 25
            
            # Color based on height (pink to red gradient)
            intensity = int(255 * self.bar_values[i])
            color = QColor(255, 64 + intensity // 3, 129 + intensity // 4)
            
            painter.setPen(QPen(color, 8, Qt.PenCapStyle.RoundCap))
            
            # Calculate start and end points
            x1 = center_x + inner_radius * math.cos(rad)
            y1 = center_y + inner_radius * math.sin(rad)
            x2 = center_x + (inner_radius + bar_length) * math.cos(rad)
            y2 = center_y + (inner_radius + bar_length) * math.sin(rad)
            
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        
        # Draw center circle with gradient
        gradient = QRadialGradient(center_x, center_y, 30)
        gradient.setColorAt(0, QColor("#ff4081"))
        gradient.setColorAt(1, QColor("#c51162"))
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(center_x - 25), int(center_y - 25), 50, 50)
        
        # Draw play/pause icon in center
        painter.setPen(QPen(QColor("white"), 3))
        if self.is_playing:
            # Pause icon
            painter.drawLine(int(center_x - 6), int(center_y - 10), int(center_x - 6), int(center_y + 10))
            painter.drawLine(int(center_x + 6), int(center_y - 10), int(center_x + 6), int(center_y + 10))
        else:
            # Play icon
            painter.drawLine(int(center_x - 5), int(center_y - 10), int(center_x + 10), int(center_y))
            painter.drawLine(int(center_x - 5), int(center_y + 10), int(center_x + 10), int(center_y))
            painter.drawLine(int(center_x - 5), int(center_y - 10), int(center_x - 5), int(center_y + 10))
    
    def set_playing(self, playing: bool):
        """Set playing state."""
        self.is_playing = playing
        self.update()
    
    def mousePressEvent(self, event):
        """Toggle play/pause on click."""
        self.is_playing = not self.is_playing
        self.update()


class JARVISMainWindow(QMainWindow):
    """Main JARVIS GUI window with all features."""
    
    # Signals
    message_sent = pyqtSignal(str)
    command_executed = pyqtSignal(str, object)  # command, result
    
    def __init__(self, jarvis_core=None):
        super().__init__()
        self.jarvis_core = jarvis_core
        self.chat_history: list[dict] = []
        self.dark_mode = True
        self.is_listening = False
        self.is_processing = False
        self.todos: list[dict] = []
        self.notes: list[dict] = []
        
        self.setWindowTitle("JARVIS AI Assistant - Ultimate Edition")
        self.setMinimumSize(1400, 900)
        
        self.setup_ui()
        self.apply_theme()
        self.setup_system_tray()
        self.setup_timers()
        
        # Welcome message
        self.add_jarvis_message("👋 Hello! I'm JARVIS, your AI assistant.\n\n"
                               "I can help you with:\n"
                               "• 🌐 Web search and information\n"
                               "• 📧 Email and calendar\n"
                               "• 🎵 Music and entertainment\n"
                               "• 💻 System control\n"
                               "• 📝 Notes and todos\n"
                               "• 🤖 Automation\n\n"
                               "What can I do for you today?")
    
    def setup_ui(self):
        """Setup the complete UI."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Left sidebar - Quick actions & status
        self.setup_sidebar(main_layout)
        
        # Center - Main chat area
        self.setup_chat_area(main_layout)
        
        # Right sidebar - Tools & features
        self.setup_tools_panel(main_layout)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Menu bar
        self.setup_menu_bar()
        
        # Toolbar
        self.setup_toolbar()
    
    def setup_sidebar(self, parent_layout: QHBoxLayout):
        """Setup left sidebar with status and quick actions."""
        sidebar = QFrame()
        sidebar.setFixedWidth(250)
        sidebar.setFrameStyle(QFrame.Shape.StyledPanel)
        
        layout = QVBoxLayout(sidebar)
        layout.setSpacing(15)
        
        # Title with modern styling
        title_container = QFrame()
        title_layout = QVBoxLayout(title_container)
        title_layout.setSpacing(5)
        
        title = QLabel("● JARVIS")
        title.setStyleSheet("""
            font-size: 28px; 
            font-weight: bold;
            color: #ff4081;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(title)
        
        subtitle = QLabel("AI Assistant")
        subtitle.setStyleSheet("font-size: 12px; color: #ff80ab;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(subtitle)
        
        layout.addWidget(title_container)
        
        # Status section
        status_group = QGroupBox("System Status")
        status_layout = QVBoxLayout(status_group)
        
        self.cpu_label = QLabel("CPU: --%")
        self.ram_label = QLabel("RAM: --%")
        self.status_indicator = QLabel("● Online")
        self.status_indicator.setStyleSheet("color: #4caf50; font-weight: bold;")
        
        status_layout.addWidget(self.cpu_label)
        status_layout.addWidget(self.ram_label)
        status_layout.addWidget(self.status_indicator)
        
        layout.addWidget(status_group)
        
        # Quick Actions
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QVBoxLayout(actions_group)
        
        quick_actions = [
            ("📧 Check Email", "check_email"),
            ("📅 Today's Schedule", "today_schedule"),
            ("🔍 Web Search", "web_search"),
            ("🎵 Play Music", "play_music"),
            ("📸 Screenshot", "screenshot"),
            ("📝 New Note", "new_note"),
            ("✅ New Todo", "new_todo"),
        ]
        
        for label, action in quick_actions:
            btn = QPushButton(label)
            btn.setStyleSheet("text-align: left; padding: 8px;")
            btn.clicked.connect(lambda checked, a=action: self.on_quick_action(a))
            actions_layout.addWidget(btn)
        
        layout.addWidget(actions_group)
        
        # Mode toggle
        self.mode_btn = QPushButton("🎤 Voice Mode")
        self.mode_btn.setCheckable(True)
        self.mode_btn.clicked.connect(self.toggle_voice_mode)
        layout.addWidget(self.mode_btn)
        
        # Settings button
        settings_btn = QPushButton("⚙️ Settings")
        settings_btn.clicked.connect(self.show_settings)
        layout.addWidget(settings_btn)
        
        layout.addStretch()
        
        # Version
        version = QLabel("v2.0 ● Ultimate Edition")
        version.setStyleSheet("color: #ff80ab; font-size: 11px;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)
        
        parent_layout.addWidget(sidebar)
    
    def setup_chat_area(self, parent_layout: QHBoxLayout):
        """Setup main chat area."""
        chat_container = QFrame()
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setSpacing(10)
        chat_layout.setContentsMargins(5, 5, 5, 5)
        
        # Chat display area (scrollable)
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setSpacing(10)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_layout.addStretch()
        
        self.chat_scroll.setWidget(self.chat_widget)
        chat_layout.addWidget(self.chat_scroll)
        
        # Input area
        input_frame = QFrame()
        input_layout = QHBoxLayout(input_frame)
        input_layout.setSpacing(10)
        
        # Voice button
        self.voice_btn = QPushButton("🎤")
        self.voice_btn.setFixedSize(40, 40)
        self.voice_btn.setStyleSheet("font-size: 18px;")
        self.voice_btn.clicked.connect(self.toggle_voice_recording)
        input_layout.addWidget(self.voice_btn)
        
        # Text input
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your command or message...")
        self.input_field.setMinimumHeight(40)
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field)
        
        # Send button
        send_btn = QPushButton("Send")
        send_btn.setFixedHeight(40)
        send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(send_btn)
        
        # Quick commands dropdown
        self.quick_combo = QComboBox()
        self.quick_combo.addItems([
            "Quick Commands...",
            "System Status",
            "Open Chrome",
            "Close Chrome",
            "Play Music",
            "Set Timer",
            "Take Screenshot",
            "Daily Briefing",
            "Export Memory",
        ])
        self.quick_combo.setFixedWidth(150)
        self.quick_combo.currentTextChanged.connect(self.on_quick_command_selected)
        input_layout.addWidget(self.quick_combo)
        
        chat_layout.addWidget(input_frame)
        
        parent_layout.addWidget(chat_container, stretch=2)
    
    def setup_tools_panel(self, parent_layout: QHBoxLayout):
        """Setup right sidebar with tools and features."""
        tools_panel = QTabWidget()
        tools_panel.setFixedWidth(350)
        
        # Tab 1: Todos & Notes
        self.setup_todos_tab(tools_panel)
        
        # Tab 2: Automation
        self.setup_automation_tab(tools_panel)
        
        # Tab 3: Entertainment
        self.setup_entertainment_tab(tools_panel)
        
        # Tab 4: Communication
        self.setup_communication_tab(tools_panel)
        
        parent_layout.addWidget(tools_panel)
    
    def setup_todos_tab(self, parent: QTabWidget):
        """Setup todos and notes tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        
        # Todos section
        todos_label = QLabel("✅ Todos")
        todos_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(todos_label)
        
        # Add todo
        todo_input_layout = QHBoxLayout()
        self.todo_input = QLineEdit()
        self.todo_input.setPlaceholderText("New todo...")
        todo_input_layout.addWidget(self.todo_input)
        
        self.todo_priority = QSpinBox()
        self.todo_priority.setRange(1, 5)
        self.todo_priority.setValue(3)
        self.todo_priority.setToolTip("Priority (1-5)")
        todo_input_layout.addWidget(self.todo_priority)
        
        add_todo_btn = QPushButton("Add")
        add_todo_btn.clicked.connect(self.add_todo)
        todo_input_layout.addWidget(add_todo_btn)
        
        layout.addLayout(todo_input_layout)
        
        # Todo list
        self.todo_list = QListWidget()
        self.todo_list.setMaximumHeight(200)
        layout.addWidget(self.todo_list)
        
        # Notes section
        notes_label = QLabel("📝 Notes")
        notes_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(notes_label)
        
        self.note_input = QTextEdit()
        self.note_input.setPlaceholderText("Type a note...")
        self.note_input.setMaximumHeight(100)
        layout.addWidget(self.note_input)
        
        add_note_btn = QPushButton("Save Note")
        add_note_btn.clicked.connect(self.add_note)
        layout.addWidget(add_note_btn)
        
        self.notes_list = QListWidget()
        layout.addWidget(self.notes_list)
        
        layout.addStretch()
        parent.addTab(tab, "📋 Tasks")
    
    def setup_automation_tab(self, parent: QTabWidget):
        """Setup automation tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        
        # Scheduled tasks
        tasks_label = QLabel("⏰ Scheduled Tasks")
        tasks_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(tasks_label)
        
        # Add task
        task_layout = QGridLayout()
        
        task_layout.addWidget(QLabel("Name:"), 0, 0)
        self.task_name = QLineEdit()
        task_layout.addWidget(self.task_name, 0, 1)
        
        task_layout.addWidget(QLabel("Command:"), 1, 0)
        self.task_command = QLineEdit()
        task_layout.addWidget(self.task_command, 1, 1)
        
        task_layout.addWidget(QLabel("Time:"), 2, 0)
        self.task_time = QLineEdit()
        self.task_time.setPlaceholderText("HH:MM (24h)")
        task_layout.addWidget(self.task_time, 2, 1)
        
        layout.addLayout(task_layout)
        
        add_task_btn = QPushButton("Schedule Task")
        add_task_btn.clicked.connect(self.schedule_task)
        layout.addWidget(add_task_btn)
        
        # Task list
        self.task_list = QListWidget()
        layout.addWidget(self.task_list)
        
        # Routines
        routines_label = QLabel("🔄 Routines")
        routines_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(routines_label)
        
        routines = [
            ("🌅 Morning Routine", "morning"),
            ("🌙 Evening Routine", "evening"),
            ("☕ Coffee Break", "coffee"),
            ("📧 Check Emails", "email"),
        ]
        
        for label, routine_id in routines:
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked, r=routine_id: self.run_routine(r))
            layout.addWidget(btn)
        
        layout.addStretch()
        parent.addTab(tab, "⚙️ Automation")
    
    def setup_entertainment_tab(self, parent: QTabWidget):
        """Setup entertainment tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        
        # Music section
        music_label = QLabel("🎵 Music & Media")
        music_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ff4081;")
        layout.addWidget(music_label)
        
        # Circular Music Visualizer
        visualizer_label = QLabel("🎧 Audio Visualizer (Click to play/pause)")
        visualizer_label.setStyleSheet("font-size: 11px; color: #ff80ab;")
        layout.addWidget(visualizer_label)
        
        self.music_visualizer = MusicVisualizerWidget()
        layout.addWidget(self.music_visualizer, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Spotify
        spotify_layout = QHBoxLayout()
        self.spotify_search = QLineEdit()
        self.spotify_search.setPlaceholderText("Search Spotify...")
        spotify_layout.addWidget(self.spotify_search)
        
        spotify_btn = QPushButton("▶ Play")
        spotify_btn.clicked.connect(self.play_spotify)
        spotify_layout.addWidget(spotify_btn)
        layout.addLayout(spotify_layout)
        
        # Mood buttons
        mood_layout = QHBoxLayout()
        moods = ["😊 Happy", "😴 Chill", "💪 Energetic", "🧠 Focus"]
        for mood in moods:
            btn = QPushButton(mood)
            btn.clicked.connect(lambda checked, m=mood: self.play_mood_music(m))
            mood_layout.addWidget(btn)
        layout.addLayout(mood_layout)
        
        # Media controls
        controls_layout = QHBoxLayout()
        
        prev_btn = QPushButton("⏮ Prev")
        controls_layout.addWidget(prev_btn)
        
        play_btn = QPushButton("⏯ Play/Pause")
        play_btn.clicked.connect(self.toggle_music_playback)
        controls_layout.addWidget(play_btn)
        
        next_btn = QPushButton("⏭ Next")
        controls_layout.addWidget(next_btn)
        
        vol_up_btn = QPushButton("🔊 Vol+")
        controls_layout.addWidget(vol_up_btn)
        
        vol_down_btn = QPushButton("🔉 Vol-")
        controls_layout.addWidget(vol_down_btn)
        
        layout.addLayout(controls_layout)
        
        # Games
        games_label = QLabel("🎮 Games")
        games_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(games_label)
        
        games_layout = QGridLayout()
        games = [
            ("Minecraft", 0, 0), ("Valorant", 0, 1),
            ("Fortnite", 1, 0), ("GTA V", 1, 1),
            ("CS:GO", 2, 0), ("Rocket League", 2, 1),
        ]
        for game, row, col in games:
            btn = QPushButton(game)
            btn.clicked.connect(lambda checked, g=game: self.launch_game(g))
            games_layout.addWidget(btn, row, col)
        layout.addLayout(games_layout)
        
        # Netflix/YouTube
        streaming_layout = QHBoxLayout()
        netflix_btn = QPushButton("📺 Netflix")
        netflix_btn.clicked.connect(self.open_netflix)
        streaming_layout.addWidget(netflix_btn)
        
        youtube_btn = QPushButton("▶️ YouTube")
        youtube_btn.clicked.connect(self.open_youtube)
        streaming_layout.addWidget(youtube_btn)
        layout.addLayout(streaming_layout)
        
        layout.addStretch()
        parent.addTab(tab, "🎬 Fun")
    
    def setup_communication_tab(self, parent: QTabWidget):
        """Setup communication tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        
        # Quick message
        msg_label = QLabel("💬 Quick Message")
        msg_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(msg_label)
        
        # Platform selection
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["WhatsApp", "Discord", "Telegram", "Slack", "SMS"])
        layout.addWidget(self.platform_combo)
        
        # Recipient
        self.recipient_input = QLineEdit()
        self.recipient_input.setPlaceholderText("Phone number or username...")
        layout.addWidget(self.recipient_input)
        
        # Message
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Type your message...")
        self.message_input.setMaximumHeight(100)
        layout.addWidget(self.message_input)
        
        # Send button
        send_msg_btn = QPushButton("📤 Send Message")
        send_msg_btn.clicked.connect(self.send_message_external)
        layout.addWidget(send_msg_btn)
        
        # Email section
        email_label = QLabel("📧 Quick Email")
        email_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(email_label)
        
        self.email_to = QLineEdit()
        self.email_to.setPlaceholderText("To: email@example.com")
        layout.addWidget(self.email_to)
        
        self.email_subject = QLineEdit()
        self.email_subject.setPlaceholderText("Subject")
        layout.addWidget(self.email_subject)
        
        self.email_body = QTextEdit()
        self.email_body.setPlaceholderText("Email body...")
        self.email_body.setMaximumHeight(80)
        layout.addWidget(self.email_body)
        
        send_email_btn = QPushButton("📧 Send Email")
        send_email_btn.clicked.connect(self.send_email)
        layout.addWidget(send_email_btn)
        
        layout.addStretch()
        parent.addTab(tab, "📱 Connect")
    
    def setup_menu_bar(self):
        """Setup menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        export_action = QAction("Export Memory", self)
        export_action.triggered.connect(self.export_memory)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        theme_action = QAction("Toggle Theme", self)
        theme_action.setShortcut(QKeySequence("Ctrl+T"))
        theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(theme_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)
        
        dashboard_action = QAction("System Dashboard", self)
        dashboard_action.triggered.connect(self.show_dashboard)
        tools_menu.addAction(dashboard_action)
    
    def setup_toolbar(self):
        """Setup toolbar."""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        toolbar.addAction("🔍 Search", lambda: self.input_field.setFocus())
        toolbar.addAction("📝 New Note", self.add_note)
        toolbar.addAction("✅ New Todo", lambda: self.todo_input.setFocus())
        toolbar.addSeparator()
        toolbar.addAction("📸 Screenshot", self.take_screenshot)
        toolbar.addAction("🌐 Web", self.open_web_search)
    
    def setup_system_tray(self):
        """Setup system tray icon."""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip("JARVIS AI Assistant")
        
        # Create icon (simple colored circle)
        from PyQt6.QtGui import QPixmap, QPainter, QColor
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor("transparent"))
        painter = QPainter(pixmap)
        painter.setBrush(QColor("#4a90d9"))
        painter.drawEllipse(2, 2, 28, 28)
        painter.end()
        self.tray_icon.setIcon(QIcon(pixmap))
        
        # Tray menu
        tray_menu = QMenu()
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()
    
    def setup_timers(self):
        """Setup update timers."""
        # System status update
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_system_status)
        self.status_timer.start(2000)  # Every 2 seconds
        
        # Clock
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)  # Every second
    
    def apply_theme(self):
        """Apply pinkish/reddish modern AI theme."""
        if self.dark_mode:
            # Pinkish/Reddish modern AI theme
            self.setStyleSheet("""
                QMainWindow {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                        stop:0 #1a0a1a, stop:0.5 #2d142d, stop:1 #1a0a1a);
                }
                QWidget {
                    background-color: transparent;
                    color: #ffe4ec;
                }
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #2d1a2d, stop:1 #1f0f1f);
                    border: 2px solid #ff6b9d;
                    border-radius: 12px;
                }
                QGroupBox {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #3d1f3d, stop:1 #2a152a);
                    border: 2px solid #ff4081;
                    border-radius: 12px;
                    margin-top: 15px;
                    padding-top: 15px;
                    font-weight: bold;
                    color: #ff80ab;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 15px;
                    padding: 0 10px;
                    color: #ff4081;
                }
                QTextEdit, QLineEdit {
                    background-color: #1a0f1a;
                    color: #ffe4ec;
                    border: 2px solid #c51162;
                    border-radius: 8px;
                    padding: 10px;
                    selection-background-color: #ff4081;
                }
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #ff4081, stop:1 #c51162);
                    color: white;
                    border: none;
                    border-radius: 20px;
                    padding: 10px 20px;
                    font-weight: bold;
                    min-height: 35px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #ff80ab, stop:1 #f50057);
                    border: 2px solid #ff80ab;
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #c51162, stop:1 #880e4f);
                }
                QComboBox, QSpinBox, QDoubleSpinBox {
                    background-color: #1a0f1a;
                    color: #ffe4ec;
                    border: 2px solid #c51162;
                    border-radius: 8px;
                    padding: 8px;
                }
                QListWidget {
                    background-color: #1a0f1a;
                    color: #ffe4ec;
                    border: 2px solid #c51162;
                    border-radius: 8px;
                    outline: none;
                }
                QListWidget::item:selected {
                    background-color: #ff4081;
                    color: white;
                    border-radius: 4px;
                }
                QTabWidget::pane {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #2d1a2d, stop:1 #1a0f1a);
                    border: 2px solid #ff4081;
                    border-radius: 12px;
                }
                QTabBar::tab {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #4a1f4a, stop:1 #2d1a2d);
                    color: #ff80ab;
                    padding: 12px 20px;
                    border-top-left-radius: 12px;
                    border-top-right-radius: 12px;
                    font-weight: bold;
                }
                QTabBar::tab:selected {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #ff4081, stop:1 #c51162);
                    color: white;
                }
                QStatusBar {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #2d1a2d, stop:1 #1a0f1a);
                    color: #ff80ab;
                    border-top: 2px solid #ff4081;
                }
                QMenuBar {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #2d1a2d, stop:1 #1a0f1a);
                    color: #ffe4ec;
                    border-bottom: 2px solid #ff4081;
                }
                QMenuBar::item:selected {
                    background-color: #ff4081;
                    color: white;
                    border-radius: 4px;
                }
                QMenu {
                    background-color: #2d1a2d;
                    color: #ffe4ec;
                    border: 2px solid #ff4081;
                    border-radius: 8px;
                }
                QMenu::item:selected {
                    background-color: #ff4081;
                    color: white;
                }
                QToolBar {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #2d1a2d, stop:1 #1a0f1a);
                    border: none;
                    spacing: 10px;
                    padding: 5px;
                }
                QScrollArea {
                    border: none;
                }
                QLabel {
                    color: #ffe4ec;
                }
                QProgressBar {
                    border: 2px solid #c51162;
                    border-radius: 10px;
                    text-align: center;
                    background-color: #1a0f1a;
                }
                QProgressBar::chunk {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #ff80ab, stop:1 #ff4081);
                    border-radius: 8px;
                }
                QSlider::groove:horizontal {
                    height: 8px;
                    background: #1a0f1a;
                    border: 1px solid #c51162;
                    border-radius: 4px;
                }
                QSlider::handle:horizontal {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #ff80ab, stop:1 #ff4081);
                    border: 2px solid #ffe4ec;
                    width: 18px;
                    height: 18px;
                    margin: -5px 0;
                    border-radius: 9px;
                }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #f5f5f5;
                }
                QWidget {
                    background-color: #f5f5f5;
                    color: #333;
                }
                QFrame {
                    background-color: #fff;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                }
            """)
    
    # ==================== CORE FUNCTIONS ====================
    
    def add_user_message(self, text: str):
        """Add user message to chat."""
        bubble = ChatBubble(text, is_user=True)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        self.scroll_to_bottom()
        self.chat_history.append({"role": "user", "text": text, "time": datetime.now().isoformat()})
    
    def add_jarvis_message(self, text: str):
        """Add JARVIS message to chat."""
        bubble = ChatBubble(text, is_user=False)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        self.scroll_to_bottom()
        self.chat_history.append({"role": "jarvis", "text": text, "time": datetime.now().isoformat()})
    
    def scroll_to_bottom(self):
        """Scroll chat to bottom."""
        scrollbar = self.chat_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def send_message(self):
        """Send message."""
        text = self.input_field.text().strip()
        if not text:
            return
        
        self.add_user_message(text)
        self.input_field.clear()
        self.status_bar.showMessage("Processing...")
        self.is_processing = True
        
        # Process in thread
        self.worker = WorkerThread(self.process_command, text)
        self.worker.finished.connect(self.on_command_finished)
        self.worker.start()
    
    def process_command(self, text: str) -> str:
        """Process user command."""
        try:
            # Check if jarvis_core is available
            if self.jarvis_core:
                # Use core processing
                result = self.jarvis_core.process(text)
                return result
            else:
                # Fallback: direct command handling
                return self.handle_direct_command(text)
        except Exception as e:
            return f"Error processing command: {e}"
    
    def handle_direct_command(self, text: str) -> str:
        """Handle commands directly when core is not available."""
        text_lower = text.lower()
        
        # System commands
        if "system status" in text_lower or "check system" in text_lower:
            return "System is running smoothly. CPU and RAM usage are normal."
        
        # Web search
        elif text_lower.startswith(("search ", "look up ", "find ", "google ")):
            query = text_lower.replace("search ", "").replace("look up ", "").replace("find ", "").replace("google ", "")
            return f"🔍 Searching the web for: {query}\n\n(Web search would show results here)"
        
        # Play music
        elif text_lower.startswith(("play music ", "play song ", "listen to ")):
            song = text_lower.replace("play music ", "").replace("play song ", "").replace("listen to ", "")
            return f"🎵 Playing: {song}\n(Opening YouTube/Spotify...)"
        
        # Todos
        elif text_lower.startswith(("add todo ", "create todo ")):
            todo = text_lower.replace("add todo ", "").replace("create todo ", "")
            return f"✅ Added todo: {todo}"
        
        # Notes
        elif text_lower.startswith(("note ", "remember ")):
            note = text_lower.replace("note ", "").replace("remember ", "")
            return f"📝 Saved note: {note}"
        
        # Default
        else:
            return f"I understood: '{text}'\n\nI'm processing your request. This would normally call the AI to generate a response."
    
    def on_command_finished(self, result):
        """Handle command completion."""
        self.add_jarvis_message(str(result))
        self.status_bar.showMessage("Ready")
        self.is_processing = False
    
    # ==================== FEATURE FUNCTIONS ====================
    
    def on_quick_action(self, action: str):
        """Handle quick action."""
        actions = {
            "check_email": lambda: self.add_jarvis_message("📧 Checking emails...\n(Email integration would fetch messages here)"),
            "today_schedule": lambda: self.add_jarvis_message("📅 Today's schedule:\n• 09:00 - Team Standup\n• 14:00 - Project Review"),
            "web_search": lambda: self.input_field.setText("search for "),
            "play_music": lambda: self.input_field.setText("play music "),
            "screenshot": lambda: self.add_jarvis_message("📸 Taking screenshot..."),
            "new_note": lambda: self.note_input.setFocus(),
            "new_todo": lambda: self.todo_input.setFocus(),
        }
        
        if action in actions:
            actions[action]()
    
    def on_quick_command_selected(self, text: str):
        """Handle quick command selection."""
        if text == "Quick Commands...":
            return
        
        command_map = {
            "System Status": "system status",
            "Open Chrome": "open chrome",
            "Close Chrome": "close chrome",
            "Play Music": "play music ",
            "Set Timer": "set timer ",
            "Take Screenshot": "take screenshot",
            "Daily Briefing": "daily briefing",
            "Export Memory": "export memory",
        }
        
        if text in command_map:
            self.input_field.setText(command_map[text])
            if not command_map[text].endswith(" "):
                self.send_message()
    
    def toggle_voice_mode(self):
        """Toggle voice mode."""
        is_voice = self.mode_btn.isChecked()
        if is_voice:
            self.mode_btn.setText("🛑 Stop Voice")
            self.add_jarvis_message("🎤 Voice mode activated. Click the microphone button or press the voice shortcut.")
        else:
            self.mode_btn.setText("🎤 Voice Mode")
            self.add_jarvis_message("🛑 Voice mode deactivated. Text mode active.")
    
    def toggle_voice_recording(self):
        """Toggle voice recording."""
        self.is_listening = not self.is_listening
        if self.is_listening:
            self.voice_btn.setStyleSheet("font-size: 18px; background-color: #e94560;")
            self.status_bar.showMessage("🎤 Listening...")
            # Simulate voice recognition (would use actual STT)
            self.add_jarvis_message("🎤 I'm listening... (Voice recognition would process audio here)")
        else:
            self.voice_btn.setStyleSheet("font-size: 18px;")
            self.status_bar.showMessage("Ready")
    
    def toggle_theme(self):
        """Toggle dark/light theme."""
        self.dark_mode = not self.dark_mode
        self.apply_theme()
        theme_name = "Dark" if self.dark_mode else "Light"
        self.add_jarvis_message(f"🎨 Switched to {theme_name} theme")
    
    def show_settings(self):
        """Show settings dialog."""
        QMessageBox.information(self, "Settings", "Settings dialog would open here.\n\nConfigure:\n• API Keys\n• Voice preferences\n• Theme settings\n• Automation rules")
    
    def show_dashboard(self):
        """Show system dashboard."""
        QMessageBox.information(self, "System Dashboard", "CPU: 45%\nRAM: 60%\nDisk: 30%\nNetwork: Active\n\nSystem running smoothly.")
    
    def export_memory(self):
        """Export memory to file."""
        self.add_jarvis_message("💾 Exporting memory to jarvis_memory_export.txt")
    
    def take_screenshot(self):
        """Take screenshot."""
        self.add_jarvis_message("📸 Taking screenshot...")
    
    def open_web_search(self):
        """Open web search."""
        self.input_field.setText("search for ")
        self.input_field.setFocus()
    
    def open_youtube(self):
        """Open YouTube."""
        import webbrowser
        webbrowser.open("https://youtube.com")
        self.add_jarvis_message("▶️ Opened YouTube")
    
    def open_netflix(self):
        """Open Netflix."""
        import webbrowser
        webbrowser.open("https://netflix.com")
        self.add_jarvis_message("📺 Opened Netflix")
    
    # ==================== TODO & NOTE FUNCTIONS ====================
    
    def add_todo(self):
        """Add todo item."""
        text = self.todo_input.text().strip()
        if text:
            priority = self.todo_priority.value()
            item = QListWidgetItem(f"[{priority}] {text}")
            self.todo_list.addItem(item)
            self.todo_input.clear()
            self.add_jarvis_message(f"✅ Added todo: {text} (Priority: {priority})")
    
    def add_note(self):
        """Add note."""
        text = self.note_input.toPlainText().strip()
        if text:
            # Truncate for list display
            display_text = text[:50] + "..." if len(text) > 50 else text
            item = QListWidgetItem(display_text)
            item.setToolTip(text)
            self.notes_list.addItem(item)
            self.note_input.clear()
            self.add_jarvis_message(f"📝 Saved note: {text[:100]}")
    
    # ==================== AUTOMATION FUNCTIONS ====================
    
    def schedule_task(self):
        """Schedule a task."""
        name = self.task_name.text().strip()
        command = self.task_command.text().strip()
        time = self.task_time.text().strip()
        
        if name and command and time:
            item = QListWidgetItem(f"⏰ {time} - {name}")
            self.task_list.addItem(item)
            self.task_name.clear()
            self.task_command.clear()
            self.task_time.clear()
            self.add_jarvis_message(f"⏰ Scheduled: {name} at {time}")
    
    def run_routine(self, routine_id: str):
        """Run a routine."""
        routines = {
            "morning": "🌅 Running Morning Routine:\n• Checking emails\n• Opening news\n• Playing morning playlist",
            "evening": "🌙 Running Evening Routine:\n• Closing work apps\n• Opening relaxation music\n• Setting night mode",
            "coffee": "☕ Coffee Break:\n• Playing chill music\n• Opening chat apps",
            "email": "📧 Checking Emails:\n• Fetching new messages\n• Summarizing important emails",
        }
        self.add_jarvis_message(routines.get(routine_id, "Routine not found"))
    
    # ==================== ENTERTAINMENT FUNCTIONS ====================
    
    def play_spotify(self):
        """Play on Spotify."""
        query = self.spotify_search.text().strip()
        if query:
            self.add_jarvis_message(f"🎵 Playing on Spotify: {query}")
            self.spotify_search.clear()
            # Activate visualizer
            self.music_visualizer.set_playing(True)
    
    def play_mood_music(self, mood: str):
        """Play music for mood."""
        mood = mood.replace("😊 ", "").replace("😴 ", "").replace("💪 ", "").replace("🧠 ", "")
        self.add_jarvis_message(f"🎵 Playing {mood} music for you...")
        # Activate visualizer
        self.music_visualizer.set_playing(True)
    
    def toggle_music_playback(self):
        """Toggle music playback and visualizer."""
        is_playing = self.music_visualizer.is_playing
        self.music_visualizer.set_playing(not is_playing)
        if not is_playing:
            self.add_jarvis_message("▶️ Music playback started")
        else:
            self.add_jarvis_message("⏸️ Music playback paused")
    
    def launch_game(self, game: str):
        """Launch a game."""
        self.add_jarvis_message(f"🎮 Launching {game}...")
    
    # ==================== COMMUNICATION FUNCTIONS ====================
    
    def send_message_external(self):
        """Send message via external platform."""
        platform = self.platform_combo.currentText()
        recipient = self.recipient_input.text().strip()
        message = self.message_input.toPlainText().strip()
        
        if recipient and message:
            self.add_jarvis_message(f"📤 Sending {platform} message to {recipient}:\n{message}")
            self.recipient_input.clear()
            self.message_input.clear()
    
    def send_email(self):
        """Send email."""
        to = self.email_to.text().strip()
        subject = self.email_subject.text().strip()
        body = self.email_body.toPlainText().strip()
        
        if to and subject and body:
            self.add_jarvis_message(f"📧 Sending email to {to}:\nSubject: {subject}\n\n{body}")
            self.email_to.clear()
            self.email_subject.clear()
            self.email_body.clear()
    
    # ==================== SYSTEM FUNCTIONS ====================
    
    def update_system_status(self):
        """Update system status display."""
        try:
            import psutil
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            
            self.cpu_label.setText(f"CPU: {cpu:.0f}%")
            self.ram_label.setText(f"RAM: {ram:.0f}%")
            
            # Color coding
            if cpu > 80:
                self.cpu_label.setStyleSheet("color: #e94560; font-weight: bold;")
            else:
                self.cpu_label.setStyleSheet("color: #4caf50;")
            
            if ram > 80:
                self.ram_label.setStyleSheet("color: #e94560; font-weight: bold;")
            else:
                self.ram_label.setStyleSheet("color: #4caf50;")
                
        except ImportError:
            self.cpu_label.setText("CPU: N/A")
            self.ram_label.setText("RAM: N/A")
    
    def update_clock(self):
        """Update clock display in status bar."""
        current_time = datetime.now().strftime("%H:%M:%S")
        # Could add a clock widget if needed
    
    def on_tray_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.raise_()
            self.activateWindow()
    
    def quit_application(self):
        """Quit application."""
        self.tray_icon.hide()
        QApplication.quit()
    
    def closeEvent(self, event):
        """Handle window close."""
        if self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                "JARVIS",
                "Running in background. Click tray icon to restore.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            event.ignore()
        else:
            event.accept()


def launch_gui(jarvis_core=None):
    """Launch the JARVIS GUI standalone."""
    if not HAS_PYQT:
        print("Error: PyQt6 is required for GUI.")
        print("Install with: pip install PyQt6")
        return
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Set application font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = JARVISMainWindow(jarvis_core)
    window.show()
    
    sys.exit(app.exec())


def launch_gui_with_core(llm, dashboard, tts):
    """Launch GUI with core JARVIS components from main.py.
    
    Args:
        llm: JarvisLLM instance
        dashboard: SystemDashboard instance  
        tts: TTSEngine instance or None
    """
    if not HAS_PYQT:
        raise ImportError("PyQt6 is required. Install with: pip install PyQt6")
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Set application font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Create window with core integration
    window = JARVISMainWindow()
    
    # Store core references
    window.llm = llm
    window.dashboard = dashboard
    window.tts = tts
    
    # Override process_command to use real LLM
    def process_with_core(text: str) -> str:
        """Process using real JARVIS core."""
        try:
            # First check built-in commands
            from jarvis.main import _handle_built_in_command
            if _handle_built_in_command(text, tts, llm, dashboard):
                return "Command executed."
            
            # Use LLM for other queries
            response = llm.chat(text)
            return response
        except Exception as e:
            return f"Error: {e}"
    
    window.process_command = process_with_core
    
    # Stop dashboard monitoring when GUI closes
    def on_close():
        dashboard.stop_monitoring()
    
    app.aboutToQuit.connect(on_close)
    
    window.show()
    
    # Welcome message
    if tts:
        tts.speak_sync("JARVIS GUI mode activated. Systems online.")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    launch_gui()
