import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jarvis.tool_metadata import catalog
from jarvis.command_engine import CommandEngine
engine = CommandEngine(catalog)
tests = [
    ('open spotify', 'open_app'),
    ('fire up spotify', 'open_app'),
    ('bring up discord', 'open_app'),
    ('boot up teams', 'open_app'),
    ('load slack', 'open_app'),
    ('start up vlc', 'open_app'),
    ('spotify', 'open_app'),
    ('discord', 'open_app'),
    ('open outlook', 'open_app'),
    ('open chrome', 'open_app'),
    ('open youtube', 'open_website'),
    ('youtube', 'open_website'),
    ('fire up edge', 'open_app'),
    ('boot up word', 'open_app'),
    ('bring up excel', 'open_app'),
    ('load paint', 'open_app'),
]
for cmd, expected in tests:
    r = engine.process(cmd)
    s = 'PASS' if r.tool_name == expected else 'FAIL'
    extra = f' params={r.params}' if s == 'FAIL' else ''
    print(f'  [{s}] "{cmd}" -> {r.tool_name} (expected {expected}){extra}')
