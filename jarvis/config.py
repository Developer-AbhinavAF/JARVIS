import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(dotenv_path=None, *_args, **_kwargs) -> bool:
        if not dotenv_path:
            return False
        path = Path(dotenv_path)
        if not path.exists():
            return False
        loaded = False
        for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
                loaded = True
        return loaded

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# =============================================================================
# AI ROUTER CONFIGURATION
# All AI requests go through the built-in router with 20+ providers.
# =============================================================================
AI_BASE_URL = os.getenv("AI_BASE_URL", "http://localhost:11434/v1").rstrip("/")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_TIMEOUT = float(os.getenv("AI_TIMEOUT", "120"))
AI_MAX_RETRIES = int(os.getenv("AI_MAX_RETRIES", "3"))
AI_STREAM = os.getenv("AI_STREAM", "true").lower() == "true"

# Model defaults — the router will use its own defaults unless these are set
AI_MODEL = os.getenv("AI_DEFAULT_MODEL", "")
AI_REASONING_MODEL = os.getenv("AI_DEFAULT_REASONING_MODEL", "")
AI_VISION_MODEL = os.getenv("AI_DEFAULT_VISION_MODEL", "")
AI_IMAGE_MODEL = os.getenv("AI_DEFAULT_IMAGE_MODEL", "")
AI_AUDIO_MODEL = os.getenv("AI_DEFAULT_AUDIO_MODEL", "")
AI_EMBEDDING_MODEL = os.getenv("AI_DEFAULT_EMBEDDING_MODEL", "")
AI_RERANK_MODEL = os.getenv("AI_DEFAULT_RERANK_MODEL", "")

# Feature flags
AI_ENABLE_MEMORY = os.getenv("AI_ENABLE_MEMORY", "true").lower() == "true"
AI_ENABLE_RAG = os.getenv("AI_ENABLE_RAG", "true").lower() == "true"
AI_ENABLE_STREAMING = os.getenv("AI_ENABLE_STREAMING", "true").lower() == "true"
AI_ENABLE_TOOLS = os.getenv("AI_ENABLE_TOOLS", "true").lower() == "true"
AI_ENABLE_REASONING = os.getenv("AI_ENABLE_REASONING", "false").lower() == "true"
AI_ENABLE_MULTIMODAL = os.getenv("AI_ENABLE_MULTIMODAL", "true").lower() == "true"

# =============================================================================
# LLM SETTINGS
# =============================================================================
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.5"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "256000"))
LLM_PROMPT_MAX_CHARS = int(os.getenv("LLM_PROMPT_MAX_CHARS", "1500"))
LLM_STREAMING = os.getenv("LLM_STREAMING", "true").lower() == "true"

# =============================================================================
# TOOL API KEYS (Non-AI services)
# =============================================================================
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
NASA_API_KEY = os.getenv("NASA_API_KEY", "")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
API_NINJAS_KEY = os.getenv("API_NINJAS_KEY", "")
CALENDARIFIC_API_KEY = os.getenv("CALENDARIFIC_API_KEY", "")

# =============================================================================
# TTS/STT CONFIGURATION
# =============================================================================
TTS_ENGINE = os.getenv("TTS_ENGINE", "pyttsx3")
STT_ENGINE = os.getenv("STT_ENGINE", "whisper")

# =============================================================================
# PATHS & DIRECTORIES
# =============================================================================
JARVIS_ROOT = Path(__file__).parent.parent
DATA_DIR = JARVIS_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
CACHE_DIR = JARVIS_ROOT / "cache"
CACHE_DIR.mkdir(exist_ok=True)
MEMORY_DB_PATH = DATA_DIR / "memory.db"
CONVERSATION_DB_PATH = DATA_DIR / "conversation_memory.db"
LESSONS_DB_PATH = DATA_DIR / "lessons_learned.db"
CHROMA_DIR = DATA_DIR / "chroma"
CHROMA_DIR.mkdir(exist_ok=True)
OS_DB_PATH = DATA_DIR / "jarvis_os.db"
TOOL_ANALYTICS_DB_PATH = DATA_DIR / "tool_analytics.db"
SESSION_FILE = DATA_DIR / "sessions.json"
USER_PREFERENCES_FILE = DATA_DIR / "preferences.json"
SCREENSHOT_PATH = str(DATA_DIR / "screenshot.png")

# =============================================================================
# SYSTEM CONFIGURATION
# =============================================================================
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

CPU_ALERT_THRESHOLD = 80.0
RAM_ALERT_THRESHOLD = 85.0
DISK_ALERT_THRESHOLD = 90.0
TEMP_ALERT_THRESHOLD = 75.0

MAX_SHORT_TERM_MEMORY = 50
MAX_LONG_TERM_MEMORY = 1000
MEMORY_SIMILARITY_THRESHOLD = 0.7
MEMORY_REFLECTION_THRESHOLD = float(os.getenv("MEMORY_REFLECTION_THRESHOLD", "0.78"))
MEMORY_IMPORTANCE_THRESHOLD = float(os.getenv("MEMORY_IMPORTANCE_THRESHOLD", "0.55"))
MEMORY_SEARCH_LIMIT = int(os.getenv("MEMORY_SEARCH_LIMIT", "5"))
RAG_CONTEXT_MAX_CHARS = int(os.getenv("RAG_CONTEXT_MAX_CHARS", "800"))
RAG_MAX_RESULTS = int(os.getenv("RAG_MAX_RESULTS", "4"))
RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.05"))

SCRAPE_TIMEOUT = int(os.getenv("SCRAPE_TIMEOUT", "15"))
SCRAPE_HEADERS = {"User-Agent": os.getenv("SCRAPE_USER_AGENT", "JARVIS/2.0 local assistant")}
MAX_SNIPPET_CHARS = int(os.getenv("MAX_SNIPPET_CHARS", "1200"))
API_TIMEOUT_SECONDS = float(os.getenv("API_TIMEOUT_SECONDS", "12"))
API_CACHE_TTL_SECONDS = int(os.getenv("API_CACHE_TTL_SECONDS", "300"))
TOOL_TIMEOUT_SECONDS = float(os.getenv("TOOL_TIMEOUT_SECONDS", "20"))
TOOL_EXECUTOR_WORKERS = int(os.getenv("TOOL_EXECUTOR_WORKERS", "4"))
ENABLE_SYSTEM_TOOLS = os.getenv("ENABLE_SYSTEM_TOOLS", "true").lower() == "true"
ENABLE_NETWORK_TOOLS = os.getenv("ENABLE_NETWORK_TOOLS", "true").lower() == "true"
ENABLE_TOOL_ANALYTICS = os.getenv("ENABLE_TOOL_ANALYTICS", "true").lower() == "true"

WAKE_WORD = os.getenv("WAKE_WORD", "hello")
STT_ENERGY_THRESHOLD = int(os.getenv("STT_ENERGY_THRESHOLD", "300"))
STT_PAUSE_THRESHOLD = float(os.getenv("STT_PAUSE_THRESHOLD", "0.5"))
STT_WAKE_TIMEOUT = int(os.getenv("STT_WAKE_TIMEOUT", "5"))
STT_WAKE_PHRASE_LIMIT = int(os.getenv("STT_WAKE_PHRASE_LIMIT", "4"))
TTS_RATE = int(os.getenv("TTS_RATE", "175"))
TTS_VOLUME = float(os.getenv("TTS_VOLUME", "1.0"))
TTS_VOICE_HINT = os.getenv("TTS_VOICE_HINT", "")
MOUSE_SPEED = float(os.getenv("MOUSE_SPEED", "0.15"))
TYPING_INTERVAL = float(os.getenv("TYPING_INTERVAL", "0.01"))

DASHBOARD_UPDATE_INTERVAL = float(os.getenv("DASHBOARD_UPDATE_INTERVAL", "2"))
BATTERY_LOW_THRESHOLD = float(os.getenv("BATTERY_LOW_THRESHOLD", "20"))

ENABLE_VOICE = os.getenv("ENABLE_VOICE", "true").lower() == "true"
ENABLE_AUTOMATION = os.getenv("ENABLE_AUTOMATION", "true").lower() == "true"
ENABLE_LEARNING = os.getenv("ENABLE_LEARNING", "true").lower() == "true"
