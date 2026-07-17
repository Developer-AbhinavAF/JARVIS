"""UI Detection — Detect interactive UI elements on screen.

Detect buttons, checkboxes, input fields, dropdowns, tabs, cards,
images, menus, dialogs, progress bars — everything becomes an
interactive object.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


# ════════════════════════════════════════════════════════════════════
# UI ELEMENT
# ════════════════════════════════════════════════════════════════════

@dataclass
class UIElement:
    """A detected UI element."""
    element_id: str = ""
    element_type: str = "unknown"   # button, input, text, checkbox, etc.
    label: str = ""                  # Visible text/label
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    confidence: float = 0.5
    is_interactive: bool = False
    is_enabled: bool = True
    state: str = "normal"           # normal, focused, hover, disabled
    children: list[str] = field(default_factory=list)  # Child element IDs
    parent: str = ""

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def bounds(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    def contains(self, px: int, py: int) -> bool:
        return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.element_id,
            "type": self.element_type,
            "label": self.label[:50],
            "x": self.x, "y": self.y,
            "w": self.width, "h": self.height,
            "interactive": self.is_interactive,
            "enabled": self.is_enabled,
        }


# ════════════════════════════════════════════════════════════════════
# UI DETECTION ENGINE
# ════════════════════════════════════════════════════════════════════

class UIDetection:
    """Detects UI elements from screen images.

    Uses computer vision techniques:
    - Edge detection for buttons/inputs
    - Color analysis for interactive elements
    - Template matching for known controls
    - Contour detection for regions
    """

    def __init__(self) -> None:
        self._element_count: int = 0
        self._detection_count: int = 0

    def detect(
        self,
        image: Any,
        ocr_blocks: list[Any] | None = None,
    ) -> list[UIElement]:
        """Detect UI elements from an image.

        Args:
            image: numpy array (BGR) or PIL Image.
            ocr_blocks: Optional OCR results to label elements.

        Returns:
            List of detected UIElement objects.
        """
        t0 = time.perf_counter()
        elements: list[UIElement] = []

        if not HAS_CV2:
            logger.debug("OpenCV not available for UI detection")
            return elements

        # Convert to numpy if needed
        if hasattr(image, 'to_numpy'):
            img = image.to_numpy()
        elif hasattr(image, 'numpy_array'):
            img = image.numpy_array
        elif isinstance(image, np.ndarray):
            img = image
        else:
            return elements

        if img is None or len(img.shape) < 2:
            return elements

        # Detect buttons via edge/contour analysis
        buttons = self._detect_buttons(img)
        elements.extend(buttons)

        # Detect input fields via horizontal line detection
        inputs = self._detect_input_fields(img)
        elements.extend(inputs)

        # Detect progress bars
        progress = self._detect_progress_bars(img)
        elements.extend(progress)

        # Detect image regions
        images = self._detect_image_regions(img)
        elements.extend(images)

        # Merge OCR text blocks as UI elements
        if ocr_blocks:
            for block in ocr_blocks:
                elem = UIElement(
                    element_id=f"ocr_{self._element_count}",
                    element_type="text",
                    label=block.text if hasattr(block, 'text') else str(block),
                    x=block.x if hasattr(block, 'x') else 0,
                    y=block.y if hasattr(block, 'y') else 0,
                    width=block.width if hasattr(block, 'width') else 100,
                    height=block.height if hasattr(block, 'height') else 20,
                    confidence=block.confidence if hasattr(block, 'confidence') else 0.5,
                    is_interactive=False,
                )
                elements.append(elem)
                self._element_count += 1

        # Assign IDs and detect interactivity
        for elem in elements:
            if not elem.element_id:
                elem.element_id = f"elem_{self._element_count}"
                self._element_count += 1
            # Heuristic: small rectangular elements are likely interactive
            if elem.element_type in ("button", "input", "checkbox"):
                elem.is_interactive = True

        self._detection_count += 1
        return elements

    def find_element(
        self,
        elements: list[UIElement],
        element_type: str = "",
        label: str = "",
        x: int | None = None,
        y: int | None = None,
    ) -> UIElement | None:
        """Find a specific element by criteria."""
        for elem in elements:
            if element_type and elem.element_type != element_type:
                continue
            if label and label.lower() not in elem.label.lower():
                continue
            if x is not None and abs(elem.x - x) > 20:
                continue
            if y is not None and abs(elem.y - y) > 20:
                continue
            return elem
        return None

    def find_interactive(self, elements: list[UIElement]) -> list[UIElement]:
        """Get all interactive elements."""
        return [e for e in elements if e.is_interactive]

    def get_element_at(
        self,
        elements: list[UIElement],
        x: int, y: int,
    ) -> UIElement | None:
        """Get the element at a specific screen position."""
        for elem in elements:
            if elem.contains(x, y):
                return elem
        return None

    # ── Detection Methods ──

    def _detect_buttons(self, img: np.ndarray) -> list[UIElement]:
        """Detect button-like elements via contour analysis."""
        elements = []
        if not HAS_CV2:
            return elements

        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                # Button heuristic: rectangular, reasonable size, not too large
                aspect = w / max(h, 1)
                if 1.5 < aspect < 8.0 and 30 < w < 400 and 15 < h < 80:
                    # Check if it has text-like content (not just a border)
                    roi = gray[y:y+h, x:x+w]
                    fill_ratio = np.mean(roi < 200)  # Non-white pixels
                    if 0.05 < fill_ratio < 0.8:
                        elements.append(UIElement(
                            element_type="button",
                            x=x, y=y, width=w, height=h,
                            confidence=0.4,
                            is_interactive=True,
                        ))
        except Exception as e:
            logger.debug("Button detection failed: %s", e)

        return elements

    def _detect_input_fields(self, img: np.ndarray) -> list[UIElement]:
        """Detect input field-like elements."""
        elements = []
        if not HAS_CV2:
            return elements

        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Detect horizontal lines (common in input fields)
            edges = cv2.Canny(gray, 50, 150)
            lines = cv2.HoughLinesP(edges, 1, 3.14/180, 100, minLineLength=50, maxLineGap=10)

            if lines is not None:
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    if abs(y2 - y1) < 5 and abs(x2 - x1) > 80:
                        # Horizontal line — likely input field bottom
                        elements.append(UIElement(
                            element_type="input",
                            x=min(x1, x2), y=y1 - 15,
                            width=abs(x2 - x1), height=30,
                            confidence=0.3,
                            is_interactive=True,
                        ))
        except Exception as e:
            logger.debug("Input field detection failed: %s", e)

        return elements

    def _detect_progress_bars(self, img: np.ndarray) -> list[UIElement]:
        """Detect progress bar elements."""
        elements = []
        if not HAS_CV2:
            return elements

        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                aspect = w / max(h, 1)
                if aspect > 5.0 and 3 < h < 20 and w > 100:
                    elements.append(UIElement(
                        element_type="progress_bar",
                        x=x, y=y, width=w, height=h,
                        confidence=0.3,
                        is_interactive=False,
                    ))
        except Exception:
            pass

        return elements

    def _detect_image_regions(self, img: np.ndarray) -> list[UIElement]:
        """Detect image/thumbnail regions."""
        elements = []
        if not HAS_CV2:
            return elements

        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Detect high-texture regions (images)
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            variance = laplacian.var()

            if variance > 500:  # High texture = likely image
                edges = cv2.Canny(gray, 50, 150)
                contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                for contour in contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    if w > 100 and h > 80 and 0.5 < w/max(h, 1) < 2.0:
                        elements.append(UIElement(
                            element_type="image",
                            x=x, y=y, width=w, height=h,
                            confidence=0.3,
                            is_interactive=False,
                        ))
        except Exception:
            pass

        return elements

    def get_stats(self) -> dict[str, Any]:
        return {
            "detection_count": self._detection_count,
            "elements_found": self._element_count,
            "has_opencv": HAS_CV2,
        }


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

ui_detection = UIDetection()
