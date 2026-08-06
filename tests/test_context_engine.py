"""Tests for core.context_engine module."""
import pytest
from core.context_engine import (
    ContextEngine, ContextEntity, ContextEntry
)


class TestContextEntity:
    """Test ContextEntity dataclass."""
    
    def test_entity_creation(self):
        """Test entity creation."""
        entity = ContextEntity(
            name="youtube",
            type="website",
            metadata={"url": "https://youtube.com"}
        )
        assert entity.name == "youtube"
        assert entity.type == "website"
        assert entity.metadata == {"url": "https://youtube.com"}
    
    def test_entity_defaults(self):
        """Test entity with defaults."""
        entity = ContextEntity(name="test", type="test")
        assert entity.metadata == {}


class TestContextEntry:
    """Test ContextEntry dataclass."""
    
    def test_entry_creation(self):
        """Test entry creation."""
        entry = ContextEntry(
            user_input="open youtube",
            entities=[ContextEntity(name="youtube", type="website")],
            timestamp=1234567890.0
        )
        assert entry.user_input == "open youtube"
        assert len(entry.entities) == 1
        assert entry.timestamp == 1234567890.0


class TestContextEngine:
    """Test ContextEngine class."""
    
    def test_engine_creation(self):
        """Test engine creation."""
        engine = ContextEngine()
        assert engine is not None
    
    def test_add_context(self):
        """Test adding context."""
        engine = ContextEngine()
        entity = ContextEntity(name="youtube", type="website")
        engine.add_context(
            user_input="open youtube",
            entities=[entity]
        )
        assert len(engine._history) > 0
    
    def test_add_context_with_multiple_entities(self):
        """Test adding context with multiple entities."""
        engine = ContextEngine()
        entities = [
            ContextEntity(name="youtube", type="website"),
            ContextEntity(name="chrome", type="app")
        ]
        engine.add_context(
            user_input="open youtube in chrome",
            entities=entities
        )
        assert len(engine._history) > 0
        assert len(engine._history[0].entities) == 2
    
    def test_resolve_reference_there(self):
        """Test resolving 'there' reference."""
        engine = ContextEngine()
        entity = ContextEntity(name="youtube.com", type="website")
        engine.add_context(
            user_input="open youtube",
            entities=[entity]
        )
        engine._active_url = "youtube.com"
        
        result = engine.resolve_reference("there")
        assert result == "youtube.com"
    
    def test_resolve_reference_it(self):
        """Test resolving 'it' reference."""
        engine = ContextEngine()
        entity = ContextEntity(name="video", type="media")
        engine.add_context(
            user_input="play video",
            entities=[entity]
        )
        engine._entities["video"] = entity
        
        result = engine.resolve_reference("it")
        assert result == "video"
    
    def test_resolve_reference_this(self):
        """Test resolving 'this' reference."""
        engine = ContextEngine()
        engine._last_result = "selected text"
        
        result = engine.resolve_reference("this")
        assert result == "selected text"
    
    def test_resolve_reference_unknown(self):
        """Test resolving unknown reference."""
        engine = ContextEngine()
        result = engine.resolve_reference("unknown")
        assert result is None
    
    def test_get_entity(self):
        """Test getting entity."""
        engine = ContextEngine()
        entity = ContextEntity(name="youtube", type="website")
        engine._entities["youtube"] = entity
        
        result = engine.get_entity("youtube")
        assert result.name == "youtube"
    
    def test_get_entity_not_found(self):
        """Test getting non-existent entity."""
        engine = ContextEngine()
        result = engine.get_entity("nonexistent")
        assert result is None
    
    def test_get_context_history(self):
        """Test getting context history."""
        engine = ContextEngine()
        engine.add_context("test1", [])
        engine.add_context("test2", [])
        
        history = engine.get_context_history(limit=10)
        assert len(history) == 2
    
    def test_context_limit(self):
        """Test context history limit."""
        engine = ContextEngine()
        for i in range(150):
            engine.add_context(f"test{i}", [])
        
        history = engine.get_context_history(limit=100)
        assert len(history) <= 100


class TestReferenceResolutionEdgeCases:
    """Test edge cases in reference resolution."""
    
    def test_resolve_with_empty_history(self):
        """Test resolving with empty history."""
        engine = ContextEngine()
        result = engine.resolve_reference("there")
        assert result is None
    
    def test_resolve_with_no_entities(self):
        """Test resolving with no entities."""
        engine = ContextEngine()
        engine.add_context("test", [])
        result = engine.resolve_reference("it")
        assert result is None
    
    def test_resolve_with_case_variations(self):
        """Test resolving with case variations."""
        engine = ContextEngine()
        engine._last_result = "test"
        
        assert engine.resolve_reference("This") == "test"
        assert engine.resolve_reference("THIS") == "test"
        assert engine.resolve_reference("this") == "test"
    
    def test_resolve_with_whitespace(self):
        """Test resolving with whitespace."""
        engine = ContextEngine()
        engine._last_result = "test"
        
        assert engine.resolve_reference(" this ") == "test"
        assert engine.resolve_reference("  this  ") == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
