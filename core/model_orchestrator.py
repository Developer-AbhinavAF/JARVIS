"""core/model_orchestrator.py — Multi-Model AI Orchestration for JARVIS vNext++.

This module implements intelligent model routing with:
- Groq as primary model with capability-based delegation
- Tag-based tool calling (<genImage>, <searchWeb>, etc.)
- Status effects for UI (thinking, generating, analyzing)
- Code fallback when tools unavailable
- Multi-provider key rotation
"""

from __future__ import annotations

import os
import re
import json
import time
import logging
import asyncio
from typing import Any, Dict, List, Optional, AsyncGenerator, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# STATUS EFFECTS FOR UI
# ═══════════════════════════════════════════════════════════════

class StatusEffect(Enum):
    """Status effects shown in UI during processing."""
    THINKING = "thinking"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    SEARCHING = "searching"
    EXECUTING = "executing"
    WAITING = "waiting"
    PROCESSING = "processing"
    VALIDATING = "validating"
    OPTIMIZING = "optimizing"
    LEARNING = "learning"


@dataclass
class StatusUpdate:
    """Real-time status update for UI."""
    effect: StatusEffect
    message: str
    progress: float = 0.0
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════
# TAG PARSING FOR DELEGATION
# ═══════════════════════════════════════════════════════════════

class DelegationTag(Enum):
    """Tags that Groq can emit to delegate tasks."""
    IMAGE_GEN = "genImage"
    WEB_SEARCH = "searchWeb"
    CODE_EXEC = "executeCode"
    MATH_CALC = "calculateMath"
    WEATHER = "getWeather"
    NASA_DATA = "getNASAData"
    MOVIE_INFO = "getMovieInfo"
    COUNTRY_INFO = "getCountryInfo"
    MAPS_LOCATION = "getLocation"
    SPEECH_OUT = "speakOutput"
    MEMORY_STORE = "storeMemory"
    MEMORY_RECALL = "recallMemory"
    FILE_CREATE = "createFile"
    FILE_READ = "readFile"
    APP_OPEN = "openApp"
    APP_CLOSE = "closeApp"


TAG_PATTERNS = {
    DelegationTag.IMAGE_GEN: re.compile(r'<genImage>(.*?)</genImage>', re.DOTALL | re.IGNORECASE),
    DelegationTag.WEB_SEARCH: re.compile(r'<searchWeb>(.*?)</searchWeb>', re.DOTALL | re.IGNORECASE),
    DelegationTag.CODE_EXEC: re.compile(r'<executeCode>(.*?)</executeCode>', re.DOTALL | re.IGNORECASE),
    DelegationTag.MATH_CALC: re.compile(r'<calculateMath>(.*?)</calculateMath>', re.DOTALL | re.IGNORECASE),
    DelegationTag.WEATHER: re.compile(r'<getWeather>(.*?)</getWeather>', re.DOTALL | re.IGNORECASE),
    DelegationTag.NASA_DATA: re.compile(r'<getNASAData>(.*?)</getNASAData>', re.DOTALL | re.IGNORECASE),
    DelegationTag.MOVIE_INFO: re.compile(r'<getMovieInfo>(.*?)</getMovieInfo>', re.DOTALL | re.IGNORECASE),
    DelegationTag.COUNTRY_INFO: re.compile(r'<getCountryInfo>(.*?)</getCountryInfo>', re.DOTALL | re.IGNORECASE),
    DelegationTag.MAPS_LOCATION: re.compile(r'<getLocation>(.*?)</getLocation>', re.DOTALL | re.IGNORECASE),
    DelegationTag.SPEECH_OUT: re.compile(r'<speakOutput>(.*?)</speakOutput>', re.DOTALL | re.IGNORECASE),
    DelegationTag.MEMORY_STORE: re.compile(r'<storeMemory>(.*?)</storeMemory>', re.DOTALL | re.IGNORECASE),
    DelegationTag.MEMORY_RECALL: re.compile(r'<recallMemory>(.*?)</recallMemory>', re.DOTALL | re.IGNORECASE),
    DelegationTag.FILE_CREATE: re.compile(r'<createFile>(.*?)</createFile>', re.DOTALL | re.DOTALL | re.IGNORECASE),
    DelegationTag.FILE_READ: re.compile(r'<readFile>(.*?)</readFile>', re.DOTALL | re.IGNORECASE),
    DelegationTag.APP_OPEN: re.compile(r'<openApp>(.*?)</openApp>', re.DOTALL | re.IGNORECASE),
    DelegationTag.APP_CLOSE: re.compile(r'<closeApp>(.*?)</closeApp>', re.DOTALL | re.IGNORECASE),
}


@dataclass
class DelegatedTask:
    """A task delegated to a specialized model/service."""
    tag: DelegationTag
    payload: str
    result: Optional[str] = None
    success: bool = False
    error: Optional[str] = None


# ═══════════════════════════════════════════════════════════════
# MODEL ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════

class ModelOrchestrator:
    """
    Intelligent model orchestrator that:
    1. Uses Groq as primary model
    2. Parses delegation tags from Groq response
    3. Routes specialized tasks to appropriate services
    4. Aggregates results and returns unified response
    """

    def __init__(self):
        self.groq_keys = self._load_api_keys('GROQ_API_KEY', 3)
        self.openrouter_keys = self._load_api_keys('OPENROUTER_API_KEY', 3)
        self.mistral_keys = self._load_api_keys('MISTRAL_API_KEY', 3)
        
        self.gemini_key = os.getenv('GEMINI_API_KEY', '')
        self.nvidia_key = os.getenv('NVIDIA_API_KEY', '')
        self.wolframalpha_appid = os.getenv('WOLFRAMALPHA_APPID', '')
        self.jina_key = os.getenv('JINA_API_KEY', '')
        self.openweathermap_key = os.getenv('OPENWEATHERMAP_API_KEY', '')
        self.nasa_key = os.getenv('NASA_API_KEY', '')
        
        # Model names
        self.groq_model = os.getenv('GROQ_MODEL_NAME', 'llama-3.3-70b-versatile')
        self.groq_vision_model = os.getenv('GROQ_VISION_MODEL', 'llama-3.2-90b-vision-preview')
        self.openrouter_model = os.getenv('OPENROUTER_DEFAULT_MODEL', 'meta-llama/llama-3-70b-instruct')
        self.mistral_model = os.getenv('MISTRAL_MODEL', 'mistral-large-latest')
        self.gemini_model = os.getenv('GEMINI_MODEL', 'gemini-1.5-pro')
        self.nvidia_model = os.getenv('NVIDIA_MODEL', 'nemotron-4-340b-instruct')
        
        # Key rotation state
        self.current_groq_key_idx = 0
        self.current_openrouter_key_idx = 0
        self.current_mistral_key_idx = 0
        
        # Status tracking
        self.status_callbacks: List[callable] = []
        
    def _load_api_keys(self, prefix: str, count: int = 3) -> List[str]:
        """Load multiple API keys from environment."""
        keys = []
        for i in range(1, count + 1):
            key = os.getenv(f'{prefix}_{i}', '')
            if key:
                keys.append(key)
        return keys if keys else ['']
    
    def _get_current_groq_key(self) -> str:
        """Get current Groq API key with rotation."""
        if not self.groq_keys:
            return ''
        return self.groq_keys[self.current_groq_key_idx % len(self.groq_keys)]
    
    def _rotate_groq_key(self):
        """Rotate to next Groq API key."""
        self.current_groq_key_idx += 1
        
    def register_status_callback(self, callback: callable):
        """Register callback for status updates."""
        self.status_callbacks.append(callback)
    
    async def _emit_status(self, effect: StatusEffect, message: str, progress: float = 0.0):
        """Emit status update to all callbacks."""
        update = StatusUpdate(effect=effect, message=message, progress=progress)
        for callback in self.status_callbacks:
            try:
                await callback(update)
            except Exception as e:
                logger.error(f"Status callback error: {e}")
    
    async def process_request(
        self,
        message: str,
        session_id: str = "default",
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Tuple[str, Optional[DelegatedTask]], None]:
        """
        Process user request through Groq with delegation support.
        
        Yields:
            Tuple of (response_chunk, delegated_task)
            - response_chunk: Text chunk for streaming
            - delegated_task: Task to delegate (None if none)
        """
        start_time = time.time()
        
        # Emit initial status
        await self._emit_status(StatusEffect.THINKING, "Analyzing request...", 0.1)
        
        try:
            # Step 1: Get Groq response
            groq_response = ""
            async for chunk in self._call_groq(message, context):
                groq_response += chunk
                yield (chunk, None)
            
            await self._emit_status(StatusEffect.ANALYZING, "Checking for delegations...", 0.5)
            
            # Step 2: Parse delegation tags
            delegated_tasks = self._parse_delegations(groq_response)
            
            if delegated_tasks:
                await self._emit_status(StatusEffect.EXECUTING, f"Executing {len(delegated_tasks)} task(s)...", 0.6)
                
                # Step 3: Execute delegated tasks
                for task in delegated_tasks:
                    yield ("", task)  # Signal delegation
                    await self._execute_delegation(task)
                
                await self._emit_status(StatusEffect.GENERATING, "Aggregating results...", 0.9)
                
                # Step 4: Clean response (remove tags)
                clean_response = self._clean_tags(groq_response)
                
                # Step 5: Append results if any
                results_text = self._format_delegation_results(delegated_tasks)
                if results_text:
                    yield (f"\n\n{results_text}", None)
            
            await self._emit_status(StatusEffect.THINKING, "Complete", 1.0)
            
        except Exception as e:
            logger.error(f"Orchestration error: {e}")
            await self._emit_status(StatusEffect.THINKING, f"Error: {str(e)}", 0.0)
            yield (f"\n\n[Error during processing: {str(e)}]", None)
    
    async def _call_groq(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """Call Groq API with streaming support."""
        # Implementation would use httpx or similar
        # This is a placeholder structure
        pass
    
    def _parse_delegations(self, text: str) -> List[DelegatedTask]:
        """Parse delegation tags from text."""
        tasks = []
        for tag, pattern in TAG_PATTERNS.items():
            matches = pattern.findall(text)
            for match in matches:
                tasks.append(DelegatedTask(tag=tag, payload=match.strip()))
        return tasks
    
    async def _execute_delegation(self, task: DelegatedTask):
        """Execute a delegated task."""
        try:
            if task.tag == DelegationTag.IMAGE_GEN:
                task.result = await self._generate_image(task.payload)
                task.success = True
            elif task.tag == DelegationTag.WEB_SEARCH:
                task.result = await self._web_search(task.payload)
                task.success = True
            elif task.tag == DelegationTag.MATH_CALC:
                task.result = await self._calculate_math(task.payload)
                task.success = True
            elif task.tag == DelegationTag.WEATHER:
                task.result = await self._get_weather(task.payload)
                task.success = True
            elif task.tag == DelegationTag.NASA_DATA:
                task.result = await self._get_nasa_data(task.payload)
                task.success = True
            elif task.tag == DelegationTag.CODE_EXEC:
                task.result = await self._execute_code(task.payload)
                task.success = True
            else:
                task.error = f"Unknown delegation tag: {task.tag}"
                task.success = False
        except Exception as e:
            task.error = str(e)
            task.success = False
    
    async def _generate_image(self, prompt: str) -> str:
        """Generate image using configured provider."""
        # Placeholder - would call actual image gen API
        return f"[Image generated for: {prompt[:50]}...]"
    
    async def _web_search(self, query: str) -> str:
        """Perform web search using Jina AI."""
        if not self.jina_key:
            return "[Web search unavailable - missing Jina API key]"
        
        # Use Jina AI Reader for search
        url = f"https://r.jina.ai/{query}"
        # Implementation would use httpx
        return f"[Search results for: {query[:50]}...]"
    
    async def _calculate_math(self, expression: str) -> str:
        """Calculate math expression using WolframAlpha."""
        if not self.wolframalpha_appid:
            # Fallback to Python eval for simple expressions
            try:
                result = eval(expression, {"__builtins__": {}}, {})
                return str(result)
            except:
                return "[Math calculation unavailable]"
        
        # Use WolframAlpha
        return f"[WolframAlpha result for: {expression}]"
    
    async def _get_weather(self, location: str) -> str:
        """Get weather from OpenWeatherMap."""
        if not self.openweathermap_key:
            return "[Weather unavailable - missing API key]"
        
        # Implementation would call OpenWeatherMap API
        return f"[Weather for {location}: Sunny, 25°C]"
    
    async def _get_nasa_data(self, query: str) -> str:
        """Get NASA data from API."""
        if not self.nasa_key:
            return "[NASA data unavailable - missing API key]"
        
        # Implementation would call NASA API
        return f"[NASA data for: {query}]"
    
    async def _execute_code(self, code: str) -> str:
        """Execute code safely."""
        # Would integrate with execution_first.py
        return f"[Code executed: {code[:50]}...]"
    
    def _clean_tags(self, text: str) -> str:
        """Remove all delegation tags from text."""
        for tag in DelegationTag:
            pattern = TAG_PATTERNS[tag]
            text = pattern.sub('', text)
        return text.strip()
    
    def _format_delegation_results(self, tasks: List[DelegatedTask]) -> str:
        """Format delegation results for display."""
        if not tasks:
            return ""
        
        results = []
        for task in tasks:
            if task.success:
                results.append(f"**{task.tag.value}**: {task.result}")
            else:
                results.append(f"**{task.tag.value}** (failed): {task.error}")
        
        return "\n".join(results)


# Singleton instance
model_orchestrator = ModelOrchestrator()
