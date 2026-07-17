import re
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
pattern = r"my email (?:is|'s)\s+(.+)"
text = "my email is test@pipeline.com"
m = re.search(pattern, text)
print(f"Match: {m}")
if m:
    print(f"Value: {m.group(1)}")

# Also test the full _handle_memory path
from app import JARVIS
import asyncio

async def test():
    jarvis = JARVIS()
    await jarvis.boot()
    
    # Test save email directly
    r = await jarvis.handle("my email is test@pipeline.com")
    print(f"Save email response: {r.get('response')}")
    print(f"Save email intent: {r.get('intent')}")
    
    # Check if preference was saved
    val = jarvis._memory.get_preference("email")
    print(f"Preference email: {val}")
    
    # Test recall email
    r = await jarvis.handle("what is my email")
    print(f"Recall email response: {r.get('response')}")
    print(f"Recall email intent: {r.get('intent')}")
    
    # Clean up
    jarvis._memory.save_preference("email", "", "personal")

asyncio.run(test())
