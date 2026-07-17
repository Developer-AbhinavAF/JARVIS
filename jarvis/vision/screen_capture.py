"""Screen Capture — Fast screenshot capture using mss.

Target: <15ms per capture
Supports: Full screen, specific window, specific region, multi-monitor
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

try:
    import mss
    import mss.tools
    HAS_MSS = True
except ImportError:
    HAS_MSS = False
    logger.debug("mss not available, falling back to pyautogui")

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


# ════════════════════════════════════════════════════════════════════
# CAPTURE RESULT
# ════════════════════════════════════════════════════════════════════

@dataclass
class CaptureResult:
    """Result of a screen capture operation."""
    image: Any = None              # PIL Image or numpy array
    numpy_array: Any = None        # numpy array (BGR for OpenCV)
    width: int = 0
    height: int = 0
    monitor: int = 0               # 0=all, 1=primary, 2=secondary
    region: tuple[int, int, int, int] | None = None  # (x, y, w, h)
    capture_time_ms: float = 0.0
    timestamp: float = 0.0
    format: str = "numpy"          # numpy or pil

    def to_numpy(self) -> np.ndarray | None:
        """Get as numpy array (BGR format for OpenCV)."""
        if self.numpy_array is not None:
            return self.numpy_array
        if self.image is not None and HAS_PIL:
            arr = np.array(self.image)
            if len(arr.shape) == 3 and arr.shape[2] == 3:
                return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR) if HAS_CV2 else arr
            return arr
        return None

    def to_pil(self) -> Any:
        """Get as PIL Image."""
        if self.image is not None and HAS_PIL:
            return self.image
        if self.numpy_array is not None and HAS_PIL:
            if HAS_CV2:
                rgb = cv2.cvtColor(self.numpy_array, cv2.COLOR_BGR2RGB)
                return Image.fromarray(rgb)
            return Image.fromarray(self.numpy_array)
        return None

    def to_bytes(self, fmt: str = "png") -> bytes | None:
        """Get as bytes."""
        if not HAS_PIL:
            return None
        pil = self.to_pil()
        if pil:
            import io
            buf = io.BytesIO()
            pil.save(buf, format=fmt.upper())
            return buf.getvalue()
        return None


# ════════════════════════════════════════════════════════════════════
# SCREEN CAPTURE
# ════════════════════════════════════════════════════════════════════

class ScreenCapture:
    """Fast screen capture engine.

    Uses mss for maximum speed (<15ms target).
    Falls back to pyautogui if mss is unavailable.
    """

    def __init__(self) -> None:
        self._sct: Any = None
        self._last_capture: CaptureResult | None = None
        self._capture_count: int = 0
        self._monitor_count: int = 0
        self._init_capture()

    def _init_capture(self) -> None:
        """Initialize the capture backend."""
        if HAS_MSS:
            self._sct = mss.MSS()
            self._monitor_count = len(self._sct.monitors) - 1  # Subtract the "all monitors" entry
            logger.debug("Screen capture: mss initialized (%d monitors)", self._monitor_count)
        else:
            self._monitor_count = 1
            logger.debug("Screen capture: using pyautogui fallback")

    def capture(
        self,
        monitor: int = 1,
        region: tuple[int, int, int, int] | None = None,
    ) -> CaptureResult:
        """Capture screen.

        Args:
            monitor: Monitor index (1=primary, 2=secondary, 0=all).
            region: Specific region (x, y, width, height).

        Returns:
            CaptureResult with image data.
        """
        t0 = time.perf_counter()
        result = CaptureResult(monitor=monitor, region=region, timestamp=time.time())

        if HAS_MSS and self._sct:
            try:
                if region:
                    grab_region = {"left": region[0], "top": region[1],
                                   "width": region[2], "height": region[3]}
                elif monitor == 0:
                    grab_region = self._sct.monitors[0]  # All monitors
                else:
                    grab_region = self._sct.monitors[min(monitor, len(self._sct.monitors) - 1)]

                sct_img = self._sct.grab(grab_region)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                result.image = img
                result.numpy_array = np.array(img)[:, :, ::-1].copy()  # RGB to BGR
                result.width = sct_img.size[0]
                result.height = sct_img.size[1]
                result.format = "numpy"
            except Exception as e:
                logger.warning("mss capture failed: %s, falling back", e)
                self._capture_fallback(result)
        else:
            self._capture_fallback(result)

        result.capture_time_ms = (time.perf_counter() - t0) * 1000
        self._last_capture = result
        self._capture_count += 1
        return result

    def capture_window(
        self,
        title: str | None = None,
        hwnd: int | None = None,
    ) -> CaptureResult:
        """Capture a specific window by title or handle."""
        import pygetwindow as gw

        t0 = time.perf_counter()
        result = CaptureResult(timestamp=time.time())

        try:
            if title:
                windows = gw.getWindowsWithTitle(title)
                if not windows:
                    logger.warning("Window not found: %s", title)
                    return self.capture()
                win = windows[0]
            elif hwnd:
                win = gw.Window(hwnd=hwnd)
            else:
                return self.capture()

            # Get window bounds
            if win.isMinimized:
                win.restore()
            win.activate()
            time.sleep(0.05)  # Brief wait for window to come to front

            region = (win.left, win.top, win.width, win.height)
            result = self.capture(region=region)
            result.region = region

        except Exception as e:
            logger.warning("Window capture failed: %s", e)
            result = self.capture()

        result.capture_time_ms = (time.perf_counter() - t0) * 1000
        return result

    def capture_region(
        self,
        x: int, y: int,
        width: int, height: int,
    ) -> CaptureResult:
        """Capture a specific screen region."""
        return self.capture(region=(x, y, width, height))

    def get_monitor_info(self) -> list[dict[str, Any]]:
        """Get information about all monitors."""
        monitors = []
        if HAS_MSS and self._sct:
            for i, m in enumerate(self._sct.monitors):
                if i == 0:
                    continue  # Skip the "all monitors" entry
                monitors.append({
                    "index": i,
                    "left": m["left"],
                    "top": m["top"],
                    "width": m["width"],
                    "height": m["height"],
                    "is_primary": i == 1,
                })
        else:
            monitors.append({"index": 1, "left": 0, "top": 0,
                           "width": 1920, "height": 1080, "is_primary": True})
        return monitors

    def _capture_fallback(self, result: CaptureResult) -> None:
        """Fallback capture using pyautogui."""
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            result.image = screenshot
            result.numpy_array = np.array(screenshot)[:, :, ::-1].copy()
            result.width = screenshot.width
            result.height = screenshot.height
            result.format = "numpy"
        except Exception as e:
            logger.error("All capture methods failed: %s", e)

    def get_last_capture(self) -> CaptureResult | None:
        return self._last_capture

    def get_stats(self) -> dict[str, Any]:
        avg_ms = 0.0
        if self._last_capture:
            avg_ms = self._last_capture.capture_time_ms
        return {
            "capture_count": self._capture_count,
            "monitor_count": self._monitor_count,
            "backend": "mss" if HAS_MSS else "pyautogui",
            "last_capture_ms": round(avg_ms, 1),
        }


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

screen_capture = ScreenCapture()
