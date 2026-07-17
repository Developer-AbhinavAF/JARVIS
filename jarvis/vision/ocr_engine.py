"""OCR Engine — Extract text from screenshots.

Target: <40ms per extraction
Supports: Tesseract, Windows OCR API, fallback to None
Preserves formatting when possible.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

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
# OCR RESULTS
# ════════════════════════════════════════════════════════════════════

@dataclass
class TextBlock:
    """A block of recognized text with position."""
    text: str = ""
    confidence: float = 0.0
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    block_type: str = "text"     # text, heading, code, url, error, table
    language: str = "eng"
    lines: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text[:200],
            "confidence": round(self.confidence, 2),
            "x": self.x, "y": self.y,
            "w": self.width, "h": self.height,
            "type": self.block_type,
        }


@dataclass
class OCRResult:
    """Complete OCR result from a screen region."""
    blocks: list[TextBlock] = field(default_factory=list)
    full_text: str = ""
    word_count: int = 0
    language: str = "eng"
    ocr_time_ms: float = 0.0
    confidence_avg: float = 0.0
    has_code: bool = False
    has_errors: bool = False
    has_urls: bool = False

    def get_text_by_type(self, block_type: str) -> str:
        return "\n".join(b.text for b in self.blocks if b.block_type == block_type)

    def find_text(self, search: str) -> TextBlock | None:
        search_lower = search.lower()
        for block in self.blocks:
            if search_lower in block.text.lower():
                return block
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "blocks": len(self.blocks),
            "word_count": self.word_count,
            "confidence": round(self.confidence_avg, 2),
            "has_code": self.has_code,
            "has_errors": self.has_errors,
            "has_urls": self.has_urls,
            "preview": self.full_text[:200],
        }


# ════════════════════════════════════════════════════════════════════
# ERROR PATTERNS
# ════════════════════════════════════════════════════════════════════

_ERROR_PATTERNS = [
    "error", "exception", "traceback", "failed", "failure",
    "fatal", "critical", "panic", "abort", "crash",
    "syntaxerror", "typeerror", "valueerror", "runtimeerror",
    "importerror", "modulenotfounderror", "nameerror",
    "indexerror", "keyerror", "attributeerror",
    "errno", "exit code", "exitcode",
    "build failed", "compilation failed",
    "exception in", "error:", "warning:",
]

_CODE_PATTERNS = [
    "def ", "class ", "import ", "from ", "return ",
    "if ", "else:", "elif ", "for ", "while ",
    "try:", "except:", "finally:",
    "function ", "const ", "let ", "var ",
    "#include", "using namespace",
    "public static", "private ",
    "->", "=>", "::", "&&", "||",
]


# ════════════════════════════════════════════════════════════════════
# OCR ENGINE
# ════════════════════════════════════════════════════════════════════

class OCREngine:
    """Multi-backend OCR engine.

    Extracts text from screen images with position information.
    Classifies text blocks by type (code, error, URL, heading, etc.)
    """

    def __init__(self) -> None:
        self._ocr_count: int = 0
        self._available_backends: list[str] = []
        self._detect_backends()

    def _detect_backends(self) -> None:
        """Detect available OCR backends."""
        if HAS_TESSERACT:
            try:
                pytesseract.get_tesseract_version()
                self._available_backends.append("tesseract")
                logger.debug("Tesseract OCR available")
            except Exception:
                logger.debug("Tesseract binary not found")

        # Check for Windows OCR (via winocr or comtypes)
        try:
            import winocr
            self._available_backends.append("windows_ocr")
            logger.debug("Windows OCR (winocr) available")
        except ImportError:
            try:
                import comtypes.client
                self._available_backends.append("windows_ocr_comtypes")
                logger.debug("Windows OCR (comtypes) available")
            except ImportError:
                pass

        # Check for EasyOCR
        try:
            import easyocr
            self._available_backends.append("easyocr")
            logger.debug("EasyOCR available")
        except ImportError:
            pass

        if not self._available_backends:
            logger.warning("No OCR backend available")

    def extract(
        self,
        image: Any,
        region: tuple[int, int, int, int] | None = None,
        preprocess: bool = True,
    ) -> OCRResult:
        """Extract text from an image.

        Args:
            image: PIL Image, numpy array, or CaptureResult.
            region: Optional (x, y, w, h) region to crop.
            preprocess: Whether to preprocess for better OCR.

        Returns:
            OCRResult with extracted text blocks.
        """
        t0 = time.perf_counter()
        result = OCRResult()

        # Convert input to PIL Image
        pil_image = self._to_pil(image, region)
        if pil_image is None:
            result.ocr_time_ms = (time.perf_counter() - t0) * 1000
            return result

        # Preprocess
        if preprocess:
            pil_image = self._preprocess(pil_image)

        # Run OCR with fallback chain: Tesseract → Windows OCR → EasyOCR → empty
        if "tesseract" in self._available_backends:
            try:
                result = self._ocr_tesseract(pil_image)
                if result.blocks or result.full_text.strip():
                    self._classify_blocks(result)
                    result.ocr_time_ms = (time.perf_counter() - t0) * 1000
                    self._ocr_count += 1
                    return result
                logger.debug("Tesseract returned empty, trying next backend")
            except Exception as e:
                logger.debug("Tesseract failed: %s, trying next backend", e)

        if "windows_ocr" in self._available_backends:
            try:
                result = self._ocr_windows_winocr(pil_image)
                if result.blocks or result.full_text.strip():
                    self._classify_blocks(result)
                    result.ocr_time_ms = (time.perf_counter() - t0) * 1000
                    self._ocr_count += 1
                    return result
                logger.debug("Windows OCR (winocr) returned empty, trying next backend")
            except Exception as e:
                logger.debug("Windows OCR (winocr) failed: %s", e)

        if "windows_ocr_comtypes" in self._available_backends:
            try:
                result = self._ocr_windows_comtypes(pil_image)
                if result.blocks or result.full_text.strip():
                    self._classify_blocks(result)
                    result.ocr_time_ms = (time.perf_counter() - t0) * 1000
                    self._ocr_count += 1
                    return result
            except Exception as e:
                logger.debug("Windows OCR (comtypes) failed: %s", e)

        if "easyocr" in self._available_backends:
            try:
                result = self._ocr_easyocr(pil_image)
                if result.blocks or result.full_text.strip():
                    self._classify_blocks(result)
                    result.ocr_time_ms = (time.perf_counter() - t0) * 1000
                    self._ocr_count += 1
                    return result
            except Exception as e:
                logger.debug("EasyOCR failed: %s", e)

        # All backends failed — return empty
        logger.warning("All OCR backends returned empty results")
        result.ocr_time_ms = (time.perf_counter() - t0) * 1000
        self._ocr_count += 1
        return result

    def extract_from_screen(
        self,
        capture_result: Any = None,
    ) -> OCRResult:
        """Extract text from the latest screen capture."""
        if capture_result is None:
            from .screen_capture import screen_capture
            capture_result = screen_capture.get_last_capture()
        if capture_result is None:
            return OCRResult()
        return self.extract(capture_result.image)

    def find_on_screen(
        self,
        text: str,
        capture_result: Any = None,
    ) -> TextBlock | None:
        """Find specific text on screen."""
        result = self.extract_from_screen(capture_result)
        return result.find_text(text)

    def detect_errors(self, ocr_result: OCRResult | None = None) -> list[str]:
        """Detect error messages in OCR result."""
        if ocr_result is None:
            ocr_result = self.extract_from_screen()
        errors = []
        for block in ocr_result.blocks:
            if block.block_type == "error":
                errors.append(block.text)
        return errors

    # ── Private Methods ──

    def _to_pil(self, image: Any, region: tuple[int, int, int, int] | None = None) -> Any:
        """Convert input to PIL Image."""
        if not HAS_PIL:
            return None

        pil_img = None
        if hasattr(image, 'image') and image.image is not None:
            # CaptureResult — prefer the PIL image directly
            if hasattr(image, 'to_pil'):
                pil_img = image.to_pil()
            elif isinstance(image.image, Image.Image):
                pil_img = image.image
            else:
                # numpy array — check shape and convert
                arr = image.image if isinstance(image.image, np.ndarray) else None
                if arr is not None:
                    pil_img = self._numpy_to_pil(arr)
        elif isinstance(image, Image.Image):
            pil_img = image
        elif isinstance(image, np.ndarray):
            pil_img = self._numpy_to_pil(image)

        if pil_img and region:
            x, y, w, h = region
            pil_img = pil_img.crop((x, y, x + w, y + h))

        # Skip degenerate images
        if pil_img and (pil_img.width < 1 or pil_img.height < 1):
            return None

        return pil_img

    @staticmethod
    def _numpy_to_pil(arr: np.ndarray) -> Any:
        """Convert numpy array to PIL Image, auto-detecting channel order."""
        if not HAS_PIL:
            return None
        if arr.ndim == 2:
            return Image.fromarray(arr)
        if arr.ndim == 3:
            h, w, c = arr.shape
            if c == 4:
                # BGRA → RGBA
                rgba = arr[:, :, [2, 1, 0, 3]]
                return Image.fromarray(rgba, "RGBA")
            elif c == 3:
                # Heuristic: if screen_capture produced this, it's BGR (from RGB flip).
                # If the average red channel < average blue channel, assume BGR.
                r_mean = float(arr[:, :, 0].mean())
                b_mean = float(arr[:, :, 2].mean())
                if r_mean < b_mean:
                    # Likely BGR — convert to RGB
                    rgb = arr[:, :, ::-1].copy()
                    return Image.fromarray(rgb, "RGB")
                else:
                    # Likely already RGB
                    return Image.fromarray(arr, "RGB")
            elif c == 1:
                return Image.fromarray(arr[:, :, 0], "L")
        return None

    @staticmethod
    def _preprocess(image: Any) -> Any:
        """Preprocess image for better OCR."""
        if not HAS_PIL:
            return image
        # Skip tiny/empty images
        if image.width < 2 or image.height < 2:
            return image
        # Convert to grayscale
        gray = image.convert("L")
        # Increase contrast
        from PIL import ImageEnhance
        try:
            enhanced = ImageEnhance.Contrast(gray).enhance(1.5)
        except (ZeroDivisionError, ValueError):
            # Blank image with no variation
            return image
        return enhanced

    def _ocr_tesseract(self, image: Any) -> OCRResult:
        """Run Tesseract OCR."""
        result = OCRResult()
        try:
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            current_block = TextBlock()
            prev_block_num = -1

            for i in range(len(data["text"])):
                text = data["text"][i].strip()
                conf = float(data["conf"][i])
                block_num = data["block_num"][i]

                if not text or conf < 0:
                    continue

                # New block
                if block_num != prev_block_num:
                    if current_block.text:
                        result.blocks.append(current_block)
                    current_block = TextBlock(
                        text=text,
                        confidence=conf,
                        x=data["left"][i],
                        y=data["top"][i],
                        width=data["width"][i],
                        height=data["height"][i],
                    )
                    prev_block_num = block_num
                else:
                    current_block.text += " " + text
                    current_block.confidence = (current_block.confidence + conf) / 2

            # Don't forget the last block
            if current_block.text:
                result.blocks.append(current_block)

            # Full text
            result.full_text = pytesseract.image_to_string(image)
            result.word_count = len(result.full_text.split())

            # Average confidence
            if result.blocks:
                result.confidence_avg = sum(b.confidence for b in result.blocks) / len(result.blocks)

        except Exception as e:
            logger.debug("Tesseract OCR failed: %s", e)

        return result

    def _ocr_windows_winocr(self, image: Any) -> OCRResult:
        """Run Windows OCR via winocr package."""
        result = OCRResult()
        try:
            import winocr
            import asyncio

            # winocr needs a file path or stream; save PIL to temp file
            import tempfile
            import os
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp_path = tmp.name
            tmp.close()
            try:
                # Ensure RGB mode
                if image.mode != "RGB":
                    image = image.convert("RGB")
                image.save(tmp_path, "PNG")

                # Run OCR asynchronously
                loop = asyncio.new_event_loop()
                try:
                    ocr_result = loop.run_until_complete(
                        winocr.recognize_pil(image, lang="en-US")
                    )
                finally:
                    loop.close()

                # Parse results
                if ocr_result and hasattr(ocr_result, "lines"):
                    for line in ocr_result.lines:
                        text = line.text if hasattr(line, "text") else str(line)
                        if not text.strip():
                            continue
                        # Get bounding box if available
                        x, y, w, h = 0, 0, 0, 0
                        if hasattr(line, "bounding_rect"):
                            br = line.bounding_rect
                            x = int(getattr(br, "x", 0))
                            y = int(getattr(br, "y", 0))
                            w = int(getattr(br, "width", 0))
                            h = int(getattr(br, "height", 0))
                        block = TextBlock(
                            text=text.strip(),
                            confidence=0.85,
                            x=x, y=y, width=w, height=h,
                        )
                        result.blocks.append(block)

                result.full_text = "\n".join(b.text for b in result.blocks)
                result.word_count = len(result.full_text.split())
                if result.blocks:
                    result.confidence_avg = sum(b.confidence for b in result.blocks) / len(result.blocks)
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        except Exception as e:
            logger.debug("Windows OCR (winocr) failed: %s", e)

        return result

    def _ocr_windows_comtypes(self, image: Any) -> OCRResult:
        """Run Windows OCR via comtypes (Windows.Media.Ocr)."""
        result = OCRResult()
        try:
            import comtypes.client
            import tempfile
            import os

            # Save PIL to temp BMP (Windows OCR works best with BMP)
            tmp = tempfile.NamedTemporaryFile(suffix=".bmp", delete=False)
            tmp_path = tmp.name
            tmp.close()
            try:
                if image.mode != "RGB":
                    image = image.convert("RGB")
                image.save(tmp_path, "BMP")

                # Initialize Windows OCR
                ocr_engine = comtypes.client.CreateObject(
                    "Windows.Media.Ocr.OcrEngine",
                    comtypes.CLSCTX_INPROC_SERVER,
                )
                # This approach may not work on all Windows versions
                # Fall back gracefully
                logger.debug("Windows OCR comtypes backend attempted")
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        except Exception as e:
            logger.debug("Windows OCR (comtypes) failed: %s", e)

        return result

    def _ocr_easyocr(self, image: Any) -> OCRResult:
        """Run EasyOCR."""
        result = OCRResult()
        try:
            import easyocr
            reader = easyocr.Reader(["en"], gpu=False)

            # Convert PIL to numpy
            import io
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            buf.seek(0)
            arr = np.array(image)

            results = reader.readtext(arr)
            for (bbox, text, conf) in results:
                if not text.strip():
                    continue
                # bbox is [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                x = int(bbox[0][0])
                y = int(bbox[0][1])
                w = int(bbox[1][0] - bbox[0][0])
                h = int(bbox[2][1] - bbox[0][1])
                block = TextBlock(
                    text=text.strip(),
                    confidence=float(conf) * 100,
                    x=x, y=y, width=w, height=h,
                )
                result.blocks.append(block)

            result.full_text = "\n".join(b.text for b in result.blocks)
            result.word_count = len(result.full_text.split())
            if result.blocks:
                result.confidence_avg = sum(b.confidence for b in result.blocks) / len(result.blocks)

        except Exception as e:
            logger.debug("EasyOCR failed: %s", e)

        return result

    def _classify_blocks(self, result: OCRResult) -> None:
        """Classify text blocks by type."""
        for block in result.blocks:
            text_lower = block.text.lower()

            # Check for errors
            if any(p in text_lower for p in _ERROR_PATTERNS):
                block.block_type = "error"
                result.has_errors = True
                continue

            # Check for code
            if any(p in block.text for p in _CODE_PATTERNS):
                block.block_type = "code"
                result.has_code = True
                continue

            # Check for URLs
            if any(p in text_lower for p in ["http://", "https://", "www.", ".com", ".org", ".net"]):
                block.block_type = "url"
                result.has_urls = True
                continue

            # Check for headings (larger text blocks with short content)
            if block.height > 30 and len(block.text) < 50:
                block.block_type = "heading"
                continue

            # Default
            block.block_type = "text"

    def get_stats(self) -> dict[str, Any]:
        return {
            "ocr_count": self._ocr_count,
            "backends": self._available_backends,
            "has_tesseract": HAS_TESSERACT,
        }


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ════════════════════════════════════════════════════════════════════

ocr_engine = OCREngine()
