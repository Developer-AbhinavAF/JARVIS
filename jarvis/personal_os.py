"""Personal AI Operating System orchestration layer.

Primary policy:
Tool > Memory > RAG > LLM.
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from jarvis import config
from jarvis.agents import AgentSpec, select_agent
from jarvis.memory_os import os_memory
from jarvis.nlp_pipeline import NLPResult, nlp_pipeline
from jarvis.rag import RAGContext, rag_builder
from jarvis.tool_system import (
    ToolResult,
    build_default_registry,
    default_tool_executor,
    default_tool_registry,
    default_tool_router,
)

logger = logging.getLogger(__name__)


# Per-request timing (same pattern as app.py)
_pt: dict[str, float] = {}
def _tm(label: str, start: float) -> None:
    _pt[label] = round((time.time() - start) * 1000, 1)

def _print_timings() -> str:
    if not _pt:
        return ""
    total = sum(_pt.values())
    parts = " | ".join(f"{k}:{v:.0f}ms" for k, v in sorted(_pt.items()))
    s = f"[TIMING_OS] {parts} | TOTAL:{total:.0f}ms"
    _pt.clear()
    return s


@dataclass
class OSResponse:
    text: str
    mode: str
    agent: str
    intent: str
    confidence: float
    actions: list[dict[str, Any]] = field(default_factory=list)
    memories: list[dict[str, Any]] = field(default_factory=list)
    rag: dict[str, Any] = field(default_factory=dict)
    tool_result: dict[str, Any] | None = None
    suggestions: list[str] = field(default_factory=list)


class PersonalAIOS:
    """Coordinates tools, memory, RAG, agents, and LLM fallback."""

    def __init__(self, *, load_legacy_tools: bool = True) -> None:
        if load_legacy_tools:
            default_tool_registry.load_legacy_tools()
        self.registry = default_tool_registry
        self.router = default_tool_router
        self.executor = default_tool_executor
        self.memory = os_memory
        self.rag_builder = rag_builder
        self._llm = None
        self._last_log_ts = 0.0

    @property
    def llm(self):
        if self._llm is None:
            from jarvis.llm import JarvisLLM

            self._llm = JarvisLLM()
        return self._llm

    def process(self, message: str, *, session_id: str = "default", allow_sensitive_tools: bool = False) -> OSResponse:
        t0 = time.time()
        message = (message or "").strip()
        if not message:
            return OSResponse(
                text="Say or type what you want JARVIS to do.",
                mode="empty",
                agent="orchestrator",
                intent="empty",
                confidence=0.0,
            )

        nlp = nlp_pipeline.process(message)
        _tm("nlp", t0)

        agent = select_agent(nlp.intent, message)
        _tm("agent", t0)

        memory_only = self._handle_memory_first(message, nlp, agent)
        if memory_only:
            return memory_only

        t2 = time.time()
        route = self.router.route(message, nlp)
        _tm("route", t2)
        if route and route.confidence >= 0.78:
            tool_response = self._execute_tool_route(route.tool_name, route.arguments, nlp, agent, allow_sensitive_tools)
            if tool_response:
                self._remember_turn_async(session_id, message, tool_response.text, nlp, mode="tool")
                _tm("total", t0)
                return tool_response

        if self._looks_like_memory_query(message, nlp):
            t3 = time.time()
            memories = self.memory.search(message, limit=config.MEMORY_SEARCH_LIMIT)
            _tm("memory_search", t3)
            text = self._format_memories(memories)
            response = OSResponse(
                text=text,
                mode="memory",
                agent=agent.name,
                intent=nlp.intent,
                confidence=nlp.confidence,
                memories=memories,
                suggestions=self._suggestions(agent),
            )
            self._remember_turn_async(session_id, message, text, nlp, mode="memory")
            _tm("total", t0)
            return response

        t4 = time.time()
        rag = self.rag_builder.build(message, categories=agent.memory_categories)
        _tm("rag", t4)

        t5 = time.time()
        llm_text = self._ask_llm(message, nlp, agent, rag)
        _tm("llm", t5)

        # Skip reflection for low-relevance queries to save latency
        if nlp.memory_relevance >= config.MEMORY_REFLECTION_THRESHOLD or nlp.intent == "remember":
            t6 = time.time()
            self._reflect(message, llm_text)
            _tm("reflect", t6)

        self._remember_turn_async(session_id, message, llm_text, nlp, mode="llm", rag=rag)
        _tm("total", t0)

        return OSResponse(
            text=llm_text,
            mode="llm",
            agent=agent.name,
            intent=nlp.intent,
            confidence=nlp.confidence,
            rag={
                "latency_ms": rag.latency_ms,
                "items": [asdict(item) for item in rag.items],
                "chars": len(rag.context_text),
            },
            suggestions=self._suggestions(agent),
        )

    def _handle_memory_first(self, message: str, nlp: NLPResult, agent: AgentSpec) -> OSResponse | None:
        if nlp.intent != "remember" and not message.lower().startswith(("remember ", "save this ", "save that ")):
            return None
        content = message
        lowered = message.lower()
        for prefix in ["remember this", "remember that", "remember", "save this", "save that"]:
            if lowered.startswith(prefix):
                content = message[len(prefix) :].strip(" :-")
                break
        record = self.memory.add(
            content or message,
            category="preference" if "prefer" in lowered else "knowledge",
            importance=0.9,
            source="user",
            tags=["explicit"],
        )
        return OSResponse(
            text=f"Saved to memory: {record.summary}",
            mode="memory_write",
            agent=agent.name,
            intent=nlp.intent,
            confidence=nlp.confidence,
            memories=[asdict(record)],
            suggestions=self._suggestions(agent),
        )

    def _execute_tool_route(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        nlp: NLPResult,
        agent: AgentSpec,
        allow_sensitive_tools: bool,
    ) -> OSResponse | None:
        result = self.executor.execute(tool_name, arguments, allow_sensitive=allow_sensitive_tools)
        if result.permission_denied:
            return OSResponse(
                text=result.error,
                mode="tool_permission",
                agent=agent.name,
                intent=nlp.intent,
                confidence=nlp.confidence,
                tool_result=self._tool_result_dict(result),
                suggestions=["enable system tools", "try a read-only query", "open settings"],
            )
        if not result.ok:
            logger.info("Tool route failed; falling back to LLM: %s", result.error)
            return None
        text = str(result.result)
        return OSResponse(
            text=text,
            mode="tool",
            agent=agent.name,
            intent=nlp.intent,
            confidence=nlp.confidence,
            actions=[{"tool": tool_name, "arguments": arguments}],
            tool_result=self._tool_result_dict(result),
            suggestions=self._suggestions(agent),
        )

    def _ask_llm(self, message: str, nlp: NLPResult, agent: AgentSpec, rag: RAGContext) -> str:
        system = [
            "You are JARVIS, a production-grade Personal AI Operating System.",
            "Policy priority: tools first, then memory, then retrieval, then LLM reasoning.",
            "Be concise, factual, and useful. Ask for missing information only when required.",
            f"Active agent: {agent.name}. Intent: {nlp.intent}.",
        ]
        if rag.context_text:
            system.append("Relevant retrieved context:\n" + rag.context_text)
        context = [{"role": "system", "content": "\n".join(system)}]
        try:
            response = self.llm.chat(message, context=context, max_tokens=config.LLM_MAX_TOKENS)
            if isinstance(response, dict):
                return str(response.get("text") or response)
            return str(response)
        except Exception as exc:
            logger.exception("LLM fallback failed")
            if rag.context_text:
                return "I found relevant memory, but the local LLM is unavailable. " + rag.context_text[:500]
            return f"I could not reach the local LLM: {exc}"

    def _reflect(self, message: str, response: str) -> None:
        try:
            from jarvis.reflection import reflection_manager

            reflection_manager.reflect_interaction(message, response)
        except Exception:
            logger.debug("Reflection skipped", exc_info=True)

    def _remember_turn_async(
        self,
        session_id: str,
        message: str,
        response: str,
        nlp: NLPResult,
        *,
        mode: str,
        rag: RAGContext | None = None,
    ) -> None:
        """Write conversation turn to memory. Skips writes for empty/low-importance replies."""
        if not message or not response:
            return
        importance = 0.6 if nlp.should_remember else 0.25
        # Skip writing for very low importance to reduce latency
        if importance < 0.3 and mode != "llm":
            return
        try:
            self.memory.remember_conversation(
                message,
                response[:1200],
                session_id=session_id,
                importance=importance,
                metadata={
                    "intent": nlp.intent,
                    "mode": mode,
                    "rag_items": len(rag.items) if rag else 0,
                },
            )
        except Exception:
            logger.debug("Conversation memory write skipped", exc_info=True)

    def _looks_like_memory_query(self, message: str, nlp: NLPResult) -> bool:
        text = message.lower()
        return any(
            marker in text
            for marker in [
                "what do you remember",
                "search memory",
                "find in memory",
                "my preference",
                "what did i say",
                "what have you learned",
            ]
        ) or nlp.intent == "remember"

    def _format_memories(self, memories: list[dict[str, Any]]) -> str:
        if not memories:
            return "I did not find a matching memory yet."
        lines = ["Relevant memory:"]
        for item in memories[:5]:
            lines.append(f"- [{item.get('category')}] {item.get('summary')}")
        return "\n".join(lines)

    def _tool_result_dict(self, result: ToolResult) -> dict[str, Any]:
        return {
            "tool_name": result.tool_name,
            "ok": result.ok,
            "error": result.error,
            "latency_ms": result.latency_ms,
            "cached": result.cached,
            "permission_denied": result.permission_denied,
        }

    def _suggestions(self, agent: AgentSpec) -> list[str]:
        if agent.name == "memory":
            return ["search memory", "show memory dashboard", "save this preference"]
        if agent.name == "research":
            return ["verify sources", "make research report", "save research notes"]
        if agent.name == "coding":
            return ["search code", "review architecture", "explain this file"]
        if agent.name == "finance":
            return ["stock AAPL", "market news", "save watchlist"]
        if agent.name == "nasa":
            return ["NASA APOD", "NEO tracking", "Mars rover data"]
        return ["system status", "search memory", "daily review"]

    def dashboard(self) -> dict[str, Any]:
        return {
            "memory": self.memory.dashboard(),
            "tools": {
                "count": len(self.registry.list(include_disabled=True)),
                "analytics": self.executor.analytics.summary(),
            },
            "apis": __import__("jarvis.api_services", fromlist=["api_services"]).api_services.key_status(),
        }


personal_ai_os = PersonalAIOS(load_legacy_tools=False)


def get_personal_ai_os(load_legacy_tools: bool = True) -> PersonalAIOS:
    if load_legacy_tools:
        personal_ai_os.registry.load_legacy_tools()
    return personal_ai_os
