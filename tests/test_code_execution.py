"""tests/test_code_execution.py — Tests for code execution fallback subsystem.

Covers: language detection, syntax validation, safety checks, execution,
        timeout, stdout/stderr capture, cleanup, and verification.
"""

import sys
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.code_execution_fallback import (
    detect_language,
    validate_syntax,
    check_safety,
    execute_code,
    CodeExecutionResult,
    _LANGUAGES,
)


class TestLanguageDetection:
    def test_detect_python(self):
        assert detect_language("import os\nprint('hello')") == "python"

    def test_detect_javascript(self):
        assert detect_language("const x = 1;\nconsole.log(x);") == "javascript"

    def test_detect_java(self):
        assert detect_language("public class Main {\n  public static void main(String[] args) {}\n}") == "java"

    def test_detect_cpp(self):
        assert detect_language("#include <iostream>\nint main() { return 0; }") == "cpp"

    def test_detect_batch(self):
        assert detect_language("@echo off\necho hello") == "batch"

    def test_detect_powershell(self):
        assert detect_language("Write-Output 'hello'") == "powershell"

    def test_detect_default_python(self):
        """Unknown code should default to python."""
        assert detect_language("something unknown") == "python"


class TestSyntaxValidation:
    def test_valid_python(self):
        ok, err = validate_syntax("x = 1\nprint(x)", "python")
        assert ok is True
        assert err == ""

    def test_invalid_python(self):
        ok, err = validate_syntax("def foo(\n  pass", "python")
        assert ok is False
        assert "syntax error" in err.lower()

    def test_batch_always_valid(self):
        ok, err = validate_syntax("echo hello", "batch")
        assert ok is True

    def test_powershell_always_valid(self):
        ok, err = validate_syntax("Write-Output 'hi'", "powershell")
        assert ok is True


class TestSafetyChecks:
    def test_safe_code(self):
        ok, err = check_safety("x = 1 + 2\nprint(x)")
        assert ok is True

    def test_os_system_blocked(self):
        ok, err = check_safety('os.system("rm -rf /")')
        assert ok is False
        assert "dangerous" in err.lower()

    def test_eval_blocked(self):
        ok, err = check_safety('eval("1+1")')
        assert ok is False

    def test_exec_blocked(self):
        ok, err = check_safety('exec("import os")')
        assert ok is False

    def test_subprocess_blocked(self):
        ok, err = check_safety('subprocess.run(["ls"])')
        assert ok is False

    def test_shutil_rmtree_blocked(self):
        ok, err = check_safety('shutil.rmtree("/tmp")')
        assert ok is False

    def test_socket_blocked(self):
        ok, err = check_safety('import socket\ns = socket.socket()')
        assert ok is False


class TestCodeExecution:
    def test_python_success(self):
        result = execute_code("print('hello world')", language="python")
        assert result.success is True
        assert "hello world" in result.stdout
        assert result.exit_code == 0
        assert result.verification_passed is True

    def test_python_calculation(self):
        result = execute_code("print(2 + 2)", language="python")
        assert result.success is True
        assert "4" in result.stdout

    def test_python_error(self):
        result = execute_code("print(undefined_var)", language="python")
        assert result.success is False
        assert result.exit_code != 0

    def test_python_syntax_error(self):
        result = execute_code("def foo(\n  pass", language="python")
        assert result.success is False
        assert "syntax error" in result.error.lower()

    def test_python_timeout(self):
        result = execute_code("import time; time.sleep(10)", language="python", timeout=2)
        assert result.success is False
        assert result.timeout is True

    def test_python_output_capture(self):
        result = execute_code("print('line1')\nprint('line2')", language="python")
        assert result.success is True
        assert "line1" in result.stdout
        assert "line2" in result.stdout

    def test_python_stderr_capture(self):
        result = execute_code("import sys; sys.stderr.write('error msg')", language="python")
        assert "error msg" in result.stderr

    def test_unsupported_language(self):
        result = execute_code("hello", language="brainfuck")
        assert result.success is False
        assert "Unsupported" in result.error

    def test_dangerous_code_blocked(self):
        result = execute_code('import os; os.system("rm -rf /")', language="python")
        assert result.success is False
        assert "blocked" in result.error.lower() or "dangerous" in result.error.lower()

    def test_auto_detect_language(self):
        result = execute_code("print('auto detected')")
        assert result.success is True
        assert result.language == "python"

    def test_execution_time_tracked(self):
        result = execute_code("print('timing')", language="python")
        assert result.execution_time_ms > 0

    def test_result_to_dict(self):
        result = execute_code("print('test')", language="python")
        d = result.to_dict()
        assert "success" in d
        assert "language" in d
        assert "stdout" in d
        assert "exit_code" in d

    def test_empty_code(self):
        result = execute_code("", language="python")
        # Empty code is valid Python, should succeed
        assert result.success is True

    def test_output_capped(self):
        """Very long output should be capped at 2000 chars."""
        code = "print('x' * 5000)"
        result = execute_code(code, language="python")
        assert len(result.stdout) <= 2000

    def test_stderr_capped(self):
        """Very long stderr should be capped at 1000 chars."""
        code = "import sys; sys.stderr.write('e' * 5000)"
        result = execute_code(code, language="python")
        assert len(result.stderr) <= 1000


class TestSupportedLanguages:
    def test_python_supported(self):
        assert "python" in _LANGUAGES

    def test_javascript_supported(self):
        assert "javascript" in _LANGUAGES

    def test_batch_supported(self):
        assert "batch" in _LANGUAGES

    def test_powershell_supported(self):
        assert "powershell" in _LANGUAGES


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
