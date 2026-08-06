"""core/prompt_assembler.py — PromptAssembler & TokenBudgetManager for JARVIS vNext++.

Assembles the minimal valid prompt context for model requests adhering to strict
token allocation limits:
- System Prompt: ~500 tokens
- Memory Context: ~250 tokens
- Dynamic Foods: ~300 tokens
- RAG Context: ~800 tokens
- Conversation Context: ~1000 tokens
- Safety Margin: ~500 tokens
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from core.world_state import world_state_engine
from core.memory import unified_memory
from core.rag import rag_engine
from core.foods import food_engine
from core.planner import ExecutionPlan

logger = logging.getLogger(__name__)


@dataclass
class AssembledPrompt:
    system_prompt: str
    messages: List[Dict[str, str]]
    profile: str
    max_tokens: int


class PromptAssembler:
    """Engine compiling smallest valid prompt context."""

    def __init__(self):
        pass

    def assemble(
        self,
        query: str,
        plan: ExecutionPlan,
        history: List[Dict[str, str]] = None,
        tool_cards: List[Dict[str, Any]] = None,
    ) -> AssembledPrompt:
        """Build context-aware message list adhering to token budget."""
        messages = []

        # 1. System Prompt & Identity Food (~500 tokens)
        food_text = food_engine.get_food_for_intent(plan.profile)
        system_content = (
            "You are JARVIS, an execution-first local AI Operating System created by Abhinav.\n"
            "Execution > Planning > Conversation. If a tool exists, use it. Never simulate an action.\n"
            "Never reveal internal reasoning. Only output a tool call or a final response.\n"
            "Respond naturally, concisely, and directly. Never invent tools.\n\n"
            f"--- Core Directives ---\n{food_text[:1200]}\n"
        )
        
        # 2. Add World State Context (~150 tokens)
        state_summary = world_state_engine.get_context_summary()
        system_content += f"\n--- World State ---\n{state_summary}\n"

        # 3. Add Candidate Tool Cards if present (~400 tokens)
        if tool_cards:
            system_content += "\n--- Available Tools ---\n"
            for card in tool_cards[:3]:
                system_content += (
                    f"Tool: {card.get('name')}\n"
                    f"Description: {card.get('description')}\n"
                    f"Args: {card.get('arguments')}\n\n"
                )

        messages.append({"role": "system", "content": system_content})

        # 4. Add Memory Context if needed (~250 tokens)
        if plan.requires_memory:
            mem_summary = unified_memory.get_memory_summary()
            if mem_summary:
                messages.append({"role": "system", "content": f"--- Retained Memory ---\n{mem_summary}"})

        # 5. Add RAG Context if required (~800 tokens)
        if plan.requires_rag and plan.top_k_rag > 0:
            rag_context = rag_engine.format_rag_context(query, top_k=plan.top_k_rag)
            if rag_context:
                messages.append({"role": "system", "content": f"--- Relevant Documentation ---\n{rag_context}"})

        # 6. Add Raw Conversation History (Last 8 messages ~1000 tokens)
        if history:
            for msg in history[-8:]:
                if msg.get("role") in ["user", "assistant"]:
                    messages.append({"role": msg["role"], "content": msg.get("content", "")})

        # 7. Add Current Query
        messages.append({"role": "user", "content": query})

        # Determine num_predict by profile
        max_predict = 2048
        if plan.profile in ["CODING", "WRITING", "RESEARCH"]:
            max_predict = 4096
        elif plan.profile in ["FAST"]:
            max_predict = 1024

        return AssembledPrompt(
            system_prompt=system_content,
            messages=messages,
            profile=plan.profile,
            max_tokens=max_predict,
        )


prompt_assembler = PromptAssembler()
