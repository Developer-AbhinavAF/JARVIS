"""Test speech listening with user interaction."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=== Speech Listening Test ===")
print("Please speak something when prompted...")
print("(The system will listen for 10 seconds)\n")

try:
    from interface.speech import speech_engine
    
    # Start the speech engine
    print("Starting speech engine...")
    speech_engine.start()
    
    # Test speaking first
    print("\nJARVIS says: 'Speech system is ready. Please speak now.'")
    speech_engine.speak("Speech system is ready. Please speak now.", blocking=True)
    
    # Listen for speech
    print("\nListening for 10 seconds... Please speak now!")
    result = speech_engine.listen(timeout=10.0)
    
    print(f"\nRecognized text: '{result}'")
    
    if result:
        print(f"JARVIS says: 'I heard you say: {result}'")
        speech_engine.speak(f"I heard you say: {result}", blocking=True)
    else:
        print("No speech detected. Try speaking louder or closer to the microphone.")
        speech_engine.speak("No speech detected. Please try again.", blocking=True)
    
    # Stop the speech engine
    speech_engine.stop()
    print("\nSpeech engine stopped.")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Test Complete ===")
