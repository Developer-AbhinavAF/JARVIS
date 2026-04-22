"""jarvis.memory

Long-term memory system for JARVIS.

SQLite-based storage for:
- Conversation history summaries
- User preferences and facts
- Important dates and reminders
- To-do items and notes

Lightweight and fast on 8GB systems.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from jarvis import config

logger = logging.getLogger(__name__)


class JarvisMemory:
    """Long-term memory manager with SQLite backend."""

    def __init__(self, db_path: str | None = None) -> None:
        """Initialize memory system.
        
        Args:
            db_path: Path to SQLite database (default: config.MEMORY_DB_PATH)
        """
        self.db_path = db_path or config.MEMORY_DB_PATH
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Conversation summaries
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        summary TEXT,
                        topics TEXT,
                        importance INTEGER DEFAULT 1
                    )
                """)

                # User preferences and facts
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS preferences (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        key TEXT UNIQUE,
                        value TEXT,
                        category TEXT,
                        timestamp TEXT
                    )
                """)

                # To-do items
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS todos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task TEXT,
                        category TEXT,
                        priority INTEGER DEFAULT 1,
                        created TEXT,
                        due TEXT,
                        completed INTEGER DEFAULT 0
                    )
                """)

                # Reminders
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS reminders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        message TEXT,
                        remind_time TEXT,
                        repeat TEXT,
                        triggered INTEGER DEFAULT 0
                    )
                """)

                # Notes
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS notes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT,
                        content TEXT,
                        category TEXT,
                        created TEXT,
                        tags TEXT
                    )
                """)

                # Important dates
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS important_dates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event TEXT,
                        date TEXT,
                        recurring INTEGER DEFAULT 0,
                        category TEXT
                    )
                """)

                conn.commit()
                logger.info("Memory database initialized")

        except Exception:
            logger.exception("Failed to initialize memory database")

    def save_conversation(self, summary: str, topics: list[str], importance: int = 1) -> bool:
        """Save a conversation summary.
        
        Args:
            summary: Brief summary of conversation
            topics: List of topics discussed
            importance: 1-5 scale for retention priority
        """
        try:
            with self._lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO conversations (timestamp, summary, topics, importance) VALUES (?, ?, ?, ?)",
                    (datetime.now().isoformat(), summary, json.dumps(topics), importance),
                )
                conn.commit()

                # Cleanup old low-importance conversations
                self._cleanup_old_memories(conn)
                return True
        except Exception:
            logger.exception("Failed to save conversation")
            return False

    def get_recent_conversations(self, limit: int = 5) -> list[dict[str, Any]]:
        """Get recent conversation summaries."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM conversations ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception:
            logger.exception("Failed to get conversations")
            return []

    def save_preference(self, key: str, value: str, category: str = "general") -> bool:
        """Save a user preference.
        
        Examples:
            key="favorite_color", value="blue"
            key="work_hours", value="9-5"
        """
        try:
            with self._lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO preferences (key, value, category, timestamp)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(key) DO UPDATE SET
                        value=excluded.value, timestamp=excluded.timestamp""",
                    (key, value, category, datetime.now().isoformat()),
                )
                conn.commit()
                return True
        except Exception:
            logger.exception("Failed to save preference")
            return False

    def get_preference(self, key: str) -> str | None:
        """Get a user preference by key."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM preferences WHERE key = ?", (key,))
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception:
            logger.exception("Failed to get preference")
            return None

    def get_all_preferences(self, category: str | None = None) -> dict[str, str]:
        """Get all preferences, optionally filtered by category."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if category:
                    cursor.execute("SELECT key, value FROM preferences WHERE category = ?", (category,))
                else:
                    cursor.execute("SELECT key, value FROM preferences")
                return {row[0]: row[1] for row in cursor.fetchall()}
        except Exception:
            logger.exception("Failed to get preferences")
            return {}

    def add_todo(self, task: str, category: str = "general", priority: int = 1, due: str | None = None) -> str:
        """Add a to-do item.
        
        Args:
            task: Description of task
            category: Task category
            priority: 1 (low) to 5 (high)
            due: Due date ISO format or None
        """
        try:
            with self._lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO todos (task, category, priority, created, due, completed) VALUES (?, ?, ?, ?, ?, 0)",
                    (task, category, priority, datetime.now().isoformat(), due),
                )
                conn.commit()
                return f"Added to-do: {task}"
        except Exception:
            logger.exception("Failed to add todo")
            return "Failed to add to-do item."

    def get_todos(self, category: str | None = None, completed: bool = False) -> list[dict[str, Any]]:
        """Get to-do items."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                if category:
                    cursor.execute(
                        "SELECT * FROM todos WHERE category = ? AND completed = ? ORDER BY priority DESC, created DESC",
                        (category, int(completed)),
                    )
                else:
                    cursor.execute(
                        "SELECT * FROM todos WHERE completed = ? ORDER BY priority DESC, created DESC",
                        (int(completed),),
                    )
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            logger.exception("Failed to get todos")
            return []

    def complete_todo(self, task_id: int) -> str:
        """Mark a to-do as completed."""
        try:
            with self._lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE todos SET completed = 1 WHERE id = ?", (task_id,))
                conn.commit()
                return f"Task {task_id} marked as complete."
        except Exception:
            logger.exception("Failed to complete todo")
            return "Failed to complete task."

    def add_reminder(self, message: str, remind_time: str, repeat: str | None = None) -> str:
        """Add a reminder.
        
        Args:
            message: Reminder text
            remind_time: ISO datetime when to remind
            repeat: Optional repeat pattern (daily, weekly, monthly)
        """
        try:
            with self._lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO reminders (message, remind_time, repeat, triggered) VALUES (?, ?, ?, 0)",
                    (message, remind_time, repeat),
                )
                conn.commit()
                return f"Reminder set: {message} at {remind_time}"
        except Exception:
            logger.exception("Failed to add reminder")
            return "Failed to set reminder."

    def check_reminders(self) -> list[str]:
        """Check for due reminders and return messages."""
        try:
            now = datetime.now().isoformat()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, message, repeat FROM reminders WHERE remind_time <= ? AND triggered = 0",
                    (now,),
                )
                due = cursor.fetchall()

                messages = []
                for row in due:
                    reminder_id, message, repeat = row
                    messages.append(message)

                    if repeat:
                        # Reschedule repeating reminders
                        next_time = self._calculate_next_reminder(remind_time=row[0], repeat=repeat)
                        cursor.execute(
                            "UPDATE reminders SET remind_time = ?, triggered = 0 WHERE id = ?",
                            (next_time, reminder_id),
                        )
                    else:
                        cursor.execute("UPDATE reminders SET triggered = 1 WHERE id = ?", (reminder_id,))

                conn.commit()
                return messages
        except Exception:
            logger.exception("Failed to check reminders")
            return []

    def _calculate_next_reminder(self, remind_time: str, repeat: str) -> str:
        """Calculate next occurrence for repeating reminders."""
        dt = datetime.fromisoformat(remind_time)
        if repeat == "daily":
            next_dt = dt.replace(day=dt.day + 1)
        elif repeat == "weekly":
            # Simple week addition
            next_dt = dt.replace(day=dt.day + 7)
        elif repeat == "monthly":
            # Simple month addition
            if dt.month == 12:
                next_dt = dt.replace(year=dt.year + 1, month=1)
            else:
                next_dt = dt.replace(month=dt.month + 1)
        else:
            next_dt = dt
        return next_dt.isoformat()

    def add_note(self, title: str, content: str, category: str = "general", tags: list[str] | None = None) -> str:
        """Add a note."""
        try:
            with self._lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO notes (title, content, category, created, tags) VALUES (?, ?, ?, ?, ?)",
                    (title, content, category, datetime.now().isoformat(), json.dumps(tags or [])),
                )
                conn.commit()
                return f"Note saved: {title}"
        except Exception:
            logger.exception("Failed to add note")
            return "Failed to save note."

    def search_notes(self, query: str) -> list[dict[str, Any]]:
        """Search notes by title or content."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                search_term = f"%{query}%"
                cursor.execute(
                    "SELECT * FROM notes WHERE title LIKE ? OR content LIKE ? ORDER BY created DESC",
                    (search_term, search_term),
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            logger.exception("Failed to search notes")
            return []

    def add_important_date(self, event: str, date: str, recurring: bool = False, category: str = "general") -> str:
        """Add an important date.
        
        Args:
            event: Event name
            date: Date in YYYY-MM-DD format
            recurring: Whether it repeats annually
            category: Event category (birthday, anniversary, etc.)
        """
        try:
            with self._lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO important_dates (event, date, recurring, category) VALUES (?, ?, ?, ?)",
                    (event, date, int(recurring), category),
                )
                conn.commit()
                return f"Added: {event} on {date}"
        except Exception:
            logger.exception("Failed to add important date")
            return "Failed to add date."

    def get_upcoming_dates(self, days: int = 30) -> list[dict[str, Any]]:
        """Get upcoming important dates within specified days."""
        try:
            from datetime import timedelta

            today = datetime.now()
            future = today + timedelta(days=days)

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                # Simple date comparison (SQLite date comparison)
                cursor.execute(
                    "SELECT * FROM important_dates WHERE date BETWEEN ? AND ? ORDER BY date",
                    (today.strftime("%Y-%m-%d"), future.strftime("%Y-%m-%d")),
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            logger.exception("Failed to get upcoming dates")
            return []

    def get_daily_briefing(self) -> str:
        """Generate a daily briefing with todos, reminders, and upcoming dates."""
        parts = []

        # Check reminders
        reminders = self.check_reminders()
        if reminders:
            parts.append(f"You have {len(reminders)} reminder(s): " + "; ".join(reminders))

        # Get todos
        todos = self.get_todos(completed=False)
        if todos:
            high_priority = [t for t in todos if t["priority"] >= 3]
            if high_priority:
                parts.append(f"You have {len(high_priority)} high-priority task(s) pending.")
            else:
                parts.append(f"You have {len(todos)} task(s) on your to-do list.")

        # Upcoming dates
        upcoming = self.get_upcoming_dates(days=7)
        if upcoming:
            events = ", ".join([f"{e['event']} on {e['date']}" for e in upcoming[:3]])
            parts.append(f"Upcoming: {events}")

        if parts:
            return "Daily briefing: " + " ".join(parts)
        return "Daily briefing: All clear. No urgent items."

    def _cleanup_old_memories(self, conn: sqlite3.Connection) -> None:
        """Remove old low-importance conversations to keep DB size manageable."""
        try:
            cursor = conn.cursor()
            # Keep only last 1000 conversations
            cursor.execute(
                "DELETE FROM conversations WHERE id NOT IN (SELECT id FROM conversations ORDER BY timestamp DESC LIMIT ?)",
                (config.MAX_LONG_TERM_MEMORY,),
            )
            conn.commit()
        except Exception:
            logger.exception("Memory cleanup failed")

    def export_to_readable(self, output_path: str = "jarvis_memory_export.txt") -> str:
        """Export all memory data to a human-readable text file.
        
        Args:
            output_path: Path to save the readable export
        """
        try:
            lines = []
            lines.append("="*60)
            lines.append("JARVIS MEMORY EXPORT")
            lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("="*60)
            lines.append("")
            
            # Conversations
            lines.append("## CONVERSATIONS")
            lines.append("-"*40)
            conversations = self.get_recent_conversations(limit=100)
            if conversations:
                for c in conversations:
                    ts = c.get('timestamp', 'Unknown')[:19]  # Truncate to remove microseconds
                    summary = c.get('summary', 'No summary')
                    topics = c.get('topics', '')
                    lines.append(f"[{ts}] {summary}")
                    if topics:
                        lines.append(f"    Topics: {topics}")
            else:
                lines.append("No conversations stored.")
            lines.append("")
            
            # Preferences
            lines.append("## PREFERENCES")
            lines.append("-"*40)
            prefs = self.get_all_preferences()
            if prefs:
                for key, value in prefs.items():
                    lines.append(f"{key}: {value}")
            else:
                lines.append("No preferences saved.")
            lines.append("")
            
            # To-dos
            lines.append("## TO-DO LIST")
            lines.append("-"*40)
            todos = self.get_todos(completed=False)
            if todos:
                for t in todos:
                    status = "[X]" if t.get('completed') else "[ ]"
                    priority = t.get('priority', 1)
                    task = t.get('task', 'Unknown')
                    lines.append(f"{status} (P{priority}) {task}")
            else:
                lines.append("No pending tasks.")
            lines.append("")
            
            # Notes
            lines.append("## NOTES")
            lines.append("-"*40)
            notes = self.search_notes("")  # Empty search = all notes
            if notes:
                for n in notes:
                    title = n.get('title', 'Untitled')
                    content = n.get('content', '')
                    created = n.get('created', 'Unknown')[:19]
                    lines.append(f"### {title} (Created: {created})")
                    lines.append(content)
                    lines.append("")
            else:
                lines.append("No notes saved.")
            lines.append("")
            
            # Important dates
            lines.append("## IMPORTANT DATES")
            lines.append("-"*40)
            dates = self.get_upcoming_dates(days=365)
            if dates:
                for d in dates:
                    event = d.get('event', 'Unknown')
                    date = d.get('date', 'Unknown')
                    recurring = "(Recurring)" if d.get('recurring') else ""
                    lines.append(f"{date}: {event} {recurring}")
            else:
                lines.append("No important dates saved.")
            
            lines.append("")
            lines.append("="*60)
            lines.append("END OF EXPORT")
            lines.append("="*60)
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines))
            
            return f"Memory exported to {output_path}"
        except Exception as e:
            logger.exception("Failed to export memory")
            return f"Export failed: {str(e)}"

    def save_permanent_info(self, info: str, category: str = "general") -> str:
        """Save important information permanently (as a note with special category).
        
        Args:
            info: The information to save
            category: Category like 'facts', 'user_info', 'important', etc.
        """
        try:
            # Create a title from first few words
            words = info.split()[:5]
            title = " ".join(words) + "..." if len(info.split()) > 5 else info
            
            # Add note with permanent category
            return self.add_note(title, info, category=category)
        except Exception as e:
            logger.exception("Failed to save permanent info")
            return f"Failed to save: {str(e)}"


# Global memory instance
memory = JarvisMemory()


def memory_add_todo(task: str, category: str = "general") -> str:
    """Tool: Add a to-do item."""
    return memory.add_todo(task, category)


def memory_get_todos() -> str:
    """Tool: Get pending to-do items."""
    todos = memory.get_todos(completed=False)
    if not todos:
        return "No pending tasks."
    lines = [f"{t['id']}: {t['task']} (priority {t['priority']})" for t in todos[:10]]
    return "To-do list:\n" + "\n".join(lines)


def memory_add_note(title: str, content: str) -> str:
    """Tool: Add a note."""
    return memory.add_note(title, content)


def memory_search_notes(query: str) -> str:
    """Tool: Search notes."""
    notes = memory.search_notes(query)
    if not notes:
        return f"No notes found matching '{query}'."
    lines = [f"{n['title']}: {n['content'][:100]}..." for n in notes[:5]]
    return "Found notes:\n" + "\n".join(lines)


def memory_get_briefing() -> str:
    """Tool: Get daily briefing."""
    return memory.get_daily_briefing()


def memory_save_preference(key: str, value: str) -> str:
    """Tool: Save user preference."""
    success = memory.save_preference(key, value)
    return f"Preference saved: {key} = {value}" if success else "Failed to save preference."


def memory_export() -> str:
    """Tool: Export memory to readable text file."""
    return memory.export_to_readable()


def memory_save_permanent(info: str, category: str = "general") -> str:
    """Tool: Save information permanently."""
    return memory.save_permanent_info(info, category)


# Tool registry
MEMORY_REGISTRY = {
    "memory_add_todo": memory_add_todo,
    "memory_get_todos": memory_get_todos,
    "memory_add_note": memory_add_note,
    "memory_search_notes": memory_search_notes,
    "memory_get_briefing": memory_get_briefing,
    "memory_save_preference": memory_save_preference,
    "memory_export": memory_export,
    "memory_save_permanent": memory_save_permanent,
}
