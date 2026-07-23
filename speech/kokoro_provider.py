# Deprecated: use generate_agi_audio.py instead
from speech.generate_agi_audio import generate_agi_audio

kokoro_provider = type("KokoroProvider", (), {
    "is_available": lambda self: __import__("speech.generate_agi_audio", fromlist=["_lazy_load"])._lazy_load(),
    "load": lambda self: __import__("speech.generate_agi_audio", fromlist=["_lazy_load"])._lazy_load(),
    "generate_audio": staticmethod(generate_agi_audio),
})()
