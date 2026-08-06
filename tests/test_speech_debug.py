"""Debug speech recognition issues."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=== Speech System Debug ===\n")

# Test 1: Check speech engine availability
print("1. Testing speech engine availability...")
try:
    from interface.speech import speech_engine
    status = speech_engine.is_available()
    print(f"Speech engine status: {status}")
except Exception as e:
    print(f"Error loading speech engine: {e}")

# Test 2: Check microphone
print("\n2. Testing microphone availability...")
try:
    import pyaudio
    p = pyaudio.PyAudio()
    print(f"PyAudio version: {pyaudio.__version__}")
    print(f"Default input device: {p.get_default_input_device_info()}")
    print(f"Number of input devices: {p.get_device_count()}")
    
    # List all input devices
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            print(f"  Device {i}: {info['name']}")
    p.terminate()
except Exception as e:
    print(f"Error with microphone: {e}")

# Test 3: Check VAD
print("\n3. Testing VAD system...")
try:
    from speech.vad import vad
    print(f"VAD provider: {vad.name}")
    print(f"VAD available: {vad._provider is not None}")
except Exception as e:
    print(f"Error with VAD: {e}")

# Test 4: Check recognizer
print("\n4. Testing speech recognizer...")
try:
    from speech.recognizer import recognizer
    providers = recognizer.providers()
    print(f"Available STT providers: {providers}")
except Exception as e:
    print(f"Error with recognizer: {e}")

# Test 5: Try to start speech engine
print("\n5. Testing speech engine startup...")
try:
    from interface.speech import speech_engine
    speech_engine.start()
    print("Speech engine started successfully")
    
    # Try a quick listen with timeout
    print("Attempting to listen for 2 seconds...")
    result = speech_engine.listen(timeout=2.0)
    print(f"Listen result: '{result}'")
    
    speech_engine.stop()
    print("Speech engine stopped successfully")
except Exception as e:
    print(f"Error with speech engine: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Debug Complete ===")
