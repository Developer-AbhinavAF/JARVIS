import sys
from pathlib import Path
root = Path(r'd:\AI\JARVIS')
sys.path.insert(0, str(root))
print('PYTHON', sys.executable)
for mod in ['fastapi','uvicorn','pydantic','httpx','requests','pytest']:
    try:
        m = __import__(mod)
        print(mod, 'ok', getattr(m, '__version__', 'unknown'))
    except Exception as e:
        print(mod, 'import failed:', type(e).__name__, e)

try:
    import jarvis.api_routes
    print('jarvis.api_routes ok')
except Exception as e:
    print('jarvis.api_routes failed:', type(e).__name__, e)
try:
    import jarvis.ai_os
    from jarvis.ai_os.nlp.pipeline import NLPPipeline
    print('jarvis.ai_os ok', NLPPipeline.__name__)
except Exception as e:
    print('jarvis.ai_os import failed:', type(e).__name__, e)
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location('backend_app', root / 'jarvis-desktop' / 'backend' / 'app.py')
    backend_app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend_app)
    print('backend.app imported ok')
except Exception as e:
    print('backend.app import failed:', type(e).__name__, e)
try:
    from fastapi import FastAPI
    from jarvis.api_routes import register_personal_os_routes
    app = FastAPI()
    register_personal_os_routes(app)
    print('register_personal_os_routes ok', len(app.routes))
except Exception as e:
    print('route registration failed:', type(e).__name__, e)
