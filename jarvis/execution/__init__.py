"""Execution Layer — Tool-first execution with verification.

Every action goes through: Intent → Tool Selection → Execute → Verify → Respond.
The LLM NEVER claims an action occurred unless verified.
"""

from .tool_registry import ToolRegistry, ToolDef, ToolResult, ToolCategory, tool_registry
from .verifier import VerificationEngine, VerificationResult, VerificationType, verification_engine
from .engine import ExecutionEngine, ExecutionTrace, execution_engine
from .core_tools import register_all_tools

__all__ = [
    "ToolRegistry", "ToolDef", "ToolResult", "ToolCategory", "tool_registry",
    "VerificationEngine", "VerificationResult", "VerificationType", "verification_engine",
    "ExecutionEngine", "ExecutionTrace", "execution_engine",
    "register_all_tools",
]
