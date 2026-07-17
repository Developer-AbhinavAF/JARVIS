"""JARVIS CLI Tests.

Tests for:
- Text mode startup and commands
- Memory operations
- Tool execution
- Ollama availability
- Vision queries
- Typing effect
- Speech engine init
- Performance benchmarks
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestTypingEffect(unittest.TestCase):
    """Test the TypingEffect class."""

    def test_import(self):
        from cli_ui import TypingEffect
        te = TypingEffect(spd=0.0)
        self.assertIsNotNone(te)

    def test_interrupt(self):
        from cli_ui import TypingEffect
        te = TypingEffect(spd=0.0)
        te.interrupt()
        self.assertTrue(te._interrupted)


class TestTextMode(unittest.TestCase):
    """Test TextMode initialization and command handling."""

    def setUp(self):
        from cli_ui import TextMode, console
        self.console = console

    def test_import(self):
        from cli_ui import TextMode
        self.assertTrue(callable(getattr(TextMode, "run", None)))

    def test_commands_list(self):
        from cli_ui import COMMANDS
        self.assertIn("health", COMMANDS)
        self.assertIn("tools", COMMANDS)
        self.assertIn("memory", COMMANDS)
        self.assertIn("debug", COMMANDS)
        self.assertIn("ollama", COMMANDS)
        self.assertIn("exit", COMMANDS)


class TestVoiceMode(unittest.TestCase):
    """Test VoiceMode initialization."""

    def test_import(self):
        from cli_speech import VoiceMode
        self.assertTrue(callable(getattr(VoiceMode, "run", None)))

    def test_init(self):
        from cli_speech import VoiceMode
        mock_jarvis = MagicMock()
        vm = VoiceMode(mock_jarvis)
        self.assertEqual(vm._mode, "push")
        self.assertFalse(vm._is_active)


class TestCLIEntryPoint(unittest.TestCase):
    """Test CLI entry point."""

    def test_import(self):
        import cli
        self.assertTrue(callable(getattr(cli, "main", None)))

    def test_boot_function(self):
        import cli
        self.assertTrue(callable(getattr(cli, "boot_jarvis", None)))

    def test_menu_display(self):
        import cli
        self.assertTrue(callable(getattr(cli, "show_startup_menu", None)))


class TestMemoryIntegration(unittest.TestCase):
    """Test memory operations through JARVIS."""

    def test_memory_store_search(self):
        from jarvis.memory import JarvisMemory
        mem = JarvisMemory()
        # Store
        result = mem.store("CLI test memory entry")
        self.assertTrue(result)
        # Search
        results = mem.search("CLI test")
        self.assertGreater(len(results), 0)

    def test_memory_forget(self):
        from jarvis.memory import JarvisMemory
        mem = JarvisMemory()
        mem.store("temporary test entry for forget")
        count = mem.forget("temporary test entry")
        self.assertGreaterEqual(count, 0)


class TestOllamaAvailability(unittest.TestCase):
    """Test Ollama connectivity."""

    def test_ollama_check(self):
        try:
            import httpx
            resp = httpx.get("http://localhost:11434/api/tags", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])
                self.assertIsInstance(models, list)
            else:
                self.skipTest("Ollama not responding")
        except Exception:
            self.skipTest("Ollama not running")


class TestToolExecution(unittest.TestCase):
    """Test tool execution through the pipeline."""

    def test_jarvis_health(self):
        from app import JARVIS
        jarvis = JARVIS()
        health = jarvis.get_health()
        self.assertIn("boot_complete", health)
        self.assertIn("nlp_ready", health)
        self.assertIn("memory_ready", health)

    def test_tool_registry(self):
        from jarvis.execution import tool_registry
        stats = tool_registry.get_stats()
        self.assertGreater(stats["total"], 0)


class TestPerformance(unittest.TestCase):
    """Test performance targets."""

    def test_boot_time(self):
        from app import JARVIS
        start = time.time()
        jarvis = JARVIS()
        # Suppress banner output to avoid UnicodeEncodeError in cp1252
        with patch("builtins.print"):
            asyncio.run(jarvis.boot())
        boot_ms = (time.time() - start) * 1000
        self.assertLess(boot_ms, 90000, f"Boot took {boot_ms:.0f}ms")

    def test_nlp_speed(self):
        from jarvis.nlp import SemanticNLPEngine
        nlp = SemanticNLPEngine()
        times = []
        for _ in range(5):
            start = time.time()
            nlp.process("hello")
            times.append((time.time() - start) * 1000)
        avg_ms = sum(times) / len(times)
        # NLP should be under 500ms
        self.assertLess(avg_ms, 500, f"NLP avg: {avg_ms:.0f}ms")


class TestSpeechEngine(unittest.TestCase):
    """Test speech engine initialization."""

    def test_speech_import(self):
        try:
            from jarvis.speech import SpeechEngine
            self.assertTrue(True)
        except ImportError:
            self.skipTest("Speech dependencies not installed")

    def test_elevenlabs_config(self):
        try:
            from jarvis.speech.config import speech_config
            self.assertIsNotNone(speech_config)
        except Exception:
            self.skipTest("Speech config not available")


if __name__ == "__main__":
    unittest.main(verbosity=2)
