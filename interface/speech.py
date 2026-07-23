"""Wrapper to point to the new VeenaTTS speech stack in speech/"""
from speech.speech_engine import speech_engine

# For backwards compatibility with any code doing `from interface.speech import SpeechEngine`
# We map it to the new engine class.
class SpeechEngine:
    def __init__(self):
        self._engine = speech_engine
        
    def is_available(self):
        return self._engine.is_available()
        
    def speak(self, text, blocking=True):
        return self._engine.speak(text, blocking=blocking)
        
    def speak_async(self, text):
        return self._engine.speak_async(text)
        
    def listen(self, timeout=5.0):
        return self._engine.listen(timeout=timeout)
