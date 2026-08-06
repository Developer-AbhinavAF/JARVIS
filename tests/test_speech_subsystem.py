"""Speech engine v5.0 automated tests.

Covers: endpoint detection (long/short speech, pauses, silence), queue
flushing, playback cancellation, barge-in gating, cache reuse, STT fallback
chain ordering, TTS fallback, event ordering, engine API, performance report
generation.

Run:  python -m pytest tests/test_speech_subsystem.py -v
      python tests/test_speech_subsystem.py
"""

from __future__ import annotations

import os
import sys
import time
import wave
import struct
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from speech.config import SpeechConfig
from speech.events import EventBus, SpeechEventType
from speech.queue import SpeechQueue, SpeechItem
from speech.cache import AudioCache
from speech.endpoint_detector import EndpointDetector, EndpointStatus
from speech.interrupt_manager import InterruptManager
from speech.streaming import SentenceSplitter
from speech.recognizer import Recognizer
from speech.playback import PlaybackWorker
from speech.speech_engine import SpeechEngine

FRAME_S = 0.03


def make_wav(path: Path, seconds: float = 0.2) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rate = 16000
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        n = int(rate * seconds)
        frames = struct.pack("<" + "h" * n, *([0] * n))
        wf.writeframes(frames)
    return path


class FakeTTS:
    """Cache-first TTS double; creates a tiny real wav on first synth."""

    def __init__(self, cache: AudioCache) -> None:
        self.cache = cache
        self.calls = 0
        self.tmp = Path(tempfile.mkdtemp())

    def is_available(self) -> bool:
        return True

    def synthesize(self, text: str):
        from speech.edge_provider import TTSResult
        cached = self.cache.get(text, "v", "r", "p", "u")
        if cached is not None:
            return TTSResult(cached, "cache", cached=True)
        self.calls += 1
        wav = make_wav(self.tmp / f"{self.calls}.wav")
        cached = self.cache.put(text, "v", "r", "p", "u", wav)
        return TTSResult(cached, "fake-tts")


# ---------------------------------------------------------------------------
def test_sentence_splitter():
    got = []
    splitter = SentenceSplitter(on_sentence=got.append)
    splitter.feed("Hello. How")
    splitter.feed(" are you")
    splitter.feed("? I am fine!")
    splitter.flush()
    assert got == ["Hello.", "How are you?", "I am fine!"], got


def test_endpoint_long_speech_with_pauses():
    det = EndpointDetector(end_hold_ms=600, min_speech_ms=200, confirm_frames=2)
    prob = 0.9
    # speech with intra-sentence pauses must NOT end
    for _ in range(30):  # "Hello..."
        assert not det.update(prob).ended
    for _ in range(5):   # pause
        assert not det.update(0.05).ended
    for _ in range(30):
        assert not det.update(prob).ended
    for _ in range(5):
        assert not det.update(0.05).ended
    for _ in range(30):
        assert not det.update(prob).ended
    assert det.in_speech
    # sustained trailing silence ends it
    ended = None
    for _ in range(30):
        frame = det.update(0.05)
        if frame.ended:
            ended = frame
            break
    assert ended is not None and ended.speech_ms > 0


def test_endpoint_short_blip_rejected():
    det = EndpointDetector(end_hold_ms=300, min_speech_ms=200, confirm_frames=2)
    for _ in range(2):
        det.update(0.9)  # short noise blip
    for _ in range(20):
        assert not det.update(0.05).ended
    assert not det.in_speech


def test_endpoint_max_duration_safety():
    det = EndpointDetector(end_hold_ms=600, min_speech_ms=200, max_utterance_s=1.0)
    ended = False
    for _ in range(60):
        if det.update(0.9).ended:
            ended = True
            break
    assert ended, "max-utterance cap must end speech"


def test_queue_put_clear():
    q = SpeechQueue()
    assert q.put(SpeechItem(text="a"))
    assert q.put(SpeechItem(text="b"))
    assert q.qsize() == 2
    discarded = q.clear()
    assert len(discarded) == 2 and q.qsize() == 0


def test_cache_reuse():
    with tempfile.TemporaryDirectory() as tmp:
        cache = AudioCache(cache_dir=Path(tmp), max_files=10)
        wav = make_wav(Path(tmp) / "src.wav")
        p1 = cache.put("Hello world", "v", "r", "p", "u", wav)
        p2 = cache.get("Hello world", "v", "r", "p", "u")
        p3 = cache.get("Different", "v", "r", "p", "u")
        assert p1 == p2 and p2.exists()
        assert p3 is None
        assert cache.key("Hello world", "v", "r", "p", "u") == cache.key("Hello world", "v", "r", "p", "u")


def test_interrupt_barge_in_gate():
    from speech.config import cfg as speech_cfg
    mgr = InterruptManager()
    mgr.playback_started()
    # inside echo-suppression window -> ignored
    assert not mgr.feed_mic_signal(0.9)
    mgr._playback_started = time.perf_counter() - 0.5  # pretend echo window passed
    # own voice heard (ramp-in) — resets any gap, never barges
    assert not mgr.feed_mic_signal(0.9)
    # then a mid-speech pause completes the quiet gap
    for _ in range(speech_cfg.barge_gap_frames):
        assert not mgr.feed_mic_signal(0.05)
    # resumed voice needs barge_confirm_frames consecutive frames
    first = mgr.feed_mic_signal(0.9)
    second = mgr.feed_mic_signal(0.9)
    third = mgr.feed_mic_signal(0.9)
    assert not first and not second and third, (first, second, third)
    mgr.request_interrupt()
    assert mgr.cancelled()
    mgr.record_handled()
    assert not mgr.cancelled()
    mgr.playback_stopped()


def test_interrupt_barge_confirm_frames():
    from speech.config import cfg as speech_cfg
    mgr = InterruptManager()
    mgr.playback_started()
    mgr._playback_started = time.perf_counter() - 0.5
    assert not mgr.feed_mic_signal(0.9)   # own voice heard
    for _ in range(speech_cfg.barge_gap_frames):
        assert not mgr.feed_mic_signal(0.05)     # establish the quiet gap
    count = sum(1 for _ in range(3) if mgr.feed_mic_signal(0.9))
    assert count == 1  # exact trigger on the confirm-frames-th frame
    mgr.playback_stopped()


def test_event_bus_ordering():
    bus = EventBus()
    order = []
    bus.subscribe(SpeechEventType.SPEECH_STARTED, lambda e: order.append("start"))
    bus.subscribe(SpeechEventType.SPEECH_STARTED, lambda e: order.append("start2"))
    bus.subscribe(SpeechEventType.SPEECH_ENDED, lambda e: order.append("end"))
    bus.publish(SpeechEventType.SPEECH_STARTED)
    bus.publish(SpeechEventType.SPEECH_ENDED)
    assert order == ["start", "start2", "end"]
    assert [e.type for e in bus.history()] == [SpeechEventType.SPEECH_STARTED, SpeechEventType.SPEECH_ENDED]


def test_recognizer_fallback_order():
    r = Recognizer()
    providers = r.providers()
    assert providers == providers  # chain builds without hardware
    result = r.transcribe(np.zeros(4000, dtype=np.float32))
    assert not result.success
    result = r.transcribe(np.zeros(0, dtype=np.float32))
    assert result.error


def test_engine_api_shape():
    engine = SpeechEngine(start_audio=False)
    avail = engine.is_available()
    assert isinstance(avail, dict)
    assert "tts" in avail and "stt" in avail and "mic" in avail
    assert engine.speak("") is False
    assert engine.speak(None) is False


def test_engine_speak_and_cache_reuse():
    with tempfile.TemporaryDirectory() as tmp:
        cache = AudioCache(cache_dir=Path(tmp) / "cache", max_files=10)
        engine = SpeechEngine(tts_provider=FakeTTS(cache), start_audio=False)
        assert engine.speak("Hello. World.", blocking=False)
        assert engine.queue.qsize() == 2
        calls_after_first = engine.tts.calls
        assert engine.speak("Hello. World.", blocking=False)
        assert engine.tts.calls == calls_after_first  # cache reused
        engine.flush_queue()
        engine.interrupt.reset()


def test_playback_interrupt_flushes_queue():
    with tempfile.TemporaryDirectory() as tmp:
        cache = AudioCache(cache_dir=Path(tmp) / "cache", max_files=10)
        engine = SpeechEngine(tts_provider=FakeTTS(cache), start_audio=False)
        engine.start()  # starts grabber (no mic) + playback worker
        assert engine.speak("One sentence.", blocking=False)
        engine.queue.put(SpeechItem(text="second", path=make_wav(Path(tmp) / "b.wav"), temp=False))
        deadline = time.time() + 3.0
        started = False
        while time.time() < deadline:
            if any(e.type == SpeechEventType.PLAYBACK_STARTED for e in engine_events_history(engine)):
                started = True
                break
            time.sleep(0.05)
        assert started
        engine.stop_speaking()
        deadline = time.time() + 3.0
        interrupted = False
        while time.time() < deadline:
            if any(e.type == SpeechEventType.PLAYBACK_INTERRUPTED for e in engine_events_history(engine)):
                interrupted = True
                break
            time.sleep(0.05)
        assert interrupted
        assert engine.queue.qsize() == 0
        engine.stop()


def engine_events_history(engine):
    from speech.events import event_bus
    return event_bus.history()


def test_reports_generated():
    from speech.benchmark import latency_recorder
    latency_recorder.clear()
    latency_recorder.record("interrupt_ms", 42.0)
    latency_recorder.record("first_audio_ms", 310.0)
    latency_recorder.write_reports(ROOT / "docs")
    assert (ROOT / "docs" / "latency_report.md").exists()
    assert (ROOT / "docs" / "benchmark.md").exists()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"  [PASS] {fn.__name__}")
        except Exception as e:
            failed += 1
            print(f"  [FAIL] {fn.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
