import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import asyncio
from app import JARVIS

async def test():
    jarvis = JARVIS()
    await jarvis.boot()
    
    # Calculator
    r = await jarvis.handle('calculate 2 + 2')
    resp = r.get('response', '')
    print(f'Calculator response: {resp}')
    print(f'Calculator success: {r.get("success")}')
    print(f'Calculator tool: {r.get("tool")}')
    
    # Email save
    r = await jarvis.handle('my email is test@example.com')
    resp = r.get('response', '')
    print(f'\nEmail save response: {resp}')
    print(f'Email save intent: {r.get("intent")}')
    
    # Email recall
    r = await jarvis.handle('what is my email')
    resp = r.get('response', '')
    print(f'\nEmail recall response: {resp}')
    print(f'Email recall intent: {r.get("intent")}')
    
    # remember this
    r = await jarvis.handle('remember this important fact')
    resp = r.get('response', '')
    print(f'\nRemember response: {resp}')
    print(f'Remember intent: {r.get("intent")}')

asyncio.run(test())
