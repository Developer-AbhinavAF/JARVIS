"""Configuration for Twilio Voice integration."""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except ImportError:
    pass

logger = logging.getLogger("jarvis.telephony.config")


@dataclass
class TelephonyConfig:
    # ── Twilio Credentials ──────────────────────────────────────────
    account_sid: str = field(
        default_factory=lambda: os.getenv("TWILIO_ACCOUNT_SID", "")
    )
    auth_token: str = field(
        default_factory=lambda: os.getenv("TWILIO_AUTH_TOKEN", "")
    )
    phone_number: str = field(
        default_factory=lambda: os.getenv("TWILIO_PHONE_NUMBER", "")
    )
    # Public URL where Twilio can reach this server (use ngrok in dev)
    webhook_url: str = field(
        default_factory=lambda: os.getenv("TWILIO_WEBHOOK", "http://localhost:8100")
    )

    # ── STT Provider ────────────────────────────────────────────────
    # Options: "twilio", "groq", "whisper", "deepgram"
    stt_provider: str = field(
        default_factory=lambda: os.getenv("WHISPER_PROVIDER", "twilio")
    )
    groq_api_key: str = field(
        default_factory=lambda: os.getenv("GROQ_API_KEY", "")
    )
    deepgram_api_key: str = field(
        default_factory=lambda: os.getenv("DEEPGRAM_API_KEY", "")
    )
    whisper_model: str = field(
        default_factory=lambda: os.getenv("WHISPER_MODEL", "whisper-1")
    )

    # ── TTS Settings ────────────────────────────────────────────────
    tts_voice: str = field(
        default_factory=lambda: os.getenv("JARVIS_SPEECH_TTS_VOICE", "en-IN-PrabhatNeural")
    )
    tts_rate: str = field(
        default_factory=lambda: os.getenv("JARVIS_SPEECH_TTS_RATE", "+0%")
    )

    # ── Server Settings ─────────────────────────────────────────────
    host: str = field(
        default_factory=lambda: os.getenv("TELEPHONY_HOST", "0.0.0.0")
    )
    port: int = field(
        default_factory=lambda: int(os.getenv("TELEPHONY_PORT", "8100"))
    )

    # ── Call Limits ─────────────────────────────────────────────────
    max_call_duration_sec: int = 3600  # 1 hour
    max_silence_sec: int = 30  # drop call after 30s silence

    # ── Transcript Storage ──────────────────────────────────────────
    transcript_dir: Path = field(
        default_factory=lambda: Path(__file__).parent.parent.parent / "convo" / "phone"
    )

    # ── Audio Settings ──────────────────────────────────────────────
    # Twilio sends mulaw 8000Hz mono. Edge-TTS produces WAV 24000Hz.
    # We convert to mulaw 8000Hz before streaming back.
    twilio_sample_rate: int = 8000
    tts_sample_rate: int = 24000

    def __post_init__(self) -> None:
        self.transcript_dir.mkdir(parents=True, exist_ok=True)
        self.validate()

    def validate(self) -> None:
        """Validate configuration and log warnings for missing values."""
        errors = []
        warnings = []

        if not self.account_sid:
            errors.append("TWILIO_ACCOUNT_SID is not set")
        elif not self.account_sid.startswith("AC"):
            warnings.append("TWILIO_ACCOUNT_SID should start with 'AC'")

        if not self.auth_token:
            errors.append("TWILIO_AUTH_TOKEN is not set")
        elif len(self.auth_token) < 10:
            warnings.append("TWILIO_AUTH_TOKEN seems too short")

        if not self.phone_number:
            errors.append("TWILIO_PHONE_NUMBER is not set")
        elif not self.phone_number.startswith("+"):
            warnings.append("TWILIO_PHONE_NUMBER should include country code (e.g., +1234567890)")

        if self.webhook_url == "http://localhost:8100":
            warnings.append("TWILIO_WEBHOOK is set to localhost - Twilio cannot reach this URL in production")

        if self.stt_provider == "groq" and not self.groq_api_key:
            errors.append("GROQ_API_KEY is required when STT provider is 'groq'")

        if self.stt_provider == "deepgram" and not self.deepgram_api_key:
            errors.append("DEEPGRAM_API_KEY is required when STT provider is 'deepgram'")

        if self.stt_provider not in ["twilio", "groq", "whisper", "deepgram"]:
            warnings.append(f"Unknown STT provider: {self.stt_provider}")

        if errors:
            logger.error("Configuration errors: %s", "; ".join(errors))
            for error in errors:
                print(f"❌ CONFIG ERROR: {error}")

        if warnings:
            for warning in warnings:
                logger.warning("Configuration warning: %s", warning)
                print(f"⚠️  CONFIG WARNING: {warning}")

    @property
    def voice_webhook_url(self) -> str:
        return f"{self.webhook_url.rstrip('/')}/voice"

    @property
    def voice_events_url(self) -> str:
        return f"{self.webhook_url.rstrip('/')}/voice/events"

    @property
    def voice_status_url(self) -> str:
        return f"{self.webhook_url.rstrip('/')}/voice/status"

    @property
    def voice_stream_url(self) -> str:
        """Get the WebSocket stream URL, ensuring proper protocol."""
        base = self.webhook_url.rstrip('/')
        # Convert HTTP to WS for WebSocket
        if base.startswith("http://"):
            return base.replace("http://", "ws://") + "/voice/stream"
        elif base.startswith("https://"):
            return base.replace("https://", "wss://") + "/voice/stream"
        elif base.startswith("ws://") or base.startswith("wss://"):
            return base + "/voice/stream"
        else:
            # Default to ws:// for local development
            return f"ws://{base}/voice/stream"

    @property
    def is_configured(self) -> bool:
        return bool(self.account_sid and self.auth_token and self.phone_number)


def validate_environment() -> dict:
    """Validate all required environment variables for the JARVIS system."""
    results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "checks": {}
    }
    
    logger.info("=== JARVIS Environment Validation ===")
    
    # Check if we can load the .env file
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        load_dotenv(env_path)
        logger.info("Loaded .env from: %s", env_path)
    except ImportError:
        logger.warning("python-dotenv not installed, using system environment only")
    except Exception as e:
        logger.warning("Failed to load .env: %s", e)

    # Twilio checks
    results["checks"]["twilio"] = {
        "account_sid": bool(telephony_config.account_sid),
        "auth_token": bool(telephony_config.auth_token),
        "phone_number": bool(telephony_config.phone_number),
        "webhook_url": telephony_config.webhook_url != "http://localhost:8100"
    }

    if not telephony_config.account_sid:
        results["errors"].append("TWILIO_ACCOUNT_SID is missing")
        results["valid"] = False
    if not telephony_config.auth_token:
        results["errors"].append("TWILIO_AUTH_TOKEN is missing")
        results["valid"] = False
    if not telephony_config.phone_number:
        results["errors"].append("TWILIO_PHONE_NUMBER is missing")
        results["valid"] = False
    if telephony_config.webhook_url == "http://localhost:8100":
        results["warnings"].append("TWILIO_WEBHOOK is localhost - Twilio cannot reach this")

    # STT provider checks
    stt_provider = telephony_config.stt_provider
    results["checks"]["stt"] = {"provider": stt_provider}

    if stt_provider == "groq":
        has_key = bool(telephony_config.groq_api_key)
        results["checks"]["stt"]["groq_api_key"] = has_key
        if not has_key:
            results["errors"].append("GROQ_API_KEY is required for Groq STT")
            results["valid"] = False
    elif stt_provider == "deepgram":
        has_key = bool(telephony_config.deepgram_api_key)
        results["checks"]["stt"]["deepgram_api_key"] = has_key
        if not has_key:
            results["errors"].append("DEEPGRAM_API_KEY is required for Deepgram STT")
            results["valid"] = False

    # LLM checks
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_ollama = bool(os.getenv("OLLAMA_HOST"))
    results["checks"]["llm"] = {
        "openai": has_openai,
        "ollama": has_ollama
    }

    if not has_openai and not has_ollama:
        results["warnings"].append("No LLM configured (OPENAI_API_KEY or OLLAMA_HOST)")

    # Log final results
    if results["valid"]:
        logger.info("✅ Environment validation passed")
    else:
        logger.error("❌ Environment validation failed with %d errors", len(results["errors"]))
    
    return results


telephony_config = TelephonyConfig()
