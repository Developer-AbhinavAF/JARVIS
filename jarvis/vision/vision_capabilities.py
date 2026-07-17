"""Vision Capability Detection — Determine what visual processing is needed.

Runs BEFORE intent classification to detect if the user's request
requires visual perception. Returns structured capability flags.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class VisionCapabilities:
    """What visual processing the current request requires."""
    requires_screen: bool = False      # Full screen capture needed
    requires_window: bool = False      # Specific window capture needed
    requires_ocr: bool = False         # Text extraction needed
    requires_ui: bool = False          # UI element detection needed
    requires_object_detection: bool = False  # Visual object detection
    requires_code_analysis: bool = False     # Code/IDE screen analysis
    requires_terminal_analysis: bool = False # Terminal output analysis
    requires_document_analysis: bool = False # Document/PDF analysis
    requires_layout: bool = False      # Layout/region analysis needed
    requires_reasoning: bool = False   # Deep visual reasoning needed
    confidence: float = 0.0            # How confident we are vision is needed
    reason: str = ""                   # Why we think vision is needed

    def any_required(self) -> bool:
        """Returns True if ANY visual capability is needed."""
        return any([
            self.requires_screen, self.requires_window, self.requires_ocr,
            self.requires_ui, self.requires_object_detection,
            self.requires_code_analysis, self.requires_terminal_analysis,
            self.requires_document_analysis, self.requires_layout,
            self.requires_reasoning,
        ])

    def to_dict(self) -> dict[str, Any]:
        return {
            "screen": self.requires_screen,
            "window": self.requires_window,
            "ocr": self.requires_ocr,
            "ui": self.requires_ui,
            "object_detection": self.requires_object_detection,
            "code_analysis": self.requires_code_analysis,
            "terminal_analysis": self.requires_terminal_analysis,
            "document_analysis": self.requires_document_analysis,
            "layout": self.requires_layout,
            "reasoning": self.requires_reasoning,
            "confidence": round(self.confidence, 2),
            "reason": self.reason,
        }


# ════════════════════════════════════════════════════════════════════
# VISUAL QUERY PATTERNS
# ════════════════════════════════════════════════════════════════════

# Patterns that indicate the user needs screen capture
_SCREEN_PATTERNS = [
    re.compile(r"\b(screen|display|monitor|desktop)\b", re.IGNORECASE),
    re.compile(r"\bwhat'?s?\s+(on|in|at)\s+(the|my|this)\s+(screen|display|window)\b", re.IGNORECASE),
    re.compile(r"\blook\s+(at|into)\b", re.IGNORECASE),
    re.compile(r"\bsee\b", re.IGNORECASE),
    re.compile(r"\bvisible\b", re.IGNORECASE),
    re.compile(r"\bshow(n|ing)?\b", re.IGNORECASE),
    re.compile(r"\bactive\b", re.IGNORECASE),
]

# Patterns that indicate OCR is needed
_OCR_PATTERNS = [
    re.compile(r"\bread\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+(does|do)\s+(this|it|the|that)\s+(say|mean|show)\b", re.IGNORECASE),
    re.compile(r"\btext\b", re.IGNORECASE),
    re.compile(r"\berror\s+(message|text|log)\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+error\b", re.IGNORECASE),
    re.compile(r"\bcompil(e|er|ation)\s+(error|output)\b", re.IGNORECASE),
    re.compile(r"\bconsole\s+(output|log|error)\b", re.IGNORECASE),
    re.compile(r"\btraceback\b", re.IGNORECASE),
    re.compile(r"\boutput\b", re.IGNORECASE),
    re.compile(r"\blog\b", re.IGNORECASE),
    re.compile(r"\bcode\b", re.IGNORECASE),
    re.compile(r"\bsummarize\b", re.IGNORECASE),
]

# Patterns that indicate UI element detection is needed
_UI_PATTERNS = [
    re.compile(r"\b(button|link|menu|tab|icon|field|input|box|checkbox|radio)\b", re.IGNORECASE),
    re.compile(r"\bclick\b", re.IGNORECASE),
    re.compile(r"\bpress\b", re.IGNORECASE),
    re.compile(r"\bfind\s+(the\s+)?(button|link|element)\b", re.IGNORECASE),
    re.compile(r"\bwhere\s+is\b", re.IGNORECASE),
    re.compile(r"\binteract\b", re.IGNORECASE),
]

# Patterns that indicate code analysis is needed
_CODE_PATTERNS = [
    re.compile(r"\b(code|script|program|function|class|method)\b", re.IGNORECASE),
    re.compile(r"\b(debug|debugging)\b", re.IGNORECASE),
    re.compile(r"\b(error|bug|issue)\s+(in|on|at|line)\b", re.IGNORECASE),
    re.compile(r"\beditor\b", re.IGNORECASE),
    re.compile(r"\bide\b", re.IGNORECASE),
    re.compile(r"\bvs\s*code\b", re.IGNORECASE),
    re.compile(r"\bpycharm\b", re.IGNORECASE),
    re.compile(r"\bintellij\b", re.IGNORECASE),
]

# Patterns that indicate terminal analysis is needed
_TERMINAL_PATTERNS = [
    re.compile(r"\b(terminal|console|command\s*line|shell|powershell|cmd|bash)\b", re.IGNORECASE),
    re.compile(r"\b命令行|终端\b"),
    re.compile(r"\brun\s+(the|this|that)\s+(command|script)\b", re.IGNORECASE),
]

# Patterns that indicate document analysis is needed
_DOCUMENT_PATTERNS = [
    re.compile(r"\b(pdf|document|doc|docx|text\s*file|spreadsheet|excel)\b", re.IGNORECASE),
    re.compile(r"\bslide|presentation|powerpoint\b", re.IGNORECASE),
]


class VisionCapabilityDetector:
    """Determines what visual processing a user request requires."""

    def __init__(self) -> None:
        self._detection_count: int = 0

    def detect(
        self,
        text: str,
        intent: str = "",
        context: dict[str, Any] | None = None,
    ) -> VisionCapabilities:
        """Detect what visual capabilities the request needs.

        Args:
            text: The user's input text
            intent: The classified intent (if available)
            context: Conversation context

        Returns:
            VisionCapabilities with flags set
        """
        self._detection_count += 1
        caps = VisionCapabilities()

        text_lower = text.lower()

        # If intent is already VISUAL_ANALYSIS, enable everything
        if intent == "VISUAL_ANALYSIS":
            caps.requires_screen = True
            caps.requires_ocr = True
            caps.requires_ui = True
            caps.requires_layout = True
            caps.requires_reasoning = True
            caps.confidence = 0.9
            caps.reason = "intent is VISUAL_ANALYSIS"
            return caps

        # Check screen patterns
        screen_matches = sum(1 for p in _SCREEN_PATTERNS if p.search(text))
        if screen_matches > 0:
            caps.requires_screen = True

        # Check OCR patterns
        ocr_matches = sum(1 for p in _OCR_PATTERNS if p.search(text))
        if ocr_matches > 0:
            caps.requires_ocr = True
            caps.requires_screen = True  # OCR needs screen capture

        # Check UI patterns
        ui_matches = sum(1 for p in _UI_PATTERNS if p.search(text))
        if ui_matches > 0:
            caps.requires_ui = True
            caps.requires_screen = True

        # Check code patterns
        code_matches = sum(1 for p in _CODE_PATTERNS if p.search(text))
        if code_matches > 0:
            caps.requires_code_analysis = True
            caps.requires_screen = True
            caps.requires_ocr = True

        # Check terminal patterns
        terminal_matches = sum(1 for p in _TERMINAL_PATTERNS if p.search(text))
        if terminal_matches > 0:
            caps.requires_terminal_analysis = True
            caps.requires_screen = True
            caps.requires_ocr = True

        # Check document patterns
        doc_matches = sum(1 for p in _DOCUMENT_PATTERNS if p.search(text))
        if doc_matches > 0:
            caps.requires_document_analysis = True
            caps.requires_screen = True
            caps.requires_ocr = True

        # Calculate confidence based on match count
        total_matches = screen_matches + ocr_matches + ui_matches + code_matches + terminal_matches + doc_matches
        if total_matches >= 3:
            caps.confidence = 0.95
        elif total_matches >= 2:
            caps.confidence = 0.85
        elif total_matches >= 1:
            caps.confidence = 0.7
        else:
            caps.confidence = 0.0

        # Determine reason
        reasons = []
        if screen_matches:
            reasons.append("screen keyword")
        if ocr_matches:
            reasons.append("text reading")
        if ui_matches:
            reasons.append("UI interaction")
        if code_matches:
            reasons.append("code context")
        if terminal_matches:
            reasons.append("terminal context")
        if doc_matches:
            reasons.append("document context")
        caps.reason = ", ".join(reasons) if reasons else "no visual signals"

        # If any capability was triggered, require screen
        if caps.any_required():
            caps.requires_screen = True

        return caps

    def get_stats(self) -> dict[str, Any]:
        return {"detection_count": self._detection_count}


vision_capability_detector = VisionCapabilityDetector()
