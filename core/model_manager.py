"""model_manager — Model backend bootstrap and fallback chain.

Boot order when `python main.py` runs:
    1. Local Ollama (preferred) — configured via .env
    2. Cloud APIs (Groq, OpenAI, Anthropic, etc.) via AI router
    3. Legacy GPU scripts (DEPRECATED) — model/start_model.py and backups

The legacy GPU scripts (start_model.py, backup1.py, etc.) are DEPRECATED
because they relied on fragile UI automation. The system now uses proper
API integration for LLM inference.

Current model setup:
- Configure OLLAMA_MODEL_URL in .env for local models
- Configure API keys for cloud providers
- The system automatically handles fallbacks
"""

from __future__ import annotations

import os
import sys
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

GPU_SCRIPTS = [
    PROJECT_ROOT / "model" / "start_model.py",
    PROJECT_ROOT / "model" / "backup1.py",
    PROJECT_ROOT / "model" / "backup2.py",
    PROJECT_ROOT / "model" / "backup3.py",
]

SCRIPT_TIMEOUT = 300  # seconds per GPU script (Colab launch + wait)


class GPUFallbackManager:
    """Runs the model/ scripts in order; API mode after all GPU backends fail."""

    def __init__(self, scripts=None) -> None:
        self._scripts = [os.fspath(s) for s in (scripts or GPU_SCRIPTS)]
        self._launched: set = set()
        self.api_mode = False

    def _run_script(self, path: str) -> bool:
        if not os.path.exists(path):
            logger.warning("GPU script missing: %s", path)
            return False
        logger.info("Launching GPU backend: %s", os.path.basename(path))
        try:
            result = subprocess.run(
                [sys.executable, path],
                cwd=os.fspath(PROJECT_ROOT),
                timeout=SCRIPT_TIMEOUT,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                self._launched.add(os.path.basename(path))
                return True
            logger.warning("GPU script %s exited with code %d", path, result.returncode)
            return False
        except subprocess.TimeoutExpired:
            logger.error("GPU script timed out: %s", os.path.basename(path))
            return False
        except Exception as e:
            logger.error("GPU script failed to launch (%s): %s", os.path.basename(path), e)
            return False

    def boot_primary(self) -> bool:
        """Run model/start_model.py first, before the CLI interface starts."""
        self._launched.add(os.path.basename(self._scripts[0]))
        return self._run_script(self._scripts[0])

    def next_fallback(self) -> bool:
        """Run the next unused backup script; False => GPU backends exhausted."""
        if self.api_mode:
            return False
        for index in range(1, len(self._scripts)):
            name = os.path.basename(self._scripts[index])
            if name in self._launched:
                continue
            self._launched.add(name)  # attempt each backend only once
            self._run_script(self._scripts[index])
            return True
        self.api_mode = True
        logger.info("GPU backends exhausted — falling back to cloud APIs")
        return False

    def status(self) -> dict:
        return {
            "api_mode": self.api_mode,
            "launched": sorted(self._launched),
            "scripts": [os.path.basename(s) for s in self._scripts],
        }


gpu_manager = GPUFallbackManager()
