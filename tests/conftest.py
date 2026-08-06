"""Pytest configuration and fixtures."""
import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_embeddings():
    """Provide sample embeddings for testing."""
    from core.execution_first import LocalNgramEmbeddings
    return LocalNgramEmbeddings()


@pytest.fixture
def sample_context():
    """Provide sample context for testing."""
    from core.execution_first import SessionContext
    return SessionContext(
        current_browser="chrome",
        current_website="youtube.com",
        current_app="chrome"
    )


@pytest.fixture
def sample_tool_registry():
    """Provide sample tool registry for testing."""
    from core.execution_first import ToolRegistry, ToolSpec, ToolResult
    registry = ToolRegistry()
    
    spec = ToolSpec(
        name="test_tool",
        description="Test tool",
        arguments={},
        example="test_tool()",
        aliases=(),
        risk="low",
        verify="check"
    )
    registry.register(spec, lambda: ToolResult(True, True, {"message": "ok"}))
    
    return registry
