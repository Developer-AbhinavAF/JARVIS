# Latency Report

Pipeline targets vs measured (measured = synthetic/live sessions recorded via the event bus).

| Metric | Target | Measured (p50) | Samples |
|---|---|---|---|
| speech_start_detect_ms | < 50 ms | — | 0 |
| speech_end_detect_ms | < 80 ms | — | 0 |
| interrupt_ms | < 100 ms | 42.0 ms | 1 |
| recognition_start_ms | < 100 ms | — | 0 |
| first_audio_ms | < 500 ms | 310.0 ms | 1 |

Notes:
- Speech end detection is dominated by the configured trailing-silence hold (700 ms default).
- Interrupt latency is measured from request to playback-worker acknowledgement.
- Recognition start is measured from SPEECH_ENDED to RECOGNITION_STARTED.