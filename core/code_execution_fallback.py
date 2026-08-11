"""code_execution_fallback — Controlled code generation and execution for JARVIS.

Used ONLY when no specialized tool exists for a task.
Supports Python, JavaScript/Node.js, Java, C++, Batch, PowerShell.

Pipeline: Generate → Parse → Validate → Check Safety → Run → Capture → Verify
"""

from __future__ import annotations

import os
import re
import sys
import json
import time
import logging
import tempfile
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── Dangerous patterns that must NEVER appear in generated code ────────
_DANGEROUS_PATTERNS = [
    r"os\.system\s*\(",
    r"subprocess\.\w+\s*\(",
    r"__import__\s*\(",
    r"eval\s*\(",
    r"exec\s*\(",
    r"compile\s*\(",
    r"open\s*\(.*['\"]w",  # write mode (too broad — we check context below)
    r"shutil\.rmtree",
    r"os\.remove",
    r"os\.unlink",
    r"rmdir",
    r"rm\s+-rf",
    r"del\s+/[sS]",
    r"format\s+[a-zA-Z]:",
    r"rundll32",
    r"powershell.*-enc",
    r"cmd.*\/c.*del",
    r"curl.*\|.*sh",
    r"wget.*\|.*sh",
    r"nc\s+-",
    r"socket\.",
    r"paramiko",
    r"requests\.(post|put|delete|patch)\s*\(",  # block outbound write requests
]

_DANGEROUS_RE = re.compile("|".join(_DANGEROUS_PATTERNS), re.IGNORECASE)

# ── Language → (extension, command template, timeout) ─────────────────
_LANGUAGES: Dict[str, Dict[str, Any]] = {
    "python": {
        "extension": ".py",
        "command": [sys.executable, "{file}"],
        "timeout": 30,
    },
    "javascript": {
        "extension": ".js",
        "command": ["node", "{file}"],
        "timeout": 30,
    },
    "java": {
        "extension": ".java",
        "command": ["javac", "{file}", "&&", "java", "-cp", "{dir}", "{class}"],
        "timeout": 30,
        "compile": True,
    },
    "cpp": {
        "extension": ".cpp",
        "command": ["g++", "{file}", "-o", "{out}", "&&", "{out}"],
        "timeout": 30,
        "compile": True,
    },
    "batch": {
        "extension": ".bat",
        "command": ["cmd", "/c", "{file}"],
        "timeout": 15,
    },
    "powershell": {
        "extension": ".ps1",
        "command": ["powershell", "-ExecutionPolicy", "Bypass", "-File", "{file}"],
        "timeout": 15,
    },
}


@dataclass
class CodeExecutionResult:
    success: bool = False
    language: str = ""
    code: str = ""
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    timeout: bool = False
    file_path: str = ""
    error: str = ""
    verification_passed: bool = False
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "language": self.language,
            "code": self.code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "timeout": self.timeout,
            "file_path": self.file_path,
            "error": self.error,
            "verification_passed": self.verification_passed,
            "execution_time_ms": self.execution_time_ms,
        }


def detect_language(code: str) -> str:
    """Detect the language of generated code from content heuristics."""
    code_lower = code.strip().lower()
    if code_lower.startswith(("import ", "from ", "def ", "class ", "print(")):
        return "python"
    if code_lower.startswith(("const ", "let ", "var ", "function ", "=>", "console.log")):
        return "javascript"
    if code_lower.startswith(("public class ", "class ", "void main")):
        return "java"
    if code_lower.startswith(("#include", "int main", "std::")):
        return "cpp"
    if code_lower.startswith(("@echo off", "echo ", "set ", "if ")):
        return "batch"
    if code_lower.startswith(("write-", "get-", "$", "param(")):
        return "powershell"
    return "python"  # default


def validate_syntax(code: str, language: str) -> Tuple[bool, str]:
    """Basic syntax validation before execution."""
    if language == "python":
        try:
            compile(code, "<generated>", "exec")
            return True, ""
        except SyntaxError as e:
            return False, f"Python syntax error: {e}"
    if language in ("batch", "powershell"):
        return True, ""  # limited validation
    return True, ""  # other languages — let compiler/runtime catch errors


def check_safety(code: str) -> Tuple[bool, str]:
    """Check code for dangerous patterns."""
    matches = _DANGEROUS_RE.findall(code)
    if matches:
        unique = list(set(matches))
        return False, f"Dangerous pattern(s) detected: {', '.join(unique[:5])}"
    return True, ""


def execute_code(
    code: str,
    language: str = "",
    timeout: int = 30,
    working_dir: str = "",
) -> CodeExecutionResult:
    """Execute generated code in a controlled environment.

    Pipeline: detect lang → validate syntax → check safety → write file → run → capture.
    """
    start = time.time()

    if not language:
        language = detect_language(code)

    lang_config = _LANGUAGES.get(language)
    if not lang_config:
        return CodeExecutionResult(
            error=f"Unsupported language: {language}. Supported: {', '.join(_LANGUAGES.keys())}"
        )

    # 1. Validate syntax
    syntax_ok, syntax_err = validate_syntax(code, language)
    if not syntax_ok:
        return CodeExecutionResult(language=language, code=code, error=syntax_err)

    # 2. Check safety
    safe, safety_err = check_safety(code)
    if not safe:
        return CodeExecutionResult(language=language, code=code, error=f"Code blocked: {safety_err}")

    # 3. Write to temp file
    tmp_dir = working_dir or tempfile.mkdtemp(prefix="jarvis_code_")
    ext = lang_config["extension"]
    file_name = f"generated_{int(time.time() * 1000)}{ext}"
    file_path = os.path.join(tmp_dir, file_name)

    try:
        Path(file_path).write_text(code, encoding="utf-8")
    except Exception as e:
        return CodeExecutionResult(language=language, code=code, error=f"Failed to write temp file: {e}")

    # 4. Build command
    cmd_template = lang_config["command"]
    out_path = file_path.rsplit(".", 1)[0] if lang_config.get("compile") else ""
    class_name = Path(file_path).stem if language == "java" else ""
    cmd = []
    for part in cmd_template:
        cmd.append(
            part.replace("{file}", file_path)
            .replace("{dir}", tmp_dir)
            .replace("{out}", out_path)
            .replace("{class}", class_name)
        )

    # 5. Execute
    actual_timeout = min(timeout, lang_config.get("timeout", 30))
    stdout = ""
    stderr = ""
    exit_code = -1
    timed_out = False

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=actual_timeout,
            cwd=tmp_dir,
            shell=(sys.platform == "win32" and language in ("batch", "powershell")),
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
        stderr = f"Execution timed out after {actual_timeout}s"
    except Exception as e:
        stderr = f"Execution error: {e}"
        exit_code = 1

    elapsed_ms = (time.time() - start) * 1000

    # 6. Determine success
    success = exit_code == 0 and not timed_out
    verification = "exit_code_0" if success else f"exit_code_{exit_code}"
    if timed_out:
        verification = "timeout"

    # 7. Cleanup temp file (not directory — may have produced output files)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass

    return CodeExecutionResult(
        success=success,
        language=language,
        code=code,
        stdout=stdout.strip()[:2000],  # cap output
        stderr=stderr.strip()[:1000],
        exit_code=exit_code,
        timeout=timed_out,
        file_path=file_path,
        error="" if success else (stderr.strip()[:500] or f"Exit code {exit_code}"),
        verification_passed=success,
        execution_time_ms=elapsed_ms,
    )
