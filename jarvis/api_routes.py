"""FastAPI route bridge for the JARVIS Personal AI OS."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from jarvis.api_services import api_services
from jarvis.memory_os import os_memory
from jarvis.personal_os import get_personal_ai_os


class OSChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    allow_sensitive_tools: bool = False


class MemoryCreateRequest(BaseModel):
    content: str
    category: str = "knowledge"
    importance: float = 0.5
    source: str = "user"
    tags: list[str] = Field(default_factory=list)
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryUpdateRequest(BaseModel):
    category: str | None = None
    importance: float | None = None
    source: str | None = None
    tags: list[str] | None = None
    summary: str | None = None
    content: str | None = None
    metadata: dict[str, Any] | None = None


def register_personal_os_routes(app) -> None:
    """Attach production OS routes to an existing FastAPI app."""

    @app.post("/api/os/chat")
    async def os_chat(request: OSChatRequest):
        os_core = get_personal_ai_os(load_legacy_tools=False)
        response = os_core.process(
            request.message,
            session_id=request.session_id,
            allow_sensitive_tools=request.allow_sensitive_tools,
        )
        return response.__dict__

    @app.get("/api/os/dashboard")
    async def os_dashboard():
        return get_personal_ai_os(load_legacy_tools=False).dashboard()

    @app.get("/api/os/apis")
    async def os_api_status():
        return api_services.key_status()

    @app.get("/api/os/tools")
    async def os_tools(query: str = "", category: str = ""):
        os_core = get_personal_ai_os(load_legacy_tools=True)
        if query:
            return {"tools": os_core.registry.search(query)}
        return {"tools": os_core.registry.list(category=category or None)}

    @app.get("/api/os/tools/analytics")
    async def os_tool_analytics():
        os_core = get_personal_ai_os(load_legacy_tools=False)
        return {"analytics": os_core.executor.analytics.summary()}

    @app.post("/api/os/memory")
    async def os_memory_create(request: MemoryCreateRequest):
        record = os_memory.add(
            request.content,
            category=request.category,
            importance=request.importance,
            source=request.source,
            tags=request.tags,
            summary=request.summary,
            metadata=request.metadata,
        )
        return record.__dict__

    @app.get("/api/os/memory")
    async def os_memory_search(query: str = "", category: str = "", limit: int = 20):
        if query:
            return {"memories": os_memory.search(query, categories=[category] if category else None, limit=limit)}
        return {"memories": os_memory.list(category=category or None, limit=limit)}

    @app.patch("/api/os/memory/{memory_id}")
    async def os_memory_update(memory_id: str, request: MemoryUpdateRequest):
        updates = {key: value for key, value in request.model_dump().items() if value is not None}
        return {"ok": os_memory.update(memory_id, updates)}

    @app.delete("/api/os/memory/{memory_id}")
    async def os_memory_delete(memory_id: str):
        return {"ok": os_memory.delete(memory_id)}

    @app.get("/api/os/rag")
    async def os_rag(query: str):
        os_core = get_personal_ai_os(load_legacy_tools=False)
        context = os_core.rag_builder.build(query)
        return {
            "query": query,
            "context_text": context.context_text,
            "items": [item.__dict__ for item in context.items],
            "latency_ms": context.latency_ms,
        }

    @app.get("/api/os/architecture")
    async def os_architecture():
        return {
            "principle": "Tool > Memory > RAG > LLM",
            "layers": [
                "Fast deterministic NLP and intent/entity extraction",
                "Typed tool registry, router, executor, permissions, monitoring, analytics",
                "SQLite memory spine with optional Chroma learning memory",
                "RAG context builder with strict character budgets",
                "LLM through AI Router v3.0 (multi-provider)",
                "Specialized agents selected by intent and domain",
            ],
            "hardware_target": {
                "cpu": "Intel i5 6th Gen",
                "ram": "8GB",
                "os": "Windows",
                "ai_router": "AI Router v3.0",
            },
        }
