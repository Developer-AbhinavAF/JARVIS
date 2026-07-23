import logging
import os
import time

from speech.generate_agi_audio import generate_agi_audio

logger = logging.getLogger(__name__)


def run_benchmark():
    logger.info("Starting Kokoro TTS Benchmark...")

    text = "bhai tension mat le, tera kaam ho gaya hai. yeh ek benchmark test hai."
    output = "bench_test.wav"

    start = time.time()
    result = generate_agi_audio(text, output)
    elapsed = time.time() - start

    result_msg = f"""
==================================================
KOKORO TTS BENCHMARK
==================================================
Success:  {result is not None}
Latency:  {elapsed * 1000:.0f} ms
Audio:    {output if result else 'N/A'}
==================================================
"""
    print(result_msg)
    logger.info(result_msg)
    if result:
        try:
            os.unlink(output)
        except OSError:
            pass
    return result_msg


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run_benchmark()
