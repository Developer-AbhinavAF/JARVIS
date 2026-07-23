"""startup — JARVIS startup screen with loading sequence.

Displays the JARVIS startup sequence with component loading status.
"""

from __future__ import annotations

import os
import sys
import time
import logging
import asyncio
from typing import Optional
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


class StartupScreen:
    """JARVIS startup screen with loading sequence."""
    
    def __init__(self):
        self.console = None  # Disable rich console to avoid encoding issues
        self.loading_steps = [
            "Loading FOOD...",
            "Loading Memories...",
            "Loading Knowledge...",
            "Loading Context Engine...",
            "Loading Planner...",
            "Loading Tool Chains...",
            "Loading Vision...",
            "Loading Speech...",
            "Loading Router...",
            "Loading Local AI...",
            "Loading Personality...",
            "Loading Tools...",
            "Loading Verification Engine...",
        ]
        self.component_status = {}
    
    def _print_simple(self, text: str) -> None:
        """Print without rich formatting."""
        print(text)
    
    def _print_rich(self, text: str, style: str = "cyan") -> None:
        """Print with rich formatting."""
        self._print_simple(text)
    
    def _print_header(self) -> None:
        """Print JARVIS header."""
        header = """
+--------------------------------------------------------------+
|                                                              |
|              J A R V I S  A I  O S                            |
|                                                              |
|         Human-Level AI Assistant System                       |
|                                                              |
+--------------------------------------------------------------+
"""
        self._print_simple(header)
    
    def _print_loading_step(self, step: str, status: str = "loading") -> None:
        """Print a loading step with status."""
        prefix = "[+]" if status == "done" else "[x]" if status == "error" else "[...]"
        self._print_simple(f"{prefix} {step}")
    
    async def load_component(self, component_name: str, load_func) -> bool:
        """Load a component with status display."""
        self._print_loading_step(f"Loading {component_name}...", "loading")
        
        try:
            start_time = time.time()
            result = await load_func()
            elapsed = time.time() - start_time
            
            if result:
                self._print_loading_step(f"Loading {component_name}... ({elapsed:.2f}s)", "done")
                self.component_status[component_name] = {"status": "success", "time": elapsed}
                return True
            else:
                self._print_loading_step(f"Loading {component_name}... failed", "error")
                self.component_status[component_name] = {"status": "failed", "time": elapsed}
                return False
        except Exception as e:
            self._print_loading_step(f"Loading {component_name}... error: {str(e)}", "error")
            self.component_status[component_name] = {"status": "error", "error": str(e)}
            return False
    
    async def load_food(self) -> bool:
        """Load FOOD system."""
        try:
            from pathlib import Path
            food_dir = Path(__file__).parent.parent / "food"
            if food_dir.exists():
                # Count markdown files
                md_files = list(food_dir.glob("*.md"))
                return len(md_files) > 0
            return False
        except Exception:
            return False
    
    async def load_memories(self) -> bool:
        """Load memory system."""
        try:
            from core.memory_engine import memory_engine
            # Memory engine is initialized on import
            return True
        except Exception:
            return False
    
    async def load_knowledge(self) -> bool:
        """Load knowledge engine."""
        try:
            from core.knowledge_engine import knowledge_engine
            return True
        except Exception:
            return False
    
    async def load_context_engine(self) -> bool:
        """Load context engine."""
        try:
            from core.context_engine import context_engine
            return True
        except Exception:
            return False
    
    async def load_planner(self) -> bool:
        """Load planner engine."""
        try:
            from core.planner_engine import planner_engine
            return True
        except Exception:
            return False
    
    async def load_tool_chains(self) -> bool:
        """Load tool chain engine."""
        try:
            from core.tool_chain_engine import tool_chain_engine
            return True
        except Exception:
            return False
    
    async def load_vision(self) -> bool:
        """Load vision engine."""
        try:
            from core.vision_engine import vision_engine
            return True
        except Exception:
            return False
    
    async def load_speech(self) -> bool:
        """Load speech engine."""
        try:
            from core.speech_engine import speech_engine
            return True
        except Exception:
            return False
    
    async def load_router(self) -> bool:
        """Load AI router."""
        try:
            from core.router import AIRouter
            router = AIRouter()
            return True
        except Exception:
            return False
    
    async def load_local_ai(self) -> bool:
        """Load local AI (QWEN3)."""
        try:
            from core.qwen3_brain import qwen3_brain
            return True
        except Exception:
            return False
    
    async def load_personality(self) -> bool:
        """Load personality settings."""
        try:
            from core.memory_engine import memory_engine
            personality = memory_engine._load_json(memory_engine._personality_file)
            return bool(personality)
        except Exception:
            return False
    
    async def load_tools(self) -> bool:
        """Load tools."""
        try:
            from core.tools import tool_registry
            tools = tool_registry.get_all()
            return len(tools) > 0
        except Exception:
            return False
    
    async def load_verification_engine(self) -> bool:
        """Load verification engine."""
        try:
            from core.execution import execution_engine
            return True
        except Exception:
            return False
    
    async def show_startup(self) -> Dict[str, Any]:
        """Show complete startup sequence."""
        start_time = time.time()
        
        # Clear screen
        os.system("cls" if os.name == "nt" else "clear")
        
        # Print header
        self._print_header()
        self._print_simple("")
        
        # Load components
        load_tasks = [
            ("FOOD", self.load_food),
            ("Memories", self.load_memories),
            ("Knowledge", self.load_knowledge),
            ("Context Engine", self.load_context_engine),
            ("Planner", self.load_planner),
            ("Tool Chains", self.load_tool_chains),
            ("Vision", self.load_vision),
            ("Speech", self.load_speech),
            ("Router", self.load_router),
            ("Local AI", self.load_local_ai),
            ("Personality", self.load_personality),
            ("Tools", self.load_tools),
            ("Verification Engine", self.load_verification_engine),
        ]
        
        for component_name, load_func in load_tasks:
            await self.load_component(component_name, load_func)
            await asyncio.sleep(0.1)  # Small delay for visual effect
        
        # Final status
        self._print_simple("")
        total_time = time.time() - start_time
        
        successful = sum(1 for status in self.component_status.values() if status.get("status") == "success")
        total = len(self.component_status)
        
        if successful == total:
            self._print_simple("JARVIS READY.")
            self._print_simple(f"All {total} components loaded successfully in {total_time:.2f}s")
        else:
            self._print_simple("JARVIS READY (with warnings).")
            self._print_simple(f"{successful}/{total} components loaded in {total_time:.2f}s")
        
        self._print_simple("")
        
        return {
            "success": successful == total,
            "total_components": total,
            "successful_components": successful,
            "loading_time": total_time,
            "component_status": self.component_status
        }
    
    def show_ready(self) -> None:
        """Show JARVIS ready message."""
        self._print_simple("JARVIS READY.")
        self._print_simple("")


async def run_startup() -> Dict[str, Any]:
    """Run the startup sequence."""
    startup = StartupScreen()
    return await startup.show_startup()


def show_startup_sync() -> Dict[str, Any]:
    """Run startup synchronously."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, run_startup())
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(run_startup())
    except RuntimeError:
        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(run_startup())


if __name__ == "__main__":
    result = show_startup_sync()
    print(f"\nStartup result: {result}")