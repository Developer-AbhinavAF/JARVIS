# JARVIS Context Engine

## Context Architecture

### Context Layers
1. Immediate Context: Current conversation, last query
2. Session Context: Current session history, active tasks
3. User Context: User profile, preferences, current state
4. Environmental Context: Time, location, system state
5. Knowledge Context: Relevant knowledge from memory

### Context Resolution

### Pronoun Resolution
- "there" → Last mentioned location/website
- "that" → Last mentioned object
- "it" → Last mentioned item
- "this" → Current subject
- "he/she/they" → Last mentioned person

### Example Conversations

#### Context: YouTube
User: "youtube kholo"
JARVIS: Opens YouTube
User: "search interstellar trailer"
JARVIS: Searches on YouTube (context: YouTube)
User: "play it"
JARVIS: Plays the video (context: interstellar trailer)

#### Context: Tabs
User: "open github"
JARVIS: Opens GitHub
User: "search ollama"
JARVIS: Searches Ollama on GitHub
User: "open first repository"
JARVIS: Opens first result (context: search results)
User: "close that tab"
JARVIS: Closes GitHub tab (context: current tab)

#### Context: Applications
User: "open chrome"
JARVIS: Opens Chrome
User: "go to chatgpt"
JARVIS: Opens ChatGPT in Chrome
User: "type hello"
JARVIS: Types in active window (context: ChatGPT)
User: "press enter"
JARVIS: Presses Enter (context: ChatGPT)

## Context Management

### Context Window
- Maintain last N interactions
- Weight recent context higher
- Decay old context
- Prune irrelevant context

### Context Tracking
- Track entities mentioned
- Track active applications
- Track browser tabs
- Track file operations
- Track current task

### Context Inference
- Infer user intent from context
- Predict next likely action
- Suggest context-aware actions
- Detect context changes

## Context Persistence

### Session Context
- Save session state
- Restore on reconnect
- Maintain across reboots
- Sync sessions if needed

### Long-term Context
- Remember user patterns
- Learn from behavior
- Adapt to preferences
- Predict needs

## Context API

### Get Context
```python
context = get_context()
# Returns: {
#   "last_query": "...",
#   "last_tool": "...",
#   "active_app": "...",
#   "browser_tabs": [...],
#   "entities": {...},
#   "timestamp": "..."
# }
```

### Update Context
```python
update_context(key="active_app", value="chrome")
update_context(key="last_mentioned", value="youtube")
```

### Resolve Reference
```python
resolved = resolve_reference("that")
# Returns actual entity based on context
```

## Context-Aware Responses

### Multi-turn Conversations
- Reference previous statements
- Maintain conversation thread
- Remember decisions
- Follow up on actions

### Adaptive Behavior
- Adjust to user expertise
- Adapt to communication style
- Remember preferences
- Learn from patterns