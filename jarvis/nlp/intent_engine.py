"""Semantic intent detection engine for JARVIS.

Replaces keyword matching with semantic understanding. Instead of checking
``if "youtube" in text``, we compute semantic similarity between the user's
input and intent descriptions stored in the knowledge base.
"""

from __future__ import annotations

from jarvis.nlp.normalizer import normalize
from jarvis.nlp.utils import (
    ExecutionMode,
    GoalCategory,
    IntentCandidate,
    ngram_overlap,
    remove_stop_words,
    remove_stop_words_platform_aware,
    tokenize,
    weighted_token_score,
    word_overlap_score,
)


# ════════════════════════════════════════════════════════════════════
# KNOWLEDGE BASE
# ════════════════════════════════════════════════════════════════════

INTENT_KNOWLEDGE_BASE: dict[str, dict] = {
    # ── Web & Browsing ──────────────────────────────────────────────
    "OPEN_WEBSITE": {
        "descriptions": [
            "open a specific website in the browser",
            "navigate to a web page or URL",
            "launch a site like google or github or amazon",
            "take me to a particular website",
            "visit a url or domain",
            "show me this website",
            "load a webpage",
            "open youtube or any known website",
            "go to a popular site like gmail or reddit",
            "turn on a website in the browser",
            "switch on a website",
            "open reddit or github or stackoverflow",
        ],
        "trigger_phrases": [
            "open website", "go to site", "visit site", "launch site",
            "open url", "browse to", "navigate to", "open youtube",
            "go to youtube", "visit youtube", "open google",
            "go to github", "open amazon", "open gmail",
            "go to reddit", "open .com",
            "turn on youtube", "turn on website", "turn on site",
            "switch on website",
            "open reddit", "open github", "open stackoverflow",
            "go to amazon", "go to gmail", "go to spotify",
            "open spotify", "open netflix", "open twitter",
        ],
        "goal": GoalCategory.INFORMATION,
        "capability": "browser",
        "priority": 5,
        "execution_mode": ExecutionMode.AUTO,
    },
    "SEARCH_WEB": {
        "descriptions": [
            "search the internet for information",
            "look something up on the web",
            "find results on google or bing",
            "query the internet for an answer",
            "web search for a topic",
            "find information online",
            "search engine query",
        ],
        "trigger_phrases": [
            "search web", "google this", "look up", "search online",
            "find on internet", "web search",
        ],
        "goal": GoalCategory.INFORMATION,
        "capability": "browser",
        "priority": 5,
        "execution_mode": ExecutionMode.AUTO,
    },
    "WEB_SEARCH": {
        "descriptions": [
            "perform a generic web search query",
            "search for something on the internet",
            "find online results for a question",
            "query a search engine for results",
            "look something up online",
            "search the world wide web",
        ],
        "trigger_phrases": [
            "search", "look up", "find online", "web search",
        ],
        "goal": GoalCategory.INFORMATION,
        "capability": "browser",
        "priority": 4,
        "execution_mode": ExecutionMode.AUTO,
    },

    # ── Platform Search ──────────────────────────────────────────────
    "SEARCH_ON_PLATFORM": {
        "descriptions": [
            "search for content on reddit or github",
            "search for videos on youtube",
            "look up topics on wikipedia",
            "find repositories on github",
            "search for posts on reddit",
            "query a specific website or platform",
            "search within a particular site",
            "look for items on an online store",
            "search on a platform like amazon or ebay",
            "find content on a particular website or service",
            "search on reddit for discussions",
            "search on github for code",
            "search on youtube for videos",
            "search on wikipedia for articles",
            "search on amazon for products",
        ],
        "trigger_phrases": [
            "search on", "find on", "look on", "browse",
            "search reddit", "search github", "search youtube",
            "search wikipedia", "search amazon", "search ebay",
            "look up on", "find on reddit", "find on github",
            "on reddit", "on github", "on youtube", "on wikipedia",
            "on amazon", "on ebay", "on spotify", "on stackoverflow",
            "search for on", "find on the",
        ],
        "goal": GoalCategory.INFORMATION,
        "capability": "browser",
        "priority": 5,
        "execution_mode": ExecutionMode.AUTO,
    },
    "SEARCH_YOUTUBE": {
        "descriptions": [
            "search for a video on youtube",
            "find youtube content about a topic",
            "look for a youtube video or channel",
            "search youtube for specific content",
            "find a video on youtube to watch",
            "query youtube for results",
        ],
        "trigger_phrases": [
            "youtube search", "search youtube", "find video",
            "look on youtube",
        ],
        "goal": GoalCategory.ENTERTAINMENT,
        "capability": "browser",
        "priority": 5,
        "execution_mode": ExecutionMode.AUTO,
    },

    # ── App Control ──────────────────────────────────────────────────
    "OPEN_APP": {
        "descriptions": [
            "launch or open an application on the computer",
            "start a program that is installed",
            "open a software application",
            "run a desktop app",
            "fire up a program",
            "need to code or write code",
            "open an ide or code editor",
            "start programming or developing",
            "need visual studio or pycharm or vscode",
            "launch a development environment",
            "turn on an application or website",
            "switch on a program or service",
        ],
        "trigger_phrases": [
            "open app", "launch app", "start app", "run app",
            "open program", "launch program", "open vscode",
            "open visual studio", "open pycharm", "start coding",
            "need to code", "open code editor", "open ide",
            "let me code", "launch ide",
            "turn on", "switch on", "fire up",
        ],
        "goal": GoalCategory.SYSTEM,
        "capability": "app_launcher",
        "priority": 8,
        "execution_mode": ExecutionMode.AUTO,
    },
    "CLOSE_APP": {
        "descriptions": [
            "close or quit a running application",
            "shut down a program that is open",
            "terminate an application process",
            "exit a running software",
            "kill an app that is currently running",
        ],
        "trigger_phrases": [
            "close app", "quit app", "kill app", "exit app",
            "close program", "shut down app",
        ],
        "goal": GoalCategory.SYSTEM,
        "capability": "app_launcher",
        "priority": 8,
        "execution_mode": ExecutionMode.CONFIRM,
    },

    # ── Media Playback ───────────────────────────────────────────────
    "PLAY_MUSIC": {
        "descriptions": [
            "play a song or music track",
            "start playing audio or music",
            "play music by an artist or genre",
            "put on some music to listen to",
            "start an audio player with music",
            "music playback control",
            "i want to listen to something",
            "play something in the background",
        ],
        "trigger_phrases": [
            "play music", "play song", "play audio", "put on music",
            "listen to", "start playing", "play something",
            "i want to listen", "background music",
        ],
        "goal": GoalCategory.ENTERTAINMENT,
        "capability": "media_player",
        "priority": 6,
        "execution_mode": ExecutionMode.AUTO,
    },
    "PLAY_YOUTUBE": {
        "descriptions": [
            "play a video on youtube",
            "watch something on youtube",
            "start a youtube video or playlist",
            "open youtube and play content",
            "stream a youtube video",
            "play video from youtube",
        ],
        "trigger_phrases": [
            "play on youtube", "youtube video", "watch youtube",
            "play youtube",
        ],
        "goal": GoalCategory.ENTERTAINMENT,
        "capability": "browser",
        "priority": 6,
        "execution_mode": ExecutionMode.AUTO,
    },
    "PLAY_SPOTIFY": {
        "descriptions": [
            "play music on spotify",
            "start a spotify playlist or song",
            "open spotify and play audio",
            "stream music through spotify",
            "play from spotify library",
            "spotify playback control",
        ],
        "trigger_phrases": [
            "play on spotify", "spotify music", "play spotify",
            "open spotify",
        ],
        "goal": GoalCategory.ENTERTAINMENT,
        "capability": "media_player",
        "priority": 6,
        "execution_mode": ExecutionMode.AUTO,
    },

    # ── Information ──────────────────────────────────────────────────
    "GET_WEATHER": {
        "descriptions": [
            "get current weather conditions",
            "check the weather forecast for today",
            "what is the temperature outside",
            "weather report for a location",
            "is it raining or sunny today",
            "tell me about the weather",
            "forecast information",
        ],
        "trigger_phrases": [
            "weather", "temperature", "forecast", "climate",
            "is it raining", "is it sunny",
        ],
        "goal": GoalCategory.INFORMATION,
        "capability": "api",
        "priority": 5,
        "execution_mode": ExecutionMode.AUTO,
    },
    "GET_NEWS": {
        "descriptions": [
            "get latest news headlines or articles",
            "read the news for today",
            "what is happening in the world right now",
            "find breaking news stories",
            "news summary or briefing",
            "current events and headlines",
        ],
        "trigger_phrases": [
            "news", "headlines", "current events", "breaking news",
            "what is happening",
        ],
        "goal": GoalCategory.INFORMATION,
        "capability": "browser",
        "priority": 5,
        "execution_mode": ExecutionMode.AUTO,
    },
    "SYSTEM_STATUS": {
        "descriptions": [
            "check system resource usage like cpu or ram",
            "what is the current system load",
            "show system information or specs",
            "is the computer running normally",
            "monitor system performance",
            "system health check",
        ],
        "trigger_phrases": [
            "system status", "system info", "system health",
            "cpu usage", "ram usage", "performance",
        ],
        "goal": GoalCategory.SYSTEM,
        "capability": "system_info",
        "priority": 6,
        "execution_mode": ExecutionMode.AUTO,
    },
    "RANDOM_FACT": {
        "descriptions": [
            "tell me a random interesting fact",
            "share a fun trivia or fact",
            "give me a random piece of knowledge",
            "did you know something interesting",
            "share some interesting trivia",
        ],
        "trigger_phrases": [
            "random fact", "fun fact", "did you know", "trivia",
            "interesting fact",
        ],
        "goal": GoalCategory.EDUCATION,
        "capability": "api",
        "priority": 3,
        "execution_mode": ExecutionMode.AUTO,
    },
    "IP_LOOKUP": {
        "descriptions": [
            "check my public ip address",
            "what is my ip address",
            "look up an ip address geolocation",
            "check my internet protocol address",
            "show the current public ip",
        ],
        "trigger_phrases": [
            "my ip", "ip address", "public ip", "ip lookup",
            "what is my ip",
        ],
        "goal": GoalCategory.INFORMATION,
        "capability": "api",
        "priority": 4,
        "execution_mode": ExecutionMode.AUTO,
    },

    # ── Volume & Brightness ──────────────────────────────────────────
    "VOLUME_CONTROL": {
        "descriptions": [
            "change the system volume level",
            "increase or decrease audio volume",
            "mute or unmute the speakers",
            "adjust volume up or down",
            "set volume to a specific level",
        ],
        "trigger_phrases": [
            "volume", "mute", "unmute", "sound level",
            "turn up", "turn down",
        ],
        "goal": GoalCategory.SYSTEM,
        "capability": "system_control",
        "priority": 7,
        "execution_mode": ExecutionMode.AUTO,
    },
    "BRIGHTNESS_CONTROL": {
        "descriptions": [
            "adjust screen brightness level",
            "make the screen brighter or dimmer",
            "change display brightness",
            "set screen luminosity",
            "control monitor brightness",
        ],
        "trigger_phrases": [
            "brightness", "screen brightness", "dim screen",
            "brighten screen", "display brightness",
        ],
        "goal": GoalCategory.SYSTEM,
        "capability": "system_control",
        "priority": 7,
        "execution_mode": ExecutionMode.AUTO,
    },

    # ── System Operations ────────────────────────────────────────────
    "SCREENSHOT": {
        "descriptions": [
            "take a screenshot of the screen",
            "capture what is currently on the display",
            "save a screen capture image",
            "grab a snapshot of the desktop",
            "capture the screen contents as an image",
        ],
        "trigger_phrases": [
            "screenshot", "screen capture", "screen grab",
            "capture screen", "snap screen",
        ],
        "goal": GoalCategory.SYSTEM,
        "capability": "screenshot",
        "priority": 7,
        "execution_mode": ExecutionMode.AUTO,
    },
    "SYSTEM_POWER": {
        "descriptions": [
            "shut down or restart the computer",
            "put the system to sleep or hibernate",
            "power off the machine",
            "log out of the current session",
            "lock the computer screen",
        ],
        "trigger_phrases": [
            "shutdown", "restart", "reboot", "sleep", "hibernate",
            "log out", "lock screen", "power off",
        ],
        "goal": GoalCategory.SYSTEM,
        "capability": "system_power",
        "priority": 10,
        "execution_mode": ExecutionMode.CONFIRM,
    },
    "CLIPBOARD": {
        "descriptions": [
            "copy text to the clipboard",
            "paste content from the clipboard",
            "read what is currently copied",
            "manage clipboard contents",
            "show clipboard history",
        ],
        "trigger_phrases": [
            "clipboard", "copy to clipboard", "paste from clipboard",
            "what is copied",
        ],
        "goal": GoalCategory.SYSTEM,
        "capability": "clipboard",
        "priority": 6,
        "execution_mode": ExecutionMode.AUTO,
    },
    "WINDOW_CONTROL": {
        "descriptions": [
            "minimize, maximize or restore a window",
            "switch between open windows",
            "manage application windows on desktop",
            "tile or arrange windows on screen",
            "focus or bring a window to the front",
        ],
        "trigger_phrases": [
            "minimize window", "maximize window", "switch window",
            "alt tab", "bring window", "window manager",
        ],
        "goal": GoalCategory.SYSTEM,
        "capability": "window_manager",
        "priority": 7,
        "execution_mode": ExecutionMode.AUTO,
    },

    # ── Utilities ────────────────────────────────────────────────────
    "CALCULATOR": {
        "descriptions": [
            "perform a mathematical calculation",
            "solve a math expression or equation",
            "compute arithmetic like addition or division",
            "calculate a number or formula",
            "do some quick math",
        ],
        "trigger_phrases": [
            "calculate", "calculator", "compute", "math",
            "what is", "how much is", "solve",
        ],
        "goal": GoalCategory.PRODUCTIVITY,
        "capability": "calculator",
        "priority": 6,
        "execution_mode": ExecutionMode.AUTO,
    },
    "TIMER": {
        "descriptions": [
            "set a countdown timer for a duration",
            "start a timer or alarm",
            "remind me after a certain number of minutes",
            "create a timed reminder",
            "set a kitchen or work timer",
        ],
        "trigger_phrases": [
            "timer", "countdown", "set alarm", "remind me in",
            "minutes from now",
        ],
        "goal": GoalCategory.PRODUCTIVITY,
        "capability": "timer",
        "priority": 7,
        "execution_mode": ExecutionMode.AUTO,
    },
    "DATETIME": {
        "descriptions": [
            "what is the current date and time",
            "tell me today's date or the time now",
            "what day of the week is it",
            "show me the current timestamp",
            "what is the time in another timezone",
            "what time is it right now",
            "give me the current hour and minute",
            "what is today",
            "tell me the time",
            "give me the current time",
        ],
        "trigger_phrases": [
            "what time", "what date", "today's date", "current time",
            "what day", "what is the time", "time now", "tell time",
            "what is the date", "current date", "time", "date",
            "tell me the time", "give me time",
        ],
        "goal": GoalCategory.INFORMATION,
        "capability": "system_info",
        "priority": 4,
        "execution_mode": ExecutionMode.AUTO,
    },

    # ── Memory ───────────────────────────────────────────────────────
    "SAVE_MEMORY": {
        "descriptions": [
            "remember a piece of information for later",
            "save a fact or preference to memory",
            "store something in long-term memory",
            "note this down so you do not forget",
            "save this information for future reference",
            "remember that my favorite color is blue",
            "store a key value pair like wifi password",
            "tell the assistant your name or personal details",
            "state personal information to be remembered",
            "provide identity information like name or preferences",
        ],
        "trigger_phrases": [
            "remember that", "save to memory", "store that",
            "note this", "keep in mind", "don't forget",
            "remember my", "my wifi", "my password", "save this",
            "remember this",
            "my name is", "my name's", "call me", "i am",
            "i'm called", "i live in", "my favorite", "my email",
            "my phone", "my address", "i work at",
            "name is", "name abhinav", "name john", "name is abhinav",
        ],
        "goal": GoalCategory.PRODUCTIVITY,
        "capability": "memory",
        "priority": 6,
        "execution_mode": ExecutionMode.AUTO,
    },
    "RECALL_MEMORY": {
        "descriptions": [
            "recall previously stored information",
            "what did you remember about something",
            "retrieve a saved fact or preference",
            "look up something from your memory",
            "tell me what you remember",
            "what do you know about a topic",
            "do you know information about me personally",
            "recall personal details like my name",
            "tell me what you know about me",
        ],
        "trigger_phrases": [
            "what do you remember", "recall", "retrieve memory",
            "did you remember", "from memory", "what do you know",
            "what have you stored",
            "do you know my", "you know my", "do you remember my",
            "what is my name", "what's my name", "tell me my",
            "what do you know about me",
            "know my name", "know name", "remember my name",
            "what is my", "what's my",
            "what is my email", "what is my phone", "what is my address",
            "what is my age", "what is my birthday",
            "what's my email", "what's my phone", "what's my address",
            "what's my age", "what's my birthday",
            "do you know my email", "do you know my phone",
            "do you know my name", "do you know my age",
            "tell me my email", "tell me my phone", "tell me my name",
        ],
        "goal": GoalCategory.PRODUCTIVITY,
        "capability": "memory",
        "priority": 6,
        "execution_mode": ExecutionMode.AUTO,
    },

    # ── Programming ──────────────────────────────────────────────────
    "PROGRAMMING": {
        "descriptions": [
            "i need to write code or program",
            "start a coding session or development work",
            "open an ide or code editor for programming",
            "i want to code or develop software",
            "set up a programming environment",
            "help me with coding or programming",
        ],
        "trigger_phrases": [
            "need coding", "start coding", "write code", "programming",
            "code editor", "ide", "development", "let me code",
            "coding environment", "open vscode",
        ],
        "goal": GoalCategory.PROGRAMMING,
        "capability": "app_launcher",
        "priority": 7,
        "execution_mode": ExecutionMode.AUTO,
    },

    # ── Fun & Casual ─────────────────────────────────────────────────
    "JOKE": {
        "descriptions": [
            "tell me a joke to make me laugh",
            "say something funny or humorous",
            "share a joke or pun",
            "make me smile with humor",
            "give me a good laugh",
            "i am bored entertain me with humor",
            "say something amusing or entertaining",
        ],
        "trigger_phrases": [
            "tell me a joke", "say something funny", "make me laugh",
            "joke", "funny", "pun", "bored", "entertain me",
            "make me smile", "say something fun",
        ],
        "goal": GoalCategory.ENTERTAINMENT,
        "capability": "llm",
        "priority": 3,
        "execution_mode": ExecutionMode.AUTO,
    },
    "QUOTE": {
        "descriptions": [
            "share an inspirational or motivational quote",
            "give me a famous quote from someone",
            "say something wise or thought-provoking",
            "tell me a quote of the day",
            "share a meaningful saying or proverb",
        ],
        "trigger_phrases": [
            "quote", "motivational quote", "inspire me",
            "saying", "proverb", "quote of the day",
        ],
        "goal": GoalCategory.ENTERTAINMENT,
        "capability": "llm",
        "priority": 3,
        "execution_mode": ExecutionMode.AUTO,
    },
    "FLIP_COIN": {
        "descriptions": [
            "flip a virtual coin to decide something",
            "heads or tails coin flip",
            "make a random binary choice with a coin",
            "give me a random heads or tails result",
            "flip a coin and tell me the outcome",
        ],
        "trigger_phrases": [
            "flip coin", "heads or tails", "coin flip",
            "toss a coin", "flip a coin",
        ],
        "goal": GoalCategory.ENTERTAINMENT,
        "capability": "calculator",
        "priority": 3,
        "execution_mode": ExecutionMode.AUTO,
    },
    "DICE_ROLL": {
        "descriptions": [
            "roll a virtual die and show the result",
            "give me a random number from one to six",
            "dice roll for a random outcome",
            "roll dice to pick a random number",
            "generate a random dice result",
        ],
        "trigger_phrases": [
            "roll dice", "dice roll", "roll a die",
            "random number", "dice",
        ],
        "goal": GoalCategory.ENTERTAINMENT,
        "capability": "calculator",
        "priority": 3,
        "execution_mode": ExecutionMode.AUTO,
    },

    # ── NASA & Space ─────────────────────────────────────────────────
    "NASA_APOD": {
        "descriptions": [
            "show nasa astronomy picture of the day",
            "what is today's nasa picture of the day",
            "display the apod from nasa",
            "share nasa's daily space image",
            "nasa astronomy photo for today",
        ],
        "trigger_phrases": [
            "nasa picture", "apod", "astronomy picture",
            "nasa photo of the day", "space picture",
        ],
        "goal": GoalCategory.EDUCATION,
        "capability": "api",
        "priority": 4,
        "execution_mode": ExecutionMode.AUTO,
    },
    "NASA_MARS": {
        "descriptions": [
            "show photos from mars taken by a rover",
            "what does mars look like from nasa",
            "display mars rover photographs",
            "show me pictures of the mars surface",
            "nasa mars rover image gallery",
        ],
        "trigger_phrases": [
            "mars photo", "mars rover", "mars picture",
            "nasa mars", "red planet photo",
        ],
        "goal": GoalCategory.EDUCATION,
        "capability": "api",
        "priority": 4,
        "execution_mode": ExecutionMode.AUTO,
    },
    "ISS_LOCATION": {
        "descriptions": [
            "where is the international space station right now",
            "show the current location of the iss",
            "track the international space station live",
            "what is the iss position above earth",
            "live tracking of the space station",
        ],
        "trigger_phrases": [
            "iss location", "space station", "iss tracker",
            "where is the iss", "international space station",
        ],
        "goal": GoalCategory.EDUCATION,
        "capability": "api",
        "priority": 4,
        "execution_mode": ExecutionMode.AUTO,
    },

    # ── Finance ──────────────────────────────────────────────────────
    "STOCK_QUOTE": {
        "descriptions": [
            "get the current stock price of a company",
            "check stock market ticker information",
            "what is the share price of a stock",
            "show me stock quotes or market data",
            "fetch financial ticker information",
        ],
        "trigger_phrases": [
            "stock price", "stock quote", "ticker",
            "share price", "market", "investing",
        ],
        "goal": GoalCategory.FINANCE,
        "capability": "api",
        "priority": 5,
        "execution_mode": ExecutionMode.AUTO,
    },

    # ── Productivity ─────────────────────────────────────────────────
    "ADD_TODO": {
        "descriptions": [
            "add a new task to the to-do list",
            "create a todo item or reminder",
            "add something to my task list",
            "put a new item on my to-do list",
            "track a new task for me",
        ],
        "trigger_phrases": [
            "add todo", "new todo", "to do list", "task list",
            "add task", "create task",
        ],
        "goal": GoalCategory.PRODUCTIVITY,
        "capability": "memory",
        "priority": 6,
        "execution_mode": ExecutionMode.AUTO,
    },
    "LIST_TODOS": {
        "descriptions": [
            "show me all my current to-do items",
            "list all pending tasks on my list",
            "what tasks do I have remaining",
            "display the to-do list",
            "review my open tasks",
        ],
        "trigger_phrases": [
            "show todo", "list todos", "my tasks", "task list",
            "what are my todos",
        ],
        "goal": GoalCategory.PRODUCTIVITY,
        "capability": "memory",
        "priority": 5,
        "execution_mode": ExecutionMode.AUTO,
    },
    "ADD_NOTE": {
        "descriptions": [
            "write down a quick note for later",
            "save a short text note",
            "create a note or memo",
            "jot something down as a note",
            "store a piece of text as a note",
        ],
        "trigger_phrases": [
            "add note", "write note", "new note", "save note",
            "create note", "jot down",
        ],
        "goal": GoalCategory.PRODUCTIVITY,
        "capability": "memory",
        "priority": 5,
        "execution_mode": ExecutionMode.AUTO,
    },

    # ── File Management ──────────────────────────────────────────────
    "OPEN_FOLDER": {
        "descriptions": [
            "open a specific folder in the file explorer",
            "navigate to a directory on the computer",
            "show me a folder's contents",
            "launch file explorer at a path",
            "open a file system location",
        ],
        "trigger_phrases": [
            "open folder", "open directory", "show folder",
            "file explorer", "open path",
        ],
        "goal": GoalCategory.PRODUCTIVITY,
        "capability": "file_manager",
        "priority": 6,
        "execution_mode": ExecutionMode.AUTO,
    },
    "FILE_MANAGEMENT": {
        "descriptions": [
            "copy, move, rename or delete a file",
            "manage files and folders on the system",
            "organize or organize files in a directory",
            "perform file operations like rename or move",
            "manage the file system and disk contents",
        ],
        "trigger_phrases": [
            "copy file", "move file", "rename file", "delete file",
            "file management", "organize files",
        ],
        "goal": GoalCategory.PRODUCTIVITY,
        "capability": "file_manager",
        "priority": 6,
        "execution_mode": ExecutionMode.CONFIRM,
    },

    # ── Greetings ────────────────────────────────────────────────────
    "GREETING": {
        "descriptions": [
            "say hello or greet the assistant",
            "a casual salutation or hello message",
            "start a conversation with a greeting",
            "say hi or good morning",
            "a polite way to begin an interaction",
        ],
        "trigger_phrases": [
            "hello", "hi", "hey", "good morning", "good evening",
            "howdy", "greetings",
        ],
        "goal": GoalCategory.COMMUNICATION,
        "capability": "llm",
        "priority": 2,
        "execution_mode": ExecutionMode.AUTO,
    },
    "CHAT": {
        "descriptions": [
            "engage in casual conversation or small talk",
            "ask how the assistant is doing",
            "have a friendly chat or conversation",
            "ask who the assistant is or what they can do",
            "make small talk or ask personal questions",
            "ask about the assistant's capabilities or identity",
        ],
        "trigger_phrases": [
            "how are you", "what's up", "how's it going",
            "who are you", "what are you", "tell me about yourself",
            "what can you do", "how do you do", "what's new",
            "how are you doing", "how's your day",
            "about yourself", "yourself", "what are you doing",
        ],
        "goal": GoalCategory.COMMUNICATION,
        "capability": "llm",
        "priority": 2,
        "execution_mode": ExecutionMode.AUTO,
    },

    # ── Vision & Visual Analysis ─────────────────────────────────────
    "VISUAL_ANALYSIS": {
        "descriptions": [
            "analyze or understand what is currently visible on screen",
            "read or extract text from the current display",
            "identify elements, buttons, or UI components on screen",
            "understand what application or content is currently showing",
            "explain what is happening on the screen right now",
            "describe the current desktop state or active window",
            "find specific text, errors, or elements on the display",
            "interpret visual information from the computer screen",
            "examine the screen for specific content or patterns",
            "look at and understand what is displayed",
        ],
        "trigger_phrases": [
            "what is on my screen", "what is this", "what am i looking at",
            "read this", "read the screen", "what does this say",
            "explain this", "describe this", "what is showing",
            "what error", "what is this error", "find the button",
            "read this window", "what is open", "summarize this screen",
            "what is active", "which application", "what app is active",
            "what is on the screen", "look at this", "see this",
            "what do you see", "tell me what you see", "analyze this",
            "what is displayed", "what is visible", "whats on screen",
            "read the code", "what does this error mean",
            "explain the error", "describe the screen",
        ],
        "goal": GoalCategory.INFORMATION,
        "capability": "vision",
        "priority": 8,
        "execution_mode": ExecutionMode.AUTO,
    },
}


# ════════════════════════════════════════════════════════════════════
# CONTEXT RULES
# ════════════════════════════════════════════════════════════════════

# Maps a previous intent to intents that naturally follow it, with boost values.
CONTEXT_FOLLOW_UPS: dict[str, dict[str, float]] = {
    "SEARCH_WEB": {
        "OPEN_WEBSITE": 0.15,
        "SEARCH_ON_PLATFORM": 0.10,
        "PLAY_YOUTUBE": 0.10,
        "SAVE_MEMORY": 0.05,
    },
    "OPEN_WEBSITE": {
        "SEARCH_WEB": 0.10,
        "SEARCH_ON_PLATFORM": 0.10,
        "SCREENSHOT": 0.05,
        "PROGRAMMING": 0.05,
    },
    "PLAY_MUSIC": {
        "VOLUME_CONTROL": 0.20,
        "PLAY_SPOTIFY": 0.15,
    },
    "GET_WEATHER": {
        "SEARCH_WEB": 0.10,
        "OPEN_WEBSITE": 0.05,
    },
    "OPEN_APP": {
        "WINDOW_CONTROL": 0.15,
        "CLOSE_APP": 0.10,
        "SCREENSHOT": 0.05,
    },
    "ADD_TODO": {
        "LIST_TODOS": 0.10,
        "SAVE_MEMORY": 0.10,
    },
    "SAVE_MEMORY": {
        "RECALL_MEMORY": 0.10,
        "ADD_TODO": 0.05,
    },
    "PROGRAMMING": {
        "OPEN_APP": 0.15,
        "WINDOW_CONTROL": 0.10,
    },
}


# ════════════════════════════════════════════════════════════════════
# ENGINE
# ════════════════════════════════════════════════════════════════════

class SemanticIntentEngine:
    """Detects user intent via semantic similarity rather than keyword matching.

    The engine pre-computes token sets for every description and trigger phrase
    in the knowledge base, then scores incoming text against these precomputed
    representations using token overlap, bigram overlap, and trigger-phrase
    matching.  Conversation context is used as a secondary boost signal.
    """

    # Weight constants for the multi-signal scoring
    _W_TOKEN_OVERLAP: float = 0.35
    _W_BIGRAM_OVERLAP: float = 0.20
    _W_TRIGGER_PHRASE: float = 0.25
    _W_DESCRIPTION_BEST: float = 0.20

    # Minimum score below which an intent candidate is discarded
    _MIN_CANDIDATE_SCORE: float = 0.05

    def __init__(self) -> None:
        """Pre-compute token sets for every intent in the knowledge base."""
        self._intent_tokens: dict[str, list[list[str]]] = {}
        self._trigger_tokens: dict[str, list[list[str]]] = {}
        self._trigger_raw_tokens: dict[str, list[list[str]]] = {}
        self._bigram_cache: dict[str, list[set[tuple[str, str]]]] = {}

        for intent_name, data in INTENT_KNOWLEDGE_BASE.items():
            # Pre-tokenize descriptions (content words only)
            desc_token_lists: list[list[str]] = []
            for desc in data["descriptions"]:
                tokens = remove_stop_words(tokenize(desc))
                desc_token_lists.append(tokens)
            self._intent_tokens[intent_name] = desc_token_lists

            # Pre-tokenize trigger phrases (content words only, preserving platform prepositions)
            trig_token_lists: list[list[str]] = []
            trig_raw_lists: list[list[str]] = []
            for phrase in data["trigger_phrases"]:
                norm_phrase = normalize(phrase)
                tokens = remove_stop_words_platform_aware(tokenize(norm_phrase))
                trig_token_lists.append(tokens)
                # Also store raw tokens (only removing punctuation, no stop words)
                raw = tokenize(norm_phrase)
                trig_raw_lists.append(raw)
            self._trigger_tokens[intent_name] = trig_token_lists
            self._trigger_raw_tokens[intent_name] = trig_raw_lists

            # Pre-compute bigrams for descriptions
            desc_bigrams: list[set[tuple[str, str]]] = []
            for tokens in desc_token_lists:
                if len(tokens) >= 2:
                    bg = set(zip(tokens, tokens[1:]))
                else:
                    bg = set()
                desc_bigrams.append(bg)
            self._bigram_cache[intent_name] = desc_bigrams

        # Precompute exact trigger phrase lookup: normalized phrase -> intent name
        self._exact_trigger_map: dict[str, str] = {}
        for intent_name, data in INTENT_KNOWLEDGE_BASE.items():
            for phrase in data["trigger_phrases"]:
                norm = normalize(phrase).strip()
                if norm and norm not in self._exact_trigger_map:
                    self._exact_trigger_map[norm] = intent_name

    # ── Public API ──────────────────────────────────────────────────

    def detect(
        self,
        text: str,
        context: dict | None = None,
    ) -> list[IntentCandidate]:
        """Detect intents in *text*, optionally using conversation *context*.

        Returns a list of :class:`IntentCandidate` objects sorted by score
        descending.  Only candidates above the minimum score threshold are
        returned.
        """
        text = normalize(text)
        raw_tokens = tokenize(text)
        input_tokens = remove_stop_words_platform_aware(raw_tokens)

        # If all tokens are stop words, use raw tokens for trigger matching
        use_raw_fallback = False
        if not input_tokens:
            if raw_tokens:
                input_tokens = raw_tokens
                use_raw_fallback = True
            else:
                return []

        # Exact trigger phrase match: if normalized input exactly matches a
        # known trigger phrase, short-circuit with high confidence.
        text_stripped = text.strip()
        if text_stripped in self._exact_trigger_map:
            matched_intent = self._exact_trigger_map[text_stripped]
            intent_data = INTENT_KNOWLEDGE_BASE[matched_intent]
            return [
                IntentCandidate(
                    intent=matched_intent,
                    score=0.95,
                    reason=f"exact trigger phrase match: '{text_stripped}'",
                    goal=intent_data["goal"],
                    required_capability=intent_data["capability"],
                    execution_mode=intent_data["execution_mode"],
                )
            ]

        # Build input bigrams once
        if len(input_tokens) >= 2:
            input_bigrams: set[tuple[str, str]] = set(
                zip(input_tokens, input_tokens[1:])
            )
        else:
            input_bigrams = set()

        candidates: list[IntentCandidate] = []

        for intent_name, intent_data in INTENT_KNOWLEDGE_BASE.items():
            score, reason = self._score_intent(
                input_tokens,
                input_bigrams,
                intent_name,
                context,
                use_raw_fallback,
            )
            if score >= self._MIN_CANDIDATE_SCORE:
                candidates.append(
                    IntentCandidate(
                        intent=intent_name,
                        score=round(score, 4),
                        reason=reason,
                        goal=intent_data["goal"],
                        required_capability=intent_data["capability"],
                        execution_mode=intent_data["execution_mode"],
                    )
                )

        # Apply context boosting as a second pass
        if context:
            candidates = self._apply_context_boost(candidates, context)

        # Disambiguation: break ties between semantically opposite intents
        candidates = self._disambiguate(candidates, raw_tokens)

        # Sort by score descending
        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates

    # ── Scoring ─────────────────────────────────────────────────────

    def _score_intent(
        self,
        input_tokens: list[str],
        input_bigrams: set[tuple[str, str]],
        intent_name: str,
        context: dict | None,
        use_raw_fallback: bool = False,
    ) -> tuple[float, str]:
        """Compute a composite semantic score for a single intent.

        Returns ``(score, reason)`` where *reason* is a human-readable
        string describing the strongest signal.
        """
        desc_token_lists = self._intent_tokens[intent_name]
        trig_token_lists = self._trigger_tokens[intent_name]
        desc_bigrams = self._bigram_cache[intent_name]

        # ── 1. Description token overlap (best match) ───────────────
        best_desc_token_score = 0.0
        best_desc_idx = 0
        for idx, desc_tokens in enumerate(desc_token_lists):
            s = word_overlap_score(input_tokens, desc_tokens)
            if s > best_desc_token_score:
                best_desc_token_score = s
                best_desc_idx = idx

        # ── 2. Bigram overlap (best match) ──────────────────────────
        best_bigram_score = 0.0
        for bg_set in desc_bigrams:
            if not bg_set or not input_bigrams:
                continue
            s = ngram_overlap(list(input_tokens), list(input_tokens), 2)
            # Compare input bigrams against description bigrams directly
            intersection = input_bigrams & bg_set
            union = input_bigrams | bg_set
            s = len(intersection) / len(union) if union else 0.0
            if s > best_bigram_score:
                best_bigram_score = s

        # ── 3. Trigger phrase matching ──────────────────────────────
        best_trigger_score = 0.0
        best_trigger_idx = 0
        trig_lists = trig_token_lists
        if use_raw_fallback:
            trig_lists = self._trigger_raw_tokens.get(intent_name, trig_token_lists)
        for idx, trig_tokens in enumerate(trig_lists):
            if not trig_tokens:
                continue
            # Exact trigger phrase match gives a large bonus
            trigger_text = " ".join(trig_tokens)
            input_text = " ".join(input_tokens)
            if trigger_text in input_text:
                best_trigger_score = 1.0
                best_trigger_idx = idx
                break
            # Otherwise use weighted token overlap where trigger tokens
            # are treated as the reference and input tokens as query
            s = weighted_token_score(input_tokens, trig_tokens)
            if s > best_trigger_score:
                best_trigger_score = s
                best_trigger_idx = idx

        # ── 4. Full-text semantic similarity (best description) ──────
        best_desc_text_score = 0.0
        for desc_tokens in desc_token_lists:
            # Build a pseudo-text from the description tokens for
            # the weighted scoring
            s = weighted_token_score(input_tokens, desc_tokens)
            if s > best_desc_text_score:
                best_desc_text_score = s

        # ── Combine ─────────────────────────────────────────────────
        raw_score = (
            self._W_TOKEN_OVERLAP * best_desc_token_score
            + self._W_BIGRAM_OVERLAP * best_bigram_score
            + self._W_TRIGGER_PHRASE * best_trigger_score
            + self._W_DESCRIPTION_BEST * best_desc_text_score
        )

        # Determine the strongest signal for the reason string
        signals = {
            "description overlap": best_desc_token_score,
            "bigram similarity": best_bigram_score,
            "trigger phrase": best_trigger_score,
            "description match": best_desc_text_score,
        }
        strongest = max(signals, key=signals.get)  # type: ignore[arg-type]

        # Bonus: if the input is very short and a trigger matched exactly,
        # give a confidence bump (short inputs are typically very targeted).
        if len(input_tokens) <= 4 and best_trigger_score >= 0.8:
            raw_score = min(raw_score * 1.25, 1.0)
            strongest = "exact trigger (short input)"

        reason = f"{strongest} (token={best_desc_token_score:.2f}, "
        reason += f"bigram={best_bigram_score:.2f}, "
        reason += f"trigger={best_trigger_score:.2f}, "
        reason += f"desc={best_desc_text_score:.2f})"

        return raw_score, reason

    # ── Context Boosting ────────────────────────────────────────────

    def _apply_context_boost(
        self,
        candidates: list[IntentCandidate],
        context: dict,
    ) -> list[IntentCandidate]:
        """Boost candidate scores when they follow naturally from context.

        *context* should contain at least ``"previous_intent"`` with the
        intent string from the last turn.
        """
        previous_intent = context.get("previous_intent", "")
        if not previous_intent:
            return candidates

        follow_ups = CONTEXT_FOLLOW_UPS.get(previous_intent, {})
        if not follow_ups:
            return candidates

        for candidate in candidates:
            boost = follow_ups.get(candidate.intent, 0.0)
            if boost > 0:
                candidate.score = round(
                    min(candidate.score + boost, 1.0), 4
                )
                candidate.reason += f" [context boost +{boost:.2f} from {previous_intent}]"

        return candidates

    def _disambiguate(
        self,
        candidates: list[IntentCandidate],
        raw_tokens: list[str],
    ) -> list[IntentCandidate]:
        """Break ties between semantically opposite intents.

        When two intents have very similar scores, use signal words in the
        raw input to pick the more appropriate one.
        """
        if len(candidates) < 2:
            return candidates

        token_set = set(raw_tokens)

        # Build lookup by intent name
        by_name = {c.intent: c for c in candidates}

        # Check all close-scoring pairs for known disambiguation rules
        for i, c1 in enumerate(candidates):
            for c2 in candidates[i + 1:]:
                gap = abs(c1.score - c2.score)
                if gap > 0.05:
                    continue
                pair = frozenset([c1.intent, c2.intent])

                # SAVE_MEMORY vs RECALL_MEMORY
                if pair == frozenset(["SAVE_MEMORY", "RECALL_MEMORY"]):
                    save_c = by_name["SAVE_MEMORY"]
                    recall_c = by_name["RECALL_MEMORY"]
                    if token_set & {"is", "are", "was", "were"}:
                        # Statement: "my name is X" → save
                        if recall_c.score >= save_c.score:
                            recall_c.score = round(save_c.score - 0.02, 4)
                    elif token_set & {"this", "these", "it"}:
                        # Imperative: "remember this", "note this" → save
                        if recall_c.score >= save_c.score:
                            recall_c.score = round(save_c.score - 0.02, 4)
                    elif token_set & {"know", "what", "do", "did"}:
                        # Question: "do you know my name" → recall
                        if save_c.score >= recall_c.score:
                            save_c.score = round(recall_c.score - 0.02, 4)

                # RANDOM_FACT vs RECALL_MEMORY
                if pair == frozenset(["RANDOM_FACT", "RECALL_MEMORY"]):
                    random_c = by_name["RANDOM_FACT"]
                    recall_c = by_name["RECALL_MEMORY"]
                    personal_words = {"name", "age", "birthday", "favorite", "email", "address", "phone"}
                    if token_set & personal_words:
                        # Personal knowledge query → recall
                        if random_c.score >= recall_c.score:
                            random_c.score = round(recall_c.score - 0.02, 4)

                # SAVE_MEMORY vs IP_LOOKUP: "my X is Y" → save (personal info)
                if pair == frozenset(["SAVE_MEMORY", "IP_LOOKUP"]):
                    save_c = by_name["SAVE_MEMORY"]
                    ip_c = by_name["IP_LOOKUP"]
                    if token_set & {"is", "are", "was", "were"}:
                        # Statement with "is" → save personal info
                        if ip_c.score >= save_c.score:
                            ip_c.score = round(save_c.score - 0.02, 4)

        return candidates

    # ── Goal Detection ──────────────────────────────────────────────

    def _detect_goal(self, input_tokens: list[str]) -> GoalCategory:
        """Heuristic detection of the underlying goal from content tokens.

        This is a lightweight fallback when the top intent's goal may not
        be the best match.  It examines high-value content tokens and maps
        them to broad goal categories.
        """
        # Token -> goal mapping for common domain words
        GOAL_SIGNALS: dict[str, GoalCategory] = {
            # Entertainment
            "music": GoalCategory.ENTERTAINMENT,
            "song": GoalCategory.ENTERTAINMENT,
            "video": GoalCategory.ENTERTAINMENT,
            "movie": GoalCategory.ENTERTAINMENT,
            "play": GoalCategory.ENTERTAINMENT,
            "watch": GoalCategory.ENTERTAINMENT,
            "listen": GoalCategory.ENTERTAINMENT,
            "joke": GoalCategory.ENTERTAINMENT,
            "fun": GoalCategory.ENTERTAINMENT,
            "game": GoalCategory.ENTERTAINMENT,
            "youtube": GoalCategory.ENTERTAINMENT,
            "spotify": GoalCategory.ENTERTAINMENT,
            "quote": GoalCategory.ENTERTAINMENT,
            # Productivity
            "todo": GoalCategory.PRODUCTIVITY,
            "task": GoalCategory.PRODUCTIVITY,
            "note": GoalCategory.PRODUCTIVITY,
            "reminder": GoalCategory.PRODUCTIVITY,
            "schedule": GoalCategory.PRODUCTIVITY,
            "meeting": GoalCategory.PRODUCTIVITY,
            "file": GoalCategory.PRODUCTIVITY,
            "folder": GoalCategory.PRODUCTIVITY,
            "document": GoalCategory.PRODUCTIVITY,
            "remember": GoalCategory.PRODUCTIVITY,
            # Information
            "search": GoalCategory.INFORMATION,
            "find": GoalCategory.INFORMATION,
            "what": GoalCategory.INFORMATION,
            "weather": GoalCategory.INFORMATION,
            "news": GoalCategory.INFORMATION,
            "time": GoalCategory.INFORMATION,
            "date": GoalCategory.INFORMATION,
            "who": GoalCategory.INFORMATION,
            "where": GoalCategory.INFORMATION,
            # System
            "open": GoalCategory.SYSTEM,
            "close": GoalCategory.SYSTEM,
            "volume": GoalCategory.SYSTEM,
            "brightness": GoalCategory.SYSTEM,
            "screenshot": GoalCategory.SYSTEM,
            "shutdown": GoalCategory.SYSTEM,
            "restart": GoalCategory.SYSTEM,
            "screen": GoalCategory.SYSTEM,
            "computer": GoalCategory.SYSTEM,
            # Finance
            "stock": GoalCategory.FINANCE,
            "price": GoalCategory.FINANCE,
            "market": GoalCategory.FINANCE,
            "invest": GoalCategory.FINANCE,
            "share": GoalCategory.FINANCE,
            "money": GoalCategory.FINANCE,
            # Education
            "learn": GoalCategory.EDUCATION,
            "teach": GoalCategory.EDUCATION,
            "explain": GoalCategory.EDUCATION,
            "fact": GoalCategory.EDUCATION,
            "nasa": GoalCategory.EDUCATION,
            "space": GoalCategory.EDUCATION,
            "mars": GoalCategory.EDUCATION,
            "science": GoalCategory.EDUCATION,
        }

        goal_votes: dict[GoalCategory, int] = {}
        for token in input_tokens:
            goal = GOAL_SIGNALS.get(token)
            if goal:
                goal_votes[goal] = goal_votes.get(goal, 0) + 1

        if not goal_votes:
            return GoalCategory.UNKNOWN

        return max(goal_votes, key=goal_votes.get)  # type: ignore[arg-type]
