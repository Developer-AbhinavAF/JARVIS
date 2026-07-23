"""Generate tool embeddings for semantic tool selection."""

import json
import asyncio
from typing import Any
from core.tools import tool_registry

# Tool metadata for embedding generation
TOOL_METADATA = {
    "open_app": {
        "name": "open_app",
        "description": "Open an application by name like Chrome, VSCode, Notepad, Calculator, etc.",
        "category": "applications",
        "keywords": ["launch", "start", "run", "execute", "app", "application", "program", "software"]
    },
    "close_app": {
        "name": "close_app",
        "description": "Close an application by name",
        "category": "applications",
        "keywords": ["quit", "exit", "terminate", "kill", "close", "shutdown"]
    },
    "open_url": {
        "name": "open_url",
        "description": "Open a website URL like YouTube, GitHub, Google, Reddit, etc.",
        "category": "browser",
        "keywords": ["website", "webpage", "browse", "visit", "goto", "go to", "url", "link"]
    },
    "web_search": {
        "name": "web_search",
        "description": "Search the web for information on Google or general web search",
        "category": "search",
        "keywords": ["google", "search", "find", "look up", "query", "information", "research"]
    },
    "get_system_stats": {
        "name": "get_system_stats",
        "description": "Get CPU, RAM, disk, battery, and system stats",
        "category": "system",
        "keywords": ["cpu", "ram", "memory", "disk", "battery", "performance", "stats", "status", "health"]
    },
    "adjust_volume": {
        "name": "adjust_volume",
        "description": "Adjust system volume up/down/mute",
        "category": "system",
        "keywords": ["volume", "sound", "audio", "mute", "unmute", "loud", "quiet"]
    },
    "take_screenshot": {
        "name": "take_screenshot",
        "description": "Take a screenshot of the screen",
        "category": "vision",
        "keywords": ["screenshot", "capture", "snap", "screen", "picture", "image"]
    },
    "list_running_apps": {
        "name": "list_running_apps",
        "description": "List all running applications",
        "category": "desktop",
        "keywords": ["running", "active", "processes", "tasks", "applications", "programs"]
    },
    "get_active_app": {
        "name": "get_active_app",
        "description": "Get the currently active application",
        "category": "desktop",
        "keywords": ["active", "current", "focused", "foreground", "window"]
    },
    "get_time": {
        "name": "get_time",
        "description": "Get current time",
        "category": "utility",
        "keywords": ["time", "clock", "hour", "minute", "now"]
    },
    "get_date": {
        "name": "get_date",
        "description": "Get current date",
        "category": "utility",
        "keywords": ["date", "day", "month", "year", "calendar", "today"]
    },
    "calculate": {
        "name": "calculate",
        "description": "Perform mathematical calculation",
        "category": "utility",
        "keywords": ["math", "calculation", "compute", "add", "subtract", "multiply", "divide", "equation"]
    },
    "create_file": {
        "name": "create_file",
        "description": "Create a new file",
        "category": "files",
        "keywords": ["create", "new", "make", "write", "file", "document"]
    },
    "read_file": {
        "name": "read_file",
        "description": "Read file contents",
        "category": "files",
        "keywords": ["read", "open", "view", "file", "document", "contents"]
    },
    "delete_file": {
        "name": "delete_file",
        "description": "Delete a file",
        "category": "files",
        "keywords": ["delete", "remove", "erase", "file", "document"]
    },
    "recall_memory": {
        "name": "recall_memory",
        "description": "Recall stored memories about user preferences, information, and personal data",
        "category": "memory",
        "keywords": ["remember", "recall", "what", "name", "email", "address", "phone", "preference", "personal"]
    },
    "save_memory": {
        "name": "save_memory",
        "description": "Save something to memory for future recall",
        "category": "memory",
        "keywords": ["remember", "save", "store", "keep", "memory", "note", "preference"]
    },
    "delete_memory": {
        "name": "delete_memory",
        "description": "Delete memories by search query",
        "category": "memory",
        "keywords": ["forget", "delete", "remove", "erase", "memory"]
    },
    "show_image": {
        "name": "show_image",
        "description": "Open the last screenshot or image",
        "category": "vision",
        "keywords": ["show", "display", "open", "image", "picture", "screenshot", "photo"]
    },
    "get_system_info": {
        "name": "get_system_info",
        "description": "Get system information like OS version, machine type, processor",
        "category": "system",
        "keywords": ["system", "info", "information", "os", "operating system", "version", "processor"]
    },
    "play_media": {
        "name": "play_media",
        "description": "Play music or video media on YouTube",
        "category": "media",
        "keywords": ["play", "music", "video", "song", "audio", "youtube", "entertainment"]
    },
    "screen_analysis": {
        "name": "screen_analysis",
        "description": "Analyze the screen content using vision capabilities",
        "category": "vision",
        "keywords": ["analyze", "screen", "content", "vision", "ocr", "text", "detect"]
    },
    "adjust_brightness": {
        "name": "adjust_brightness",
        "description": "Adjust screen brightness up/down",
        "category": "system",
        "keywords": ["brightness", "screen", "display", "light", "dim", "bright"]
    },
    "ask_ai": {
        "name": "ask_ai",
        "description": "Ask an AI question for general knowledge, explanations, and information",
        "category": "utility",
        "keywords": ["ai", "question", "ask", "tell", "explain", "what", "why", "how", "knowledge"]
    },
    "image_search": {
        "name": "image_search",
        "description": "Search for images on Google Images",
        "category": "search",
        "keywords": ["image", "picture", "photo", "search", "find", "visual"]
    },
    "file_operation": {
        "name": "file_operation",
        "description": "Perform file operations (create/read/delete)",
        "category": "files",
        "keywords": ["file", "operation", "create", "read", "delete", "manage"]
    },
    "copy_to_clipboard": {
        "name": "copy_to_clipboard",
        "description": "Copy text to clipboard",
        "category": "utility",
        "keywords": ["copy", "clipboard", "paste", "text", "buffer"]
    },
    "paste_from_clipboard": {
        "name": "paste_from_clipboard",
        "description": "Paste text from clipboard",
        "category": "utility",
        "keywords": ["paste", "clipboard", "copy", "text", "buffer"]
    },
    "send_email": {
        "name": "send_email",
        "description": "Send email via default email client",
        "category": "utility",
        "keywords": ["email", "mail", "send", "message", "compose", "recipient"]
    },
    "system_sleep": {
        "name": "system_sleep",
        "description": "Put system to sleep (requires confirmation)",
        "category": "system",
        "keywords": ["sleep", "suspend", "hibernate", "power", "rest"]
    },
    "system_shutdown": {
        "name": "system_shutdown",
        "description": "Shutdown system (requires confirmation)",
        "category": "system",
        "keywords": ["shutdown", "power off", "turn off", "shut down"]
    },
    "system_lock": {
        "name": "system_lock",
        "description": "Lock system (requires confirmation)",
        "category": "system",
        "keywords": ["lock", "screen lock", "secure", "password"]
    }
}

def generate_embeddings() -> dict[str, Any]:
    """Generate embeddings for all tools using LLM."""
    embeddings = {}
    
    for tool_name, metadata in TOOL_METADATA.items():
        # Create a rich text description for embedding
        text = f"{metadata['name']}: {metadata['description']}. Keywords: {', '.join(metadata['keywords'])}. Category: {metadata['category']}"
        
        # For now, we'll use simple keyword matching as placeholder
        # In production, this would use actual embeddings from the LLM
        embeddings[tool_name] = {
            "metadata": metadata,
            "text": text,
            "keywords": metadata["keywords"],
            "category": metadata["category"]
        }
    
    return embeddings

def save_embeddings(embeddings: dict[str, Any], output_path: str = "tool_embeddings.json") -> None:
    """Save embeddings to JSON file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(embeddings, f, indent=2)
    print(f"Embeddings saved to {output_path}")

def main():
    print("Generating tool embeddings...")
    embeddings = generate_embeddings()
    save_embeddings(embeddings)
    print(f"Generated embeddings for {len(embeddings)} tools")

if __name__ == "__main__":
    main()