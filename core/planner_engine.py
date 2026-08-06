"""planner_engine — Planning engine for complex task execution.

DEPRECATED: This is the legacy planner being replaced by execution_first intent classification.

Handles single-step, multi-step, conditional, and iterative plans.
Analyzes user intent, selects tools, handles dependencies, and plans verification.

TODO: Migrate planning logic to execution_first.Intent and dynamic reasoning levels.
"""

from __future__ import annotations

import json
import logging
import asyncio
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import time

from core.tools import tool_registry, ToolResult
from core.context_engine import context_engine

logger = logging.getLogger(__name__)


class PlanType(Enum):
    """Types of plans."""
    SINGLE_STEP = "single_step"
    MULTI_STEP = "multi_step"
    CONDITIONAL = "conditional"
    ITERATIVE = "iterative"
    PARALLEL = "parallel"


@dataclass
class PlanStep:
    """Represents a single step in a plan."""
    step_id: str
    tool_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    condition: Optional[str] = None
    verification: Optional[str] = None
    timeout: float = 30.0
    retry_count: int = 3
    description: str = ""


@dataclass
class ExecutionPlan:
    """Represents a complete execution plan."""
    plan_id: str
    plan_type: PlanType
    steps: List[PlanStep] = field(default_factory=list)
    description: str = ""
    estimated_time: float = 0.0
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanResult:
    """Result of plan execution."""
    plan_id: str
    success: bool = False
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    step_results: Dict[str, ToolResult] = field(default_factory=dict)
    total_time: float = 0.0
    error: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class PlannerEngine:
    """Planning engine for complex task execution."""
    
    def __init__(self):
        self._plans: Dict[str, ExecutionPlan] = {}
        self._plan_history: List[PlanResult] = []
        self._max_history = 100
        
    def create_plan(self, user_input: str, intent: str = "", tool: str = "", 
                    parameters: Dict[str, Any] = None) -> ExecutionPlan:
        """Create an execution plan based on user input."""
        parameters = parameters or {}
        
        # Analyze complexity
        if self._is_single_step(tool, parameters):
            return self._create_single_step_plan(tool, parameters, user_input)
        elif self._is_multi_step(user_input):
            return self._create_multi_step_plan(user_input, tool, parameters)
        elif self._is_conditional(user_input):
            return self._create_conditional_plan(user_input, tool, parameters)
        elif self._is_iterative(user_input):
            return self._create_iterative_plan(user_input, tool, parameters)
        else:
            return self._create_single_step_plan(tool, parameters, user_input)
    
    def _is_single_step(self, tool: str, parameters: Dict[str, Any]) -> bool:
        """Check if this is a single-step operation."""
        # Most tool calls are single-step by default
        return True
    
    def _is_multi_step(self, user_input: str) -> bool:
        """Check if this requires multiple steps.
        
        DEPRECATED: Uses keyword matching. Should be replaced with semantic analysis.
        TODO: Replace with execution_first.Intent classification.
        """
        # Keyword matching removed - always return False to avoid multi-step
        # Multi-step planning should be handled by execution_first runtime
        return False
    
    def _is_conditional(self, user_input: str) -> bool:
        """Check if this requires conditional logic.
        
        DEPRECATED: Uses keyword matching. Should be replaced with semantic analysis.
        TODO: Replace with execution_first.Intent classification.
        """
        # Keyword matching removed - always return False to avoid conditional
        # Conditional planning should be handled by execution_first runtime
        return False
    
    def _is_iterative(self, user_input: str) -> bool:
        """Check if this requires iteration.
        
        DEPRECATED: Uses keyword matching. Should be replaced with semantic analysis.
        TODO: Replace with execution_first.Intent classification.
        """
        # Keyword matching removed - always return False to avoid iterative
        # Iterative planning should be handled by execution_first runtime
        return False
    
    def _create_single_step_plan(self, tool: str, parameters: Dict[str, Any], 
                                 user_input: str) -> ExecutionPlan:
        """Create a single-step plan."""
        plan_id = f"plan_{int(time.time() * 1000)}"
        
        step = PlanStep(
            step_id=f"step_1",
            tool_name=tool,
            parameters=parameters,
            description=f"Execute {tool} with parameters {parameters}"
        )
        
        return ExecutionPlan(
            plan_id=plan_id,
            plan_type=PlanType.SINGLE_STEP,
            steps=[step],
            description=f"Single-step: {tool}",
            estimated_time=5.0
        )
    
    def _create_multi_step_plan(self, user_input: str, tool: str, 
                               parameters: Dict[str, Any]) -> ExecutionPlan:
        """Create a multi-step plan.
        
        DEPRECATED: Uses keyword matching patterns. Should be replaced with semantic analysis.
        TODO: Replace with execution_first.Intent classification and dynamic reasoning.
        """
        # Keyword matching removed - fall back to single-step
        # Multi-step planning should be handled by execution_first runtime
        return self._create_single_step_plan(tool, parameters, user_input)
    
    def _create_conditional_plan(self, user_input: str, tool: str, 
                                 parameters: Dict[str, Any]) -> ExecutionPlan:
        """Create a conditional plan.
        
        DEPRECATED: Uses keyword matching patterns. Should be replaced with semantic analysis.
        TODO: Replace with execution_first.Intent classification and dynamic reasoning.
        """
        # Keyword matching removed - fall back to single-step
        # Conditional planning should be handled by execution_first runtime
        return self._create_single_step_plan(tool, parameters, user_input)
    
    def _create_iterative_plan(self, user_input: str, tool: str, 
                               parameters: Dict[str, Any]) -> ExecutionPlan:
        """Create an iterative plan.
        
        DEPRECATED: Uses keyword matching patterns. Should be replaced with semantic analysis.
        TODO: Replace with execution_first.Intent classification and dynamic reasoning.
        """
        # Keyword matching removed - fall back to single-step
        # Iterative planning should be handled by execution_first runtime
        return self._create_single_step_plan(tool, parameters, user_input)
    
    def _extract_search_query(self, user_input: str) -> str:
        """Extract search query from user input.
        
        DEPRECATED: Uses keyword matching. Should be replaced with semantic analysis.
        TODO: Replace with execution_first.Intent entity extraction.
        """
        # Keyword matching removed - return empty string
        # Entity extraction should be handled by execution_first runtime
        return ""
    
    async def execute_plan(self, plan: ExecutionPlan) -> PlanResult:
        """Execute an execution plan."""
        result = PlanResult(plan_id=plan.plan_id)
        start_time = time.time()
        
        try:
            # Execute steps in order
            for step in plan.steps:
                # Check dependencies
                if not self._check_dependencies(step, result.completed_steps):
                    logger.warning(f"Step {step.step_id} dependencies not met")
                    result.failed_steps.append(step.step_id)
                    continue
                
                # Check condition if present
                if step.condition and not self._evaluate_condition(step.condition):
                    logger.info(f"Step {step.step_id} condition not met, skipping")
                    continue
                
                # Execute step
                step_result = await self._execute_step(step)
                result.step_results[step.step_id] = step_result
                
                if step_result.success:
                    result.completed_steps.append(step.step_id)
                else:
                    result.failed_steps.append(step.step_id)
                    
                    # Retry if configured
                    if step.retry_count > 0:
                        for retry in range(step.retry_count):
                            logger.info(f"Retrying step {step.step_id}, attempt {retry + 1}")
                            await asyncio.sleep(1)
                            step_result = await self._execute_step(step)
                            result.step_results[f"{step.step_id}_retry_{retry}"] = step_result
                            
                            if step_result.success:
                                result.completed_steps.append(step.step_id)
                                break
                    else:
                        # Stop on failure
                        logger.error(f"Step {step.step_id} failed, stopping plan")
                        break
            
            result.success = len(result.failed_steps) == 0
            result.total_time = time.time() - start_time
            
            # Store plan
            self._plans[plan.plan_id] = plan
            self._plan_history.append(result)
            
            # Trim history
            if len(self._plan_history) > self._max_history:
                self._plan_history = self._plan_history[-self._max_history:]
            
            return result
            
        except Exception as e:
            logger.error(f"Plan execution failed: {e}")
            result.success = False
            result.error = str(e)
            result.total_time = time.time() - start_time
            return result
    
    def _check_dependencies(self, step: PlanStep, completed_steps: List[str]) -> bool:
        """Check if step dependencies are met."""
        for dep in step.depends_on:
            if dep not in completed_steps:
                return False
        return True
    
    def _evaluate_condition(self, condition: str) -> bool:
        """Evaluate a condition string."""
        # Simple condition evaluation
        # In production, use proper expression evaluation
        context = context_engine.get_context()
        
        if "chrome_running" in condition:
            return context.get("active_app", "") == "chrome"
        
        return True
    
    async def _execute_step(self, step: PlanStep) -> ToolResult:
        """Execute a single plan step."""
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    tool_registry.execute,
                    step.tool_name,
                    **step.parameters
                ),
                timeout=step.timeout
            )
            return result
        except asyncio.TimeoutError:
            return ToolResult(success=False, error=f"Step {step.step_id} timed out")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    def get_plan(self, plan_id: str) -> Optional[ExecutionPlan]:
        """Get a plan by ID."""
        return self._plans.get(plan_id)
    
    def get_plan_history(self, limit: int = 20) -> List[PlanResult]:
        """Get recent plan execution history."""
        return self._plan_history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get planning statistics."""
        total_plans = len(self._plan_history)
        successful = sum(1 for p in self._plan_history if p.success)
        
        plan_type_counts = {}
        for result in self._plan_history:
            plan = self._plans.get(result.plan_id)
            if plan:
                plan_type = plan.plan_type.value
                plan_type_counts[plan_type] = plan_type_counts.get(plan_type, 0) + 1
        
        return {
            "total_plans": total_plans,
            "successful_plans": successful,
            "success_rate": successful / total_plans if total_plans > 0 else 0,
            "plan_type_distribution": plan_type_counts,
            "average_execution_time": sum(p.total_time for p in self._plan_history) / total_plans if total_plans > 0 else 0
        }


# Global planner engine instance
planner_engine = PlannerEngine()