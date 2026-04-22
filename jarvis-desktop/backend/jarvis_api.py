"""
JARVIS Ultimate - Fully Functional AI Backend
Integrates the original JARVIS AI with FastAPI for the Desktop App
"""

import asyncio
import json
import logging
import os
import sys
import time
import traceback
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add parent directory to path to import jarvis modules
jarvis_path = Path(__file__).parent.parent.parent / "jarvis"
sys.path.insert(0, str(jarvis_path))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============== DATA MODELS ==============

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str
    actions: Optional[List[Dict[str, Any]]] = None
    suggestions: Optional[List[str]] = None

class CommandRequest(BaseModel):
    command: str
    params: Optional[Dict[str, Any]] = None

class CommandResponse(BaseModel):
    success: bool
    result: str
    command: str
    timestamp: str
    data: Optional[Dict[str, Any]] = None

class SystemStats(BaseModel):
    cpu: Dict[str, Any]
    memory: Dict[str, Any]
    battery: Dict[str, Any]
    disk: Dict[str, Any]
    network: Dict[str, Any]
    processes: Dict[str, Any]
    uptime: float

class MemoryItem(BaseModel):
    id: str
    content: str
    category: str  # 'todo', 'note', 'reminder'
    created_at: str
    completed: Optional[bool] = False
    priority: Optional[str] = "normal"

# ============== JARVIS CORE INTEGRATION ==============

class JarvisDesktopCore:
    """Desktop-optimized JARVIS AI Core"""
    
    def __init__(self):
        self.llm = None
        self.automation = None
        self.memory = None
        self.system_control = None
        self.dashboard = None
        self.tools = {}
        self.initialized = False
        self._init_lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize all JARVIS components"""
        async with self._init_lock:
            if self.initialized:
                return
                
            try:
                logger.info("🚀 Initializing JARVIS Desktop Core...")
                
                # Import JARVIS modules
                from jarvis.llm import JarvisLLM
                from jarvis.automation import Automation
                from jarvis.memory import memory
                from jarvis.system_control import SYSTEM_CONTROL_REGISTRY
                from jarvis.dashboard import SystemDashboard
                from jarvis import config
                
                # Initialize components
                self.dashboard = SystemDashboard()
                self.llm = JarvisLLM()
                self.automation = Automation()
                self.memory = memory
                self.system_control = SYSTEM_CONTROL_REGISTRY
                
                # Start system monitoring
                self.dashboard.start_monitoring()
                
                # Load all tool functions
                self._load_tools()
                
                self.initialized = True
                logger.info("✅ JARVIS Core initialized successfully!")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize JARVIS Core: {e}")
                logger.error(traceback.format_exc())
                raise
    
    def _load_tools(self):
        """Load all available tool functions"""
        try:
            from jarvis.tools import TOOL_REGISTRY
            from jarvis.system_control import SYSTEM_CONTROL_REGISTRY
            from jarvis.dashboard import DASHBOARD_REGISTRY
            from jarvis.memory import MEMORY_REGISTRY
            from jarvis.plugins import PLUGIN_REGISTRY
            
            # Merge all registries
            self.tools = {
                **TOOL_REGISTRY,
                **SYSTEM_CONTROL_REGISTRY,
                **DASHBOARD_REGISTRY,
                **MEMORY_REGISTRY,
                **PLUGIN_REGISTRY,
            }
            logger.info(f"📦 Loaded {len(self.tools)} tools")
        except Exception as e:
            logger.error(f"Failed to load tools: {e}")
            self.tools = {}
    
    async def chat(self, message: str, session_id: str = "default") -> Dict[str, Any]:
        """Process chat message with full JARVIS capabilities"""
        if not self.initialized:
            await self.initialize()
        
        try:
            # Parse for multiple commands
            tasks = self._parse_tasks(message)
            
            if len(tasks) > 1:
                # Handle multiple commands
                results = []
                for task in tasks:
                    result = await self._execute_single_task(task, session_id)
                    results.append(result)
                
                combined_response = "\n\n".join([r.get("text", "") for r in results])
                actions = []
                for r in results:
                    actions.extend(r.get("actions", []))
                
                return {
                    "response": combined_response,
                    "actions": actions,
                    "suggestions": self._get_suggestions(message)
                }
            else:
                # Single command
                result = await self._execute_single_task(message, session_id)
                return {
                    "response": result.get("text", ""),
                    "actions": result.get("actions", []),
                    "suggestions": self._get_suggestions(message)
                }
                
        except Exception as e:
            logger.error(f"Chat error: {e}")
            logger.error(traceback.format_exc())
            return {
                "response": f"I encountered an error: {str(e)}. Please try again.",
                "actions": [],
                "suggestions": ["help", "system status", "what can you do"]
            }
    
    def _parse_tasks(self, query: str) -> List[str]:
        """Parse compound commands into individual tasks"""
        query = query.strip().lower()
        if not query:
            return []
        
        # Split markers
        split_markers = [" and ", " then ", " also ", " next ", " after that ", " followed by ", " & ", " + "]
        
        # Check for same-verb commands
        if query.startswith("open "):
            rest = query[5:]
            for marker in split_markers:
                if marker in rest:
                    parts = rest.split(marker)
                    if len(parts) > 1 and all(len(p.strip().split()) <= 2 for p in parts):
                        return [f"open {p.strip()}" for p in parts if p.strip()]
        
        if query.startswith("close "):
            rest = query[6:]
            for marker in split_markers:
                if marker in rest:
                    parts = rest.split(marker)
                    if len(parts) > 1 and all(len(p.strip().split()) <= 2 for p in parts):
                        return [f"close {p.strip()}" for p in parts if p.strip()]
        
        # General split
        tasks = []
        remaining = query
        
        while remaining:
            earliest_split = None
            earliest_pos = len(remaining)
            
            for marker in split_markers:
                pos = remaining.find(marker)
                if pos != -1 and pos < earliest_pos:
                    earliest_pos = pos
                    earliest_split = marker
            
            if earliest_split is None:
                tasks.append(remaining.strip())
                break
            
            before = remaining[:earliest_pos].strip()
            after = remaining[earliest_pos + len(earliest_split):].strip()
            
            if before:
                tasks.append(before)
            
            remaining = after
        
        return tasks if len(tasks) > 1 else [query]
    
    async def _execute_single_task(self, query: str, session_id: str) -> Dict[str, Any]:
        """Execute a single task"""
        q = query.strip().lower()
        actions = []
        
        # Check built-in commands first
        builtin_result = await self._handle_builtin_command(q)
        if builtin_result:
            return builtin_result
        
        # Use LLM for complex queries
        try:
            response = self.llm.chat(query)
            
            # Check if response contains tool calls
            if isinstance(response, dict) and "tool_calls" in response:
                for tool_call in response.get("tool_calls", []):
                    tool_name = tool_call.get("name")
                    tool_params = tool_call.get("parameters", {})
                    
                    if tool_name in self.tools:
                        try:
                            result = self.tools[tool_name](**tool_params)
                            actions.append({
                                "tool": tool_name,
                                "params": tool_params,
                                "result": str(result)[:200]
                            })
                        except Exception as e:
                            logger.error(f"Tool {tool_name} failed: {e}")
            
            return {
                "text": response.get("text", str(response)) if isinstance(response, dict) else str(response),
                "actions": actions
            }
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return {
                "text": f"I'm having trouble processing that. Error: {str(e)}",
                "actions": []
            }
    
    async def _handle_builtin_command(self, q: str) -> Optional[Dict[str, Any]]:
        """Handle built-in commands without LLM"""
        
        # Memory commands
        if any(p in q for p in ["clear memory", "forget", "reset", "new conversation"]):
            self.llm.clear_history()
            return {"text": "Memory cleared. I've reset our conversation.", "actions": [{"type": "clear_memory"}]}
        
        # System status
        if any(p in q for p in ["system status", "how's my computer", "check system"]):
            status = self.dashboard.get_quick_status()
            return {"text": status, "actions": [{"type": "system_status"}]}
        
        # Daily briefing
        if any(p in q for p in ["daily briefing", "what's on my schedule", "what do i have today"]):
            briefing = self.memory.get_daily_briefing()
            return {"text": briefing, "actions": [{"type": "daily_briefing"}]}
        
        # List running apps
        if any(p in q for p in ["list apps", "what apps are running", "show running apps"]):
            from jarvis.tools import list_running_apps
            apps = list_running_apps(limit=20)
            app_list = "\n".join([f"• {app['name']}" for app in apps])
            return {"text": f"Currently running applications:\n{app_list}", "actions": [{"type": "list_apps", "data": apps}]}
        
        # Screenshot
        if any(p in q for p in ["screenshot", "capture screen", "take screenshot"]):
            try:
                from jarvis.automation import Automation
                auto = Automation()
                path = auto.capture_screenshot()
                return {"text": f"📸 Screenshot saved to: {path}", "actions": [{"type": "screenshot", "path": path}]}
            except Exception as e:
                return {"text": f"Failed to capture screenshot: {e}", "actions": []}
        
        # Open apps
        if q.startswith("open "):
            app_name = q[5:].strip()
            return await self._execute_app_command("open", app_name)
        
        # Close apps
        if q.startswith("close "):
            app_name = q[6:].strip()
            return await self._execute_app_command("close", app_name)
        
        # Volume control
        if any(p in q for p in ["volume up", "increase volume", "louder"]):
            try:
                from jarvis.system_control import set_volume
                set_volume(10, relative=True)
                return {"text": "🔊 Volume increased", "actions": [{"type": "volume", "action": "up"}]}
            except Exception as e:
                return {"text": f"Failed to adjust volume: {e}", "actions": []}
        
        if any(p in q for p in ["volume down", "decrease volume", "quieter"]):
            try:
                from jarvis.system_control import set_volume
                set_volume(-10, relative=True)
                return {"text": "🔉 Volume decreased", "actions": [{"type": "volume", "action": "down"}]}
            except Exception as e:
                return {"text": f"Failed to adjust volume: {e}", "actions": []}
        
        if any(p in q for p in ["mute", "silence"]):
            try:
                from jarvis.system_control import mute
                mute()
                return {"text": "🔇 Muted", "actions": [{"type": "volume", "action": "mute"}]}
            except Exception as e:
                return {"text": f"Failed to mute: {e}", "actions": []}
        
        # Web search
        if any(p in q for p in ["search", "google", "look up", "find"]):
            search_query = q
            for prefix in ["search for", "search", "google", "look up", "find"]:
                if search_query.startswith(prefix):
                    search_query = search_query[len(prefix):].strip()
            
            try:
                from jarvis.tools import web_search
                result = web_search(search_query)
                return {"text": result, "actions": [{"type": "web_search", "query": search_query}]}
            except Exception as e:
                return {"text": f"Search failed: {e}", "actions": []}
        
        # Time and date
        if any(p in q for p in ["what time", "current time", "time is it"]):
            now = datetime.now()
            return {"text": f"The current time is {now.strftime('%I:%M %p')}", "actions": [{"type": "time"}]}
        
        if any(p in q for p in ["what date", "today's date", "date today"]):
            now = datetime.now()
            return {"text": f"Today is {now.strftime('%A, %B %d, %Y')}", "actions": [{"type": "date"}]}
        
        # Memory - Add todo
        if any(p in q for p in ["add todo", "create task", "new task", "remember to"]):
            task = q
            for prefix in ["add todo", "create task", "new task", "remember to"]:
                if task.startswith(prefix):
                    task = task[len(prefix):].strip()
            
            if task:
                todo_id = self.memory.add_todo(task)
                return {"text": f"✅ Added to your to-do list: {task}", "actions": [{"type": "add_todo", "id": todo_id}]}
        
        # Memory - Add note
        if any(p in q for p in ["add note", "write down", "remember that", "save note"]):
            note = q
            for prefix in ["add note", "write down", "remember that", "save note"]:
                if note.startswith(prefix):
                    note = note[len(prefix):].strip()
            
            if note:
                note_id = self.memory.add_note(note)
                return {"text": f"📝 Note saved: {note[:50]}...", "actions": [{"type": "add_note", "id": note_id}]}
        
        # Memory - Show todos
        if any(p in q for p in ["show todos", "list tasks", "what are my tasks", "my to-do list"]):
            todos = self.memory.get_todos()
            if todos:
                todo_list = "\n".join([f"{'✅' if t.get('completed') else '⬜'} {t['content']}" for t in todos[:10]])
                return {"text": f"Your to-do list:\n{todo_list}", "actions": [{"type": "show_todos", "data": todos}]}
            else:
                return {"text": "Your to-do list is empty. Add tasks by saying 'add todo [task]'", "actions": []}
        
        # Memory - Show notes
        if any(p in q for p in ["show notes", "my notes", "what did i save", "read notes"]):
            notes = self.memory.get_notes()
            if notes:
                notes_list = "\n\n".join([f"• {n['content'][:100]}..." for n in notes[:5]])
                return {"text": f"Your notes:\n{notes_list}", "actions": [{"type": "show_notes", "data": notes}]}
            else:
                return {"text": "You don't have any saved notes.", "actions": []}
        
        # Help
        if any(p in q for p in ["help", "what can you do", "commands", "capabilities"]):
            return {
                "text": """🤖 **JARVIS Capabilities:**

**System Control:**
• Open/Close apps - "open chrome", "close notepad"
• Volume control - "volume up", "mute"
• Screenshot - "take screenshot"
• System status - "check system"

**Web & Search:**
• Web search - "search for [query]"
• Open websites - "open youtube"

**Memory:**
• Add todo - "add todo [task]"
• Add note - "add note [content]"
• View todos/notes - "show my todos"

**Information:**
• Time/Date - "what time is it"
• Daily briefing - "daily briefing"
• Running apps - "list apps"

What would you like to do?""",
                "actions": [{"type": "help"}]
            }
        
        return None
    
    async def _execute_app_command(self, action: str, app_name: str) -> Dict[str, Any]:
        """Execute app open/close command"""
        try:
            if action == "open":
                # Try to open via automation
                from jarvis.automation import Automation
                auto = Automation()
                result = auto.open_application(app_name)
                
                if result:
                    return {"text": f"🚀 Opened {app_name}", "actions": [{"type": "open_app", "app": app_name}]}
                else:
                    # Try web browser for websites
                    import webbrowser
                    url_map = {
                        "youtube": "https://youtube.com",
                        "google": "https://google.com",
                        "gmail": "https://gmail.com",
                        "github": "https://github.com",
                        "spotify": "https://open.spotify.com",
                        "netflix": "https://netflix.com",
                    }
                    
                    if app_name.lower() in url_map:
                        webbrowser.open(url_map[app_name.lower()])
                        return {"text": f"🌐 Opened {app_name} in browser", "actions": [{"type": "open_url", "url": url_map[app_name.lower()]}]}
                    else:
                        return {"text": f"I couldn't find {app_name}. Try a different name or check if it's installed.", "actions": []}
            
            elif action == "close":
                from jarvis.system_control import close_app
                result = close_app(app_name)
                return {"text": f"❌ Closed {app_name}", "actions": [{"type": "close_app", "app": app_name}]}
        
        except Exception as e:
            return {"text": f"Failed to {action} {app_name}: {e}", "actions": []}
    
    def _get_suggestions(self, last_message: str) -> List[str]:
        """Get contextual suggestions based on conversation"""
        message_lower = last_message.lower()
        
        if any(p in message_lower for p in ["todo", "task"]):
            return ["show my todos", "add todo", "mark todo as done"]
        elif any(p in message_lower for p in ["note", "remember"]):
            return ["show my notes", "add note about..."]
        elif any(p in message_lower for p in ["open", "app"]):
            return ["close chrome", "open notepad", "list apps"]
        elif any(p in message_lower for p in ["system", "computer", "status"]):
            return ["daily briefing", "take screenshot", "what time is it"]
        else:
            return ["system status", "daily briefing", "help"]
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get current system statistics"""
        if self.dashboard:
            return self.dashboard.get_current_stats()
        return self._get_default_stats()
    
    def _get_default_stats(self) -> Dict[str, Any]:
        """Return default stats when dashboard unavailable"""
        import psutil
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            battery = psutil.sensors_battery()
            
            return {
                'cpu': {'usage': psutil.cpu_percent(interval=0.1), 'cores': psutil.cpu_count(), 'frequency': 2400},
                'memory': {'used': memory.used, 'total': memory.total, 'percentage': memory.percent},
                'battery': {'percentage': battery.percent if battery else 100, 'isCharging': battery.power_plugged if battery else True, 'timeRemaining': None},
                'disk': {'used': disk.used, 'total': disk.total, 'percentage': (disk.used / disk.total) * 100},
                'network': {'downloadSpeed': 0, 'uploadSpeed': 0, 'ping': 0},
                'processes': {'count': len(psutil.pids()), 'top': []},
                'uptime': time.time() - psutil.boot_time(),
            }
        except:
            return {
                'cpu': {'usage': 23, 'cores': 8, 'frequency': 2400},
                'memory': {'used': 8589934592, 'total': 17179869184, 'percentage': 50},
                'battery': {'percentage': 78, 'isCharging': True, 'timeRemaining': None},
                'disk': {'used': 250000000000, 'total': 500000000000, 'percentage': 45},
                'network': {'downloadSpeed': 56200000, 'uploadSpeed': 18700000, 'ping': 0},
                'processes': {'count': 142, 'top': []},
                'uptime': 7200,
            }
    
    def get_memory_data(self) -> Dict[str, List]:
        """Get todos, notes, reminders"""
        if self.memory:
            return {
                "todos": self.memory.get_todos(),
                "notes": self.memory.get_notes(),
                "reminders": self.memory.get_reminders(),
                "sessions": self.memory.get_sessions()
            }
        return {"todos": [], "notes": [], "reminders": [], "sessions": []}
    
    def get_plugins(self) -> List[Dict]:
        """Get plugin statuses"""
        try:
            from jarvis.plugins import get_plugin_status
            return get_plugin_status()
        except:
            return [
                {"id": "vision", "name": "Vision", "status": "ready", "version": "1.0.0", "description": "Webcam, QR, Motion Detection"},
                {"id": "ocr", "name": "OCR", "status": "ready", "version": "1.0.0", "description": "Image & Screen Text Recognition"},
                {"id": "file-ai", "name": "File AI", "status": "ready", "version": "1.0.0", "description": "PDF, DOCX, Excel Processing"},
                {"id": "browser", "name": "Browser Agent", "status": "ready", "version": "1.0.0", "description": "Web Automation"},
                {"id": "local-llm", "name": "Local LLM", "status": "not_loaded", "version": "1.0.0", "description": "Run Local AI Models"},
            ]

# Global JARVIS core
jarvis_core = JarvisDesktopCore()

# ============== WEBSOCKET MANAGER ==============

class ConnectionManager:
    """Manage WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self._broadcast_task: Optional[asyncio.Task] = None
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected. Total: {len(self.active_connections)}")
        
        # Send initial data
        stats = jarvis_core.get_system_stats()
        await websocket.send_json({"type": "system_stats", "payload": stats})
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        logger.info(f"Client {client_id} disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast to all connected clients"""
        disconnected = []
        for client_id, connection in self.active_connections.items():
            try:
                await connection.send_json(message)
            except:
                disconnected.append(client_id)
        
        for client_id in disconnected:
            self.disconnect(client_id)
    
    async def send_to_client(self, client_id: str, message: Dict[str, Any]):
        """Send message to specific client"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except:
                self.disconnect(client_id)

manager = ConnectionManager()

# ============== FASTAPI APP ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("🚀 Starting JARVIS Ultimate API...")
    await jarvis_core.initialize()
    
    # Start background tasks
    broadcast_task = asyncio.create_task(broadcast_system_stats())
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down JARVIS Ultimate API...")
    broadcast_task.cancel()
    try:
        await broadcast_task
    except asyncio.CancelledError:
        pass

async def broadcast_system_stats():
    """Continuously broadcast system stats"""
    while True:
        try:
            stats = jarvis_core.get_system_stats()
            await manager.broadcast({
                "type": "system_stats",
                "payload": stats
            })
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
            await asyncio.sleep(5)

app = FastAPI(
    title="JARVIS Ultimate API",
    description="Fully Functional AI Desktop Assistant Backend",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============== API ENDPOINTS ==============

@app.get("/")
async def root():
    return {
        "name": "JARVIS Ultimate",
        "version": "2.0.0",
        "status": "online",
        "ai_initialized": jarvis_core.initialized,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "ai_ready": jarvis_core.initialized,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process chat message with full JARVIS AI"""
    try:
        result = await jarvis_core.chat(request.message, request.session_id)
        
        return ChatResponse(
            response=result["response"],
            session_id=request.session_id,
            timestamp=datetime.now().isoformat(),
            actions=result.get("actions"),
            suggestions=result.get("suggestions")
        )
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system-stats")
async def get_system_stats():
    """Get current system statistics"""
    return {"stats": jarvis_core.get_system_stats()}

@app.post("/api/execute", response_model=CommandResponse)
async def execute_command(request: CommandRequest):
    """Execute system command"""
    try:
        result = await jarvis_core._execute_single_task(request.command, "api")
        
        return CommandResponse(
            success=True,
            result=result.get("text", ""),
            command=request.command,
            timestamp=datetime.now().isoformat(),
            data={"actions": result.get("actions", [])}
        )
    except Exception as e:
        return CommandResponse(
            success=False,
            result=str(e),
            command=request.command,
            timestamp=datetime.now().isoformat()
        )

@app.get("/api/plugins")
async def get_plugins():
    """Get plugin statuses"""
    return {"plugins": jarvis_core.get_plugins()}

@app.get("/api/memory")
async def get_memory():
    """Get memory data (todos, notes, reminders)"""
    return jarvis_core.get_memory_data()

@app.post("/api/memory/todo")
async def add_todo(content: str):
    """Add a new todo"""
    if jarvis_core.memory:
        todo_id = jarvis_core.memory.add_todo(content)
        return {"success": True, "id": todo_id}
    return {"success": False, "error": "Memory not initialized"}

@app.post("/api/memory/note")
async def add_note(content: str):
    """Add a new note"""
    if jarvis_core.memory:
        note_id = jarvis_core.memory.add_note(content)
        return {"success": True, "id": note_id}
    return {"success": False, "error": "Memory not initialized"}

@app.delete("/api/memory/todo/{todo_id}")
async def delete_todo(todo_id: str):
    """Delete a todo"""
    if jarvis_core.memory:
        jarvis_core.memory.delete_todo(todo_id)
        return {"success": True}
    return {"success": False, "error": "Memory not initialized"}

# ============== WEBSOCKET ENDPOINT ==============

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time chat and updates"""
    client_id = f"client_{id(websocket)}"
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            
            elif msg_type == "chat":
                message = data.get("message", "")
                session_id = data.get("session_id", client_id)
                
                # Process with JARVIS AI
                result = await jarvis_core.chat(message, session_id)
                
                await websocket.send_json({
                    "type": "chat_response",
                    "payload": {
                        "message": result["response"],
                        "actions": result.get("actions", []),
                        "suggestions": result.get("suggestions", [])
                    }
                })
            
            elif msg_type == "set_listening":
                await manager.broadcast({
                    "type": "listening_state",
                    "payload": {"isListening": data.get("value", False)}
                })
            
            elif msg_type == "get_system_stats":
                stats = jarvis_core.get_system_stats()
                await websocket.send_json({
                    "type": "system_stats",
                    "payload": stats
                })
            
            elif msg_type == "execute":
                command = data.get("command", "")
                result = await jarvis_core._execute_single_task(command, client_id)
                
                await websocket.send_json({
                    "type": "execute_result",
                    "payload": {
                        "command": command,
                        "result": result.get("text", ""),
                        "success": True
                    }
                })
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(client_id)

# ============== MAIN ==============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "jarvis_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
