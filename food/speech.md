# JARVIS Speech Engine

## Speech Architecture

### Speech Modes

### Text Mode
- User types input
- JARVIS displays text response
- JARVIS speaks response (optional)
- Primary: CLI interface

### Speech Mode
- User speaks input
- Continuous listening
- Voice activity detection
- JARVIS speaks response
- Natural conversation flow

## Text-to-Speech (TTS)

### TTS Priority
1. **Local TTS** - Fastest, no network needed
2. **ElevenLabs** - High quality, requires API
3. **pyttsx3** - Fallback, basic quality

### Local TTS
- Windows: SAPI5
- macOS: NSSpeechSynthesizer
- Linux: espeak/festival
- Always available
- Zero latency

### ElevenLabs
- API-based
- High quality voices
- Emotion control
- Requires internet
- API key needed

### TTS Features
- Voice selection
- Speed control
- Pitch adjustment
- Emotion injection
- Multi-language support

## Speech-to-Text (STT)

### STT Priority
1. **Local STT** - Whisper local
2. **Groq API** - Fast, accurate
3. **OpenAI Whisper** - High accuracy
4. **Google Speech** - Fallback

### Voice Activity Detection (VAD)
- Detect when user starts speaking
- Detect when user stops speaking
- No fixed timers
- Natural conversation flow
- Background noise filtering

### Continuous Listening
- Always listening in speech mode
- Wake word detection (optional)
- Automatic activation on speech
- Smart silence detection
- Interruption handling

### STT Features
- Multi-language support
- Real-time transcription
- Punctuation insertion
- Capitalization
- Confidence scoring

## Speech Mode Workflow

### Conversation Loop
```
User speaks
    ↓
VAD detects speech start
    ↓
STT transcribes audio
    ↓
VAD detects speech end
    ↓
Process text
    ↓
Generate response
    ↓
TTS speaks response
    ↓
Resume listening
```

### Interruption Handling
- Detect user interruption
- Stop current TTS
- Process new input
- Seamless transition

### Natural Timing
- No artificial delays
- No fixed timeouts
- Respond when ready
- Natural pause detection

## Speech Configuration

### Voice Settings
```python
voice_config = {
    "provider": "local",  # local, elevenlabs, pyttsx3
    "voice": "default",
    "speed": 1.0,
    "pitch": 1.0,
    "emotion": "neutral",
    "language": "en-US"
}
```

### STT Settings
```python
stt_config = {
    "provider": "local",  # local, groq, openai, google
    "language": "en-US",
    "model": "base",
    "vad_sensitivity": 0.5,
    "continuous": True
}
```

## Multi-Language Speech

### Supported Languages
- English (en-US, en-GB)
- Hindi (hi-IN)
- Hinglish (mixed)
- Auto-detection

### Language Switching
- Detect language automatically
- Switch TTS voice
- Switch STT model
- Maintain context

## Speech Quality

### Audio Quality
- High sample rate
- Noise cancellation
- Echo suppression
- Volume normalization

### Naturalness
- Proper intonation
- Emotion in speech
- Natural pauses
- Context-aware prosody

## Speech Commands

### Voice Commands
- "Stop" - Stop speaking
- "Pause" - Pause TTS
- "Continue" - Resume TTS
- "Louder" - Increase volume
- "Softer" - Decrease volume
- "Faster" - Increase speed
- "Slower" - Decrease speed

### Wake Words (Optional)
- "Hey JARVIS"
- "OK JARVIS"
- Customizable

## Speech Privacy

### Local Processing
- Prefer local STT/TTS
- No cloud when possible
- User control over providers
- Clear indication of cloud usage

### Data Storage
- Don't store audio by default
- Optional transcription storage
- User consent required
- Easy deletion