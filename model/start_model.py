"""DEPRECATED: model/start_model.py — Legacy GPU model startup script.

This script was used to automate Google Colab startup for cloud GPU access.
It is now DEPRECATED because:

1. It relied on hardcoded mouse coordinates and Chrome paths
2. It was fragile and unreliable
3. JARVIS now uses proper Ollama/local LLM integration
4. Cloud API fallbacks are built into the system

The system now uses:
- Local Ollama for LLM inference (preferred)
- Cloud API fallbacks when local unavailable
- Proper API integration instead of UI automation

This file is kept for reference only and should not be used.
The main system will handle model startup automatically.

If you need to run a specific GPU model, configure it in .env:
- OLLAMA_MODEL_URL for local Ollama
- API keys for cloud providers (OpenAI, Anthropic, etc.)
"""

# This script is disabled. The system now handles model startup properly.
# See .env configuration and core/brain_adapter.py for model setup.