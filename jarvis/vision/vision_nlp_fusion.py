"""Vision + NLP Fusion — Combine visual understanding with language.

Handles ALL visual queries without crashing. Returns structured answers
for every type of visual question the user might ask.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class VisionNLPFusion:
    """Combines visual understanding with NLP capabilities."""

    def __init__(self) -> None:
        self._fusion_count: int = 0

    def fuse(
        self,
        text_query: str,
        desktop_state: Any = None,
        ocr_result: Any = None,
        elements: list[Any] | None = None,
        nlp_output: Any = None,
    ) -> dict[str, Any]:
        """Fuse visual and NLP information to answer a query.

        Never crashes. Always returns a dict with at least 'answer' and 'confidence'.
        """
        self._fusion_count += 1
        query_lower = text_query.lower()

        try:
            return self._fuse_internal(query_lower, desktop_state, ocr_result, elements, nlp_output)
        except Exception as e:
            logger.debug("Fusion failed: %s", e)
            return {"answer": "I can see the screen but had trouble analyzing it", "confidence": 0.2, "source": "fusion_error"}

    def _fuse_internal(
        self,
        query_lower: str,
        desktop_state: Any,
        ocr_result: Any,
        elements: list[Any] | None,
        nlp_output: Any,
    ) -> dict[str, Any]:
        """Internal fusion logic."""

        # ── Error queries ──────────────────────────────────────────
        if any(w in query_lower for w in ["error", "exception", "traceback", "bug", "crash"]):
            return self._answer_error(query_lower, ocr_result, desktop_state)

        # ── Reading/text queries ───────────────────────────────────
        if any(w in query_lower for w in ["read", "say", "text", "code", "log", "output"]):
            return self._answer_read(ocr_result)

        # ── Application/window queries ─────────────────────────────
        if any(w in query_lower for w in ["app", "application", "program", "window", "active", "running", "open", "focus"]):
            return self._answer_application(desktop_state)

        # ── Count queries ──────────────────────────────────────────
        if "how many" in query_lower:
            return self._answer_count(desktop_state)

        # ── UI interaction queries ─────────────────────────────────
        if any(w in query_lower for w in ["click", "press", "tap", "button", "link", "menu"]):
            return self._answer_ui(query_lower, elements)

        # ── Location queries ───────────────────────────────────────
        if any(w in query_lower for w in ["where", "location", "position"]):
            return self._answer_location(desktop_state)

        # ── Description/summary queries ────────────────────────────
        if any(w in query_lower for w in ["describe", "explain", "summarize", "what", "whats", "what's"]):
            return self._answer_describe(query_lower, desktop_state, ocr_result)

        # ── General visual question ────────────────────────────────
        return self._answer_general(desktop_state, ocr_result)

    def _answer_error(self, query_lower: str, ocr_result: Any, desktop_state: Any) -> dict[str, Any]:
        """Answer error-related queries."""
        # First check OCR for error text
        if ocr_result and hasattr(ocr_result, 'blocks'):
            errors = [b.text for b in ocr_result.blocks if getattr(b, 'block_type', '') == 'error']
            if errors:
                return {
                    "answer": f"Error on screen: {errors[0][:300]}",
                    "source": "vision_ocr",
                    "confidence": 0.85,
                    "error_count": len(errors),
                    "all_errors": [e[:200] for e in errors[:5]],
                }

        # Check desktop state for error indicators
        if desktop_state:
            d = desktop_state.to_dict() if hasattr(desktop_state, 'to_dict') else {}
            if d.get("has_errors"):
                error_msgs = d.get("error_messages", [])
                if error_msgs:
                    return {
                        "answer": f"Error detected: {error_msgs[0][:300]}",
                        "source": "vision_state",
                        "confidence": 0.75,
                    }

        # Check if OCR is available but returned no errors
        if ocr_result:
            full_text = getattr(ocr_result, 'full_text', '')
            if full_text:
                # Search for error-like patterns in raw text
                error_keywords = ["error", "exception", "traceback", "failed", "fatal", "panic"]
                for line in full_text.split('\n'):
                    if any(kw in line.lower() for kw in error_keywords):
                        return {
                            "answer": f"Possible error: {line.strip()[:300]}",
                            "source": "vision_ocr_raw",
                            "confidence": 0.7,
                        }

        return {
            "answer": "No error visible on screen. The display appears normal.",
            "source": "vision",
            "confidence": 0.6,
        }

    def _answer_read(self, ocr_result: Any) -> dict[str, Any]:
        """Answer reading/text queries."""
        if ocr_result:
            full_text = getattr(ocr_result, 'full_text', '')
            if full_text and full_text.strip():
                return {
                    "answer": full_text[:500],
                    "source": "vision_ocr",
                    "confidence": 0.8,
                    "word_count": getattr(ocr_result, 'word_count', 0),
                }
        return {
            "answer": "No readable text detected on screen. The screen may contain images or graphics rather than text.",
            "source": "vision",
            "confidence": 0.4,
        }

    def _answer_application(self, desktop_state: Any) -> dict[str, Any]:
        """Answer application/window queries."""
        if desktop_state:
            d = desktop_state.to_dict() if hasattr(desktop_state, 'to_dict') else {}
            focused = d.get('focused', 'Unknown')
            app = d.get('app', 'Unknown')
            windows = d.get('windows', 0)
            return {
                "answer": f"Active application: {focused} ({app}). {windows} window(s) open.",
                "source": "window_manager",
                "confidence": 0.9,
                "focused_window": focused,
                "focused_app": app,
                "window_count": windows,
            }
        return {
            "answer": "Unable to detect current application",
            "source": "vision",
            "confidence": 0.3,
        }

    def _answer_count(self, desktop_state: Any) -> dict[str, Any]:
        """Answer count queries."""
        if desktop_state:
            d = desktop_state.to_dict() if hasattr(desktop_state, 'to_dict') else {}
            windows = d.get('windows', 0)
            return {
                "answer": f"{windows} window(s) currently open on screen",
                "source": "window_manager",
                "confidence": 0.9,
                "count": windows,
            }
        return {"answer": "Unable to count windows", "confidence": 0.3}

    def _answer_ui(self, query_lower: str, elements: list[Any] | None) -> dict[str, Any]:
        """Answer UI interaction queries."""
        if elements:
            # Try to find matching elements
            interactive = [e for e in elements if getattr(e, 'is_interactive', False)]
            if interactive:
                matches = []
                for elem in interactive:
                    label = getattr(elem, 'label', '') or ''
                    etype = getattr(elem, 'element_type', '') or ''
                    if any(w in label.lower() or w in etype.lower() for w in query_lower.split()):
                        matches.append(elem)

                if matches:
                    elem = matches[0]
                    return {
                        "answer": f"Found: {getattr(elem, 'label', '') or getattr(elem, 'element_type', 'element')} at ({getattr(elem, 'x', 0)}, {getattr(elem, 'y', 0)})",
                        "element": elem.to_dict() if hasattr(elem, 'to_dict') else None,
                        "action": "click",
                        "confidence": 0.75,
                        "match_count": len(matches),
                    }

            # Return general UI info
            return {
                "answer": f"Found {len(elements)} UI elements on screen, {len(interactive)} are interactive",
                "source": "ui_detection",
                "confidence": 0.5,
                "element_count": len(elements),
                "interactive_count": len(interactive),
            }

        return {
            "answer": "No UI elements detected on screen",
            "confidence": 0.3,
        }

    def _answer_location(self, desktop_state: Any) -> dict[str, Any]:
        """Answer location queries."""
        if desktop_state:
            d = desktop_state.to_dict() if hasattr(desktop_state, 'to_dict') else {}
            return {
                "answer": f"Currently viewing: {d.get('focused', 'Unknown')} ({d.get('app', 'Unknown')})",
                "source": "window_manager",
                "confidence": 0.8,
            }
        return {"answer": "Unable to determine location on screen", "confidence": 0.3}

    def _answer_describe(self, query_lower: str, desktop_state: Any, ocr_result: Any) -> dict[str, Any]:
        """Answer description/what queries."""
        parts = []

        if desktop_state:
            d = desktop_state.to_dict() if hasattr(desktop_state, 'to_dict') else {}
            parts.append(f"Active: {d.get('focused', 'Unknown')} ({d.get('app', 'Unknown')})")
            parts.append(f"{d.get('windows', 0)} windows open")

        if ocr_result:
            full_text = getattr(ocr_result, 'full_text', '')
            if full_text:
                preview = full_text[:200].replace('\n', ' ')
                parts.append(f"Text visible: {preview}")

        if parts:
            return {
                "answer": ". ".join(parts),
                "source": "vision_fusion",
                "confidence": 0.75,
            }

        return {
            "answer": "I can see your screen but need more specific information to describe it in detail",
            "confidence": 0.4,
        }

    def _answer_general(self, desktop_state: Any, ocr_result: Any) -> dict[str, Any]:
        """General visual answer."""
        if desktop_state:
            d = desktop_state.to_dict() if hasattr(desktop_state, 'to_dict') else {}
            return {
                "answer": f"Screen shows: {d.get('focused', 'Unknown application')}. {d.get('windows', 0)} window(s) visible.",
                "source": "vision",
                "confidence": 0.5,
            }
        return {
            "answer": "I can see the screen but need more context to answer your question",
            "confidence": 0.3,
        }

    def get_stats(self) -> dict[str, Any]:
        return {"fusion_count": self._fusion_count}


vision_nlp_fusion = VisionNLPFusion()
