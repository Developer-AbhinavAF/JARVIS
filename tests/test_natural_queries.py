"""Natural language query test to verify NLP pattern improvements."""
import sys
sys.path.insert(0, "D:\\AI\\JARVIS")

from jarvis.tool_metadata import catalog

# Test cases: (query, expected_tool)
NATURAL_QUERIES = [
    # System status
    ("cpu usage right now", "system_status"),
    ("how much ram am i using", "system_status"),
    ("how is my system doing", "system_status"),
    ("how many apps are open", "list_apps"),
    
    # Battery
    ("how much battery do i have", "battery_status"),
    ("is my laptop charging", "battery_status"),
    
    # Datetime
    ("what time is it right now", "datetime"),
    ("current date and time", "datetime"),
    
    # Volume
    ("make it louder", "volume_control"),
    ("turn it up", "volume_control"),
    
    # Brightness
    ("turn down the brightness", "brightness_control"),
    ("make the screen dimmer", "brightness_control"),
    
    # Weather
    ("whats the weather like", "weather"),
    ("is it going to rain today", "weather"),
    ("how hot is it in dubai", "weather"),
    
    # Jokes
    ("tell me something funny", "joke"),
    ("got any jokes", "joke"),
    
    # Quotes
    ("give me some inspiration", "quote"),
    ("say something motivational", "quote"),
    
    # Calculator
    ("multiply 5 by 3", "calculator"),
    ("10 divided by 2", "calculator"),
    
    # Clipboard
    ("paste from clipboard", "clipboard_paste"),
    
    # Todo
    ("add buy milk to my todo list", "add_todo"),
    ("show me my tasks", "list_todos"),
    
    # Window control
    ("minimize this window", "window_control"),
    ("maximize the screen", "window_control"),
    ("close this window", "window_control"),
    
    # List apps
    ("show me open programs", "list_apps"),
    
    # News
    ("give me the news", "news"),
    
    # NASA
    ("show me a picture from space", "nasa_apod"),
    ("nasa photo of the day", "nasa_apod"),
    
    # Stocks
    ("how is tesla doing", "stock_quote"),
    
    # Greetings
    ("hello", "greeting"),
    ("hi", "greeting"),
    ("how are you", "greeting"),
    ("who are you", "greeting"),
    
    # General search
    ("find me some recipes", "web_search"),
    ("tell me about neural networks", "web_search"),
    ("explain recursion", "web_search"),
]

def test_natural_queries():
    passed = 0
    failed = 0
    
    for query, expected_tool in NATURAL_QUERIES:
        # Use command engine to match
        from jarvis.command_engine import CommandEngine
        engine = CommandEngine()
        result = engine.process(query)
        
        if result.tool_name == expected_tool:
            passed += 1
            print(f"  [+] PASS: '{query}' -> {result.tool_name}")
        else:
            failed += 1
            print(f"  [-] FAIL: '{query}' -> got '{result.tool_name}', expected '{expected_tool}'")
    
    print(f"\n  RESULTS: {passed}/{passed+failed} passed, {failed}/{passed+failed} failed")
    return failed == 0

if __name__ == "__main__":
    print("=" * 60)
    print("  NATURAL LANGUAGE QUERY TEST")
    print("=" * 60)
    success = test_natural_queries()
    sys.exit(0 if success else 1)
