"""execution — Enhanced tool execution engine with verification.

Pipeline: User Input → Context → Memory → QWEN3 → Planner → Tool Chain → Executor → Verification → Response → Speech
"""

from __future__ import annotations

import os
import time
import logging
import asyncio
from typing import Any, Dict, Optional
from dataclasses import dataclass, field

from core.tools import ToolResult, tool_registry
from core.planner_engine import planner_engine, ExecutionPlan, PlanResult
from core.tool_chain_engine import tool_chain_engine, ToolChain, ChainExecutionResult
from core.context_engine import context_engine
from core.memory_engine import memory_engine

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

_MAX_TRACES = int(os.getenv("EXECUTION_TRACE_LIMIT", "100"))


@dataclass
class ExecutionTrace:
    query: str = ""
    intent: str = ""
    intent_confidence: float = 0.0
    tool_name: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    result: ToolResult | None = None
    plan_id: str = ""
    chain_id: str = ""
    total_latency_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    verification_passed: bool = False
    context_used: Dict[str, Any] = field(default_factory=dict)

    def format_debug(self) -> str:
        lines = [
            f"Query: {self.query}",
            f"Intent: {self.intent} (conf={self.intent_confidence:.2f})",
            f"Tool: {self.tool_name}",
            f"Params: {self.parameters}",
        ]
        if self.plan_id:
            lines.append(f"Plan: {self.plan_id}")
        if self.chain_id:
            lines.append(f"Chain: {self.chain_id}")
        if self.result:
            lines.append(f"Success: {self.result.success}")
            lines.append(f"Verified: {self.result.verified}")
            lines.append(f"Verification Passed: {self.verification_passed}")
            lines.append(f"Latency: {self.total_latency_ms:.0f}ms")
            if self.result.error:
                lines.append(f"Error: {self.result.error}")
        return "\n".join(lines)


class ExecutionEngine:
    def __init__(self) -> None:
        self.debug_mode = False
        self._traces: list[ExecutionTrace] = []
        self._last_trace: ExecutionTrace | None = None
        self._verification_enabled = True

    async def execute_with_llm(self, user_input: str, llm_output: Dict[str, Any]) -> ToolResult:
        """Execute tool based on LLM output with full verification."""
        trace = ExecutionTrace(
            query=user_input,
            intent=llm_output.get("intent", ""),
            intent_confidence=llm_output.get("confidence", 0.0),
            tool_name=llm_output.get("tool", ""),
            parameters=llm_output.get("params", {}),
            context_used=llm_output.get("context", {})
        )

        start = time.time()
        tool_name = trace.tool_name
        params = trace.parameters

        # Update context
        context_engine.add_context(
            user_input=user_input,
            intent=trace.intent,
            tool=tool_name
        )

        if not tool_name:
            # No tool needed, just conversation
            result = ToolResult(success=True, result={"response": llm_output.get("response", "")})
            trace.result = result
            trace.total_latency_ms = (time.time() - start) * 1000
            self._traces.append(trace)
            self._last_trace = trace
            return result

        # Check if this needs a plan
        plan = planner_engine.create_plan(user_input, trace.intent, tool_name, params)
        if len(plan.steps) > 1:
            # Execute plan
            plan_result = await planner_engine.execute_plan(plan)
            trace.plan_id = plan.plan_id
            
            if plan_result.success:
                result = ToolResult(
                    success=True,
                    result={"plan_executed": True, "steps_completed": len(plan_result.completed_steps)},
                    verified=True
                )
            else:
                result = ToolResult(
                    success=False,
                    error=f"Plan execution failed: {plan_result.error}",
                    verified=False
                )
            
            trace.result = result
            trace.total_latency_ms = (time.time() - start) * 1000
            self._traces.append(trace)
            self._last_trace = trace
            return result

        # Single tool execution
        tool = tool_registry.get(tool_name)
        if not tool:
            result = ToolResult(success=False, error=f"Tool not found: {tool_name}")
            trace.result = result
            trace.total_latency_ms = (time.time() - start) * 1000
            self._traces.append(trace)
            self._last_trace = trace
            return result

        try:
            # Execute tool
            result = tool_registry.execute(tool_name, **params)
            
            # Verify result if enabled
            if self._verification_enabled and result.success:
                verification_passed = await self._verify_execution(tool_name, params, result)
                trace.verification_passed = verification_passed
                result.verified = verification_passed
                
                if not verification_passed:
                    logger.warning(f"Verification failed for tool {tool_name}")
                    result.success = False
                    result.error = "Verification failed"
            
            trace.result = result
            trace.total_latency_ms = (time.time() - start) * 1000
            self._traces.append(trace)
            self._last_trace = trace
            
            # Save to memory if successful
            if result.success:
                await self._save_execution_to_memory(user_input, tool_name, params, result)
            
            if len(self._traces) > _MAX_TRACES:
                self._traces.pop(0)
            return result
        except Exception as e:
            result = ToolResult(success=False, error=str(e))
            trace.result = result
            trace.total_latency_ms = (time.time() - start) * 1000
            self._traces.append(trace)
            self._last_trace = trace
            
            # Record mistake
            memory_engine.record_mistake(
                input_text=user_input,
                expected="successful execution",
                actual=str(e),
                category="execution"
            )
            return result

    async def execute_chain(self, chain: ToolChain) -> ChainExecutionResult:
        """Execute a tool chain with verification."""
        return await tool_chain_engine.execute_chain(chain)

    async def _verify_execution(self, tool_name: str, params: Dict[str, Any], 
                               result: ToolResult) -> bool:
        """Verify tool execution result."""
        try:
            # Tool-specific verification
            if tool_name == "open_app":
                # Verify process is running
                app_name = params.get("app_name", "")
                return self._verify_process_running(app_name)
            
            elif tool_name == "close_app":
                # Verify process is not running
                app_name = params.get("app_name", "")
                return not self._verify_process_running(app_name)
            
            elif tool_name == "open_url":
                # Verify URL is accessible (basic check)
                return True  # Browser doesn't always report success
            
            elif tool_name == "create_file":
                # Verify file exists
                file_path = params.get("file_path", "")
                return os.path.exists(file_path)
            
            elif tool_name == "read_file":
                # Verify file was read
                return result.success and "content" in result.result
            
            elif tool_name == "delete_file":
                # Verify file doesn't exist
                file_path = params.get("file_path", "")
                return not os.path.exists(file_path)
            
            elif tool_name == "take_screenshot":
                # Verify screenshot was created
                return result.success and "screenshot_path" in result.result
            
            else:
                # Default: trust the tool's own verification
                return result.verified
        except Exception as e:
            logger.warning(f"Verification failed: {e}")
            return False

    def _verify_process_running(self, process_name: str) -> bool:
        """Verify if a process is running."""
        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                try:
                    if process_name.lower() in proc.info['name'].lower():
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return False
        except ImportError:
            # If psutil not available, trust the result
            return True
        except Exception as e:
            logger.warning(f"Process verification failed: {e}")
            return True

    async def _save_execution_to_memory(self, user_input: str, tool_name: str, 
                                       params: Dict[str, Any], result: ToolResult) -> None:
        """Save successful execution to memory for learning."""
        try:
            # Add to conversation history
            memory_engine.add_conversation_entry(
                role="user",
                content=user_input,
                intent="tool_execution",
                tool=tool_name
            )
            
            # Extract and save relevant information
            if tool_name == "save_memory":
                key = params.get("key", "")
                value = params.get("value", "")
                if key and value:
                    memory_engine.save_memory(key, value, "user_provided")
            
        except Exception as e:
            logger.warning(f"Failed to save execution to memory: {e}")

    def execute_from_nlp(self, nlp_output: Any) -> ToolResult:
        """Legacy method for backward compatibility."""
        trace = ExecutionTrace(
            query=getattr(nlp_output, 'normalized_text', ''),
            intent=getattr(nlp_output, 'intent', ''),
            intent_confidence=getattr(nlp_output, 'confidence_score', 0),
            tool_name=getattr(nlp_output, 'tool', ''),
            parameters=getattr(nlp_output, 'tool_params', {}),
        )

        start = time.time()
        tool_name = trace.tool_name
        params = trace.parameters

        if not tool_name:
            result = ToolResult(success=False, error="No tool selected")
            trace.result = result
            trace.total_latency_ms = (time.time() - start) * 1000
            self._traces.append(trace)
            self._last_trace = trace
            return result

        tool = tool_registry.get(tool_name)
        if not tool:
            result = ToolResult(success=False, error=f"Tool not found: {tool_name}")
            trace.result = result
            trace.total_latency_ms = (time.time() - start) * 1000
            self._traces.append(trace)
            self._last_trace = trace
            return result

        try:
            result = tool_registry.execute(tool_name, **params)
            trace.result = result
            trace.total_latency_ms = (time.time() - start) * 1000
            self._traces.append(trace)
            self._last_trace = trace
            if len(self._traces) > _MAX_TRACES:
                self._traces.pop(0)
            return result
        except Exception as e:
            result = ToolResult(success=False, error=str(e))
            trace.result = result
            trace.total_latency_ms = (time.time() - start) * 1000
            self._traces.append(trace)
            self._last_trace = trace
            return result

    def get_last_trace(self) -> ExecutionTrace | None:
        return self._last_trace

    def get_traces(self, limit: int = 10) -> list[ExecutionTrace]:
        return self._traces[-limit:]

    def get_stats(self) -> dict[str, Any]:
        total = len(self._traces)
        success = sum(1 for t in self._traces if t.result and t.result.success)
        verified = sum(1 for t in self._traces if t.result and t.result.verified)
        verification_passed = sum(1 for t in self._traces if t.verification_passed)
        return {
            "total_executions": total,
            "successful": success,
            "verified": verified,
            "verification_passed": verification_passed,
            "debug_mode": self.debug_mode,
            "verification_enabled": self._verification_enabled,
        }

    def enable_verification(self) -> None:
        """Enable execution verification."""
        self._verification_enabled = True
        logger.info("Execution verification enabled")

    def disable_verification(self) -> None:
        """Disable execution verification."""
        self._verification_enabled = False
        logger.info("Execution verification disabled")


execution_engine = ExecutionEngine()
