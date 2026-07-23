"""jarvis_core — Main JARVIS AI Operating System integration.

Integrates all components:
- Context Engine
- Memory Engine  
- QWEN3 Brain
- Planner Engine
- Tool Chain Engine
- Tool Executor
- Response Engine
- Speech Engine
- Vision Engine
- Web Automation
- Desktop Control
- Knowledge Engine
- Self-Improvement
"""

from __future__ import annotations

import os
import sys
import json
import logging
import asyncio
from typing import Any, Dict, List, Optional, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


@dataclass
class JARVISConfig:
    """JARVIS configuration."""
    debug_mode: bool = False
    speech_enabled: bool = True
    thinking_enabled: bool = True
    streaming_enabled: bool = True
    language: str = "en"
    personality: str = "professional"
    verification_enabled: bool = True


@dataclass
class JARVISResponse:
    """Complete JARVIS response."""
    user_input: str = ""
    response: str = ""
    thinking: str = ""
    success: bool = True
    tool_used: str = ""
    verified: bool = False
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class JARVISCore:
    """Main JARVIS AI Operating System."""
    
    def __init__(self, config: JARVISConfig = None):
        self._config = config or JARVISConfig()
        self._initialized = False
        self._running = False
        
        # Import all engines
        self._import_engines()
    
    def _import_engines(self) -> None:
        """Import all JARVIS engines."""
        try:
            from core.context_engine import context_engine
            from core.memory_engine import memory_engine
            from core.qwen3_brain import qwen3_brain
            from core.planner_engine import planner_engine
            from core.tool_chain_engine import tool_chain_engine
            from core.execution import execution_engine
            from core.response_engine import response_engine
            from core.speech_engine import speech_engine
            from core.vision_engine import vision_engine
            from core.web_automation import web_automation_engine
            from core.desktop_control import desktop_control
            from core.knowledge_engine import knowledge_engine
            from core.self_improvement import self_improvement_engine
            from core.startup import StartupScreen
            
            self.context_engine = context_engine
            self.memory_engine = memory_engine
            self.qwen3_brain = qwen3_brain
            self.planner_engine = planner_engine
            self.tool_chain_engine = tool_chain_engine
            self.execution_engine = execution_engine
            self.response_engine = response_engine
            self.speech_engine = speech_engine
            self.vision_engine = vision_engine
            self.web_automation = web_automation_engine
            self.desktop_control = desktop_control
            self.knowledge_engine = knowledge_engine
            self.self_improvement = self_improvement_engine
            self.startup_screen = StartupScreen
            
            logger.info("All engines imported successfully")
            
        except ImportError as e:
            logger.error(f"Failed to import engines: {e}")
            raise
    
    async def initialize(self) -> bool:
        """Initialize JARVIS system."""
        if self._initialized:
            return True
        
        try:
            # Show startup screen
            startup_result = await self.startup_screen.show_startup()
            
            if not startup_result["success"]:
                logger.warning("Some components failed to load")
            
            self._initialized = True
            logger.info("JARVIS initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize JARVIS: {e}")
            return False
    
    async def handle(self, user_input: str) -> JARVISResponse:
        """Handle user input through the complete pipeline."""
        start_time = time.time()
        
        if not self._initialized:
            await self.initialize()
        
        response = JARVISResponse(user_input=user_input)
        
        try:
            # Add to context
            self.context_engine.add_context(user_input=user_input)
            
            # Generate thinking if enabled
            if self._config.thinking_enabled:
                thinking_tokens = []
                async for token in self.response_engine.generate_thinking_stream(user_input):
                    thinking_tokens.append(token)
                response.thinking = "".join(thinking_tokens)
            
            # Parse LLM response
            brain_response = await self.qwen3_brain.generate_complete(user_input)
            
            if brain_response.success:
                # Check if tool call needed
                if brain_response.content.startswith("{") and brain_response.content.endswith("}"):
                    try:
                        tool_data = json.loads(brain_response.content)
                        tool_name = tool_data.get("tool", "")
                        params = tool_data.get("params", {})
                        llm_response = tool_data.get("response", "")
                        
                        if tool_name:
                            # Execute tool
                            tool_result = await self.execution_engine.execute_from_llm(
                                user_input,
                                {"tool": tool_name, "params": params, "response": llm_response}
                            )
                            
                            response.tool_used = tool_name
                            response.verified = tool_result.verified
                            response.success = tool_result.success
                            
                            if tool_result.success:
                                response.response = llm_response or f"Executed {tool_name}"
                            else:
                                response.response = f"Failed to execute {tool_name}: {tool_result.error}"
                        else:
                            response.response = llm_response
                    except json.JSONDecodeError:
                        response.response = brain_response.content
                else:
                    response.response = brain_response.content
            else:
                response.response = "I'm having trouble processing that right now."
                response.success = False
            
            # Generate final response
            if response.response:
                final_response = await self.response_engine.generate_response(
                    user_input,
                    response.tool_used if response.tool_used else None,
                    response.response
                )
                response.response = final_response.content
            
            # Speak if enabled
            if self._config.speech_enabled and response.response:
                await self.speech_engine.speak_async(response.response)
            
            response.processing_time = time.time() - start_time
            response.metadata = {
                "provider": brain_response.provider if brain_response.success else "",
                "model": brain_response.model if brain_response.success else "",
                "latency_ms": brain_response.latency_ms if brain_response.success else 0
            }
            
            # Add to conversation history
            self.memory_engine.add_conversation_entry(
                role="user",
                content=user_input,
                tool=response.tool_used
            )
            self.memory_engine.add_conversation_entry(
                role="assistant",
                content=response.response,
                tool=response.tool_used
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling input: {e}")
            response.response = f"Something went wrong: {str(e)}"
            response.success = False
            response.processing_time = time.time() - start_time
            return response
    
    async def handle_stream(self, user_input: str) -> AsyncGenerator[str, None]:
        """Handle user input with streaming response."""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Stream thinking
            if self._config.thinking_enabled:
                async for token in self.response_engine.generate_thinking_stream(user_input):
                    yield token
            
            # Stream response
            async for token in self.response_engine.generate_response_stream(user_input):
                yield token
                
        except Exception as e:
            logger.error(f"Error in streaming response: {e}")
            yield f"Error: {str(e)}"
    
    async def self_command(self, command: str) -> str:
        """Handle self-improvement commands."""
        command = command.lower().strip()
        
        if command == "audit yourself":
            return await self.self_improvement.audit_yourself()
        elif command == "repair yourself":
            return await self.self_improvement.repair_yourself()
        elif command == "benchmark yourself":
            return await self.self_improvement.benchmark_yourself()
        elif command == "show weak points":
            return self.self_improvement.show_weak_points()
        elif command == "run diagnostics":
            return await self.self_improvement.run_diagnostics()
        elif command == "test tools":
            return await self.self_improvement.test_tools()
        elif command == "test memory":
            return await self.self_improvement.test_memory()
        elif command == "test speech":
            return await self.self_improvement.test_speech()
        elif command == "test vision":
            return await self.self_improvement.test_vision()
        elif command == "run all tests":
            return await self.self_improvement.run_all_tests()
        elif command == "optimize yourself":
            return await self.self_improvement.optimize_yourself()
        else:
            return f"Unknown self-command: {command}"
    
    def enable_debug(self) -> None:
        """Enable debug mode."""
        self._config.debug_mode = True
        self.execution_engine.enable_debug()
        logger.info("Debug mode enabled")
    
    def disable_debug(self) -> None:
        """Disable debug mode."""
        self._config.debug_mode = False
        self.execution_engine.disable_debug()
        logger.info("Debug mode disabled")
    
    def enable_speech(self) -> None:
        """Enable speech output."""
        self._config.speech_enabled = True
        logger.info("Speech enabled")
    
    def disable_speech(self) -> None:
        """Disable speech output."""
        self._config.speech_enabled = False
        logger.info("Speech disabled")
    
    def enable_thinking(self) -> None:
        """Enable thinking mode."""
        self._config.thinking_enabled = True
        self.qwen3_brain.enable_thinking_mode()
        logger.info("Thinking mode enabled")
    
    def disable_thinking(self) -> None:
        """Disable thinking mode."""
        self._config.thinking_enabled = False
        self.qwen3_brain.disable_thinking_mode()
        logger.info("Thinking mode disabled")
    
    def enable_streaming(self) -> None:
        """Enable streaming mode."""
        self._config.streaming_enabled = True
        self.qwen3_brain.enable_stream_mode()
        logger.info("Streaming enabled")
    
    def disable_streaming(self) -> None:
        """Disable streaming mode."""
        self._config.streaming_enabled = False
        self.qwen3_brain.disable_stream_mode()
        logger.info("Streaming disabled")
    
    def set_language(self, language: str) -> None:
        """Set language preference."""
        self._config.language = language
        self.response_engine.set_language(language)
        logger.info(f"Language set to {language}")
    
    def set_personality(self, personality: str) -> None:
        """Set personality preference."""
        self._config.personality = personality
        self.response_engine.reload_personality()
        logger.info(f"Personality set to {personality}")
    
    async def shutdown(self) -> None:
        """Shutdown JARVIS system."""
        self._running = False
        
        # Cleanup resources
        try:
            if hasattr(self, 'web_automation'):
                await self.web_automation.close_browser()
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
        
        logger.info("JARVIS shutdown complete")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current system status."""
        return {
            "initialized": self._initialized,
            "running": self._running,
            "debug_mode": self._config.debug_mode,
            "speech_enabled": self._config.speech_enabled,
            "thinking_enabled": self._config.thinking_enabled,
            "streaming_enabled": self._config.streaming_enabled,
            "language": self._config.language,
            "personality": self._config.personality,
            "verification_enabled": self._config.verification_enabled
        }


# Global JARVIS instance
_jarvis_instance: Optional[JARVISCore] = None


def get_jarvis(config: JARVISConfig = None) -> JARVISCore:
    """Get or create JARVIS instance."""
    global _jarvis_instance
    if _jarvis_instance is None:
        _jarvis_instance = JARVISCore(config)
    return _jarvis_instance