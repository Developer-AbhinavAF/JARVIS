"""vision — Screen capture, OCR, and visual analysis.

Minimal dependencies. Graceful fallbacks.
"""

from __future__ import annotations

import time
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class VisionEngine:
    def __init__(self) -> None:
        self._capture_count = 0

    def capture_screen(self, region: tuple[int, int, int, int] | None = None) -> dict[str, Any]:
        try:
            import pyautogui
            screenshot = pyautogui.screenshot(region=region)
            ss_dir = Path.home() / "Pictures" / "JARVIS"
            ss_dir.mkdir(parents=True, exist_ok=True)
            path = ss_dir / f"vision_capture_{int(time.time())}.png"
            screenshot.save(str(path))
            self._capture_count += 1
            return {"success": True, "path": str(path), "width": screenshot.width, "height": screenshot.height}
        except ImportError:
            try:
                import PIL.ImageGrab
                screenshot = PIL.ImageGrab.grab(bbox=region)
                ss_dir = Path.home() / "Pictures" / "JARVIS"
                ss_dir.mkdir(parents=True, exist_ok=True)
                path = ss_dir / f"vision_capture_{int(time.time())}.png"
                screenshot.save(str(path))
                return {"success": True, "path": str(path), "width": screenshot.width, "height": screenshot.height}
            except ImportError:
                return {"success": False, "error": "Cannot capture screen. Install pyautogui or Pillow."}

    def ocr(self, image_path: str = "") -> dict[str, Any]:
        try:
            import pytesseract
            from PIL import Image
            if not image_path:
                capture = self.capture_screen()
                if not capture.get("success"):
                    return {"success": False, "error": "Could not capture screen"}
                image_path = capture["path"]
            text = pytesseract.image_to_string(Image.open(image_path))
            return {"success": True, "text": text.strip(), "source": image_path}
        except ImportError:
            return {"success": False, "error": "pytesseract not available. Install pytesseract and tesseract-ocr."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def analyze_screen(self, prompt: str = "Describe the contents of this screen.") -> dict[str, Any]:
        capture = self.capture_screen()
        if not capture.get("success"):
            return capture
        image_path = capture["path"]
        
        # Try LLM first
        try:
            import base64
            from core.router import router
            import asyncio
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
            
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        future = pool.submit(asyncio.run, router.chat(messages))
                        result = future.result(timeout=30)
                else:
                    result = loop.run_until_complete(router.chat(messages))
            except RuntimeError:
                result = asyncio.run(router.chat(messages))

            if result.success and result.content:
                return {
                    "success": True,
                    "capture": capture,
                    "analysis": result.content,
                    "method": "llm",
                }
        except Exception as e:
            logger.debug("LLM vision analysis failed: %s", e)

        # Fallback to OCR
        ocr_result = self.ocr(image_path)
        return {
            "success": True,
            "capture": capture,
            "ocr": ocr_result.get("text", "") if ocr_result.get("success") else "",
            "method": "ocr",
        }

    def get_stats(self) -> dict[str, Any]:
        return {"capture_count": self._capture_count}


vision_engine = VisionEngine()
