"""Debug remaining 4 failures."""
import sys
sys.path.insert(0, "D:\\AI\\JARVIS")

import re
from jarvis.tool_metadata import catalog

queries = [
    ("what time is it right now", "datetime"),
    ("current date and time", "datetime"),
    ("turn down the brightness", "brightness_control"),
    ("whats the weather like", "weather"),
]

for q, expected in queries:
    cleaned = q.strip().lower()
    print(f"Query: '{q}'")
    print(f"  Cleaned: '{cleaned}'")
    
    # Try to find matching tool
    meta = catalog.find_by_pattern(cleaned)
    if meta:
        print(f"  Matched: {meta.name}")
    else:
        print(f"  No match")
    
    # Debug datetime patterns
    if expected == "datetime":
        meta_dt = catalog.get("datetime")
        if meta_dt:
            for i, pattern in enumerate(meta_dt.patterns):
                m = re.search(pattern, cleaned, re.IGNORECASE)
                print(f"  datetime pattern {i}: '{pattern}' -> {'MATCH' if m else 'no match'}")
    
    # Debug brightness patterns
    if expected == "brightness_control":
        meta_br = catalog.get("brightness_control")
        if meta_br:
            for i, pattern in enumerate(meta_br.patterns):
                m = re.search(pattern, cleaned, re.IGNORECASE)
                print(f"  brightness pattern {i}: '{pattern}' -> {'MATCH' if m else 'no match'}")
    
    # Debug weather patterns
    if expected == "weather":
        meta_w = catalog.get("weather")
        if meta_w:
            for i, pattern in enumerate(meta_w.patterns):
                m = re.search(pattern, cleaned, re.IGNORECASE)
                print(f"  weather pattern {i}: '{pattern}' -> {'MATCH' if m else 'no match'}")
    
    print()
