"""qwen3_brain — QWEN3 brain integration with thinking mode and streaming.

Primary AI: QWEN3:1.7B Q4_K_M via Ollama
Secondary: Groq
Tertiary: Other APIs
Fallback: Ollama backup models

Features:
- Real-time thinking tokens display
- Token-by-token streaming
- Multi-language support (English, Hindi, Hinglish)
- Context-aware responses
- Personality-infused output
"""

from __future__ import annotations

import os
import json
import time
import logging
import asyncio
from typing import Any, Dict, List, Optional, AsyncGenerator
from dataclasses import dataclass

from core.router import AIRouter, RouterResponse
from core.context_engine import context_engine

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

CREATOR = "Abhinav"


@dataclass
class BrainResponse:
    """Response from the QWEN3 brain."""
    content: str = ""
    thinking: str = ""
    success: bool = False
    provider: str = ""
    model: str = ""
    latency_ms: float = 0.0
    tokens_generated: int = 0
    error: str = ""


class QWEN3Brain:
    """QWEN3 brain with thinking mode and streaming."""
    
    def __init__(self):
        self._router = AIRouter()
        self._thinking_mode = True  # Enabled - let the model reason freely
        self._stream_mode = True
        self._personality = self._load_personality()
        self._system_prompt = self._build_system_prompt()
        self._temperature = 0.7  # Allow natural, unrestricted reasoning
        
    def _load_personality(self) -> Dict[str, str]:
        """Load personality from memory or use defaults."""
        # TODO: Load from execution_first.MemoryStore when integrated
        # For now, use default personality
        return {
            "style": "concise",
            "formality": "professional",
            "humor": "light",
            "communication": "natural"
        }
    
    DOC_FILES = (
        "master_system_prompt.md",
        "thinking_pipeline.md",
        "planner.md",
        "memory.md",
        "safety_layer.md",
    )

    FOOD_FILES = (
        "00_identity.md", "01_reasoning.md", "02_tools.md",
        "10_personality.md", "11_safety.md", "19_response_style.md",
    )

    def _load_docs(self) -> str:
        """Load compact operating rules at startup (fits provider budgets)."""
        root = os.path.dirname(os.path.dirname(__file__))
        parts = []
        for name in self.DOC_FILES:
            path = None
            for candidate in (os.path.join(root, name), os.path.join(root, "docs", name)):
                if os.path.exists(candidate):
                    path = candidate
                    break
            if not path:
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    parts.append(f"=== {name} ===\n{content[:1500]}")
            except OSError:
                continue
        foods_dir = os.path.join(root, "foods")
        for fname in self.FOOD_FILES:
            path = os.path.join(foods_dir, fname)
            try:
                with open(path, encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    parts.append(f"=== foods/{fname} ===\n{content[:1200]}")
            except OSError:
                continue
        return "\n\n".join(parts)

    def _load_tools(self) -> str:
        """Load every registered tool contract for the LLM (compact)."""
        try:
            from core.tools import tool_registry
            tools = tool_registry.get_all()
            lines = []
            for name, t in tools.items():
                params = ", ".join(t.get("params", {}).keys())
                desc = t.get("description", "")
                if params:
                    lines.append(f"- {name}({params}): {desc[:90]}")
                else:
                    lines.append(f"- {name}(): {desc[:90]}")
            return "\n".join(lines) if lines else "No tools registered."
        except Exception:
            return "No tools registered."

    def _build_system_prompt(self) -> str:
        """Build system prompt: master rules + full docs + all tool contracts."""
        root = os.path.dirname(os.path.dirname(__file__))
        master_prompt = ""
        for candidate in (
            os.path.join(root, "master_system_prompt.md"),
            os.path.join(root, "docs", "master_system_prompt.md"),
        ):
            try:
                with open(candidate, encoding="utf-8") as f:
                    master_prompt = f.read().strip()
                if master_prompt:
                    logger.info("Loaded master system prompt from %s", candidate)
                    break
            except OSError:
                continue

        if master_prompt:
            docs = self._load_docs()
            tools = self._load_tools()
            return (
                master_prompt
                + "\n\n=== OPERATING DOCUMENTATION AND RULES ===\n" + docs
                + "\n\n=== AVAILABLE TOOLS ===\n" + tools
                + "\n\n=== TOOL CALL FORMAT ===\n"
                + "To call a tool, think about which tool fits, then end your reply with a JSON block:\n"
                + '{"tool":"tool_name","params":{"arg":"value"}}\n'
                + "Only include the JSON block when a tool call is needed. Never invent tools."
            )
        
        prompt_parts = [
            "You are JARVIS, an execution-first AI operating system created by Abhinav.",
            "",
            "Execution > Planning > Conversation.",
            "If a tool exists, use it. Never simulate or pretend an action happened.",
            "",
            "Think silently. Never include reasoning, meta-commentary, or think tags in your reply.",
            "For simple requests (greetings, quick facts), answer immediately without lengthy reasoning.",
            "",
            "Open apps and websites, search, play media, run system tasks.",
            "Only use conversation as the fallback when no tool matches.",
            "To call a tool, end your reply with a JSON block: {\"tool\":\"name\",\"params\":{...}}"
        ]
        return "\n".join(prompt_parts)
    
    def _update_context(self, user_input: str) -> None:
        """Update context engine with user input.
        
        TODO: Integrate with execution_first.MemoryStore when tool system is migrated.
        For now, use legacy context_engine.
        """
        try:
            context_engine.add_to_history(user_input, role="user")
        except Exception as e:
            logger.debug(f"Context update failed: {e}")
    
    def _history_messages(self) -> List[Dict[str, str]]:
        """Ongoing conversation from convo/ (persisted JSON) so fallback switches keep context."""
        try:
            from core.conversation_store import conversation_store
            history = conversation_store.messages(limit=20)
        except Exception as e:
            logger.debug(f"Conversation store unavailable: {e}")
            history = []
        if not history:
            try:
                history = context_engine.get_recent_history(limit=5)
            except Exception:
                history = []
        return history
    
    async def think(self, user_input: str, context: Dict[str, Any] = None) -> AsyncGenerator[str, None]:
        """Generate ultra-brief thinking tokens (rule-based, not LLM)."""
        context = context or {}
        
        # Simple rule-based thinking (2-3 words max)
        input_lower = user_input.lower().strip()
        
        # Greetings
        if any(word in input_lower for word in ["hello", "hi", "hey", "hii", "helloo"]):
            yield "\x00User wants greeting"
        # How are you
        elif "how are you" in input_lower or "how r u" in input_lower:
            yield "\x00User asking about me"
        # Questions
        elif "?" in input_lower:
            yield "\x00User has question"
        # Commands
        elif any(word in input_lower for word in ["open", "close", "play", "search", "launch"]):
            yield "\x00User wants action"
        # Default
        else:
            yield "\x00Processing request"
    
    async def generate(self, user_input: str, context: Dict[str, Any] = None) -> AsyncGenerator[str, None]:
        """Generate response token by token."""
        context = context or {}
        
        # Build messages
        messages = [
            {"role": "system", "content": self._system_prompt},
        ]
        
        # Add conversation history
        history = self._history_messages()
        for entry in history:
            messages.append({
                "role": entry["role"],
                "content": entry.get("content", "")
            })
        
        # Add current user input
        messages.append({"role": "user", "content": user_input})
        
        # Add context if available
        if context:
            context_str = f"\n\nCurrent Context:\n{json.dumps(context, indent=2)}"
            messages[-1]["content"] += context_str
        
        # Update context engine
        self._update_context(user_input)
        
        try:
            # Try Ollama first (QWEN2.5:14B - Primary via tunnel)
            if self._router._ollama:
                try:
                    emitted = False
                    async for token in self._router._ollama.chat_stream(
                        messages,
                        model=self._router._ollama.model,
                        temperature=self._temperature
                    ):
                        if token.strip():
                            emitted = True
                            yield token
                    if emitted:
                        return
                except Exception as e:
                    logger.debug(f"Ollama generation failed: {e}")
            
            # Fallback to other providers
            for provider in sorted(self._router._providers, key=lambda p: p.info.priority):
                try:
                    emitted = False
                    async for token in provider.chat_stream(messages, temperature=self._temperature):
                        if token.strip():
                            emitted = True
                            yield token
                    if emitted:
                        return
                except Exception as e:
                    logger.debug(f"Provider {provider.info.name} failed: {e}")
                    continue
            
            # All providers failed
            yield "I'm having trouble connecting right now. Please try again."
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            yield "Something went wrong. Please try again."
    
    async def generate_complete(self, user_input: str, context: Dict[str, Any] = None) -> BrainResponse:
        """Generate complete response (non-streaming)."""
        context = context or {}
        start_time = time.time()
        
        # Build messages
        messages = [
            {"role": "system", "content": self._system_prompt},
        ]
        
        # Add conversation history
        history = self._history_messages()
        for entry in history:
            messages.append({
                "role": entry["role"],
                "content": entry.get("content", "")
            })
        
        # Add current user input
        messages.append({"role": "user", "content": user_input})
        
        # Add context if available
        if context:
            context_str = f"\n\nCurrent Context:\n{json.dumps(context, indent=2)}"
            messages[-1]["content"] += context_str
        
        # Update context engine
        self._update_context(user_input)
        
        try:
            # Try Ollama first (QWEN3 - Primary)
            if self._router._ollama:
                try:
                    resp = await self._router._ollama.chat(
                        messages,
                        model=self._router._ollama.model,
                        temperature=self._temperature
                    )
                    if resp.success:
                        context_engine.add_to_history(resp.content, role="assistant")
                        return BrainResponse(
                            content=resp.content,
                            success=True,
                            provider="ollama",
                            model=self._router._ollama.model,
                            latency_ms=resp.latency_ms
                        )
                except Exception as e:
                    logger.debug(f"Ollama generation failed: {e}")
            
            # Fallback to other providers
            for provider in sorted(self._router._providers, key=lambda p: p.info.priority):
                try:
                    resp = await provider.chat(messages, temperature=self._temperature)
                    if resp.success:
                        context_engine.add_to_history(resp.content, role="assistant")
                        return BrainResponse(
                            content=resp.content,
                            success=True,
                            provider=provider.info.name,
                            model=provider.info.models[0] if provider.info.models else "unknown",
                            latency_ms=resp.latency_ms
                        )
                except Exception as e:
                    logger.debug(f"Provider {provider.info.name} failed: {e}")
                    continue
            
            # All providers failed
            return BrainResponse(
                success=False,
                error="All AI providers failed",
                latency_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return BrainResponse(
                success=False,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000
            )
    
    def enable_thinking_mode(self) -> None:
        """Enable thinking mode."""
        self._thinking_mode = True
        logger.info("Thinking mode enabled")
    
    def disable_thinking_mode(self) -> None:
        """Disable thinking mode."""
        self._thinking_mode = False
        logger.info("Thinking mode disabled")
    
    def enable_stream_mode(self) -> None:
        """Enable streaming mode."""
        self._stream_mode = True
        logger.info("Stream mode enabled")
    
    def disable_stream_mode(self) -> None:
        """Disable streaming mode."""
        self._stream_mode = False
        logger.info("Stream mode disabled")
    
    def set_temperature(self, temperature: float) -> None:
        """Set temperature for generation (0.0 - 1.0)."""
        self._temperature = max(0.0, min(1.0, temperature))
        logger.info(f"Temperature set to {self._temperature}")
    
    def reload_system_prompt(self) -> None:
        """Reload system prompt (useful after personality changes)."""
        self._personality = self._load_personality()
        self._system_prompt = self._build_system_prompt()
        logger.info("System prompt reloaded")


# Global QWEN3 brain instance
qwen3_brain = QWEN3Brain()
