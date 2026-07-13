"""Debug remaining failures."""
import sys
sys.path.insert(0, "D:\\AI\\JARVIS")

from jarvis.command_engine import CommandEngine

engine = CommandEngine()

queries = [
    "what time is it right now",
    "current date and time",
    "turn it up",
    "turn down the brightness",
    "whats the weather like",
    "10 divided by 2",
]

for q in queries:
    result = engine.process(q)
    print(f"Query: '{q}'")
    print(f"  Normalized: '{result.normalized_text}'")
    print(f"  Tool: '{result.tool_name}'")
    print(f"  Confidence: {result.confidence}")
    print(f"  Matched: {result.matched}")
    print()
