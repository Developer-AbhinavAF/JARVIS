"""Comprehensive intent types for JARVIS NLP engine.

All 18 supported intents with metadata and classification confidence ranges.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Dict, Any


class Intent(Enum):
    """All 18 supported intents in JARVIS."""
    
    # Website & Navigation
    OPEN_WEBSITE = auto()           # open youtube, open github
    
    # Search Intents
    SEARCH_YOUTUBE = auto()         # search gamerfleet on youtube
    SEARCH_WEB = auto()             # search X on google, google X
    SEARCH_WIKIPEDIA = auto()       # search X on wikipedia
    SEARCH_GITHUB = auto()          # search X on github
    
    # Entertainment/Media
    PLAY_YOUTUBE = auto()           # play shape of you
    PLAY_SPOTIFY = auto()           # play song on spotify
    
    # Information Queries
    GET_WEATHER = auto()            # weather in delhi
    GET_NEWS = auto()               # latest AI news
    GET_STOCK = auto()              # stock price AAPL
    GET_CRYPTO = auto()             # bitcoin price
    GET_NASA_APOD = auto()          # nasa apod
    
    # Document/Media Analysis
    READ_DOCUMENT = auto()          # read file.pdf, analyze document
    ANALYZE_IMAGE = auto()          # analyze image.png
    
    # Memory & Learning
    SAVE_MEMORY = auto()            # save this to memory
    RECALL_MEMORY = auto()          # what do I know about X
    LEARN = auto()                  # learn from this content
    
    # General Conversation
    CHAT = auto()                   # general chat/fallback


@dataclass
class IntentConfig:
    """Configuration for an intent."""
    intent: Intent
    priority: int                          # 0-100, higher = more specific
    min_confidence: float                  # Minimum confidence threshold
    command_words: List[str]              # Words that trigger this intent
    platform_names: List[str]             # Platform/website names
    patterns: List[str]                   # Regex patterns for matching


# Intent Configurations with priorities and confidence thresholds
INTENT_CONFIGS: Dict[Intent, IntentConfig] = {
    Intent.OPEN_WEBSITE: IntentConfig(
        intent=Intent.OPEN_WEBSITE,
        priority=95,
        min_confidence=0.92,
        command_words=["open", "launch", "go to", "visit", "start"],
        platform_names=["youtube", "google", "github", "spotify", "netflix", "amazon", 
                       "linkedin", "reddit", "twitter", "instagram", "facebook"],
        patterns=[
            r"^(?:open|launch|go\s+to|visit|start)\s+(?:the\s+)?(?:website\s+)?({platform})\s*$",
        ],
    ),
    
    Intent.SEARCH_YOUTUBE: IntentConfig(
        intent=Intent.SEARCH_YOUTUBE,
        priority=94,
        min_confidence=0.91,
        command_words=["search", "find", "look for", "search for"],
        platform_names=["youtube", "youtube.com"],
        patterns=[
            r"^(?:search|find|look\s+for)\s+(.+?)\s+on\s+youtube\s*$",
            r"^(?:search|find|look\s+for)\s+(.+?)\s+on\s+yt\s*$",
        ],
    ),
    
    Intent.SEARCH_WEB: IntentConfig(
        intent=Intent.SEARCH_WEB,
        priority=85,
        min_confidence=0.85,
        command_words=["search", "find", "look for", "google"],
        platform_names=["google", "web", "internet"],
        patterns=[
            r"^(?:search|google|find)\s+(.+)$",
            r"^(?:search|find|look\s+for)\s+(?:on\s+)?(?:web|internet|google)\s+(.+)$",
        ],
    ),
    
    Intent.SEARCH_WIKIPEDIA: IntentConfig(
        intent=Intent.SEARCH_WIKIPEDIA,
        priority=92,
        min_confidence=0.90,
        command_words=["search", "find", "look for"],
        platform_names=["wikipedia"],
        patterns=[
            r"^(?:search|find|look\s+for)\s+(.+?)\s+on\s+wikipedia\s*$",
            r"^wikipedia\s+(.+)$",
        ],
    ),
    
    Intent.SEARCH_GITHUB: IntentConfig(
        intent=Intent.SEARCH_GITHUB,
        priority=91,
        min_confidence=0.89,
        command_words=["search", "find"],
        platform_names=["github"],
        patterns=[
            r"^(?:search|find)\s+(.+?)\s+on\s+github\s*$",
            r"^github\s+(.+)$",
        ],
    ),
    
    Intent.PLAY_YOUTUBE: IntentConfig(
        intent=Intent.PLAY_YOUTUBE,
        priority=90,
        min_confidence=0.88,
        command_words=["play"],
        platform_names=["youtube"],
        patterns=[
            r"^play\s+(.+)\s*$",
            r"^(?:play|watch)\s+(?:video|song|music)\s+(.+)$",
        ],
    ),
    
    Intent.PLAY_SPOTIFY: IntentConfig(
        intent=Intent.PLAY_SPOTIFY,
        priority=89,
        min_confidence=0.87,
        command_words=["play"],
        platform_names=["spotify"],
        patterns=[
            r"^play\s+(.+?)\s+on\s+spotify\s*$",
            r"^spotify\s+play\s+(.+)$",
        ],
    ),
    
    Intent.GET_WEATHER: IntentConfig(
        intent=Intent.GET_WEATHER,
        priority=88,
        min_confidence=0.86,
        command_words=["weather"],
        platform_names=[],
        patterns=[
            r"^(?:weather|what'?s?\s+the\s+weather)\s+(?:in|at|for|of)\s+(.+)\s*$",
            r"^(?:what'?s?\s+the\s+)?weather\s+(?:like\s+)?(?:in|at|for)\s+(.+)\s*$",
        ],
    ),
    
    Intent.GET_NEWS: IntentConfig(
        intent=Intent.GET_NEWS,
        priority=87,
        min_confidence=0.85,
        command_words=["news", "latest", "headlines"],
        platform_names=[],
        patterns=[
            r"^(?:latest\s+)?(?:news|headlines)(?:\s+(?:about|on|in|regarding)\s+(.+))?\s*$",
            r"^(?:show|give|tell)\s+me\s+(?:the\s+)?(?:latest\s+)?(?:news|headlines)\s*$",
        ],
    ),
    
    Intent.GET_STOCK: IntentConfig(
        intent=Intent.GET_STOCK,
        priority=83,
        min_confidence=0.82,
        command_words=["stock", "price", "ticker"],
        platform_names=[],
        patterns=[
            r"^(?:stock\s+)?price\s+(?:of\s+)?([A-Z]{1,5})\s*$",
            r"^([A-Z]{1,5})\s+(?:stock|price|ticker)\s*$",
        ],
    ),
    
    Intent.GET_CRYPTO: IntentConfig(
        intent=Intent.GET_CRYPTO,
        priority=82,
        min_confidence=0.81,
        command_words=["crypto", "bitcoin", "ethereum", "price"],
        platform_names=[],
        patterns=[
            r"^(?:crypto|bitcoin|ethereum)\s+price(?:\s+(?:for|of)\s+(.+))?\s*$",
            r"^([a-z]+)\s+(?:crypto|coin)\s+price\s*$",
        ],
    ),
    
    Intent.GET_NASA_APOD: IntentConfig(
        intent=Intent.GET_NASA_APOD,
        priority=75,
        min_confidence=0.80,
        command_words=["nasa", "apod", "astronomy"],
        platform_names=[],
        patterns=[
            r"^(?:nasa\s+)?apod\s*$",
            r"^(?:show|get)\s+(?:nasa\s+)?(?:astronomy\s+)?picture\s+(?:of\s+)?(?:the\s+)?day\s*$",
        ],
    ),
    
    Intent.READ_DOCUMENT: IntentConfig(
        intent=Intent.READ_DOCUMENT,
        priority=80,
        min_confidence=0.79,
        command_words=["read", "open", "analyze", "summarize"],
        platform_names=[],
        patterns=[
            r"^(?:read|open|analyze|summarize)\s+(.+\.(?:pdf|docx?|txt|md))\s*$",
            r"^(?:read|analyze)\s+(?:the\s+)?file\s+(.+)\s*$",
        ],
    ),
    
    Intent.ANALYZE_IMAGE: IntentConfig(
        intent=Intent.ANALYZE_IMAGE,
        priority=81,
        min_confidence=0.78,
        command_words=["analyze", "describe", "what"],
        platform_names=[],
        patterns=[
            r"^(?:analyze|describe|what'?s?\s+in)\s+(.+\.(?:png|jpg|jpeg|gif|webp))\s*$",
            r"^(?:analyze|describe)\s+(?:this\s+)?image\s+(.+)\s*$",
        ],
    ),
    
    Intent.SAVE_MEMORY: IntentConfig(
        intent=Intent.SAVE_MEMORY,
        priority=93,
        min_confidence=0.90,
        command_words=["save", "remember", "store", "keep", "add"],
        platform_names=[],
        patterns=[
            r"^(?:save|remember|store|keep|add)\s+(?:this|that)(?:\s+to\s+memory)?\s*$",
            r"^(?:save|remember)\s+(?:this\s+)?(?:for\s+)?(?:me|later)\s*$",
        ],
    ),
    
    Intent.RECALL_MEMORY: IntentConfig(
        intent=Intent.RECALL_MEMORY,
        priority=86,
        min_confidence=0.84,
        command_words=["recall", "remember", "what", "tell", "do you know"],
        platform_names=[],
        patterns=[
            r"^(?:recall|remember|what\s+do\s+you\s+know\s+about)\s+(.+)\s*$",
            r"^(?:do\s+you\s+know|what.*)\s+(.+)\s*$",
        ],
    ),
    
    Intent.LEARN: IntentConfig(
        intent=Intent.LEARN,
        priority=84,
        min_confidence=0.83,
        command_words=["learn", "study", "analyze", "process"],
        platform_names=[],
        patterns=[
            r"^(?:learn|study|analyze|process)\s+(?:this|that|from\s+)?(.+)\s*$",
            r"^learn\s+(?:from\s+)?(?:this|the)\s+(.+)\s*$",
        ],
    ),
    
    Intent.CHAT: IntentConfig(
        intent=Intent.CHAT,
        priority=0,
        min_confidence=0.0,
        command_words=[],
        platform_names=[],
        patterns=[r".+"],  # Catch-all
    ),
}


def get_intent_config(intent: Intent) -> IntentConfig:
    """Get configuration for an intent."""
    return INTENT_CONFIGS.get(intent)


def get_all_intents() -> List[Intent]:
    """Get all supported intents."""
    return list(INTENT_CONFIGS.keys())
