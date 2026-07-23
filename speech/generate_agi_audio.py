import logging
import os
import re
import tempfile
from pathlib import Path

import soundfile as sf
from indic_transliteration import sanscript

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "kokoro"
MODEL_FILE = MODEL_DIR / "kokoro-v1.0.int8.onnx"
VOICES_FILE = MODEL_DIR / "voices-v1.0.bin"

_kokoro = None
_kokoro_sr = 24000


def _lazy_load():
    global _kokoro
    if _kokoro is not None:
        return True
    if not MODEL_FILE.is_file() or not VOICES_FILE.is_file():
        logger.error("Kokoro model files not found at %s", MODEL_DIR)
        return False
    try:
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(str(MODEL_FILE), str(VOICES_FILE))
        logger.info("Kokoro loaded, %d voices available", len(_kokoro.get_voices()))
        return True
    except Exception as e:
        logger.error("Failed to load Kokoro: %s", e)
        return False


def _normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _roman_to_devanagari(text: str) -> str:
    try:
        return sanscript.transliterate(text, sanscript.ITRANS, sanscript.DEVANAGARI)
    except Exception as e:
        logger.warning("Transliteration failed, using original text: %s", e)
        return text


def generate_agi_audio(input_text: str, output_filepath: str = "agi_out.wav") -> str | None:
    if not _lazy_load():
        return None

    try:
        normalized = _normalize_text(input_text)
        devanagari_text = _roman_to_devanagari(normalized)
        audio, sample_rate = _kokoro.create(
            devanagari_text,
            voice="im_nicola",
            speed=1.0,
            lang="hi",
        )
        sf.write(output_filepath, audio, sample_rate)
        logger.info(
            "Generated %.1fs audio -> %s", len(audio) / sample_rate, output_filepath
        )
        return output_filepath
    except Exception as e:
        logger.error("Audio generation failed: %s", e)
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    test_phrase = "bhai tension mat le, tera kaam ho gaya hai. chal ab coding shuru karte hain."
    logger.info("Input: %s", test_phrase)

    output = generate_agi_audio(test_phrase, "agi_test.wav")
    if output:
        import winsound

        winsound.PlaySound(output, winsound.SND_FILENAME | winsound.SND_NODEFAULT)
        os.unlink(output)
        logger.info("Test playback complete.")
    else:
        logger.error("Test FAILED - no audio generated.")
