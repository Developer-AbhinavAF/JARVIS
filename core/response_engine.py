"""response_engine — Response generation and formatting engine.

Handles:
- Natural language response generation
- Multi-language formatting
- Personality infusion
- Response styling
- Speech preparation
- Error message formatting
"""

from __future__ import annotations

import json
import logging
import asyncio
from typing import Any, Dict, List, Optional, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
import time

from core.qwen3_brain import qwen3_brain, BrainResponse
from core.memory_engine import memory_engine
from core.context_engine import context_engine
from core.tools import ToolResult

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


class ResponseStyle(Enum):
    """Response style options."""
    CONCISE = "concise"
    DETAILED = "detailed"
    CONVERSATIONAL = "conversational"
    TECHNICAL = "technical"
    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"


class ResponseMedium(Enum):
    """Response medium options."""
    TEXT = "text"
    SPEECH = "speech"
    BOTH = "both"


@dataclass
class Response:
    """Represents a complete response."""
    content: str = ""
    thinking: str = ""
    success: bool = True
    style: ResponseStyle = ResponseStyle.CONVERSATIONAL
    medium: ResponseMedium = ResponseMedium.BOTH
    language: str = "en"
    confidence: float = 0.0
    tool_used: str = ""
    tool_result: Optional[ToolResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class ResponseEngine:
    """Response generation and formatting engine."""
    
    def __init__(self):
        self._personality = self._load_personality()
        self._default_style = ResponseStyle.CONVERSATIONAL
        self._default_medium = ResponseMedium.BOTH
        self._default_language = "en"
        
    def _load_personality(self) -> Dict[str, str]:
        """Load personality settings from memory."""
        personality = memory_engine._load_json(memory_engine._personality_file)
        return {
            "style": personality.get("response_preference", "concise"),
            "formality": personality.get("formality_preference", "professional"),
            "humor": personality.get("humor_tolerance", "light"),
            "communication": personality.get("communication_style", "natural")
        }
    
    def _detect_language(self, text: str) -> str:
        """Detect language of input text."""
        # Simple language detection
        hindi_indicators = ["kya", "kaise", "kahan", "hai", "ho", "kar", "karo", "kholo", "banao"]
        hinglish_indicators = ["kya", "kaise", "please", "can you", "could you"]
        
        text_lower = text.lower()
        
        # Check for Hindi words
        if any(indicator in text_lower for indicator in hindi_indicators):
            # Check if mixed with English
            if any(word in text_lower for word in ["please", "can", "could", "would"]):
                return "hi-en"  # Hinglish
            return "hi"  # Hindi
        
        # Default to English
        return "en"
    
    def _apply_personality(self, content: str, style: ResponseStyle) -> str:
        """Apply personality to response content."""
        # In production, this would use more sophisticated NLP
        personality = self._personality
        
        # Adjust based on formality
        if personality["formality"] == "professional":
            # Make more formal
            content = content.replace("hey", "hello")
            content = content.replace("yeah", "yes")
            content = content.replace("nope", "no")
        elif personality["formality"] == "casual":
            # Make more casual
            content = content.replace("hello", "hey")
            content = content.replace("yes", "yeah")
        
        # Adjust based on humor tolerance
        if personality["humor"] == "none":
            # Remove humor markers (simplified)
            content = content.replace("😊", "")
            content = content.replace("😄", "")
        
        return content
    
    def _format_for_medium(self, content: str, medium: ResponseMedium) -> str:
        """Format response for specific medium."""
        if medium == ResponseMedium.SPEECH:
            # Add speech-friendly formatting
            # Remove special characters that don't speak well
            content = content.replace("*", "")
            content = content.replace("_", "")
            content = content.replace("~", "")
            # Add natural pauses
            content = content.replace(". ", ". ... ")
            content = content.replace("! ", "! ... ")
            content = content.replace("? ", "? ... ")
        
        return content
    
    def _format_tool_result(self, tool_result: ToolResult, tool_name: str) -> str:
        """Format tool result into natural language."""
        if not tool_result:
            return ""
        
        if tool_result.success:
            if tool_result.verified:
                return f"Successfully {tool_name.replace('_', ' ')}."
            else:
                return f"Executed {tool_name.replace('_', ' ')}, but verification failed."
        else:
            return f"Failed to {tool_name.replace('_', ' ')}: {tool_result.error}"
    
    def _format_error(self, error: str, context: str = "") -> str:
        """Format error message naturally."""
        if context:
            return f"I encountered an error while {context}: {error}. Please try again or let me know if you need help."
        return f"Something went wrong: {error}. Please try again."
    
    async def generate_response(self, user_input: str, tool_result: Optional[ToolResult] = None,
                                 tool_name: str = "", context: Dict[str, Any] = None) -> Response:
        """Generate a complete response."""
        context = context or {}
        
        # Detect language
        language = self._detect_language(user_input)
        
        # Get personality settings
        style = self._default_style
        if self._personality["style"] == "concise":
            style = ResponseStyle.CONCISE
        elif self._personality["style"] == "detailed":
            style = ResponseStyle.DETAILED
        
        # Generate response using QWEN3 brain
        brain_response = await qwen3_brain.generate_complete(user_input, context)
        
        if brain_response.success:
            content = brain_response.content
        else:
            # Fallback response
            if tool_result and tool_result.success:
                content = self._format_tool_result(tool_result, tool_name)
            else:
                content = "I'm not sure how to help with that. Could you please rephrase your request?"
        
        # Apply personality
        content = self._apply_personality(content, style)
        
        # Add tool result information if available
        if tool_result and tool_name:
            tool_message = self._format_tool_result(tool_result, tool_name)
            if tool_message and tool_result.success:
                content = f"{content} {tool_message}"
        
        # Create response object
        response = Response(
            content=content,
            thinking=brain_response.thinking if brain_response.success else "",
            success=brain_response.success,
            style=style,
            medium=self._default_medium,
            language=language,
            confidence=0.8,  # Placeholder confidence
            tool_used=tool_name,
            tool_result=tool_result,
            metadata={
                "provider": brain_response.provider if brain_response.success else "",
                "model": brain_response.model if brain_response.success else "",
                "latency_ms": brain_response.latency_ms if brain_response.success else 0
            }
        )
        
        return response
    
    async def generate_response_stream(self, user_input: str, tool_result: Optional[ToolResult] = None,
                                      tool_name: str = "", context: Dict[str, Any] = None) -> AsyncGenerator[str, None]:
        """Generate streaming response token by token."""
        context = context or {}
        
        # Detect language
        language = self._detect_language(user_input)
        
        # Stream from QWEN3 brain
        async for token in qwen3_brain.generate(user_input, context):
            # Apply personality (simplified for streaming)
            yield token
        
        # Add tool result information if available
        if tool_result and tool_name and tool_result.success:
            tool_message = self._format_tool_result(tool_result, tool_name)
            for char in tool_message:
                yield char
    
    async def generate_error_response(self, error: str, context: str = "") -> Response:
        """Generate an error response."""
        content = self._format_error(error, context)
        
        return Response(
            content=content,
            success=False,
            style=ResponseStyle.CONVERSATIONAL,
            medium=self._default_medium,
            language=self._default_language,
            metadata={"error": error, "context": context}
        )
    
    async def generate_thinking_stream(self, user_input: str) -> AsyncGenerator[str, None]:
        """Generate thinking stream for display."""
        yield "Thinking..."
        async for token in qwen3_brain.think(user_input):
            yield token
        yield "\nAnswer..."
    
    def set_style(self, style: ResponseStyle) -> None:
        """Set default response style."""
        self._default_style = style
        logger.info(f"Response style set to {style.value}")
    
    def set_medium(self, medium: ResponseMedium) -> None:
        """Set default response medium."""
        self._default_medium = medium
        logger.info(f"Response medium set to {medium.value}")
    
    def set_language(self, language: str) -> None:
        """Set default language."""
        self._default_language = language
        logger.info(f"Language set to {language}")
    
    def reload_personality(self) -> None:
        """Reload personality settings."""
        self._personality = self._load_personality()
        logger.info("Personality reloaded")
    
    def format_for_speech(self, response: Response) -> str:
        """Format response for speech output."""
        content = response.content
        
        # Apply speech formatting
        content = self._format_for_medium(content, ResponseMedium.SPEECH)
        
        # Add speech markers if needed
        if response.language == "hi":
            # Hindi-specific speech formatting
            content = content.replace("।", " ... ")
        
        return content
    
    def format_for_text(self, response: Response) -> str:
        """Format response for text display."""
        content = response.content
        
        # Apply text formatting
        if response.style == ResponseStyle.TECHNICAL:
            # Add code formatting markers
            if "```" in content:
                pass  # Already has code blocks
        
        return content
    
    def get_response_stats(self) -> Dict[str, Any]:
        """Get response generation statistics."""
        return {
            "default_style": self._default_style.value,
            "default_medium": self._default_medium.value,
            "default_language": self._default_language,
            "personality": self._personality
        }


# Global response engine instance
response_engine = ResponseEngine()