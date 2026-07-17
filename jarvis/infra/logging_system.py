"""Centralized Logging — Searchable, filterable, exportable log system.

Logs should never impact performance.
"""

from __future__ import annotations

import time
import logging
import threading
from typing import Any
from dataclasses import dataclass, field
from enum import Enum


class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class LogEntry:
    """Single log entry."""
    timestamp: float = 0.0
    level: LogLevel = LogLevel.INFO
    subsystem: str = ""
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class LogHandler(logging.Handler):
    """Python logging handler that feeds into CentralizedLogger."""

    def __init__(self, logger_instance: 'CentralizedLogger'):
        super().__init__()
        self._logger = logger_instance

    def emit(self, record: logging.LogRecord):
        level_map = {
            logging.DEBUG: LogLevel.DEBUG,
            logging.INFO: LogLevel.INFO,
            logging.WARNING: LogLevel.WARNING,
            logging.ERROR: LogLevel.ERROR,
            logging.CRITICAL: LogLevel.CRITICAL,
        }
        level = level_map.get(record.levelno, LogLevel.INFO)
        subsystem = record.name.split(".")[-1] if record.name else ""
        self._logger._add_entry(level, subsystem, record.getMessage())


class CentralizedLogger:
    """Centralized, searchable log system.

    Usage:
        logger = CentralizedLogger()
        logger.info("nlp", "Pipeline started")
        logger.error("router", "Provider failed", {"provider": "groq"})
        entries = logger.search("pipeline")
        logger.export("logs.json")
    """

    def __init__(self, max_entries: int = 10000):
        self._entries: list[LogEntry] = []
        self._max_entries = max_entries
        self._lock = threading.Lock()
        self._handler = LogHandler(self)
        self._handler.setLevel(logging.DEBUG)
        logging.root.addHandler(self._handler)

    def debug(self, subsystem: str, message: str, details: dict[str, Any] | None = None):
        self._add_entry(LogLevel.DEBUG, subsystem, message, details)

    def info(self, subsystem: str, message: str, details: dict[str, Any] | None = None):
        self._add_entry(LogLevel.INFO, subsystem, message, details)

    def warning(self, subsystem: str, message: str, details: dict[str, Any] | None = None):
        self._add_entry(LogLevel.WARNING, subsystem, message, details)

    def error(self, subsystem: str, message: str, details: dict[str, Any] | None = None):
        self._add_entry(LogLevel.ERROR, subsystem, message, details)

    def critical(self, subsystem: str, message: str, details: dict[str, Any] | None = None):
        self._add_entry(LogLevel.CRITICAL, subsystem, message, details)

    def _add_entry(self, level: LogLevel, subsystem: str, message: str, details: dict[str, Any] | None = None):
        entry = LogEntry(
            timestamp=time.time(),
            level=level,
            subsystem=subsystem,
            message=message,
            details=details or {},
        )
        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self._max_entries:
                self._entries = self._entries[-self._max_entries:]

    def search(self, query: str, limit: int = 50) -> list[LogEntry]:
        query_lower = query.lower()
        with self._lock:
            entries = [
                e for e in self._entries
                if query_lower in e.message.lower() or query_lower in e.subsystem.lower()
            ]
        return entries[-limit:]

    def filter(
        self,
        level: LogLevel | None = None,
        subsystem: str | None = None,
        limit: int = 50,
    ) -> list[LogEntry]:
        with self._lock:
            entries = list(self._entries)
        if level:
            entries = [e for e in entries if e.level == level]
        if subsystem:
            entries = [e for e in entries if e.subsystem == subsystem]
        return entries[-limit:]

    def get_recent(self, limit: int = 50) -> list[LogEntry]:
        with self._lock:
            return list(self._entries[-limit:])

    def get_subsystems(self) -> list[str]:
        with self._lock:
            return list({e.subsystem for e in self._entries if e.subsystem})

    def get_level_counts(self) -> dict[str, int]:
        with self._lock:
            counts: dict[str, int] = {}
            for e in self._entries:
                counts[e.level.value] = counts.get(e.level.value, 0) + 1
        return counts

    def export(self, path: str) -> int:
        """Export logs to JSON file. Returns number of entries exported."""
        import json
        with self._lock:
            entries = list(self._entries)
        data = [
            {
                "timestamp": e.timestamp,
                "level": e.level.value,
                "subsystem": e.subsystem,
                "message": e.message,
                "details": e.details,
            }
            for e in entries
        ]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return len(data)

    def clear(self):
        with self._lock:
            self._entries.clear()

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            entries = list(self._entries)
        return {
            "total_entries": len(entries),
            "levels": self.get_level_counts(),
            "subsystems": len(self.get_subsystems()),
        }


# Global instance
central_logger = CentralizedLogger()

__all__ = ["CentralizedLogger", "LogLevel", "LogEntry", "central_logger"]
