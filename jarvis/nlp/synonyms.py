"""Synonym expansion for JARVIS NLP pipeline.

Maps natural language variations to canonical tool/intent names.
"""

from __future__ import annotations

import re

# ── Verb synonyms → canonical action ──
VERB_SYNONYMS: dict[str, str] = {
    # open / launch
    "open": "open",
    "launch": "open",
    "start": "open",
    "run": "open",
    "go to": "open",
    "visit": "open",
    "navigate to": "open",
    "browse to": "open",
    "fire up": "open",
    "boot up": "open",
    "spin up": "open",
    "bring up": "open",
    "pull up": "open",
    "load": "open",
    "access": "open",

    # close
    "close": "close",
    "shut": "close",
    "kill": "close",
    "stop": "close",
    "quit": "close",
    "exit": "close",
    "terminate": "close",
    "end": "close",
    "turn off": "close",

    # play
    "play": "play",
    "watch": "play",
    "listen to": "play",
    "stream": "play",
    "run": "play",
    "put on": "play",
    "start playing": "play",

    # search
    "search": "search",
    "find": "search",
    "look up": "search",
    "google": "search",
    "look for": "search",
    "seek": "search",
    "query": "search",
    "check": "search",
    "hunt": "search",
    "scout": "search",

    # volume
    "volume up": "volume_up",
    "volume down": "volume_down",
    "louder": "volume_up",
    "softer": "volume_down",
    "increase volume": "volume_up",
    "decrease volume": "volume_down",
    "raise volume": "volume_up",
    "lower volume": "volume_down",
    "turn up": "volume_up",
    "turn down": "volume_down",
    "mute": "mute",
    "unmute": "unmute",
    "silence": "mute",
    "unsilence": "unmute",

    # brightness
    "brighter": "brightness_up",
    "dimmer": "brightness_down",
    "brightness up": "brightness_up",
    "brightness down": "brightness_down",
    "increase brightness": "brightness_up",
    "decrease brightness": "brightness_down",

    # system
    "shutdown": "shutdown",
    "shut down": "shutdown",
    "power off": "shutdown",
    "poweroff": "shutdown",
    "restart": "restart",
    "reboot": "restart",
    "sleep": "sleep",
    "hibernate": "sleep",
    "lock": "lock",
    "lock pc": "lock",
    "lock computer": "lock",

    # screenshot
    "screenshot": "screenshot",
    "screen shot": "screenshot",
    "screen capture": "screenshot",
    "capture screen": "screenshot",
    "take screenshot": "screenshot",

    # clipboard
    "copy to clipboard": "clipboard_copy",
    "clipboard": "clipboard_get",
    "what's on clipboard": "clipboard_get",
    "what is on clipboard": "clipboard_get",

    # memory
    "remember": "save_memory",
    "save": "save_memory",
    "store": "save_memory",
    "keep": "save_memory",
    "note": "save_memory",
    "note down": "save_memory",

    # recall
    "recall": "recall_memory",
    "what do you know": "recall_memory",
    "what do i know": "recall_memory",
    "tell me about": "recall_memory",

    # calculator
    "calculate": "calculate",
    "calc": "calculate",
    "compute": "calculate",
    "solve": "calculate",
    "evaluate": "calculate",

    # weather
    "weather": "weather",
    "forecast": "weather",
    "temperature": "weather",

    # news
    "news": "news",
    "headlines": "news",
    "latest news": "news",

    # timer
    "timer": "timer",
    "alarm": "timer",
    "remind me in": "timer",
    "set timer": "timer",

    # joke
    "joke": "joke",
    "tell me a joke": "joke",
    "make me laugh": "joke",

    # quote
    "quote": "quote",
    "inspire me": "quote",
    "motivational quote": "quote",

    # datetime
    "time": "datetime",
    "date": "datetime",
    "what time": "datetime",
    "what date": "datetime",
    "what day": "datetime",

    # system status
    "system status": "system_status",
    "computer status": "system_status",
    "pc status": "system_status",
    "how's my pc": "system_status",
    "system stats": "system_status",

    # window control
    "minimize": "window_minimize",
    "maximize": "window_maximize",
    "restore": "window_restore",
    "switch to": "window_switch",
    "focus": "window_focus",
    "show desktop": "show_desktop",

    # file operations
    "create folder": "create_folder",
    "make folder": "create_folder",
    "new folder": "create_folder",
    "delete file": "delete_file",
    "remove file": "delete_file",
    "rename": "rename_file",
    "copy file": "copy_file",
    "move file": "move_file",
    "compress": "compress",
    "extract": "extract",

    # information
    "random fact": "random_fact",
    "tell me a fact": "random_fact",
    "did you know": "random_fact",
    "fun fact": "random_fact",

    # ip
    "ip address": "ip_lookup",
    "what's my ip": "ip_lookup",
    "my ip": "ip_lookup",

    # nasa
    "nasa apod": "nasa_apod",
    "picture of the day": "nasa_apod",
    "astronomy picture": "nasa_apod",
    "mars rover": "nasa_mars",
    "iss location": "iss_location",
    "where is iss": "iss_location",

    # stocks
    "stock price": "stock_quote",
    "stock": "stock_quote",
    "share price": "stock_quote",
    "ticker": "stock_quote",

    # news
    "market news": "market_news",
    "business news": "market_news",
    "financial news": "market_news",
}

# ── Platform / website synonyms ──
PLATFORM_SYNONYMS: dict[str, str] = {
    # YouTube
    "youtube": "youtube",
    "yt": "youtube",
    "youtube.com": "youtube",
    "y t": "youtube",
    "y/t": "youtube",

    # Google
    "google": "google",
    "google.com": "google",

    # GitHub
    "github": "github",
    "github.com": "github",
    "git hub": "github",

    # Spotify
    "spotify": "spotify",
    "spotify.com": "spotify",

    # Reddit
    "reddit": "reddit",
    "reddit.com": "reddit",

    # Twitter / X
    "twitter": "x",
    "x.com": "x",
    "x": "x",

    # Instagram
    "instagram": "instagram",
    "ig": "instagram",
    "insta": "instagram",

    # Facebook
    "facebook": "facebook",
    "fb": "facebook",
    "meta": "facebook",

    # Netflix
    "netflix": "netflix",

    # Amazon
    "amazon": "amazon",
    "amazon.com": "amazon",

    # LinkedIn
    "linkedin": "linkedin",
    "linkedin.com": "linkedin",

    # WhatsApp
    "whatsapp": "whatsapp",
    "whats app": "whatsapp",

    # Stack Overflow
    "stackoverflow": "stackoverflow",
    "stack overflow": "stackoverflow",

    # Wikipedia
    "wikipedia": "wikipedia",
    "wiki": "wikipedia",

    # Gmail
    "gmail": "gmail",
    "google mail": "gmail",

    # ChatGPT
    "chatgpt": "chatgpt",
    "chat gpt": "chatgpt",
    "openai": "chatgpt",

    # Discord
    "discord": "discord",
    "discord.com": "discord",

    # Twitch
    "twitch": "twitch",
    "twitch.tv": "twitch",

    # Spotify Music
    "spotify music": "spotify_music",
    "spotify playlist": "spotify_playlist",

    # YouTube Music
    "youtube music": "youtube_music",
    "yt music": "youtube_music",
    "youtube music video": "youtube_music",
}

# ── Application name synonyms ──
APP_SYNONYMS: dict[str, str] = {
    "vscode": "vscode",
    "vs code": "vscode",
    "visual studio code": "vscode",
    "visual studio": "visual_studio",
    "cursor": "cursor",
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "mozilla firefox": "firefox",
    "edge": "edge",
    "microsoft edge": "edge",
    "explorer": "explorer",
    "file explorer": "explorer",
    "windows explorer": "explorer",
    "notepad": "notepad",
    "notepad++": "notepadpp",
    "notepad plus plus": "notepadpp",
    "calculator": "calculator",
    "calc": "calculator",
    "paint": "paint",
    "mspaint": "paint",
    "word": "word",
    "microsoft word": "word",
    "excel": "excel",
    "microsoft excel": "excel",
    "powerpoint": "powerpoint",
    "microsoft powerpoint": "powerpoint",
    "outlook": "outlook",
    "microsoft outlook": "outlook",
    "terminal": "terminal",
    "cmd": "cmd",
    "command prompt": "cmd",
    "command line": "cmd",
    "powershell": "powershell",
    "ps": "powershell",
    "settings": "settings",
    "control panel": "control_panel",
    "task manager": "task_manager",
    "obs": "obs",
    "obs studio": "obs",
    "obs studio": "obs",
    "spotify": "spotify",
    "discord": "discord",
    "steam": "steam",
    "epic games": "epic_games",
    "epic": "epic_games",
    "whatsapp": "whatsapp",
    "telegram": "telegram",
    "teams": "teams",
    "microsoft teams": "teams",
    "zoom": "zoom",
    "slack": "slack",
    "skype": "skype",
    "vlc": "vlc",
    "media player": "vlc",
    "itunes": "itunes",
    "snipping tool": "snipping_tool",
    "wordpad": "wordpad",
    "onenote": "onenote",
    "microsoft onenote": "onenote",
    "sublime": "sublime",
    "sublime text": "sublime",
    "intellij": "intellij",
    "intellij idea": "intellij",
    "pycharm": "pycharm",
    "webstorm": "webstorm",
    "android studio": "android_studio",
    "blender": "blender",
    "gimp": "gimp",
    "photoshop": "photoshop",
    "premiere": "premiere",
    "after effects": "after_effects",
}

# ── Semantic intent keywords ──
# Maps natural language phrases to intent keywords for semantic matching
SEMANTIC_INTENT_KEYWORDS: dict[str, list[str]] = {
    "open_website": ["open", "launch", "go to", "visit", "navigate", "browse", "take me to", "i want to see", "i need to see"],
    "open_app": ["open", "launch", "start", "run", "fire up", "boot up", "bring up"],
    "close_app": ["close", "shut", "kill", "stop", "quit", "exit", "terminate", "end"],
    "search_web": ["search", "find", "look up", "google", "look for", "seek", "query", "check", "hunt", "scout", "browse for", "search for"],
    "search_on_platform": ["search on", "find on", "look up on", "search in", "find in"],
    "play_music": ["play", "listen to", "stream", "put on", "start playing", "i want to hear", "i feel like listening", "i want some music", "need something relaxing", "need to relax"],
    "play_youtube": ["play on youtube", "watch on youtube", "play youtube", "watch youtube", "youtube play"],
    "play_spotify": ["play on spotify", "spotify play", "play spotify"],
    "get_weather": ["weather", "forecast", "temperature", "how hot", "how cold", "is it raining", "is it going to rain", "do i need an umbrella"],
    "get_news": ["news", "headlines", "latest news", "what's happening", "current events", "breaking news"],
    "system_status": ["system status", "computer status", "pc status", "how's my pc", "system stats", "cpu usage", "ram usage", "memory usage", "disk usage", "how is my system", "how much ram", "how much cpu", "how much battery", "is my laptop charging"],
    "volume_control": ["volume", "louder", "softer", "mute", "unmute", "silence", "make it louder", "make it quieter", "turn it up", "turn it down", "volume up", "volume down"],
    "brightness_control": ["brightness", "brighter", "dimmer", "dim", "bright", "turn down the brightness", "turn up the brightness", "make the screen dimmer", "make the screen brighter"],
    "screenshot": ["screenshot", "screen shot", "screen capture", "capture screen", "take screenshot", "capture my screen"],
    "system_power": ["shutdown", "shut down", "power off", "restart", "reboot", "sleep", "hibernate", "lock", "lock pc", "lock computer", "lock screen"],
    "clipboard": ["clipboard", "copy", "paste", "what's on clipboard", "paste from clipboard", "show clipboard"],
    "calculator": ["calculate", "calc", "compute", "solve", "evaluate", "math", "multiply", "divide", "add", "subtract", "what is", "what's"],
    "timer": ["timer", "alarm", "remind me in", "set timer", "countdown"],
    "datetime": ["time", "date", "day", "what time", "what date", "what day", "current time", "current date", "right now", "currently"],
    "save_memory": ["remember", "save", "store", "keep", "note", "note down", "write down", "don't forget"],
    "recall_memory": ["recall", "what do you know", "what do i know", "tell me about", "search my memory", "search my notes"],
    "window_control": ["minimize", "maximize", "restore", "close window", "switch to", "focus", "show desktop", "minimize this window", "maximize the screen", "close this window"],
    "joke": ["joke", "tell me a joke", "make me laugh", "something funny", "got any jokes", "i'm bored", "entertain me"],
    "quote": ["quote", "inspire me", "motivational quote", "say something motivational", "give me some inspiration", "i need motivation"],
    "flip_coin": ["flip", "toss", "coin", "flip a coin", "heads or tails"],
    "roll_dice": ["roll", "throw", "dice", "roll a dice"],
    "datetime": ["time", "date", "day", "what time", "what date", "what day"],
    "nasa_apod": ["nasa", "apod", "astronomy picture", "picture of the day", "show me a picture from space", "nasa photo of the day"],
    "nasa_mars": ["mars rover", "mars photo", "mars picture", "nasa mars"],
    "iss_location": ["iss", "international space station", "where is iss", "iss location"],
    "stock_quote": ["stock", "share", "price", "quote", "how is", "how's", "doing", "performing", "trading"],
    "random_fact": ["fact", "trivia", "did you know", "tell me a fact", "fun fact", "random fact"],
    "ip_lookup": ["ip address", "what's my ip", "my ip", "ip lookup"],
    "add_todo": ["add todo", "create todo", "make todo", "add task", "create task", "remind me to", "don't forget to"],
    "list_todos": ["list todos", "show todos", "what are my todos", "show my tasks", "what do i need to do"],
    "add_note": ["add note", "create note", "make note", "take note"],
    "greeting": ["hello", "hi", "hey", "howdy", "good morning", "good afternoon", "good evening", "how are you", "who are you", "thanks", "bye"],
    "web_search": ["search", "find", "look up", "google", "what is", "who is", "how to", "how do", "why is", "where is", "tell me about", "explain", "define", "describe", "find me", "i want to know", "i need information"],
}


def expand_synonyms(text: str) -> str:
    """Expand synonyms in normalized text.

    Does not replace platform/app names - those are handled by entity extraction.
    Only expands verb/action synonyms.
    """
    result = text
    for synonym, canonical in sorted(VERB_SYNONYMS.items(), key=lambda x: len(x[0]), reverse=True):
        pattern = rf"\b{re.escape(synonym)}\b"
        result = re.sub(pattern, canonical, result, flags=re.IGNORECASE)
    return result


def resolve_platform(name: str) -> str | None:
    """Resolve a platform name to its canonical form."""
    return PLATFORM_SYNONYMS.get(name.lower().strip())


def resolve_app(name: str) -> str | None:
    """Resolve an application name to its canonical form."""
    return APP_SYNONYMS.get(name.lower().strip())


def get_semantic_keywords(intent: str) -> list[str]:
    """Get semantic keywords for an intent."""
    return SEMANTIC_INTENT_KEYWORDS.get(intent, [])
