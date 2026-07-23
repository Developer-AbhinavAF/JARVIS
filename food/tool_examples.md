# JARVIS Tool Examples

## Application Control

### Open Applications
```python
# English
open_app("chrome")
open_app("vscode")
open_app("spotify")

# Hindi
open_app("chrome kholo")
open_app("vscode launch karo")
open_app("spotify chala do")

# Hinglish
open_app("chrome khol do")
open_app("vscode open karo")
```

### Close Applications
```python
# English
close_app("chrome")
close_app("vscode")

# Hindi
close_app("chrome band karo")
close_app("vscode close karo")

# Hinglish
close_app("chrome close kar do")
```

## Browser Operations

### Open Websites
```python
# English
open_url("youtube")
open_url("github")
open_url("chatgpt")

# Hindi
open_url("youtube kholo")
open_url("github open karo")
open_url("chatgpt launch karo")

# Hinglish
open_url("youtube khol do")
open_url("github open kar do")
```

### Search Operations
```python
# English
web_search("python tutorials")
search_youtube("believer song")
open_url("youtube", search_query="interstellar")

# Hindi
web_search("python tutorials dhundo")
search_youtube("believer song")
open_url("youtube", search_query="interstellar")

# Hinglish
web_search("python tutorials search karo")
search_youtube("believer song dhundo")
```

## Media Operations

### Play Media
```python
# English
play_media("believer")
play_media("interstellar trailer")
play_media("lofi beats")

# Hindi
play_media("believer baja do")
play_media("interstellar chalao")
play_media("lofi beats play karo")

# Hinglish
play_media("believer chala do")
play_media("interstellar trailer play karo")
```

## System Operations

### System Information
```python
# English
get_system_stats()
get_time()
get_weather("delhi")

# Hindi
get_system_stats()
get_time()
get_weather("delhi")

# Hinglish
system status batao
time batado
delhi ka weather batao
```

### System Control
```python
# English
system_sleep()
system_lock()
adjust_volume("up")
adjust_brightness("down")

# Hindi
system_sleep()
system_lock()
volume badhao
brightness kam karo

# Hinglish
system sleep karo
screen lock karo
volume up karo
brightness down karo
```

## Memory Operations

### Save Information
```python
# English
save_memory("name", "Abhinav")
save_memory("dream", "Build AGI")
save_memory("interest", "Anime")

# Hindi
save_memory("name", "Abhinav")
save_memory("dream", "AGI banana")
save_memory("interest", "Anime")

# Hinglish
mera naam Abhinav hai
mera dream hai AGI banana
mujhe Anime pasand hai
```

### Recall Information
```python
# English
recall_memory("name")
recall_memory("dream")
recall_memory("interests")

# Hindi
recall_memory("name")
recall_memory("dream")
recall_memory("interests")

# Hinglish
mera naam kya hai
meri dream kya hai
mere interests kya hain
```

## File Operations

### File Management
```python
# English
create_file("notes.txt", "Meeting notes")
read_file("notes.txt")
delete_file("old.txt")

# Hindi
create_file("notes.txt", "Meeting notes")
read_file("notes.txt")
delete_file("old.txt")

# Hinglish
notes.txt file banao
notes.txt padhao
old.txt file delete karo
```

## Desktop Control

### Keyboard & Mouse
```python
# English
type_text("hello world")
press_key("enter")
click(x=100, y=200)

# Hindi
type_text("hello world")
press_key("enter")
click(x=100, y=200)

# Hinglish
hello world type karo
enter press karo
yahan click karo
```

## Vision Operations

### Screen Analysis
```python
# English
take_screenshot()
screen_analysis()
analyze_image("screenshot.png")

# Hindi
take_screenshot()
screen_analysis()
analyze_image("screenshot.png")

# Hinglish
screenshot le lo
screen analyze karo
ye image analyze karo
```

## Complex Tool Chains

### Multi-Step Operations
```python
# Chain: Open browser → Search → Play
User: "youtube kholo, interstellar search karo, play karo"
1. open_url("youtube")
2. search_youtube("interstellar")
3. play_media(first_result)

# Chain: Open app → Type → Send
User: "open gmail, type hello, send to john"
1. open_url("gmail.com")
2. recall_memory("john's email")
3. type_text("hello")
4. press_key("enter")

# Chain: Screenshot → Analyze → Save
User: "screenshot le, analyze kar, save kar"
1. take_screenshot()
2. screen_analysis()
3. create_file("analysis.txt", analysis_result)
```

## Context-Dependent Operations

### Using Context
```python
# Context: YouTube is open
User: "search interstellar"
→ search_youtube("interstellar") [context: youtube]

# Context: Chrome is active
User: "close that tab"
→ close_active_tab() [context: current tab]

# Context: Previous result
User: "open it"
→ open_url(previous_result) [context: last result]
```

## Error Handling Examples

### Graceful Failures
```python
# App not found
User: "open nonexistentapp"
→ "I couldn't find 'nonexistentapp'. Would you like me to search for it?"

# File not found
User: "read file missing.txt"
→ "File 'missing.txt' doesn't exist. Would you like me to create it?"

# Network error
User: "search something"
→ "I'm having trouble connecting. Let me try again..."
```