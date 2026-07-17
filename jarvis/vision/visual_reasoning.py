"""Visual Reasoning — Answer questions about the screen.

The AI should answer:
- What is happening?
- Which window is active?
- Which application failed?
- What error is shown?
- Which button should be clicked?
- What changed?
- Where is the problem?

Reason from the visual environment.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# VISUAL REASONING ENGINE
# ════════════════════════════════════════════════════════════════════

class VisualReasoning:
    """Answers questions about the visual environment.

    Combines window state, OCR text, UI elements, and layout
    to reason about what's happening on screen.
    """

    def __init__(self) -> None:
        self._reasoning_count: int = 0

    def answer(
        self,
        question: str,
        desktop_state: Any = None,
        ocr_result: Any = None,
        elements: list[Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Answer a visual question.

        Returns:
            Dict with answer, confidence, and supporting evidence.
        """
        self._reasoning_count += 1
        question_lower = question.lower()

        # Route to specific handler
        if any(w in question_lower for w in ["what", "which"]):
            if "error" in question_lower:
                return self._find_errors(desktop_state, ocr_result)
            if "window" in question_lower or "app" in question_lower:
                return self._describe_active(desktop_state)
            if "button" in question_lower or "click" in question_lower:
                return self._find_clickable(elements, desktop_state)
            if "text" in question_lower or "says" in question_lower:
                return self._read_text(ocr_result)
            if "change" in question_lower:
                return self._detect_changes(desktop_state)
            return self._general_describe(desktop_state, ocr_result)

        if any(w in question_lower for w in ["where", "find", "locate"]):
            return self._visual_search(question, elements, desktop_state)

        if any(w in question_lower for w in ["help", "fix", "solve"]):
            return self._suggest_help(desktop_state, ocr_result)

        if "how many" in question_lower:
            return self._count_elements(desktop_state, elements)

        return self._general_describe(desktop_state, ocr_result)

    def explain_screen(self, desktop_state: Any = None) -> str:
        """Generate a natural language explanation of the screen."""
        if not desktop_state:
            return "No screen data available"

        parts = []

        # Active app
        focused = getattr(desktop_state, 'focused_window', '') or desktop_state.to_dict().get('focused', '')
        if focused:
            parts.append(f"Active window: {focused}")

        # Window count
        wc = getattr(desktop_state, 'window_count', 0) or desktop_state.to_dict().get('windows', 0)
        if wc:
            parts.append(f"{wc} windows open")

        # Errors
        if getattr(desktop_state, 'has_errors', False):
            errors = getattr(desktop_state, 'error_messages', [])
            parts.append(f"ERROR DETECTED: {errors[0] if errors else 'Unknown error'}")

        # Text
        text = getattr(desktop_state, 'visible_text', '')
        if text and len(text) > 20:
            parts.append(f"Visible text includes: {text[:100]}...")

        return ". ".join(parts) if parts else "Screen is active"

    # ── Question Handlers ──

    def _find_errors(self, desktop_state: Any, ocr_result: Any) -> dict[str, Any]:
        errors = []
        if ocr_result and hasattr(ocr_result, 'blocks'):
            errors = [b.text for b in ocr_result.blocks if getattr(b, 'block_type', '') == 'error']
        if desktop_state and getattr(desktop_state, 'has_errors', False):
            errors.extend(getattr(desktop_state, 'error_messages', []))

        if errors:
            return {
                "answer": f"Found {len(errors)} error(s): {errors[0][:100]}",
                "errors": errors,
                "confidence": 0.8,
            }
        return {"answer": "No errors detected on screen", "confidence": 0.7}

    def _describe_active(self, desktop_state: Any) -> dict[str, Any]:
        if not desktop_state:
            return {"answer": "No screen data", "confidence": 0.0}
        d = desktop_state.to_dict() if hasattr(desktop_state, 'to_dict') else {}
        focused = d.get("focused", "Unknown")
        app = d.get("app", "Unknown")
        return {
            "answer": f"Active: {focused} ({app})",
            "window": focused,
            "app": app,
            "confidence": 0.9,
        }

    def _find_clickable(self, elements: list[Any] | None, desktop_state: Any) -> dict[str, Any]:
        if not elements:
            return {"answer": "No interactive elements detected", "confidence": 0.3}
        interactive = [e for e in elements if getattr(e, 'is_interactive', False)]
        if interactive:
            labels = [getattr(e, 'label', '') or getattr(e, 'element_type', '') for e in interactive[:5]]
            return {
                "answer": f"Found {len(interactive)} clickable elements: {', '.join(labels)}",
                "elements": [e.to_dict() if hasattr(e, 'to_dict') else str(e) for e in interactive[:10]],
                "confidence": 0.6,
            }
        return {"answer": "No clearly clickable elements found", "confidence": 0.4}

    def _read_text(self, ocr_result: Any) -> dict[str, Any]:
        if not ocr_result:
            return {"answer": "No text data available", "confidence": 0.0}
        text = getattr(ocr_result, 'full_text', '')
        if text:
            preview = text[:300].replace('\n', ' ')
            return {"answer": f"Screen text: {preview}", "confidence": 0.7}
        return {"answer": "No readable text found", "confidence": 0.5}

    def _detect_changes(self, desktop_state: Any) -> dict[str, Any]:
        if not desktop_state:
            return {"answer": "No change data", "confidence": 0.0}
        # This would compare with history
        return {"answer": "Change detection available in desktop map", "confidence": 0.5}

    def _visual_search(self, query: str, elements: list[Any] | None, desktop_state: Any) -> dict[str, Any]:
        if not elements:
            return {"answer": f"Cannot search — no elements detected", "confidence": 0.2}
        # Simple text matching
        query_lower = query.lower()
        matches = []
        for e in elements:
            label = getattr(e, 'label', '').lower()
            etype = getattr(e, 'element_type', '').lower()
            if query_lower in label or query_lower in etype:
                matches.append(e)
        if matches:
            return {
                "answer": f"Found {len(matches)} matching elements",
                "matches": [m.to_dict() if hasattr(m, 'to_dict') else str(m) for m in matches[:5]],
                "confidence": 0.6,
            }
        return {"answer": f"Could not find '{query}' on screen", "confidence": 0.3}

    def _suggest_help(self, desktop_state: Any, ocr_result: Any) -> dict[str, Any]:
        errors = []
        if ocr_result and hasattr(ocr_result, 'blocks'):
            errors = [b.text for b in ocr_result.blocks if getattr(b, 'block_type', '') == 'error']
        if errors:
            return {
                "answer": f"I see an error: {errors[0][:200]}. Let me help you fix it.",
                "error": errors[0],
                "confidence": 0.7,
            }
        return {"answer": "I don't see any obvious issues. What do you need help with?", "confidence": 0.5}

    def _count_elements(self, desktop_state: Any, elements: list[Any] | None) -> dict[str, Any]:
        wc = getattr(desktop_state, 'window_count', 0) if desktop_state else 0
        ec = len(elements) if elements else 0
        return {
            "answer": f"{wc} windows, {ec} UI elements detected",
            "windows": wc,
            "elements": ec,
            "confidence": 0.8,
        }

    def _general_describe(self, desktop_state: Any, ocr_result: Any) -> dict[str, Any]:
        desc = self.explain_screen(desktop_state)
        return {"answer": desc, "confidence": 0.6}

    def get_stats(self) -> dict[str, Any]:
        return {"reasoning_count": self._reasoning_count}


visual_reasoning = VisualReasoning()
