"""Agent definitions for the JARVIS Personal AI OS."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentSpec:
    name: str
    purpose: str
    tool_categories: list[str]
    memory_categories: list[str]
    max_context_chars: int = 1800
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


AGENT_REGISTRY: dict[str, AgentSpec] = {
    "planner": AgentSpec(
        "planner",
        "Break user goals into steps, choose tools, and keep work scoped.",
        ["productivity", "memory", "research"],
        ["conversation", "project", "preference"],
    ),
    "tool": AgentSpec(
        "tool",
        "Execute direct actions through the tool registry with permissions and monitoring.",
        ["system", "web", "documents", "coding", "automation"],
        ["project", "preference"],
    ),
    "research": AgentSpec(
        "research",
        "Perform multi-source search, verification, source ranking, and report generation.",
        ["research", "web", "documents"],
        ["research", "knowledge"],
    ),
    "memory": AgentSpec(
        "memory",
        "Store, search, edit, delete, and summarize personal memory.",
        ["memory"],
        ["conversation", "learning", "knowledge", "project", "research", "document", "preference"],
    ),
    "learning": AgentSpec(
        "learning",
        "Extract durable knowledge from notes, web pages, PDFs, DOCX, TXT, videos, and corrections.",
        ["learning", "documents", "media"],
        ["learning", "knowledge"],
    ),
    "document": AgentSpec(
        "document",
        "Read, compare, edit, search, and generate documents.",
        ["documents"],
        ["document", "project"],
    ),
    "coding": AgentSpec(
        "coding",
        "Search repositories, explain code, detect bugs, refactor, and review architecture.",
        ["coding", "files"],
        ["project", "knowledge"],
    ),
    "finance": AgentSpec(
        "finance",
        "Track markets, watchlists, company analysis, earnings, and financial research.",
        ["finance", "research"],
        ["research", "preference"],
    ),
    "nasa": AgentSpec(
        "nasa",
        "Explore APOD, Mars rover data, Earth imagery, NEOs, missions, and space research.",
        ["nasa", "research"],
        ["knowledge", "research"],
    ),
    "orchestrator": AgentSpec(
        "orchestrator",
        "Coordinate planner, memory, tools, RAG, and LLM fallback for every request.",
        ["memory", "research", "documents", "coding", "finance", "nasa", "productivity"],
        ["conversation", "learning", "knowledge", "project", "research", "document", "preference"],
        max_context_chars=2200,
    ),
}


def select_agent(intent: str, message: str) -> AgentSpec:
    text = (message or "").lower()
    if intent in {"remember"} or "memory" in text or "remember" in text:
        return AGENT_REGISTRY["memory"]
    if any(word in text for word in ["research", "verify", "sources", "paper", "citation"]):
        return AGENT_REGISTRY["research"]
    if any(word in text for word in ["pdf", "docx", "document", "resume", "report"]):
        return AGENT_REGISTRY["document"]
    if any(word in text for word in ["code", "repo", "bug", "refactor", "architecture"]):
        return AGENT_REGISTRY["coding"]
    if any(word in text for word in ["stock", "market", "crypto", "finance", "earnings"]):
        return AGENT_REGISTRY["finance"]
    if any(word in text for word in ["nasa", "mars", "asteroid", "apod", "space"]):
        return AGENT_REGISTRY["nasa"]
    if any(word in text for word in ["plan", "task", "goal", "review"]):
        return AGENT_REGISTRY["planner"]
    return AGENT_REGISTRY["orchestrator"]
