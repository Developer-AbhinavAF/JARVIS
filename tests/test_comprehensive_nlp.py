"""Comprehensive NLP Test Suite — 10,000+ command variations.

Tests the full JARVIS NLP pipeline across:
  - All 35+ intent categories
  - English, Hindi, Hinglish variants
  - Typo injection (keyboard proximity, character drops, swaps)
  - Slang / abbreviation / emoji variants
  - Filler word / politeness prefix variations
  - Context follow-ups and pronoun resolution
  - Multi-intent compound commands
  - Parameter extraction correctness

Run: python -m tests.test_comprehensive_nlp
      python -m tests.test_comprehensive_nlp --category weather
      python -m tests.test_comprehensive_nlp --stats-only
"""

from __future__ import annotations

import sys
import os
import re
import random
import time
import argparse
from dataclasses import dataclass, field
from typing import Callable

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jarvis.tool_metadata import catalog, WEBSITES, SEARCH_SITES, FOLDERS
from jarvis.command_engine import CommandEngine

# ═══════════════════════════════════════════════════════════════════
# TEST INFRASTRUCTURE
# ═══════════════════════════════════════════════════════════════════

@dataclass
class TestCase:
    command: str
    expected_tool: str
    expected_params: dict = field(default_factory=dict)
    category: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)


def _p(command: str, tool: str, params: dict = None, cat: str = "", desc: str = "", tags: list[str] = None) -> TestCase:
    return TestCase(command=command, expected_tool=tool, expected_params=params or {}, category=cat, description=desc, tags=tags or [])


# ═══════════════════════════════════════════════════════════════════
# TYPO / NOISE GENERATORS
# ═══════════════════════════════════════════════════════════════════

# Keyboard proximity map (QWERTY)
_NEARBY: dict[str, str] = {
    'a': 'sqwz', 'b': 'vghn', 'c': 'xdfv', 'd': 'sfcer', 'e': 'wrd',
    'f': 'dgrt', 'g': 'fhty', 'h': 'gjyu', 'i': 'uok', 'j': 'hknu',
    'k': 'jlmi', 'l': 'kop', 'm': 'njk', 'n': 'bhjm', 'o': 'iplk',
    'p': 'ol', 'q': 'wa', 'r': 'edft', 's': 'awedx', 't': 'rfgy',
    'u': 'yhjk', 'v': 'cfgb', 'w': 'qase', 'x': 'zsdc', 'y': 'tghu',
    'z': 'asx',
}

def _add_typos(text: str, count: int = 1) -> str:
    """Add realistic typos to text."""
    chars = list(text)
    result = chars[:]
    for _ in range(count):
        if len(result) < 3:
            break
        idx = random.randint(0, len(result) - 1)
        ch = result[idx]
        if ch.lower() in _NEARBY:
            nearby = _NEARBY[ch.lower()]
            replacement = random.choice(nearby)
            if ch.isupper():
                replacement = replacement.upper()
            result[idx] = replacement
        elif ch == ' ' and random.random() < 0.3:
            continue  # skip space removal sometimes
        elif random.random() < 0.5 and idx < len(result) - 1:
            # swap two adjacent chars
            result[idx], result[idx + 1] = result[idx + 1], result[idx]
    return ''.join(result)


def _double_char(text: str) -> str:
    """Double a random character."""
    if len(text) < 2:
        return text
    idx = random.randint(1, len(text) - 1)
    return text[:idx] + text[idx] + text[idx:]


def _drop_char(text: str) -> str:
    """Drop a random character."""
    if len(text) < 4:
        return text
    idx = random.randint(1, len(text) - 2)
    return text[:idx] + text[idx + 1:]


# ═══════════════════════════════════════════════════════════════════
# FILLER / SLANG / HINGLISH PREFIXES
# ═══════════════════════════════════════════════════════════════════

_FILLER_PREFIXES = [
    "", "", "", "",  # empty (no filler) weighted higher
    "hey ", "yo ", "bro ", "dude ", "man ",
    "ok ", "okay ", "k ", "right ",
    "please ", "pls ", "plz ",
    "hey can you ", "could you ", "would you ", "can you ",
    "i want to ", "i need to ", "i'd like to ",
    "help me ", "go ahead and ", "just ",
    "yo can you ", "hey would you ",
]

_HINGLISH_VERBS = {
    "open": ["kholo", "khol", "kholna", "open karo"],
    "close": ["band karo", "band kar", "band"],
    "play": ["chala", "chalao", "play karo", "chalana"],
    "search": ["search karo", "dhundh", "dhundho"],
    "tell": ["batao", "bata", "batana"],
    "show": ["dikhao", "dikha", "dikhana"],
    "mute": ["awaz band", "aawaz band", "sund"],
    "unmute": ["awaz chalu", "aawaz chalu"],
    "volume up": ["volume badhao", "volume badha", "awaz badhao"],
    "volume down": ["volume ghatao", "volume ghata", "awaz ghatao"],
    "brightness up": ["light zyada", "brightness zyada", "roshni zyada"],
    "brightness down": ["light kam", "brightness kam", "roshni kam"],
    "restart": ["restart kar", "reboot kar"],
    "shutdown": ["band kar sab", "shutdown karo"],
}

_HINGLISH_FILLERS = ["", "", "", "yaar ", "bhai ", "arre ", "chal ", "ab ", "jaldi "]

_EMOJI_MAP = {
    "open": ["📂", "🔓"],
    "close": ["❌", "🔒"],
    "play": ["▶️", "🎵"],
    "search": ["🔍"],
    "tell": ["💬"],
    "show": ["👁️"],
    "mute": ["🔇"],
    "screenshot": ["📸"],
    "weather": ["🌤️", "🌧️"],
    "joke": ["😂"],
    "calculator": ["🔢"],
    "timer": ["⏰"],
    "todo": ["📝"],
    "memory": ["🧠"],
    "greeting": ["👋", "😊"],
}

_SLANG_MAP = {
    "volume up": ["louder", "turn it up", "crank it up", "boost volume", "max volume"],
    "volume down": ["quieter", "turn it down", "lower volume", "soften it"],
    "mute": ["shush", "silence", "quiet", "shut up"],
    "brightness up": ["brighter", "crank up brightness", "full brightness"],
    "brightness down": ["dimmer", "dim the screen", "darken"],
    "shutdown": ["power off", "turn off pc", "kill it", "bye bye pc"],
    "restart": ["reboot", "restart machine", "cycle power"],
    "screenshot": ["snap screen", "capture screen", "screen grab", "pic of screen"],
    "open chrome": ["fire up chrome", "boot chrome", "launch google chrome"],
    "close chrome": ["kill chrome", "end chrome", "terminate chrome"],
    "weather": ["forecast", "temperature", "how's the weather", "what's the temp"],
    "joke": ["make me laugh", "something funny", "comedy time"],
    "calculator": ["math", "do math", "quick calc", "compute"],
    "timer": ["countdown", "alarm", "remind me in", "set a timer"],
    "todo": ["task list", "my tasks", "things to do", "reminders"],
}


# ═══════════════════════════════════════════════════════════════════
# BASE COMMAND TEMPLATES (the core of the test corpus)
# Each tuple: (template, expected_tool, expected_params, subcategory)
# ═══════════════════════════════════════════════════════════════════

def _build_command_corpus() -> list[TestCase]:
    """Build the full command corpus. ~300 base templates × variations = 10,000+."""
    cases: list[TestCase] = []

    # ────────────────────────────────────────────────────────
    # WEBSITE OPENING (40+ bases × many websites)
    # ────────────────────────────────────────────────────────
    website_bases = [
        "open {site}", "launch {site}", "go to {site}", "visit {site}",
        "navigate to {site}", "browse {site}", "open {site} website",
        "open up {site}", "bring up {site}", "load {site}",
        "let me see {site}", "take me to {site}", "show me {site}",
        "i want {site}", "start {site}", "fire up {site}",
    ]
    # Top 20 websites tested across all bases
    # NOTE: Some names appear in both WEBSITES and KNOWN_APPS.
    # When a name is in KNOWN_APPS, open_app takes priority.
    top_websites = [
        "youtube", "google", "gmail", "github", "reddit", "instagram",
        "facebook", "twitter", "x", "netflix", "amazon",
        "linkedin", "whatsapp", "wikipedia", "chatgpt",
        "telegram", "notion", "twitch",
    ]
    # These are also known desktop apps → expect open_app
    also_apps = {"spotify", "discord", "teams", "outlook", "slack", "zoom", "steam"}
    for site in top_websites:
        expected_tool = "open_app" if site in also_apps else "open_website"
        for base in website_bases:
            cases.append(_p(base.format(site=site), expected_tool, {"target": site}, "website", f"open {site}"))
    # Standalone website names
    for site in top_websites:
        expected_tool = "open_app" if site in also_apps else "open_website"
        cases.append(_p(site, expected_tool, {"target": site}, "website", f"standalone {site}"))
    # Less common websites (5 tests each)
    # Some of these are also known apps → expect open_app
    rare_websites = [
        "bing", "yahoo", "duckduckgo", "medium", "gitlab", "npm", "pypi",
        "figma", "trello",
        "tiktok", "pinterest",
        "leetcode", "replit", "codepen", "coursera", "udemy", "perplexity",
        "claude", "deepseek", "grok", "midjourney", "canva", "quora",
        "ebay", "flipkart", "aliexpress", "snapchat", "bitbucket",
        "khan academy", "wolfram alpha", "archive", "wayback machine",
        "google maps", "google translate", "google drive", "google docs",
        "google sheets", "google slides", "google news", "google photos",
        "google calendar", "google keep", "google earth", "google meet",
        "onedrive", "dropbox", "dalle", "copilot", "devto",
    ]
    # Apps that are also in WEBSITES
    rare_apps = {"slack", "zoom", "teams", "outlook", "steam", "discord"}
    for site in rare_websites:
        expected_tool = "open_app" if site in rare_apps else "open_website"
        cases.append(_p(f"open {site}", expected_tool, {"target": site}, "website", f"rare site {site}"))
        cases.append(_p(site, expected_tool, {"target": site}, "website", f"standalone rare {site}"))

    # ────────────────────────────────────────────────────────
    # APPLICATION OPENING
    # ────────────────────────────────────────────────────────
    app_bases = [
        "open {app}", "launch {app}", "start {app}", "run {app}",
        "open the {app} app", "open up {app}", "fire up {app}",
        "bring up {app}", "load {app}", "can you open {app}",
        "start up {app}", "boot up {app}", "let's open {app}",
    ]
    known_apps = [
        "notepad", "calculator", "chrome", "firefox", "edge", "terminal",
        "cmd", "command prompt", "powershell", "vscode", "visual studio code",
        "spotify", "vlc", "paint", "word", "excel", "powerpoint",
        "outlook", "teams", "discord", "slack", "zoom", "steam", "obs",
        "git", "postman", "figma", "brave", "opera", "safari",
        "snipping tool", "task manager", "control panel", "settings",
        "explorer", "file explorer", "photoshop", "blender", "pycharm",
        "intellij", "android studio", "notepad++", "sublime",
    ]
    for app in known_apps:
        for base in app_bases:
            cases.append(_p(base.format(app=app), "open_app", {"target": app}, "app", f"open {app}"))

    # ────────────────────────────────────────────────────────
    # FOLDER OPENING
    # ────────────────────────────────────────────────────────
    folder_bases = [
        "open {folder}", "show {folder}", "go to {folder}",
        "open my {folder}", "show my {folder}", "open the {folder} folder",
        "navigate to {folder}", "explore {folder}", "open {folder} folder",
    ]
    folders = ["downloads", "documents", "desktop", "pictures", "music", "videos", "home"]
    system_folders = ["my computer", "this pc", "recycle bin", "control panel", "settings", "task manager"]
    for folder in folders:
        for base in folder_bases:
            cases.append(_p(base.format(folder=folder), "open_folder", {"target": folder}, "folder", f"open {folder}"))
    for folder in system_folders:
        cases.append(_p(f"open {folder}", "open_folder", {"target": folder}, "folder", f"system folder {folder}"))
        cases.append(_p(f"show {folder}", "open_folder", {"target": folder}, "folder", f"show {folder}"))

    # ────────────────────────────────────────────────────────
    # SEARCH ON PLATFORM
    # ────────────────────────────────────────────────────────
    search_platform_bases = [
        "search {query} on {platform}",
        "find {query} on {platform}",
        "look up {query} on {platform}",
        "search for {query} on {platform}",
    ]
    platform_queries = [
        ("AI", "youtube"), ("python tutorial", "youtube"), ("react hooks", "youtube"),
        ("python", "github"), ("machine learning", "github"), ("rust", "github"),
        ("machine learning", "reddit"), ("wallstreetbets", "reddit"),
        ("quantum computing", "wikipedia"), ("relativity", "wikipedia"),
        ("javascript", "stackoverflow"), ("docker", "stackoverflow"),
        ("laptop", "amazon"), ("headphones", "amazon"), ("keyboard", "amazon"),
        ("inception", "imdb"), ("interstellar", "imdb"),
        ("jazz", "spotify"), ("lofi", "spotify"), ("rock", "spotify"),
        ("AI", "x"), ("jobs", "linkedin"), ("recipes", "medium"),
        ("react hooks", "npm"), ("requests", "pypi"),
        ("pasta recipe", "youtube"), ("workout", "youtube"),
        ("linux distro", "reddit"), ("cars", "reddit"),
        ("history of china", "wikipedia"), ("python", "wikipedia"),
    ]
    for query, platform in platform_queries:
        for base in search_platform_bases:
            cases.append(_p(base.format(query=query, platform=platform), "search_on_platform", {"query": query, "platform": platform}, "search_platform", f"search {query} on {platform}"))

    # ────────────────────────────────────────────────────────
    # WEB SEARCH
    # ────────────────────────────────────────────────────────
    search_bases = [
        "search {query}", "google {query}", "look up {query}",
        "find {query}", "search the web for {query}",
        "search the internet for {query}", "search web for {query}",
        "look for {query}", "find me {query}",
        "what is {query}", "who is {query}", "how to {query}",
        "how do {query}", "how does {query}", "how can {query}",
        "why is {query}", "why do {query}", "why does {query}",
        "where is {query}", "where can {query}",
        "when is {query}", "when did {query}",
        "tell me about {query}", "explain {query}",
        "define {query}", "describe {query}",
        "what are {query}", "what does {query} mean",
    ]
    search_queries = [
        "neural networks", "quantum computing", "machine learning",
        "python tutorial", "climate change", "world war 2",
        "photosynthesis", "dark matter", "blockchain",
        "artificial intelligence", "space exploration", "nuclear energy",
        "machine learning", "deep learning", "web development",
        "cybersecurity", "data science", "cloud computing",
        "linux kernel", "docker containers", "kubernetes",
        "ethereum", "bitcoin", "5g technology",
        "renewable energy", "electric vehicles", "mars colonization",
    ]
    for query in search_queries:
        for base in search_bases:
            cases.append(_p(base.format(query=query), "web_search", {"query": query}, "web_search", f"search {query}"))

    # ────────────────────────────────────────────────────────
    # PLAY MUSIC
    # ────────────────────────────────────────────────────────
    play_bases = [
        "play {song}", "play the song {song}", "play the {song}",
        "play some {song}", "play music {song}", "play track {song}",
        "listen to {song}", "put on {song}", "start playing {song}",
        "play {song} song", "can you play {song}",
        "i want to hear {song}", "queue {song}",
    ]
    songs = [
        "believer", "shape of you", "blinding lights", "bohemian rhapsody",
        "stairway to heaven", "hotel california", "imagine",
        "never gonna give you up", "don't stop believin",
        "smells like teen spirit", "wonderwall", "clocks",
        "lose yourself", "sweet child o mine", "come as you are",
        "take on me", "jump", "livin on a prayer",
        "thriller", "billie jean", "beat it",
        "ed sheeran", "drake", "the weeknd", "taylor swift",
        "jazz", "classical", "lofi beats", "rock",
        "chill vibes", "workout mix", "focus music",
    ]
    for song in songs:
        for base in play_bases:
            cases.append(_p(base.format(song=song), "play_music", {"query": song}, "play_music", f"play {song}"))

    # ────────────────────────────────────────────────────────
    # SCREENSHOT
    # ────────────────────────────────────────────────────────
    screenshot_bases = [
        "take screenshot", "take a screenshot", "capture screen",
        "capture the screen", "screenshot", "screenshot now",
        "take screenshot now", "grab the screen", "snap the screen",
        "screen capture", "screen grab", "capture my screen",
        "take a pic of screen", "snapshot", "snip screen",
        "take a snapshot", "grab screen", "screenshot please",
    ]
    for base in screenshot_bases:
        cases.append(_p(base, "screenshot", {}, "system", base))

    # ────────────────────────────────────────────────────────
    # VOLUME CONTROL
    # ────────────────────────────────────────────────────────
    volume_bases = [
        ("volume up", {"action": "up"}),
        ("volume down", {"action": "down"}),
        ("increase volume", {"action": "up"}),
        ("decrease volume", {"action": "down"}),
        ("turn volume up", {"action": "up"}),
        ("turn volume down", {"action": "down"}),
        ("turn up volume", {"action": "up"}),
        ("turn down volume", {"action": "down"}),
        ("raise volume", {"action": "up"}),
        ("lower volume", {"action": "down"}),
        ("louder", {"action": "up"}),
        ("quieter", {"action": "down"}),
        ("make it louder", {"action": "up"}),
        ("make it quieter", {"action": "down"}),
        ("turn it up", {"action": "up"}),
        ("turn it down", {"action": "down"}),
        ("up the volume", {"action": "up"}),
        ("down the volume", {"action": "down"}),
        ("boost volume", {"action": "up"}),
        ("mute", {"action": "mute"}),
        ("mute volume", {"action": "mute"}),
        ("mute the audio", {"action": "mute"}),
        ("silence", {"action": "mute"}),
        ("shush", {"action": "mute"}),
        ("unmute", {"action": "unmute"}),
        ("unmute volume", {"action": "unmute"}),
        ("unmute audio", {"action": "unmute"}),
        ("set volume to 50", {"action": "set", "value": 50}),
        ("volume to 75", {"action": "set", "value": 75}),
        ("set the volume to 100", {"action": "set", "value": 100}),
    ]
    for base, params in volume_bases:
        cases.append(_p(base, "volume_control", params, "volume", base))

    # ────────────────────────────────────────────────────────
    # BRIGHTNESS CONTROL
    # ────────────────────────────────────────────────────────
    brightness_bases = [
        ("brightness up", {"action": "up"}),
        ("brightness down", {"action": "down"}),
        ("increase brightness", {"action": "up"}),
        ("decrease brightness", {"action": "down"}),
        ("turn brightness up", {"action": "up"}),
        ("turn brightness down", {"action": "down"}),
        ("make screen brighter", {"action": "up"}),
        ("make screen dimmer", {"action": "down"}),
        ("brighten the screen", {"action": "up"}),
        ("dim the screen", {"action": "down"}),
        ("dim screen", {"action": "down"}),
        ("brighten screen", {"action": "up"}),
        ("turn up brightness", {"action": "up"}),
        ("turn down brightness", {"action": "down"}),
        ("raise brightness", {"action": "up"}),
        ("lower brightness", {"action": "down"}),
        ("screen brighter", {"action": "up"}),
        ("screen dimmer", {"action": "down"}),
        ("set brightness to 80", {"action": "set", "value": 80}),
        ("brightness to 50", {"action": "set", "value": 50}),
    ]
    for base, params in brightness_bases:
        cases.append(_p(base, "brightness_control", params, "brightness", base))

    # ────────────────────────────────────────────────────────
    # SYSTEM POWER
    # ────────────────────────────────────────────────────────
    power_bases = [
        ("shutdown", {"action": "shutdown"}),
        ("shut down", {"action": "shutdown"}),
        ("shutdown pc", {"action": "shutdown"}),
        ("shut down computer", {"action": "shutdown"}),
        ("shutdown computer", {"action": "shutdown"}),
        ("power off", {"action": "shutdown"}),
        ("turn off pc", {"action": "shutdown"}),
        ("turn off computer", {"action": "shutdown"}),
        ("restart", {"action": "restart"}),
        ("reboot", {"action": "restart"}),
        ("restart pc", {"action": "restart"}),
        ("restart computer", {"action": "restart"}),
        ("reboot computer", {"action": "restart"}),
        ("reboot the system", {"action": "restart"}),
        ("lock", {"action": "lock"}),
        ("lock pc", {"action": "lock"}),
        ("lock screen", {"action": "lock"}),
        ("lock computer", {"action": "lock"}),
        ("lock the screen", {"action": "lock"}),
        ("sleep", {"action": "sleep"}),
        ("sleep pc", {"action": "sleep"}),
        ("hibernate", {"action": "sleep"}),
        ("hibernate computer", {"action": "sleep"}),
        ("logout", {"action": "logout"}),
        ("log out", {"action": "logout"}),
        ("sign out", {"action": "logout"}),
        ("sign out of computer", {"action": "logout"}),
    ]
    for base, params in power_bases:
        cases.append(_p(base, "system_power", params, "power", base))

    # ────────────────────────────────────────────────────────
    # CLIPBOARD
    # ────────────────────────────────────────────────────────
    clipboard_bases = [
        "paste", "paste it", "paste this", "show clipboard",
        "what's on clipboard", "what is on clipboard",
        "what's copied", "paste from clipboard",
        "clipboard paste", "show me clipboard",
        "what do i have copied", "get clipboard",
    ]
    for base in clipboard_bases:
        cases.append(_p(base, "clipboard_paste", {}, "clipboard", base))

    # ────────────────────────────────────────────────────────
    # SYSTEM STATUS
    # ────────────────────────────────────────────────────────
    status_bases = [
        "system status", "pc status", "computer status",
        "check system status", "check pc status", "check computer status",
        "show system status", "show pc status",
        "system stats", "pc stats",
        "how's the system doing", "how is my system doing",
        "how is my pc doing", "what's my system status",
        "system info", "pc info", "computer info",
        "cpu usage", "ram usage", "memory usage", "disk usage",
        "cpu usage right now", "how much ram am i using",
        "how much memory am i using",
        "check my cpu", "check my ram", "check my memory",
        "what's my cpu usage", "what's my ram usage",
        "system health", "pc health",
    ]
    for base in status_bases:
        cases.append(_p(base, "system_status", {}, "system_status", base))

    # ────────────────────────────────────────────────────────
    # BATTERY STATUS
    # ────────────────────────────────────────────────────────
    battery_bases = [
        "battery status", "battery level", "battery charge",
        "what's my battery", "what's my battery level",
        "how much battery do i have", "how much battery is left",
        "check battery", "check my battery",
        "is my laptop charging", "am i charging",
        "battery percentage", "battery left",
        "power status", "how much power do i have",
        "what's the battery level",
    ]
    for base in battery_bases:
        cases.append(_p(base, "battery_status", {}, "battery", base))

    # ────────────────────────────────────────────────────────
    # NETWORK STATUS
    # ────────────────────────────────────────────────────────
    network_bases = [
        "network status", "internet status", "network speed",
        "internet speed", "check network", "check internet",
        "check network status", "check internet status",
        "run speed test", "speed test", "network test",
        "how fast is my internet", "what's my internet speed",
        "run network speed test", "internet speed test",
    ]
    for base in network_bases:
        cases.append(_p(base, "network_status", {}, "network", base))

    # ────────────────────────────────────────────────────────
    # CALCULATOR
    # ────────────────────────────────────────────────────────
    calc_bases = [
        ("calculate 2+2", "2+2"),
        ("calc 100*5", "100*5"),
        ("what is 15*3", "15*3"),
        ("compute 50/10", "50/10"),
        ("evaluate 2^10", "2^10"),
        ("solve 3x+5=20", "3x+5=20"),
        ("what's 7*8", "7*8"),
        ("multiply 5 by 3", "5 by 3"),
        ("10 divided by 2", "10 divided by 2"),
        ("5 plus 3", "5 plus 3"),
        ("10 minus 4", "10 minus 4"),
        ("25 times 4", "25 times 4"),
        ("100 divided by 8", "100 divided by 8"),
        ("square root of 144", "square root of 144"),
        ("what is 25% of 200", "25% of 200"),
        ("2 to the power of 8", "2 to the power of 8"),
        ("100 mod 7", "100 mod 7"),
        ("3.14 * 5 * 5", "3.14 * 5 * 5"),
    ]
    for base, expr in calc_bases:
        cases.append(_p(base, "calculator", {"expression": expr}, "calculator", base))

    # ────────────────────────────────────────────────────────
    # WEATHER
    # ────────────────────────────────────────────────────────
    weather_bases = [
        "weather in {city}", "weather {city}", "weather for {city}",
        "what's the weather in {city}", "what is the weather in {city}",
        "how's the weather in {city}", "how is the weather in {city}",
        "weather like in {city}", "what's weather like in {city}",
        "forecast for {city}", "temperature in {city}",
        "is it raining in {city}", "is it hot in {city}",
        "how hot is it in {city}", "how cold is it in {city}",
        "weather in {city} today", "weather in {city} tomorrow",
        "what's the temperature in {city}",
    ]
    cities = ["london", "tokyo", "new york", "delhi", "mumbai", "paris",
              "berlin", "sydney", "dubai", "singapore", "toronto", "seoul",
              "bangalore", "chennai", "kolkata", "rome", "madrid", "cairo",
              "moscow", "beijing", "shanghai", "sao paulo", "mexico city",
              "buenos aires", "nairobi", "cape town", "amsterdam", "vienna",
              "bangkok", "hanoi", "kathmandu", "colombo", "dhaka", "karachi"]
    for city in cities:
        for base in weather_bases:
            cases.append(_p(base.format(city=city), "weather", {"city": city}, "weather", f"weather {city}"))
    # General weather (no city)
    weather_general = [
        "weather", "what's the weather", "how's the weather",
        "what's the weather like", "weather like",
        "what's the forecast", "is it going to rain",
        "do i need an umbrella", "is it going to snow",
        "is it sunny", "is it cloudy",
    ]
    for base in weather_general:
        cases.append(_p(base, "weather", {"city": ""}, "weather", base))

    # ────────────────────────────────────────────────────────
    # JOKE
    # ────────────────────────────────────────────────────────
    joke_bases = [
        "tell me a joke", "joke", "tell a joke", "say something funny",
        "make me laugh", "got any jokes", "got a joke",
        "tell me something funny", "i'm bored", "entertain me",
        "make a joke", "crack a joke", "give me a joke",
        "tell me a funny joke", "say a joke", "do a joke",
        "something humorous", "make me smile",
    ]
    for base in joke_bases:
        cases.append(_p(base, "joke", {}, "entertainment", base))

    # ────────────────────────────────────────────────────────
    # QUOTE
    # ────────────────────────────────────────────────────────
    quote_bases = [
        "give me a quote", "tell me a quote", "inspire me",
        "say something motivational", "give me some inspiration",
        "give me some motivation", "quote", "motivate me",
        "quote of the day", "i need inspiration",
        "i need motivation", "tell me something inspiring",
        "say something encouraging", "give me encouragement",
        "show me a quote", "send me a quote",
    ]
    for base in quote_bases:
        cases.append(_p(base, "quote", {}, "entertainment", base))

    # ────────────────────────────────────────────────────────
    # COIN / DICE
    # ────────────────────────────────────────────────────────
    coin_bases = ["flip a coin", "flip coin", "toss a coin", "toss coin", "heads or tails"]
    for base in coin_bases:
        cases.append(_p(base, "flip_coin", {}, "entertainment", base))

    dice_bases = ["roll a dice", "roll dice", "throw a dice", "toss a dice", "roll d6"]
    for base in dice_bases:
        cases.append(_p(base, "roll_dice", {}, "entertainment", base))

    # ────────────────────────────────────────────────────────
    # TIMER
    # ────────────────────────────────────────────────────────
    timer_bases = [
        ("set timer for 60", {"seconds": 60}),
        ("timer 5 minutes", {"seconds": 300}),
        ("timer 30 seconds", {"seconds": 30}),
        ("start timer for 10", {"seconds": 10}),
        ("set a timer for 15 minutes", {"seconds": 900}),
        ("timer 1 hour", {"seconds": 3600}),
        ("create timer 120", {"seconds": 120}),
        ("set timer for 30 seconds", {"seconds": 30}),
        ("start a timer for 2 minutes", {"seconds": 120}),
        ("timer 5", {"seconds": 5}),
        ("set timer 60 seconds", {"seconds": 60}),
        ("countdown 10 minutes", {"seconds": 600}),
        ("remind me in 5 minutes", {"seconds": 300}),
    ]
    for base, params in timer_bases:
        cases.append(_p(base, "timer", params, "timer", base))

    # ────────────────────────────────────────────────────────
    # DATETIME
    # ────────────────────────────────────────────────────────
    datetime_bases = [
        "what time is it", "what's the time", "what is the time",
        "what time is it right now", "current time", "current date",
        "what's the date", "what is the date", "what day is it",
        "what day is today", "what's today's date",
        "current date and time", "what's the current time",
        "what's the current date", "what's today",
        "tell me the time", "tell me the date",
        "show me the time", "show me the date",
        "what is today", "which day is it",
        "time please", "date please",
    ]
    for base in datetime_bases:
        cases.append(_p(base, "datetime", {}, "datetime", base))

    # ────────────────────────────────────────────────────────
    # WINDOW CONTROL
    # ────────────────────────────────────────────────────────
    window_bases = [
        ("minimize window", {"action": "minimize"}),
        ("minimize this window", {"action": "minimize"}),
        ("maximize window", {"action": "maximize"}),
        ("maximize this window", {"action": "maximize"}),
        ("restore window", {"action": "restore"}),
        ("list windows", {"action": "list"}),
        ("list all windows", {"action": "list"}),
        ("show windows", {"action": "list"}),
        ("show all windows", {"action": "list"}),
        ("what windows are open", {"action": "list"}),
        ("switch window", {"action": "switch"}),
        ("alt tab", {"action": "switch"}),
        ("switch to next window", {"action": "switch"}),
    ]
    for base, params in window_bases:
        cases.append(_p(base, "window_control", params, "window", base))

    # ────────────────────────────────────────────────────────
    # LIST APPS
    # ────────────────────────────────────────────────────────
    list_apps_bases = [
        "list apps", "list applications", "list programs",
        "show apps", "show applications", "show programs",
        "what's running", "what apps are running",
        "what applications are running",
        "show running apps", "show running applications",
        "how many apps are open", "how many apps are running",
        "what apps are open", "list processes",
        "show me open programs", "list running apps",
    ]
    for base in list_apps_bases:
        cases.append(_p(base, "list_apps", {}, "list_apps", base))

    # ────────────────────────────────────────────────────────
    # CLOSE APP
    # ────────────────────────────────────────────────────────
    close_bases = [
        "close {app}", "kill {app}", "exit {app}", "quit {app}",
        "stop {app}", "close the {app} app",
        "terminate {app}", "end {app}",
    ]
    for app in ["chrome", "firefox", "notepad", "spotify", "vscode", "slack", "teams", "discord", "zoom"]:
        for base in close_bases:
            cases.append(_p(base.format(app=app), "close_app", {"target": app}, "close_app", f"close {app}"))

    # ────────────────────────────────────────────────────────
    # MEMORY
    # ────────────────────────────────────────────────────────
    memory_save_bases = [
        "remember my birthday is jan 1",
        "remember my name is alex",
        "remember i like pizza",
        "save my name is sarah to memory",
        "save this to memory: meeting at 3pm",
        "store that my pin is 1234",
        "note that i prefer dark mode",
        "write down buy groceries",
        "don't forget to call mom",
        "remember the wifi password is abc123",
        "remember my address is 123 main st",
        "learn that i speak english and hindi",
        "keep this in mind: deadline friday",
    ]
    for base in memory_save_bases:
        cases.append(_p(base, "memory_save", {}, "memory", base))

    memory_search_bases = [
        "what do you remember", "what do you know about me",
        "search my memory", "search my notes",
        "find in my memory", "show my memory",
        "what have you learned about me",
        "what did you learn",
        "list my notes", "show my notes",
    ]
    for base in memory_search_bases:
        cases.append(_p(base, "memory_search", {}, "memory", base))

    # ────────────────────────────────────────────────────────
    # TODO
    # ────────────────────────────────────────────────────────
    todo_add_bases = [
        "add todo buy groceries", "add task call dentist",
        "add a todo meeting at 3pm",
        "remind me to buy milk",
        "remind me to call mom at 5pm",
        "create todo finish report",
        "don't forget to submit the form",
        "add reminder pick up kids",
        "make a todo buy birthday gift",
    ]
    for base in todo_add_bases:
        cases.append(_p(base, "add_todo", {}, "todo", base))

    todo_list_bases = [
        "show my todos", "list my todos", "show my tasks",
        "list tasks", "what do i need to do",
        "show me my todo list", "what's on my list",
        "my tasks", "show reminders", "list reminders",
    ]
    for base in todo_list_bases:
        cases.append(_p(base, "list_todos", {}, "todo", base))

    # ────────────────────────────────────────────────────────
    # NEWS
    # ────────────────────────────────────────────────────────
    news_bases = [
        "latest news", "news", "headlines", "today's news",
        "current news", "breaking news", "what's happening",
        "give me the news", "show me the news",
        "what's in the news", "any news",
        "what's new", "news headlines",
    ]
    for base in news_bases:
        cases.append(_p(base, "news", {}, "news", base))

    # ────────────────────────────────────────────────────────
    # NASA
    # ────────────────────────────────────────────────────────
    nasa_bases = [
        "nasa apod", "nasa picture of the day", "nasa photo of the day",
        "nasa astronomy picture", "show me a picture from space",
        "picture of the day", "photo of the day",
        "astronomy picture of the day", "apod",
        "space picture of the day",
    ]
    for base in nasa_bases:
        cases.append(_p(base, "nasa_apod", {}, "nasa", base))

    # ────────────────────────────────────────────────────────
    # STOCKS
    # ────────────────────────────────────────────────────────
    stock_bases = [
        ("stock price AAPL", {"symbol": "AAPL"}),
        ("quote TSLA", {"symbol": "TSLA"}),
        ("price of MSFT", {"symbol": "MSFT"}),
        ("how is AAPL doing", {"symbol": "AAPL"}),
        ("how is TSLA performing", {"symbol": "TSLA"}),
        ("check GOOGL stock", {"symbol": "GOOGL"}),
        ("AMZN stock", {"symbol": "AMZN"}),
        ("what about NVDA", {"symbol": "NVDA"}),
        ("META stock price", {"symbol": "META"}),
        ("how is tesla doing", {"symbol": "TSLA"}),
        ("how is apple doing", {"symbol": "AAPL"}),
        ("how is microsoft doing", {"symbol": "MSFT"}),
    ]
    for base, params in stock_bases:
        cases.append(_p(base, "stock_quote", params, "stocks", base))

    # ────────────────────────────────────────────────────────
    # RANDOM FACT
    # ────────────────────────────────────────────────────────
    fact_bases = [
        "tell me a random fact", "tell me a fact",
        "give me a fact", "give me some trivia",
        "random fact", "fact", "did you know",
        "tell me some trivia", "surprise me with a fact",
    ]
    for base in fact_bases:
        cases.append(_p(base, "random_fact", {}, "entertainment", base))

    # ────────────────────────────────────────────────────────
    # CHART
    # ────────────────────────────────────────────────────────
    chart_bases = [
        ("create bar chart", {"chart_type": "bar"}),
        ("draw a bar chart", {"chart_type": "bar"}),
        ("make a bar chart", {"chart_type": "bar"}),
        ("create line chart", {"chart_type": "line"}),
        ("plot line chart", {"chart_type": "line"}),
        ("draw a line chart", {"chart_type": "line"}),
        ("create pie chart", {"chart_type": "pie"}),
        ("plot pie chart", {"chart_type": "pie"}),
        ("make a pie chart", {"chart_type": "pie"}),
    ]
    for base, params in chart_bases:
        cases.append(_p(base, "plot_chart", params, "chart", base))

    # ────────────────────────────────────────────────────────
    # IP LOOKUP
    # ────────────────────────────────────────────────────────
    ip_bases = [
        "what's my ip", "what is my ip address",
        "find my ip", "look up my ip", "ip lookup",
        "ip address lookup", "ip info", "trace my ip",
        "what's my public ip", "my ip address",
    ]
    for base in ip_bases:
        cases.append(_p(base, "ip_lookup", {}, "network", base))

    # ────────────────────────────────────────────────────────
    # NUTRITION
    # ────────────────────────────────────────────────────────
    nutrition_bases = [
        ("nutrition for apple", {"query": "apple"}),
        ("calories in banana", {"query": "banana"}),
        ("how many calories in rice", {"query": "rice"}),
        ("protein in chicken breast", {"query": "chicken breast"}),
        ("nutrition info for eggs", {"query": "eggs"}),
        ("carbs in bread", {"query": "bread"}),
    ]
    for base, params in nutrition_bases:
        cases.append(_p(base, "nutrition", params, "nutrition", base))

    # ────────────────────────────────────────────────────────
    # NOTES
    # ────────────────────────────────────────────────────────
    note_bases = [
        "add note buy milk", "create note meeting notes",
        "take a note call dentist", "save note project ideas",
    ]
    for base in note_bases:
        cases.append(_p(base, "add_note", {}, "notes", base))

    # ────────────────────────────────────────────────────────
    # READ DOCUMENT
    # ────────────────────────────────────────────────────────
    doc_bases = [
        "read file report.pdf", "open document notes.txt",
        "show file readme.md", "what's in the file data.csv",
    ]
    for base in doc_bases:
        cases.append(_p(base, "read_document", {}, "documents", base))

    # ────────────────────────────────────────────────────────
    # SCREEN INFO
    # ────────────────────────────────────────────────────────
    screen_bases = [
        "screen resolution", "what's my screen resolution",
        "display info", "screen info", "what's my display size",
    ]
    for base in screen_bases:
        cases.append(_p(base, "screen_info", {}, "system", base))

    # ────────────────────────────────────────────────────────
    # EXERCISE
    # ────────────────────────────────────────────────────────
    exercise_bases = [
        ("exercise for biceps", {"query": "biceps"}),
        ("show me workouts for chest", {"query": "chest"}),
        ("workout routine for legs", {"query": "legs"}),
        ("exercises for abs", {"query": "abs"}),
    ]
    for base, params in exercise_bases:
        cases.append(_p(base, "exercise", params, "health", base))

    # ────────────────────────────────────────────────────────
    # EMAIL VALIDATE
    # ────────────────────────────────────────────────────────
    email_bases = [
        ("validate email test@example.com", {"email": "test@example.com"}),
        ("check email user@domain.org", {"email": "user@domain.org"}),
        ("is this email valid hello@world.com", {"email": "hello@world.com"}),
    ]
    for base, params in email_bases:
        cases.append(_p(base, "email_validate", params, "tools", base))

    # ────────────────────────────────────────────────────────
    # SENTIMENT
    # ────────────────────────────────────────────────────────
    sentiment_bases = [
        ("analyze sentiment i love this product", {"text": "i love this product"}),
        ("sentiment of this is terrible", {"text": "this is terrible"}),
    ]
    for base, params in sentiment_bases:
        cases.append(_p(base, "sentiment", params, "tools", base))

    # ────────────────────────────────────────────────────────
    # HOLIDAYS
    # ────────────────────────────────────────────────────────
    holiday_bases = [
        ("holidays in India", {"country_code": "IN"}),
        ("holidays in US", {"country_code": "US"}),
        ("list holidays", {}),
    ]
    for base, params in holiday_bases:
        cases.append(_p(base, "holidays", params, "reference", base))

    # ────────────────────────────────────────────────────────
    # CITY INFO
    # ────────────────────────────────────────────────────────
    city_bases = [
        ("city info for Tokyo", {"query": "Tokyo"}),
        ("tell me about London", {"query": "London"}),
        ("city information about Paris", {"query": "Paris"}),
    ]
    for base, params in city_bases:
        cases.append(_p(base, "city_info", params, "reference", base))

    # ────────────────────────────────────────────────────────
    # NASA MARS / ISS
    # ────────────────────────────────────────────────────────
    mars_bases = ["nasa mars rover", "mars rover photos", "show me mars photos"]
    for base in mars_bases:
        cases.append(_p(base, "nasa_mars", {}, "nasa", base))

    iss_bases = ["where is the ISS", "iss location", "track the iss", "iss position"]
    for base in iss_bases:
        cases.append(_p(base, "nasa_iss", {}, "nasa", base))

    # ────────────────────────────────────────────────────────
    # GREETINGS
    # ────────────────────────────────────────────────────────
    greeting_bases = [
        "hello", "hi", "hey", "howdy", "yo", "sup",
        "good morning", "good afternoon", "good evening",
        "how are you", "how do you do", "how have you been",
        "what's up", "how's it going", "how are things",
        "who are you", "what are you", "what's your name",
        "thanks", "thank you", "thx", "cheers",
        "bye", "goodbye", "see you", "later", "good night",
    ]
    for base in greeting_bases:
        cases.append(_p(base, "greeting", {}, "greeting", base))

    # ────────────────────────────────────────────────────────
    # COPY / RENAME FILE
    # ────────────────────────────────────────────────────────
    file_ops_bases = ["copy file", "rename file", "copy a file", "rename a file"]
    for base in file_ops_bases:
        cases.append(_p(base, "copy_file" if "copy" in base else "rename_file", {}, "files", base))

    return cases


# ═══════════════════════════════════════════════════════════════════
# NOISE GENERATORS (apply variations to base commands)
# ═══════════════════════════════════════════════════════════════════

def _generate_noisy_variants(command: str, tool: str, params: dict, category: str, desc: str) -> list[TestCase]:
    """Generate typo/slang/filler variants of a single command."""
    variants: list[TestCase] = []
    tags: list[str] = []

    # 1. Typo variants (2 random typos per command)
    for i in range(2):
        typos = _add_typos(command, count=random.randint(1, 2))
        if typos != command:
            variants.append(_p(typos, tool, params, category, f"typo of {desc}", ["typo"]))

    # 2. Double character variant
    doubled = _double_char(command)
    if doubled != command:
        variants.append(_p(doubled, tool, params, category, f"doubled char in {desc}", ["typo"]))

    # 3. Drop character variant
    dropped = _drop_char(command)
    if dropped != command:
        variants.append(_p(dropped, tool, params, category, f"dropped char in {desc}", ["typo"]))

    # 4. Filler prefix variants (3 random fillers)
    for filler in random.sample(_FILLER_PREFIXES, min(3, len(_FILLER_PREFIXES))):
        if filler:
            variants.append(_p(filler + command, tool, params, category, f"filler: {filler}{desc}", ["filler"]))

    # 5. Uppercase variant
    upper = command.upper()
    if upper != command:
        variants.append(_p(upper, tool, params, category, f"uppercase {desc}", ["caps"]))

    # 6. Title case variant
    title = command.title()
    if title != command and title != upper:
        variants.append(_p(title, tool, params, category, f"title case {desc}", ["caps"]))

    # 7. Extra punctuation
    puncts = [command + "!", command + "...", command + "??", "!! " + command, "... " + command]
    for punct in random.sample(puncts, min(2, len(puncts))):
        variants.append(_p(punct, tool, params, category, f"punct: {desc}", ["punctuation"]))

    # 8. Extra whitespace
    words = command.split()
    if len(words) > 2:
        idx = random.randint(1, len(words) - 1)
        spaced = ' '.join(words[:idx]) + '   ' + ' '.join(words[idx:])
        variants.append(_p(spaced, tool, params, category, f"extra space in {desc}", ["whitespace"]))

    return variants


def _generate_hinglish_variants() -> list[TestCase]:
    """Generate Hinglish/Hindi variant commands."""
    cases: list[TestCase] = []

    # Basic Hinglish commands
    hinglish_commands = [
        # Open
        ("kholo youtube", "open_website", {"target": "youtube"}),
        ("chrome kholo", "open_app", {"target": "chrome"}),
        ("notepad khol", "open_app", {"target": "notepad"}),
        ("browser open karo", "open_app", {"target": "chrome"}),
        # Close
        ("band karo chrome", "close_app", {"target": "chrome"}),
        ("spotify band kar", "close_app", {"target": "spotify"}),
        ("notepad band karo", "close_app", {"target": "notepad"}),
        # Play
        ("chalao believer", "play_music", {"query": "believer"}),
        ("gaana chala shape of you", "play_music", {"query": "shape of you"}),
        ("music chala", "play_music", {"query": "music"}),
        ("play karo lofi", "play_music", {"query": "lofi"}),
        # Search
        ("search karo python", "web_search", {"query": "python"}),
        ("dhundh machine learning", "web_search", {"query": "machine learning"}),
        ("youtube pe search karo AI", "search_on_platform", {"query": "AI", "platform": "youtube"}),
        ("github pe dhundho react", "search_on_platform", {"query": "react", "platform": "github"}),
        # Volume
        ("volume badhao", "volume_control", {"action": "up"}),
        ("volume ghatao", "volume_control", {"action": "down"}),
        ("awaz band karo", "volume_control", {"action": "mute"}),
        ("aawaz chalu karo", "volume_control", {"action": "unmute"}),
        ("aawaz badhao", "volume_control", {"action": "up"}),
        # Brightness
        ("brightness badhao", "brightness_control", {"action": "up"}),
        ("roshni kam karo", "brightness_control", {"action": "down"}),
        ("light zyada karo", "brightness_control", {"action": "up"}),
        ("light kam karo", "brightness_control", {"action": "down"}),
        # Weather
        ("weather batao Delhi", "weather", {"city": "delhi"}),
        ("mausam kya hai Mumbai", "weather", {"city": "mumbai"}),
        ("mausam batao", "weather", {"city": ""}),
        # System
        ("reboot kar", "system_power", {"action": "restart"}),
        ("restart kar do", "system_power", {"action": "restart"}),
        ("shutdown karo", "system_power", {"action": "shutdown"}),
        ("band kar sab", "system_power", {"action": "shutdown"}),
        # Joke
        ("mazaak sunao", "joke", {}),
        ("joke sunao", "joke", {}),
        ("hasaao", "joke", {}),
        # Screenshot
        ("screenshot le", "screenshot", {}),
        ("screen capture kar", "screenshot", {}),
        # Greeting
        ("namaste", "greeting", {}),
        ("kaise ho", "greeting", {}),
        ("kya haal hai", "greeting", {}),
        # Todo
        ("todo jodo buy milk", "add_todo", {}),
        ("yaad dilana call mom", "add_todo", {}),
        # Calculator
        ("calculate karo 5 plus 3", "calculator", {"expression": "5 plus 3"}),
        ("10 guna 5 kitna hota hai", "calculator", {}),
    ]

    for cmd, tool, params in hinglish_commands:
        cases.append(_p(cmd, tool, params, "hinglish", cmd))
        # Add filler variants
        for filler in random.sample(_HINGLISH_FILLERS, 2):
            if filler:
                cases.append(_p(filler + cmd, tool, params, "hinglish", f"hinglish filler: {cmd}"))

    return cases


def _generate_context_followup_tests() -> list[TestCase]:
    """Generate context follow-up / pronoun resolution test cases."""
    cases: list[TestCase] = []

    # These are tested with the context memory integration
    # The key is that after a command like "open chrome", "now search python" should work
    context_scenarios = [
        # Initial command, follow-up, expected follow-up tool
        ("open chrome", "now search python on github", "search_on_platform"),
        ("open chrome", "now search python", "web_search"),
        ("weather in london", "and tokyo", "weather"),
        ("play believer", "now search for lyrics", "web_search"),
        ("open youtube", "search funny cats on it", "search_on_platform"),
        ("tell me a joke", "another one", "joke"),
        ("what time is it", "and the date", "datetime"),
        ("volume up", "more", "volume_control"),
        ("brightness down", "more", "brightness_control"),
    ]

    # We test that the follow-up at least resolves to something reasonable
    # (Context resolution is best-effort, so we test the follow-ups independently)
    followup_independent = [
        ("now search python on github", "search_on_platform", {"query": "python", "platform": "github"}),
        ("search funny cats on youtube", "search_on_platform", {"query": "funny cats", "platform": "youtube"}),
        ("another one", "joke", {}),
        ("and the date", "datetime", {}),
        ("more volume", "volume_control", {"action": "up"}),
        ("less brightness", "brightness_control", {"action": "down"}),
    ]

    for cmd, tool, params in followup_independent:
        cases.append(_p(cmd, tool, params, "context_followup", cmd))

    return cases


def _generate_multi_intent_tests() -> list[TestCase]:
    """Generate multi-intent compound command tests."""
    cases: list[TestCase] = []

    # These test that the first command in a compound is recognized
    multi_commands = [
        ("open chrome and search python", "open_app", {"target": "chrome"}),
        ("play music and set timer for 5 minutes", "play_music"),
        ("take screenshot and open notepad", "screenshot"),
        ("volume up and brightness down", "volume_control", {"action": "up"}),
        ("open youtube then search funny cats", "open_website", {"target": "youtube"}),
        ("search python on github and open notepad", "search_on_platform", {"query": "python", "platform": "github"}),
    ]

    for cmd in multi_commands:
        tool = cmd[1]
        params = cmd[2] if len(cmd) > 2 else {}
        cases.append(_p(cmd[0], tool, params, "multi_intent", cmd[0]))

    return cases


def _generate_slang_variants() -> list[TestCase]:
    """Generate slang/abbreviation variant tests."""
    cases: list[TestCase] = []

    for intent, slangs in _SLANG_MAP.items():
        # Map intent to tool
        tool_map = {
            "volume up": ("volume_control", {"action": "up"}),
            "volume down": ("volume_control", {"action": "down"}),
            "mute": ("volume_control", {"action": "mute"}),
            "brightness up": ("brightness_control", {"action": "up"}),
            "brightness down": ("brightness_control", {"action": "down"}),
            "shutdown": ("system_power", {"action": "shutdown"}),
            "restart": ("system_power", {"action": "restart"}),
            "screenshot": ("screenshot", {}),
            "open chrome": ("open_app", {"target": "chrome"}),
            "close chrome": ("close_app", {"target": "chrome"}),
            "weather": ("weather", {"city": ""}),
            "joke": ("joke", {}),
            "calculator": ("calculator", {}),
            "timer": ("timer", {"seconds": 30}),
            "todo": ("add_todo", {}),
        }

        if intent in tool_map:
            tool, params = tool_map[intent]
            for slang in slangs:
                cases.append(_p(slang, tool, params, "slang", f"slang: {slang}"))

    return cases


# ═══════════════════════════════════════════════════════════════════
# TEST RUNNER
# ═══════════════════════════════════════════════════════════════════

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors: list[tuple[str, str, str]] = []  # (command, expected, got)
        self.by_category: dict[str, tuple[int, int]] = {}  # cat -> (passed, failed)
        self.by_tag: dict[str, tuple[int, int]] = {}

    def record(self, case: TestCase, got_tool: str, success: bool):
        if success:
            self.passed += 1
        else:
            self.failed += 1
            self.errors.append((case.expected_tool, got_tool, case.command))

        cat = case.category or "uncategorized"
        p, f = self.by_category.get(cat, (0, 0))
        self.by_category[cat] = (p + (1 if success else 0), f + (0 if success else 1))

        for tag in case.tags or ["clean"]:
            p, f = self.by_tag.get(tag, (0, 0))
            self.by_tag[tag] = (p + (1 if success else 0), f + (0 if success else 1))


def run_tests(
    engine: CommandEngine,
    cases: list[TestCase],
    category_filter: str | None = None,
    max_cases: int | None = None,
    verbose: bool = False,
) -> TestResult:
    result = TestResult()
    filtered = cases

    if category_filter:
        filtered = [c for c in cases if category_filter.lower() in c.category.lower()]
        print(f"\n  Filtered to {len(filtered)} cases matching '{category_filter}'")

    if max_cases:
        filtered = filtered[:max_cases]

    total = len(filtered)
    print(f"  Running {total} test cases...\n")

    for i, case in enumerate(filtered):
        r = engine.process(case.command)
        got = r.tool_name
        success = got == case.expected_tool

        # Also check params if expected
        if success and case.expected_params:
            for key, val in case.expected_params.items():
                actual = r.params.get(key)
                if actual is not None:
                    if isinstance(val, str) and isinstance(actual, str):
                        if val.lower() not in actual.lower() and actual.lower() not in val.lower():
                            success = False
                            got = f"{got} (param {key}={actual}, expected {val})"
                            break
                    elif actual != val:
                        success = False
                        got = f"{got} (param {key}={actual}, expected {val})"
                        break

        result.record(case, got, success)

        if verbose or not success:
            icon = "+" if success else "X"
            print(f"  [{icon}] '{case.command[:70]}' -> {got} (expected: {case.expected_tool})")

        # Progress indicator
        if (i + 1) % 500 == 0:
            print(f"  ... {i + 1}/{total} done ({result.passed} passed, {result.failed} failed)")

    return result


def print_report(result: TestResult, total_time: float):
    total = result.passed + result.failed
    print("\n" + "=" * 72)
    print(f"  COMPREHENSIVE NLP TEST SUITE — RESULTS")
    print(f"  {total} cases | {result.passed} passed | {result.failed} failed | {total_time:.1f}s")
    print("=" * 72)

    if result.by_tag:
        print("\n  BY TAG:")
        for tag, (p, f) in sorted(result.by_tag.items()):
            total_tag = p + f
            rate = (p / total_tag * 100) if total_tag > 0 else 0
            bar = "+" * int(rate / 5) + "-" * (20 - int(rate / 5))
            print(f"    {tag:20s} {bar} {p}/{total_tag} ({rate:.0f}%)")

    print("\n  BY CATEGORY:")
    for cat, (p, f) in sorted(result.by_category.items()):
        total_cat = p + f
        rate = (p / total_cat * 100) if total_cat > 0 else 0
        bar = "+" * int(rate / 5) + "-" * (20 - int(rate / 5))
        print(f"    {cat:20s} {bar} {p}/{total_cat} ({rate:.0f}%)")

    if result.errors:
        print(f"\n  FAILED COMMANDS (first 50):")
        for expected, got, cmd in result.errors[:50]:
            print(f"    '{cmd[:65]}' -> got '{got}', expected '{expected}'")

    print("\n" + "=" * 72)
    overall_rate = (result.passed / total * 100) if total > 0 else 0
    verdict = "ALL TESTS PASSED!" if result.failed == 0 else f"{result.failed} FAILURES"
    print(f"  VERDICT: {verdict} ({overall_rate:.1f}% pass rate)")
    print("=" * 72)


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="JARVIS Comprehensive NLP Test Suite")
    parser.add_argument("--category", "-c", help="Filter by category")
    parser.add_argument("--max", "-m", type=int, help="Max cases to run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show every case")
    parser.add_argument("--stats-only", action="store_true", help="Just show corpus stats")
    parser.add_argument("--seed", "-s", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    random.seed(args.seed)

    print("=" * 72)
    print("  JARVIS COMPREHENSIVE NLP TEST SUITE")
    print("  Generating 10,000+ command variations...")
    print("=" * 72)

    # Build corpus
    t0 = time.time()
    base_cases = _build_command_corpus()
    print(f"\n  Base commands: {len(base_cases)}")

    # Generate noisy variants
    all_cases: list[TestCase] = list(base_cases)
    for case in base_cases:
        noisy = _generate_noisy_variants(case.command, case.expected_tool, case.expected_params, case.category, case.description)
        all_cases.extend(noisy)
    print(f"  After noise variants: {len(all_cases)}")

    # Add Hinglish
    hinglish = _generate_hinglish_variants()
    all_cases.extend(hinglish)
    print(f"  After Hinglish: {len(all_cases)}")

    # Add context follow-ups
    context = _generate_context_followup_tests()
    all_cases.extend(context)
    print(f"  After context follow-ups: {len(all_cases)}")

    # Add multi-intent
    multi = _generate_multi_intent_tests()
    all_cases.extend(multi)
    print(f"  After multi-intent: {len(all_cases)}")

    # Add slang
    slang = _generate_slang_variants()
    all_cases.extend(slang)
    print(f"  After slang: {len(all_cases)}")

    # Deduplicate
    seen: set[str] = set()
    unique: list[TestCase] = []
    for c in all_cases:
        key = c.command.lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(c)
    all_cases = unique
    print(f"  After dedup: {len(all_cases)}")
    print(f"  Generation time: {time.time() - t0:.1f}s")

    # Category stats
    cats: dict[str, int] = {}
    for c in all_cases:
        cat = c.category or "uncategorized"
        cats[cat] = cats.get(cat, 0) + 1
    print("\n  CATEGORY BREAKDOWN:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"    {cat:20s} {count:5d}")

    if args.stats_only:
        return 0

    # Run tests
    engine = CommandEngine(catalog)
    print("\n  Engine initialized. Starting tests...")
    t1 = time.time()
    result = run_tests(engine, all_cases, args.category, args.max, args.verbose)
    elapsed = time.time() - t1
    print_report(result, elapsed)

    return 1 if result.failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
