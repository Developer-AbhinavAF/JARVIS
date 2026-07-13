"""Test suite for the new NLP pipeline.

Tests intent classification, entity extraction, parameter parsing,
and tool routing for all supported intents.
"""

import sys
import os

# Add the project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jarvis.nlp.normalizer import normalize
from jarvis.nlp.synonyms import expand_synonyms, resolve_platform, resolve_app
from jarvis.nlp.patterns import PatternBank
from jarvis.nlp.confidence import ConfidenceScorer, confidence_scorer
from jarvis.nlp.entity_extractor import EntityExtractor
from jarvis.nlp.parameter_parser import ParameterParser
from jarvis.nlp.intent_classifier import IntentClassifier, intent_classifier
from jarvis.nlp.command_parser import CommandParser
from jarvis.nlp.tool_router import NLPToolRouter, nlp_tool_router


def test_normalizer():
    """Test text normalization."""
    print("\n=== Testing Normalizer ===")
    
    tests = [
        ("Open YouTube", "open youtube"),
        ("  hello   world  ", "hello world"),
        ("What's the weather?", "what is the weather?"),
        ("I can't open chrome", "i cannot open chrome"),
        ("kholo youtube", "open youtube"),
        ("play karo music", "play music"),
        ("search karo AI on youtube", "search ai on youtube"),
    ]
    
    for input_text, expected in tests:
        result = normalize(input_text)
        status = "OK" if result == expected else "FAIL"
        print(f"  {status}: '{input_text}' -> '{result}' (expected: '{expected}')")
    
    print("  Normalizer tests complete.")


def test_synonyms():
    """Test synonym expansion."""
    print("\n=== Testing Synonyms ===")
    
    # Platform resolution
    platform_tests = [
        ("youtube", "youtube"),
        ("yt", "youtube"),
        ("github", "github"),
        ("git hub", "github"),
        ("ig", "instagram"),
        ("fb", "facebook"),
    ]
    
    for name, expected in platform_tests:
        result = resolve_platform(name)
        status = "OK" if result == expected else "FAIL"
        print(f"  {status}: Platform '{name}' -> '{result}' (expected: '{expected}')")
    
    # App resolution
    app_tests = [
        ("vscode", "vscode"),
        ("vs code", "vscode"),
        ("visual studio code", "vscode"),
        ("chrome", "chrome"),
        ("google chrome", "chrome"),
    ]
    
    for name, expected in app_tests:
        result = resolve_app(name)
        status = "OK" if result == expected else "FAIL"
        print(f"  {status}: App '{name}' -> '{result}' (expected: '{expected}')")
    
    print("  Synonym tests complete.")


def test_intent_classification():
    """Test intent classification with natural language variations."""
    print("\n=== Testing Intent Classification ===")
    
    test_cases = [
        # OPEN_WEBSITE
        ("open youtube", "OPEN_WEBSITE"),
        ("launch youtube", "OPEN_WEBSITE"),
        ("go to youtube", "OPEN_WEBSITE"),
        ("youtube kholo", "OPEN_WEBSITE"),
        ("open yt", "OPEN_WEBSITE"),
        ("youtube", "OPEN_WEBSITE"),
        ("open github", "OPEN_WEBSITE"),
        ("open chatgpt", "OPEN_WEBSITE"),
        ("open gmail", "OPEN_WEBSITE"),
        ("open reddit", "OPEN_WEBSITE"),
        
        # OPEN_APP
        ("open chrome", "OPEN_APP"),
        ("launch vscode", "OPEN_APP"),
        ("start discord", "OPEN_APP"),
        ("run notepad", "OPEN_APP"),
        ("open calculator", "OPEN_APP"),
        ("open settings", "OPEN_APP"),
        ("open paint", "OPEN_APP"),
        ("open obs", "OPEN_APP"),
        
        # CLOSE_APP
        ("close chrome", "CLOSE_APP"),
        ("kill notepad", "CLOSE_APP"),
        ("stop discord", "CLOSE_APP"),
        
        # SEARCH_YOUTUBE
        ("search AI on youtube", "SEARCH_YOUTUBE"),
        ("find music on youtube", "SEARCH_YOUTUBE"),
        ("search for python tutorials on yt", "SEARCH_YOUTUBE"),
        
        # SEARCH_ON_PLATFORM
        ("search AI on github", "SEARCH_ON_PLATFORM"),
        ("search python on reddit", "SEARCH_ON_PLATFORM"),
        ("search machine learning on wikipedia", "SEARCH_ON_PLATFORM"),
        ("search javascript on stackoverflow", "SEARCH_ON_PLATFORM"),
        ("search headphones on amazon", "SEARCH_ON_PLATFORM"),
        
        # SEARCH_WEB
        ("search AI", "SEARCH_WEB"),
        ("google python", "SEARCH_WEB"),
        ("look up machine learning", "SEARCH_WEB"),
        ("what is quantum computing", "SEARCH_WEB"),
        ("how to learn python", "SEARCH_WEB"),
        ("who is Elon Musk", "SEARCH_WEB"),
        
        # PLAY_YOUTUBE
        ("play shape of you on youtube", "PLAY_YOUTUBE"),
        ("play despacito", "PLAY_MUSIC"),
        ("watch lofi hip hop on youtube", "PLAY_YOUTUBE"),
        
        # PLAY_SPOTIFY
        ("play believer on spotify", "PLAY_SPOTIFY"),
        ("play my playlist on spotify", "PLAY_SPOTIFY"),
        
        # GET_WEATHER
        ("weather in Mumbai", "GET_WEATHER"),
        ("what's the weather in Delhi", "GET_WEATHER"),
        ("forecast in London", "GET_WEATHER"),
        ("temperature in New York", "GET_WEATHER"),
        
        # GET_NEWS
        ("latest news", "GET_NEWS"),
        ("news about AI", "GET_NEWS"),
        ("headlines about technology", "GET_NEWS"),
        
        # SYSTEM_STATUS
        ("system status", "SYSTEM_STATUS"),
        ("computer status", "SYSTEM_STATUS"),
        ("pc stats", "SYSTEM_STATUS"),
        ("cpu usage", "SYSTEM_STATUS"),
        
        # VOLUME_CONTROL
        ("volume up", "VOLUME_CONTROL"),
        ("volume down", "VOLUME_CONTROL"),
        ("mute", "VOLUME_CONTROL"),
        ("unmute", "VOLUME_CONTROL"),
        ("set volume to 50", "VOLUME_CONTROL"),
        
        # BRIGHTNESS_CONTROL
        ("brightness up", "BRIGHTNESS_CONTROL"),
        ("brightness down", "BRIGHTNESS_CONTROL"),
        ("make it brighter", "BRIGHTNESS_CONTROL"),
        ("set brightness to 80", "BRIGHTNESS_CONTROL"),
        
        # SCREENSHOT
        ("take screenshot", "SCREENSHOT"),
        ("screenshot", "SCREENSHOT"),
        ("capture screen", "SCREENSHOT"),
        
        # SYSTEM_POWER
        ("shutdown pc", "SYSTEM_POWER"),
        ("restart computer", "SYSTEM_POWER"),
        ("lock pc", "SYSTEM_POWER"),
        ("sleep computer", "SYSTEM_POWER"),
        
        # CALCULATOR
        ("calculate 2 + 2", "CALCULATOR"),
        ("what is 10 * 5", "CALCULATOR"),
        ("2 + 2", "CALCULATOR"),
        
        # TIMER
        ("set timer for 5 minutes", "TIMER"),
        ("timer 30 seconds", "TIMER"),
        ("remind me in 10 minutes", "TIMER"),
        
        # DATETIME
        ("what time is it", "DATETIME"),
        ("current date", "DATETIME"),
        ("what day is it today", "DATETIME"),
        
        # JOKE
        ("tell me a joke", "JOKE"),
        ("joke", "JOKE"),
        ("make me laugh", "JOKE"),
        
        # QUOTE
        ("give me a quote", "QUOTE"),
        ("inspire me", "QUOTE"),
        ("motivational quote", "QUOTE"),
        
        # SAVE_MEMORY
        ("remember this", "SAVE_MEMORY"),
        ("save this to memory", "SAVE_MEMORY"),
        ("note this", "SAVE_MEMORY"),
        
        # RECALL_MEMORY
        ("what do you know about AI", "RECALL_MEMORY"),
        ("recall my notes", "RECALL_MEMORY"),
        
        # NASA
        ("nasa apod", "NASA_APOD"),
        ("picture of the day", "NASA_APOD"),
        ("mars rover photos", "NASA_MARS"),
        ("where is the iss", "ISS_LOCATION"),
        
        # STOCK
        ("stock price AAPL", "STOCK_QUOTE"),
        ("AAPL stock", "STOCK_QUOTE"),
        
        # TODO
        ("add todo buy groceries", "ADD_TODO"),
        ("remind me to call mom", "ADD_TODO"),
        ("list my todos", "LIST_TODOS"),
        
        # CHAT (fallback)
        ("hello", "CHAT"),
        ("how are you", "CHAT"),
        ("tell me about yourself", "CHAT"),
    ]
    
    correct = 0
    total = len(test_cases)
    
    for text, expected_intent in test_cases:
        result = intent_classifier.classify(text)
        status = "OK" if result.intent == expected_intent else "FAIL"
        if result.intent == expected_intent:
            correct += 1
        print(f"  {status}: '{text}' -> {result.intent} (expected: {expected_intent}, conf: {result.confidence:.2f})")
    
    accuracy = (correct / total) * 100
    print(f"\n  Accuracy: {correct}/{total} ({accuracy:.1f}%)")


def test_confidence_scoring():
    """Test confidence scoring system."""
    print("\n=== Testing Confidence Scoring ===")
    
    scorer = ConfidenceScorer()
    
    tests = [
        (0.95, "open_app", True, "auto_execute"),
        (0.90, "web_search", True, "execute"),
        (0.85, "calculator", True, "confirm"),
        (0.75, None, True, "low"),
        (0.50, None, False, "fallback"),
        (0.90, "system_power", True, "execute"),  # Destructive at 0.90 = execute with confirmation
    ]
    
    for confidence, action, has_entity, expected_level in tests:
        result = scorer.score(confidence, action=action, has_entity=has_entity)
        status = "OK" if result.level == expected_level else "FAIL"
        print(f"  {status}: conf={confidence:.2f}, action={action}, entity={has_entity} -> {result.level} (expected: {expected_level})")
    
    print("  Confidence scoring tests complete.")


def test_parameter_parsing():
    """Test parameter parsing for different intents."""
    print("\n=== Testing Parameter Parsing ===")
    
    from jarvis.nlp.entity_extractor import ExtractionResult, Entity
    
    parser = ParameterParser()
    
    # Test weather parsing
    entities = ExtractionResult()
    entities.entities["city"] = Entity(name="city", value="Mumbai", raw_value="Mumbai")
    result = parser.parse("GET_WEATHER", entities)
    print(f"  Weather: tool={result.tool_name}, params={result.params}")
    assert result.tool_name == "get_weather"
    assert result.params.get("city") == "Mumbai"
    
    # Test search parsing
    entities = ExtractionResult()
    entities.entities["query"] = Entity(name="query", value="python tutorials", raw_value="python tutorials")
    result = parser.parse("SEARCH_WEB", entities)
    print(f"  Search: tool={result.tool_name}, params={result.params}")
    assert result.tool_name == "web_search"
    assert result.params.get("query") == "python tutorials"
    
    # Test calculator parsing
    entities = ExtractionResult()
    entities.entities["expression"] = Entity(name="expression", value="2 + 2", raw_value="2 + 2")
    result = parser.parse("CALCULATOR", entities)
    print(f"  Calculator: tool={result.tool_name}, params={result.params}")
    assert result.tool_name == "calculator"
    assert result.params.get("expression") == "2 + 2"
    
    print("  Parameter parsing tests complete.")


def test_tool_routing():
    """Test complete tool routing pipeline."""
    print("\n=== Testing Tool Routing ===")
    
    router = NLPToolRouter()
    
    test_cases = [
        ("open youtube", "open_app", True),
        ("search AI on github", "web_search", True),
        ("weather in Mumbai", "get_weather", True),
        ("what time is it", "get_datetime", True),
        ("tell me a joke", "get_joke", True),
        ("take screenshot", "screenshot", True),
        ("volume up", "volume_control", True),
        ("system status", "get_system_stats", True),
        ("calculate 2 + 2", "calculator", True),
        ("set timer for 5 minutes", "timer", True),
        ("hello", "chat", True),  # Routes to chat tool via CHAT intent
        ("how are you", "chat", True),  # Routes to chat tool via CHAT intent
    ]
    
    for query, expected_tool, should_execute in test_cases:
        route = router.route(query)
        tool_match = route.tool_name == expected_tool if expected_tool else True
        exec_match = route.should_execute == should_execute
        status = "OK" if tool_match and exec_match else "FAIL"
        print(f"  {status}: '{query}' -> tool={route.tool_name}, execute={route.should_execute}, conf={route.confidence:.2f}")
        if not tool_match:
            print(f"      Expected tool: {expected_tool}")
        if not exec_match:
            print(f"      Expected execute: {should_execute}")
    
    print("  Tool routing tests complete.")


def test_command_parsing():
    """Test multi-command parsing."""
    print("\n=== Testing Command Parsing ===")
    
    parser = CommandParser()
    
    tests = [
        ("open youtube", 1),
        ("open chrome and open firefox", 2),
        ("search AI then search python", 2),
        ("open youtube and search music on youtube", 2),
    ]
    
    for text, expected_count in tests:
        chain = parser.parse(text)
        status = "OK" if chain.count == expected_count else "FAIL"
        print(f"  {status}: '{text}' -> {chain.count} commands (expected: {expected_count})")
        if chain.count != expected_count:
            for i, cmd in enumerate(chain.commands):
                print(f"      Command {i+1}: {cmd.text}")
    
    print("  Command parsing tests complete.")


def test_hinglish_support():
    """Test Hindi/Hinglish variations."""
    print("\n=== Testing Hinglish Support ===")
    
    test_cases = [
        ("youtube kholo", "OPEN_WEBSITE"),
        ("chrome kholo", "OPEN_APP"),
        ("music chalao", "PLAY_MUSIC"),
        ("AI dhundho", "SEARCH_WEB"),
        ("screenshot maro", "SCREENSHOT"),
        ("volume badhao", "VOLUME_CONTROL"),
    ]
    
    for text, expected_intent in test_cases:
        result = intent_classifier.classify(text)
        status = "OK" if result.intent == expected_intent else "FAIL"
        print(f"  {status}: '{text}' -> {result.intent} (expected: {expected_intent})")
    
    print("  Hinglish support tests complete.")


def main():
    """Run all tests."""
    print("=" * 60)
    print("  JARVIS NLP Pipeline Test Suite")
    print("=" * 60)
    
    try:
        test_normalizer()
        test_synonyms()
        test_intent_classification()
        test_confidence_scoring()
        test_parameter_parsing()
        test_tool_routing()
        test_command_parsing()
        test_hinglish_support()
        
        print("\n" + "=" * 60)
        print("  All tests completed!")
        print("=" * 60)
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
