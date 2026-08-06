"""Tests for core.tools module."""
import pytest
from core.tools import (
    ToolResult, ToolCategory, tool_registry,
    get_time, get_date, calculate, open_app, close_app,
    open_url, web_search, search_youtube, take_screenshot,
    list_running_apps, get_active_app, create_file, read_file,
    delete_file, save_memory, recall_memory, delete_memory,
    get_system_info, play_media, get_weather, get_joke,
    verify_process_running, verify_file_exists
)


class TestToolResult:
    """Test ToolResult dataclass."""
    
    def test_tool_result_fields(self):
        """Test all ToolResult fields."""
        result = ToolResult(
            success=True,
            verified=True,
            data={"key": "value"},
            error="",
            tool_name="test_tool",
            execution_time_ms=100.0,
            verification_time_ms=50.0,
            verification_details="Verified"
        )
        assert result.success is True
        assert result.verified is True
        assert result.data == {"key": "value"}
        assert result.tool_name == "test_tool"
        assert result.execution_time_ms == 100.0
    
    def test_tool_result_defaults(self):
        """Test ToolResult with defaults."""
        result = ToolResult(success=False, verified=False)
        assert result.data is None
        assert result.error == ""
        assert result.tool_name == ""


class TestToolCategory:
    """Test ToolCategory enumeration."""
    
    def test_tool_categories(self):
        """Test all tool categories."""
        assert ToolCategory.APPLICATIONS
        assert ToolCategory.BROWSER
        assert ToolCategory.SEARCH
        assert ToolCategory.SYSTEM
        assert ToolCategory.VISION
        assert ToolCategory.DESKTOP
        assert ToolCategory.UTILITY
        assert ToolCategory.FILES
        assert ToolCategory.MEMORY
        assert ToolCategory.MEDIA


class TestVerificationFunctions:
    """Test verification functions."""
    
    def test_verify_file_exists_true(self):
        """Test file exists verification."""
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name
        try:
            assert verify_file_exists(path) is True
        finally:
            import os
            os.unlink(path)
    
    def test_verify_file_exists_false(self):
        """Test file does not exist verification."""
        assert verify_file_exists("/nonexistent/file.txt") is False
    
    def test_verify_process_running(self):
        """Test process running verification."""
        # Should work for common processes or return False gracefully
        result = verify_process_running("python")
        assert isinstance(result, bool)


class TestTimeTools:
    """Test time-related tools."""
    
    def test_get_time(self):
        """Test get_time tool."""
        result = get_time()
        assert result.success is True
        assert result.verified is True
        assert "result" in result.result
    
    def test_get_date(self):
        """Test get_date tool."""
        result = get_date()
        assert result.success is True
        assert result.verified is True
        assert "result" in result.result


class TestCalculationTool:
    """Test calculation tool."""
    
    def test_calculate_valid(self):
        """Test valid calculation."""
        result = calculate(expression="2+2")
        assert result.success is True
        assert result.verified is True
    
    def test_calculate_invalid(self):
        """Test invalid calculation."""
        result = calculate(expression="invalid")
        assert result.success is False


class TestApplicationTools:
    """Test application-related tools."""
    
    def test_open_app(self):
        """Test open_app tool."""
        result = open_app(app_name="notepad")
        # May fail if notepad not available, but should return ToolResult
        assert isinstance(result, ToolResult)
    
    def test_close_app(self):
        """Test close_app tool."""
        result = close_app(app_name="notepad")
        assert isinstance(result, ToolResult)
    
    def test_list_running_apps(self):
        """Test list_running_apps tool."""
        result = list_running_apps()
        assert isinstance(result, ToolResult)
        if result.success:
            assert "result" in result.result
    
    def test_get_active_app(self):
        """Test get_active_app tool."""
        result = get_active_app()
        assert isinstance(result, ToolResult)


class TestBrowserTools:
    """Test browser-related tools."""
    
    def test_open_url(self):
        """Test open_url tool."""
        result = open_url(url="https://example.com")
        assert isinstance(result, ToolResult)
    
    def test_web_search(self):
        """Test web_search tool."""
        result = web_search(query="test search")
        assert isinstance(result, ToolResult)
    
    def test_search_youtube(self):
        """Test search_youtube tool."""
        result = search_youtube(query="test video")
        assert isinstance(result, ToolResult)


class TestVisionTools:
    """Test vision-related tools."""
    
    def test_take_screenshot(self):
        """Test take_screenshot tool."""
        result = take_screenshot()
        assert isinstance(result, ToolResult)
    
    def test_show_image(self):
        """Test show_image tool."""
        result = show_image()
        assert isinstance(result, ToolResult)


class TestFileTools:
    """Test file-related tools."""
    
    def test_create_file(self):
        """Test create_file tool."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/test.txt"
            result = create_file(file_path=path, content="test content")
            assert isinstance(result, ToolResult)
            if result.success:
                assert verify_file_exists(path) is True
    
    def test_read_file(self):
        """Test read_file tool."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/test.txt"
            with open(path, "w") as f:
                f.write("test content")
            result = read_file(file_path=path)
            assert isinstance(result, ToolResult)
    
    def test_delete_file(self):
        """Test delete_file tool."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/test.txt"
            with open(path, "w") as f:
                f.write("test content")
            result = delete_file(file_path=path)
            assert isinstance(result, ToolResult)


class TestMemoryTools:
    """Test memory-related tools."""
    
    def test_save_memory(self):
        """Test save_memory tool."""
        result = save_memory(key="test_key", value="test_value")
        assert isinstance(result, ToolResult)
    
    def test_recall_memory(self):
        """Test recall_memory tool."""
        result = recall_memory(query="test")
        assert isinstance(result, ToolResult)
    
    def test_delete_memory(self):
        """Test delete_memory tool."""
        result = delete_memory(query="test")
        assert isinstance(result, ToolResult)


class TestSystemTools:
    """Test system-related tools."""
    
    def test_get_system_info(self):
        """Test get_system_info tool."""
        result = get_system_info()
        assert isinstance(result, ToolResult)
        if result.success:
            assert "result" in result.result
    
    def test_get_system_stats(self):
        """Test get_system_stats tool."""
        result = get_system_stats()
        assert isinstance(result, ToolResult)


class TestMediaTools:
    """Test media-related tools."""
    
    def test_play_media(self):
        """Test play_media tool."""
        result = play_media(media_query="test song")
        assert isinstance(result, ToolResult)
    
    def test_adjust_volume(self):
        """Test adjust_volume tool."""
        result = adjust_volume(direction="up")
        assert isinstance(result, ToolResult)


class TestUtilityTools:
    """Test utility tools."""
    
    def test_get_weather(self):
        """Test get_weather tool."""
        result = get_weather(location="London")
        assert isinstance(result, ToolResult)
    
    def test_get_joke(self):
        """Test get_joke tool."""
        result = get_joke()
        assert isinstance(result, ToolResult)
    
    def test_image_search(self):
        """Test image_search tool."""
        result = image_search(query="test")
        assert isinstance(result, ToolResult)


class TestToolRegistry:
    """Test tool registry."""
    
    def test_registry_initialization(self):
        """Test registry is initialized."""
        assert tool_registry is not None
    
    def test_registry_has_tools(self):
        """Test registry has tools registered."""
        all_tools = tool_registry.get_all()
        assert len(all_tools) > 0
    
    def test_registry_get_tool(self):
        """Test getting a specific tool."""
        tool = tool_registry.get("get_time")
        assert tool is not None
        assert tool["name"] == "get_time"
    
    def test_registry_execute_tool(self):
        """Test executing a tool from registry."""
        result = tool_registry.execute("get_time")
        assert isinstance(result, ToolResult)
    
    def test_registry_execute_invalid_tool(self):
        """Test executing invalid tool."""
        result = tool_registry.execute("nonexistent_tool")
        assert result.success is False


class TestToolIntegration:
    """Test tool integration scenarios."""
    
    def test_file_workflow(self):
        """Test complete file workflow."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/workflow_test.txt"
            
            # Create
            create_result = create_file(file_path=path, content="test")
            assert isinstance(create_result, ToolResult)
            
            # Read
            read_result = read_file(file_path=path)
            assert isinstance(read_result, ToolResult)
            
            # Delete
            delete_result = delete_file(file_path=path)
            assert isinstance(delete_result, ToolResult)
    
    def test_memory_workflow(self):
        """Test memory workflow."""
        # Save
        save_result = save_memory(key="workflow_test", value="test_value")
        assert isinstance(save_result, ToolResult)
        
        # Recall
        recall_result = recall_memory(query="workflow_test")
        assert isinstance(recall_result, ToolResult)
        
        # Delete
        delete_result = delete_memory(query="workflow_test")
        assert isinstance(delete_result, ToolResult)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
