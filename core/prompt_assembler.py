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
from core.memory_human import human_memory
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
        """Build context-aware message list adhering to token budget.

        JARVIS AGI already contains identity, behavior, tool-selection and
        execution rules — the legacy identity/food/tool-card system prompt is
        NOT injected. Only live dynamic context (world state) is attached.
        """
        messages = []

        # 1. Minimal system context — no identity duplication, no instruction
        #    prompts, no natural-language tool contract dump (tools are sent
        #    as structured schemas by the brain when the API supports them).
        system_content = ""
        state_summary = world_state_engine.get_context_summary()
        if state_summary:
            system_content += f"--- World State ---\n{state_summary}\n"

        messages.append({"role": "system", "content": system_content})

        # 4. Add Memory Context if needed (~250 tokens, just-in-time)
        #    Priority: human-like memory (Drive-backed) first, then legacy unified_memory
        if plan.requires_memory:
            mem_block = ""
            
            # Try human-like memory first (Google Drive backed, ranked, bounded)
            if human_memory.is_started():
                mem_block = human_memory.context_for(query, budget_tokens=4000)
            
            # Fallback to legacy unified_memory if human memory not available
            if not mem_block:
                mem_entries = unified_memory.retrieve(query, top_k=5)
                mem_block = unified_memory.format_memories(mem_entries)
                if mem_block:
                    mem_block = f"--- Retained Memory ---\n{mem_block}\n\n"
            
            if mem_block:
                instruction = (
                    "Use only the memories listed above to ground your "
                    "answer. If the user asked you to remember "
                    "something, confirm the save only if the matching "
                    "entry is listed above; otherwise say you couldn't "
                    "save it. If no memory matches the user's question, "
                    "say you don't have that stored."
                )
                messages.append({
                    "role": "system",
                    "content": f"{mem_block}{instruction}",
                })

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
