# JARVIS Complete Testing Guide

## 🚀 Quick Start Test

Run JARVIS and select your mode:
```powershell
cd D:\JARVIS
.\.venv\Scripts\Activate.ps1
python -m jarvis.main
```

You'll see:
```
==================================================
  JARVIS MODE SELECTOR
==================================================
  Press 'y' then Enter for VOICE mode (default)
  Press 'n' then Enter for TEXT mode
  Waiting 10 seconds...
==================================================

  Your choice (y/n):
```

- Press `y` + Enter = Voice mode (speak commands)
- Press `n` + Enter = Text mode (type commands)
- Wait 10 seconds = Defaults to voice mode

---

## 🎤 PART 1: Voice/Text Interface Tests

### Test 1.1: Basic Wake (Voice Mode)
```
Say: "hello"
Expected: JARVIS responds "Yes?"
```

### Test 1.2: Time Query
```
Say/Type: "what time is it"
Expected: Current date and time spoken/displayed
```

### Test 1.3: Stop Speaking
```
Say/Type: "stop talking" or "be quiet"
Expected: JARVIS stops current speech immediately
```

### Test 1.4: Exit
```
Say/Type: "goodbye" or "exit" or "quit"
Expected: JARVIS shuts down gracefully
```

---

## 🖱️ PART 2: Mouse & Keyboard Tests

### Test 2.1: Test Mouse
```
Say/Type: "test mouse"
Expected: Mouse moves in square pattern around screen center
          Then clicks at center
```

### Test 2.2: Test Keyboard
```
Say/Type: "test keyboard"
Expected: Notepad opens
          Types test pattern with all characters
          Shows: "Keyboard Test - JARVIS"
```

### Test 2.3: Mouse Movement
```
Say/Type: "move mouse to 500 300"
Expected: Cursor moves to coordinates (500, 300)
```

### Test 2.4: Click
```
Say/Type: "click at current position"
or: "click at 500 300"
Expected: Mouse clicks at specified position
```

### Test 2.5: Type Text
```
Say/Type: "type hello world"
Expected: Types "hello world" at cursor location
```

### Test 2.6: Hotkeys
```
Say/Type: "press ctrl c"
Expected: Copies selected text

Say/Type: "press alt tab"
Expected: Switches to next window

Say/Type: "press enter 3 times"
Expected: Presses Enter key 3 times
```

---

## 🔊 PART 3: System Control Tests

### Test 3.1: Volume Control
```
Say/Type: "volume up"
Expected: System volume increases + confirmation

Say/Type: "volume down"
Expected: Volume decreases

Say/Type: "set volume to 50"
Expected: Volume set to 50%

Say/Type: "mute volume"
Expected: System muted

Say/Type: "unmute volume"
Expected: System unmuted
```

### Test 3.2: Brightness Control
```
Say/Type: "increase brightness"
Expected: Screen brightness increases

Say/Type: "set brightness to 80"
Expected: Brightness set to 80%
```

---

## 📱 PART 4: Application Tests

### Test 4.1: Open/Close Built-in Apps
```
Say/Type: "open calculator"
Expected: Calculator opens

Say/Type: "close calculator"
Expected: Calculator closes

Say/Type: "open notepad"
Expected: Notepad opens

Say/Type: "type hello from JARVIS"
Expected: Text appears in Notepad

Say/Type: "close notepad"
Expected: Notepad closes
```

### Test 4.2: Open Chrome
```
Say/Type: "open chrome"
Expected: Google Chrome browser opens
```

### Test 4.3: Open Other Apps
```
Say/Type: "open spotify"
Expected: Spotify opens (if installed)

Say/Type: "open discord"
Expected: Discord opens (if installed)

Say/Type: "open vscode"
Expected: Visual Studio Code opens (if installed)
```

### Test 4.4: Multi-App Command
```
Say/Type: "open calculator notepad and chrome"
Expected: All 3 apps open in sequence
          "Got it. Processing 3 tasks."
          "All 3 tasks complete."
```

### Test 4.5: Close Multiple Apps
```
Say/Type: "close notepad and calculator"
Expected: Both apps close
```

---

## 🪟 PART 5: Window Management Tests

### Test 5.1: List Windows
```
Say/Type: "list windows"
or: "show active windows"
Expected: List of all open windows displayed
```

### Test 5.2: Window Control
```
Say/Type: "minimize window"
Expected: Current window minimizes

Say/Type: "maximize window"
Expected: Current window maximizes

Say/Type: "close window"
Expected: Current window closes
```

### Test 5.3: Switch Windows
```
Say/Type: "switch to chrome"
Expected: Chrome window comes to front

Say/Type: "switch window"
or: "next window"
Expected: Switches to next window (Alt+Tab)
```

---

## 🔍 PART 6: Web & Search Tests

### Test 6.1: Web Search (Built-in)
```
Say/Type: "search web for python tutorials"
Expected: Returns search results from web

Say/Type: "what is artificial intelligence"
Expected: Searches and provides answer

Say/Type: "who is Elon Musk"
Expected: Returns information about Elon Musk
```

### Test 6.2: Open Website
```
Say/Type: "open google.com"
Expected: Opens Google in default browser

Say/Type: "open youtube.com"
Expected: Opens YouTube
```

---

## 🎵 PART 7: YouTube & Media Tests

### Test 7.1: Play Music
```
Say/Type: "play song Shape of You"
Expected: Opens YouTube with Shape of You video

Say/Type: "play music Despacito"
Expected: Plays Despacito music video
```

### Test 7.2: Play Video
```
Say/Type: "play video funny cats"
Expected: Opens YouTube with funny cat videos
```

### Test 7.3: Search YouTube
```
Say/Type: "search youtube for python tutorials"
Expected: Lists top 5 YouTube results
```

---

## 🎲 PART 8: Utility & Fun Tests

### Test 8.1: Calculator
```
Say/Type: "calculate 25 * 4"
Expected: "25 * 4 = 100"

Say/Type: "what is 100 divided by 5"
Expected: Division result

Say/Type: "calculate sqrt(16)"
Expected: "sqrt(16) = 4.0"
```

### Test 8.2: Coin Flip
```
Say/Type: "flip a coin"
Expected: "Heads!" or "Tails!"
```

### Test 8.3: Dice Roll
```
Say/Type: "roll a dice"
Expected: "Rolled a 6-sided dice: 4!" (random number)

Say/Type: "roll 20 sided dice"
Expected: "Rolled a 20-sided dice: 15!"
```

### Test 8.4: Jokes
```
Say/Type: "tell me a joke"
or: "make me laugh"
Expected: Random tech joke
```

### Test 8.5: Inspirational Quotes
```
Say/Type: "give me a quote"
or: "inspire me"
Expected: Random inspirational quote
```

### Test 8.6: Timer
```
Say/Type: "set timer for 10 seconds"
Expected: "Timer set for 10 seconds."
          (Beep after 10 seconds)
```

---

## 📊 PART 9: Graphical Feature Tests (Charts)

### Test 9.1: Create Bar Chart
```
Say/Type: "plot a bar chart"
or: "create chart title Sales labels A B C D values 100 150 80 200"
Expected: Pop-up window with bar chart displayed
```

### Test 9.2: Create Pie Chart
```
Say/Type: "plot pie chart of market share"
Expected: Pie chart displayed
```

### Test 9.3: Create Line Chart
```
Say/Type: "plot line chart of monthly sales"
Expected: Line chart displayed
```

**Note:** Charts appear in separate matplotlib windows

---

## 🧠 PART 10: Memory & Task Tests

### Test 10.1: Add To-Do
```
Say/Type: "add todo buy groceries"
Expected: "Added to-do: buy groceries"

Say/Type: "add todo call mom tomorrow"
Expected: Task added
```

### Test 10.2: List To-Dos
```
Say/Type: "what's on my to-do list"
or: "show my tasks"
Expected: List of all to-do items
```

### Test 10.3: Complete Task
```
Say/Type: "complete task 1"
Expected: First task marked complete
```

### Test 10.4: Save Notes
```
Say/Type: "save note Project Ideas: Build an AI assistant with voice control"
Expected: Note saved confirmation
```

### Test 10.5: Search Notes
```
Say/Type: "search notes for project"
Expected: Shows notes matching "project"
```

### Test 10.6: Daily Briefing
```
Say/Type: "daily briefing"
or: "what do I have today"
Expected: Summary of todos, reminders, upcoming dates
```

### Test 10.7: Memory Recall
```
Say/Type: "my name is John"
(some conversation later)
Say/Type: "what did we talk about"
Expected: Recalls recent conversation including your name
```

---

## 🖥️ PART 11: System Monitoring Tests

### Test 11.1: System Status
```
Say/Type: "system status"
or: "how's my computer"
Expected: "CPU: 15%, RAM: 45%, Battery: 85%"
```

### Test 11.2: CPU Check
```
Say/Type: "check cpu usage"
Expected: Current CPU percentage
```

### Test 11.3: RAM Check
```
Say/Type: "what's my ram usage"
Expected: Current RAM usage
```

### Test 11.4: List Running Apps
```
Say/Type: "list apps"
or: "what apps are running"
Expected: List of running processes
```

### Test 11.5: Kill Process
```
Say/Type: "kill process notepad"
Expected: Notepad process terminated
```

### Test 11.6: Screenshot
```
Say/Type: "take a screenshot"
Expected: Screenshot saved to screenshots folder
          Confirmation with file path
```

---

## 🔄 PART 12: Multi-Task Tests (Advanced)

### Test 12.1: Play + Open App (The Bug You Found)
```
Say/Type: "play shape of you and open calculator"
Expected: 
  - Task 1: Plays Shape of You on YouTube
  - Task 2: Opens Calculator
  - "All 2 tasks complete."
```

### Test 12.2: Multiple Actions
```
Say/Type: "volume up then open notepad then type hello"
Expected: All 3 actions performed in sequence
```

### Test 12.3: Complex Multi-Task
```
Say/Type: "open chrome and search web for news and set volume to 50"
Expected: All 3 tasks completed
```

---

## 🔧 Troubleshooting Common Issues

### Issue: "Keyboard not working"
**Fix:**
```powershell
pip install pyautogui
```

### Issue: "Mouse control not available"
**Fix:**
```powershell
pip install pyautogui
```

### Issue: "Web search not working"
**Fix:** Check internet connection OR API keys in `config.py`

### Issue: "Chrome not opening"
**Fix:** Check if Chrome is installed at standard locations

### Issue: "LLM not responding"
**Fix:** Check Groq API key in `config.py` line 15

### Issue: "Features cut off mid-command"
**Fix:** This was the listening bug - now uses 1.2s silence detection

---

## ✅ Final Validation (5-Minute Test)

Run these 10 tests to validate everything:

1. `test keyboard` - Should open Notepad with test text
2. `open calculator` - Calculator should open
3. `move mouse to 500 300` - Cursor should move
4. `search web for news` - Should return search results
5. `play song Despacito` - YouTube should open
6. `system status` - Should report CPU/RAM
7. `flip a coin` - Should return Heads or Tails
8. `plot bar chart` - Chart window should appear
9. `add todo test JARVIS` - Should save to-do
10. `play shape of you and open chrome` - Both should work

**If all 10 pass → JARVIS is fully operational!**

---

## 🐛 Reporting Bugs

If a feature doesn't work:

1. **Check terminal output** - Shows error messages
2. **Enable debug logging** in `config.py`:
   ```python
   LOG_LEVEL = "DEBUG"
   ```
3. **Try text mode first** - Easier to debug than voice
4. **Check dependencies**:
   ```powershell
   pip list | findstr pyautogui
   pip list | findstr psutil
   ```

---

**Happy Testing! 🎉**
