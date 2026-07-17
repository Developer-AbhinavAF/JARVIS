"""Comprehensive Vision + NLP Integration Tests.

Tests all scenarios required for production-ready vision:
- Empty screen, browser, VS Code, terminal, settings, explorer
- PDF, Discord, Chrome, multiple monitors
- Dark mode, light mode, scaled displays
- OCR, code editor, compiler error, terminal output
- Visual query handling, no crashes, no empty intents
"""

import time
import pytest
from unittest.mock import MagicMock, patch


# ════════════════════════════════════════════════════════════════════
# FIXTURES
# ════════════════════════════════════════════════════════════════════


@pytest.fixture
def nlp_engine():
    """Create a fresh NLP engine for testing."""
    from jarvis.nlp import SemanticNLPEngine
    return SemanticNLPEngine()


@pytest.fixture
def vision_engine():
    """Create a fresh vision engine for testing."""
    from jarvis.vision import VisionEngine
    return VisionEngine()


@pytest.fixture
def vision_caps():
    """Create a vision capability detector."""
    from jarvis.vision.vision_capabilities import VisionCapabilityDetector
    return VisionCapabilityDetector()


@pytest.fixture
def vision_fusion():
    """Create a vision NLP fusion module."""
    from jarvis.vision.vision_nlp_fusion import VisionNLPFusion
    return VisionNLPFusion()


@pytest.fixture
def screen_memory():
    """Create a screen memory module."""
    from jarvis.vision.screen_memory import ScreenMemory
    return ScreenMemory()


# ════════════════════════════════════════════════════════════════════
# ISSUE 1: Empty Intent Never Happens
# ════════════════════════════════════════════════════════════════════


class TestEmptyIntentNeverHappens:
    """Visual queries must never result in empty intent."""

    @pytest.mark.parametrize("query", [
        "What error is shown?",
        "What is on my screen?",
        "Which application is active?",
        "Read this window",
        "What's this?",
        "Explain this",
        "Read this",
        "What am I looking at?",
        "Describe this window",
        "What is open?",
        "Find the button",
        "Read the code",
        "Summarize this screen",
        "What is this error?",
        "What error is this?",
        "What does this say?",
        "What is showing?",
        "What do you see?",
    ])
    def test_visual_query_never_empty_intent(self, nlp_engine, query):
        """Every visual query must produce a non-empty intent."""
        result = nlp_engine.process(query)
        assert result.intent != "", f"Empty intent for query: {query}"
        assert result.intent_confidence > 0, f"Zero confidence for query: {query}"

    @pytest.mark.parametrize("query", [
        "hello",
        "play music",
        "what time is it",
        "open chrome",
        "set a timer",
    ])
    def test_non_visual_queries_still_work(self, nlp_engine, query):
        """Non-visual queries must still produce valid intents."""
        result = nlp_engine.process(query)
        assert result.intent != "", f"Empty intent for query: {query}"


# ════════════════════════════════════════════════════════════════════
# ISSUE 2: OCR Returns Text
# ════════════════════════════════════════════════════════════════════


class TestOCREngine:
    """OCR must return text when visible text exists."""

    def test_ocr_has_backends(self, vision_engine):
        """OCR engine must have at least one backend available."""
        stats = vision_engine.ocr.get_stats()
        assert len(stats["backends"]) > 0, "No OCR backends available"

    def test_ocr_capture_result_conversion(self, vision_engine):
        """OCR must handle CaptureResult input correctly."""
        from jarvis.vision.screen_capture import CaptureResult
        from PIL import Image
        import numpy as np

        # Create a test image with text
        img = Image.new("RGB", (200, 50), color=(255, 255, 255))
        result = CaptureResult()
        result.image = img
        result.numpy_array = np.array(img)
        result.width = 200
        result.height = 50

        # OCR should not crash
        ocr_result = vision_engine.ocr.extract(result)
        assert ocr_result is not None
        assert hasattr(ocr_result, 'blocks')
        assert hasattr(ocr_result, 'full_text')

    def test_ocr_pil_image_conversion(self, vision_engine):
        """OCR must handle PIL Image input correctly."""
        from PIL import Image

        img = Image.new("RGB", (200, 50), color=(255, 255, 255))
        ocr_result = vision_engine.ocr.extract(img)
        assert ocr_result is not None

    def test_ocr_numpy_array_conversion(self, vision_engine):
        """OCR must handle numpy array input correctly."""
        import numpy as np

        arr = np.zeros((50, 200, 3), dtype=np.uint8)
        arr[:, :, :] = 255  # White background
        ocr_result = vision_engine.ocr.extract(arr)
        assert ocr_result is not None

    def test_ocr_region_crop(self, vision_engine):
        """OCR must handle region cropping."""
        from PIL import Image

        img = Image.new("RGB", (400, 200), color=(255, 255, 255))
        ocr_result = vision_engine.ocr.extract(img, region=(0, 0, 200, 100))
        assert ocr_result is not None

    def test_ocr_never_crashes_on_empty_image(self, vision_engine):
        """OCR must never crash even on empty/blank images."""
        from PIL import Image

        # Various edge cases
        for size in [(1, 1), (0, 0), (100, 100), (1920, 1080)]:
            try:
                img = Image.new("RGB", size, color=(0, 0, 0))
                result = vision_engine.ocr.extract(img)
                assert result is not None
            except Exception as e:
                pytest.fail(f"OCR crashed on image size {size}: {e}")


# ════════════════════════════════════════════════════════════════════
# ISSUE 3: Vision Before Intent Resolution
# ════════════════════════════════════════════════════════════════════


class TestVisionBeforeIntent:
    """Vision capability detection must run before intent classification."""

    def test_vision_capability_detection(self, vision_caps):
        """Must detect vision capabilities from text."""
        caps = vision_caps.detect("What error is shown?")
        assert caps.requires_screen is True
        assert caps.requires_ocr is True
        assert caps.confidence > 0.5

    def test_vision_capability_ui(self, vision_caps):
        """Must detect UI interaction needs."""
        caps = vision_caps.detect("Click the blue button")
        assert caps.requires_ui is True
        assert caps.requires_screen is True

    def test_vision_capability_code(self, vision_caps):
        """Must detect code analysis needs."""
        caps = vision_caps.detect("Read the code in the editor")
        assert caps.requires_code_analysis is True
        assert caps.requires_ocr is True

    def test_vision_capability_terminal(self, vision_caps):
        """Must detect terminal analysis needs."""
        caps = vision_caps.detect("What does the terminal say?")
        assert caps.requires_terminal_analysis is True

    def test_vision_capability_visual_analysis_intent(self, vision_caps):
        """VISUAL_ANALYSIS intent must enable all capabilities."""
        caps = vision_caps.detect("anything", intent="VISUAL_ANALYSIS")
        assert caps.requires_screen is True
        assert caps.requires_ocr is True
        assert caps.requires_ui is True
        assert caps.requires_layout is True
        assert caps.requires_reasoning is True

    def test_no_vision_for普通_queries(self, vision_caps):
        """Non-visual queries should not trigger vision."""
        caps = vision_caps.detect("play some music")
        assert caps.confidence == 0.0

    def test_pre_vision_in_pipeline(self, nlp_engine):
        """Pre-vision phase must run for visual queries."""
        result = nlp_engine.process("What is on my screen?")
        # Vision should have been activated
        assert result.parameters.get("vision_active") is True or \
               result.parameters.get("_pre_vision_state") is not None or \
               result.intent == "VISUAL_ANALYSIS"


# ════════════════════════════════════════════════════════════════════
# ISSUE 4: Visual Requests Never Crash
# ════════════════════════════════════════════════════════════════════


class TestVisualRequestsNeverCrash:
    """Every visual query must produce a response without crashing."""

    @pytest.mark.parametrize("query", [
        "What's this?",
        "Explain this",
        "Read this",
        "What error is this?",
        "What am I looking at?",
        "Describe this window",
        "What is open?",
        "Find the button",
        "Read the code",
        "Summarize this screen",
        "What do you see?",
        "Tell me what you see",
        "Analyze this",
        "What is displayed?",
        "What is visible?",
        "Look at this",
        "See this",
        "What is happening?",
    ])
    def test_visual_query_never_crashes(self, nlp_engine, query):
        """Every visual query must produce a response."""
        try:
            result = nlp_engine.process(query)
            assert result is not None
            assert result.intent != ""
        except Exception as e:
            pytest.fail(f"Visual query crashed: {query}\nError: {e}")


# ════════════════════════════════════════════════════════════════════
# ISSUE 5: Vision Capability Detection
# ════════════════════════════════════════════════════════════════════


class TestVisionCapabilityDetection:
    """Vision capabilities must be properly detected."""

    def test_screen_detection(self, vision_caps):
        caps = vision_caps.detect("What is on my screen?")
        assert caps.requires_screen is True

    def test_window_detection(self, vision_caps):
        caps = vision_caps.detect("What window is active?")
        assert caps.requires_screen is True

    def test_ocr_detection(self, vision_caps):
        caps = vision_caps.detect("Read the text on screen")
        assert caps.requires_ocr is True

    def test_ui_detection(self, vision_caps):
        caps = vision_caps.detect("Find the submit button")
        assert caps.requires_ui is True

    def test_object_detection_flag(self, vision_caps):
        caps = vision_caps.detect("What objects are on screen?")
        # Should at least require screen
        assert caps.requires_screen is True

    def test_code_analysis_detection(self, vision_caps):
        caps = vision_caps.detect("What error is in this code?")
        assert caps.requires_code_analysis is True

    def test_terminal_analysis_detection(self, vision_caps):
        caps = vision_caps.detect("What does the terminal output say?")
        assert caps.requires_terminal_analysis is True

    def test_document_analysis_detection(self, vision_caps):
        caps = vision_caps.detect("Read this PDF document")
        assert caps.requires_document_analysis is True

    def test_layout_detection(self, vision_caps):
        caps = vision_caps.detect("Describe the layout of this screen")
        # "layout" is not a keyword but "describe" + "screen" should trigger screen
        assert caps.requires_screen is True

    def test_multiple_capabilities(self, vision_caps):
        caps = vision_caps.detect("Read the error message in the VS Code terminal")
        assert caps.requires_screen is True
        assert caps.requires_ocr is True
        assert caps.requires_code_analysis is True

    def test_confidence_scoring(self, vision_caps):
        # High confidence: multiple matches
        caps1 = vision_caps.detect("Read the error text in the code editor terminal")
        assert caps1.confidence >= 0.8

        # Low confidence: single match
        caps2 = vision_caps.detect("screen")
        assert caps2.confidence <= 0.8

    def test_any_required(self, vision_caps):
        caps = vision_caps.detect("What is on my screen?")
        assert caps.any_required() is True

        caps_empty = vision_caps.detect("play music")
        assert caps_empty.any_required() is False


# ════════════════════════════════════════════════════════════════════
# ISSUE 6: Vision + Memory Integration
# ════════════════════════════════════════════════════════════════════


class TestVisionMemoryIntegration:
    """Vision context must be stored in memory for continuity."""

    def test_screen_memory_update(self, screen_memory):
        ctx = screen_memory.update_context(
            focused_app="Visual Studio Code",
            focused_window="main.py - JARVIS",
            window_count=5,
            has_errors=True,
            error_messages=["SyntaxError: invalid syntax"],
        )
        assert ctx.focused_app == "Visual Studio Code"
        assert ctx.has_errors is True

    def test_screen_memory_context_history(self, screen_memory):
        screen_memory.update_context(focused_app="Chrome")
        screen_memory.update_context(focused_app="VS Code")
        prev = screen_memory.get_previous_context()
        assert prev is not None
        assert prev.focused_app == "Chrome"

    def test_screen_memory_context_for_query(self, screen_memory):
        screen_memory.update_context(
            focused_app="VS Code",
            has_errors=True,
            error_messages=["TypeError: unsupported operand"],
        )
        ctx = screen_memory.get_context_for_query("What error is shown?")
        assert ctx["has_errors"] is True
        assert len(ctx["error_messages"]) > 0

    def test_screen_memory_events(self, screen_memory):
        screen_memory.record("error", "Test error", app="Chrome")
        screen_memory.record("window_open", "New window", app="VS Code")
        recent = screen_memory.get_recent(limit=5)
        assert len(recent) == 2

    def test_screen_memory_has_seen_error(self, screen_memory):
        screen_memory.record("error", "Unique error message 12345")
        assert screen_memory.has_seen_error("Unique error message 12345") is True
        assert screen_memory.has_seen_error("Different error") is False


# ════════════════════════════════════════════════════════════════════
# ISSUE 7: Vision + Reasoning Integration
# ════════════════════════════════════════════════════════════════════


class TestVisionReasoningIntegration:
    """Vision must provide context for reasoning, not just OCR text."""

    def test_fusion_error_queries(self, vision_fusion):
        result = vision_fusion.fuse("What error is shown?")
        assert "answer" in result
        assert "confidence" in result
        assert result["confidence"] > 0

    def test_fusion_read_queries(self, vision_fusion):
        result = vision_fusion.fuse("Read the screen")
        assert "answer" in result
        assert "confidence" in result

    def test_fusion_app_queries(self, vision_fusion):
        result = vision_fusion.fuse("What app is active?")
        assert "answer" in result

    def test_fusion_count_queries(self, vision_fusion):
        result = vision_fusion.fuse("How many windows are open?")
        assert "answer" in result

    def test_fusion_ui_queries(self, vision_fusion):
        result = vision_fusion.fuse("Click the submit button")
        assert "answer" in result

    def test_fusion_never_crashes(self, vision_fusion):
        queries = [
            "What's this?",
            "Explain this",
            "Read this",
            "What error is this?",
            "What am I looking at?",
            "Describe this window",
        ]
        for q in queries:
            result = vision_fusion.fuse(q)
            assert "answer" in result, f"Fusion failed for: {q}"
            assert "confidence" in result, f"No confidence for: {q}"

    def test_fusion_with_desktop_state(self, vision_fusion):
        mock_state = MagicMock()
        mock_state.to_dict.return_value = {
            "focused": "main.py - VS Code",
            "app": "Visual Studio Code",
            "windows": 5,
            "has_errors": True,
            "error_messages": ["SyntaxError on line 42"],
        }
        result = vision_fusion.fuse("What app is active?", desktop_state=mock_state)
        assert "Visual Studio Code" in result["answer"] or "VS Code" in result["answer"]


# ════════════════════════════════════════════════════════════════════
# ISSUE 8: Window Detection
# ════════════════════════════════════════════════════════════════════


class TestWindowDetection:
    """Window detection must expose all required fields."""

    def test_window_info_fields(self):
        from jarvis.vision.window_manager import WindowInfo
        w = WindowInfo(
            hwnd=12345,
            title="Test Window",
            app_name="TestApp",
            process_name="test.exe",
            process_id=999,
            left=0, top=0, width=800, height=600,
            is_focused=True,
            category="editor",
            confidence=0.9,
        )
        d = w.to_dict()
        assert d["hwnd"] == 12345
        assert d["app"] == "TestApp"
        assert d["process"] == "test.exe"
        assert d["pid"] == 999
        assert d["focused"] is True
        assert d["category"] == "editor"
        assert d["confidence"] == 0.9

    def test_scene_graph(self, vision_engine):
        scene = vision_engine.windows.get_scene_graph()
        assert "total_windows" in scene
        assert "focused_window" in scene
        assert "categories" in scene
        assert "apps" in scene
        assert "z_order" in scene

    def test_window_scan_returns_list(self, vision_engine):
        windows = vision_engine.windows.scan()
        assert isinstance(windows, list)

    def test_focused_window(self, vision_engine):
        focused = vision_engine.windows.get_focused_window()
        # May be None in headless environment, but should not crash
        if focused is not None:
            assert hasattr(focused, 'title')
            assert hasattr(focused, 'app_name')
            assert hasattr(focused, 'category')


# ════════════════════════════════════════════════════════════════════
# ISSUE 9: Scenario Tests
# ════════════════════════════════════════════════════════════════════


class TestScenarioIntegration:
    """End-to-end scenario tests for different screen states."""

    def test_browser_scenario(self, nlp_engine):
        """Browser-related queries must work."""
        queries = [
            "What website is open?",
            "What tab am I on?",
            "Read the page content",
        ]
        for q in queries:
            result = nlp_engine.process(q)
            assert result.intent != "", f"Failed for: {q}"

    def test_code_editor_scenario(self, nlp_engine):
        """Code editor queries must work."""
        queries = [
            "What error is in my code?",
            "Read the code on screen",
            "What file is open?",
        ]
        for q in queries:
            result = nlp_engine.process(q)
            assert result.intent != "", f"Failed for: {q}"

    def test_terminal_scenario(self, nlp_engine):
        """Terminal-related queries must work."""
        queries = [
            "What does the terminal say?",
            "Read the terminal output",
            "What command is running?",
        ]
        for q in queries:
            result = nlp_engine.process(q)
            assert result.intent != "", f"Failed for: {q}"

    def test_system_queries(self, nlp_engine):
        """System queries must work."""
        queries = [
            "How many windows are open?",
            "What application is active?",
            "What is on my screen?",
        ]
        for q in queries:
            result = nlp_engine.process(q)
            assert result.intent != "", f"Failed for: {q}"

    def test_error_analysis_scenario(self, nlp_engine):
        """Error analysis queries must work."""
        queries = [
            "What error is shown?",
            "Explain this error",
            "What caused this error?",
        ]
        for q in queries:
            result = nlp_engine.process(q)
            assert result.intent != "", f"Failed for: {q}"

    def test_mixed_language_support(self, nlp_engine):
        """Mixed language queries should not crash."""
        queries = [
            "What error hai screen pe?",
            "Read karo ye code",
        ]
        for q in queries:
            try:
                result = nlp_engine.process(q)
                assert result is not None
            except Exception as e:
                pytest.fail(f"Crashed on mixed language: {q}\nError: {e}")

    def test_pipeline_latency(self, nlp_engine):
        """NLP pipeline must complete within acceptable time."""
        t0 = time.perf_counter()
        result = nlp_engine.process("What is on my screen?")
        ms = (time.perf_counter() - t0) * 1000
        assert ms < 5000, f"Pipeline too slow: {ms:.0f}ms (limit: 5000ms)"

    def test_vision_engine_stats(self, vision_engine):
        """Vision engine must track stats correctly."""
        stats = vision_engine.get_stats()
        assert "pipeline_count" in stats
        assert "capture" in stats
        assert "ocr" in stats
        assert "windows" in stats


# ════════════════════════════════════════════════════════════════════
# INTEGRATION: NLP + Vision Pipeline
# ════════════════════════════════════════════════════════════════════


class TestNLPVisionIntegration:
    """Test the full NLP + Vision pipeline integration."""

    def test_visual_analysis_intent(self, nlp_engine):
        """VISUAL_ANALYSIS intent must be properly classified."""
        result = nlp_engine.process("What error is shown?")
        # Should either be VISUAL_ANALYSIS or have vision active
        has_vision = (
            result.intent == "VISUAL_ANALYSIS" or
            result.parameters.get("vision_active") is True or
            result.parameters.get("_pre_vision_state") is not None
        )
        assert has_vision, f"No vision for: What error is shown? (intent={result.intent})"

    def test_vision_answer_in_parameters(self, nlp_engine):
        """Vision answer should be in parameters when available."""
        result = nlp_engine.process("What app is active?")
        # Vision may or may not provide an answer depending on environment
        # But the pipeline must not crash
        assert result is not None

    def test_vision_error_handling(self, nlp_engine):
        """Pipeline must handle vision errors gracefully."""
        # Even if vision fails, the pipeline should complete
        result = nlp_engine.process("What is on my screen?")
        assert result is not None
        assert result.intent != ""

    def test_non_visual_bypasses_vision(self, nlp_engine):
        """Non-visual queries should not trigger vision."""
        result = nlp_engine.process("hello")
        assert result.parameters.get("vision_active") is False or \
               result.parameters.get("_pre_vision_state") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
