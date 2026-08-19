"""core/execute_engine.py — Execute Engine for JARVIS vNext++.

Integrates <execute> tag parsing with the existing code execution fallback system.
Provides secure, validated execution of shell and code commands.
"""

from __future__ import annotations

import logging
import time
import subprocess
import sys
import os
from typing import Any, Dict, Optional
from dataclasses import dataclass

from core.execute_parser import ExecuteRequest, execute_parser
from core.code_execution_fallback import execute_code, detect_language

logger = logging.getLogger(__name__)


@dataclass
class ExecuteResult:
    """Structured execution result."""
    execution_type: str
    command: str
    status: str  # "success" or "failed"
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    error: Optional[str] = None


class ExecuteEngine:
    """Executes commands from <execute> tags using existing infrastructure."""

    # Shell command execution timeout
    SHELL_TIMEOUT = 30

    # Map execute types to execution methods
    TYPE_MAPPING = {
        "bash": "_execute_shell",
        "sh": "_execute_shell",
        "cmd": "_execute_shell",
        "powershell": "_execute_powershell",
        "python": "_execute_code",
        "node": "_execute_code",
        "javascript": "_execute_code",
    }

    def __init__(self):
        pass

    def execute(self, request: ExecuteRequest) -> ExecuteResult:
        """Execute a parsed execute request.

        Args:
            request: Parsed ExecuteRequest from execute_parser

        Returns:
            ExecuteResult with execution details
        """
        if not request.is_valid:
            return ExecuteResult(
                execution_type=request.execution_type,
                command=request.command,
                status="failed",
                exit_code=-1,
                stdout="",
                stderr="",
                duration_ms=0,
                error=request.error
            )

        start = time.time()
        
        try:
            # Route to appropriate execution method
            executor_method = getattr(self, self.TYPE_MAPPING.get(request.execution_type, "_execute_shell"), None)
            
            if executor_method is None:
                return ExecuteResult(
                    execution_type=request.execution_type,
                    command=request.command,
                    status="failed",
                    exit_code=-1,
                    stdout="",
                    stderr="",
                    duration_ms=0,
                    error=f"No executor for type: {request.execution_type}"
                )

            result = executor_method(request)
            duration_ms = (time.time() - start) * 1000
            result.duration_ms = duration_ms
            
            logger.info(
                "[EXECUTE_ENGINE] Type=%s, Command=%s, Status=%s, Duration=%.2fms",
                request.execution_type,
                request.command[:50],
                result.status,
                duration_ms
            )
            
            return result
            
        except Exception as exc:
            duration_ms = (time.time() - start) * 1000
            logger.error("[EXECUTE_ENGINE] Execution failed: %s", exc)
            return ExecuteResult(
                execution_type=request.execution_type,
                command=request.command,
                status="failed",
                exit_code=-1,
                stdout="",
                stderr=str(exc),
                duration_ms=duration_ms,
                error=str(exc)
            )

    def _execute_shell(self, request: ExecuteRequest) -> ExecuteResult:
        """Execute shell commands (bash, sh, cmd)."""
        try:
            # Determine shell based on type and platform
            if request.execution_type in ("bash", "sh"):
                if sys.platform == "win32":
                    shell = ["powershell", "-Command"]
                    command = request.command
                else:
                    shell = ["/bin/bash", "-c"]
                    command = request.command
            elif request.execution_type == "cmd":
                shell = ["cmd", "/c"]
                command = request.command
            else:
                shell = ["/bin/sh", "-c"]
                command = request.command

            # Execute with timeout
            result = subprocess.run(
                shell + [command],
                capture_output=True,
                text=True,
                timeout=self.SHELL_TIMEOUT,
                shell=False
            )

            return ExecuteResult(
                execution_type=request.execution_type,
                command=request.command,
                status="success" if result.returncode == 0 else "failed",
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_ms=0  # Will be set by caller
            )
            
        except subprocess.TimeoutExpired:
            return ExecuteResult(
                execution_type=request.execution_type,
                command=request.command,
                status="failed",
                exit_code=-1,
                stdout="",
                stderr="Command timed out",
                duration_ms=0,
                error="Command timed out"
            )
        except Exception as exc:
            return ExecuteResult(
                execution_type=request.execution_type,
                command=request.command,
                status="failed",
                exit_code=-1,
                stdout="",
                stderr=str(exc),
                duration_ms=0,
                error=str(exc)
            )

    def _execute_powershell(self, request: ExecuteRequest) -> ExecuteResult:
        """Execute PowerShell commands."""
        try:
            result = subprocess.run(
                ["powershell", "-Command", request.command],
                capture_output=True,
                text=True,
                timeout=self.SHELL_TIMEOUT
            )

            return ExecuteResult(
                execution_type=request.execution_type,
                command=request.command,
                status="success" if result.returncode == 0 else "failed",
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_ms=0
            )
            
        except subprocess.TimeoutExpired:
            return ExecuteResult(
                execution_type=request.execution_type,
                command=request.command,
                status="failed",
                exit_code=-1,
                stdout="",
                stderr="Command timed out",
                duration_ms=0,
                error="Command timed out"
            )
        except Exception as exc:
            return ExecuteResult(
                execution_type=request.execution_type,
                command=request.command,
                status="failed",
                exit_code=-1,
                stdout="",
                stderr=str(exc),
                duration_ms=0,
                error=str(exc)
            )

    def _execute_code(self, request: ExecuteRequest) -> ExecuteResult:
        """Execute code using existing code execution fallback."""
        try:
            # Map execute types to code execution languages
            lang_mapping = {
                "python": "python",
                "node": "javascript",
                "javascript": "javascript",
            }
            
            language = lang_mapping.get(request.execution_type, "python")
            
            # Use existing code execution fallback
            code_result = execute_code(
                code=request.command,
                language=language,
                timeout=self.SHELL_TIMEOUT
            )
            
            return ExecuteResult(
                execution_type=request.execution_type,
                command=request.command,
                status="success" if code_result.success else "failed",
                exit_code=code_result.exit_code,
                stdout=code_result.stdout,
                stderr=code_result.stderr,
                duration_ms=code_result.execution_time_ms,
                error=code_result.error if not code_result.success else None
            )
            
        except Exception as exc:
            return ExecuteResult(
                execution_type=request.execution_type,
                command=request.command,
                status="failed",
                exit_code=-1,
                stdout="",
                stderr=str(exc),
                duration_ms=0,
                error=str(exc)
            )


execute_engine = ExecuteEngine()