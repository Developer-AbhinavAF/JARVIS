# JARVIS Text Mode Complete Testing Guide

## 🚀 Quick Start

```powershell
cd D:\JARVIS
.\.venv\Scripts\Activate.ps1
python -m jarvis.main

# Press 'n' for TEXT MODE
```

---

## 📋 Test All Features (Copy-Paste Ready Commands)

### 1. **Basic Communication**
```
You: hello
You: how are you
You: what can you do
You: tell me about yourself
```

### 2. **System Control**
```
You: system status
You: check my computer
You: list apps
You: close notepad
You: take a screenshot
You: open chrome
You: open calculator
You: play spotify
```

### 3. **Multi-Task Commands**
```
You: open calculator and notepad
You: play shape of you and open chrome
You: close chrome and open file explorer
```

### 4. **Web & Search**
```
You: search web for python tutorials
You: what is machine learning
You: who is the president of USA
You: news about technology
```

### 5. **YouTube Control**
```
You: play song Believer
You: play video funny cats
You: play music Lo-fi beats
You: search youtube for programming tutorials
```

### 6. **Memory & Notes**
```
You: remember my name is John
You: save this in your memory: I like Python programming
You: add todo Buy groceries
You: add todo Call mom priority 5
You: what are my todos
You: export memory
```

### 7. **Utilities**
```
You: tell me a joke
You: tell me a quote
You: flip a coin
You: roll a dice
You: what time is it
You: set timer 10 seconds
```

### 8. **New Features (Just Implemented)**

#### **Email (If Configured)**
```
You: setup email test@example.com password123
You: read my emails
You: read unread emails only
You: send email to friend@example.com subject Hello body How are you
```

#### **Calendar**
```
You: what's my schedule
You: what's on my calendar today
You: schedule meeting Team Standup date 2024-01-20 time 10:00 duration 30
```

#### **Automation**
```
You: schedule task Daily Backup command backup_data daily at 02:00
You: create routine Good Morning steps open chrome,play music,check emails
You: run routine Good Morning
You: add custom command coffee time action open spotify
```

#### **Entertainment**
```
You: play spotify Bohemian Rhapsody
You: play music for happy mood
You: play music for focused mood
You: launch game minecraft
You: watch netflix
You: play podcast tech
```

#### **Communication**
```
You: send whatsapp to +919876543210 message Hello from JARVIS
You: send telegram Hello everyone
You: send discord message Hello channel general
```

#### **Multiple LLM**
```
You: use openai for next question
You: use groq for this
You: which llm providers are available
You: switch to anthropic
```

#### **GUI Launch**
```
You: open gui
You: launch graphical interface
```

### 9. **Health & Status**
```
You: check system health
You: show component status
You: daily briefing
You: what's my cpu usage
```

### 10. **Settings**
```
You: change wake word to jarvis
You: set tts rate to 200
You: export settings
You: import settings from my_settings.json
```

---

## 🧪 Test Script (Automated)

Save this as `test_text_mode.py` and run:

```python
"""Quick test script for text mode features."""

import time

test_commands = [
    # Basic
    "hello",
    "system status",
    
    # Apps
    "open calculator",
    "list apps",
    
    # Search
    "search web for python",
    
    # YouTube
    "play music lo-fi beats",
    
    # Memory
    "remember I love coding",
    "add todo Test JARVIS",
    "what are my todos",
    
    # Utilities
    "tell me a joke",
    "flip a coin",
    "what time is it",
    
    # Status
    "daily briefing",
    
    # Exit
    "exit",
]

print("="*50)
print("JARVIS Text Mode Test Script")
print("="*50)
print("\nCommands to test:\n")

for i, cmd in enumerate(test_commands, 1):
    print(f"{i:2}. {cmd}")

print("\n" + "="*50)
print("Run: python -m jarvis.main")
print("Select 'n' for text mode")
print("Then type each command above")
print("="*50)
```

---

## ✅ Expected Results

| Command | Expected Response |
|---------|-----------------|
| `hello` | Greeting message |
| `system status` | CPU, RAM, battery info |
| `open calculator` | "Opening Calculator..." |
| `list apps` | List of running apps |
| `search web for X` | Search results |
| `play song X` | Opens YouTube with song |
| `remember X` | "Note saved..." |
| `add todo X` | "Todo added..." |
| `tell me a joke` | Random joke |
| `daily briefing` | Today's todos and reminders |
| `export memory` | "Memory exported..." |

---

## 🔧 Testing Checklist

### Core Features
- [ ] Text mode starts without errors
- [ ] Commands are recognized
- [ ] Responses are displayed
- [ ] No speech output (pure text)

### System Control
- [ ] Can open apps (Chrome, Calc, Notepad)
- [ ] Can close apps
- [ ] Can list running apps
- [ ] Can take screenshots

### Search & Web
- [ ] Web search works
- [ ] YouTube search works
- [ ] YouTube playback works

### Memory
- [ ] Can save notes
- [ ] Can add todos
- [ ] Can retrieve todos
- [ ] Export works

### Multi-Task
- [ ] Multiple apps open correctly
- [ ] Mixed commands work (play + open)

### New Features
- [ ] Email reads (if configured)
- [ ] Calendar shows events (if configured)
- [ ] Entertainment commands work
- [ ] Automation commands work
- [ ] Multiple LLM fallback works

---

## 🐛 Troubleshooting

### Issue: Command not recognized
**Fix:** Speak/type clearly, check spelling

### Issue: No response
**Fix:** Check API keys in .env file

### Issue: Crashes
**Fix:** Check logs in `jarvis_log.txt`

### Issue: Features not working
**Fix:** Install missing dependencies:
```powershell
pip install groq openai anthropic spotipy twilio pystray
```

---

## 📊 Performance Testing

Test these rapidly to check responsiveness:
```
You: what time is it
You: flip a coin
You: tell me a joke
You: system status
```

Expected: Each response within 2-3 seconds

---

## 🎯 Complete Test Sequence

Run this full sequence (takes ~5 minutes):

```
1. Start JARVIS: python -m jarvis.main (select 'n')
2. hello
3. system status
4. list apps
5. open calculator
6. close calculator
7. search web for AI news
8. play music happy mood
9. remember my favorite color is blue
10. add todo Test JARVIS
11. what are my todos
12. tell me a joke
13. daily briefing
14. export memory
15. goodbye
```

---

## 📝 Reporting Issues

If something fails:
1. Check `jarvis_log.txt`
2. Note the exact command
3. Note the error message
4. Check if dependencies are installed

---

**Happy Testing!** 🎉

Run: `python -m jarvis.main` and press **'n'** for pure text mode!
