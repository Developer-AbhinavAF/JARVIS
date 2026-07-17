"""Computer Vision & Environment Understanding for JARVIS.

Transforms pixels into understanding.

Pipeline:
  Screen → Image Capture → Object Detection → OCR → Layout Analysis →
  Window Detection → Element Detection → Relationship Mapping →
  Reasoning → Memory → Action

Every visible object becomes meaningful information.
"""

from __future__ import annotations

import time
import logging
from typing import Any

from .screen_capture import ScreenCapture, screen_capture, CaptureResult
from .ocr_engine import OCREngine, ocr_engine, OCRResult
from .window_manager import WindowManager, window_manager, WindowInfo
from .ui_detection import UIDetection, ui_detection, UIElement
from .layout_analyzer import LayoutAnalyzer, layout_analyzer, LayoutRegion
from .desktop_map import DesktopMap, desktop_map, DesktopState
from .visual_reasoning import VisualReasoning, visual_reasoning
from .screen_memory import ScreenMemory, screen_memory
from .mouse_tracker import MouseTracker, mouse_tracker
from .event_detector import EventDetector, event_detector
from .vision_nlp_fusion import VisionNLPFusion, vision_nlp_fusion
from .vision_capabilities import VisionCapabilityDetector, vision_capability_detector

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# VISION ENGINE
# ════════════════════════════════════════════════════════════════════

class VisionEngine:
    """The unified computer vision engine.

    Orchestrates the full vision pipeline:
    1. Capture screen
    2. Detect windows
    3. Extract text (OCR)
    4. Detect UI elements
    5. Analyze layout
    6. Update desktop map
    7. Detect events
    8. Reason about content
    """

    def __init__(self) -> None:
        self.capture = screen_capture
        self.ocr = ocr_engine
        self.windows = window_manager
        self.ui = ui_detection
        self.layout = layout_analyzer
        self.desktop = desktop_map
        self.reasoning = visual_reasoning
        self.memory = screen_memory
        self.mouse = mouse_tracker
        self.events = event_detector
        self.fusion = vision_nlp_fusion
        self.capability_detector = vision_capability_detector

        self._pipeline_count: int = 0

    def see(
        self,
        region: tuple[int, int, int, int] | None = None,
        full_pipeline: bool = True,
    ) -> DesktopState:
        """Run the full vision pipeline.

        Captures screen, extracts all information, and returns
        a complete DesktopState.
        """
        t0 = time.perf_counter()

        # 1. Capture screen
        capture = self.capture.capture(region=region)

        # 2. Scan windows
        windows = self.windows.scan()

        # 3. OCR
        ocr_result = self.ocr.extract(capture)

        # 4. UI element detection
        elements = self.ui.detect(capture, ocr_result.blocks if ocr_result else None)

        # 5. Layout analysis
        regions = self.layout.analyze(elements, capture.width, capture.height)

        # 6. Update desktop map
        displays = self.capture.get_monitor_info()
        state = self.desktop.update(windows, elements, ocr_result, regions, displays)

        # 7. Detect events
        event_detector.detect(windows, ocr_result)

        # 8. Record in memory
        if state.has_errors:
            self.memory.record("error", state.error_messages[0] if state.error_messages else "Unknown error",
                             app=state.focused_app)

        # 9. Update vision context for reasoning
        ocr_text = ocr_result.full_text if ocr_result else ""
        visible_urls = [b.text for b in (ocr_result.blocks if ocr_result else [])
                       if getattr(b, 'block_type', '') == 'url']
        visible_documents = [b.text for b in (ocr_result.blocks if ocr_result else [])
                            if any(ext in b.text.lower() for ext in ['.pdf', '.doc', '.docx', '.txt', '.md'])]

        self.memory.update_context(
            focused_app=state.focused_app,
            focused_window=state.focused_window if hasattr(state, 'focused_window') else '',
            window_count=state.window_count,
            has_errors=state.has_errors,
            error_messages=state.error_messages[:5] if state.error_messages else [],
            visible_urls=visible_urls,
            visible_documents=visible_documents,
            visible_code=ocr_result.has_code if ocr_result else False,
            visible_terminal=any(w.app_name.lower() in ('terminal', 'cmd', 'powershell', 'wt', 'bash')
                               for w in windows),
            element_count=state.element_count,
            ocr_text_preview=ocr_text[:500] if ocr_text else '',
        )

        self._pipeline_count += 1
        total_ms = (time.perf_counter() - t0) * 1000
        logger.debug("Vision pipeline: %.1fms (capture=%.1f ocr=%.1f)",
                     total_ms, capture.capture_time_ms, ocr_result.ocr_time_ms if ocr_result else 0)

        return state

    def look_at(
        self,
        target: str,
    ) -> dict[str, Any]:
        """Look at a specific target (window, region, etc)."""
        # Try to find and focus the window
        window = self.windows.get_window_by_title(target)
        if window:
            capture = self.capture.capture_window(title=target)
            ocr_result = self.ocr.extract(capture)
            elements = self.ui.detect(capture, ocr_result.blocks if ocr_result else None)
            return {
                "window": window.to_dict(),
                "text": ocr_result.full_text[:500] if ocr_result else "",
                "elements": len(elements),
                "has_errors": ocr_result.has_errors if ocr_result else False,
            }
        return {"error": f"Could not find: {target}"}

    def ask(
        self,
        question: str,
    ) -> dict[str, Any]:
        """Ask a question about the current screen."""
        state = self.see()
        ocr_result = self.ocr.extract_from_screen()
        elements = self.ui.detect(
            self.capture.get_last_capture(),
            ocr_result.blocks if ocr_result else None,
        )
        return self.fusion.fuse(question, state, ocr_result, elements)

    def find_text(self, text: str) -> dict[str, Any] | None:
        """Find specific text on screen."""
        result = self.ocr.find_on_screen(text)
        if result:
            return {"found": True, "text": result.text, "position": (result.x, result.y)}
        return {"found": False}

    def get_stats(self) -> dict[str, Any]:
        return {
            "pipeline_count": self._pipeline_count,
            "capture": self.capture.get_stats(),
            "ocr": self.ocr.get_stats(),
            "windows": self.windows.get_stats(),
            "ui": self.ui.get_stats(),
            "layout": self.layout.get_stats(),
            "desktop": self.desktop.get_stats(),
            "memory": self.memory.get_stats(),
            "events": self.events.get_stats(),
            "fusion": self.fusion.get_stats(),
        }


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

vision_engine = VisionEngine()

__all__ = [
    "VisionEngine",
    "vision_engine",
    "screen_capture",
    "ocr_engine",
    "window_manager",
    "ui_detection",
    "layout_analyzer",
    "desktop_map",
    "visual_reasoning",
    "screen_memory",
    "mouse_tracker",
    "event_detector",
    "vision_nlp_fusion",
]
