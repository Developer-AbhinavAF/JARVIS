"""Streaming bridge — Twilio Media Streams ↔ JARVIS Brain.

Handles:
- Receiving audio chunks from Twilio WebSocket
- Buffering and transcribing audio
- Synthesizing JARVIS responses via Edge-TTS
- Streaming audio back to Twilio
- Interruption handling (barge-in)
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import struct
import time
import wave
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

logger = logging.getLogger("jarvis.telephony.streaming")


class AudioBuffer:
    """Accumulates mulaw audio chunks from Twilio until silence is detected."""

    def __init__(self, sample_rate: int = 8000, silence_threshold_ms: int = 1200) -> None:
        self.sample_rate = sample_rate
        self.silence_threshold_ms = silence_threshold_ms
        self._buffer: bytearray = bytearray()
        self._last_voice_time: float = 0.0
        self._is_speaking: bool = False
        self._bytes_per_ms = sample_rate // 1000  # 8 bytes/ms for 8kHz mulaw
        self._min_audio_bytes = 2000  # Minimum audio before considering it speech

    def add_chunk(self, mulaw_bytes: bytes) -> None:
        self._buffer.extend(mulaw_bytes)
        self._last_voice_time = time.time()
        self._is_speaking = True

    @property
    def has_speech(self) -> bool:
        return len(self._buffer) >= self._min_audio_bytes

    @property
    def is_silence_detected(self) -> bool:
        if not self._is_speaking or not self.has_speech:
            return False
        elapsed_ms = (time.time() - self._last_voice_time) * 1000
        return elapsed_ms >= self.silence_threshold_ms

    def get_audio(self) -> bytes:
        data = bytes(self._buffer)
        self._buffer.clear()
        self._is_speaking = False
        return data

    def clear(self) -> None:
        self._buffer.clear()
        self._is_speaking = False


class TwilioStreamHandler:
    """Handles a single Twilio Media Stream WebSocket connection.

    Flow:
    1. Receive audio chunks from Twilio → buffer → transcribe
    2. Pass transcribed text to JARVIS brain
    3. Synthesize response via Edge-TTS → convert to mulaw → stream back
    """

    def __init__(self, session: Any, ws: Any) -> None:
        from interface.telephony.session import CallSession
        self.session: CallSession = session
        self.ws = ws
        self._audio_buffer = AudioBuffer()
        self._running = False
        self._tts_queue: asyncio.Queue[Optional[bytes]] = asyncio.Queue()
        self._send_task: Optional[asyncio.Task] = None
        self._process_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start processing the media stream."""
        self._running = True
        self._send_task = asyncio.create_task(self._send_loop())
        self._process_task = asyncio.create_task(self._receive_loop())
        logger.info("Stream started for call %s", self.session.call_sid)

    async def stop(self) -> None:
        self._running = False
        await self._tts_queue.put(None)
        for task in [self._send_task, self._process_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error("Error stopping task for call %s: %s", self.session.call_sid, e)
        logger.info("Stream stopped for call %s", self.session.call_sid)

    async def _receive_loop(self) -> None:
        """Receive audio chunks from Twilio WebSocket."""
        try:
            async for message in self.ws:
                if isinstance(message, str):
                    data = json.loads(message)
                    event = data.get("event")

                    if event == "connected":
                        logger.info("Twilio stream connected")
                    elif event == "start":
                        self.session.stream_sid = data.get("streamSid")
                        logger.info("Stream started: %s", self.session.stream_sid)
                    elif event == "media":
                        payload = data.get("media", {}).get("payload", "")
                        if payload:
                            audio_bytes = base64.b64decode(payload)
                            self._audio_buffer.add_chunk(audio_bytes)
                    elif event == "stop":
                        logger.info("Stream stop received")
                        self._running = False
                        break
                    elif event == "mark":
                        label = data.get("mark", {}).get("name", "")
                        logger.debug("Mark received: %s", label)
        except Exception as e:
            if self._running:
                logger.error("Receive loop error: %s", e)
        finally:
            self._running = False

    async def _send_loop(self) -> None:
        """Send audio back to Twilio."""
        try:
            while self._running:
                audio_chunk = await self._tts_queue.get()
                if audio_chunk is None:
                    break
                await self._send_audio(audio_chunk)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Send loop error: %s", e)

    async def _send_audio(self, mulaw_bytes: bytes) -> None:
        """Send mulaw audio chunk to Twilio via WebSocket."""
        if not self.session.stream_sid or not self.ws:
            return
        payload = base64.b64encode(mulaw_bytes).decode("ascii")
        msg = json.dumps({
            "event": "media",
            "streamSid": self.session.stream_sid,
            "media": {"payload": payload},
        })
        try:
            await self.ws.send(msg)
        except Exception as e:
            logger.error("Failed to send audio: %s", e)

    async def sendmark(self, name: str) -> None:
        """Send a mark event to Twilio (for synchronization)."""
        if not self.session.stream_sid or not self.ws:
            return
        msg = json.dumps({
            "event": "mark",
            "streamSid": self.session.stream_sid,
            "mark": {"name": name},
        })
        try:
            await self.ws.send(msg)
        except Exception:
            pass

    async def clear_speaker(self) -> None:
        """Clear Twilio's speaker buffer (for interruption support)."""
        if not self.session.stream_sid or not self.ws:
            return
        msg = json.dumps({
            "event": "clear",
            "streamSid": self.session.stream_sid,
        })
        try:
            await self.ws.send(msg)
            # Drain the TTS queue on interruption
            while not self._tts_queue.empty():
                try:
                    self._tts_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        except Exception:
            pass

    def feed_tts_audio(self, mulaw_bytes: bytes) -> None:
        """Enqueue audio for sending to Twilio (thread-safe)."""
        try:
            self._tts_queue.put_nowait(mulaw_bytes)
        except asyncio.QueueFull:
            logger.warning("TTS queue full, dropping audio")

    async def synthesize_and_stream(self, text: str) -> float:
        """Synthesize text to audio and stream to Twilio. Returns TTS latency in ms."""
        from interface.telephony.config import telephony_config

        start = time.time()

        # Use Edge-TTS to get WAV audio
        try:
            wav_path = await self._synthesize_edge_tts(text)
            if not wav_path:
                return 0.0

            # Convert WAV to mulaw 8kHz for Twilio
            mulaw_chunks = wav_to_mulaw_chunks(
                wav_path,
                target_rate=telephony_config.twilio_sample_rate,
                chunk_ms=20,  # 20ms chunks for Twilio
            )

            for chunk in mulaw_chunks:
                self.feed_tts_audio(chunk)
                # Pace audio: sleep ~16ms per 20ms chunk to avoid burst
                await asyncio.sleep(0.016)

            # Send mark to indicate end of this utterance
            await self.sendmark(f"tts-{int(time.time() * 1000)}")

        except Exception as e:
            logger.error("TTS synthesis failed: %s", e)

        return (time.time() - start) * 1000

    async def _synthesize_edge_tts(self, text: str) -> Optional[Path]:
        """Synthesize text via Edge-TTS, return WAV file path."""
        try:
            from speech.edge_provider import edge_tts_provider
            import asyncio

            result = await asyncio.to_thread(edge_tts_provider.synthesize, text)
            if result and result.path and result.path.exists():
                return result.path
        except Exception as e:
            logger.error("Edge-TTS provider failed: %s", e)

        # Fallback: direct edge_tts call → MP3 → WAV
        try:
            import edge_tts
            from interface.telephony.config import telephony_config

            communicate = edge_tts.Communicate(
                text,
                telephony_config.tts_voice,
                rate=telephony_config.tts_rate,
            )
            mp3_path = Path(f"/tmp/tts_{int(time.time() * 1000)}.mp3")
            wav_path = mp3_path.with_suffix(".wav")

            await communicate.save(str(mp3_path))

            # Convert MP3 to WAV
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_mp3(str(mp3_path))
                audio.export(str(wav_path), format="wav")
            except ImportError:
                try:
                    import miniaudio
                    decoded = miniaudio.decode_file(str(mp3_path))
                    with wave.open(str(wav_path), "wb") as wf:
                        wf.setnchannels(decoded.nchannels)
                        wf.setsampwidth(2)
                        wf.setframerate(decoded.sample_rate)
                        wf.writeframes(decoded.samples)
                except ImportError:
                    logger.error("No MP3->WAV converter (install pydub or miniaudio)")
                    mp3_path.unlink(missing_ok=True)
                    return None

            mp3_path.unlink(missing_ok=True)
            return wav_path

        except Exception as e:
            logger.error("Edge-TTS fallback failed: %s", e)
            return None


def wav_to_mulaw_chunks(
    wav_path: Path,
    target_rate: int = 8000,
    chunk_ms: int = 20,
) -> list[bytes]:
    """Convert a WAV file to mulaw 8kHz audio chunks."""
    import wave as wave_mod

    with wave_mod.open(str(wav_path), "rb") as wf:
        nchannels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        pcm_data = wf.readframes(wf.getnframes())

    # Convert to mono 16-bit samples
    if sampwidth != 2:
        logger.error("Unsupported sample width: %d", sampwidth)
        return []

    samples = list(struct.unpack(f"<{len(pcm_data) // 2}h", pcm_data))

    # Downmix to mono if stereo
    if nchannels == 2:
        mono: list[int] = []
        for i in range(0, len(samples), 2):
            mono.append((samples[i] + samples[i + 1]) // 2)
        samples = mono

    # Resample if needed
    if framerate != target_rate:
        ratio = target_rate / framerate
        new_len = int(len(samples) * ratio)
        samples = [samples[int(i / ratio)] for i in range(new_len)]

    # Convert to mulaw
    mulaw_data = _ulaw_encode(samples)

    # Split into chunks
    chunk_size = target_rate * chunk_ms // 1000
    chunks = [mulaw_data[i : i + chunk_size] for i in range(0, len(mulaw_data), chunk_size)]

    wav_path.unlink(missing_ok=True)
    return chunks


def _ulaw_encode(pcm_samples: list[int]) -> bytes:
    """Encode linear 16-bit PCM samples to mulaw."""
    result = bytearray()
    BIAS = 33
    CLIP = 32635

    for sample in pcm_samples:
        sample = max(-32768, min(32767, sample))
        sign = 0x80 if sample < 0 else 0
        if sign:
            sample = -sample
        sample = min(sample + BIAS, CLIP)

        exponent = 7
        mask = 0x4000
        while exponent > 0 and (sample & mask) == 0:
            exponent -= 1
            mask >>= 1

        mantissa = (sample >> (exponent + 3)) & 0x0F
        mulaw_byte = ~(sign | (exponent << 4) | mantissa) & 0xFF
        result.append(mulaw_byte)

    return bytes(result)


def pcm_to_mulaw(pcm_data: bytes, sample_rate: int = 8000) -> bytes:
    """Convert raw PCM 16-bit to mulaw."""
    samples = struct.unpack(f"<{len(pcm_data) // 2}h", pcm_data)
    return _ulaw_encode(list(samples))
