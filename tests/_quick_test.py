import sys, asyncio
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from interface.app import JARVIS
from core.tools import tool_registry

async def test():
    j = JARVIS()
    j.enable_debug()
    j.boot()

    # 1) Non-streaming handle
    r = await j.handle('hello')
    resp = r.get('response', '')
    print(f'[NON-STREAM] ok — "{resp[:80]}"')

    # 2) Streaming handle — no duplicate in content (thinking tokens allowed)
    tokens = []
    think_tokens = []
    async for tok in j.handle_stream('hello'):
        if tok.startswith('\x00'):
            think_tokens.append(tok[1:])
        else:
            tokens.append(tok)
    full = ''.join(tokens)
    hello_content = full.lower().count('hello')
    hello_think = ''.join(think_tokens).lower().count('hello') if think_tokens else 0
    print(f'[STREAM] content_len={len(full)} think_tokens={len(think_tokens)} "hello" in content={hello_content} (want <=1)')
    if hello_content > 1:
        print('  FAIL: DUPLICATE DETECTED in content')
    else:
        print('  PASS: no duplicate in content')
    if think_tokens:
        print(f'  THINK: visible ({hello_think} refs in thinking)')

    # 3) Tool execution test
    r2 = await j.handle('open youtube')
    tool = r2.get('tool', '')
    if tool:
        print(f'[TOOL] tool={tool} success={r2.get("success")} — PASS')
    else:
        print(f'[TOOL] no tool called (model chose natural response)')
        print(f'  response={r2.get("response", "")[:60]}')

    # 4) Tools registered
    tools = tool_registry.get_all()
    print(f'[TOOLS] {len(tools)} registered')

    await j.shutdown()
    print('\nDONE')

asyncio.run(test())
