"""Debug script for command engine."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jarvis.tool_metadata import WEBSITES, catalog

# Check if 'news' is in WEBSITES
print("news in WEBSITES:", "news" in WEBSITES)
print("nasa in WEBSITES:", "nasa" in WEBSITES)
print()

# Test the catalog directly
tests = [
    "latest news", "news", "nasa apod", "nasa", "youtube", "google",
    "open news", "open nasa", "nasa picture of the day",
    "increase brightness", "dim screen", "weather tokyo", "joke",
    "rename file", "copy file",
]

for t in tests:
    meta = catalog.find_by_pattern(t)
    if meta:
        print(f"  {t!r}: tool={meta.name} priority={meta.priority} conf={meta.confidence}")
    else:
        print(f"  {t!r}: NO MATCH")
