"""core/jarvis_core.py — Single Shared Core Entrypoint for JARVIS vNext++.

All interfaces (CLI, Desktop UI, REST API, Speech Mode, Mobile, Web) call
the exact same Jarvis Core instance, consuming the exact same event stream.
"""

from __future__ import annotations

import time
import logging
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional

from core.events import (
    BaseEvent,
    ThinkingEvent,
    PlannerEvent,
    MemoryEvent,
    ExecutionEvent,
    VerificationEvent,
    ReflectionEvent,
    LearningEvent,
    FinalResponseToken,
    FinalResponse,
)
from core.brain_adapter import BrainAdapter
from core.thinking_middleware import ThinkingMiddleware
from core.world_state import world_state_engine
from core.memory import unified_memory
from core.knowledge_graph import knowledge_graph
from core.goal_manager import goal_manager
from core.skill_manager import skill_manager
from core.planner import planner_engine
from core.safety import safety_layer
from core.rag import rag_engine
from core.prompt_assembler import prompt_assembler
from core.tools_registry import tool_registry
from core.learning_engine import learning_engine, FailureEvent
from core.performance_manager import performance_manager
from core.diagnostics import self_diagnostics
from core.background_workers import background_workers

logger = logging.getLogger(__name__)


class JarvisCore:
    """Master single core orchestrator for JARVIS vNext++."""

    def __init__(self):
        self.brain_adapter = BrainAdapter()
        self.thinking_middleware = ThinkingMiddleware()
        self._booted = False

    def boot(self) -> Dict[str, Any]:
        """Execute boot sequence & self diagnostics."""
        if self._booted:
            return {"status": "already_booted"}

        logger.info("Booting JARVIS vNext++ Core...")
        health = self_diagnostics.run_diagnostics()

        # Trigger background warmup non-blockingly
        background_workers.submit_task(self._async_warmup_runner)
        self._booted = True
        return {"status": "booted", "health": health}

    def _async_warmup_runner(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.brain_adapter.warmup())
        loop.close()

    async def process_stream(
        self, user_input: str, history: Optional[list] = None
    ) -> AsyncGenerator[BaseEvent, None]:
        """Unified 22-step execution pipeline yielding BaseEvent stream."""
        if not self._booted:
            self.boot()

        # 1-5. Intent, Context, World State
        world_state_engine.update(last_user_request=user_input)
        
        # 6. Memory Lookup
        mem_hit = unified_memory.search(user_input)
        if mem_hit:
            yield MemoryEvent(action="hit", tier="Facts", value=mem_hit)

        # 7-8. Planner Layer
        plan = planner_engine.build_plan(user_input)
        yield PlannerEvent(goal=plan.goal, steps=[s.action_type for s in plan.steps], profile=plan.profile, confidence=plan.confidence)

        # Confidence Check (< 30% -> ask user)
        if plan.confidence < 0.30:
            yield FinalResponse(text="I am unsure of your request. Could you please clarify?")
            return

        # Handle Direct Tool Action
        if plan.requires_tools:
            # Use classify_input to determine the correct tool AND argument
            tool_name, arg_name, arg_value = tool_registry.classify_input(user_input)
            if tool_name:
                # Safety Check
                if safety_layer.is_high_risk(tool_name):
                    token = safety_layer.request_confirmation(tool_name, {})
                    yield FinalResponse(text=f"Action '{tool_name}' is high risk. Please confirm (Token: {token}).")
                    return

                yield ExecutionEvent(target_name=tool_name, status="executing")
                exec_result = tool_registry.execute(tool_name, **{arg_name: arg_value})

                yield VerificationEvent(
                    target_name=tool_name,
                    verified=exec_result.get("verified", False),
                    details=exec_result,
                )

                if exec_result.get("success"):
                    yield FinalResponse(text=exec_result.get("output", "Action completed."))
                    return
                else:
                    # Learning Event on Tool Failure
                    learning_engine.record_failure(
                        FailureEvent(
                            tool_name=tool_name,
                            args={arg_name: arg_value},
                            error_message=exec_result.get("error", "Execution failed"),
                        )
                    )
                    yield LearningEvent(
                        failure_reason=exec_result.get("error", ""),
                        pattern_updated=f"Avoid failure in {tool_name}",
                    )

        # 9-11. LLM Generation via PromptAssembler & BrainAdapter
        candidate_cards = tool_registry.search_candidates(user_input, top_k=3) if plan.requires_tools else None
        assembled = prompt_assembler.assemble(user_input, plan, history=history, tool_cards=candidate_cards if candidate_cards else None)

        # Dynamic Resource Adaptation
        adj_predict, adj_top_k = performance_manager.adapt_parameters(assembled.max_tokens, plan.top_k_rag)

        raw_stream = self.brain_adapter.chat_stream(
            assembled.messages,
            temperature=0.25,
            max_tokens=adj_predict,
        )

        full_text = ""
        # Centralized Thinking Middleware parses <think> blocks into ThinkingEvents
        async for event in self.thinking_middleware.process_stream(raw_stream):
            if isinstance(event, FinalResponseToken):
                full_text += event.token
            yield event

        yield FinalResponse(text=full_text, confidence=plan.confidence)

    async def shutdown() -> None:
        """Shutdown background pools."""
        background_workers.shutdown()


jarvis_core = JarvisCore()
