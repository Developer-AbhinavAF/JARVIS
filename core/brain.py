"""brain — Unified brain system for all JARVIS interfaces.

Consolidates QWEN3 brain and AI router into a single unified brain
that uses dynamic profiles for adaptive generation.
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
from core.context import get_context
from core.profiles import ProfileManager, Profile
from core.cache import get_cache

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

CREATOR = "Abhinav"


@dataclass
class BrainResponse:
    """Response from the brain."""
    content: str = ""
    thinking: str = ""
    success: bool = False
    provider: str = ""
    model: str = ""
    latency_ms: float = 0.0
    tokens_generated: int = 0
    profile: str = ""
    error: str = ""


class Brain:
    """Unified brain with dynamic profile support."""
    
    def __init__(self):
        self._router = AIRouter()
        self._profiles = ProfileManager()
        self._cache = get_cache()
        self._context = get_context()
        
        # Personality system
        self._personality = self._load_personality()
        self._system_prompt = self._build_system_prompt()
        
        # Stats
        self._total_requests = 0
        self._total_tokens = 0
    
    def _load_personality(self) -> Dict[str, str]:
        """Load personality from memory or use defaults."""
        # Try to load from memory
        from core.memory import get_memory
        memory = get_memory()
        
        personality_entry = memory.recall("personality", "preferences")
        if personality_entry:
            return personality_entry.value
        
        # Default personality
        return {
            "style": "concise",
            "formality": "professional",
            "humor": "light",
            "communication": "natural"
        }
    
    MASTER_PROMPT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "master_system_prompt.md")
    MASTER_PROMPT_PATHS = (
        MASTER_PROMPT_PATH,
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "master_system_prompt.md"),
    )

    def _build_system_prompt(self) -> str:
        """Build system prompt.

        JARVIS AGI is a fine-tuned model with behavior, personality and
        tool-selection rules embedded — the legacy master system prompt is
        NOT injected at runtime to avoid duplicating identity/instructions.
        """
        return ""
    
    def _update_personality(self, trait: str, value: str) -> None:
        """Update personality trait."""
        self._personality[trait] = value
        self._system_prompt = self._build_system_prompt()
        
        # Save to memory
        from core.memory import get_memory
        memory = get_memory()
        memory.remember("personality", self._personality, "preferences")
    
    async def think(self, user_input: str, context: Dict[str, Any] = None) -> AsyncGenerator[str, None]:
        """Generate ultra-brief thinking tokens (rule-based)."""
        context = context or {}
        input_lower = user_input.lower().strip()
        
        # Simple rule-based thinking
        if any(word in input_lower for word in ["hello", "hi", "hey", "hii", "helloo"]):
            yield "\x00User wants greeting"
        elif "how are you" in input_lower or "how r u" in input_lower:
            yield "\x00User asking about me"
        elif "?" in input_lower:
            yield "\x00User has question"
        elif any(word in input_lower for word in ["open", "close", "play", "search", "launch"]):
            yield "\x00User wants action"
        else:
            yield "\x00Processing request"
    
    async def generate(self, user_input: str, profile: Optional[Profile] = None,
                      context: Dict[str, Any] = None) -> AsyncGenerator[str, None]:
        """Generate response token by token using dynamic profile."""
        context = context or {}
        
        # Select profile if not provided
        if profile is None:
            profile = self._profiles.select_profile(user_input, context)
        
        # Get LLM parameters from profile
        params = profile.get_llm_params()
        
        # Build messages
        messages = [
            {"role": "system", "content": self._system_prompt},
        ]
        
        # Add conversation history
        history = self._context.get_recent_history(limit=5)
        for entry in history:
            if entry["role"] in ["user", "assistant"]:
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
        
        # Update context
        self._context.add_context(user_input)
        
        # Check cache first
        cache_key = self._cache._hash_text(json.dumps(messages[-5:]))
        cached_response = self._cache.get_prompt(cache_key)
        if cached_response and not profile.think:
            logger.debug("Using cached response")
            for char in cached_response:
                yield char
            return
        
        try:
            # Try Ollama first (QWEN3 - Primary)
            if self._router._ollama:
                try:
                    async for token in self._router._ollama.chat_stream(
                        messages,
                        model=self._router._ollama.model,
                        temperature=params["temperature"],
                        num_predict=params["num_predict"]
                    ):
                        if token.strip():
                            yield token
                    return
                except Exception as e:
                    logger.debug(f"Ollama generation failed: {e}")
            
            # Fallback to other providers
            for provider in sorted(self._router._providers, key=lambda p: p.info.priority):
                try:
                    async for token in provider.chat_stream(
                        messages,
                        temperature=params["temperature"]
                    ):
                        if token.strip():
                            yield token
                    return
                except Exception as e:
                    logger.debug(f"Provider {provider.info.name} failed: {e}")
                    continue
            
            # All providers failed
            yield "I'm having trouble connecting right now. Please try again."
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            yield "Something went wrong. Please try again."
    
    async def generate_complete(self, user_input: str, profile: Optional[Profile] = None,
                               context: Dict[str, Any] = None) -> BrainResponse:
        """Generate complete response (non-streaming)."""
        context = context or {}
        start_time = time.time()
        
        # Select profile if not provided
        if profile is None:
            profile = self._profiles.select_profile(user_input, context)
        
        # Get LLM parameters from profile
        params = profile.get_llm_params()
        
        # Build messages
        messages = [
            {"role": "system", "content": self._system_prompt},
        ]
        
        # Add conversation history
        history = self._context.get_recent_history(limit=5)
        for entry in history:
            if entry["role"] in ["user", "assistant"]:
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
        
        # Update context
        self._context.add_context(user_input)
        
        # Check cache first
        cache_key = self._cache._hash_text(json.dumps(messages[-5:]))
        cached_response = self._cache.get_prompt(cache_key)
        if cached_response and not profile.think:
            logger.debug("Using cached response")
            return BrainResponse(
                content=cached_response,
                success=True,
                provider="cache",
                model="cached",
                latency_ms=0.0,
                profile=profile.name
            )
        
        try:
            # Try Ollama first (QWEN3 - Primary)
            if self._router._ollama:
                try:
                    resp = await self._router._ollama.chat(
                        messages,
                        model=self._router._ollama.model,
                        temperature=params["temperature"],
                        num_predict=params["num_predict"]
                    )
                    if resp.success:
                        # Cache response
                        self._cache.set_prompt(cache_key, resp.content)
                        
                        # Update context with response
                        self._context.add_context(
                            user_input,
                            metadata={"response": resp.content}
                        )
                        
                        # Update stats
                        self._total_requests += 1
                        self._total_tokens += len(resp.content)
                        
                        return BrainResponse(
                            content=resp.content,
                            success=True,
                            provider="ollama",
                            model=resp.model,
                            latency_ms=resp.latency_ms,
                            profile=profile.name
                        )
                except Exception as e:
                    logger.debug(f"Ollama generation failed: {e}")
            
            # Fallback to other providers
            for provider in sorted(self._router._providers, key=lambda p: p.info.priority):
                try:
                    resp = await provider.chat(
                        messages,
                        temperature=params["temperature"]
                    )
                    if resp.success:
                        # Cache response
                        self._cache.set_prompt(cache_key, resp.content)
                        
                        # Update context with response
                        self._context.add_context(
                            user_input,
                            metadata={"response": resp.content}
                        )
                        
                        # Update stats
                        self._total_requests += 1
                        self._total_tokens += len(resp.content)
                        
                        return BrainResponse(
                            content=resp.content,
                            success=True,
                            provider=provider.info.name,
                            model=resp.model,
                            latency_ms=resp.latency_ms,
                            profile=profile.name
                        )
                except Exception as e:
                    logger.debug(f"Provider {provider.info.name} failed: {e}")
                    continue
            
            # All providers failed
            return BrainResponse(
                content="I'm having trouble connecting right now. Please try again.",
                success=False,
                error="All providers failed"
            )
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return BrainResponse(
                content="Something went wrong. Please try again.",
                success=False,
                error=str(e)
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get brain statistics."""
        return {
            "total_requests": self._total_requests,
            "total_tokens": self._total_tokens,
            "personality": self._personality,
            "available_profiles": list(self._profiles.get_all_profiles().keys())
        }


# Global brain instance
global_brain: Optional[Brain] = None


def get_brain() -> Brain:
    """Get global brain instance."""
    global global_brain
    if global_brain is None:
        global_brain = Brain()
    return global_brain


def set_brain(brain: Brain) -> None:
    """Set global brain instance."""
    global global_brain
    global_brain = brain
