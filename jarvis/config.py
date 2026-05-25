"""JARVIS Configuration Module.

All configuration settings and API keys for JARVIS.
Load from .env file for sensitive keys.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# =============================================================================
# GROQ API CONFIGURATION
# =============================================================================
GROQ_API_KEYS = [
    os.getenv("GROQ_API_KEY", ""),
    os.getenv("GROQ_API_KEY2", ""),
    os.getenv("GROQ_API_KEY3", ""),
    os.getenv("GROQ_API_KEY4", ""),
]
# Filter out empty keys
GROQ_API_KEYS = [key for key in GROQ_API_KEYS if key]

# Default model - llama-3.1-8b-instant is fast and reliable
GROQ_MODEL = "llama-3.1-8b-instant"

# Alternative models
GROQ_MODELS = {
    "fast": "llama-3.1-8b-instant",
    "balanced": "llama-3.3-70b-versatile",
    "smart": "mixtral-8x7b-32768",
    "code": "deepseek-r1-distill-llama-70b",
}

# =============================================================================
# OTHER API KEYS
# =============================================================================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# =============================================================================
# NASA API
# =============================================================================
NASA_API_KEY = os.getenv("NASA_API_KEY", "")

# =============================================================================
# FINNHUB API
# =============================================================================
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

# =============================================================================
# API NINJAS
# =============================================================================
API_NINJAS_KEY = os.getenv("API_NINJAS_KEY", "")

# =============================================================================
# CALENDARIFIC API
# =============================================================================
CALENDARIFIC_API_KEY = os.getenv("CALENDARIFIC_API_KEY", "")

# =============================================================================
# TTS/STT CONFIGURATION
# =============================================================================
TTS_ENGINE = os.getenv("TTS_ENGINE", "pyttsx3")  # pyttsx3, edge-tts
STT_ENGINE = os.getenv("STT_ENGINE", "whisper")  # whisper, vosk

# =============================================================================
# PATHS & DIRECTORIES
# =============================================================================
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
MEMORY_DB_PATH = DATA_DIR / "memory.db"
SESSION_FILE = DATA_DIR / "sessions.json"
USER_PREFERENCES_FILE = DATA_DIR / "preferences.json"

# =============================================================================
# SYSTEM CONFIGURATION
# =============================================================================
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Dashboard thresholds
CPU_ALERT_THRESHOLD = 80.0
RAM_ALERT_THRESHOLD = 85.0
DISK_ALERT_THRESHOLD = 90.0
TEMP_ALERT_THRESHOLD = 75.0

# Memory settings
MAX_SHORT_TERM_MEMORY = 50
MAX_LONG_TERM_MEMORY = 1000
MEMORY_SIMILARITY_THRESHOLD = 0.7

# =============================================================================
# FEATURE FLAGS
# =============================================================================
ENABLE_VOICE = os.getenv("ENABLE_VOICE", "true").lower() == "true"
ENABLE_AUTOMATION = os.getenv("ENABLE_AUTOMATION", "true").lower() == "true"
ENABLE_LEARNING = os.getenv("ENABLE_LEARNING", "true").lower() == "true"
