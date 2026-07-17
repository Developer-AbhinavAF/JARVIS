"""Comprehensive Speech Engine Tests.

Tests all speech subsystems:
- ElevenLabs TTS provider
- Audio player
- Stream manager (sentence buffering)
- Speech-to-text (Whisper, VAD)
- Interrupt handler
- Prosody engine
- Conversation loop
- SpeechEngine orchestrator
"""

import time
import pytest
from unittest.mock import MagicMock, patch


# ════════════════════════════════════════════════════════════════════
# FIXTURES
# ════════════════════════════════════════════════════════════════════


@pytest.fixture
def speech_config():
    from jarvis.speech.config import SpeechConfig
    return SpeechConfig()


@pytest.fixture
def tts_provider(speech_config):
    from jarvis.speech.elevenlabs_provider import ElevenLabsProvider
    return ElevenLabsProvider(config=speech_config.elevenlabs)


@pytest.fixture
def audio_player():
    from jarvis.speech.audio_player import AudioPlayer
    return AudioPlayer()


@pytest.fixture
def stream_manager():
    from jarvis.speech.stream_manager import StreamManager
    return StreamManager()


@pytest.fixture
def stt_engine():
    from jarvis.speech.speech_to_text import SpeechToText
    return SpeechToText()


@pytest.fixture
def interrupt_handler():
    from jarvis.speech.interrupt_handler import InterruptHandler
    return InterruptHandler()


@pytest.fixture
def prosody_engine():
    from jarvis.speech.prosody import ProsodyEngine
    return ProsodyEngine()


@pytest.fixture
def conversation_loop():
    from jarvis.speech.conversation_loop import ConversationLoop
    return ConversationLoop()


@pytest.fixture
def speech_engine(speech_config):
    from jarvis.speech import SpeechEngine
    return SpeechEngine(config=speech_config)


# ════════════════════════════════════════════════════════════════════
# SPEECH CONFIG TESTS
# ════════════════════════════════════════════════════════════════════


class TestSpeechConfig:
    def test_config_loads(self, speech_config):
        assert speech_config is not None

    def test_config_has_elevenlabs_section(self, speech_config):
        assert hasattr(speech_config, 'elevenlabs')
        assert speech_config.elevenlabs is not None

    def test_config_has_stt_section(self, speech_config):
        assert hasattr(speech_config, 'stt')
        assert speech_config.stt is not None

    def test_config_has_audio_section(self, speech_config):
        assert hasattr(speech_config, 'audio')
        assert speech_config.audio is not None

    def test_config_has_interrupt_setting(self, speech_config):
        assert hasattr(speech_config, 'interrupt_enabled')
        assert isinstance(speech_config.interrupt_enabled, bool)

    def test_config_has_auto_listening(self, speech_config):
        assert hasattr(speech_config, 'auto_listening')
        assert isinstance(speech_config.auto_listening, bool)

    def test_config_has_prosody_setting(self, speech_config):
        assert hasattr(speech_config, 'enable_prosody')

    def test_config_summary(self, speech_config):
        s = speech_config.summary()
        assert isinstance(s, dict)
        assert 'enabled' in s


# ════════════════════════════════════════════════════════════════════
# ELEVENLABS TTS TESTS
# ════════════════════════════════════════════════════════════════════


class TestElevenLabsTTS:
    def test_tts_instantiates(self, tts_provider):
        assert tts_provider is not None

    def test_tts_has_is_available(self, tts_provider):
        assert hasattr(tts_provider, 'is_available')
        assert isinstance(tts_provider.is_available, bool)

    def test_tts_synthesize_returns_result(self, tts_provider):
        result = tts_provider.synthesize("Hello world")
        assert hasattr(result, 'audio_data')
        assert hasattr(result, 'duration_ms')

    def test_tts_synthesize_empty_string(self, tts_provider):
        result = tts_provider.synthesize("")
        assert result.audio_data == b""

    def test_tts_synthesize_stream_returns_iterable(self, tts_provider):
        gen = tts_provider.synthesize_stream("Hello world")
        assert hasattr(gen, '__iter__') or hasattr(gen, '__next__')

    def test_tts_get_voices(self, tts_provider):
        voices = tts_provider.get_voices()
        assert isinstance(voices, list)

    def test_tts_get_account_info(self, tts_provider):
        info = tts_provider.get_account_info()
        assert info is not None

    def test_tts_get_capabilities(self, tts_provider):
        caps = tts_provider.get_capabilities()
        assert isinstance(caps, dict)

    def test_tts_get_stats(self, tts_provider):
        stats = tts_provider.get_stats()
        assert isinstance(stats, dict)
        assert 'synthesis_count' in stats


# ════════════════════════════════════════════════════════════════════
# AUDIO PLAYER TESTS
# ════════════════════════════════════════════════════════════════════


class TestAudioPlayer:
    def test_player_instantiates(self, audio_player):
        assert audio_player is not None

    def test_player_has_state(self, audio_player):
        assert hasattr(audio_player, 'state')
        assert audio_player.state is not None

    def test_player_is_idle_initially(self, audio_player):
        from jarvis.speech.audio_player import PlaybackState
        assert audio_player.state == PlaybackState.IDLE

    def test_player_has_volume_control(self, audio_player):
        assert hasattr(audio_player, 'set_volume')

    def test_player_stop_when_idle(self, audio_player):
        audio_player.stop()

    def test_player_play_bytes(self, audio_player):
        audio_player.play_bytes(b"", blocking=False)
        time.sleep(0.05)

    def test_player_has_streaming_support(self, audio_player):
        assert hasattr(audio_player, 'start_streaming')
        assert hasattr(audio_player, 'feed_chunk')
        assert hasattr(audio_player, 'stop_streaming')

    def test_player_streaming_lifecycle(self, audio_player):
        audio_player.start_streaming()
        audio_player.feed_chunk(b"")
        audio_player.stop_streaming()

    def test_player_get_stats(self, audio_player):
        stats = audio_player.get_stats()
        assert isinstance(stats, dict)
        assert 'playback_count' in stats


# ════════════════════════════════════════════════════════════════════
# STREAM MANAGER TESTS
# ════════════════════════════════════════════════════════════════════


class TestStreamManager:
    def test_manager_instantiates(self, stream_manager):
        assert stream_manager is not None

    def test_start_add_token_end(self, stream_manager):
        stream_manager.start_stream()
        seg = stream_manager.add_token("Hello", "neutral")
        seg2 = stream_manager.add_token(" world!", "neutral")
        final = stream_manager.end_stream()
        assert final is not None

    def test_segments_have_required_fields(self, stream_manager):
        stream_manager.start_stream()
        stream_manager.add_token("Hello", "happy")
        final = stream_manager.end_stream()
        if final:
            assert hasattr(final, 'text')
            assert hasattr(final, 'is_final')
            assert hasattr(final, 'emotion')

    def test_process_text_stream(self, stream_manager):
        def gen():
            for word in "Hello world this is a test.".split():
                yield word
        segments = list(stream_manager.process_text_stream(gen()))
        assert len(segments) > 0

    def test_empty_tokens(self, stream_manager):
        stream_manager.start_stream()
        final = stream_manager.end_stream()
        assert final is None

    def test_get_stats(self, stream_manager):
        stats = stream_manager.get_stats()
        assert isinstance(stats, dict)
        assert 'stream_count' in stats


# ════════════════════════════════════════════════════════════════════
# SPEECH-TO-TEXT TESTS
# ════════════════════════════════════════════════════════════════════


class TestSpeechToText:
    def test_stt_instantiates(self, stt_engine):
        assert stt_engine is not None

    def test_stt_has_listen_once(self, stt_engine):
        assert hasattr(stt_engine, 'listen_once')

    def test_stt_has_listen_continuous(self, stt_engine):
        assert hasattr(stt_engine, 'listen_continuous')

    def test_stt_has_stop_listening(self, stt_engine):
        assert hasattr(stt_engine, 'stop_listening')

    def test_stt_has_vad(self, stt_engine):
        assert hasattr(stt_engine, '_vad')

    def test_stt_listen_once_returns_result(self, stt_engine):
        result = stt_engine.listen_once(timeout=1.0)
        assert hasattr(result, 'text')
        assert hasattr(result, 'confidence')

    def test_stt_get_stats(self, stt_engine):
        stats = stt_engine.get_stats()
        assert isinstance(stats, dict)


# ════════════════════════════════════════════════════════════════════
# INTERRUPT HANDLER TESTS
# ════════════════════════════════════════════════════════════════════


class TestInterruptHandler:
    def test_handler_instantiates(self, interrupt_handler):
        assert interrupt_handler is not None

    def test_handler_has_is_interrupted(self, interrupt_handler):
        assert hasattr(interrupt_handler, 'is_interrupted')
        assert isinstance(interrupt_handler.is_interrupted, bool)

    def test_handler_not_interrupted_initially(self, interrupt_handler):
        assert interrupt_handler.is_interrupted is False

    def test_handler_has_start_monitoring(self, interrupt_handler):
        assert hasattr(interrupt_handler, 'start_monitoring')

    def test_handler_has_stop_monitoring(self, interrupt_handler):
        assert hasattr(interrupt_handler, 'stop_monitoring')

    def test_handler_has_reset(self, interrupt_handler):
        assert hasattr(interrupt_handler, 'reset')

    def test_handler_configure(self, interrupt_handler):
        cb = MagicMock()
        interrupt_handler.configure(on_interrupt=cb)
        interrupt_handler._on_interrupt = cb

    def test_handler_start_stop(self, interrupt_handler):
        interrupt_handler.start_monitoring()
        time.sleep(0.05)
        interrupt_handler.stop_monitoring()

    def test_handler_get_stats(self, interrupt_handler):
        stats = interrupt_handler.get_stats()
        assert isinstance(stats, dict)
        assert 'interrupt_count' in stats


# ════════════════════════════════════════════════════════════════════
# PROSODY ENGINE TESTS
# ════════════════════════════════════════════════════════════════════


class TestProsodyEngine:
    def test_engine_instantiates(self, prosody_engine):
        assert prosody_engine is not None

    def test_enhance_returns_string(self, prosody_engine):
        result = prosody_engine.enhance("Hello world!")
        assert isinstance(result, str)

    def test_enhance_preserves_content(self, prosody_engine):
        text = "The capital of France is Paris."
        result = prosody_engine.enhance(text)
        assert "Paris" in result
        assert "France" in result

    def test_enhance_empty_string(self, prosody_engine):
        result = prosody_engine.enhance("")
        assert result == ""

    def test_enhance_with_emotion(self, prosody_engine):
        result = prosody_engine.enhance("Great news!", emotion="excited")
        assert isinstance(result, str)

    def test_enhance_question(self, prosody_engine):
        result = prosody_engine.enhance("What time is it?")
        assert "?" in result

    def test_enhance_list(self, prosody_engine):
        result = prosody_engine.enhance("Buy milk, eggs, bread, and butter.")
        assert "milk" in result

    def test_apply_emotion_to_text(self, prosody_engine):
        result = prosody_engine.apply_emotion_to_text("Hello!", "excited")
        assert isinstance(result, str)

    def test_get_stats(self, prosody_engine):
        stats = prosody_engine.get_stats()
        assert isinstance(stats, dict)
        assert 'modification_count' in stats


# ════════════════════════════════════════════════════════════════════
# CONVERSATION LOOP TESTS
# ════════════════════════════════════════════════════════════════════


class TestConversationLoop:
    def test_loop_instantiates(self, conversation_loop):
        assert conversation_loop is not None

    def test_loop_has_state(self, conversation_loop):
        assert hasattr(conversation_loop, 'state')

    def test_loop_starts_idle(self, conversation_loop):
        from jarvis.speech.conversation_loop import ConversationState
        assert conversation_loop.state == ConversationState.IDLE

    def test_loop_has_is_running(self, conversation_loop):
        assert hasattr(conversation_loop, 'is_running')
        assert conversation_loop.is_running is False

    def test_loop_has_turns(self, conversation_loop):
        assert hasattr(conversation_loop, 'turns')
        assert isinstance(conversation_loop.turns, list)

    def test_loop_configure(self, conversation_loop):
        conversation_loop.configure(
            on_listen=lambda: "test",
            on_think=lambda x: ("response", "neutral"),
        )

    def test_loop_process_single(self, conversation_loop):
        conversation_loop.configure(
            on_listen=lambda: "hello",
            on_think=lambda x: ("hi there", "happy"),
            on_speak=lambda t, e: None,
        )
        turn = conversation_loop.process_single("hello")
        assert turn.user_input == "hello"
        assert turn.response == "hi there"

    def test_loop_get_stats(self, conversation_loop):
        stats = conversation_loop.get_stats()
        assert isinstance(stats, dict)
        assert 'state' in stats
        assert 'turn_count' in stats


# ════════════════════════════════════════════════════════════════════
# SPEECH ENGINE INTEGRATION TESTS
# ════════════════════════════════════════════════════════════════════


class TestSpeechEngine:
    def test_engine_instantiates(self, speech_engine):
        assert speech_engine is not None

    def test_engine_has_tts(self, speech_engine):
        assert hasattr(speech_engine, 'tts')
        assert speech_engine.tts is not None

    def test_engine_has_audio(self, speech_engine):
        assert hasattr(speech_engine, 'audio')
        assert speech_engine.audio is not None

    def test_engine_has_stream(self, speech_engine):
        assert hasattr(speech_engine, 'stream')
        assert speech_engine.stream is not None

    def test_engine_has_stt(self, speech_engine):
        assert hasattr(speech_engine, 'stt')
        assert speech_engine.stt is not None

    def test_engine_has_interrupts(self, speech_engine):
        assert hasattr(speech_engine, 'interrupts')
        assert speech_engine.interrupts is not None

    def test_engine_has_prosody(self, speech_engine):
        assert hasattr(speech_engine, 'prosody')
        assert speech_engine.prosody is not None

    def test_engine_has_loop(self, speech_engine):
        assert hasattr(speech_engine, 'loop')
        assert speech_engine.loop is not None

    def test_engine_is_active_initially(self, speech_engine):
        assert speech_engine.is_active is False

    def test_engine_speak(self, speech_engine):
        result = speech_engine.speak("Hello world!", blocking=False)
        assert hasattr(result, 'audio_data')

    def test_engine_speak_empty(self, speech_engine):
        result = speech_engine.speak("")
        assert result.audio_data == b""

    def test_engine_listen_once(self, speech_engine):
        result = speech_engine.listen_once(timeout=1.0)
        assert hasattr(result, 'text')
        assert hasattr(result, 'confidence')

    def test_engine_configure_nlp(self, speech_engine):
        class MockResult:
            text = "hi"
            emotion = "happy"
        class MockNLPResult:
            response_text = MockResult()
            emotion = "happy"
        speech_engine.configure_nlp(lambda x: MockNLPResult())

    def test_engine_get_capabilities(self, speech_engine):
        caps = speech_engine.get_capabilities()
        assert isinstance(caps, dict)
        assert 'tts_available' in caps
        assert 'stt_engine' in caps
        assert 'interrupt_enabled' in caps
        assert 'auto_listening' in caps

    def test_engine_get_stats(self, speech_engine):
        stats = speech_engine.get_stats()
        assert isinstance(stats, dict)
        assert 'active' in stats
        assert 'speak_count' in stats

    def test_engine_start_stop(self, speech_engine):
        speech_engine.start()
        assert speech_engine.is_active is True
        time.sleep(0.1)
        speech_engine.stop()
        assert speech_engine.is_active is False


# ════════════════════════════════════════════════════════════════════
# PIPELINE INTEGRATION TESTS
# ════════════════════════════════════════════════════════════════════


class TestSpeechNLPIntegration:
    def test_speech_to_nlp_to_speech(self, speech_engine):
        """Full pipeline: Listen → NLP → Speak."""
        from jarvis.nlp import SemanticNLPEngine
        nlp = SemanticNLPEngine()

        speech_engine.configure_nlp(nlp.process)

        turn = speech_engine.loop.process_single("what time is it")
        assert turn is not None
        assert turn.user_input == "what time is it"

    def test_speech_emotion_passthrough(self, speech_engine):
        result = speech_engine.speak(
            "I'm so excited!",
            emotion="excited",
            blocking=False,
        )
        assert result is not None
