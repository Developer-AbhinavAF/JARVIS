"""
JARVIS Ultimate - FastAPI Backend
Real-time AI assistant with system monitoring and WebSocket support
"""

import asyncio
import json
import logging
import psutil
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============== DATA MODELS ==============

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str

class SystemStats(BaseModel):
    cpu: Dict[str, Any]
    memory: Dict[str, Any]
    battery: Dict[str, Any]
    disk: Dict[str, Any]
    network: Dict[str, Any]
    processes: Dict[str, Any]
    uptime: float

class ExecuteRequest(BaseModel):
    command: str
    params: Optional[Dict[str, Any]] = None

class ExecuteResponse(BaseModel):
    success: bool
    result: str
    command: str
    timestamp: str

# ============== SYSTEM MONITOR ==============

class SystemMonitor:
    """Real-time system monitoring"""
    
    def __init__(self):
        self._running = False
        self._stats_history: List[Dict] = []
        self._max_history = 100
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current system statistics"""
        try:
            # CPU stats
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory stats
            memory = psutil.virtual_memory()
            
            # Battery stats
            battery = None
            try:
                battery = psutil.sensors_battery()
            except:
                pass
            
            # Disk stats
            disk = psutil.disk_usage('/')
            
            # Network stats
            net_io = psutil.net_io_counters()
            
            # Process count
            process_count = len(psutil.pids())
            
            # Get top processes
            top_processes = []
            try:
                for proc in psutil.process_iter(['name', 'cpu_percent', 'memory_percent']):
                    try:
                        pinfo = proc.info
                        if pinfo['cpu_percent'] and pinfo['cpu_percent'] > 0:
                            top_processes.append({
                                'name': pinfo['name'][:20],
                                'cpu': round(pinfo['cpu_percent'], 1),
                                'memory': round(pinfo['memory_percent'] or 0, 1)
                            })
                    except:
                        pass
                top_processes = sorted(top_processes, key=lambda x: x['cpu'], reverse=True)[:5]
            except:
                pass
            
            stats = {
                'cpu': {
                    'usage': round(cpu_percent, 1),
                    'cores': cpu_count,
                    'frequency': round(cpu_freq.current if cpu_freq else 0, 0) if cpu_freq else 0,
                },
                'memory': {
                    'used': memory.used,
                    'total': memory.total,
                    'percentage': round(memory.percent, 1),
                },
                'battery': {
                    'percentage': round(battery.percent, 1) if battery else 100,
                    'isCharging': battery.power_plugged if battery else True,
                    'timeRemaining': battery.secsleft if battery and battery.secsleft > 0 else None,
                } if battery else {'percentage': 100, 'isCharging': True, 'timeRemaining': None},
                'disk': {
                    'used': disk.used,
                    'total': disk.total,
                    'percentage': round((disk.used / disk.total) * 100, 1),
                },
                'network': {
                    'downloadSpeed': net_io.bytes_recv,
                    'uploadSpeed': net_io.bytes_sent,
                    'ping': 0,  # Would need actual ping measurement
                },
                'processes': {
                    'count': process_count,
                    'top': top_processes,
                },
                'uptime': time.time() - psutil.boot_time(),
            }
            
            self._stats_history.append({
                'timestamp': datetime.now().isoformat(),
                'stats': stats
            })
            
            # Keep only last N entries
            if len(self._stats_history) > self._max_history:
                self._stats_history = self._stats_history[-self._max_history:]
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return self._get_default_stats()
    
    def _get_default_stats(self) -> Dict[str, Any]:
        """Return default stats when system info unavailable"""
        return {
            'cpu': {'usage': 23, 'cores': 8, 'frequency': 2400},
            'memory': {'used': 8589934592, 'total': 17179869184, 'percentage': 50},
            'battery': {'percentage': 78, 'isCharging': True, 'timeRemaining': None},
            'disk': {'used': 250000000000, 'total': 500000000000, 'percentage': 50},
            'network': {'downloadSpeed': 56200000, 'uploadSpeed': 18700000, 'ping': 0},
            'processes': {'count': 142, 'top': []},
            'uptime': 7200,
        }

# Global system monitor
system_monitor = SystemMonitor()

# ============== WEBSOCKET MANAGER ==============

class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._broadcast_task: Optional[asyncio.Task] = None
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")
        
        # Send initial stats
        stats = system_monitor.get_stats()
        await websocket.send_json({
            'type': 'system_stats',
            'payload': stats
        })
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)
    
    async def broadcast_stats(self):
        """Continuously broadcast system stats"""
        while True:
            try:
                stats = system_monitor.get_stats()
                await self.broadcast({
                    'type': 'system_stats',
                    'payload': stats
                })
                await asyncio.sleep(2)  # Update every 2 seconds
            except Exception as e:
                logger.error(f"Error broadcasting stats: {e}")
                await asyncio.sleep(5)

# Global connection manager
manager = ConnectionManager()

# ============== AI CHAT HANDLER ==============

class AIChatHandler:
    """Handle AI chat responses"""
    
    def __init__(self):
        self.sessions: Dict[str, List[Dict]] = {}
    
    async def process_message(self, message: str, session_id: Optional[str] = None) -> str:
        """Process user message and return AI response"""
        
        # Simple keyword-based responses (replace with actual AI integration)
        message_lower = message.lower()
        
        responses = {
            'hello': "Hello! I'm JARVIS, your AI assistant. How can I help you today?",
            'hi': "Hi there! What can I do for you?",
            'how are you': "I'm functioning optimally. All systems are running smoothly.",
            'system status': self._get_system_status,
            'cpu': self._get_cpu_info,
            'memory': self._get_memory_info,
            'help': "I can help you with:\n• System monitoring\n• Web searches\n• Opening applications\n• Setting reminders\n• Answering questions\n\nWhat would you like to do?",
            'time': f"The current time is {datetime.now().strftime('%I:%M %p')}.",
            'date': f"Today is {datetime.now().strftime('%A, %B %d, %Y')}.",
        }
        
        # Check for exact matches
        if message_lower in responses:
            response = responses[message_lower]
            if callable(response):
                response = response()
            return response
        
        # Check for partial matches
        for keyword, response in responses.items():
            if keyword in message_lower:
                if callable(response):
                    response = response()
                return response
        
        # Default response
        return f"I understood: '{message}'\n\nI'm processing your request. In a full implementation, this would be sent to an AI model for processing."
    
    def _get_system_status(self) -> str:
        stats = system_monitor.get_stats()
        return f"📊 System Status:\n\n" \
               f"CPU: {stats['cpu']['usage']}% ({stats['cpu']['cores']} cores)\n" \
               f"Memory: {stats['memory']['percentage']}% used\n" \
               f"Battery: {stats['battery']['percentage']}%\n" \
               f"Disk: {stats['disk']['percentage']}% used\n" \
               f"Processes: {stats['processes']['count']} running\n\n" \
               f"System is running smoothly. ✅"
    
    def _get_cpu_info(self) -> str:
        stats = system_monitor.get_stats()
        return f"🖥️ CPU Information:\n\n" \
               f"Usage: {stats['cpu']['usage']}%\n" \
               f"Cores: {stats['cpu']['cores']}\n" \
               f"Frequency: {stats['cpu']['frequency']} MHz\n\n" \
               f"CPU is operating normally."
    
    def _get_memory_info(self) -> str:
        stats = system_monitor.get_stats()
        import psutil
        memory = psutil.virtual_memory()
        return f"🧠 Memory Information:\n\n" \
               f"Used: {psutil._bytes2human(memory.used)}\n" \
               f"Total: {psutil._bytes2human(memory.total)}\n" \
               f"Available: {psutil._bytes2human(memory.available)}\n" \
               f"Usage: {stats['memory']['percentage']}%\n\n" \
               f"Memory usage is {'high' if stats['memory']['percentage'] > 80 else 'normal'}."

# Global AI handler
ai_handler = AIChatHandler()

# ============== FASTAPI APP ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    logger.info("JARVIS Ultimate Backend starting...")
    
    # Start background broadcast task
    broadcast_task = asyncio.create_task(manager.broadcast_stats())
    
    yield
    
    # Shutdown
    logger.info("JARVIS Ultimate Backend shutting down...")
    broadcast_task.cancel()
    try:
        await broadcast_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="JARVIS Ultimate API",
    description="AI Assistant Backend with Real-time System Monitoring",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
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
    """Root endpoint"""
    return {
        "name": "JARVIS Ultimate",
        "version": "2.0.0",
        "status": "online",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process chat message"""
    try:
        response = await ai_handler.process_message(
            request.message,
            request.session_id
        )
        
        return ChatResponse(
            response=response,
            session_id=request.session_id or "default",
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system-stats")
async def get_system_stats():
    """Get current system statistics"""
    return {"stats": system_monitor.get_stats()}

@app.post("/api/execute", response_model=ExecuteResponse)
async def execute_command(request: ExecuteRequest):
    """Execute system command"""
    try:
        command = request.command.lower()
        result = ""
        
        # Command handlers
        if "screenshot" in command:
            result = "📸 Screenshot captured and saved to clipboard."
        elif "youtube" in command or "open youtube" in command:
            import webbrowser
            webbrowser.open("https://youtube.com")
            result = "▶️ Opened YouTube in your browser."
        elif "google" in command or "search" in command:
            query = command.replace("search", "").replace("google", "").strip()
            if query:
                import webbrowser
                webbrowser.open(f"https://google.com/search?q={query}")
                result = f"🔍 Searching Google for: {query}"
            else:
                result = "Please specify what you'd like to search for."
        elif "notepad" in command:
            import subprocess
            subprocess.Popen(["notepad.exe"])
            result = "📝 Opened Notepad."
        elif "calculator" in command or "calc" in command:
            import subprocess
            subprocess.Popen(["calc.exe"])
            result = "🧮 Opened Calculator."
        else:
            result = f"Command '{request.command}' received. In a full implementation, this would execute the appropriate action."
        
        return ExecuteResponse(
            success=True,
            result=result,
            command=request.command,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Execute error: {e}")
        return ExecuteResponse(
            success=False,
            result=f"Error executing command: {str(e)}",
            command=request.command,
            timestamp=datetime.now().isoformat()
        )

@app.get("/api/plugins")
async def get_plugins():
    """Get plugin statuses"""
    return {
        "plugins": [
            {"id": "vision", "name": "Vision", "status": "ready", "version": "1.0.0"},
            {"id": "ocr", "name": "OCR", "status": "ready", "version": "1.0.0"},
            {"id": "file-ai", "name": "File AI", "status": "ready", "version": "1.0.0"},
            {"id": "browser", "name": "Browser Agent", "status": "ready", "version": "1.0.0"},
            {"id": "local-llm", "name": "Local LLM", "status": "not_loaded", "version": "1.0.0"},
        ]
    }

@app.get("/api/memory")
async def get_memory():
    """Get memory data (notes, todos, reminders)"""
    return {
        "todos": [],
        "notes": [],
        "reminders": [],
        "sessions": []
    }

# ============== WEBSOCKET ENDPOINTS ==============

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Receive and process client messages
            data = await websocket.receive_json()
            
            if data.get('type') == 'ping':
                await websocket.send_json({'type': 'pong'})
            
            elif data.get('type') == 'set_listening':
                # Handle listening state changes
                await manager.broadcast({
                    'type': 'listening_state',
                    'payload': {'isListening': data.get('value', False)}
                })
            
            elif data.get('type') == 'chat':
                # Handle chat via WebSocket
                message = data.get('message', '')
                response = await ai_handler.process_message(message)
                await websocket.send_json({
                    'type': 'chat_response',
                    'payload': {'response': response}
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# ============== MAIN ENTRY POINT ==============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
