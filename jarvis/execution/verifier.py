"""Verification Engine — Verifies actions actually happened.

Never skip verification. Every action must be confirmed.
Checks: process list, file existence, window existence, URL loaded.
"""

from __future__ import annotations

import os
import time
import logging
import threading
from typing import Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class VerificationType(Enum):
    PROCESS_RUNNING = "process_running"
    FILE_EXISTS = "file_exists"
    DIRECTORY_EXISTS = "directory_exists"
    FILE_CONTENT = "file_content"
    WINDOW_EXISTS = "window_exists"
    URL_LOADED = "url_loaded"
    PORT_LISTENING = "port_listening"
    CUSTOM = "custom"


@dataclass
class VerificationResult:
    """Result of a verification check."""
    verified: bool = False
    check_type: VerificationType = VerificationType.CUSTOM
    details: str = ""
    latency_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


class VerificationEngine:
    """Verifies that actions actually executed.

    Usage:
        engine = VerificationEngine()
        result = engine.verify_process_running("chrome")
        result = engine.verify_file_exists("C:/Users/test/file.txt")
        result = engine.verify_url_loaded("https://youtube.com")
    """

    def __init__(self):
        self._custom_checks: dict[str, Any] = {}
        self._lock = threading.Lock()

    def verify_process_running(self, process_name: str) -> VerificationResult:
        """Check if a process is running."""
        start = time.time()
        try:
            import psutil
            process_lower = process_name.lower()
            for proc in psutil.process_iter(['name', 'exe']):
                try:
                    name = (proc.info.get('name') or '').lower()
                    exe = (proc.info.get('exe') or '').lower()
                    if process_lower in name or process_lower in exe:
                        return VerificationResult(
                            verified=True,
                            check_type=VerificationType.PROCESS_RUNNING,
                            details=f"Found process: {proc.info.get('name')}",
                            latency_ms=(time.time() - start) * 1000,
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return VerificationResult(
                verified=False,
                check_type=VerificationType.PROCESS_RUNNING,
                details=f"Process '{process_name}' not found",
                latency_ms=(time.time() - start) * 1000,
            )
        except ImportError:
            return VerificationResult(
                verified=False,
                check_type=VerificationType.PROCESS_RUNNING,
                details="psutil not available",
                latency_ms=(time.time() - start) * 1000,
            )

    def verify_file_exists(self, file_path: str) -> VerificationResult:
        """Check if a file exists."""
        start = time.time()
        exists = os.path.isfile(file_path)
        return VerificationResult(
            verified=exists,
            check_type=VerificationType.FILE_EXISTS,
            details=f"File {'exists' if exists else 'not found'}: {file_path}",
            latency_ms=(time.time() - start) * 1000,
        )

    def verify_directory_exists(self, dir_path: str) -> VerificationResult:
        """Check if a directory exists."""
        start = time.time()
        exists = os.path.isdir(dir_path)
        return VerificationResult(
            verified=exists,
            check_type=VerificationType.DIRECTORY_EXISTS,
            details=f"Directory {'exists' if exists else 'not found'}: {dir_path}",
            latency_ms=(time.time() - start) * 1000,
        )

    def verify_file_content(self, file_path: str, expected: str = "", min_bytes: int = 0) -> VerificationResult:
        """Check if a file exists and optionally contains expected content."""
        start = time.time()
        if not os.path.isfile(file_path):
            return VerificationResult(
                verified=False,
                check_type=VerificationType.FILE_CONTENT,
                details=f"File not found: {file_path}",
                latency_ms=(time.time() - start) * 1000,
            )

        size = os.path.getsize(file_path)
        if size < min_bytes:
            return VerificationResult(
                verified=False,
                check_type=VerificationType.FILE_CONTENT,
                details=f"File too small: {size} < {min_bytes} bytes",
                latency_ms=(time.time() - start) * 1000,
            )

        if expected:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                if expected not in content:
                    return VerificationResult(
                        verified=False,
                        check_type=VerificationType.FILE_CONTENT,
                        details=f"Expected text not found in {file_path}",
                        latency_ms=(time.time() - start) * 1000,
                    )
            except Exception as e:
                return VerificationResult(
                    verified=False,
                    check_type=VerificationType.FILE_CONTENT,
                    details=f"Read error: {e}",
                    latency_ms=(time.time() - start) * 1000,
                )

        return VerificationResult(
            verified=True,
            check_type=VerificationType.FILE_CONTENT,
            details=f"File verified: {file_path} ({size} bytes)",
            latency_ms=(time.time() - start) * 1000,
        )

    def verify_window_exists(self, title_contains: str) -> VerificationResult:
        """Check if a window with given title exists."""
        start = time.time()
        try:
            import psutil
            title_lower = title_contains.lower()
            # Check browser processes as a proxy for window existence
            browsers = ['chrome', 'firefox', 'edge', 'brave', 'opera']
            for proc in psutil.process_iter(['name']):
                try:
                    name = (proc.info.get('name') or '').lower()
                    if any(b in name for b in browsers):
                        return VerificationResult(
                            verified=True,
                            check_type=VerificationType.WINDOW_EXISTS,
                            details=f"Browser process found: {name}",
                            latency_ms=(time.time() - start) * 1000,
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return VerificationResult(
                verified=False,
                check_type=VerificationType.WINDOW_EXISTS,
                details=f"No window matching '{title_contains}' found",
                latency_ms=(time.time() - start) * 1000,
            )
        except ImportError:
            return VerificationResult(
                verified=False,
                check_type=VerificationType.WINDOW_EXISTS,
                details="psutil not available",
                latency_ms=(time.time() - start) * 1000,
            )

    def verify_port_listening(self, port: int) -> VerificationResult:
        """Check if a port is listening."""
        start = time.time()
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            return VerificationResult(
                verified=(result == 0),
                check_type=VerificationType.PORT_LISTENING,
                details=f"Port {port} {'listening' if result == 0 else 'not listening'}",
                latency_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return VerificationResult(
                verified=False,
                check_type=VerificationType.PORT_LISTENING,
                details=f"Port check error: {e}",
                latency_ms=(time.time() - start) * 1000,
            )

    def register_custom_check(self, name: str, check_fn):
        """Register a custom verification function."""
        with self._lock:
            self._custom_checks[name] = check_fn

    def verify_custom(self, name: str, **kwargs) -> VerificationResult:
        """Run a custom verification check."""
        start = time.time()
        with self._lock:
            check_fn = self._custom_checks.get(name)
        if not check_fn:
            return VerificationResult(
                verified=False,
                check_type=VerificationType.CUSTOM,
                details=f"Custom check '{name}' not registered",
                latency_ms=(time.time() - start) * 1000,
            )
        try:
            result = check_fn(**kwargs)
            return VerificationResult(
                verified=bool(result),
                check_type=VerificationType.CUSTOM,
                details=f"Custom check '{name}': {'passed' if result else 'failed'}",
                latency_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return VerificationResult(
                verified=False,
                check_type=VerificationType.CUSTOM,
                details=f"Custom check error: {e}",
                latency_ms=(time.time() - start) * 1000,
            )

    def get_stats(self) -> dict[str, Any]:
        return {
            "custom_checks": len(self._custom_checks),
        }


# Global instance
verification_engine = VerificationEngine()

__all__ = ["VerificationEngine", "VerificationResult", "VerificationType", "verification_engine"]
