"""JARVIS CLI — Speech mode.

Wraps jarvis/speech/ engine for CLI context.
Supports push-to-talk and wake-word modes.
Falls back to text mode if speech engine unavailable.
"""

from __future__ import annotations

import asyncio
import sys
import time
import threading
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from app import JARVIS

console = Console()


class VoiceMode:
    """Voice conversation mode for JARVIS CLI.

    Uses jarvis/speech/ SpeechEngine for:
    - Whisper STT (speech-to-text)
    - ElevenLabs TTS (text-to-speech)
    - WebRTC VAD (voice activity detection)

    Modes:
    - Push-to-talk: Hold Enter to speak
    - Wake word: Continuous listening for wake word
    """

    def __init__(self, jarvis: JARVIS):
        self._jarvis = jarvis
        self._engine = None
        self._tts = None
        self._stt = None
        self._is_active = False
        self._mode = "push"  # "push" or "wake"

    def _init_speech(self) -> bool:
        """Initialize speech subsystems. Returns True if successful."""
        try:
            from jarvis.speech import speech_engine
            self._engine = speech_engine
            console.print("  [green]Speech engine loaded[/green]")
            return True
        except Exception as e:
            console.print(f"  [yellow]Speech engine unavailable: {e}[/yellow]")

        # Fallback: try individual components
        try:
            from jarvis.speech.elevenlabs_provider import elevenlabs_provider
            self._tts = elevenlabs_provider
            console.print("  [green]ElevenLabs TTS loaded[/green]")
        except Exception as e:
            console.print(f"  [yellow]TTS unavailable: {e}[/yellow]")

        try:
            from jarvis.speech.speech_to_text import speech_to_text
            self._stt = speech_to_text
            console.print("  [green]Whisper STT loaded[/green]")
        except Exception as e:
            console.print(f"  [yellow]STT unavailable: {e}[/yellow]")

        return self._tts is not None or self._stt is not None

    def _speak(self, text: str):
        """Speak text via TTS."""
        if self._engine:
            try:
                self._engine.speak(text)
                return
            except Exception:
                pass
        if self._tts:
            try:
                self._tts.synthesize(text)
                return
            except Exception:
                pass
        # Fallback: just print
        console.print(f"  [JARVIS] {text}")

    def _listen_once(self) -> str | None:
        """Listen for a single utterance. Returns text or None."""
        if self._engine:
            try:
                result = self._engine.listen_once()
                if result and hasattr(result, "text"):
                    return result.text
                if isinstance(result, str):
                    return result
            except Exception:
                pass
        if self._stt:
            try:
                result = self._stt.listen_once()
                if result and hasattr(result, "text"):
                    return result.text
                if isinstance(result, str):
                    return result
            except Exception:
                pass
        return None

    def run(self):
        """Main voice loop."""
        if not self._init_speech():
            console.print("  [red]No speech engines available. Falling back to text mode.[/red]")
            from cli_ui import TextMode
            TextMode(self._jarvis).run()
            return

        console.print()
        console.print("  [bold #ff6ec7]Voice Mode Active[/bold #ff6ec7]")
        console.print("  [dim]Press Enter to speak (push-to-talk), type 'text' to switch to text mode[/dim]")
        console.print("  [dim]Type 'mode' to toggle wake-word, 'exit' to quit[/dim]\n")

        self._is_active = True

        while self._is_active:
            try:
                if self._mode == "push":
                    self._push_to_talk_loop()
                else:
                    self._wake_word_loop()
            except KeyboardInterrupt:
                console.print()
                self._shutdown()
                break

    def _push_to_talk_loop(self):
        """Push-to-talk: wait for Enter, record, process."""
        try:
            user_input = input("  [Enter to speak] > ").strip()
        except (EOFError, KeyboardInterrupt):
            self._shutdown()
            return

        if not user_input:
            # Enter pressed — listen
            console.print("  [bold #ff6ec7]Listening...[/bold #ff6ec7]")
            text = self._listen_once()
            if text:
                console.print(f"  [dim]You: {text}[/dim]")
                self._process_and_speak(text)
            else:
                console.print("  [dim]Could not understand. Try again.[/dim]")
            return

        cmd = user_input.lower()
        if cmd in ("exit", "quit", "q"):
            self._shutdown()
        elif cmd == "text":
            console.print("  [dim]Switching to text mode...[/dim]")
            from cli_ui import TextMode
            TextMode(self._jarvis).run()
        elif cmd == "mode":
            self._mode = "wake"
            console.print("  [green]Switched to wake-word mode[/green]")
        else:
            # Treat as direct input
            self._process_and_speak(user_input)

    def _wake_word_loop(self):
        """Wake-word mode: continuous listening."""
        console.print("  [dim]Listening for wake word... (say 'hello' or 'jarvis')[/dim]")
        try:
            if self._engine and hasattr(self._engine, "stt"):
                # Use the speech engine's built-in wake word detection
                result = self._engine.stt.listen_once()
                if result and hasattr(result, "text"):
                    text = result.text
                elif isinstance(result, str):
                    text = result
                else:
                    text = None

                if text and any(w in text.lower() for w in ["hello", "jarvis", "hey computer"]):
                    console.print("  [bold #ff6ec7]Yes?[/bold #ff6ec7]")
                    utterance = self._listen_once()
                    if utterance:
                        console.print(f"  [dim]You: {utterance}[/dim]")
                        self._process_and_speak(utterance)
            else:
                # Fallback: just listen once
                text = self._listen_once()
                if text:
                    console.print(f"  [dim]You: {text}[/dim]")
                    self._process_and_speak(text)
        except Exception as e:
            console.print(f"  [dim]Listening error: {e}[/dim]")

        # Check for mode switch
        try:
            cmd = input("").strip().lower()
            if cmd == "mode":
                self._mode = "push"
                console.print("  [green]Switched to push-to-talk mode[/green]")
            elif cmd in ("exit", "quit"):
                self._shutdown()
        except (EOFError, KeyboardInterrupt):
            self._shutdown()

    def _process_and_speak(self, text: str):
        """Process input through pipeline and speak response."""
        with console.status("[bold #ff6ec7]Thinking...", spinner="dots"):
            try:
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(self._jarvis.handle(text))
                loop.close()
            except Exception as e:
                console.print(f"  [red]Error: {e}[/red]")
                return

        response = result.get("response", "I couldn't process that.")
        tool = result.get("tool", "llm")
        intent = result.get("intent", "?")
        ms = result.get("total_ms", 0)

        console.print(f"  [bold white]{response}[/bold white]")
        console.print(f"  [dim][{tool} | intent={intent} | {ms:.0f}ms][/dim]")

        self._speak(response)

    def _shutdown(self):
        self._is_active = False
        console.print("\n  [dim]Shutting down voice mode...[/dim]")
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(self._jarvis.shutdown())
            loop.close()
        except Exception:
            pass
        console.print("  [green]Goodbye.[/green]\n")
