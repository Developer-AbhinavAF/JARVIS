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
from core.memory_engine import memory_engine
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
        self._thinking_mode = True
        self._stream_mode = True
        self._personality = self._load_personality()
        self._system_prompt = self._build_system_prompt()
        
    def _load_personality(self) -> Dict[str, str]:
        """Load personality from memory."""
        personality = memory_engine._load_json(memory_engine._personality_file)
        return {
            "style": personality.get("response_preference", "concise"),
            "formality": personality.get("formality_preference", "professional"),
            "humor": personality.get("humor_tolerance", "light"),
            "communication": personality.get("communication_style", "natural")
        }
    
    def _build_system_prompt(self) -> str:
        """Build comprehensive system prompt from FOOD system."""
        # Load FOOD configuration
        food_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "food")
        
        prompt_parts = [
            "# JARVIS AI System",
            "",
            "You are JARVIS, an intelligent AI assistant created by Abhinav.",
            "",
            "## Core Personality",
            "- Intelligent: Capable and knowledgeable",
            "- Calm: Composed under pressure",
            "- Human: Natural and relatable",
            "- Helpful: Proactive and solution-oriented",
            "- Slightly Witty: Appropriate humor",
            "- Professional: Respectful and reliable",
            "",
            "## Communication Style",
            f"- Formality: {self._personality['formality']}",
            f"- Humor: {self._personality['humor']}",
            f"- Response style: {self._personality['style']}",
            f"- Communication: {self._personality['communication']}",
            "",
            "## Multi-Language Support",
            "- English: Full support",
            "- Hindi: Full support (हिंदी)",
            "- Hinglish: Full support (Roman Hindi + English mix)",
            "- Roman Hindi: Full support",
            "- Detect language automatically and respond appropriately",
            "- Examples:",
            "  - 'open youtube' → English",
            "  - 'youtube kholo' → Hindi",
            "  - 'youtube khol do' → Hinglish",
            "  - 'jara youtube open karo' → Mixed",
            "  - 'can you launch youtube please' → English formal",
            "",
            "## Tool Usage",
            "You have access to these tools:",
            "- open_app: Launch applications",
            "- close_app: Close applications",
            "- open_url: Open websites",
            "- web_search: Search Google",
            "- search_youtube: Search YouTube",
            "- play_media: Play songs/videos",
            "- take_screenshot: Capture screen",
            "- screen_analysis: Analyze screen with OCR",
            "- get_system_stats: System information",
            "- system_sleep/shutdown/lock: System control",
            "- adjust_volume/brightness: System controls",
            "- save_memory/recall_memory: Memory operations",
            "- create_file/read_file/delete_file: File operations",
            "- calculate: Math calculations",
            "- get_time/get_date: Time and date",
            "- get_weather: Weather information",
            "- type_text/press_key: Desktop control",
            "- copy_to_clipboard/paste_from_clipboard: Clipboard",
            "",
            "## Response Format",
            "When you need to use a tool, respond with JSON:",
            '```json',
            '{"tool": "tool_name", "params": {"param": "value"}, "response": "natural language response"}',
            '```',
            "",
            "For general conversation, respond naturally without JSON.",
            "",
            "## Context Understanding",
            "- Maintain conversation context",
            "- Resolve pronouns (there, that, it, this)",
            "- Reference previous statements",
            "- Track entities mentioned",
            "",
            "## User Profile",
        ]
        
        # Add user profile if available
        profile_summary = memory_engine.get_profile_summary()
        if profile_summary and "No profile information" not in profile_summary:
            prompt_parts.append(profile_summary)
        
        prompt_parts.extend([
            "",
            "## Important Rules",
            "- NO hardcoded responses",
            "- NO keyword matching",
            "- NO fake success messages",
            "- Always verify tool execution",
            "- Be helpful and honest",
            "- Admit when you don't know something",
            "- Learn from mistakes",
            "- Protect user privacy",
            "",
            "## Thinking Process",
            "When processing complex requests, think step-by-step:",
            "1. Understand user intent",
            "2. Analyze context",
            "3. Select appropriate tool(s)",
            "4. Plan execution",
            "5. Consider verification",
            "6. Formulate response",
            "",
            "Remember: You are JARVIS, a human-level AI assistant. Be helpful, be accurate, be real.",
        ])
        
        return "\n".join(prompt_parts)
    
    def _update_context(self, user_input: str) -> None:
        """Update context engine with user input."""
        from core.context_engine import ContextEntity
        entities: list[ContextEntity] = []
        text = user_input.lower()
        
        apps = ["chrome", "firefox", "vscode", "spotify", "youtube", "github", "gmail"]
        for app in apps:
            if app in text:
                entities.append(ContextEntity(name=app, type="app"))
        
        websites = ["youtube", "github", "google", "gmail", "chatgpt", "reddit", "twitter"]
        for site in websites:
            if site in text:
                entities.append(ContextEntity(name=site, type="website"))
        
        context_engine.add_context(
            user_input=user_input,
            entities=entities
        )
    
    async def think(self, user_input: str, context: Dict[str, Any] = None) -> AsyncGenerator[str, None]:
        """Generate thinking tokens in real-time."""
        context = context or {}
        
        # Build messages
        messages = [
            {"role": "system", "content": self._system_prompt},
        ]
        
        # Add conversation history
        history = context_engine.get_recent_history(limit=5)
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
        
        # Update context engine
        self._update_context(user_input)
        
        # Generate thinking process
        thinking_prompt = f"""Think step-by-step about this user request: "{user_input}"

Consider:
1. What does the user want?
2. What tools might be needed?
3. What is the current context?
4. How should I respond?

Provide your thinking process step by step."""
        
        try:
            # Try Ollama first (QWEN3)
            if self._router._ollama:
                try:
                    async for token in self._router._ollama.chat_stream(
                        [{"role": "user", "content": thinking_prompt}],
                        model=self._router._ollama.model
                    ):
                        if token.strip():
                            yield token
                except Exception as e:
                    logger.debug(f"Ollama thinking failed: {e}")
                    yield "Thinking..."
            
            # Fallback to other providers
            for provider in sorted(self._router._providers, key=lambda p: p.info.priority):
                try:
                    async for token in provider.chat_stream([{"role": "user", "content": thinking_prompt}]):
                        if token.strip():
                            yield token
                    break
                except Exception as e:
                    logger.debug(f"Provider {provider.info.name} thinking failed: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Thinking generation failed: {e}")
            yield "Thinking..."
    
    async def generate(self, user_input: str, context: Dict[str, Any] = None) -> AsyncGenerator[str, None]:
        """Generate response token by token."""
        context = context or {}
        
        # Build messages
        messages = [
            {"role": "system", "content": self._system_prompt},
        ]
        
        # Add conversation history
        history = context_engine.get_recent_history(limit=5)
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
        
        # Update context engine
        self._update_context(user_input)
        
        try:
            # Try Ollama first (QWEN3 - Primary)
            if self._router._ollama:
                try:
                    async for token in self._router._ollama.chat_stream(
                        messages,
                        model=self._router._ollama.model
                    ):
                        if token.strip():
                            yield token
                    return
                except Exception as e:
                    logger.debug(f"Ollama generation failed: {e}")
            
            # Fallback to Groq (Secondary)
            for provider in sorted(self._router._providers, key=lambda p: p.info.priority):
                try:
                    async for token in provider.chat_stream(messages):
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
    
    async def generate_complete(self, user_input: str, context: Dict[str, Any] = None) -> BrainResponse:
        """Generate complete response (non-streaming)."""
        context = context or {}
        
        # Build messages
        messages = [
            {"role": "system", "content": self._system_prompt},
        ]
        
        # Add conversation history
        history = context_engine.get_recent_history(limit=5)
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
        
        # Update context engine
        self._update_context(user_input)
        
        start_time = time.time()
        
        try:
            # Try Ollama first (QWEN3 - Primary)
            if self._router._ollama:
                try:
                    response = await self._router._ollama.chat(
                        messages,
                        model=self._router._ollama.model
                    )
                    if response.success:
                        return BrainResponse(
                            content=response.content,
                            success=True,
                            provider="ollama",
                            model=response.model,
                            latency_ms=response.latency_ms
                        )
                except Exception as e:
                    logger.debug(f"Ollama generation failed: {e}")
            
            # Fallback to Groq (Secondary)
            for provider in sorted(self._router._providers, key=lambda p: p.info.priority):
                try:
                    response = await provider.chat(messages)
                    if response.success:
                        return BrainResponse(
                            content=response.content,
                            success=True,
                            provider=provider.info.name,
                            model=response.model,
                            latency_ms=response.latency_ms
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
    
    def reload_system_prompt(self) -> None:
        """Reload system prompt (useful after personality changes)."""
        self._personality = self._load_personality()
        self._system_prompt = self._build_system_prompt()
        logger.info("System prompt reloaded")


# Global QWEN3 brain instance
qwen3_brain = QWEN3Brain()