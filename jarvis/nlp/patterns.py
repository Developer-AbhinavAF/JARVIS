"""Pattern bank for JARVIS NLP intent classification.

Contains comprehensive regex patterns for all supported intents.
Each intent has multiple patterns to handle natural language variations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class IntentPattern:
    """A single intent pattern with regex and metadata."""
    intent: str
    confidence: float
    patterns: list[str]
    priority: int = 0  # Higher = checked first
    requires_entity: str | None = None  # Entity key that must be present
    action: str | None = None  # Direct action mapping
    extract_params: bool = True  # Whether to extract parameters


class PatternBank:
    """Collection of all intent patterns for rule-based classification."""

    def __init__(self) -> None:
        self._patterns: list[IntentPattern] = []
        self._build_all_patterns()

    def _build_all_patterns(self) -> None:
        """Build all intent patterns."""

        # ── OPEN WEBSITE ──
        self._patterns.append(IntentPattern(
            intent="OPEN_WEBSITE",
            confidence=0.95,
            priority=100,
            patterns=[
                r"^(?:open|launch|go\s+to|visit|navigate\s+to|browse\s+to)\s+(?:the\s+)?(?:website\s+)?(?P<target>youtube|google|gmail|github|stackoverflow|stack\s*overflow|reddit|twitter|x\.com|instagram|facebook|netflix|spotify|amazon|linkedin|whatsapp|wikipedia|chatgpt|claude|discord|twitch)\s*$",
                r"^(?:open|launch|go\s+to|visit|navigate\s+to)\s+(?:the\s+)?(?:website\s+)?(?P<url>https?://[^\s]+)\s*$",
                r"^(?P<target>youtube|google|gmail|github|stackoverflow|stack\s*overflow|reddit|twitter|x\.com|instagram|facebook|netflix|spotify|amazon|linkedin|whatsapp|wikipedia|chatgpt|claude|discord|twitch)\s*$",
                r"^(?:open|launch|go\s+to|visit)\s+(?:the\s+)?(?P<target>youtube|google|gmail|github|stackoverflow|stack\s*overflow|reddit|twitter|x\.com|instagram|facebook|netflix|spotify|amazon|linkedin|whatsapp|wikipedia|chatgpt|claude|discord|twitch)\s+(?:website|page|site)\s*$",
                r"^(?:open|launch)\s+(?:the\s+)?(?P<target>youtube|google|gmail|github|stackoverflow|stack\s*overflow|reddit|twitter|x\.com|instagram|facebook|netflix|spotify|amazon|linkedin|whatsapp|wikipedia|chatgpt|claude|discord|twitch)\s*$",
                r"^(?:open|launch|go\s+to|visit|navigate\s+to)\s+(?:the\s+)?(?P<target>yt|youtube)\s*$",
                r"^(?P<target>yt)\s*$",
                r"^(?:open|launch|go\s+to|visit)\s+(?:the\s+)?(?P<target>yt)\s*$",
            ],
            action="open_website",
        ))

        # ── OPEN APPLICATION ──
        self._patterns.append(IntentPattern(
            intent="OPEN_APP",
            confidence=0.92,
            priority=95,
            patterns=[
                r"^(?:open|launch|start|run)\s+(?:the\s+)?(?:app\s+)?(?P<target>(?:chrome|firefox|edge|vscode|vs\s*code|cursor|discord|steam|spotify|whatsapp|explorer|settings|control\s+panel|task\s+manager|cmd|powershell|terminal|calculator|notepad|paint|obs|word|excel|powerpoint|outlook|onenote|teams|zoom|slack|skype|vlc|telegram|sublime|notepad\+\+|intellij|pycharm|blender|gimp|photoshop|epic\s+games|file\s+explorer|snipping\s+tool|wordpad))\s*$",
                r"^(?:open|launch|start|run)\s+(?:the\s+)?(?P<target>(?:chrome|firefox|edge|vscode|vs\s*code|cursor|discord|steam|spotify|whatsapp|explorer|settings|control\s+panel|task\s+manager|cmd|powershell|terminal|calculator|notepad|paint|obs|word|excel|powerpoint|outlook|onenote|teams|zoom|slack|skype|vlc|telegram|sublime|notepad\+\+|intellij|pycharm|blender|gimp|photoshop|epic\s+games|file\s+explorer|snipping\s+tool|wordpad))\s+(?:app|application|program)\s*$",
                r"^(?:open|launch|start|run)\s+(?:the\s+)?(?P<target>[a-z0-9\s._-]{2,30})\s*$",
            ],
            action="open_app",
        ))

        # ── CLOSE APPLICATION ──
        self._patterns.append(IntentPattern(
            intent="CLOSE_APP",
            confidence=0.92,
            priority=94,
            patterns=[
                r"^(?:close|kill|stop|exit|quit)\s+(?:the\s+)?(?:app\s+)?(?P<target>[a-z0-9\s._-]{2,30})\s*$",
                r"^(?:close|kill|stop|exit|quit)\s+(?:the\s+)?(?P<target>[a-z0-9\s._-]{2,30})\s+(?:app|application|program)\s*$",
            ],
            action="close_app",
        ))

        # ── SEARCH YOUTUBE ──
        self._patterns.append(IntentPattern(
            intent="SEARCH_YOUTUBE",
            confidence=0.95,
            priority=90,
            patterns=[
                r"^(?:search|find|look\s+for|search\s+for)\s+(?P<query>.+?)\s+on\s+(?:youtube|yt)\s*$",
                r"^(?:youtube|yt)\s+(?:search|find)\s+(?P<query>.+)\s*$",
                r"^(?:search|find)\s+(?P<query>.+?)\s+on\s+(?:youtube|yt)\s*$",
            ],
            action="search_youtube",
        ))

        # ── SEARCH WEB (platform-specific) ──
        self._patterns.append(IntentPattern(
            intent="SEARCH_ON_PLATFORM",
            confidence=0.93,
            priority=88,
            patterns=[
                r"^(?:search|find|look\s+for|search\s+for)\s+(?P<query>.+?)\s+on\s+(?P<platform>reddit|github|wikipedia|stackoverflow|stack\s*overflow|amazon|imdb|spotify|linkedin|google\s+scholar)\s*$",
                r"^(?:search|find)\s+(?P<query>.+?)\s+on\s+(?P<platform>reddit|github|wikipedia|stackoverflow|stack\s*overflow|amazon|imdb|spotify|linkedin|google\s+scholar)\s*$",
                r"^(?P<platform>reddit|github|wikipedia|stackoverflow|stack\s*overflow|amazon|imdb|spotify|linkedin|google\s+scholar)\s+(?:search|find)\s+(?P<query>.+)\s*$",
            ],
            action="search_platform",
        ))

        # ── SEARCH WEB (default Google) ──
        self._patterns.append(IntentPattern(
            intent="SEARCH_WEB",
            confidence=0.90,
            priority=85,
            patterns=[
                r"^(?:search|google|look\s+up|find|search\s+for|search\s+(?:the\s+)?(?:web|internet)\s+for)\s+(?P<query>.+)\s*$",
                r"^(?:what\s+is|who\s+is|how\s+to|how\s+do|why\s+(?:is|are|do|does|did)|when\s+(?:is|was|did)|where\s+(?:is|was|can))\s+(?P<query>.+)\s*$",
                r"^(?P<query>.+)\s+(?:information|info|details)\s*$",
                r"^(?:tell\s+me\s+about|give\s+me\s+(?:info|information)\s+about|explain)\s+(?P<query>.+)\s*$",
            ],
            action="search_web",
        ))

        # ── PLAY YOUTUBE ──
        self._patterns.append(IntentPattern(
            intent="PLAY_YOUTUBE",
            confidence=0.92,
            priority=82,
            patterns=[
                r"^play\s+(?P<query>.+?)\s+on\s+youtube\s*$",
                r"^play\s+(?P<query>.+?)\s+(?:video|song|music)\s*$",
                r"^(?:watch|show|play)\s+(?P<query>.+?)\s+on\s+youtube\s*$",
                r"^youtube\s+(?:play|watch)\s+(?P<query>.+)\s*$",
                r"^(?:play|watch)\s+(?P<query>.+?)\s+(?:on\s+)?(?:yt|youtube)\s*$",
            ],
            action="play_youtube",
        ))

        # ── PLAY SPOTIFY ──
        self._patterns.append(IntentPattern(
            intent="PLAY_SPOTIFY",
            confidence=0.92,
            priority=83,
            patterns=[
                r"^play\s+(?P<query>.+?)\s+on\s+spotify\s*$",
                r"^spotify\s+(?:play|search)\s+(?P<query>.+)\s*$",
                r"^(?:play|stream)\s+(?P<query>.+?)\s+(?:on\s+)?spotify\s*$",
            ],
            action="play_spotify",
        ))

        # ── PLAY MUSIC (generic - fallback to YouTube) ──
        self._patterns.append(IntentPattern(
            intent="PLAY_MUSIC",
            confidence=0.88,
            priority=80,
            patterns=[
                r"^play\s+(?P<query>.+)\s*$",
                r"^(?:play|put\s+on|stream)\s+(?:some\s+)?(?P<query>.+?)\s+(?:music|song|audio|tune|track)\s*$",
                r"^(?:play|put\s+on|stream)\s+(?:some\s+)?(?P<query>.+)\s*$",
            ],
            action="play_music",
        ))

        # ── WEATHER ──
        self._patterns.append(IntentPattern(
            intent="GET_WEATHER",
            confidence=0.95,
            priority=75,
            patterns=[
                r"^(?:weather|forecast|temperature)\s+(?:in|at|for|of)\s+(?P<city>.+)\s*$",
                r"^(?:what'?s?|what\s+is)\s+the\s+weather\s+(?:in|at|for|of)\s+(?P<city>.+)\s*$",
                r"^(?:what'?s?|what\s+is)\s+the\s+weather\s+like\s+(?:in|at|for)\s+(?P<city>.+)\s*$",
                r"^(?:how'?s?|how\s+is)\s+the\s+weather\s+(?:in|at|for)\s+(?P<city>.+)\s*$",
                r"^(?:weather|forecast|temperature)\s+(?P<city>.+)\s*$",
            ],
            action="get_weather",
        ))

        # ── NEWS ──
        self._patterns.append(IntentPattern(
            intent="GET_NEWS",
            confidence=0.90,
            priority=70,
            patterns=[
                r"^(?:latest|breaking|today'?s?|current|recent)\s+(?:news|headlines)\s*(?:about|on|in|of|for)\s+(?P<topic>.+)\s*$",
                r"^(?:news|headlines)\s+(?:about|on|in|of|for)\s+(?P<topic>.+)\s*$",
                r"^(?:show|give|tell|get|fetch)\s+(?:me\s+)?(?:the\s+)?(?:latest\s+)?(?:news|headlines)\s*$",
                r"^(?:latest|breaking|today'?s?|current)\s+(?:news|headlines)\s*$",
                r"^(?:news|headlines)\s*$",
                r"^(?:what'?s?|what\s+is)\s+happening\s+(?:in|around)\s+(?P<topic>.+)\s*$",
            ],
            action="get_news",
        ))

        # ── SYSTEM STATUS ──
        self._patterns.append(IntentPattern(
            intent="SYSTEM_STATUS",
            confidence=0.95,
            priority=93,
            patterns=[
                r"^(?:system|computer|pc|laptop)\s+(?:status|stats|info|information|health|performance)\s*$",
                r"^(?:show|get|check|display)\s+(?:my\s+)?(?:system|computer|pc)\s+(?:status|stats|info|information|health|performance)\s*$",
                r"^(?:what'?s?|what\s+is)\s+(?:the\s+)?(?:system|computer|pc)\s+(?:status|health|performance)\s*$",
                r"^(?:how'?s?|how\s+is)\s+(?:my\s+)?(?:system|computer|pc)\s+(?:doing|running|performing)\s*$",
                r"^(?:cpu|memory|ram|disk)\s+(?:usage|status|info)\s*$",
                r"^(?:system|computer)\s+monitor(ing)?\s*$",
            ],
            action="system_status",
        ))

        # ── VOLUME CONTROL ──
        self._patterns.append(IntentPattern(
            intent="VOLUME_CONTROL",
            confidence=0.95,
            priority=92,
            patterns=[
                r"^volume\s+(up|down|increase|decrease|raise|lower)\s*$",
                r"^(?:turn|put)\s+(?:it\s+)?(?:the\s+volume\s+)?(?:up|down)\s*$",
                r"^(?:increase|decrease|raise|lower)\s+(?:the\s+)?volume\s*$",
                r"^(?:mute|unmute|silence|unsilence)\s*(?:the\s+)?(?:audio|sound|volume)?\s*$",
                r"^set\s+volume\s+(?:to\s+)?(?P<value>\d+)\s*$",
                r"^(?:volume|sound)\s+(?P<value>\d+)\s*(?:percent|%)?\s*$",
            ],
            action="volume_control",
        ))

        # ── BRIGHTNESS CONTROL ──
        self._patterns.append(IntentPattern(
            intent="BRIGHTNESS_CONTROL",
            confidence=0.93,
            priority=85,
            patterns=[
                r"^brightness\s+(up|down|increase|decrease|raise|lower)\s*$",
                r"^(?:turn|make)\s+(?:it\s+|the\s+screen\s+)?(?:brighter|dimmer)\s*$",
                r"^(?:increase|decrease|raise|lower)\s+(?:the\s+)?brightness\s*$",
                r"^set\s+brightness\s+(?:to\s+)?(?P<value>\d+)\s*$",
                r"^screen\s+(?:brightness\s+)?(?:up|down)\s*$",
            ],
            action="brightness_control",
        ))

        # ── SCREENSHOT ──
        self._patterns.append(IntentPattern(
            intent="SCREENSHOT",
            confidence=0.95,
            priority=88,
            patterns=[
                r"^(?:take|get|capture|grab|do)\s+(?:a\s+)?(?:screenshot|screen\s*shot|screen\s*capture|snapshot)\s*$",
                r"^(?:screenshot|screen\s*shot|screen\s*capture)\s*(?:now|please)?\s*$",
                r"^capture\s+(?:the\s+)?screen\s*$",
            ],
            action="screenshot",
        ))

        # ── CLIPBOARD ──
        self._patterns.append(IntentPattern(
            intent="CLIPBOARD",
            confidence=0.90,
            priority=72,
            patterns=[
                r"^(?:get|show|read|paste|what'?s?\s+on)\s+(?:the\s+)?(?:clipboard|clip\s*board)\s*$",
                r"^(?:what'?s?|what\s+is)\s+(?:copied|on\s+the\s+clipboard)\s*$",
                r"^copy\s+(?:this|that|the\s+following|['\"]?.+?['\"]?)\s+(?:to\s+)?(?:clipboard)?\s*$",
                r"^(?:clear|empty)\s+(?:the\s+)?clipboard\s*$",
            ],
            action="clipboard",
        ))

        # ── SYSTEM POWER ──
        self._patterns.append(IntentPattern(
            intent="SYSTEM_POWER",
            confidence=0.95,
            priority=91,
            patterns=[
                r"^(?:shut\s*down|shutdown|power\s*off|poweroff)\s+(?:the\s+)?(?:computer|pc|system|laptop)?\s*$",
                r"^(?:restart|reboot)\s+(?:the\s+)?(?:computer|pc|system|laptop)?\s*$",
                r"^(?:sleep|hibernate)\s+(?:the\s+)?(?:computer|pc|system|laptop)?\s*$",
                r"^(?:lock|log\s*out)\s+(?:the\s+)?(?:computer|pc|system|session|workstation)?\s*$",
                r"^(?:cancel|abort)\s+(?:shutdown|restart)\s*$",
            ],
            action="system_power",
        ))

        # ── CALCULATOR ──
        self._patterns.append(IntentPattern(
            intent="CALCULATOR",
            confidence=0.92,
            priority=78,
            patterns=[
                r"^(?:calculate|calc|compute|eval|solve|evaluate)\s+(?P<expression>.+)\s*$",
                r"^(?:what'?s?|what\s+is)\s+(?P<expression>\d[\d\s+\-*/().%^]+)\s*$",
                r"^(?P<expression>\d[\d\s+\-*/().%^]+)\s*$",
                r"^(?:what'?s?|what\s+is)\s+(?P<expression>.+?)\s+(?:equal|equals|result)\s*$",
            ],
            action="calculator",
        ))

        # ── TIMER ──
        self._patterns.append(IntentPattern(
            intent="TIMER",
            confidence=0.93,
            priority=76,
            patterns=[
                r"^(?:set|start|create|begin)\s+(?:a\s+)?timer\s+(?:for\s+)?(?P<seconds>\d+)\s*(?:seconds?|secs?|minutes?|mins?|hours?|hrs?)?\s*$",
                r"^timer\s+(?P<seconds>\d+)\s*(?:seconds?|secs?|minutes?|mins?|hours?|hrs?)?\s*$",
                r"^(?:remind|reminder)\s+(?:me\s+)?(?:in|after)\s+(?P<seconds>\d+)\s*(?:seconds?|secs?|minutes?|mins?|hours?|hrs?)?\s*$",
                r"^(?:set|start)\s+(?:a\s+)?(?P<seconds>\d+)\s*(?:seconds?|secs?|minutes?|mins?|hours?|hrs?)?\s+(?:timer|alarm|reminder)\s*$",
            ],
            action="timer",
        ))

        # ── DAILY BRIEFING ──
        self._patterns.append(IntentPattern(
            intent="DAILY_BRIEFING",
            confidence=0.95,
            priority=87,
            patterns=[
                r"^(?:daily\s+)?(?:briefing|schedule|agenda|plan)\s*$",
                r"^(?:what'?s?|what\s+is)\s+(?:on\s+)?my\s+(?:schedule|agenda|plan)\s*$",
                r"^(?:what\s+do\s+i\s+have)\s+(?:today|tomorrow|this\s+week)?\s*$",
                r"^(?:give\s+me\s+(?:a\s+)?(?:daily\s+)?briefing)\s*$",
                r"^(?:start\s+my\s+day|morning\s+briefing)\s*$",
            ],
            action="daily_briefing",
        ))

        # ── SAVE MEMORY ──
        self._patterns.append(IntentPattern(
            intent="SAVE_MEMORY",
            confidence=0.94,
            priority=86,
            patterns=[
                r"^(?:remember|save|store|keep|note)\s+(?:this|that|the\s+following|it)\s*$",
                r"^(?:remember|save|store|keep|note)\s+(?:this\s+)?(?:to\s+)?(?:memory|for\s+)?(?:me|later)\s*$",
                r"^(?:add|put)\s+(?:this|that)\s+to\s+(?:my\s+)?(?:memory|notes|journal)\s*$",
                r"^(?:don'?t?\s+forget|never\s+forget)\s+(?:to\s+)?(?:about\s+)?(.+)\s*$",
                r"^(?:this\s+is|that\s+is)\s+important\s*$",
                r"^save\s+this\s+to\s+memory\s*$",
            ],
            action="save_memory",
        ))

        # ── RECALL MEMORY ──
        self._patterns.append(IntentPattern(
            intent="RECALL_MEMORY",
            confidence=0.88,
            priority=74,
            patterns=[
                r"^(?:recall|what|tell\s+me|show)\s+(?:do\s+you\s+|did\s+you\s+)?(?:remember|know|have)\s+(?:about\s+)?(?P<query>.+)\s*$",
                r"^(?:search|find|look)\s+(?:in\s+)?(?:my\s+)?(?:memory|notes)\s*(?:for\s+)?(?P<query>.+)?\s*$",
                r"^(?:what|which)\s+(?:did\s+you|have\s+you)\s+(?:learn|discover|find)\s*$",
                r"^(?:do\s+you\s+know)\s+(?:about\s+)?(?P<query>.+)\s*$",
                r"^recall\s+(?:my\s+)?(?:notes|memory)\s*$",
            ],
            action="recall_memory",
        ))

        # ── WINDOW CONTROL ──
        self._patterns.append(IntentPattern(
            intent="WINDOW_CONTROL",
            confidence=0.88,
            priority=82,
            patterns=[
                r"^(?:minimize|maximize|restore|close)\s+(?:the\s+)?(?:current\s+)?(?:window|app|application)\s*$",
                r"^(?:switch|toggle)\s+to\s+(?P<target>.+)\s*$",
                r"^(?:focus|bring)\s+(?:the\s+)?(?:window|app)\s+(?:to\s+)?(?:the\s+)?(?:front|foreground)\s*$",
                r"^(?:show|go\s+to)\s+(?:the\s+)?desktop\s*$",
                r"^(?:next|previous)\s+window\s*$",
            ],
            action="window_control",
        ))

        # ── SCREEN INFO ──
        self._patterns.append(IntentPattern(
            intent="SCREEN_INFO",
            confidence=0.90,
            priority=68,
            patterns=[
                r"^(?:screen|display|monitor)\s+(?:resolution|info|information|size|details)\s*$",
                r"^(?:what'?s?|what\s+is)\s+(?:my\s+)?(?:screen|display)\s+(?:resolution|size)\s*$",
                r"^(?:what|which)\s+(?:is\s+)?(?:my\s+)?(?:screen|display)\s+size\s*$",
            ],
            action="screen_info",
        ))

        # ── SPEED TEST ──
        self._patterns.append(IntentPattern(
            intent="SPEED_TEST",
            confidence=0.88,
            priority=66,
            patterns=[
                r"^(?:network|internet)\s+(?:speed|test|speedtest|performance)\s*$",
                r"^(?:run|do|check|start)\s+(?:a\s+)?(?:network|internet)\s+(?:speed|test)\s*$",
                r"^speed\s*test\s*$",
            ],
            action="speed_test",
        ))

        # ── TYPE TEXT ──
        self._patterns.append(IntentPattern(
            intent="TYPE_TEXT",
            confidence=0.88,
            priority=77,
            patterns=[
                r"^(?:type|write|enter|input)\s+(?:the\s+)?(?:text|word|words|sentence)?\s*['\"]?(?P<text>.+?)['\"]?\s*$",
                r"^(?:type|write)\s+(?P<text>.+)\s*$",
            ],
            action="type_text",
        ))

        # ── MOUSE CONTROL ──
        self._patterns.append(IntentPattern(
            intent="MOUSE_CONTROL",
            confidence=0.85,
            priority=73,
            patterns=[
                r"^(?:move|click|double.?click|right.?click|drag)\s+(?:the\s+)?(?:mouse|cursor)\s*(?:to\s+(?P<x>\d+)\s*,?\s*(?P<y>\d+))?\s*$",
                r"^mouse\s+(?:move|click|position)\s*$",
                r"^(?:scroll|scroll\s+up|scroll\s+down)\s*$",
            ],
            action="mouse_control",
        ))

        # ── JOKE ──
        self._patterns.append(IntentPattern(
            intent="JOKE",
            confidence=0.93,
            priority=64,
            patterns=[
                r"^(?:tell|make|give|crack|say)\s+(?:me\s+)?(?:a\s+)?(?:joke|funny)\s*$",
                r"^joke\s*$",
                r"^joke\s+(?:please|now)?\s*$",
                r"^(?:make|let)\s+me\s+laugh\s*$",
                r"^(?:tell|give)\s+(?:me\s+)?(?:a\s+)?joke\s*$",
            ],
            action="get_joke",
        ))

        # ── QUOTE ──
        self._patterns.append(IntentPattern(
            intent="QUOTE",
            confidence=0.90,
            priority=62,
            patterns=[
                r"^(?:give|tell|show|get|inspire)\s+(?:me\s+)?(?:a\s+)?(?:quote|inspiration|motivational)\s*$",
                r"^(?:quote|inspire\s+me)\s+(?:of\s+the\s+day|please|now)?\s*$",
                r"^(?:motivational|inspirational)\s+(?:quote|words)\s*$",
                r"^inspire\s+me\s*$",
            ],
            action="get_quote",
        ))

        # ── COIN FLIP ──
        self._patterns.append(IntentPattern(
            intent="COIN_FLIP",
            confidence=0.95,
            priority=60,
            patterns=[
                r"^(?:flip|toss)\s+(?:a\s+)?(?:coin|quarter)\s*$",
                r"^heads\s+or\s+tails\s*$",
            ],
            action="flip_coin",
        ))

        # ── DICE ROLL ──
        self._patterns.append(IntentPattern(
            intent="DICE_ROLL",
            confidence=0.95,
            priority=59,
            patterns=[
                r"^(?:roll|throw|toss)\s+(?:a\s+)?(?:(?P<sides>\d+)\s*(?:sided\s+)?)?(?:dice|die|d\s*6)\s*$",
                r"^d(?P<sides>\d+)\s*$",
            ],
            action="roll_dice",
        ))

        # ── DATETIME ──
        self._patterns.append(IntentPattern(
            intent="DATETIME",
            confidence=0.95,
            priority=90,
            patterns=[
                r"^(?:what'?s?|what\s+is|tell\s+me)\s+(?:the\s+)?(?:time|date|day)\s*$",
                r"^(?:current|today'?s?)\s+(?:time|date|day)\s*$",
                r"^(?:what|which)\s+(?:day|date|time)\s+is\s+(?:it|today)\s*$",
                r"^(?:tell\s+me\s+the\s+)?(?:time|date)\s*$",
                r"^what\s+day\s+is\s+it\s+today\s*$",
            ],
            action="get_datetime",
        ))

        # ── NASA APOD ──
        self._patterns.append(IntentPattern(
            intent="NASA_APOD",
            confidence=0.95,
            priority=65,
            patterns=[
                r"^nasa\s+(?:apod|picture\s+of\s+the\s+day|astronomy\s+picture)\s*$",
                r"^(?:show|get|display)\s+(?:nasa\s+)?(?:astronomy\s+)?picture\s+(?:of\s+)?(?:the\s+)?day\s*$",
                r"^(?:picture|photo|image)\s+of\s+the\s+day\s*$",
            ],
            action="nasa_apod",
        ))

        # ── NASA MARS ──
        self._patterns.append(IntentPattern(
            intent="NASA_MARS",
            confidence=0.90,
            priority=63,
            patterns=[
                r"^nasa\s+mars\s+(?:rover|photo|picture|photos)\s*$",
                r"^(?:show|get)\s+(?:me\s+)?mars\s+rover\s+(?:photos?|pictures?)?\s*$",
                r"^mars\s+rover\s+(?:photos?|pictures?)?\s*$",
                r"^(?:show|get|fetch)\s+(?:me\s+)?mars\s+(?:photos?|pictures?)\s*$",
            ],
            action="nasa_mars",
        ))

        # ── ISS LOCATION ──
        self._patterns.append(IntentPattern(
            intent="ISS_LOCATION",
            confidence=0.90,
            priority=86,
            patterns=[
                r"^(?:iss|international\s+space\s+station)\s+(?:location|where|position|track)\s*$",
                r"^where\s+is\s+(?:the\s+)?(?:iss|international\s+space\s+station)\s*$",
                r"^(?:track|locate)\s+(?:the\s+)?iss\s*$",
                r"^where(?:'s| is)\s+the\s+iss\s*$",
            ],
            action="iss_location",
        ))

        # ── CHAT (conversational) ──
        self._patterns.append(IntentPattern(
            intent="CHAT",
            confidence=0.92,
            priority=87,
            patterns=[
                r"^tell\s+me\s+about\s+yourself\s*$",
                r"^(?:who|what)\s+(?:are|r)\s+you\s*$",
                r"^how\s+(?:are|r)\s+you\s*(?:doing)?\s*$",
                r"^(?:hello|hi|hey|howdy|greetings|good\s+(?:morning|afternoon|evening|night))\s*$",
            ],
            action="chat",
        ))

        # ── STOCK QUOTE ──
        self._patterns.append(IntentPattern(
            intent="STOCK_QUOTE",
            confidence=0.90,
            priority=71,
            patterns=[
                r"^(?:stock|share|price|quote)\s+(?:price|of|for|info|information)?\s*(?P<symbol>\w+)\s*$",
                r"^(?P<symbol>\w+)\s+(?:stock|share)\s+(?:price|quote)\s*$",
                r"^(?P<symbol>\w+)\s+stock\s*$",
                r"^(?:what'?s?|what\s+is)\s+(?:the\s+)?(?:stock|share)\s+price\s+(?:of\s+)?(?P<symbol>\w+)\s*$",
            ],
            action="stock_quote",
        ))

        # ── RANDOM FACT ──
        self._patterns.append(IntentPattern(
            intent="RANDOM_FACT",
            confidence=0.90,
            priority=61,
            patterns=[
                r"^(?:tell|give|show|get)\s+(?:me\s+)?(?:a\s+)?(?:random\s+)?(?:fact|trivia)\s*$",
                r"^(?:fact|fun\s+fact|random\s+fact)\s+(?:please|now)?\s*$",
                r"^did\s+you\s+know\s*$",
            ],
            action="random_fact",
        ))

        # ── IP LOOKUP ──
        self._patterns.append(IntentPattern(
            intent="IP_LOOKUP",
            confidence=0.90,
            priority=67,
            patterns=[
                r"^(?:what'?s?|what\s+is|find|look\s+up|trace)\s+(?:my\s+)?(?:ip|ip\s+address)\s*$",
                r"^ip\s+(?:address\s+)?(?:lookup|info|geolocation)\s*$",
                r"^(?:my|show\s+my)\s+ip\s+address\s*$",
            ],
            action="ip_lookup",
        ))

        # ── NUTRITION ──
        self._patterns.append(IntentPattern(
            intent="NUTRITION_INFO",
            confidence=0.85,
            priority=58,
            patterns=[
                r"^(?:nutrition|calories?|protein|carbs?|fat|food\s+info)\s+(?:for|of|in)\s+(?P<query>.+)\s*$",
                r"^(?:how\s+many\s+)?(?:calories|protein|carbs|fat)\s+(?:in|does|are)\s+(?:in\s+)?(?P<query>.+)\s*$",
            ],
            action="nutrition_info",
        ))

        # ── EMAIL VALIDATE ──
        self._patterns.append(IntentPattern(
            intent="EMAIL_VALIDATE",
            confidence=0.88,
            priority=57,
            patterns=[
                r"^(?:validate|verify|check)\s+(?:email|e.?mail)\s+(?P<email>[^\s]+)\s*$",
                r"^is\s+(?:this\s+)?(?:email|e.?mail)\s+(?P<email>[^\s]+)\s+(?:valid|legitimate|real)\s*$",
            ],
            action="email_validate",
        ))

        # ── EXERCISES ──
        self._patterns.append(IntentPattern(
            intent="EXERCISES",
            confidence=0.85,
            priority=56,
            patterns=[
                r"^(?:exercise|workout|gym)\s+(?:for|routine|info|guide)\s+(?P<query>.+)\s*$",
                r"^(?:tell|give|show)\s+(?:me\s+)?(?:exercises?|workouts?)\s+(?:for|to|about)\s+(?P<query>.+)\s*$",
            ],
            action="exercises",
        ))

        # ── SENTIMENT ──
        self._patterns.append(IntentPattern(
            intent="SENTIMENT_ANALYSIS",
            confidence=0.82,
            priority=55,
            patterns=[
                r"^(?:sentiment|sentiment\s+analysis|mood)\s+(?:of|analyze|analysis|check)\s+(?P<text>.+)\s*$",
                r"^analyze\s+(?:the\s+)?(?:sentiment|mood|tone|emotion)\s+(?:of\s+)?(?P<text>.+)\s*$",
            ],
            action="sentiment_analysis",
        ))

        # ── HOLIDAYS ──
        self._patterns.append(IntentPattern(
            intent="HOLIDAYS",
            confidence=0.85,
            priority=54,
            patterns=[
                r"^(?:holidays?|festivals?|events?)\s+(?:in|for|on)\s+(?P<country>.+)\s*$",
                r"^(?:list|show|get)\s+(?:holidays?|festivals?)\s*$",
                r"^(?:national|public)\s+(?:holidays?)\s*$",
            ],
            action="holidays",
        ))

        # ── PLOT CHART ──
        self._patterns.append(IntentPattern(
            intent="PLOT_CHART",
            confidence=0.80,
            priority=53,
            patterns=[
                r"^(?:plot|draw|create|make|show)\s+(?:a\s+)?(?P<type>bar|line|pie)\s+(?:chart|graph|plot)\s*$",
                r"^(?:plot|draw|create|make|show)\s+(?:a\s+)?(?:chart|graph|plot)\s*$",
            ],
            action="plot_chart",
        ))

        # ── TODO ──
        self._patterns.append(IntentPattern(
            intent="ADD_TODO",
            confidence=0.90,
            priority=81,
            patterns=[
                r"^(?:add|create|make)\s+(?:a\s+)?(?:todo|to.?do\s+item|task|reminder)\s*(?:to|for|about)?\s*(?P<task>.+)?\s*$",
                r"^(?:remind|reminder)\s+(?:me\s+)?(?:to|about)\s+(?P<task>.+)\s*$",
                r"^(?:don'?t?\s+forget)\s+(?:to|about)\s+(?P<task>.+)\s*$",
            ],
            action="add_todo",
        ))

        # ── LIST TODOS ──
        self._patterns.append(IntentPattern(
            intent="LIST_TODOS",
            confidence=0.90,
            priority=80,
            patterns=[
                r"^(?:list|show|get|what\s+are)\s+(?:my\s+)?(?:todos?|to.?do\s+(?:list|items|tasks)|tasks|reminders)\s*$",
                r"^(?:what\s+(?:do\s+i\s+need\s+to\s+do|is\s+on\s+my\s+(?:list|todo)))\s*$",
            ],
            action="list_todos",
        ))

        # ── ADD NOTE ──
        self._patterns.append(IntentPattern(
            intent="ADD_NOTE",
            confidence=0.88,
            priority=79,
            patterns=[
                r"^(?:add|create|make|save|take)\s+(?:a\s+)?note\s*$",
                r"^(?:note|note\s+down)\s+(?:this|that|it)\s*$",
            ],
            action="add_note",
        ))

        # ── LIST NOTES ──
        self._patterns.append(IntentPattern(
            intent="LIST_NOTES",
            confidence=0.88,
            priority=78,
            patterns=[
                r"^(?:list|show|get|find)\s+(?:my\s+)?(?:notes|saved\s+notes)\s*$",
            ],
            action="list_notes",
        ))

        # Sort by priority (highest first)
        self._patterns.sort(key=lambda p: p.priority, reverse=True)

    def get_patterns(self) -> list[IntentPattern]:
        """Return all patterns sorted by priority."""
        return self._patterns

    def get_pattern(self, intent: str) -> IntentPattern | None:
        """Get pattern by intent name."""
        for p in self._patterns:
            if p.intent == intent:
                return p
        return None
