"""Test all NLP fixes."""
from jarvis.nlp import SemanticNLPEngine

nlp = SemanticNLPEngine()

tests = [
    # Spell corrector fixes
    ("search black hole on reddit", "SEARCH_ON_PLATFORM"),
    ("search cosmic star on wikipedia", "SEARCH_ON_PLATFORM"),
    ("search voyager 1 on google", "SEARCH_WEB"),
    
    # Chat intent fixes
    ("how are you", "CHAT"),
    ("how are you bro", "CHAT"),
    ("how are you doing", "CHAT"),
    ("what's up", "CHAT"),
    ("who are you", "CHAT"),
    ("tell me about yourself", "CHAT"),
    
    # Memory intent fixes
    ("my name is abhinav", "SAVE_MEMORY"),
    ("call me john", "SAVE_MEMORY"),
    ("do you know my name", "RECALL_MEMORY"),
    ("what is my name", "RECALL_MEMORY"),
    ("you know my name", "RECALL_MEMORY"),
    
    # Existing functionality (should still work)
    ("open youtube", "OPEN_WEBSITE"),
    ("open chrome", "OPEN_APP"),
    ("search python on github", "SEARCH_ON_PLATFORM"),
    ("search headphones on amazon", "SEARCH_ON_PLATFORM"),
    ("hello", "GREETING"),
    ("tell me a joke", "JOKE"),
]

print("Query".ljust(45), "Expected".ljust(20), "Actual".ljust(20), "Status")
print("-" * 100)

for query, expected in tests:
    r = nlp.process(query)
    actual = r.intent
    status = "OK" if actual == expected else "FAIL"
    print(f"{query:45s} {expected:20s} {actual:20s} {status}")
