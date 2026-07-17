"""Test memory connection for personal info."""
import asyncio
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from app import JARVIS

async def test():
    jarvis = JARVIS()
    await jarvis.boot()
    
    print("=== Testing personal info save ===")
    r1 = await jarvis.handle("my name is abhinav")
    print(f"  Save: {r1}")
    
    r2 = await jarvis.handle("call me john")
    print(f"  Save: {r2}")
    
    r3 = await jarvis.handle("my email is test@example.com")
    print(f"  Save: {r3}")
    
    print("\n=== Testing personal info recall ===")
    r4 = await jarvis.handle("what is my name")
    print(f"  Recall: {r4}")
    
    r5 = await jarvis.handle("do you know my name")
    print(f"  Recall: {r5}")
    
    r6 = await jarvis.handle("what is my email")
    print(f"  Recall: {r6}")
    
    r7 = await jarvis.handle("what do you know about me")
    print(f"  Recall all: {r7}")
    
    # Clean up test data
    jarvis._memory.save_preference("name", "", "personal")
    jarvis._memory.save_preference("email", "", "personal")
    
    print("\nDone!")

asyncio.run(test())
