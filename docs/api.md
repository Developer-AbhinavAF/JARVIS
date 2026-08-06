# JARVIS API Documentation

## Overview

JARVIS provides a unified REST API for all interfaces. All intelligence is delegated to Jarvis Core, ensuring consistent responses across CLI, Web, and Speech interfaces.

## Base URL

```
http://localhost:8001
```

## Authentication

Currently no authentication is required. This will be added in production.

## Endpoints

### Health Check

#### GET /health

Check if the API and Jarvis Core are healthy.

**Response:**
```json
{
  "status": "healthy",
  "boot_complete": true,
  "boot_time": 2.3
}
```

### System Statistics

#### GET /stats

Get system statistics (CPU, memory, disk, network, etc.).

**Response:**
```json
{
  "cpu": {
    "usage": 25.5,
    "cores": 8
  },
  "memory": {
    "used": 8.2,
    "total": 16.0,
    "percentage": 51.2
  },
  "battery": {
    "percentage": 85,
    "isCharging": true
  },
  "disk": {
    "used": 250.5,
    "total": 500.0,
    "percentage": 50.1
  },
  "network": {
    "downloadSpeed": 1024000,
    "uploadSpeed": 512000,
    "ping": 15.5
  },
  "processes": {
    "count": 145
  },
  "uptime": 3600
}
```

#### GET /stats/core

Get Jarvis Core statistics.

**Response:**
```json
{
  "boot_complete": true,
  "boot_time": 2.3,
  "brain": {
    "total_requests": 150,
    "total_tokens": 45000,
    "personality": {
      "style": "concise",
      "formality": "professional",
      "humor": "light",
      "communication": "natural"
    },
    "available_profiles": ["FAST", "NORMAL", "WRITING", "CODING", "PROJECT"]
  },
  "memory": {
    "total_entries": 25,
    "categories": {
      "facts": 10,
      "preferences": 5,
      "goals": 3,
      "mistakes": 2,
      "conversation": 5,
      "knowledge": 0
    }
  },
  "cache": {
    "embedding": {
      "size": 45,
      "maxsize": 1000,
      "total_hits": 120,
      "hit_rate": 0.72
    },
    "food": {
      "size": 12,
      "maxsize": 500,
      "total_hits": 45,
      "hit_rate": 0.78
    },
    "memory": {
      "size": 25,
      "maxsize": 2000,
      "total_hits": 200,
      "hit_rate": 0.88
    },
    "conversation": {
      "size": 5,
      "maxsize": 100,
      "total_hits": 50,
      "hit_rate": 0.90
    },
    "prompt": {
      "size": 30,
      "maxsize": 500,
      "total_hits": 150,
      "hit_rate": 0.83
    },
    "tool": {
      "size": 15,
      "maxsize": 200,
      "total_hits": 80,
      "hit_rate": 0.84
    },
    "context": {
      "size": 8,
      "maxsize": 300,
      "total_hits": 60,
      "hit_rate": 0.86
    }
  },
  "context": {
    "history_size": 10,
    "entities_count": 5
  }
}
```

### Process Input

#### POST /process

Process user input through Jarvis Core.

**Request Body:**
```json
{
  "input": "Hello, JARVIS",
  "context": {
    "current_app": "chrome",
    "current_website": "https://github.com"
  },
  "profile_hint": "NORMAL"
}
```

**Parameters:**
- `input` (string, required): User input to process
- `context` (object, optional): Additional context
- `profile_hint` (string, optional): Profile hint (FAST, NORMAL, WRITING, CODING, PROJECT)

**Response:**
```json
{
  "text": "Hello! How can I help you today?",
  "success": true,
  "tool": null,
  "intent": "greeting",
  "intent_confidence": 0.95,
  "profile": "FAST",
  "provider": "ollama",
  "model": "qwen3:1.7b-q4_k_m",
  "latency_ms": 150.5,
  "context": {
    "session": {
      "current_browser": "",
      "current_website": "",
      "current_folder": "",
      "current_app": "",
      "current_window": "",
      "current_tab": "",
      "current_selection": "",
      "current_clipboard": "",
      "current_screenshot": "",
      "current_file": "",
      "current_camera_frame": "",
      "current_mouse_position": "",
      "last_tool": "",
      "last_entity": "",
      "last_person": "",
      "last_command": "",
      "last_user_request": "Hello, JARVIS",
      "conversation_topic": ""
    },
    "last_query": "Hello, JARVIS",
    "last_intent": "greeting",
    "last_tool": "",
    "browser_tabs": [],
    "entities": {},
    "current_task": "",
    "timestamp": 1698765432.123
  },
  "error": ""
}
```

### Stream Process

#### GET /process/stream

Process user input with streaming response.

**Query Parameters:**
- `input` (string, required): User input to process
- `context` (string, optional): JSON string of context
- `profile_hint` (string, optional): Profile hint

**Response:**
Server-Sent Events (SSE) stream:

```
data: H
data: e
data: l
data: l
data: o
data: !
```

### WebSocket

#### WS /ws

WebSocket endpoint for real-time communication.

**Client Message:**
```json
{
  "input": "Open YouTube",
  "context": {
    "current_app": "chrome"
  },
  "profile_hint": "FAST"
}
```

**Server Response:**
```json
{
  "text": "Opening YouTube...",
  "success": true,
  "tool": "open_url",
  "intent": "open_website",
  "intent_confidence": 0.98,
  "profile": "FAST",
  "provider": "ollama",
  "model": "qwen3:1.7b-q4_k_m",
  "latency_ms": 120.3,
  "context": {...},
  "error": ""
}
```

### Context

#### GET /context

Get current context from Jarvis Core.

**Response:**
```json
{
  "session": {
    "current_browser": "chrome",
    "current_website": "https://github.com",
    "current_folder": "/home/user/projects",
    "current_app": "vscode",
    "current_window": "JARVIS",
    "current_tab": "README.md",
    "current_selection": "Hello World",
    "current_clipboard": "Hello World",
    "current_screenshot": "",
    "current_file": "/home/user/projects/README.md",
    "current_camera_frame": "",
    "current_mouse_position": "100,200",
    "last_tool": "read_file",
    "last_entity": "README.md",
    "last_person": "",
    "last_command": "read file",
    "last_user_request": "Read the README",
    "conversation_topic": "Project documentation"
  },
  "last_query": "Read the README",
  "last_intent": "read_file",
  "last_tool": "read_file",
  "browser_tabs": ["https://github.com", "https://youtube.com"],
  "entities": {
    "README.md": {
      "type": "file",
      "mentions": 3,
      "last_mentioned": 1698765432.123
    },
    "chrome": {
      "type": "app",
      "mentions": 5,
      "last_mentioned": 1698765430.456
    }
  },
  "current_task": "Document project setup",
  "timestamp": 1698765432.123
}
```

#### DELETE /context

Clear conversation context in Jarvis Core.

**Response:**
```json
{
  "status": "cleared"
}
```

### Memory

#### GET /memory

Get memory statistics from Jarvis Core.

**Response:**
```json
{
  "total_entries": 25,
  "categories": {
    "facts": 10,
    "preferences": 5,
    "goals": 3,
    "mistakes": 2,
    "conversation": 5,
    "knowledge": 0
  }
}
```

### Conversation

#### GET /conversation

Get conversation history from Jarvis Core.

**Query Parameters:**
- `limit` (integer, optional): Number of recent messages (default: 10)

**Response:**
```json
[
  {
    "role": "user",
    "content": "Hello, JARVIS",
    "timestamp": 1698765430.123
  },
  {
    "role": "assistant",
    "content": "Hello! How can I help you today?",
    "timestamp": 1698765430.456
  }
]
```

### Tools

#### GET /tools

Get available tools from Jarvis Core.

**Response:**
```json
{
  "tools": [
    {
      "name": "open_app",
      "description": "Open an application",
      "category": "applications",
      "arguments": {
        "app_name": "Name of the application to open"
      },
      "example": "open_app(app_name='chrome')",
      "risk": "low",
      "verify": "Check if process is running",
      "aliases": ["launch", "start"],
      "requires_confirmation": false
    },
    {
      "name": "open_url",
      "description": "Open a URL in the default browser",
      "category": "browser",
      "arguments": {
        "url": "URL to open",
        "search_query": "Optional search query"
      },
      "example": "open_url(url='https://youtube.com')",
      "risk": "low",
      "verify": "Check if browser opened",
      "aliases": ["browse", "visit"],
      "requires_confirmation": false
    }
  ],
  "count": 15
}
```

### Logs

#### GET /logs

Get recent logs.

**Response:**
```json
{
  "logs": [
    {
      "timestamp": "2024-01-15T10:30:00.123",
      "level": "INFO",
      "logger": "jarvis.core",
      "message": "Booting JarvisCore...",
      "raw_message": "Booting JarvisCore..."
    },
    {
      "timestamp": "2024-01-15T10:30:02.456",
      "level": "INFO",
      "logger": "jarvis.core",
      "message": "JarvisCore booted successfully",
      "raw_message": "JarvisCore booted successfully"
    }
  ]
}
```

#### WS /ws/logs

WebSocket endpoint for log streaming.

**Server Message:**
```json
{
  "type": "log",
  "data": {
    "timestamp": "2024-01-15T10:30:05.789",
    "level": "INFO",
    "logger": "jarvis.core",
    "message": "Processing user input",
    "raw_message": "Processing user input"
  }
}
```

## Error Responses

All endpoints may return error responses:

```json
{
  "error": "Error message",
  "detail": "Detailed error information"
}
```

## Rate Limiting

Currently no rate limiting is implemented. This will be added in production.

## CORS

CORS is enabled for all origins. This will be restricted in production.

## WebSocket Connection

### WebSocket URL

```
ws://localhost:8001/ws
```

### Connection Example (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8001/ws');

ws.onopen = () => {
  console.log('Connected to JARVIS WebSocket');
  
  // Send message
  ws.send(JSON.stringify({
    input: "Hello, JARVIS",
    context: {},
    profile_hint: "NORMAL"
  }));
};

ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  console.log('Response:', response.text);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('WebSocket disconnected');
};
```

### Connection Example (Python)

```python
import asyncio
import websockets
import json

async def connect():
    uri = "ws://localhost:8001/ws"
    async with websockets.connect(uri) as websocket:
        # Send message
        message = {
            "input": "Hello, JARVIS",
            "context": {},
            "profile_hint": "NORMAL"
        }
        await websocket.send(json.dumps(message))
        
        # Receive response
        response = await websocket.recv()
        data = json.loads(response)
        print(f"Response: {data['text']}")

asyncio.run(connect())
```

## SSE Streaming Example

### JavaScript

```javascript
const eventSource = new EventSource('http://localhost:8001/process/stream?input=Hello');

eventSource.onmessage = (event) => {
  const token = event.data;
  process.stdout.write(token);
};

eventSource.onerror = (error) => {
  console.error('SSE error:', error);
  eventSource.close();
};
```

### Python

```python
import requests
import json

response = requests.get(
    'http://localhost:8001/process/stream',
    params={'input': 'Hello'},
    stream=True
)

for line in response.iter_lines():
    if line:
        data = line.decode('utf-8')
        if data.startswith('data: '):
            token = data[6:]  # Remove 'data: ' prefix
            print(token, end='', flush=True)
```

## Testing

### cURL Examples

#### Health Check
```bash
curl http://localhost:8001/health
```

#### Process Input
```bash
curl -X POST http://localhost:8001/process \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello, JARVIS"}'
```

#### Get Context
```bash
curl http://localhost:8001/context
```

#### Get Tools
```bash
curl http://localhost:8001/tools
```

#### Stream Process
```bash
curl "http://localhost:8001/process/stream?input=Hello"
```

## Performance

- Health check: <10ms
- System stats: <50ms
- Core stats: <20ms
- Process (FAST profile): 100-200ms
- Process (NORMAL profile): 500-1000ms
- Process (WRITING profile): 1-2s
- Process (CODING profile): 2-5s
- Process (PROJECT profile): 5-10s
- Context retrieval: <10ms
- Memory stats: <20ms
- Tools list: <10ms

## Versioning

Current API version: 2.0.0

Version history:
- 2.0.0 - Unified Jarvis Core API
- 1.0.0 - Initial API (deprecated)

## Deprecation

The old API (v1.0.0) is deprecated and will be removed in future releases. All interfaces should migrate to the new unified API.
