from jarvis.nlp.intent_engine import SemanticIntentEngine
from jarvis.nlp.normalizer import normalize

engine = SemanticIntentEngine()
n = normalize('remember this')
print(f"Normalized: {n!r}")
print(f"In map: {n in engine._exact_trigger_map}")
val = engine._exact_trigger_map.get(n, "NOT FOUND")
print(f"Map value: {val}")

# Check why RECALL_MEMORY wins
candidates = engine.detect('remember this')
for c in candidates[:3]:
    print(f"  {c.intent:25s} score={c.score:.4f} reason={c.reason[:80]}")
