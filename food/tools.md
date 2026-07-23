# JARVIS Tool System

## Core Philosophy
Every tool must have real execution and real verification. No fake success messages. No placeholder implementations.

## Tool Categories

### APPLICATIONS
- open_app: Launch desktop applications
- close_app: Terminate running applications
- get_active_app: Identify currently focused window
- list_running_apps: Show all active processes

### BROWSER
- open_url: Open websites in browser
- web_search: Search Google
- search_youtube: Search YouTube specifically
- play_media: Play songs/videos on YouTube

### FILES
- create_file: Create new files with content
- read_file: Read and display file contents
- delete_file: Remove files
- list_directory: Show folder contents

### SYSTEM
- get_system_stats: CPU, RAM, battery, disk usage
- system_sleep: Put computer to sleep
- system_shutdown: Shutdown computer
- system_lock: Lock screen
- adjust_volume: Control system audio
- adjust_brightness: Control screen brightness
- get_system_info: OS, processor, hostname details

### VISION
- take_screenshot: Capture screen
- screen_analysis: OCR and AI vision analysis
- analyze_image: Process uploaded images

### MEMORY
- save_memory: Store user information
- recall_memory: Retrieve stored information
- delete_memory: Remove stored information
- search_memories: Semantic search through memories

### KNOWLEDGE
- add_knowledge: Store documents/notes
- search_knowledge: Semantic search through knowledge base
- get_knowledge: Retrieve specific knowledge entries

### DESKTOP CONTROL
- type_text: Type at cursor position
- press_key: Press keyboard combinations
- click: Mouse click at coordinates
- double_click: Double click
- right_click: Context menu click
- hover: Mouse hover

### COMMUNICATION
- send_email: Compose email
- copy_to_clipboard: Copy text
- paste_from_clipboard: Read clipboard

### UTILITY
- calculate: Mathematical calculations
- get_time: Current time
- get_date: Today's date
- get_weather: Weather information
- image_search: Google Images search

## Tool Execution Rules

1. Every tool must have execute() function
2. Every tool must have verify() function
3. Tools must return ToolResult with verification status
4. No tool should claim success without verification
5. Tools must handle errors gracefully
6. Tools must log execution time
7. Tools must be idempotent where possible

## Verification Standards

- Process running: Check process list
- File operations: Verify file existence/contents
- Network operations: Check response codes
- UI operations: Verify window states
- Media operations: Check playback status

## Tool Chaining

Tools can be chained for complex operations:
- Multi-step workflows
- Conditional execution
- Parallel execution where safe
- Error recovery between steps
- State management across chains