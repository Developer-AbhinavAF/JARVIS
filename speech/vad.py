"""speech/vad.py — Voice Activity Detection.

Chain: Silero VAD (primary) -> WebRTC VAD -> energy VAD.

Only detects speech presence per frame; speech recognition runs strictly
after VAD confirms speech completion (see endpoint_detector.py).
"""

from __future__ import annotations

import io
import math
import threading
import urllib.request
from typing import Optional

import numpy as np

from speech.config import cfg
from speech.logger import get_logger

logger = get_logger("vad")


def _ensure_pkg_resources_stub() -> None:
    """webrtcvad imports pkg_resources; some envs lack setuptools. Provide a stub."""
    import sys, importlib.util
    if "pkg_resources" in sys.modules:
        return
    if importlib.util.find_spec("pkg_resources") is None:
        import types
        stub = types.ModuleType("pkg_resources")
        stub.require = lambda *a, **kw: []
        stub.get_distribution = lambda *a, **kw: types.SimpleNamespace(version="0")
        sys.modules["pkg_resources"] = stub


class BaseVAD:
    name = "base"

    def process(self, frame: np.ndarray) -> float:
        raise NotImplementedError

    def reset(self) -> None:
        pass


class EnergyVAD(BaseVAD):
    """Adaptive energy VAD — last-resort fallback."""

    name = "energy"

    def __init__(self, threshold: float = 0.02) -> None:
        self._threshold = threshold
        self._noise_floor = 0.01

    def process(self, frame: np.ndarray) -> float:
        rms = float(np.sqrt(np.mean(frame.astype(np.float32) ** 2) + 1e-9))
        self._noise_floor = 0.98 * self._noise_floor + 0.02 * min(rms, self._noise_floor * 2.0 + 0.005)
        level = rms / max(self._noise_floor + self._threshold, 1e-6)
        return float(np.clip((level - 1.0) / 2.0, 0.0, 1.0))


class WebRTCVAD(BaseVAD):
    """webrtcvad wrapper (returns hard 0/1, smoothed)."""

    name = "webrtc"

    def __init__(self, aggressiveness: int = 2) -> None:
        _ensure_pkg_resources_stub()
        import webrtcvad
        self._vad = webrtcvad.Vad(aggressiveness)
        self._frame_bytes = cfg.sample_rate // 1000 * cfg.frame_ms * 2
        self._smoothed = 0.0

    def process(self, frame: np.ndarray) -> float:
        pcm = (np.clip(frame, -1.0, 1.0) * 32767).astype(np.int16)
        if pcm.nbytes != self._frame_bytes:
            pcm = pcm[: self._frame_bytes // 2]
            if pcm.nbytes != self._frame_bytes:
                return self._smoothed
        try:
            speech = self._vad.is_speech(pcm.tobytes(), cfg.sample_rate)
        except Exception:
            return self._smoothed
        self._smoothed = 0.9 * self._smoothed + 0.1 * (1.0 if speech else 0.0)
        return self._smoothed

    def reset(self) -> None:
        self._smoothed = 0.0


class SileroVAD(BaseVAD):
    """Silero VAD v5 via onnxruntime (512-sample frames @16 kHz)."""

    name = "silero"

    def __init__(self, model_path: Optional[str] = None) -> None:
        self._session = None
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros(512, dtype=np.float32)
        self._sr = np.array(16000, dtype=np.int64)
        self._sr_epoch = 0
        self._load(model_path or cfg.silero_model_path)

    def _load(self, path) -> None:
        try:
            import onnxruntime as ort
        except ImportError as e:
            raise RuntimeError("onnxruntime not installed") from e
        if not path or not getattr(path, "exists", lambda: False)():
            raise FileNotFoundError(
                f"Silero model not found at {path}. "
                f"Download it: python -m speech.vad"
            )
        self._session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])

    def process(self, frame: np.ndarray) -> float:
        if self._session is None:
            return 0.0
        # Silero expects exactly 512 samples; pad 32ms frames with context.
        if len(frame) < 512:
            padded = np.concatenate([self._context, frame])
            self._context = padded[-512:]
            input_frame = padded
        else:
            input_frame = frame[:512]
        audio = np.expand_dims(input_frame.astype(np.float32), axis=0)
        try:
            (prob,), self._state = self._session.run(
                ["output", "state"],
                {
                    "input": audio,
                    "state": self._state,
                    "sr": self._sr,
                },
            )
        except Exception:
            return 0.0
        self._sr_epoch += 1
        return float(prob)

    def reset(self) -> None:
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros(512, dtype=np.float32)


class CompositeVAD:
    """Best available VAD: Silero -> WebRTC -> energy."""

    def __init__(self) -> None:
        self._provider = None
        self._fallbacks: list[BaseVAD] = []
        self._lock = threading.Lock()
        self._init()

    def _init(self) -> None:
        try:
            self._provider = SileroVAD()
            logger.info("VAD: Silero (onnx) active")
            return
        except Exception as e:
            logger.info("Silero unavailable (%s); trying WebRTC", e.__class__.__name__)
        try:
            self._provider = WebRTCVAD()
            self._fallbacks = [EnergyVAD()]
            logger.info("VAD: WebRTC active (fallback: energy)")
            return
        except Exception as e:
            logger.info("WebRTC unavailable (%s); using energy VAD", e.__class__.__name__)
        self._provider = EnergyVAD()
        logger.info("VAD: energy active")

    @property
    def name(self) -> str:
        return self._provider.name

    def process(self, frame: np.ndarray) -> float:
        with self._lock:
            prob = self._provider.process(frame)
            if prob > 0.05 or not self._fallbacks:
                return prob
            return max(prob, max(fb.process(frame) for fb in self._fallbacks))

    def reset(self) -> None:
        with self._lock:
            self._provider.reset()
            for fb in self._fallbacks:
                fb.reset()


def download_silero_model(path=None, url: Optional[str] = None) -> bool:
    """Fetch the Silero VAD ONNX model (small, ~2 MB)."""
    dest = path or cfg.silero_model_path
    dest = dest if isinstance(dest, str) else str(dest)
    if __import__("os").path.exists(dest):
        return True
    src = url or cfg.silero_url
    logger.info("Downloading Silero VAD from %s ...", src)
    try:
        urllib.request.urlretrieve(src, dest)
        return True
    except Exception as e:
        logger.error("Silero download failed: %s", e)
        return False


vad = CompositeVAD()


if __name__ == "__main__":
    download_silero_model()
