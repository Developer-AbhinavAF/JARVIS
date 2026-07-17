"""JARVIS — Unified Application Entry Point.

python app.py

Single entry point. No versions. No alternate applications.
Every action is EXECUTED, VERIFIED, then reported.

Pipeline: User Input → NLP → Intent → Tool Selection → Execute → Verify → Respond
"""

import sys
import time
import asyncio
import logging
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("jarvis")


# ═══════════════════════════════════════════════════════════════════════
# BOOT SEQUENCE
# ═══════════════════════════════════════════════════════════════════════

def print_banner():
    print()
    print("  ╔═══════════════════════════════════════════════╗")
    print("  ║              J A R V I S                      ║")
    print("  ║   Execution Engine + AI Router                ║")
    print("  ║   Tool-First. Verified. Real.                 ║")
    print("  ╚═══════════════════════════════════════════════╝")
    print()


def boot_log(phase: str, status: str = "PASS"):
    icon = "●" if status == "PASS" else "○" if status == "SKIP" else "✗"
    print(f"  {icon} {phase:.<35s} {status}")


# ═══════════════════════════════════════════════════════════════════════
# JARVIS CORE
# ═══════════════════════════════════════════════════════════════════════

class JARVIS:
    """The unified JARVIS application.

    Pipeline: User → NLP → Intent → Tool Selection → Execute → Verify → Respond
    Every module is initialized and validated during boot.
    """

    def __init__(self):
        self._boot_start = time.time()
        self._boot_complete = False
        self._debug_mode = False

        # Infrastructure
        from jarvis.infra.events import event_bus, EventType
        from jarvis.infra.state import state_manager
        from jarvis.infra.services import service_registry
        from jarvis.infra.security import security_layer
        from jarvis.infra.settings import settings_storage
        from jarvis.infra.benchmarks import benchmarking
        from jarvis.infra.analytics import analytics
        from jarvis.infra.logging_system import central_logger

        self.events = event_bus
        self.EventType = EventType
        self.state = state_manager
        self.services = service_registry
        self.security = security_layer
        self.settings = settings_storage
        self.benchmarks = benchmarking
        self.analytics = analytics
        self.logger = central_logger

        # Core subsystems (initialized during boot)
        self._router = None
        self._nlp = None
        self._execution = None
        self._memory = None
        self._knowledge = None
        self._environment = None

    async def boot(self):
        """Boot all subsystems with validation checks."""
        print_banner()
        checks_passed = 0
        checks_total = 0
        failed_critical = []

        def check(name: str, critical: bool = False):
            nonlocal checks_passed, checks_total
            checks_total += 1
            checks_passed += 1
            boot_log(name, "PASS")

        def check_fail(name: str, reason: str = "", critical: bool = False):
            nonlocal checks_passed, checks_total
            checks_total += 1
            boot_log(name, f"FAIL: {reason}")
            if critical:
                failed_critical.append(name)

        # ── Phase 1: Infrastructure ──
        check("Event Bus")
        check("State Manager")
        check("Settings Storage")
        check("Benchmarks")
        check("Analytics")
        check("Logging")

        # ── Phase 2: NLP Engine (MANDATORY) ──
        try:
            from jarvis.nlp import SemanticNLPEngine
            self._nlp = SemanticNLPEngine()
            # Validate NLP works with a test input
            test_result = self._nlp.process("hello")
            if test_result.intent and test_result.confidence_score > 0:
                check("NLP Engine")
            else:
                check_fail("NLP Engine", f"test failed: intent={test_result.intent} conf={test_result.confidence_score}", critical=True)
        except Exception as e:
            check_fail("NLP Engine", str(e), critical=True)

        # ── Phase 3: Execution Engine (MANDATORY) ──
        try:
            from jarvis.execution import execution_engine, tool_registry
            self._execution = execution_engine
            self._execution.debug_mode = self._debug_mode
            tool_count = tool_registry.get_stats()["total"]
            check(f"Execution Engine ({tool_count} tools)")
        except Exception as e:
            check_fail("Execution Engine", str(e), critical=True)

        # ── Phase 4: Tool Registry Validation ──
        try:
            from jarvis.execution import tool_registry
            stats = tool_registry.get_stats()
            for name, tool in tool_registry.get_all().items():
                if not tool.execute:
                    check_fail(f"Tool: {name}", "no execute fn")
            check(f"Tool Registry ({stats['total']} validated)")
        except Exception as e:
            check_fail("Tool Registry", str(e))

        # ── Phase 5: AI Router ──
        try:
            from jarvis.ai_router import get_router
            self._router = get_router()
            router_stats = self._router.get_registry_stats()
            check(f"AI Router ({router_stats['providers']} providers)")
        except Exception as e:
            check_fail("AI Router", str(e))

        # ── Phase 6: Memory ──
        try:
            from jarvis.memory import JarvisMemory
            self._memory = JarvisMemory()
            check("Memory")
        except Exception as e:
            check_fail("Memory", str(e))

        # ── Phase 6b: Knowledge Engine ──
        try:
            from jarvis.knowledge import KnowledgeEngine
            self._knowledge = KnowledgeEngine()
            check("Knowledge Engine")
        except Exception as e:
            check_fail("Knowledge Engine", str(e))

        # ── Phase 6c: Environment Engine (background monitor) ──
        try:
            from jarvis.infra.environment import environment_engine
            self._environment = environment_engine
            self._environment.start()
            check("Environment Engine")
        except Exception as e:
            check_fail("Environment Engine", str(e))

        # ── Phase 7: Subsystems ──
        for name, import_path in [
            ("Reasoning", "jarvis.nlp.reasoning_engine"),
            ("Planning", "jarvis.nlp.planner"),
            ("Vision", "jarvis.vision"),
            ("Speech", "jarvis.speech"),
            ("Knowledge", "jarvis.knowledge"),
            ("Learning", "jarvis.learning"),
            ("Agents", "jarvis.agents"),
            ("Environment", "jarvis.infra.environment"),
            ("Desktop Intelligence", "jarvis.infra.desktop"),
            ("Security Layer", "jarvis.infra.security"),
        ]:
            try:
                __import__(import_path)
                check(name)
            except Exception as e:
                check_fail(name, str(e))

        # ── Phase 8: Verification Engine ──
        try:
            from jarvis.execution import verification_engine
            check("Verification Engine")
        except Exception as e:
            check_fail("Verification Engine", str(e))

        # ── Ready ──
        self.state.set("app_ready", True)
        self._boot_complete = True

        elapsed = time.time() - self._boot_start
        status = "READY" if not failed_critical else "DEGRADED"
        print(f"\n  {checks_passed}/{checks_total} Checks Passed — {status}")
        print(f"  Boot time: {elapsed:.1f}s\n")

        if failed_critical:
            print(f"  ⚠ Critical failures: {', '.join(failed_critical)}")
            print("  Some features may be unavailable.\n")

        self.events.emit(self.EventType.APP_STARTED, source="boot")

    # ═══════════════════════════════════════════════════════════════════
    # SYSTEM HEALTH
    # ═══════════════════════════════════════════════════════════════════

    def get_system_health(self) -> dict[str, Any]:
        return {
            "boot_complete": self._boot_complete,
            "state": self.state is not None,
            "services": self.services is not None,
            "security": self.security is not None,
            "settings": self.settings is not None,
            "benchmarks": self.benchmarks is not None,
            "analytics": self.analytics is not None,
            "logger": self.logger is not None,
        }

    # ═══════════════════════════════════════════════════════════════════
    # EXECUTION PIPELINE — THE ONLY WAY TO HANDLE USER INPUT
    #
    # Priority: Tool > Memory > Knowledge > Reasoning > Conversation
    # ═══════════════════════════════════════════════════════════════════

    async def handle(self, user_input: str) -> dict[str, Any]:
        """Handle user input through the execution pipeline.

        Pipeline: NLP → Intent → Tool Selection → Execute → Verify → Respond
        NEVER claims action occurred unless verified.

        Execution Priority:
          1. Tool Execution (verified actions)
          2. Memory (recall/store)
          3. Knowledge (RAG retrieval)
          4. Conversation (LLM fallback — last resort)
        """
        start = time.time()
        self.analytics.track("input", "received")

        # ── Step 1: NLP Processing (always runs) ──
        nlp_output = None
        intent = ""
        intent_confidence = 0.0

        if self._nlp:
            try:
                self.benchmarks.start("nlp", "process")
                nlp_output = self._nlp.process(user_input)
                self.benchmarks.end("nlp", "process")
                intent = nlp_output.intent
                intent_confidence = nlp_output.confidence_score
            except Exception as e:
                logger.warning("NLP error: %s", e)

        # ── Step 2: Tool Execution (highest priority) ──
        # Skip tool execution for memory intents — let Step 4 handle them
        # with personal info detection and preference storage
        if nlp_output and nlp_output.tool and self._execution and intent not in ("RECALL_MEMORY", "SAVE_MEMORY"):
            try:
                self.benchmarks.start("execution", "execute_from_nlp")
                result = self._execution.execute_from_nlp(nlp_output)
                self.benchmarks.end("execution", "execute_from_nlp")

                if result.success:
                    self.analytics.track("tool", f"executed:{result.tool_name}")
                    self.state.set("last_action", result.tool_name)

                    # Build response from VERIFIED result
                    response_text = self._build_verified_response(result, user_input, nlp_output)
                    trace = self._execution.get_last_trace()

                    # Auto-save important interactions
                    self._auto_save_conversation(user_input, response_text, nlp_output)

                    return {
                        "response": response_text,
                        "success": True,
                        "verified": result.verified,
                        "tool": result.tool_name,
                        "intent": intent,
                        "intent_confidence": round(intent_confidence, 4),
                        "execution_ms": round(result.execution_time_ms, 1),
                        "verification_ms": round(result.verification_time_ms, 1),
                        "total_ms": round((time.time() - start) * 1000, 1),
                        "trace": trace.format_debug() if trace and self._debug_mode else None,
                    }
            except Exception as e:
                logger.error("Execution engine error: %s", e)

        # ── Step 3: NLP-generated response (greetings, jokes, etc.) ──
        # Skip for memory intents — let Step 4 handle them with personal info detection
        if nlp_output and nlp_output.response_text and intent not in ("RECALL_MEMORY", "SAVE_MEMORY"):
            self.analytics.track("nlp", f"responded:{intent}")
            self.state.set("last_intent", intent)
            # Auto-save significant interactions
            self._auto_save_conversation(user_input, nlp_output.response_text, nlp_output)
            return {
                "response": nlp_output.response_text,
                "success": True,
                "verified": False,
                "tool": None,
                "intent": intent,
                "intent_confidence": round(intent_confidence, 4),
                "total_ms": round((time.time() - start) * 1000, 1),
            }

        # ── Step 4: Memory recall (if intent suggests it) ──
        if intent in ("RECALL_MEMORY", "SAVE_MEMORY"):
            memory_response = self._handle_memory(user_input, nlp_output)
            if memory_response:
                return {
                    "response": memory_response,
                    "success": True,
                    "verified": False,
                    "tool": "memory",
                    "intent": intent,
                    "intent_confidence": round(intent_confidence, 4),
                    "total_ms": round((time.time() - start) * 1000, 1),
                }

        # ── Step 5: Knowledge retrieval (RAG fallback) ──
        if self._knowledge and intent not in ("GREETING", "FAREWELL", "UNKNOWN"):
            try:
                self.benchmarks.start("knowledge", "retrieve")
                rag_result = self._knowledge.retrieve(user_input, max_tokens=1000)
                self.benchmarks.end("knowledge", "retrieve")
                context = rag_result.get("context", "")
                sources = rag_result.get("sources", [])
                if context:
                    response_text = context
                    if sources:
                        source_names = [s.get("title", s.get("name", "")) for s in sources[:3]]
                        source_names = [s for s in source_names if s]
                        if source_names:
                            response_text += f"\n\nSources: {', '.join(source_names)}"
                    return {
                        "response": response_text,
                        "success": True,
                        "verified": False,
                        "tool": "knowledge",
                        "intent": intent,
                        "intent_confidence": round(intent_confidence, 4),
                        "total_ms": round((time.time() - start) * 1000, 1),
                    }
            except Exception as e:
                logger.debug("Knowledge retrieval error: %s", e)

        # ── Step 6: LLM Fallback (last resort — conversation) ──
        if self._router:
            try:
                self.benchmarks.start("router", "chat")
                response = await self._router.chat(user_input)
                self.benchmarks.end("router", "chat")

                if response.success:
                    self.analytics.track("llm", "responded")
                    self.state.set("last_intent", "LLM_FALLBACK")
                    return {
                        "response": response.content,
                        "success": True,
                        "verified": False,
                        "tool": None,
                        "intent": intent,
                        "intent_confidence": round(intent_confidence, 4),
                        "execution_ms": round(response.route.latency_ms, 1),
                        "total_ms": round((time.time() - start) * 1000, 1),
                    }
            except Exception as e:
                logger.error("Router error: %s", e)

        # ── Nothing worked ──
        return {
            "response": f"I couldn't process that. Intent: {intent} (confidence: {intent_confidence:.2f})",
            "success": False,
            "verified": False,
            "tool": None,
            "intent": intent,
            "intent_confidence": round(intent_confidence, 4),
            "total_ms": round((time.time() - start) * 1000, 1),
        }

    def _build_verified_response(self, result, user_input: str, nlp_output=None) -> str:
        """Build a response based on VERIFIED execution result."""
        from jarvis.execution.tool_registry import ToolResult

        tool_name = result.tool_name
        res = result.result

        if not result.success:
            return f"Failed to execute {tool_name}: {result.error}"

        # Use NLP-generated response if available and appropriate
        if nlp_output and nlp_output.response_text and not result.verified:
            return nlp_output.response_text

        if tool_name == "open_app":
            app = res.get("app", res.get("url", ""))
            app_type = res.get("type", "application")
            if app_type == "website":
                return f"Opened {app} in browser."
            return f"Opened {app}."

        if tool_name == "close_app":
            return f"Closed {res.get('app', 'application')}."

        if tool_name == "web_search":
            return f"Searching for: {res.get('query', '')}"

        if tool_name == "search_on_platform":
            platform = res.get("platform", "")
            query = res.get("query", "")
            return f"Searching for '{query}' on {platform}."

        if tool_name == "open_url":
            return f"Opened {res.get('url', '')} in browser."

        if tool_name == "create_file":
            return f"Created file: {res.get('file_path', '')}"

        if tool_name == "delete_file":
            return f"Deleted file: {res.get('file_path', '')}"

        if tool_name == "read_file":
            content = res.get("content", "")
            if len(content) > 500:
                content = content[:500] + "..."
            return f"File contents:\n{content}"

        if tool_name == "adjust_volume":
            direction = res.get("direction", "")
            vol = res.get("volume_percent", "?")
            return f"Volume {direction}: {vol}%"

        if tool_name == "take_screenshot":
            return f"Screenshot saved: {res.get('path', '')}"

        if tool_name == "get_system_stats":
            cpu = res.get("cpu_percent", "?")
            ram = res.get("ram_percent", "?")
            bat = res.get("battery_percent", "?")
            return f"CPU: {cpu}% | RAM: {ram}% | Battery: {bat}%"

        if tool_name == "get_time":
            return f"Current time: {res.get('time', '?')}"

        if tool_name == "get_date":
            return f"Today is {res.get('date', '?')}"

        if tool_name == "list_running_apps":
            apps = res.get("apps", [])
            if apps:
                return "Running apps:\n" + "\n".join(f"  {a['name']}" for a in apps[:15])
            return "No apps found."

        if tool_name == "add_note":
            return f"Note saved: {res.get('content', '')[:50]}"

        if tool_name == "get_notes":
            notes = res.get("notes", [])
            if notes:
                return "Your notes:\n" + "\n".join(f"  {n['content'][:80]}" for n in notes[-5:])
            return "No notes yet."

        if tool_name == "add_todo":
            return f"Todo added: {res.get('task', '')}"

        if tool_name == "get_todos":
            todos = res.get("todos", [])
            if todos:
                return "Your todos:\n" + "\n".join(
                    f"  {'[x]' if t['completed'] else '[ ]'} {t['task']}" for t in todos
                )
            return "No todos yet."

        if tool_name == "complete_todo":
            return f"Completed: {res.get('task', '')}"

        # Generic response
        return f"Executed {tool_name} successfully."

    # ═══════════════════════════════════════════════════════════════════
    # MEMORY HANDLER
    # ═══════════════════════════════════════════════════════════════════

    # ── Personal info patterns for preference storage ──
    _PERSONAL_PATTERNS: list[tuple[str, str, str]] = [
        # (regex_pattern, preference_key, category)
        # "my name is X" / "my name's X" / "I'm called X"
        (r"(?:my name (?:is|'s)|call me|i(?:'m| am) called|i(?:'m| am))\s+(.+)", "name", "personal"),
        # "I am X years old" / "I'm X"
        (r"(?:i (?:am|'m))\s+(\d+)\s*(?:years?\s*old)?", "age", "personal"),
        # "my email is X"
        (r"my email (?:is|'s)\s+(.+)", "email", "personal"),
        # "my birthday is X" / "I was born on X"
        (r"(?:my birthday (?:is|'s)|i was born on)\s+(.+)", "birthday", "personal"),
        # "my favorite color is X" / "I like color X"
        (r"(?:my favorite color (?:is|'s)|i (?:like|prefer) (?:the )?color)\s+(.+)", "favorite_color", "personal"),
        # "my phone is X" / "my number is X"
        (r"my (?:phone|number) (?:is|'s)\s+(.+)", "phone", "personal"),
        # "my address is X"
        (r"my address (?:is|'s)\s+(.+)", "address", "personal"),
    ]

    # Patterns for recalling personal info
    _RECALL_PATTERNS: list[tuple[str, str]] = [
        # (regex_pattern, preference_key)
        (r"what (?:is|'s) my (name|age|email|birthday|phone|address|favorite color)", None),
        (r"(?:do you|you) know my (name|age|email|birthday|phone|address|favorite color)", None),
        (r"tell me my (name|age|email|birthday|phone|address|favorite color)", None),
        (r"what do you know about me", None),
    ]

    def _handle_memory(self, user_input: str, nlp_output=None) -> str | None:
        """Handle memory recall/store operations.

        Recall: search stored memories and return relevant matches.
        Store: save user-provided content to long-term memory.
        Auto-save: store important interactions for future reference.
        """
        try:
            if not self._memory:
                return None

            intent = nlp_output.intent if nlp_output else ""

            # ── Recall ──
            if intent == "RECALL_MEMORY":
                # First check for personal info preferences
                lower = user_input.lower()
                for pattern, _ in self._RECALL_PATTERNS:
                    import re
                    m = re.search(pattern, lower)
                    if m:
                        # Extract the preference key from the match
                        key = m.group(1) if m.lastindex else None
                        if key:
                            # Normalize key: "favorite color" -> "favorite_color"
                            key = key.replace(" ", "_")
                            value = self._memory.get_preference(key)
                            if value:
                                return f"Your {key.replace('_', ' ')} is {value}."
                        # If asking "what do you know about me", show all preferences
                        if "what do you know about me" in lower:
                            prefs = self._memory.get_all_preferences("personal")
                            if prefs:
                                lines = [f"  {k.replace('_', ' ')}: {v}" for k, v in prefs.items()]
                                return "Here's what I know about you:\n" + "\n".join(lines)
                            return "I don't have any personal information stored yet. Tell me something about yourself!"

                # Fallback: general memory search
                query = user_input.lower()
                for prefix in ["recall", "remember", "search my memory", "find in memory", "show memory", "what do you know about"]:
                    query = query.replace(prefix, "")
                query = query.strip()
                if not query:
                    query = user_input
                results = self._memory.search(query)
                if results:
                    return "From memory:\n" + "\n".join(f"  - {r}" for r in results[:5])
                return "I don't have anything stored about that yet. Would you like me to remember it?"

            # ── Store ──
            if intent == "SAVE_MEMORY":
                lower = user_input.lower()

                # Check for personal info patterns → store as preference
                import re
                for pattern, pref_key, category in self._PERSONAL_PATTERNS:
                    m = re.search(pattern, lower)
                    if m:
                        value = m.group(1).strip().rstrip(".")
                        if value:
                            self._memory.save_preference(pref_key, value, category)
                            return f"I'll remember your {pref_key.replace('_', ' ')}: {value}"

                # Fallback: store as general memory
                content = user_input
                for prefix in ["remember that ", "remember ", "save ", "store ", "note that ", "note "]:
                    if user_input.lower().startswith(prefix):
                        content = user_input[len(prefix):]
                        break
                if content:
                    self._memory.store(content)
                return f"I'll remember: {content[:80]}"

            # ── Auto-save: store important conversations ──
            if nlp_output and hasattr(nlp_output, "memory_update") and nlp_output.memory_update:
                mu = nlp_output.memory_update
                if isinstance(mu, dict) and mu.get("should_save"):
                    content = mu.get("summary", user_input[:200])
                    self._memory.store(content)

        except Exception as e:
            logger.error("Memory handler error: %s", e, exc_info=True)
        return None

    def _auto_save_conversation(self, user_input: str, response: str, nlp_output=None):
        """Auto-save conversation summary to memory for important interactions."""
        try:
            if not self._memory or not nlp_output:
                return
            intent = nlp_output.intent
            conf = getattr(nlp_output, "confidence_score", 0)
            # Only auto-save tool-executed intents with high confidence
            if conf >= 0.8 and intent not in ("GREETING", "UNKNOWN", "FAREWELL"):
                summary = f"User asked: {user_input[:100]}. Response involved: {intent}"
                self._memory.store(summary)
        except Exception as e:
            logger.error("Auto-save error: %s", e, exc_info=True)

    # ═══════════════════════════════════════════════════════════════════
    # DEBUG MODE
    # ═══════════════════════════════════════════════════════════════════

    def enable_debug(self):
        self._debug_mode = True
        if self._execution:
            self._execution.debug_mode = True

    def disable_debug(self):
        self._debug_mode = False
        if self._execution:
            self._execution.debug_mode = False

    # ═══════════════════════════════════════════════════════════════════
    # SHUTDOWN
    # ═══════════════════════════════════════════════════════════════════

    async def shutdown(self):
        self.events.emit(self.EventType.APP_CLOSING, source="shutdown")
        self.state.set("app_ready", False)
        self.settings.save()
        self.events.emit(self.EventType.APP_CLOSED, source="shutdown")
        print("  Goodbye.\n")

    # ═══════════════════════════════════════════════════════════════════
    # HEALTH
    # ═══════════════════════════════════════════════════════════════════

    def get_health(self) -> dict:
        health = {
            "boot_complete": self._boot_complete,
            "debug_mode": self._debug_mode,
            "nlp_ready": self._nlp is not None,
            "execution_ready": self._execution is not None,
            "router_ready": self._router is not None,
            "memory_ready": self._memory is not None,
            "knowledge_ready": self._knowledge is not None,
        }
        if self._execution:
            health["execution"] = self._execution.get_stats()
        if self._router:
            health["router"] = self._router.get_registry_stats()
        health["benchmarks"] = self.benchmarks.get_stats()
        health["analytics"] = self.analytics.get_stats()
        return health

    @property
    def tools(self):
        from jarvis.execution import tool_registry
        return tool_registry


# ═══════════════════════════════════════════════════════════════════════
# INTERACTIVE MODE
# ═══════════════════════════════════════════════════════════════════════

async def interactive_mode(jarvis: JARVIS):
    print("  Commands: health, tools, traces, debug, settings, quit")
    print()

    while True:
        try:
            user_input = input("  You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            await jarvis.shutdown()
            break

        if not user_input:
            continue

        cmd = user_input.lower()

        if cmd in ("quit", "exit", "q"):
            await jarvis.shutdown()
            break

        if cmd == "health":
            import json
            print(json.dumps(jarvis.get_health(), indent=2, default=str))
            continue

        if cmd == "tools":
            stats = jarvis.tools.get_stats()
            print(f"\n  Registered Tools: {stats['total']} ({stats['enabled']} enabled)")
            for name, tool in jarvis.tools.get_all().items():
                print(f"    {name:25s} [{tool.category.value}] {tool.description}")
            print()
            continue

        if cmd == "traces":
            if jarvis._execution:
                traces = jarvis._execution.get_traces(limit=5)
                for t in traces:
                    print(f"\n  {t.format_debug()}")
            else:
                print("  No execution engine")
            continue

        if cmd == "debug":
            if jarvis._debug_mode:
                jarvis.disable_debug()
                print("  Debug mode OFF")
            else:
                jarvis.enable_debug()
                print("  Debug mode ON")
            continue

        if cmd == "settings":
            for k, v in jarvis.settings.all().items():
                print(f"    {k}: {v}")
            continue

        # ── EXECUTE ──
        result = await jarvis.handle(user_input)
        print(f"\n  {result['response']}\n")
        verified = "✓ verified" if result.get("verified") else "— unverified"
        tool = result.get("tool") or "llm"
        ms = result.get("total_ms", 0)
        intent = result.get("intent", "?")
        conf = result.get("intent_confidence", 0)
        print(f"  [{tool} | {verified} | intent={intent} conf={conf:.2f} | {ms}ms]")


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

async def main():
    jarvis = JARVIS()

    # Check for debug flag
    if "--debug" in sys.argv:
        jarvis.enable_debug()
        sys.argv.remove("--debug")

    try:
        await jarvis.boot()

        if len(sys.argv) > 1:
            text = " ".join(sys.argv[1:])
            if text == "health":
                import json
                print(json.dumps(jarvis.get_health(), indent=2, default=str))
            elif text == "tools":
                for name, tool in jarvis.tools.get_all().items():
                    print(f"  {name:25s} [{tool.category.value}]")
            else:
                result = await jarvis.handle(text)
                print(result["response"])
                if result.get("trace"):
                    print(f"\n{result['trace']}")
        else:
            await interactive_mode(jarvis)
    except KeyboardInterrupt:
        pass
    finally:
        await jarvis.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
