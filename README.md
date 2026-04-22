# JARVIS Ultimate - Voice AI Assistant

A fully-featured, modular voice-activated AI assistant optimized for **8GB RAM Windows PCs** (Intel i5 6th Gen, Intel HD 520).

## System Requirements

- **OS**: Windows 10/11 (Linux support partial)
- **RAM**: 8GB
- **CPU**: Intel i5 6th Gen or equivalent
- **GPU**: None required (integrated graphics work fine)
- **Storage**: ~500MB for installation
- **Microphone**: Required for voice input
- **Internet**: Required for cloud LLM features

## Architecture

### Always-On Core (Lightweight)
- **Voice Interface**: Wake word detection, STT, offline TTS
- **PC Control**: Mouse, keyboard, window management
- **System Monitor**: CPU/RAM/Battery alerts
- **Smart Assistant**: Groq LLM integration with tool calling
- **Memory**: SQLite-based long-term memory

### On-Demand Plugins (Heavy Features)
- **Vision**: Webcam, QR detection, motion detection
- **OCR**: Screen reading, document parsing
- **File AI**: PDF, DOCX, Excel reading
- **Browser Agent**: Selenium automation
- **Local LLM**: Offline Phi-3/Gemma models (requires ~2-3GB RAM when loaded)

## Quick Start

### 1. Install System Dependencies (Windows)

```powershell
# Install Tesseract OCR (optional, for OCR features)
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
# Add to PATH during installation

# Install Python 3.11 if not already installed
python --version  # Should show 3.11.x
```

### 2. Create Virtual Environment

```powershell
cd D:\JARVIS
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Python Dependencies

```powershell
# Core dependencies (required)
pip install SpeechRecognition PyAudio pyttsx3 groq==0.9.0 httpx==0.27.0 requests beautifulsoup4 lxml matplotlib pandas

# System control (recommended)
pip install pyautogui keyboard pyperclip pywin32 psutil

# Optional plugins (install as needed)
pip install pytesseract Pillow opencv-python  # Vision/OCR
pip install PyPDF2 python-docx openpyxl       # File AI
pip install selenium                          # Browser automation
pip install llama-cpp-python                  # Local LLM (heavy)
```

### 4. Configure API Keys

Edit `jarvis/config.py`:

```python
GROQ_API_KEY: str = "your-groq-api-key-here"
TAVILY_API_KEY: str = "your-tavily-api-key-here"
```

**Get API Keys:**
- Groq: https://console.groq.com/keys
- Tavily: https://app.tavily.com/dashboard

### 5. Run JARVIS

```powershell
python -m jarvis.main
```

## Voice Commands

### Built-in Commands
| Command | Action |
|---------|--------|
| `hello` | Wake word (configurable in config.py) |
| `goodbye` / `shut down` / `exit` | Exit JARVIS |
| `clear memory` / `forget` | Wipe conversation history |
| `stop talking` / `be quiet` | Cancel current response |
| `daily briefing` | Get todos, reminders, upcoming dates |
| `system status` | Check CPU/RAM/battery status |

### PC Control Commands
| Say | Action |
|-----|--------|
| `move mouse to 500, 300` | Move cursor to screen position |
| `click at 500, 300` | Click at position |
| `type hello world` | Type text at cursor |
| `press ctrl c` | Execute hotkey |
| `set volume to 50` | Control system volume |
| `open notepad` / `open chrome` | Launch applications |
| `take a screenshot` | Capture screen |

### Knowledge Commands
| Say | Action |
|-----|--------|
| `what time is it` | Get current datetime |
| `search web for python tutorials` | Web search |
| `plot a bar chart of sales` | Create charts |
| `add todo buy groceries` | Add to-do item |
| `save note about project ideas` | Save a note |
| `what's my cpu usage` | System monitoring |

### Plugin Commands (Load on Demand)
| Say | Action |
|-----|--------|
| `load plugin vision` | Enable webcam features |
| `load plugin ocr` | Enable screen reading |
| `read my screen` | OCR current screen |
| `scan qr code` | Detect QR from webcam |
| `read pdf document.pdf` | Extract PDF text |

## File Structure

```
jarvis/
├── __init__.py           # Package init
├── config.py             # All settings & API keys
├── main.py               # Entry point & event loop
├── stt.py                # Speech-to-text engine
├── tts.py                # Text-to-speech engine
├── llm.py                # Groq LLM integration
├── tools.py              # Tool registry & basic tools
├── system_control.py     # Mouse/keyboard/PC control
├── dashboard.py          # System monitoring
├── memory.py             # SQLite long-term memory
└── plugins.py            # On-demand heavy features

requirements.txt          # Pinned dependencies
README.md                 # This file
```

## Configuration

Edit `jarvis/config.py` to customize:

### Wake Word
```python
WAKE_WORD: str = "hello"  # Change to "jarvis", "computer", etc.
```

### STT Sensitivity
```python
STT_ENERGY_THRESHOLD: int = 300  # Lower = more sensitive
STT_PAUSE_THRESHOLD: float = 0.8  # Seconds of silence to end phrase
```

### TTS Settings
```python
TTS_RATE: int = 175        # Speaking speed (words per minute)
TTS_VOLUME: float = 1.0    # 0.0 to 1.0
```

### Alert Thresholds
```python
CPU_ALERT_THRESHOLD: int = 90      # CPU % to trigger warning
RAM_ALERT_THRESHOLD: int = 85       # RAM % to trigger warning
BATTERY_LOW_THRESHOLD: int = 20   # Battery % to trigger warning
```

## Troubleshooting

### "LLM backend error: model_decommissioned"
- **Fix**: Update `GROQ_MODEL` in config.py to a current model
- Try: `llama-3.1-8b-instant` or `mixtral-8x7b-32768`

### Microphone not working
- Check Windows Privacy Settings → Microphone → Allow apps access
- Try different `STT_ENERGY_THRESHOLD` values (100-1000)
- Test with `python -c "import speech_recognition as sr; r = sr.Recognizer(); print('Mic OK')"`

### "Mouse control not available"
- Install pyautogui: `pip install pyautogui`
- On Linux: `sudo apt install python3-tk python3-dev`

### High CPU usage
- JARVIS wakes on every sound by default
- Increase `STT_ENERGY_THRESHOLD` to reduce false wakes
- Reduce `DASHBOARD_UPDATE_INTERVAL` (default: 5 seconds)

### TTS not speaking
- Windows: Check volume mixer for Python/pyttsx3
- Install espeak on Linux: `sudo apt install espeak`

## Security Notes

⚠️ **API Keys**: Never commit real API keys to git. Use environment variables:

```python
import os
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
```

⚠️ **PC Control**: Mouse/keyboard automation can interfere with your work:
- Always keep `pyautogui.FAILSAFE = True` (move mouse to corner to abort)
- Use with caution - JARVIS can click/type anywhere

⚠️ **Plugin Safety**: Heavy plugins (local LLM, browser automation) use significant RAM:
- Load only when needed: `load plugin vision`
- Unload when done: `unload plugin vision`
- Monitor RAM with `system status` command

## Performance Tips

1. **Keep browser tabs low** - Chrome tabs use 50-200MB each
2. **Close heavy apps** - Photoshop, VS Code, etc. compete for RAM
3. **Enable virtual memory** - Windows page file helps with 8GB
4. **Use SSD** - SQLite memory database benefits from fast disk
5. **Unload unused plugins** - Free RAM when not needed

## Extending JARVIS

### Add a New Tool

1. Create function in `tools.py` or new module:
```python
def my_tool(param: str) -> str:
    """Tool description for LLM to understand."""
    return f"Result: {param}"
```

2. Register in `TOOL_REGISTRY`:
```python
TOOL_REGISTRY["my_tool"] = my_tool
```

3. Update system prompt in `config.py` to teach LLM when to use it.

### Create a Plugin

1. Add loading logic to `plugins.py`:
```python
def _load_my_plugin(self) -> dict[str, Any] | None:
    try:
        import my_library
        return {
            "lib": my_library,
            "functions": {"do_something": lambda: "Done!"}
        }
    except ImportError:
        return None
```

2. Add to `PLUGIN_REGISTRY` for voice loading.

## License

MIT License - Build your own JARVIS!

## Credits

- Speech Recognition: Google Web Speech API (via SpeechRecognition library)
- LLM: Groq Cloud API
- TTS: pyttsx3 (offline)
- Architecture: Modular design for 8GB constraint optimization
