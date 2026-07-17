"""Layout Analyzer — Understand screen layout structure.

Analyze the spatial arrangement of windows and UI elements.
Build a hierarchical understanding of the screen.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# LAYOUT REGION
# ════════════════════════════════════════════════════════════════════

@dataclass
class LayoutRegion:
    """A region of the screen with semantic meaning."""
    region_type: str = "unknown"   # toolbar, sidebar, content, statusbar, etc.
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    elements: list[str] = field(default_factory=list)  # Element IDs
    children: list[str] = field(default_factory=list)   # Child region IDs
    confidence: float = 0.5

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    def overlaps(self, other: "LayoutRegion") -> bool:
        return not (self.x + self.width < other.x or other.x + other.width < self.x
                    or self.y + self.height < other.y or other.y + other.height < self.y)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.region_type,
            "x": self.x, "y": self.y,
            "w": self.width, "h": self.height,
            "elements": len(self.elements),
            "children": len(self.children),
        }


# ════════════════════════════════════════════════════════════════════
# LAYOUT ANALYZER
# ════════════════════════════════════════════════════════════════════

class LayoutAnalyzer:
    """Analyzes screen layout structure.

    Divides the screen into semantic regions:
    - Toolbar/menu bar (top)
    - Sidebar (left/right)
    - Content area (center)
    - Status bar (bottom)
    - Dialogs/popups (floating)
    """

    def __init__(self) -> None:
        self._analysis_count: int = 0

    def analyze(
        self,
        elements: list[Any],
        window_width: int = 1920,
        window_height: int = 1080,
    ) -> list[LayoutRegion]:
        """Analyze the layout of UI elements.

        Returns a list of LayoutRegion objects describing the screen structure.
        """
        regions: list[LayoutRegion] = []

        if not elements:
            return regions

        # Classify elements into regions
        toolbar_elems = []
        sidebar_elems = []
        content_elems = []
        statusbar_elems = []
        floating_elems = []

        for elem in elements:
            ey = getattr(elem, 'y', 0)
            ex = getattr(elem, 'x', 0)
            ew = getattr(elem, 'width', 0)
            eh = getattr(elem, 'height', 0)

            # Top area — toolbar/menu
            if ey < 50 and eh < 60:
                toolbar_elems.append(elem)
            # Bottom area — status bar
            elif ey > window_height - 50 and eh < 50:
                statusbar_elems.append(elem)
            # Left sidebar
            elif ex < 250 and ew < 350:
                sidebar_elems.append(elem)
            # Right sidebar
            elif ex > window_width - 250 and ew < 350:
                sidebar_elems.append(elem)
            # Content
            else:
                content_elems.append(elem)

        # Build regions
        if toolbar_elems:
            regions.append(self._build_region("toolbar", toolbar_elems))
        if sidebar_elems:
            regions.append(self._build_region("sidebar", sidebar_elems))
        if content_elems:
            regions.append(self._build_region("content", content_elems))
        if statusbar_elems:
            regions.append(self._build_region("statusbar", statusbar_elems))

        self._analysis_count += 1
        return regions

    def detect_overlays(self, elements: list[Any]) -> list[LayoutRegion]:
        """Detect floating overlays (dialogs, popups)."""
        overlays = []
        if not elements:
            return overlays

        # Find elements that overlap many others (likely overlay)
        for elem in elements:
            overlaps = 0
            ex, ey = getattr(elem, 'x', 0), getattr(elem, 'y', 0)
            ew, eh = getattr(elem, 'width', 0), getattr(elem, 'height', 0)

            if ew < 100 or eh < 50:
                continue

            for other in elements:
                if other is elem:
                    continue
                ox, oy = getattr(other, 'x', 0), getattr(other, 'y', 0)
                ow, oh = getattr(other, 'width', 0), getattr(other, 'height', 0)
                # Check if 'other' is inside 'elem'
                if ex < ox and ey < oy and ex + ew > ox + ow and ey + eh > oy + oh:
                    overlaps += 1

            if overlaps > 3:
                overlays.append(LayoutRegion(
                    region_type="overlay",
                    x=ex, y=ey, width=ew, height=eh,
                    confidence=0.5,
                ))

        return overlays

    def describe_layout(self, regions: list[LayoutRegion]) -> str:
        """Generate a natural language description of the layout."""
        if not regions:
            return "No layout structure detected"

        parts = []
        for r in regions:
            if r.region_type == "toolbar":
                parts.append("a toolbar at the top")
            elif r.region_type == "sidebar":
                parts.append("a sidebar on the side")
            elif r.region_type == "content":
                parts.append("a main content area")
            elif r.region_type == "statusbar":
                parts.append("a status bar at the bottom")
            elif r.region_type == "overlay":
                parts.append("a popup/dialog overlay")

        return "Screen contains " + ", ".join(parts) if parts else "Layout analyzed"

    @staticmethod
    def _build_region(region_type: str, elements: list[Any]) -> LayoutRegion:
        if not elements:
            return LayoutRegion(region_type=region_type)

        xs = [getattr(e, 'x', 0) for e in elements]
        ys = [getattr(e, 'y', 0) for e in elements]
        x2 = [getattr(e, 'x', 0) + getattr(e, 'width', 0) for e in elements]
        y2 = [getattr(e, 'y', 0) + getattr(e, 'height', 0) for e in elements]

        return LayoutRegion(
            region_type=region_type,
            x=min(xs), y=min(ys),
            width=max(x2) - min(xs),
            height=max(y2) - min(ys),
            elements=[getattr(e, 'element_id', '') for e in elements],
        )

    def get_stats(self) -> dict[str, Any]:
        return {"analysis_count": self._analysis_count}


layout_analyzer = LayoutAnalyzer()
