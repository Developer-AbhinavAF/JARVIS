"""Tests for execution_first runtime."""
import pytest
from core.execution_first import (
    ReasoningLevel, Intent, ToolSpec, ToolResult, ToolRegistry,
    SessionContext, MemoryStore, LocalNgramEmbeddings, SemanticIntentEngine,
    FoodCache, ExecutionFirstRuntime, build_runtime
)


class TestReasoningLevel:
    """Test reasoning level enumeration."""
    
    def test_reasoning_levels(self):
        """Test all reasoning levels are defined."""
        assert ReasoningLevel.ZERO == 0
        assert ReasoningLevel.SIMPLE == 1
        assert ReasoningLevel.MEMORY == 2
        assert ReasoningLevel.NORMAL == 3
        assert ReasoningLevel.COMPLEX == 4


class TestIntent:
    """Test Intent dataclass."""
    
    def test_intent_creation(self):
        """Test intent creation with all fields."""
        intent = Intent(
            name="test",
            confidence=0.95,
            entities={"key": "value"},
            context={"ctx": "val"},
            level=ReasoningLevel.NORMAL,
            tool="test_tool"
        )
        assert intent.name == "test"
        assert intent.confidence == 0.95
        assert intent.entities == {"key": "value"}
        assert intent.context == {"ctx": "val"}
        assert intent.level == ReasoningLevel.NORMAL
        assert intent.tool == "test_tool"
    
    def test_intent_defaults(self):
        """Test intent creation with defaults."""
        intent = Intent(name="test", confidence=0.5)
        assert intent.entities == {}
        assert intent.context == {}
        assert intent.level == ReasoningLevel.NORMAL
        assert intent.tool is None


class TestToolSpec:
    """Test ToolSpec dataclass."""
    
    def test_tool_spec_creation(self):
        """Test tool spec creation."""
        spec = ToolSpec(
            name="test_tool",
            description="Test tool",
            arguments={"arg1": "desc"},
            example="test_tool(arg1='value')",
            aliases=("alias1", "alias2"),
            risk="low",
            verify="verification check",
            requires_confirmation=False
        )
        assert spec.name == "test_tool"
        assert spec.description == "Test tool"
        assert spec.arguments == {"arg1": "desc"}
        assert spec.example == "test_tool(arg1='value')"
        assert spec.aliases == ("alias1", "alias2")
        assert spec.risk == "low"
        assert spec.verify == "verification check"
        assert spec.requires_confirmation is False
    
    def test_tool_spec_llm_card(self):
        """Test LLM card generation."""
        spec = ToolSpec(
            name="test",
            description="Test",
            arguments={"arg": "desc"},
            example="test(arg='val')",
            aliases=("alias",),
            risk="low",
            verify="check"
        )
        card = spec.llm_card()
        assert card["name"] == "test"
        assert card["description"] == "Test"
        assert card["arguments"] == {"arg": "desc"}
        assert card["example"] == "test(arg='val')"
        assert "risk" not in card  # Risk not exposed to LLM
        assert "verify" not in card  # Verify not exposed to LLM


class TestToolResult:
    """Test ToolResult dataclass."""
    
    def test_tool_result_success(self):
        """Test successful tool result."""
        result = ToolResult(True, True, {"message": "Success"})
        assert result.success is True
        assert result.verified is True
        assert result.data == {"message": "Success"}
        assert result.error == ""
    
    def test_tool_result_failure(self):
        """Test failed tool result."""
        result = ToolResult(False, False, error="Test error")
        assert result.success is False
        assert result.verified is False
        assert result.error == "Test error"
    
    def test_tool_result_unverified(self):
        """Test unverified tool result."""
        result = ToolResult(True, False, {"message": "Done"})
        assert result.success is True
        assert result.verified is False


class TestToolRegistry:
    """Test ToolRegistry class."""
    
    def test_registry_registration(self):
        """Test tool registration."""
        registry = ToolRegistry()
        spec = ToolSpec(
            name="test",
            description="Test",
            arguments={},
            example="test()",
            aliases=(),
            risk="low",
            verify="check"
        )
        handler = lambda: ToolResult(True, True, {"message": "ok"})
        registry.register(spec, handler)
        
        assert registry.get("test") == spec
    
    def test_registry_execution(self):
        """Test tool execution."""
        registry = ToolRegistry()
        spec = ToolSpec(
            name="test",
            description="Test",
            arguments={},
            example="test()",
            aliases=(),
            risk="low",
            verify="check"
        )
        handler = lambda: ToolResult(True, True, {"message": "ok"})
        registry.register(spec, handler)
        
        result = registry.execute("test")
        assert result.success is True
        assert result.verified is True
    
    def test_registry_missing_tool(self):
        """Test execution of missing tool."""
        registry = ToolRegistry()
        result = registry.execute("nonexistent")
        assert result.success is False
        assert "Unknown tool" in result.error
    
    def test_registry_missing_arguments(self):
        """Test execution with missing arguments."""
        registry = ToolRegistry()
        spec = ToolSpec(
            name="test",
            description="Test",
            arguments={"arg1": "required"},
            example="test(arg1='val')",
            aliases=(),
            risk="low",
            verify="check"
        )
        handler = lambda arg1: ToolResult(True, True, {"arg1": arg1})
        registry.register(spec, handler)
        
        result = registry.execute("test")
        assert result.success is False
        assert "Missing arguments" in result.error
    
    def test_registry_cards(self):
        """Test LLM cards generation."""
        registry = ToolRegistry()
        spec = ToolSpec(
            name="test",
            description="Test",
            arguments={},
            example="test()",
            aliases=(),
            risk="low",
            verify="check"
        )
        handler = lambda: ToolResult(True, True, {})
        registry.register(spec, handler)
        
        cards = registry.cards()
        assert len(cards) == 1
        assert cards[0]["name"] == "test"


class TestSessionContext:
    """Test SessionContext dataclass."""
    
    def test_context_creation(self):
        """Test context creation with all fields."""
        context = SessionContext(
            current_browser="chrome",
            current_website="youtube.com",
            current_folder="/home/user",
            current_app="vscode",
            current_window="editor",
            current_tab="main",
            current_selection="text",
            current_clipboard="copied",
            current_screenshot="/path/to/ss.png",
            current_file="/path/to/file.txt",
            current_camera_frame="/path/to/frame.jpg",
            current_mouse_position="100,200",
            last_tool="open_url",
            last_entity="youtube",
            last_person="user",
            last_command="open youtube",
            last_user_request="open youtube",
            conversation_topic="media"
        )
        assert context.current_browser == "chrome"
        assert context.current_website == "youtube.com"
        assert context.current_file == "/path/to/file.txt"
        assert context.conversation_topic == "media"
    
    def test_context_defaults(self):
        """Test context with defaults."""
        context = SessionContext()
        assert context.current_browser == ""
        assert context.current_file == ""
        assert context.conversation_topic == ""
    
    def test_context_snapshot(self):
        """Test context snapshot."""
        context = SessionContext(current_app="chrome")
        snapshot = context.snapshot()
        assert snapshot["current_app"] == "chrome"
        assert isinstance(snapshot, dict)
    
    def test_context_resolve(self):
        """Test reference resolution."""
        context = SessionContext(
            current_website="youtube.com",
            current_selection="text",
            last_command="open url"
        )
        assert context.resolve("there") == "youtube.com"
        assert context.resolve("it") == "text"
        assert context.resolve("again") == "open url"
    
    def test_context_update(self):
        """Test context update."""
        context = SessionContext()
        context.update(current_app="chrome", current_website="youtube.com")
        assert context.current_app == "chrome"
        assert context.current_website == "youtube.com"


class TestLocalNgramEmbeddings:
    """Test LocalNgramEmbeddings class."""
    
    def test_embedding_dimension(self):
        """Test embedding dimension."""
        embeddings = LocalNgramEmbeddings()
        assert embeddings.dimension == 512
    
    def test_single_embedding(self):
        """Test single text embedding."""
        embeddings = LocalNgramEmbeddings()
        vectors = embeddings.embed(["hello"])
        assert len(vectors) == 1
        assert len(vectors[0]) == 512
    
    def test_multiple_embeddings(self):
        """Test multiple text embeddings."""
        embeddings = LocalNgramEmbeddings()
        vectors = embeddings.embed(["hello", "world"])
        assert len(vectors) == 2
        assert len(vectors[0]) == 512
        assert len(vectors[1]) == 512
    
    def test_case_insensitive(self):
        """Test case insensitivity."""
        embeddings = LocalNgramEmbeddings()
        v1 = embeddings.embed(["hello"])[0]
        v2 = embeddings.embed(["HELLO"])[0]
        assert v1 == v2
    
    def test_whitespace_handling(self):
        """Test whitespace handling."""
        embeddings = LocalNgramEmbeddings()
        v1 = embeddings.embed(["hello"])[0]
        v2 = embeddings.embed(["  hello  "])[0]
        assert v1 == v2


class TestSemanticIntentEngine:
    """Test SemanticIntentEngine class."""
    
    def test_intent_detection_high_confidence(self):
        """Test high confidence intent detection."""
        embeddings = LocalNgramEmbeddings()
        engine = SemanticIntentEngine(embeddings)
        context = SessionContext()
        
        intent = engine.detect("hello", context)
        assert intent.name == "greeting"
        assert intent.confidence >= engine.threshold
    
    def test_intent_detection_low_confidence(self):
        """Test low confidence intent detection."""
        embeddings = LocalNgramEmbeddings()
        engine = SemanticIntentEngine(embeddings)
        context = SessionContext()
        
        intent = engine.detect("unknown complex command", context)
        assert intent.name == "unknown"
        assert intent.confidence < engine.threshold
    
    def test_intent_with_tool(self):
        """Test intent detection with tool mapping."""
        embeddings = LocalNgramEmbeddings()
        engine = SemanticIntentEngine(embeddings)
        context = SessionContext()
        
        intent = engine.detect("open youtube", context)
        assert intent.tool == "open_url"
        assert "url" in intent.entities
    
    def test_intent_reasoning_levels(self):
        """Test intent reasoning level assignment."""
        embeddings = LocalNgramEmbeddings()
        engine = SemanticIntentEngine(embeddings)
        context = SessionContext()
        
        greeting = engine.detect("hello", context)
        assert greeting.level == ReasoningLevel.ZERO
        
        time = engine.detect("what time is it", context)
        assert time.level == ReasoningLevel.SIMPLE


class TestMemoryStore:
    """Test MemoryStore class."""
    
    def test_memory_store_creation(self):
        """Test memory store creation."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryStore(tmpdir)
            assert memory.root.name == tmpdir
    
    def test_remember_fact(self):
        """Test remembering a fact."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryStore(tmpdir)
            result = memory.remember("name", "Ada", "facts")
            assert result.success is True
            assert result.verified is True
    
    def test_recall_with_embeddings(self):
        """Test recall with embeddings."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            embeddings = LocalNgramEmbeddings()
            memory = MemoryStore(tmpdir, embeddings)
            memory.remember("name", "Ada", "facts")
            
            result = memory.recall("name", limit=5)
            assert result.success is True
            assert result.verified is True
    
    def test_recall_without_embeddings(self):
        """Test recall without embeddings returns error."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryStore(tmpdir, None)
            result = memory.recall("name", limit=5)
            assert result.success is False
            assert "unavailable" in result.error


class TestFoodCache:
    """Test FoodCache class."""
    
    def test_food_cache_creation(self):
        """Test food cache creation."""
        cache = FoodCache()
        assert len(cache.modules) > 0
    
    def test_system_prompt(self):
        """Test system prompt generation."""
        cache = FoodCache()
        prompt = cache.system_prompt()
        assert len(prompt) > 0
        assert "JARVIS" in prompt or "Identity" in prompt


class TestExecutionFirstRuntime:
    """Test ExecutionFirstRuntime class."""
    
    def test_runtime_creation(self):
        """Test runtime creation."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = build_runtime(tmpdir)
            assert runtime.intents is not None
            assert runtime.tools is not None
            assert runtime.memory is not None
            assert runtime.food is not None
    
    def test_runtime_handle_greeting(self):
        """Test handling greeting."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = build_runtime(tmpdir)
            result = runtime.handle("hello")
            assert result["success"] is True
            assert result["intent"] == "greeting"
    
    def test_runtime_handle_unknown(self):
        """Test handling unknown command."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = build_runtime(tmpdir)
            result = runtime.handle("complex unknown command with no match")
            assert result["intent"] == "unknown"
    
    def test_runtime_context_updates(self):
        """Test context updates after execution."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = build_runtime(tmpdir)
            runtime.handle("hello")
            assert runtime.context.last_command == "hello"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
