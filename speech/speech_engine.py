"""speech/speech_engine.py — Production conversational speech engine.

Natural turn-based orchestration:

    MIC ALWAYS ON
        -> VAD (Silero/WebRTC/energy)
        -> smart endpoint (pauses don't end speech)
        -> recognition (faster-whisper -> Google -> Vosk) only after end
        -> handler -> streamed reply -> sentence splitter -> Edge-TTS
        -> playback queue (parallel with LLM generation)
        -> natural turn-taking (no barge-in)

Public surface is compatible with the previous `interface.speech`
(speech_engine.is_available/listen/speak/stop_speaking) so JarvisCore, CLI,
desktop backend, REST and WebSocket keep working unchanged.
"""

from __future__ import annotations

import time
import threading
from typing import Any, Callable, Iterator, Optional

from speech.config import cfg
from speech.events import event_bus, SpeechEventType
from speech.logger import get_logger, conversation_view
from speech.queue import SpeechQueue, SpeechItem
from speech.vad import vad
from speech.endpoint_detector import EndpointDetector
from speech.recognizer import recognizer, RecognitionResult
from speech.streaming import UtteranceGrabber, SentenceSplitter
from speech.interrupt_manager import interrupt_manager
from speech.playback import PlaybackWorker
from speech.edge_provider import edge_tts_provider
from speech.benchmark import latency_recorder

logger = get_logger("engine")


class SpeechEngine:
    def __init__(self, tts_provider=None, recognizer_impl=None, start_audio=True) -> None:
        self.cfg = cfg
        self.tts = tts_provider or edge_tts_provider
        self.recognizer = recognizer_impl or recognizer
        self.interrupt = interrupt_manager
        self.queue = SpeechQueue()
        self.playback = PlaybackWorker(self.queue, interrupt=self.interrupt, start_audio=start_audio)
        self._start_audio = start_audio
        self._running = False
        self._grabber: Optional[UtteranceGrabber] = None
        self._grabber_lock = threading.Lock()
        self._listener: Optional[threading.Event] = None
        self._listener_result = {"text": ""}
        self._conv_handler: Optional[Callable[[str], Any]] = None
        self._conv_queue: "queue.Queue[tuple[Any, float]]" = __import__("queue").Queue(maxsize=16)
        self._conv_stop = threading.Event()
        self._conv_worker: Optional[threading.Thread] = None
        self._abort_current = threading.Event()
        self._drained = threading.Event()

    # ---------------------------------------------------------------- status
    def is_available(self) -> dict:
        stt = self.recognizer.providers() if hasattr(self.recognizer, "providers") else []
        tts_ok = self.tts.is_available() if hasattr(self.tts, "is_available") else False
        mic_ok = bool(self._grabber and self._grabber.mic_available) if self._grabber else (self._start_audio and _pyaudio_importable())
        return {
            "tts": bool(tts_ok),
            "stt": bool(stt),
            "mic": mic_ok,
            "tts_engine": self.tts.__class__.__name__,
            "stt_engine": stt[0] if stt else "none",
        }

    # ------------------------------------------------------------- lifecycle
    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self.cfg.ensure_dirs()
        self.playback.start_worker()
        self._grabber = UtteranceGrabber(
            on_utterance=self._on_utterance,
            on_speech_signal=self._on_speech_signal,
            start_audio=self._start_audio,
        )
        self._grabber.start_worker()
        threading.Thread(target=self._warmup, daemon=True).start()
        logger.info("Speech engine started (mic always on)")

    def _warmup(self) -> None:
        """Background model prep: Vosk download, whisper model warm-up."""
        try:
            from speech.recognizer import ensure_vosk_model
            ensure_vosk_model()
        except Exception:
            pass
        try:
            if self.recognizer.providers():
                pass
        except Exception:
            pass

    def stop(self) -> None:
        self._running = False
        self._conv_stop.set()
        self.interrupt.request_interrupt()
        self.playback.stop_worker()
        if self._grabber:
            self._grabber.stop_worker()
            self._grabber = None
        # Ensure queue is cleared to prevent memory leaks
        self.queue.clear()
        logger.info("Speech engine stopped")

    def shutdown(self) -> None:
        self.stop()

    # ------------------------------------------------------------ grabber io
    def _on_speech_signal(self, prob: float) -> None:
        # Barge-in disabled for natural turn-based conversation
        pass

    def _on_utterance(self, audio, speech_ms: float) -> None:
        if self._listener is not None:
            threading.Thread(target=self._recognize_into, args=(audio, self._listener, self._listener_result),
                             name="speech-recognize", daemon=True).start()
            return
        if self._conv_handler is not None:
            try:
                self._conv_queue.put_nowait((audio, speech_ms))
            except Exception:
                pass

    @staticmethod
    def _recognize_into(audio, slot: threading.Event, result: dict) -> None:
        result["text"] = ""
        try:
            r = recognizer.transcribe(audio)
            result["text"] = r.text
            result["provider"] = r.provider
            result["confidence"] = r.confidence
            # Print transcript
            if r.text:
                conversation_view.user(r.text)
        except Exception as e:
            logger.warning("Recognition failed: %s", e)
        finally:
            slot.set()

    def _enqueue_speech(self, text: str) -> bool:
        if self.interrupt.cancelled():
            return False
        try:
            result = self.tts.synthesize(text)
        except Exception as e:
            logger.warning("TTS failed: %s", e)
            return False
        if result is None:
            return False
        # Print Jarvis response transcript
        from speech.logger import conversation_view
        conversation_view.jarvis(text)
        return self.queue.put(SpeechItem(text=text, path=result.path, temp=False))

    # ---------------------------------------------------------------- listen
    def listen(self, timeout: Optional[float] = 5.0) -> str:
        """Wait for the next complete utterance; returns recognized text."""
        if not self._running:
            self.start()
        grabber = self._grabber
        if grabber is None or not grabber.mic_available:
            return ""
        slot = threading.Event()
        self._listener = slot
        self._listener_result = {"text": ""}
        try:
            if timeout is None:
                slot.wait()
            else:
                slot.wait(timeout=timeout)
        finally:
            self._listener = None
        return self._listener_result.get("text", "")

    async def listen_async(self, timeout: Optional[float] = 5.0) -> str:
        import asyncio
        return await asyncio.get_running_loop().run_in_executor(None, self.listen, timeout)

    # ----------------------------------------------------------------- speak
    def speak(self, text: str, blocking: bool = True) -> bool:
        """Split text into sentences, synthesize, queue, play (streamed)."""
        if not text or not text.strip():
            return False
        # Print transcript
        conversation_view.jarvis(text)
        self.interrupt.reset()
        self._abort_current.clear()
        if self._start_audio:
            self.playback.start_worker()
        self._drained.clear()
        splitter = SentenceSplitter(on_sentence=self._enqueue_speech)
        splitter.feed(text)
        splitter.flush()
        if blocking:
            self._wait_drained()
        return not self.interrupt.cancelled()

    def speak_stream(self, tokens: Iterator[str], blocking: bool = False) -> None:
        """Consume LLM tokens and speak sentence-by-sentence as they complete."""
        self.interrupt.reset()
        self._abort_current.clear()
        event_bus.publish(SpeechEventType.RESPONSE_STARTED)
        splitter = SentenceSplitter(on_sentence=self._enqueue_speech)
        for token in tokens:
            if self.interrupt.cancelled():
                break
            if isinstance(token, str):
                splitter.feed(token)
        if not self.interrupt.cancelled():
            splitter.flush()
        if blocking:
            self._wait_drained()
        event_bus.publish(SpeechEventType.RESPONSE_FINISHED)

    async def speak_from_core_stream(self, core_stream, blocking: bool = True) -> None:
        """Consume JarvisCore event stream and speak responses as they arrive.

        This integrates with JarvisCore's async event stream, extracting
        FinalResponse tokens and speaking them in real-time.
        """
        self.interrupt.reset()
        self._abort_current.clear()
        event_bus.publish(SpeechEventType.RESPONSE_STARTED)
        splitter = SentenceSplitter(on_sentence=self._enqueue_speech)
        response_text = ""

        async for event in core_stream:
            if self.interrupt.cancelled():
                break
            # Extract text from FinalResponse events
            if hasattr(event, 'text') and event.text:
                # Handle both FinalResponse and FinalResponseToken
                text = event.text
                response_text += text
                splitter.feed(text)
            # Also handle raw text if event is just a string
            elif isinstance(event, str):
                response_text += event
                splitter.feed(event)

        if not self.interrupt.cancelled():
            splitter.flush()
        if blocking:
            self._wait_drained()
        event_bus.publish(SpeechEventType.RESPONSE_FINISHED)

    def speak_async(self, text: str) -> bool:
        threading.Thread(target=self.speak, args=(text, False), name="speech-speak", daemon=True).start()
        return True

    def play(self, path) -> bool:
        return self.queue.put(SpeechItem(text="", path=path, temp=False))

    def stop_speaking(self) -> None:
        self.interrupt.request_interrupt()
        self._abort_current.set()

    def flush_queue(self) -> None:
        discarded = self.queue.clear()
        for item in discarded:
            pass  # cached files persist; only stop playback
        self.interrupt.playback_stopped()

    def _wait_drained(self) -> None:
        while not self.interrupt.cancelled():
            if self.queue.qsize() == 0 and not self.playback.is_playing:
                return
            time.sleep(0.02)

    # ---------------------------------------------------------- full-duplex
    def run_conversation(self, handler: Callable[[str], Any]) -> None:
        """Natural turn-based conversational loop.

        handler(text) -> response text (or dict with "response").
        """
        self._conv_handler = handler
        self._conv_stop.clear()
        self._conv_worker = threading.Thread(target=self._conversation_loop,
                                             name="speech-conv", daemon=True)
        self._conv_worker.start()
        if not self._running:
            self.start()

    def _conversation_loop(self) -> None:
        import queue as _queue
        while not self._conv_stop.is_set():
            try:
                audio, speech_ms = self._conv_queue.get(timeout=0.2)
            except _queue.Empty:
                continue
            if self._conv_stop.is_set():
                break
            # Natural turn-taking: wait for user to finish speaking
            self._abort_current.clear()
            result = self._recognize_blocking(audio)
            text = result.text.strip()
            if not text:
                continue
            conversation_view.user(text)
            try:
                response = self._conv_handler(text)
            except Exception as e:
                logger.warning("Handler error: %s", e)
                response = ""
            if isinstance(response, dict):
                response = response.get("response", "") or ""
            if not response or not str(response).strip():
                continue
            conversation_view.jarvis(response)
            event_bus.publish(SpeechEventType.RESPONSE_STARTED)
            self.speak(str(response), blocking=True)
            event_bus.publish(SpeechEventType.RESPONSE_FINISHED)

    def _recognize_blocking(self, audio) -> RecognitionResult:
        try:
            return self.recognizer.transcribe(audio)
        except Exception as e:
            logger.warning("Recognition error: %s", e)
            return RecognitionResult(error=str(e))

    def stop_conversation(self) -> None:
        self._conv_stop.set()
        self.stop_speaking()
        # Clear conversation queue to prevent memory leaks
        try:
            while not self._conv_queue.empty():
                self._conv_queue.get_nowait()
        except Exception:
            pass


def _pyaudio_importable() -> bool:
    try:
        import pyaudio  # noqa: F401
        return True
    except ImportError:
        return False


# Global singleton (compatible with `from interface.speech import speech_engine`)
speech_engine = SpeechEngine()