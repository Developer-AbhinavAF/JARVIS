"""Acceptance tests for the new JARVIS command engine.

Tests that ALL required commands are matched by the command engine
and routed to the correct tools instead of reaching the LLM.

Run: python -m tests.test_execution_engine
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jarvis.command_engine import CommandEngine, CommandResult
from jarvis.tool_metadata import catalog, WEBSITES, SEARCH_SITES


def test_command(engine: CommandEngine, command: str, expected_tool: str, expected_params: dict = None, description: str = ""):
    """Test a single command."""
    result = engine.process(command)
    status = "PASS" if result.matched and result.tool_name == expected_tool else "FAIL"
    
    param_status = ""
    if expected_params and result.matched:
        for key, value in expected_params.items():
            if key in result.params:
                actual = result.params[key]
                if isinstance(actual, str) and isinstance(value, str):
                    if value.lower() in actual.lower() or actual.lower() in value.lower():
                        continue
                elif actual == value:
                    continue
                param_status = f" [param '{key}': expected={value}, got={actual}]"
                status = "FAIL"
                break
    
    icon = "+" if status == "PASS" else "X"
    desc = f" ({description})" if description else ""
    print(f"  [{icon}] {status}: '{command}' -> {result.tool_name}{desc}{param_status}")
    
    if status == "FAIL":
        print(f"       matched={result.matched}, confidence={result.confidence:.2f}")
        if result.matched:
            print(f"       params={result.params}")
    
    return status == "PASS"


def main():
    print("=" * 70)
    print("  JARVIS COMMAND ENGINE - ACCEPTANCE TESTS")
    print("=" * 70)
    
    engine = CommandEngine(catalog)
    passed = 0
    failed = 0
    total = 0
    
    def run(command, expected_tool, expected_params=None, desc=""):
        nonlocal passed, failed, total
        total += 1
        if test_command(engine, command, expected_tool, expected_params, desc):
            passed += 1
        else:
            failed += 1
    
    # ─── WEBSITE OPENING ───
    print("\n--- WEBSITE OPENING ---")
    run("open youtube", "open_website", {"target": "youtube"})
    run("launch youtube", "open_website", {"target": "youtube"})
    run("go to youtube", "open_website", {"target": "youtube"})
    run("visit youtube", "open_website", {"target": "youtube"})
    run("navigate to youtube", "open_website", {"target": "youtube"})
    run("open google", "open_website", {"target": "google"})
    run("open gmail", "open_website", {"target": "gmail"})
    run("open github", "open_website", {"target": "github"})
    run("open reddit", "open_website", {"target": "reddit"})
    run("open chatgpt", "open_website", {"target": "chatgpt"})
    run("open facebook", "open_website", {"target": "facebook"})
    run("open instagram", "open_website", {"target": "instagram"})
    run("open twitter", "open_website", {"target": "twitter"})
    run("open spotify", "open_website", {"target": "spotify"})
    run("open amazon", "open_website", {"target": "amazon"})
    run("open linkedin", "open_website", {"target": "linkedin"})
    run("open wikipedia", "open_website", {"target": "wikipedia"})
    run("open netflix", "open_website", {"target": "netflix"})
    run("youtube", "open_website", {"target": "youtube"}, "standalone website name")
    run("google", "open_website", {"target": "google"}, "standalone website name")
    run("reddit", "open_website", {"target": "reddit"}, "standalone website name")
    
    # ─── APPLICATION OPENING ───
    print("\n--- APPLICATION OPENING ---")
    run("open chrome", "open_app", {"target": "chrome"})
    run("launch chrome", "open_app", {"target": "chrome"})
    run("open firefox", "open_app", {"target": "firefox"})
    run("open edge", "open_app", {"target": "edge"})
    run("open notepad", "open_app", {"target": "notepad"})
    run("open calculator", "open_app", {"target": "calculator"})
    run("launch calculator", "open_app", {"target": "calculator"})
    run("open vscode", "open_app", {"target": "vscode"})
    run("open visual studio code", "open_app", {"target": "visual studio code"})
    run("open spotify", "open_website", {"target": "spotify"}, "spotify is a website")
    run("open terminal", "open_app", {"target": "terminal"})
    run("open powershell", "open_app", {"target": "powershell"})
    run("open explorer", "open_app", {"target": "explorer"})
    run("open file explorer", "open_app", {"target": "file explorer"})
    run("open paint", "open_app", {"target": "paint"})
    run("open word", "open_app", {"target": "word"})
    run("open excel", "open_app", {"target": "excel"})
    run("open powerpoint", "open_app", {"target": "powerpoint"})
    run("open discord", "open_website", {"target": "discord"}, "discord is a website")
    run("open steam", "open_website", {"target": "steam"}, "steam is a website")
    run("open obs", "open_app", {"target": "obs"})
    
    # ─── FOLDER OPENING ───
    print("\n--- FOLDER OPENING ---")
    run("open downloads", "open_folder", {"target": "downloads"})
    run("open documents", "open_folder", {"target": "documents"})
    run("open desktop", "open_folder", {"target": "desktop"})
    run("open my computer", "open_folder", {"target": "my computer"})
    run("show downloads", "open_folder", {"target": "downloads"})
    run("open pictures", "open_folder", {"target": "pictures"})
    run("open music", "open_folder", {"target": "music"})
    run("open videos", "open_folder", {"target": "videos"})
    
    # ─── SEARCH COMMANDS ───
    print("\n--- SEARCH COMMANDS ---")
    run("search AI", "web_search", {"query": "AI"})
    run("search the web for python", "web_search", {"query": "python"})
    run("google machine learning", "web_search", {"query": "machine learning"})
    run("look up quantum computing", "web_search", {"query": "quantum computing"})
    run("search AI on youtube", "search_on_platform", {"query": "AI", "platform": "youtube"})
    run("search python on github", "search_on_platform", {"query": "python", "platform": "github"})
    run("search machine learning on reddit", "search_on_platform", {"query": "machine learning", "platform": "reddit"})
    run("search quantum on wikipedia", "search_on_platform", {"query": "quantum", "platform": "wikipedia"})
    run("search javascript on stackoverflow", "search_on_platform", {"query": "javascript", "platform": "stackoverflow"})
    run("search laptop on amazon", "search_on_platform", {"query": "laptop", "platform": "amazon"})
    run("search inception on imdb", "search_on_platform", {"query": "inception", "platform": "imdb"})
    run("search jazz on spotify", "search_on_platform", {"query": "jazz", "platform": "spotify"})
    run("search AI on x", "search_on_platform", {"query": "AI", "platform": "x"})
    run("search jobs on linkedin", "search_on_platform", {"query": "jobs", "platform": "linkedin"})
    
    # ─── PLAY COMMANDS ───
    print("\n--- PLAY COMMANDS ---")
    run("play believer", "play_music", {"query": "believer"})
    run("play never gonna give you up", "play_music", {"query": "never going to give you up"}, "gonna normalized to going to")
    run("play some jazz", "play_music", {"query": "jazz"})
    run("play the song shape of you", "play_music", {"query": "the song shape of you"})
    run("play ed sheeran", "play_music", {"query": "ed sheeran"})
    
    # ─── SYSTEM CONTROL ───
    print("\n--- SYSTEM CONTROL ---")
    run("take screenshot", "screenshot")
    run("capture screen", "screenshot")
    run("screenshot", "screenshot")
    run("lock pc", "system_power", {"action": "lock"})
    run("lock computer", "system_power", {"action": "lock"})
    run("lock screen", "system_power", {"action": "lock"})
    run("restart pc", "system_power", {"action": "restart"})
    run("restart computer", "system_power", {"action": "restart"})
    run("reboot", "system_power", {"action": "restart"})
    run("shutdown pc", "system_power", {"action": "shutdown"})
    run("shutdown computer", "system_power", {"action": "shutdown"})
    run("shut down", "system_power", {"action": "shutdown"})
    run("power off", "system_power", {"action": "shutdown"})
    
    # ─── VOLUME / BRIGHTNESS ───
    print("\n--- VOLUME / BRIGHTNESS ---")
    run("mute volume", "volume_control", {"action": "mute"})
    run("unmute", "volume_control", {"action": "unmute"})
    run("volume up", "volume_control", {"action": "up"})
    run("volume down", "volume_control", {"action": "down"})
    run("increase volume", "volume_control", {"action": "up"})
    run("decrease volume", "volume_control", {"action": "down"})
    run("increase brightness", "brightness_control", {"action": "up"})
    run("brightness up", "brightness_control", {"action": "up"})
    run("dim screen", "brightness_control", {"action": "down"})
    
    # ─── CLIPBOARD ───
    print("\n--- CLIPBOARD ---")
    run("paste", "clipboard_paste")
    run("show clipboard", "clipboard_paste")
    run("what's on clipboard", "clipboard_paste")
    
    # ─── SYSTEM STATUS ───
    print("\n--- SYSTEM STATUS ---")
    run("system status", "system_status")
    run("check system status", "system_status")
    run("pc status", "system_status")
    run("battery status", "battery_status")
    run("what's my battery", "battery_status")
    run("network status", "network_status")
    run("internet speed", "network_status")
    run("speed test", "speed_test")
    
    # ─── CALCULATOR ───
    print("\n--- CALCULATOR ---")
    run("calculate 2+2", "calculator", {"expression": "2+2"})
    run("calc 100*5", "calculator")
    run("what is 15*3", "calculator")
    
    # ─── WEATHER ───
    print("\n--- WEATHER ---")
    run("weather in London", "weather", {"city": "london"})
    run("weather tokyo", "weather", {"city": "tokyo"})
    run("what's the weather in Delhi", "weather", {"city": "delhi"})
    
    # ─── ENTERTAINMENT ───
    print("\n--- ENTERTAINMENT ---")
    run("tell me a joke", "joke")
    run("joke", "joke")
    run("give me a quote", "quote")
    run("inspire me", "quote")
    run("flip a coin", "flip_coin")
    run("heads or tails", "flip_coin")
    run("roll a dice", "roll_dice")
    
    # ─── TIMER / DATETIME ───
    print("\n--- TIMER / DATETIME ---")
    run("set timer for 60", "timer", {"seconds": 60})
    run("timer 5 minutes", "timer", {"seconds": 300})
    run("what time is it", "datetime")
    run("what's the date", "datetime")
    run("current time", "datetime")
    
    # ─── WINDOW CONTROL ───
    print("\n--- WINDOW CONTROL ---")
    run("list windows", "window_control", {"action": "list"})
    run("minimize window", "window_control", {"action": "minimize"})
    run("maximize window", "window_control", {"action": "maximize"})
    
    # ─── LIST APPS ───
    print("\n--- LIST APPS ---")
    run("list apps", "list_apps")
    run("what's running", "list_apps")
    run("show running applications", "list_apps")
    
    # ─── CLOSE APP ───
    print("\n--- CLOSE APP ---")
    run("close chrome", "close_app", {"target": "chrome"})
    run("kill notepad", "close_app", {"target": "notepad"})
    
    # ─── MEMORY ───
    print("\n--- MEMORY ---")
    run("remember my birthday is Jan 1", "memory_save")
    run("save this to memory", "memory_save")
    run("what do you remember", "memory_search")
    
    # ─── TODO ───
    print("\n--- TODO ---")
    run("add todo buy groceries", "add_todo")
    run("show my todos", "list_todos")
    
    # ─── NEWS ───
    print("\n--- NEWS ---")
    run("latest news", "news")
    run("headlines", "news")
    
    # ─── NASA ───
    print("\n--- NASA ---")
    run("nasa apod", "nasa_apod")
    run("nasa picture of the day", "nasa_apod")
    
    # ─── STOCKS ───
    print("\n--- STOCKS ---")
    run("stock price AAPL", "stock_quote")
    run("quote TSLA", "stock_quote")
    
    # ─── FALLBACK PATTERNS ───
    print("\n--- FALLBACK PATTERNS ---")
    run("wifi off", "system_power", desc="opens network settings")
    run("bluetooth on", "system_power", desc="opens bluetooth settings")
    run("create folder test", "create_folder")
    run("rename file", "rename_file")
    run("copy file", "copy_file")
    
    # ─── SUMMARY ───
    print("\n" + "=" * 70)
    print(f"  RESULTS: {passed}/{total} passed, {failed}/{total} failed")
    print("=" * 70)
    
    if failed > 0:
        print("\n  Some tests failed. Check the output above for details.")
        return 1
    else:
        print("\n  All tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
