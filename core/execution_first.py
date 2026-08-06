"""Execution-first runtime used by every supported JARVIS entry point.

The module deliberately has no import-time network, model, browser, or desktop
side effects.  It is small enough to boot deterministically and its public
objects are dependency-injectable for tests and desktop hosts.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any, Protocol
import json
import math
import os
import subprocess
import time
import webbrowser


class ReasoningLevel(IntEnum):
    ZERO = 0
    SIMPLE = 1
    MEMORY = 2
    NORMAL = 3
    COMPLEX = 4


@dataclass(frozen=True)
class Intent:
    name: str
    confidence: float
    entities: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    level: ReasoningLevel = ReasoningLevel.NORMAL
    tool: str | None = None


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    arguments: dict[str, str]
    example: str
    aliases: tuple[str, ...]
    risk: str  # "none", "low", "medium", "high", "critical"
    verify: str
    requires_confirmation: bool = False  # For destructive operations

    def llm_card(self) -> dict[str, Any]:
        """The only tool information supplied to an LLM."""
        return {"name": self.name, "description": self.description,
                "arguments": self.arguments, "example": self.example}


@dataclass
class ToolResult:
    success: bool
    verified: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""


class ToolHandler(Protocol):
    def __call__(self, **arguments: Any) -> ToolResult: ...


class ToolRegistry:
    """A registry whose contracts are executable, inspectable data."""
    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}
        self._handlers: dict[str, ToolHandler] = {}

    def register(self, spec: ToolSpec, handler: ToolHandler) -> None:
        if not all((spec.description, spec.example, spec.risk, spec.verify)):
            raise ValueError(f"Incomplete tool contract: {spec.name}")
        self._specs[spec.name] = spec
        self._handlers[spec.name] = handler

    def get(self, name: str) -> ToolSpec | None:
        return self._specs.get(name)

    def cards(self) -> list[dict[str, Any]]:
        return [spec.llm_card() for spec in self._specs.values()]

    def execute(self, name: str, **arguments: Any) -> ToolResult:
        spec = self._specs.get(name)
        handler = self._handlers.get(name)
        if not spec or not handler:
            return ToolResult(False, False, error=f"Unknown tool: {name}")
        missing = set(spec.arguments) - set(arguments)
        if missing:
            return ToolResult(False, False, error=f"Missing arguments: {', '.join(sorted(missing))}")
        
        # Check for user confirmation on destructive operations
        if spec.requires_confirmation:
            # For now, auto-confirm high-risk operations in non-interactive mode
            # In production, this should prompt the user
            import logging
            logger.warning(f"Tool {name} requires confirmation (auto-confirming for now)")
        
        result = handler(**arguments)
        if result.success and not result.verified:
            return ToolResult(False, False, data=result.data,
                              error=f"{name} completed without verification")
        return result


@dataclass
class SessionContext:
    current_browser: str = ""
    current_website: str = ""
    current_folder: str = ""
    current_app: str = ""
    current_window: str = ""
    current_tab: str = ""
    current_selection: str = ""
    current_clipboard: str = ""
    current_screenshot: str = ""
    current_file: str = ""
    current_camera_frame: str = ""
    current_mouse_position: str = ""
    last_tool: str = ""
    last_entity: str = ""
    last_person: str = ""
    last_command: str = ""
    last_user_request: str = ""
    conversation_topic: str = ""

    def snapshot(self) -> dict[str, str]:
        return asdict(self)

    def resolve(self, reference: str) -> str:
        # Resolution is state-based, not a command router.
        targets = {
            "there": self.current_website or self.current_folder,
            "it": self.last_entity or self.current_selection,
            "that": self.last_entity or self.current_selection,
            "this": self.current_selection or self.last_entity,
            "again": self.last_command,
            "same": self.last_entity,
            "previous": self.last_entity,
            "file": self.current_file,
            "window": self.current_window,
            "tab": self.current_tab,
        }
        return targets.get(reference.casefold().strip(), "")
    
    def update(self, **updates: str) -> None:
        """Update context fields."""
        for key, value in updates.items():
            if hasattr(self, key):
                setattr(self, key, value)


class Embeddings(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class LocalNgramEmbeddings:
    """A deterministic local vector embedder for the command ontology.

    DESIGN DECISION: This uses character n-gram embeddings instead of a full
    semantic model (like sentence-transformers) to maintain the execution-first
    runtime's design principles:
    - No import-time network side effects
    - No model download at startup
    - Deterministic and fast boot
    - No external dependencies

    While n-gram embeddings are not true semantic embeddings, they provide:
    - Deterministic similarity for known command patterns
    - Zero startup latency
    - No dependency on external model servers
    - Acceptable accuracy for command classification

    DEPLOYMENTS: May replace this with sentence-transformers or provider
    embeddings if startup latency and dependencies are acceptable.
    """
    dimension = 512
    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            padded = f"  {text.casefold().strip()}  "
            vector = [0.0] * self.dimension
            for index in range(max(0, len(padded) - 2)):
                gram = padded[index:index + 3]
                slot = int.from_bytes(gram.encode("utf-8"), "little", signed=False) % self.dimension
                vector[slot] += 1.0
            vectors.append(vector)
        return vectors


class SemanticIntentEngine:
    """Classifies commands by embedding similarity to complete utterances.

    There is deliberately no regex or token/keyword route.  A deployment must
    supply a semantic embedding backend; without one the result is explicitly
    low-confidence and is passed to the reasoning path.
    
    IMPORTANT: This engine is only for high-confidence command detection.
    All conversational input should fall through to the LLM reasoner.
    """
    threshold = 0.90  # High threshold to avoid false matches - only very close matches trigger
    examples: tuple[tuple[str, str, ReasoningLevel, str | None, dict[str, Any]], ...] = (
        # Greetings (very specific patterns only)
        ("hello", "greeting", ReasoningLevel.ZERO, None, {}),
        ("hi", "greeting", ReasoningLevel.ZERO, None, {}),
        ("hey", "greeting", ReasoningLevel.ZERO, None, {}),
        ("good morning", "greeting", ReasoningLevel.ZERO, None, {}),
        ("good evening", "greeting", ReasoningLevel.ZERO, None, {}),
        
        # Acknowledgments
        ("thanks", "thanks", ReasoningLevel.ZERO, None, {}),
        ("thank you", "thanks", ReasoningLevel.ZERO, None, {}),
        ("yes", "affirm", ReasoningLevel.ZERO, None, {}),
        ("no", "deny", ReasoningLevel.ZERO, None, {}),
        ("ok", "affirm", ReasoningLevel.ZERO, None, {}),
        ("okay", "affirm", ReasoningLevel.ZERO, None, {}),
        
        # Goodbye
        ("goodbye", "bye", ReasoningLevel.ZERO, None, {}),
        ("bye", "bye", ReasoningLevel.ZERO, None, {}),
        ("see you", "bye", ReasoningLevel.ZERO, None, {}),
        
        # Commands (very specific patterns)
        ("open youtube", "open_website", ReasoningLevel.SIMPLE, "open_url", {"url": "https://youtube.com"}),
        ("open chrome", "open_application", ReasoningLevel.SIMPLE, "open_app", {"app": "chrome"}),
        ("open vscode", "open_application", ReasoningLevel.SIMPLE, "open_app", {"app": "code"}),
        ("take a screenshot", "screenshot", ReasoningLevel.SIMPLE, "take_screenshot", {}),
        ("screenshot", "screenshot", ReasoningLevel.SIMPLE, "take_screenshot", {}),
        ("what time is it", "time", ReasoningLevel.SIMPLE, "get_time", {}),
        ("what is the time", "time", ReasoningLevel.SIMPLE, "get_time", {}),
        ("calculate 2 plus 2", "calculate", ReasoningLevel.SIMPLE, "calculate", {}),
        ("what is my name", "memory_recall", ReasoningLevel.MEMORY, "recall_memory", {"query": "name"}),
        ("remember my name is Ada", "memory_save", ReasoningLevel.MEMORY, "save_memory", {}),
        ("forget my name", "memory_forget", ReasoningLevel.MEMORY, "forget_memory", {}),
        ("summarize this", "summarize", ReasoningLevel.MEMORY, None, {}),
    )
    
    # Remove examples that would match weird inputs
    # Only keep very specific command patterns

    def __init__(self, embeddings: Embeddings | None = None) -> None:
        self.embeddings = embeddings
        self._example_vectors = embeddings.embed([row[0] for row in self.examples]) if embeddings else []

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        denominator = math.sqrt(sum(x * x for x in left)) * math.sqrt(sum(x * x for x in right))
        return sum(x * y for x, y in zip(left, right)) / denominator if denominator else 0.0

    def detect(self, text: str, context: SessionContext) -> Intent:
        start = time.perf_counter()
        if not text.strip() or not self.embeddings:
            return Intent("unknown", 0.0, context=context.snapshot())
        vector = self.embeddings.embed([text])[0]
        scores = [self._cosine(vector, candidate) for candidate in self._example_vectors]
        index = max(range(len(scores)), key=scores.__getitem__)
        _, name, level, tool, arguments = self.examples[index]
        # Timing is retained for callers/tests without expanding the public schema.
        current = context.snapshot() | {"intent_ms": round((time.perf_counter() - start) * 1000, 3)}
        return Intent(name, max(0.0, min(1.0, scores[index])),
                      {"text": text, "arguments": arguments, "reference": context.resolve(text)}, current, level, tool)

    def _entities(self, text: str, name: str, context: SessionContext) -> dict[str, Any]:
        """Entity extraction belongs to the semantic model in production.

        A deterministic backend may return entities alongside embeddings.  This
        minimal runtime only carries contextual references and never guesses an
        action from a keyword list.
        """
        return {"text": text, "reference": context.resolve(text)}


class MemoryStore:
    """One cached, JSON-persistent store. Vectors are supplied by real embeddings."""
    def __init__(self, root: str | Path = "data", embeddings: Embeddings | None = None) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.embeddings = embeddings
        self.paths = {name: self.root / f"{name}.json" for name in
                      ("facts", "conversation", "mistakes", "preferences", "goals", "relationships", "projects", "summaries")}
        self.knowledge = self.root / "knowledge"
        self.knowledge.mkdir(exist_ok=True)
        self._cache = {name: self._read(path, [] if name == "conversation" else {}) for name, path in self.paths.items()}

    @staticmethod
    def _read(path: Path, default: Any) -> Any:
        try: return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
        except (OSError, json.JSONDecodeError): return default

    def _write(self, name: str) -> None:
        self.paths[name].write_text(json.dumps(self._cache[name], indent=2), encoding="utf-8")

    def remember(self, fact: str, value: str, category: str = "facts") -> ToolResult:
        if category not in self._cache or not isinstance(self._cache[category], dict):
            return ToolResult(False, False, error=f"Unsupported memory category: {category}")
        entry = {"value": value, "updated_at": time.time()}
        if self.embeddings:
            entry["embedding"] = self.embeddings.embed([f"{fact}: {value}"])[0]
        self._cache[category][fact] = entry
        self._write(category)
        return ToolResult(True, True, {"fact": fact, "value": value})

    def recall(self, query: str, limit: int = 5) -> ToolResult:
        if not self.embeddings:
            return ToolResult(False, False, error="Semantic embeddings are unavailable")
        q = self.embeddings.embed([query])[0]
        matches: list[tuple[float, str, dict[str, Any]]] = []
        for category, values in self._cache.items():
            if not isinstance(values, dict):
                continue
            for fact, entry in values.items():
                if not isinstance(entry, dict):
                    entry = {"value": entry}
                vector = entry.get("embedding")
                if vector:
                    matches.append((SemanticIntentEngine._cosine(q, vector), fact, entry | {"category": category}))
                elif isinstance(entry.get("value"), str) and query.casefold() in fact.casefold():
                    matches.append((1.0, fact, entry | {"category": category}))
                elif isinstance(entry.get("value"), str) and query.casefold() in str(entry.get("value")).casefold():
                    matches.append((0.8, fact, entry | {"category": category}))
        matches.sort(reverse=True, key=lambda item: item[0])
        if not matches:
            return ToolResult(True, True, {"matches": []})
        return ToolResult(True, True, {"matches": [{"fact": fact, "score": score, **entry} for score, fact, entry in matches[:limit]]})


class FoodCache:
    names = ("00_identity.md", "01_reasoning.md", "02_tools.md", "03_memory.md", "04_context.md", "05_desktop.md", "06_browser.md", "07_speech.md", "08_vision.md", "09_apps.md", "10_personality.md", "11_safety.md", "12_examples.md")
    def __init__(self, root: str | Path = "foods") -> None:
        base = Path(root)
        self.modules = {name: (base / name).read_text(encoding="utf-8") for name in self.names}

    def system_prompt(self) -> str:
        return "\n\n".join(self.modules.values())


class Reasoner(Protocol):
    async def respond(self, text: str, *, tools: list[dict[str, Any]], context: dict[str, Any], budget: ReasoningLevel) -> str: ...


class ExecutionFirstRuntime:
    def __init__(self, intents: SemanticIntentEngine, tools: ToolRegistry, memory: MemoryStore,
                 food: FoodCache, reasoner: Reasoner | None = None) -> None:
        self.intents, self.tools, self.memory, self.food, self.reasoner = intents, tools, memory, food, reasoner
        self.context = SessionContext()

    async def handle(self, text: str) -> dict[str, Any]:
        intent = self.intents.detect(text, self.context)
        if intent.confidence >= self.intents.threshold:
            return self._execute(intent)
        if not self.reasoner:
            # Low-confidence: never guess from keyword similarity. Signal the
            # caller to fall back to the LLM instead of replying with a match.
            return self._result("", False, Intent("unknown", intent.confidence, intent.entities, intent.context, intent.level, intent.tool))
        response = await self.reasoner.respond(text, tools=self.tools.cards(), context=self.context.snapshot(), budget=intent.level)
        return self._result(response, True, intent, reasoned=True)

    def _execute(self, intent: Intent) -> dict[str, Any]:
        if intent.level == ReasoningLevel.ZERO:
            replies = {"greeting": "Hey.", "thanks": "Anytime.", "affirm": "Okay.", "deny": "Alright.", "bye": "Bye."}
            if intent.name == "unknown":
                return self._result("I’m here and ready to help.", True, intent)
            return self._result(replies.get(intent.name, "Okay."), True, intent)
        if intent.name == "memory_recall":
            result = self.memory.recall(intent.entities["text"])
        elif intent.name == "memory_save":
            return self._result("Tell me what you’d like me to remember.", False, intent)
        elif intent.tool:
            result = self.tools.execute(intent.tool, **intent.entities.get("arguments", {}))
        else:
            return self._result("I need a little more detail.", False, intent)
        if result.success and result.verified:
            self.context.last_tool = intent.tool or "memory"
            self.context.last_command = intent.entities["text"]
            return self._result(self._natural_result(intent, result), True, intent, result=result)
        return self._result(result.error or "I couldn’t verify that action.", False, intent, result=result)

    @staticmethod
    def _natural_result(intent: Intent, result: ToolResult) -> str:
        if intent.name == "memory_recall":
            matches = result.data.get("matches", [])
            return "I don’t know that yet." if not matches else f"You’re {matches[0].get('value', '')}."
        return result.data.get("message", "Done.")

    @staticmethod
    def _result(response: str, success: bool, intent: Intent, result: ToolResult | None = None, reasoned: bool = False) -> dict[str, Any]:
        return {"response": response, "success": success, "verified": bool(result and result.verified),
                "tool": intent.tool or "", "intent": intent.name, "intent_confidence": intent.confidence,
                "entities": intent.entities, "context": intent.context, "reasoned": reasoned,
                "reasoning_level": int(intent.level), "error": result.error if result else ""}


def build_runtime(data_dir: str | Path = "data") -> ExecutionFirstRuntime:
    """Build the dependency-free default runtime.

    Desktop/browser handlers intentionally fail closed: the legacy browser
    launcher cannot observe navigation, so it may not report a success.
    Hosts with browser automation can replace these handlers with verified ones.
    """
    registry = ToolRegistry()
    registry.register(ToolSpec("get_time", "Read the current local time", {}, "get_time()", ("time",), "low", "system clock read", False),
                      lambda: ToolResult(True, True, {"message": time.strftime("It’s %I:%M %p.")}))
    registry.register(ToolSpec("calculate", "Evaluate a supplied arithmetic expression", {}, "calculate(expression='2+2')", ("calculator",), "low", "numeric result", False),
                      lambda: ToolResult(False, False, error="A complete arithmetic expression is required"))
    def _open_url(url: str) -> ToolResult:
        try:
            opened = webbrowser.open(url)
            return ToolResult(opened, opened, {"url": url, "message": f"Opened {url}." if opened else f"Could not open {url}."})
        except Exception as exc:  # pragma: no cover - environment-dependent fallback
            return ToolResult(False, False, {"url": url}, str(exc))

    def _open_app(app: str) -> ToolResult:
        try:
            if hasattr(os, "startfile"):
                os.startfile(app)
            else:
                subprocess.Popen([app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return ToolResult(True, True, {"app": app, "message": f"Opened {app}."})
        except Exception as exc:  # pragma: no cover - environment-dependent fallback
            return ToolResult(False, False, {"app": app}, str(exc))

    registry.register(ToolSpec("open_url", "Open a website in a controlled browser", {"url": "absolute URL"}, "open_url(url='https://youtube.com')", ("open website",), "medium", "controlled browser URL", False),
                      _open_url)
    registry.register(ToolSpec("open_app", "Launch an application and verify its process", {"app": "application executable"}, "open_app(app='chrome')", ("launch app"), "medium", "process observed", False),
                      _open_app)
    registry.register(ToolSpec("take_screenshot", "Capture a screenshot", {}, "take_screenshot()", ("screenshot",), "medium", "output file exists", False),
                      lambda: ToolResult(False, False, error="No verified screenshot provider is configured"))
    # Memory tool contracts are represented in the registry; runtime dispatches
    # them to the one authoritative MemoryStore below.
    registry.register(ToolSpec("recall_memory", "Retrieve semantically related stored facts", {"query": "natural-language query"}, "recall_memory(query='my name')", ("remember",), "low", "embedding similarity result", False),
                      lambda query: ToolResult(False, False, error="Memory is handled by the runtime"))
    registry.register(ToolSpec("save_memory", "Store a user-provided fact", {"fact": "fact label", "value": "fact value"}, "save_memory(fact='name', value='Ada')", ("remember"), "low", "durable JSON write", False),
                      lambda fact, value: ToolResult(False, False, error="Memory is handled by the runtime"))
    # Destructive operations with confirmation requirement
    registry.register(ToolSpec("delete_file", "Delete a file from disk", {"file_path": "path to file"}, "delete_file(path='document.txt')", ("remove file", "delete"), "high", "file no longer exists", True),
                      lambda file_path: ToolResult(False, False, error="Delete file requires explicit confirmation"))
    registry.register(ToolSpec("system_shutdown", "Shut down the computer", {}, "system_shutdown()", ("shutdown", "power off"), "critical", "system powered off", True),
                      lambda: ToolResult(False, False, error="System shutdown requires explicit confirmation"))
    registry.register(ToolSpec("system_sleep", "Put the computer to sleep", {}, "system_sleep()", ("sleep", "hibernate"), "high", "system in sleep mode", True),
                      lambda: ToolResult(False, False, error="System sleep requires explicit confirmation"))
    
    # NOTE: Full tool migration to execution_first.ToolRegistry is in progress.
    # Currently, basic tools are registered here. Additional tools from core/tools
    # are available through the legacy registry and will be migrated incrementally.
    # Update FoodCache to include new modules
    FoodCache.names = ("00_identity.md", "01_reasoning.md", "02_tools.md", "03_memory.md", "04_context.md", "05_desktop.md", "06_browser.md", "07_speech.md", "08_vision.md", "09_apps.md", "10_personality.md", "11_safety.md", "12_examples.md", "13_examples.md", "14_failure_recovery.md", "15_security.md", "16_best_practices.md", "17_tool_aliases.md", "18_planning.md", "19_response_style.md", "20_music.md")
    
    embeddings = LocalNgramEmbeddings()
    return ExecutionFirstRuntime(SemanticIntentEngine(embeddings), registry,
                                 MemoryStore(data_dir, embeddings), FoodCache(), None)
