"""core/jarvis_core.py — Single Shared Core Entrypoint for JARVIS vNext++.

All interfaces (CLI, Desktop UI, REST API, Speech Mode, Mobile, Web) call
the exact same Jarvis Core instance, consuming the exact same event stream.
"""

from __future__ import annotations

import time
import logging
import asyncio
import re
import json
from typing import AsyncGenerator, Dict, Any, Optional, List

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
    ImageResultEvent,
    ImageGalleryEvent,
    CodeExecutionEvent,
    ExecuteEvent,
)

# ── Pipeline timeouts ────────────────────────────────────────────────
MAX_LLM_STREAM_SECONDS = 360.0
MAX_TOOL_EXECUTION_SECONDS = 45.0
MAX_AGENT_ITERATIONS = 8

from core.brain_adapter import BrainAdapter, LLMResult, ToolCall
from core.toolcall_parser import tool_call_parser
from core.thinking_middleware import ThinkingMiddleware
from core.world_state import world_state_engine
from core.memory import unified_memory, extract_memory_intent
from core.memory_human import human_memory
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
from core.execute_parser import execute_parser
from core.execute_engine import execute_engine

# New multi-provider architecture
try:
    from core.provider_registry import provider_registry
    from core.capability_router import capability_router
    from core.config_manager import config_manager
    from core.web_food_loader import web_food_loader
    MULTI_PROVIDER_AVAILABLE = True
except ImportError:
    MULTI_PROVIDER_AVAILABLE = False
    logger.warning("Multi-provider architecture not available, using legacy systems")

logger = logging.getLogger(__name__)


class JarvisCore:
    """Master single core orchestrator for JARVIS vNext++."""

    def __init__(self):
        self.brain_adapter = BrainAdapter()
        self.thinking_middleware = ThinkingMiddleware()
        self._booted = False
        self._human_memory_started = False

    @staticmethod
    def _chunk_text(text: str, size: int = 4) -> list[str]:
        """Split text into small chunks for streaming as FinalResponseToken events."""
        return [text[i:i + size] for i in range(0, len(text), size)] if text else []

    @staticmethod
    def _parse_tool_call_from_text(text: str) -> Optional[tuple[str, dict]]:
        """Parse tool call text like 'open_application({"app_name": "chrome"})'
        or raw JSON like '{"name":"open_application","arguments":{...}}' from
        LLM output.

        Only matches KNOWN registered tools with validated arguments.
        Returns None if no parseable tool call is found.
        """
        parsed = tool_call_parser.parse_text(text)
        if not parsed:
            return None
        tc = parsed[0]
        return tc.name, tc.arguments

    # ====================================================================
    # TOOL EXECUTION — single canonical path for every tool invocation
    # ====================================================================

    async def _execute_tool_call(
        self,
        tc: ToolCall,
        agent_messages: list,
        user_input: str,
    ) -> None:
        """Execute one ToolCall, emit pipeline events, append the tool result
        to the agent conversation.

        This is the ONLY execution path — native tool calls, JSON-as-text
        tool calls and fast-path routes all funnel through the executor here
        or through tool_registry.execute directly.
        """
        logger.info("[LLM] Tool call detected: %s", tc.name)
        logger.info("[ARGS] %s=%s", tc.name, tc.arguments)

        yield ExecutionEvent(target_name=tc.name, status="executing", args=tc.arguments)

        try:
            logger.info("[EXECUTOR] Executing %s", tc.name)
            exec_result = await asyncio.wait_for(
                asyncio.to_thread(tool_registry.execute, tc.name, **tc.arguments),
                timeout=MAX_TOOL_EXECUTION_SECONDS,
            )
        except asyncio.TimeoutError:
            exec_result = {
                "success": False,
                "output": None,
                "verified": False,
                "tool": tc.name,
                "error": f"Tool '{tc.name}' timed out after {MAX_TOOL_EXECUTION_SECONDS}s",
            }
            logger.warning("[EXECUTOR] %s timed out after %.0fs", tc.name, MAX_TOOL_EXECUTION_SECONDS)

        if exec_result.get("success") and exec_result.get("verified"):
            logger.info("[VERIFY] %s: Success", tc.name)
        else:
            logger.info(
                "[VERIFY] %s: Failed (%s)",
                tc.name,
                exec_result.get("error") or "unverified",
            )

        yield VerificationEvent(
            target_name=tc.name,
            verified=bool(exec_result.get("verified", False)),
            details=exec_result,
        )

        # Append to conversation so the LLM can see the result and respond.
        agent_messages.append({
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "function": {
                    "name": tc.name,
                    "arguments": json.dumps(tc.arguments, default=str),
                }
            }],
        })
        agent_messages.append({
            "role": "tool",
            "content": json.dumps(exec_result, default=str),
        })

        # Handle NASA visual results inline.
        if exec_result.get("success") and tc.name in ("nasa_apod", "nasa_image_search"):
            results_list = exec_result.get("results", [])
            if results_list:
                if len(results_list) == 1:
                    r = results_list[0]
                    yield ImageResultEvent(
                        source="NASA",
                        title=r.get("title", ""),
                        description=r.get("description", ""),
                        image_url=r.get("image_url", ""),
                        thumbnail_url=r.get("thumbnail_url", ""),
                        source_url=r.get("source_url", ""),
                        media_type=r.get("media_type", "image"),
                        metadata={"date": r.get("date", ""), "nasa_id": r.get("nasa_id", "")},
                    )
                else:
                    yield ImageGalleryEvent(
                        source="NASA",
                        query=exec_result.get("query", user_input),
                        results=results_list,
                        count=len(results_list),
                    )

    def _final_text_is_pure_tool_call(self, text: str) -> bool:
        """True when the entire final text is a valid tool call (and nothing
        else) — used to guarantee raw tool JSON never reaches the user."""
        stripped = text.strip()
        if not stripped:
            return False
        parsed = tool_call_parser.parse_text(stripped)
        if not parsed:
            return False
        try:
            json.loads(stripped)
        except json.JSONDecodeError:
            return False
        return True

    def boot(self) -> Dict[str, Any]:
        """Execute boot sequence & self diagnostics."""
        if self._booted:
            return {"status": "already_booted"}

        logger.info("Booting JARVIS vNext++ Core...")
        health = self_diagnostics.run_diagnostics()
        
        # Initialize multi-provider architecture if available
        if MULTI_PROVIDER_AVAILABLE:
            try:
                logger.info("Initializing multi-provider architecture...")
                
                # Start configuration monitoring
                config_manager.start_monitoring()
                logger.info("Configuration monitoring started")
                
                # Log provider status
                provider_status = provider_registry.get_provider_status()
                logger.info("Provider registry: %d providers loaded", len(provider_status))
                for provider_name, status in provider_status.items():
                    logger.info("  %s: enabled=%s, available=%s, keys=%d", 
                              provider_name, status['enabled'], status['available'], status['keys_count'])
                
                # Log web_food status
                web_food_stats = web_food_loader.get_stats()
                logger.info("Web food loader: %d documents loaded", web_food_stats['total_documents'])
                
                # Log router status
                router_status = capability_router.get_status()
                logger.info("Capability router: ready with max_attempts=%d", router_status['max_attempts'])
                
            except Exception as e:
                logger.error("Error initializing multi-provider architecture: %s", e)
        
        # Start human-like memory system
        if not self._human_memory_started:
            memory_startup = human_memory.startup()
            self._human_memory_started = memory_startup.get("started", False)
            logger.info(
                "Human memory system: drive_ready=%s, pending_sync=%d",
                memory_startup.get("drive_ready"),
                memory_startup.get("pending_sync", 0),
            )
        
        background_workers.submit_task(self._async_warmup_runner)
        self._booted = True
        return {"status": "booted", "health": health, "memory": memory_startup}

    def _async_warmup_runner(self) -> None:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.brain_adapter.warmup())
        finally:
            try:
                loop.close()
            except Exception:
                pass

    # ====================================================================
    # AGENT LOOP — THE CORE EXECUTION PIPELINE
    # ====================================================================

    async def process_stream(
        self, user_input: str, history: Optional[list] = None
    ) -> AsyncGenerator[BaseEvent, None]:
        """Unified execution pipeline with agent loop for tool calling."""
        request_start = time.time()
        request_id = f"req_{int(request_start * 1000)}"
        
        logger.info("[%s] [PROCESS_START] user_input='%s', length=%d", request_id, user_input, len(user_input))
        
        if not self._booted:
            logger.info("[%s] [BOOT] Booting JarvisCore", request_id)
            self.boot()

        # Load conversation history from conversation_store if not provided
        if history is None:
            try:
                from core.conversation_store import conversation_store
                history = conversation_store.messages(limit=8)
                logger.info("[%s] [SESSION] loaded %d messages from history", request_id, len(history))
            except Exception as e:
                logger.warning("[%s] [SESSION] failed to load history: %s", request_id, e)
                history = []

        # 1-5. Intent, Context, World State
        logger.info("[%s] [REQUEST] %s", request_id, user_input[:100])
        world_state_engine.update(last_user_request=user_input)
        
        # Check for configuration changes (multi-provider architecture)
        if MULTI_PROVIDER_AVAILABLE:
            try:
                config_manager.reload_configuration()
                rag_engine.reload_if_changed()
            except Exception as e:
                logger.debug("[%s] [CONFIG] Error checking for changes: %s", request_id, e)
        
        # Track user message in human memory
        if self._human_memory_started:
            human_memory.on_user_message(user_input)

        # 5.5. Handle explicit memory commands (deterministic routing)
        if self._human_memory_started:
            memory_command = human_memory.route_command(user_input)
            if memory_command:
                logger.info(
                    "[MEMORY_COMMAND] kind=%s success=%s",
                    memory_command.get("kind"),
                    memory_command.get("success"),
                )
                response_text = memory_command.get("text", "")
                for token in self._chunk_text(response_text):
                    yield FinalResponseToken(token=token)
                yield FinalResponse(text=response_text)
                return

        # 6. Memory Lookup (legacy unified_memory)
        memory_start = time.time()
        mem_hit = unified_memory.search(user_input)
        memory_end = time.time()
        logger.info("[%s] [MEMORY] retrieval %.0fms", request_id, (memory_end - memory_start) * 1000)
        if mem_hit:
            yield MemoryEvent(action="hit", tier="Facts", value=mem_hit)

        # 7-8. Planner Layer
        plan = planner_engine.build_plan(user_input)
        logger.info("[%s] [PLANNER] Intent: %s (profile=%s, confidence=%.2f, tools=%s)",
                    request_id,
                    plan.steps[0].action_type if plan.steps else "response",
                    plan.profile, plan.confidence, plan.requires_tools)
        yield PlannerEvent(goal=plan.goal, steps=[s.action_type for s in plan.steps], profile=plan.profile, confidence=plan.confidence)

        # Confidence Check
        if plan.confidence < 0.30:
            msg = "I am unsure of your request. Could you please clarify?"
            for token in self._chunk_text(msg):
                yield FinalResponseToken(token=token)
            yield FinalResponse(text=msg)
            return

        # ── MEMORY WRITE: explicit "remember/save ..." commands ─────
        # Deterministic backend-side persistence — never depends on the
        # model emitting a tool call. Store BEFORE the agent loop so the
        # LLM's confirmation is grounded in the verified write.
        memory_write_note: Optional[str] = None
        if plan.requires_memory and not plan.requires_tools:
            mem_intent = extract_memory_intent(user_input)
            if mem_intent:
                stored = unified_memory.store(
                    content=mem_intent["content"],
                    memory_type=mem_intent["memory_type"],
                    key=mem_intent.get("key"),
                    value=mem_intent.get("value"),
                    explicit=True,
                )
                if stored.get("success"):
                    logger.info(
                        "[MEMORY] Saved id=%s type=%s action=%s",
                        stored.get("memory_id"),
                        stored.get("type"),
                        stored.get("action"),
                    )
                    yield MemoryEvent(
                        action="saved",
                        tier=stored.get("type", "fact"),
                        key=mem_intent.get("key") or "",
                        value=stored.get("memory_id"),
                    )
                    memory_write_note = (
                        "A persistent memory write completed for this "
                        f"request (id={stored.get('memory_id')}, "
                        f"type={stored.get('type')}, "
                        f"action={stored.get('action')}). "
                        "Briefly confirm the save to the user. Do not "
                        "claim any other memory was stored."
                    )
                else:
                    logger.error(
                        "[MEMORY] Persistent write FAILED: %s",
                        stored.get("error"),
                    )
                    yield MemoryEvent(
                        action="save_failed",
                        tier=mem_intent["memory_type"],
                        key=mem_intent.get("key") or "",
                        value=None,
                    )
                    msg = "I couldn't save that to persistent memory."
                    for token in self._chunk_text(msg):
                        yield FinalResponseToken(token=token)
                    yield FinalResponse(text=msg)
                    return

        # ── FAST PATH: Deterministic keyword routing ─────────────────
        # Obvious explicit commands bypass the LLM entirely.
        if plan.requires_tools:
            tool_name, arg_name, arg_value = tool_registry.classify_input(user_input)
            if tool_name:
                # Safety Check
                if safety_layer.is_high_risk(tool_name):
                    token = safety_layer.request_confirmation(tool_name, {})
                    msg = f"Action '{tool_name}' is high risk. Please confirm (Token: {token})."
                    for t in self._chunk_text(msg):
                        yield FinalResponseToken(token=t)
                    yield FinalResponse(text=msg)
                    return

                logger.info("[ROUTER] Fast path: %s(%s=%s)", tool_name, arg_name, arg_value)
                logger.info("[EXECUTOR] Executing %s", tool_name)
                yield ExecutionEvent(target_name=tool_name, status="executing")
                try:
                    exec_result = await asyncio.wait_for(
                        asyncio.to_thread(
                            tool_registry.execute, tool_name, **{arg_name: arg_value}
                        ),
                        timeout=MAX_TOOL_EXECUTION_SECONDS,
                    )
                except asyncio.TimeoutError:
                    exec_result = {"success": False, "error": f"Tool '{tool_name}' timed out after {MAX_TOOL_EXECUTION_SECONDS}s"}
                    logger.warning("Tool %s timed out after %.0fs", tool_name, MAX_TOOL_EXECUTION_SECONDS)

                logger.info("[VERIFY] %s: %s", tool_name, "Success" if exec_result.get("verified") else "Failed")
                yield VerificationEvent(
                    target_name=tool_name,
                    verified=exec_result.get("verified", False),
                    details=exec_result,
                )

                if exec_result.get("success"):
                    # Handle NASA visual results
                    results_list = exec_result.get("results", [])
                    if results_list and tool_name in ("nasa_apod", "nasa_image_search"):
                        if len(results_list) == 1:
                            r = results_list[0]
                            yield ImageResultEvent(
                                source="NASA",
                                title=r.get("title", ""),
                                description=r.get("description", ""),
                                image_url=r.get("image_url", ""),
                                thumbnail_url=r.get("thumbnail_url", ""),
                                source_url=r.get("source_url", ""),
                                media_type=r.get("media_type", "image"),
                                metadata={"date": r.get("date", ""), "nasa_id": r.get("nasa_id", "")},
                            )
                        else:
                            yield ImageGalleryEvent(
                                source="NASA",
                                query=exec_result.get("query", user_input),
                                results=results_list,
                                count=len(results_list),
                            )
                        if tool_name == "nasa_apod":
                            first = results_list[0]
                            text = f"**{first.get('title', 'NASA APOD')}**\n{first.get('description', '')[:200]}..."
                        else:
                            text = f"Found {len(results_list)} NASA results for '{exec_result.get('query', user_input)}'."
                        yield FinalResponse(text=text)
                        return

                    result_text = exec_result.get("output", "Action completed.")
                    for token in self._chunk_text(result_text):
                        yield FinalResponseToken(token=token)
                    yield FinalResponse(text=result_text)
                    return
                else:
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
                    err_msg = (
                        f"Tool execution failed: {exec_result.get('error', 'unknown error')}"
                    )
                    for token in self._chunk_text(err_msg):
                        yield FinalResponseToken(token=token)
                    yield FinalResponse(text=err_msg)
                return

            # Code execution fallback for tasks that look like code generation
            if not tool_name:
                from core.code_execution_fallback import execute_code, detect_language
                if any(w in user_input.lower() for w in [
                    "write", "create", "generate", "make", "build",
                    "script", "code", "program", "calculator", "utility",
                    "python", "javascript",
                ]):
                    yield ExecutionEvent(target_name="code_fallback", status="executing")
                    code = self._generate_fallback_code(user_input)

                    # If the deterministic template engine has no match but the
                    # user explicitly asked to EXECUTE code, ask the LLM to
                    # generate the script, then run it through the same executor.
                    if not code and re.search(
                        r"\b(execute|run|run it|execute it)\b", user_input.lower()
                    ):
                        code = await self._ask_llm_for_code(user_input)

                    if code:
                        lang = detect_language(code)
                        exec_result = execute_code(code, language=lang)
                        yield CodeExecutionEvent(
                            language=exec_result.language,
                            code=exec_result.code,
                            stdout=exec_result.stdout,
                            stderr=exec_result.stderr,
                            exit_code=exec_result.exit_code,
                            success=exec_result.success,
                            verification="passed" if exec_result.verification_passed else exec_result.error,
                        )
                        yield VerificationEvent(
                            target_name="code_fallback",
                            verified=exec_result.verification_passed,
                            details=exec_result.to_dict(),
                        )
                        if exec_result.success:
                            output = exec_result.stdout or "Code executed successfully."
                            for token in self._chunk_text(output):
                                yield FinalResponseToken(token=token)
                            yield FinalResponse(text=output)
                            return
                        else:
                            err_text = f"Code execution failed: {exec_result.error}"
                            for token in self._chunk_text(err_text):
                                yield FinalResponseToken(token=token)
                            yield FinalResponse(text=err_text)
                            return

        # ── AGENT LOOP: LLM with native tool calling (TRUE STREAMING) ─────
        # Build messages for the LLM
        prompt_start = time.time()
        candidate_cards = tool_registry.search_candidates(user_input, top_k=5) if plan.requires_tools else None
        assembled = prompt_assembler.assemble(user_input, plan, history=history, tool_cards=candidate_cards)
        adj_predict, adj_top_k = performance_manager.adapt_parameters(assembled.max_tokens, plan.top_k_rag)
        prompt_end = time.time()
        logger.info("[%s] [PROMPT] build %.0fms", request_id, (prompt_end - prompt_start) * 1000)
        
        # Log provider information if using multi-provider architecture
        if MULTI_PROVIDER_AVAILABLE:
            try:
                router_status = capability_router.get_routing_stats()
                logger.info("[%s] [ROUTER] routing stats: %s", request_id, router_status)
            except Exception as e:
                logger.debug("[%s] [ROUTER] Error getting routing stats: %s", request_id, e)

        # Get native tool schemas for the LLM
        tool_schemas = tool_registry.get_tool_schemas_for_llm() if plan.requires_tools else []

        # Build conversation messages for the agent loop
        agent_messages = list(assembled.messages)
        if memory_write_note:
            agent_messages.append({
                "role": "system",
                "content": memory_write_note,
            })
        
        # For streaming, we accumulate tokens and emit them immediately
        accumulated_text = ""
        native_sink: Dict[int, Dict[str, str]] = {}
        first_token_emitted = False
        final_text = ""  # Initialize to avoid UnboundLocalError

        for iteration in range(MAX_AGENT_ITERATIONS):
            logger.info("[%s] [AGENT] iteration %d/%d", request_id, iteration + 1, MAX_AGENT_ITERATIONS)

            # Stream from LLM
            ollama_start = time.time()
            accumulated_text = ""
            native_sink = {}
            token_count = 0
            
            logger.info("[%s] [AGENT] Starting chat_stream with model=%s", request_id, self.brain_adapter.primary_model)
            
            async for token in self.brain_adapter.chat_stream(
                messages=agent_messages,
                model=self.brain_adapter.primary_model,
                temperature=0.25,
                max_tokens=adj_predict,
                tools=tool_schemas,
                tool_call_sink=native_sink,
            ):
                if not first_token_emitted and token:
                    first_token_emitted = True
                    ttft = (time.time() - ollama_start) * 1000
                    logger.info("[%s] [TTFT] First token emitted: %.0fms", request_id, ttft)
                
                # Emit token immediately for streaming
                if token and not token.startswith("["):  # Skip error markers
                    token_count += 1
                    accumulated_text += token
                    yield FinalResponseToken(token=token)
            
            ollama_end = time.time()
            logger.info("[%s] [OLLAMA] stream complete %.0fms, accumulated_text length=%d, token_count=%d", 
                       request_id, (ollama_end - ollama_start) * 1000, len(accumulated_text), token_count)

            # Flush and check for native tool calls
            tool_calls: List[ToolCall] = []
            self.brain_adapter._flush_tool_call_slots(native_sink, tool_calls)
            
            if tool_calls:
                logger.info("[%s] [AGENT] Native tool calls: %s", request_id, [tc.name for tc in tool_calls])
                # Execute tools
                for tc in tool_calls:
                    async for ev in self._execute_tool_call(tc, agent_messages, user_input):
                        yield ev
                # Continue loop with tool results
                continue

            # Check for text-based tool calls (fallback)
            if plan.requires_tools and accumulated_text.strip():
                text_calls = tool_call_parser.parse_text(accumulated_text)
                if text_calls:
                    logger.info("[%s] [AGENT] Text tool calls: %s", request_id, [tc.name for tc in text_calls])
                    for tc in text_calls:
                        async for ev in self._execute_tool_call(tc, agent_messages, user_input):
                            yield ev
                    accumulated_text = ""  # Clear tool call text
                    continue

            # No tool calls - this is the final response
            final_text = accumulated_text or ""
            break

        # Parse and execute <execute> tags from final text
        if final_text and execute_parser.has_execute_tags(final_text):
            execute_requests = execute_parser.parse(final_text)
            
            for req in execute_requests:
                if req.is_valid:
                    yield ExecutionEvent(target_name=f"execute_{req.execution_type}", status="executing")
                    
                    result = execute_engine.execute(req)
                    
                    yield ExecuteEvent(
                        execution_type=result.execution_type,
                        command=result.command,
                        status=result.status,
                        exit_code=result.exit_code,
                        stdout=result.stdout,
                        stderr=result.stderr,
                        duration_ms=result.duration_ms,
                        error=result.error
                    )
                    
                    # Remove execute tags from response text
                    final_text = execute_parser.remove_execute_tags(final_text)
                    
                    # If execution failed, update response to reflect failure
                    if result.status == "failed":
                        final_text = f"Execution failed: {result.error or result.stderr}"
                else:
                    logger.warning("[EXECUTE] Invalid execute request: %s", req.error)

        # Stream the final response
        logger.info("[%s] [FINAL_TEXT_CHECK] final_text length: %d, content: '%s'", request_id, len(final_text), final_text[:100] if final_text else "(empty)")
        
        if final_text:
            # Safety net: never surface raw tool-call JSON as a response.
            if plan.requires_tools and self._final_text_is_pure_tool_call(final_text):
                final_text = "Done."
            logger.info("[%s] [RESPONSE] %s", request_id, final_text[:200].replace("\n", " "))
            
            # Save to conversation store
            try:
                from core.conversation_store import conversation_store
                conversation_store.append(
                    user=user_input,
                    assistant=final_text,
                    provider=self.brain_adapter.provider,
                    model=self.brain_adapter.primary_model,
                    tier="desktop"
                )
                logger.info("[%s] [SESSION] saved conversation turn", request_id)
            except Exception as e:
                logger.warning("[%s] [SESSION] failed to save conversation: %s", request_id, e)
            
            # Track assistant message in human memory (non-blocking)
            if self._human_memory_started:
                import threading
                def save_memory_async():
                    try:
                        memory_save_start = time.time()
                        human_memory.on_assistant_message(final_text)
                        memory_save_end = time.time()
                        logger.info("[%s] [MEMORY] background save %.0fms", request_id, (memory_save_end - memory_save_start) * 1000)
                    except Exception as e:
                        logger.warning("[%s] [MEMORY] background save failed: %s", request_id, e)
                
                memory_thread = threading.Thread(target=save_memory_async, daemon=True)
                memory_thread.start()
                logger.info("[%s] [MEMORY] save queued in background", request_id)
            
            token_count = 0
            for token in self._chunk_text(final_text):
                token_count += 1
                yield FinalResponseToken(token=token)
            logger.info("[%s] [STREAMING] Emitted %d FinalResponseToken events", request_id, token_count)
            yield FinalResponse(text=final_text, confidence=plan.confidence)
            logger.info("[%s] [STREAMING] Emitted FinalResponse event", request_id)
        else:
            logger.warning("[%s] [NO_RESPONSE] final_text is empty, sending default response", request_id)
            yield FinalResponse(text="I apologize, but I couldn't generate a response. Please try again.", confidence=0.0)
        
        total_latency = time.time() - request_start
        logger.info("[%s] [COMPLETE] total %.0fms", request_id, total_latency * 1000)

    async def _ask_llm_for_code(self, query: str) -> Optional[str]:
        """Generate Python code via the LLM for fallback execution.

        Returns raw code text or None on failure/malformed response.
        """
        try:
            msgs = [
                {
                    "role": "system",
                    "content": (
                        "You generate Python code only. "
                        "Return ONLY raw code — no prose, no markdown fences."
                    ),
                },
                {"role": "user", "content": query},
            ]
            result = await asyncio.wait_for(
                self.brain_adapter.chat_with_tools(
                    messages=msgs,
                    tools=[],
                    temperature=0.2,
                    max_tokens=1024,
                ),
                timeout=MAX_LLM_STREAM_SECONDS,
            )
            code = (result.content or "").strip()
            code = re.sub(r"^```(?:python|py)?\s*", "", code).rstrip()
            code = re.sub(r"\s*```$", "", code)
            if not code or not code.strip():
                return None
            return code.strip()
        except Exception as exc:
            logger.warning("LLM code generation failed: %s", exc)
            return None

    async def process_stream_with_image(
        self, user_input: str, image_context: dict[str, Any], history: Optional[list] = None
    ) -> AsyncGenerator[BaseEvent, None]:
        """Process user input with an attached image using multimodal support."""
        if not self._booted:
            self.boot()

        logger.info("[USER][IMAGE] %s (image: %s)", user_input, image_context.get("image_name", "unknown"))
        
        # Track user message in human memory (text only, not image data)
        if self._human_memory_started:
            human_memory.on_user_message(user_input)

        # Skip explicit memory commands for image requests (focus on vision)
        # Images are processed directly through the multimodal LLM

        # Planner still applies - the model might need tools after vision analysis
        plan = planner_engine.build_plan(user_input)
        logger.info("[ROUTER][IMAGE] Intent: %s (profile=%s, confidence=%.2f, tools=%s)",
                    plan.steps[0].action_type if plan.steps else "response",
                    plan.profile, plan.confidence, plan.requires_tools)
        yield PlannerEvent(goal=plan.goal, steps=[s.action_type for s in plan.steps], profile=plan.profile, confidence=plan.confidence)

        # Build multimodal message
        # Format: image first, then text
        image_data = image_context.get("image_data", "")
        image_type = image_context.get("image_type", "image/jpeg")
        
        # Construct the multimodal message for Ollama
        # Ollama format: {"role": "user", "images": [base64], "content": text}
        multimodal_message = {
            "role": "user",
            "images": [image_data],
            "content": user_input or "Analyze this image",
        }

        logger.info("[IMAGE] Preparing multimodal request")

        # For image requests, we go directly to the LLM with the image
        # Tool calling can still happen after vision analysis
        candidate_cards = tool_registry.search_candidates(user_input, top_k=5) if plan.requires_tools else None
        tool_schemas = tool_registry.get_tool_schemas_for_llm() if plan.requires_tools else []
        
        agent_messages = [multimodal_message]
        final_text = ""

        for iteration in range(MAX_AGENT_ITERATIONS):
            logger.info("Agent loop iteration %d/%d (with image)", iteration + 1, MAX_AGENT_ITERATIONS)

            # Call LLM with tools and image
            # Note: chat_with_tools expects messages with role/content, but we need to pass the image
            # We'll need to extend the brain adapter to handle images
            try:
                # For now, use chat_stream directly with the multimodal message
                # The brain adapter needs to be extended to support images
                llm_text = ""
                async for token in self.brain_adapter.chat_stream(
                    messages=agent_messages,
                    temperature=0.25,
                    max_tokens=2048,
                ):
                    if token.startswith("[") and ("Error" in token or "error" in token):
                        logger.error("[IMAGE] LLM error: %s", token)
                        final_text = "I couldn't process that image due to an error."
                        break
                    llm_text += token
                    yield FinalResponseToken(token=token)
                
                final_text = llm_text
            except Exception as exc:
                logger.error("[IMAGE] LLM call failed: %s", exc)
                final_text = f"I couldn't process that image: {str(exc)}"
                for token in self._chunk_text(final_text):
                    yield FinalResponseToken(token=token)
                yield FinalResponse(text=final_text)
                return

            # Check if the LLM wants to call tools after vision analysis
            if plan.requires_tools and final_text:
                text_calls = tool_call_parser.parse_text(final_text)
                if text_calls:
                    logger.info("[EXECUTOR] Image response contains tool calls: %d", len(text_calls))
                    for tc in text_calls:
                        async for ev in self._execute_tool_call(tc, agent_messages, user_input):
                            yield ev
                    # Continue for tool results
                    continue

            # Final response
            break

        # Track assistant response in human memory
        if self._human_memory_started:
            human_memory.on_assistant_message(final_text)

        yield FinalResponse(text=final_text)

    def _generate_fallback_code(self, query: str) -> Optional[str]:
        """Generate simple code for common patterns when no specialized tool exists."""
        q = query.lower().strip()

        url_match = None
        url_patterns = [
            r"open\s+(https?://\S+)",
            r"open\s+(\w+\.\w+)",
            r"go\s+to\s+(https?://\S+)",
            r"go\s+to\s+(\w+)",
        ]
        for pat in url_patterns:
            m = re.search(pat, q)
            if m:
                url_match = m.group(1)
                break

        if url_match:
            url = url_match
            if not url.startswith("http"):
                url = f"https://www.{url}.com"
            return f"""import webbrowser
webbrowser.open("{url}")
print(f"Opened: {url}")"""

        calc_match = re.search(r"(calculate|compute|eval|solve)\s+(.+)", q)
        if calc_match:
            expr = calc_match.group(2).strip()
            safe_expr = "".join(c for c in expr if c in "0123456789+-*/.()% ")
            if safe_expr:
                return f"""result = {safe_expr}
print(f"Result: {{result}}")"""

        file_match = re.search(r"(create|write|make)\s+(?:a\s+)?(?:file|text)\s+(?:called\s+)?(\S+)", q)
        if file_match:
            fname = file_match.group(2)
            return f"""with open("{fname}", "w") as f:
    f.write("Created by JARVIS code fallback")
print(f"Created: {fname}")"""

        return None

    async def shutdown(self) -> None:
        """Shutdown background pools."""
        background_workers.shutdown()


jarvis_core = JarvisCore()
