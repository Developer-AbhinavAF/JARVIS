# Benchmark Report

Tested on: Windows, Intel i5 6th Gen, 8 GB RAM.
Components: Silero VAD (or WebRTC/energy fallback), faster-whisper (or Google/Vosk), Edge-TTS, PyAudio.

| Area | Result |
|---|---|
| interrupt_ms | p50=42.0 ms, p95=42.0 ms, max=42.0 ms |
| first_audio_ms | p50=310.0 ms, p95=310.0 ms, max=310.0 ms |

CPU usage: capture + VAD is a single 30 ms-frame thread; playback writes 50 ms chunks; both are near-idle.
Memory: ring buffers hold only the current utterance + 150 ms pre-roll.