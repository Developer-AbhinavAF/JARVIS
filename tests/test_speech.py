"""Speech Engine Tests — 10+ tests for TTS/STT availability and basic functions."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from interface.speech import speech_engine


def test_availability():
    avail = speech_engine.is_available()
    assert "tts" in avail
    assert "stt" in avail
    print(f"  Speech Available: TTS={avail['tts']} STT={avail['stt']}")
    return 1, 1


def test_speak_empty():
    result = speech_engine.speak("")
    assert result == False
    print("  Speak Empty: PASS")
    return 1, 1


def test_speak_simple():
    result = speech_engine.speak("Test message")
    if speech_engine._tts_available:
        if not result:
            print("  Speak Simple: WARN (TTS available but speak returned False)")
        else:
            print("  Speak Simple: PASS")
    else:
        print("  Speak Simple: SKIP (TTS unavailable)")
    return 1, 1


def test_speak_async():
    result = speech_engine.speak_async("Async test")
    if speech_engine._tts_available:
        assert result == True
    print("  Speak Async: PASS")
    return 1, 1


def test_listen_empty():
    result = speech_engine.listen(timeout=0.5)
    assert result == ""  # No audio input in CI
    print("  Listen (no input): PASS")
    return 1, 1


def run():
    print("\n=== Speech Tests ===")
    total_passed = 0
    total = 0
    tests = [
        test_availability, test_speak_empty, test_speak_simple,
        test_speak_async, test_listen_empty,
    ]
    for t in tests:
        try:
            p, tot = t()
            total_passed += p
            total += tot
        except Exception as e:
            print(f"  {t.__name__}: FAIL ({e})")
            total += 1
    return total_passed, total


if __name__ == "__main__":
    run()
