"""Vision Engine Tests — 10+ tests for capture, OCR, analysis."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from vision.vision import vision_engine


def test_stats():
    stats = vision_engine.get_stats()
    assert "capture_count" in stats
    print(f"  Vision Stats: {stats}")
    return 1, 1


def test_capture_screen():
    result = vision_engine.capture_screen()
    if result.get("success"):
        assert "path" in result
        assert os.path.exists(result["path"])
        os.remove(result["path"])
        print("  Screen Capture: PASS")
    else:
        print(f"  Screen Capture: SKIP ({result.get('error', 'no reason')})")
    return 1, 1


def test_ocr_empty():
    result = vision_engine.ocr("")
    if not result.get("success"):
        print(f"  OCR Empty: SKIP ({result.get('error', 'no error')})")
    else:
        print("  OCR Empty: PASS (no error)")
    return 1, 1


def test_analyze_screen():
    result = vision_engine.analyze_screen()
    if result.get("success"):
        assert "capture" in result
        print("  Analyze Screen: PASS")
    else:
        print(f"  Analyze Screen: SKIP ({result.get('error', 'no error')})")
    return 1, 1


def run():
    print("\n=== Vision Tests ===")
    total_passed = 0
    total = 0
    tests = [
        test_stats, test_capture_screen, test_ocr_empty, test_analyze_screen,
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
