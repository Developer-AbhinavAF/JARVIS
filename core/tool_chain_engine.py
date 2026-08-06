"""tool_chain_engine — Advanced tool chaining with data flow and error recovery.

DEPRECATED: This is the legacy tool chain engine being replaced by execution_first.

Supports:
- Sequential chains
- Parallel execution
- Conditional branching
- Data passing between steps
- Error recovery and rollback
- Chain templates
- Custom chains

TODO: Migrate tool chaining logic to execution_first dynamic reasoning.
"""

from __future__ import annotations

import json
import logging
import asyncio
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
import uuid

from core.tools import tool_registry, ToolResult
from core.context_engine import context_engine
from core.planner_engine import PlanStep, ExecutionPlan, PlanResult

logger = logging.getLogger(__name__)


class ChainType(Enum):
    """Types of tool chains."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    ITERATIVE = "iterative"
    HYBRID = "hybrid"


@dataclass
class ChainStep:
    """Represents a step in a tool chain."""
    step_id: str
    tool_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    input_mapping: Dict[str, str] = field(default_factory=dict)  # Map step outputs to inputs
    output_mapping: Dict[str, str] = field(default_factory=dict)  # Map outputs to variables
    depends_on: List[str] = field(default_factory=list)
    condition: Optional[str] = None
    timeout: float = 30.0
    retry_count: int = 3
    continue_on_failure: bool = False
    description: str = ""


@dataclass
class ToolChain:
    """Represents a complete tool chain."""
    chain_id: str
    chain_type: ChainType
    name: str
    steps: List[ChainStep] = field(default_factory=list)
    input_variables: Dict[str, Any] = field(default_factory=dict)
    output_variables: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChainExecutionResult:
    """Result of chain execution."""
    chain_id: str
    success: bool = False
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    step_results: Dict[str, ToolResult] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    total_time: float = 0.0
    error: str = ""
    rollback_performed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolChainEngine:
    """Advanced tool chaining engine."""
    
    def __init__(self):
        self._chains: Dict[str, ToolChain] = {}
        self._chain_templates: Dict[str, ToolChain] = {}
        self._execution_history: List[ChainExecutionResult] = []
        self._max_history = 100
        
        # Load default templates
        self._load_default_templates()
    
    def _load_default_templates(self) -> None:
        """Load default chain templates."""
        
        # Web Research Template
        web_research = ToolChain(
            chain_id="template_web_research",
            chain_type=ChainType.SEQUENTIAL,
            name="Web Research",
            description="Research a topic and save summary",
            steps=[
                ChainStep(
                    step_id="search",
                    tool_name="web_search",
                    parameters={"query": "{query}"},
                    output_mapping={"results": "search_results"},
                    description="Search web for query"
                ),
                ChainStep(
                    step_id="open_first",
                    tool_name="open_url",
                    parameters={"url": "{search_results[0]}"},
                    depends_on=["search"],
                    description="Open first result"
                ),
                ChainStep(
                    step_id="analyze",
                    tool_name="screen_analysis",
                    depends_on=["open_first"],
                    output_mapping={"analysis": "screen_analysis"},
                    description="Analyze screen content"
                ),
                ChainStep(
                    step_id="save",
                    tool_name="create_file",
                    parameters={"file_path": "{query}_research.txt", "content": "{screen_analysis}"},
                    depends_on=["analyze"],
                    description="Save research to file"
                )
            ]
        )
        self._chain_templates["web_research"] = web_research
        
        # Email Composition Template
        email_compose = ToolChain(
            chain_id="template_email_compose",
            chain_type=ChainType.SEQUENTIAL,
            name="Email Composition",
            description="Compose and send email",
            steps=[
                ChainStep(
                    step_id="get_email",
                    tool_name="recall_memory",
                    parameters={"query": "{recipient} email"},
                    output_mapping={"email": "recipient_email"},
                    description="Get recipient email from memory"
                ),
                ChainStep(
                    step_id="open_client",
                    tool_name="open_url",
                    parameters={"url": "gmail.com"},
                    depends_on=["get_email"],
                    description="Open email client"
                ),
                ChainStep(
                    step_id="compose",
                    tool_name="type_text",
                    parameters={"text": "{recipient_email}"},
                    depends_on=["open_client"],
                    description="Type recipient email"
                ),
                ChainStep(
                    step_id="subject",
                    tool_name="type_text",
                    parameters={"text": "{subject}"},
                    depends_on=["compose"],
                    description="Type subject"
                ),
                ChainStep(
                    step_id="body",
                    tool_name="type_text",
                    parameters={"text": "{body}"},
                    depends_on=["subject"],
                    description="Type email body"
                )
            ]
        )
        self._chain_templates["email_compose"] = email_compose
        
        # Video Watching Template
        video_watch = ToolChain(
            chain_id="template_video_watch",
            chain_type=ChainType.SEQUENTIAL,
            name="Video Watching",
            description="Search and play video",
            steps=[
                ChainStep(
                    step_id="search",
                    tool_name="search_youtube",
                    parameters={"query": "{query}"},
                    output_mapping={"results": "video_results"},
                    description="Search YouTube"
                ),
                ChainStep(
                    step_id="play",
                    tool_name="play_media",
                    parameters={"query": "{video_results[0]}"},
                    depends_on=["search"],
                    description="Play first result"
                )
            ]
        )
        self._chain_templates["video_watch"] = video_watch
        
        logger.info(f"Loaded {len(self._chain_templates)} chain templates")
    
    def create_chain(self, name: str, steps: List[ChainStep], 
                     chain_type: ChainType = ChainType.SEQUENTIAL,
                     description: str = "") -> ToolChain:
        """Create a new tool chain."""
        chain_id = f"chain_{uuid.uuid4().hex[:8]}"
        
        chain = ToolChain(
            chain_id=chain_id,
            chain_type=chain_type,
            name=name,
            steps=steps,
            description=description
        )
        
        self._chains[chain_id] = chain
        logger.info(f"Created chain: {name} ({chain_id})")
        return chain
    
    def create_chain_from_template(self, template_name: str, 
                                    variables: Dict[str, Any]) -> Optional[ToolChain]:
        """Create a chain from a template with variables."""
        template = self._chain_templates.get(template_name)
        if not template:
            logger.error(f"Template not found: {template_name}")
            return None
        
        # Clone template
        chain = ToolChain(
            chain_id=f"chain_{uuid.uuid4().hex[:8]}",
            chain_type=template.chain_type,
            name=f"{template.name}_instance",
            steps=[],
            input_variables=variables.copy(),
            description=template.description
        )
        
        # Substitute variables in steps
        for step in template.steps:
            # Substitute parameters
            substituted_params = {}
            for key, value in step.parameters.items():
                substituted_params[key] = self._substitute_variables(value, variables)
            
            chain_step = ChainStep(
                step_id=f"{step.step_id}_{uuid.uuid4().hex[:4]}",
                tool_name=step.tool_name,
                parameters=substituted_params,
                input_mapping=step.input_mapping.copy(),
                output_mapping=step.output_mapping.copy(),
                depends_on=step.depends_on.copy(),
                condition=step.condition,
                timeout=step.timeout,
                retry_count=step.retry_count,
                continue_on_failure=step.continue_on_failure,
                description=step.description
            )
            chain.steps.append(chain_step)
        
        self._chains[chain.chain_id] = chain
        logger.info(f"Created chain from template: {template_name}")
        return chain
    
    def _substitute_variables(self, value: Any, variables: Dict[str, Any]) -> Any:
        """Substitute variables in a value."""
        if isinstance(value, str):
            # Simple variable substitution {var}
            for var_name, var_value in variables.items():
                value = value.replace(f"{{{var_name}}}", str(var_value))
            return value
        elif isinstance(value, dict):
            return {k: self._substitute_variables(v, variables) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._substitute_variables(item, variables) for item in value]
        return value
    
    async def execute_chain(self, chain: ToolChain) -> ChainExecutionResult:
        """Execute a tool chain."""
        result = ChainExecutionResult(chain_id=chain.chain_id)
        result.variables = chain.input_variables.copy()
        start_time = time.time()
        
        try:
            if chain.chain_type == ChainType.SEQUENTIAL:
                await self._execute_sequential(chain, result)
            elif chain.chain_type == ChainType.PARALLEL:
                await self._execute_parallel(chain, result)
            elif chain.chain_type == ChainType.CONDITIONAL:
                await self._execute_conditional(chain, result)
            elif chain.chain_type == ChainType.ITERATIVE:
                await self._execute_iterative(chain, result)
            else:
                await self._execute_sequential(chain, result)
            
            result.success = len(result.failed_steps) == 0
            result.total_time = time.time() - start_time
            
            # Store in history
            self._execution_history.append(result)
            if len(self._execution_history) > self._max_history:
                self._execution_history = self._execution_history[-self._max_history:]
            
            return result
            
        except Exception as e:
            logger.error(f"Chain execution failed: {e}")
            result.success = False
            result.error = str(e)
            result.total_time = time.time() - start_time
            
            # Attempt rollback
            if len(result.completed_steps) > 0:
                await self._rollback_chain(chain, result)
            
            return result
    
    async def _execute_sequential(self, chain: ToolChain, result: ChainExecutionResult) -> None:
        """Execute chain sequentially."""
        for step in chain.steps:
            # Check dependencies
            if not self._check_dependencies(step, result.completed_steps):
                logger.warning(f"Step {step.step_id} dependencies not met")
                result.failed_steps.append(step.step_id)
                if not step.continue_on_failure:
                    break
                continue
            
            # Check condition
            if step.condition and not self._evaluate_condition(step.condition, result.variables):
                logger.info(f"Step {step.step_id} condition not met, skipping")
                continue
            
            # Execute step
            step_result = await self._execute_chain_step(step, result.variables)
            result.step_results[step.step_id] = step_result
            
            if step_result.success:
                result.completed_steps.append(step.step_id)
                
                # Map outputs to variables
                for var_name, result_key in step.output_mapping.items():
                    if result_key in step_result.result:
                        result.variables[var_name] = step_result.result[result_key]
            else:
                result.failed_steps.append(step.step_id)
                
                # Retry if configured
                if step.retry_count > 0:
                    for retry in range(step.retry_count):
                        logger.info(f"Retrying step {step.step_id}, attempt {retry + 1}")
                        await asyncio.sleep(1)
                        step_result = await self._execute_chain_step(step, result.variables)
                        result.step_results[f"{step.step_id}_retry_{retry}"] = step_result
                        
                        if step_result.success:
                            result.completed_steps.append(step.step_id)
                            break
                
                if not step.continue_on_failure:
                    logger.error(f"Step {step.step_id} failed, stopping chain")
                    break
    
    async def _execute_parallel(self, chain: ToolChain, result: ChainExecutionResult) -> None:
        """Execute chain steps in parallel."""
        # Group steps by dependency level
        levels = self._group_steps_by_level(chain.steps)
        
        for level_steps in levels:
            # Execute steps in this level in parallel
            tasks = [self._execute_chain_step(step, result.variables) for step in level_steps]
            step_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for step, step_result in zip(level_steps, step_results):
                if isinstance(step_result, Exception):
                    result.failed_steps.append(step.step_id)
                    result.step_results[step.step_id] = ToolResult(success=False, error=str(step_result))
                else:
                    result.step_results[step.step_id] = step_result
                    if step_result.success:
                        result.completed_steps.append(step.step_id)
                    else:
                        result.failed_steps.append(step.step_id)
    
    async def _execute_conditional(self, chain: ToolChain, result: ChainExecutionResult) -> None:
        """Execute chain with conditional logic."""
        for step in chain.steps:
            if step.condition and not self._evaluate_condition(step.condition, result.variables):
                continue
            
            step_result = await self._execute_chain_step(step, result.variables)
            result.step_results[step.step_id] = step_result
            
            if step_result.success:
                result.completed_steps.append(step.step_id)
            else:
                result.failed_steps.append(step.step_id)
    
    async def _execute_iterative(self, chain: ToolChain, result: ChainExecutionResult) -> None:
        """Execute chain iteratively."""
        # Simplified iterative execution
        # In production, implement proper iteration logic
        for step in chain.steps:
            step_result = await self._execute_chain_step(step, result.variables)
            result.step_results[step.step_id] = step_result
            
            if step_result.success:
                result.completed_steps.append(step.step_id)
            else:
                result.failed_steps.append(step.step_id)
    
    async def _execute_chain_step(self, step: ChainStep, variables: Dict[str, Any]) -> ToolResult:
        """Execute a single chain step."""
        try:
            # Substitute variables in parameters
            final_params = self._substitute_variables(step.parameters, variables)
            
            # Execute with timeout
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    tool_registry.execute,
                    step.tool_name,
                    **final_params
                ),
                timeout=step.timeout
            )
            return result
        except asyncio.TimeoutError:
            return ToolResult(success=False, error=f"Step {step.step_id} timed out")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    def _check_dependencies(self, step: ChainStep, completed_steps: List[str]) -> bool:
        """Check if step dependencies are met."""
        for dep in step.depends_on:
            if dep not in completed_steps:
                return False
        return True
    
    def _evaluate_condition(self, condition: str, variables: Dict[str, Any]) -> bool:
        """Evaluate a condition string."""
        # Simple condition evaluation
        # In production, use proper expression evaluation
        try:
            # Replace variables in condition
            for var_name, var_value in variables.items():
                condition = condition.replace(f"{{{var_name}}}", str(var_value))
            
            # Safe evaluation
            return eval(condition, {"__builtins__": {}}, variables)
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {e}")
            return False
    
    def _group_steps_by_level(self, steps: List[ChainStep]) -> List[List[ChainStep]]:
        """Group steps by dependency level for parallel execution."""
        levels = []
        remaining = steps.copy()
        
        while remaining:
            # Find steps with no dependencies or all dependencies met
            current_level = []
            for step in remaining:
                if not step.depends_on or all(dep in [s.step_id for s in current_level + sum(levels, [])] for dep in step.depends_on):
                    current_level.append(step)
            
            if not current_level:
                # Circular dependency or unresolved
                current_level = remaining[:1]
            
            levels.append(current_level)
            remaining = [s for s in remaining if s not in current_level]
        
        return levels
    
    async def _rollback_chain(self, chain: ToolChain, result: ChainExecutionResult) -> None:
        """Rollback completed steps."""
        logger.info(f"Rolling back chain {chain.chain_id}")
        result.rollback_performed = True
        
        # Execute rollback in reverse order
        for step_id in reversed(result.completed_steps):
            step = next((s for s in chain.steps if s.step_id == step_id), None)
            if step:
                # Simple rollback: log the step
                logger.info(f"Rollback step: {step_id}")
                # In production, implement actual rollback logic
    
    def get_chain(self, chain_id: str) -> Optional[ToolChain]:
        """Get a chain by ID."""
        return self._chains.get(chain_id)
    
    def get_template(self, template_name: str) -> Optional[ToolChain]:
        """Get a chain template by name."""
        return self._chain_templates.get(template_name)
    
    def list_templates(self) -> List[str]:
        """List available chain templates."""
        return list(self._chain_templates.keys())
    
    def get_execution_history(self, limit: int = 20) -> List[ChainExecutionResult]:
        """Get recent chain execution history."""
        return self._execution_history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get chain execution statistics."""
        total_chains = len(self._execution_history)
        successful = sum(1 for c in self._execution_history if c.success)
        
        chain_type_counts = {}
        for result in self._execution_history:
            chain = self._chains.get(result.chain_id)
            if chain:
                chain_type = chain.chain_type.value
                chain_type_counts[chain_type] = chain_type_counts.get(chain_type, 0) + 1
        
        return {
            "total_chains": total_chains,
            "successful_chains": successful,
            "success_rate": successful / total_chains if total_chains > 0 else 0,
            "chain_type_distribution": chain_type_counts,
            "average_execution_time": sum(c.total_time for c in self._execution_history) / total_chains if total_chains > 0 else 0,
            "available_templates": len(self._chain_templates)
        }


# Global tool chain engine instance
tool_chain_engine = ToolChainEngine()