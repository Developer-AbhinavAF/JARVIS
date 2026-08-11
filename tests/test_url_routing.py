"""tests/test_url_routing.py — URL / website routing contract.

Verifies that arbitrary URLs and bare domains route to the generic
browser executor (open_url) and are NEVER passed to subprocess /
executable execution, while known websites, applications and search
requests keep their dedicated routes.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import core.tools_registry as tr
from core.tools_registry import UnifiedToolRegistry
from core.toolcall_parser import tool_call_parser


registry = UnifiedToolRegistry()

OPEN_URL = "open_url"
OPEN_APP = "open_application"
WEB_SEARCH = "web_search"
YT_SEARCH = "youtube_search"


def classify(query):
    return registry.classify_input(query)


# ---------------------------------------------------------------------------
# ROUTING — arbitrary URLs
# ---------------------------------------------------------------------------

def test_open_https_url():
    tool, arg, value = classify("open https://example.com")
    assert tool == OPEN_URL
    assert arg == "url"
    assert value == "https://example.com"


def test_open_http_url():
    tool, _, value = classify("open http://example.com")
    assert tool == OPEN_URL
    assert value == "http://example.com"


def test_open_url_with_path():
    tool, _, value = classify("open https://example.com/path")
    assert tool == OPEN_URL
    assert value == "https://example.com/path"


def test_open_url_with_query():
    tool, _, value = classify("open https://example.com/path?q=test")
    assert tool == OPEN_URL
    assert value == "https://example.com/path?q=test"


def test_open_url_with_fragment():
    tool, _, value = classify("go to https://example.com/#section")
    assert tool == OPEN_URL
    assert value == "https://example.com/#section"


def test_open_url_embedded_phrase():
    tool, _, value = classify("open this website: https://example.com")
    assert tool == OPEN_URL
    assert value == "https://example.com"


def test_launch_url():
    tool, _, value = classify("launch https://some-new-site.com")
    assert tool == OPEN_URL
    assert value == "https://some-new-site.com"


def test_take_me_to_url():
    tool, _, value = classify("take me to https://example.com")
    assert tool == OPEN_URL
    assert value == "https://example.com"


# ---------------------------------------------------------------------------
# ROUTING — bare domains (normalized, never blind-mangled)
# ---------------------------------------------------------------------------

def test_open_bare_domain():
    tool, _, value = classify("open example.com")
    assert tool == OPEN_URL
    assert value == "https://example.com"


def test_go_to_bare_domain():
    tool, _, value = classify("go to example.com")
    assert tool == OPEN_URL
    assert value == "https://example.com"


def test_visit_bare_domain():
    tool, _, value = classify("visit example.com")
    assert tool == OPEN_URL
    assert value == "https://example.com"


def test_bare_domain_with_path_and_query():
    tool, _, value = classify("open example.com/path?q=test")
    assert tool == OPEN_URL
    assert value == "https://example.com/path?q=test"


def test_ngrok_style_domain():
    tool, _, value = classify("open my-ngrok-url.example.dev")
    assert tool == OPEN_URL
    assert value == "https://my-ngrok-url.example.dev"


def test_localhost_bare():
    tool, _, value = classify("open localhost:3000")
    assert tool == OPEN_URL
    assert value == "http://localhost:3000"


def test_executable_name_not_urlified():
    tool, _, value = classify("open chrome.exe")
    assert tool == OPEN_APP
    assert "chrome.exe" == value or "chrome" == value


def test_plain_word_not_urlified():
    tool, _, value = classify("open notepad")
    assert tool == OPEN_APP


# ---------------------------------------------------------------------------
# ROUTING — known websites / apps / search stay separate
# ---------------------------------------------------------------------------

def test_known_webapp_route():
    tool, _, value = classify("open youtube")
    assert tool == OPEN_APP
    assert value == "youtube"


def test_known_webapp_github():
    tool, _, value = classify("open github")
    assert tool == OPEN_APP
    assert value == "github"


def test_known_webapp_with_domain_uses_generic_route():
    tool, _, value = classify("open youtube.com")
    assert tool == OPEN_URL
    assert value == "https://youtube.com"


def test_desktop_app_route():
    tool, _, value = classify("open chrome")
    assert tool == OPEN_APP


def test_search_google_stays_search():
    tool, _, value = classify("search Python on Google")
    assert tool == WEB_SEARCH
    assert "python" in value


def test_search_youtube_stays_search():
    tool, _, value = classify("search Minecraft tutorials on YouTube")
    assert tool == YT_SEARCH
    assert "minecraft" in value


def test_multi_command_not_swallowed():
    assert registry.route_fast_path("open youtube and search dogs") is None
    assert registry.route_fast_path("open https://a.com and search b") is None


# ---------------------------------------------------------------------------
# EXECUTION — URLs never reach subprocess
# ---------------------------------------------------------------------------

def test_open_url_executes_via_browser(monkeypatch):
    opened = []
    monkeypatch.setattr(tr.webbrowser, "open_new_tab", opened.append)

    def _no_popen(*args, **kwargs):
        raise AssertionError("URL must never reach subprocess.Popen")

    monkeypatch.setattr(tr.subprocess, "Popen", _no_popen)

    result = registry.execute("open_url", url="https://example.com/x?y=1")
    assert result["success"] is True
    assert opened == ["https://example.com/x?y=1"]
    assert result["verified"] is True
    assert result["metadata"]["url"] == "https://example.com/x?y=1"


def test_open_url_rejects_unsafe_scheme(monkeypatch):
    monkeypatch.setattr(tr.webbrowser, "open_new_tab", lambda u: True)

    def _no_popen(*args, **kwargs):
        raise AssertionError("URL must never reach subprocess.Popen")

    monkeypatch.setattr(tr.subprocess, "Popen", _no_popen)

    result = registry.execute("open_url", url="javascript:alert(1)")
    assert result["success"] is False
    assert "url" in (result.get("error") or "").lower() or "http" in (
        result.get("error") or ""
    ).lower()


def test_open_url_rejects_file_scheme(monkeypatch):
    monkeypatch.setattr(tr.webbrowser, "open_new_tab", lambda u: True)
    result = registry.execute("open_url", url="file:///etc/passwd")
    assert result["success"] is False


def test_open_application_redirects_urls_to_browser(monkeypatch):
    opened = []
    monkeypatch.setattr(tr.webbrowser, "open_new_tab", opened.append)

    def _no_popen(*args, **kwargs):
        raise AssertionError("URL must never reach subprocess.Popen")

    monkeypatch.setattr(tr.subprocess, "Popen", _no_popen)

    result = registry.execute(
        "open_application",
        app_name="https://example.com/Path/With?q=Case",
    )
    assert result["success"] is True
    assert opened == ["https://example.com/Path/With?q=Case"]
    assert result["metadata"]["url_dispatched"] is True


def test_fast_path_url_end_to_end(monkeypatch):
    opened = []
    monkeypatch.setattr(tr.webbrowser, "open_new_tab", opened.append)

    tool, arg, value = classify("open https://example.com")
    result = registry.execute(tool, **{arg: value})
    assert result["success"] is True
    assert opened == ["https://example.com"]


# ---------------------------------------------------------------------------
# LLM-GENERATED TOOL CALLS
# ---------------------------------------------------------------------------

def test_llm_tool_call_open_url_parses_and_executes(monkeypatch):
    opened = []
    monkeypatch.setattr(tr.webbrowser, "open_new_tab", opened.append)

    calls = tool_call_parser.parse_text(
        '{"name": "open_url", "arguments": '
        '{"url": "https://example.com"}}'
    )
    assert calls and calls[0].name == "open_url"
    result = registry.execute(calls[0].name, **calls[0].arguments)
    assert result["success"] is True
    assert opened == ["https://example.com"]


def test_open_url_schema_present():
    schemas = registry.get_tool_schemas_for_llm()
    names = {s["function"]["name"] for s in schemas}
    assert "open_url" in names
    open_url_schema = next(
        s for s in schemas if s["function"]["name"] == "open_url"
    )
    props = open_url_schema["function"]["parameters"]["properties"]
    assert "url" in props
    assert props["url"]["type"] == "string"
    assert "url" in open_url_schema["function"]["parameters"]["required"]