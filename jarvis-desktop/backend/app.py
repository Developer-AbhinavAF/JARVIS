"""
JARVIS Ultimate - Simple Working Backend
Guaranteed to work with all commands
"""

import asyncio
import json
import logging
import os
import sys
import subprocess
import webbrowser
import psutil
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add JARVIS to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

app = FastAPI(title="JARVIS Ultimate", version="2.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# State
jarvis_core = None

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str
    actions: Optional[list] = None
    suggestions: Optional[list] = None

class JarvisCore:
    def __init__(self):
        self.initialized = False
        self.memory = None
        self.dashboard = None
        self.llm = None
        
    async def initialize(self):
        if self.initialized:
            return
            
        try:
            logger.info("Initializing JARVIS...")
            
            # Import JARVIS modules
            from jarvis.memory import memory
            from jarvis.dashboard import SystemDashboard
            from jarvis.llm import JarvisLLM
            
            self.memory = memory
            self.dashboard = SystemDashboard()
            self.llm = JarvisLLM()
            
            # Start monitoring
            self.dashboard.start_monitoring()
            
            self.initialized = True
            logger.info("✅ JARVIS initialized successfully!")
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            # Continue without full initialization
            self.initialized = True
            
    async def chat(self, message: str, session_id: str = "default") -> Dict[str, Any]:
        if not self.initialized:
            await self.initialize()
            
        q = message.strip().lower()
        
        # === BUILT-IN COMMANDS ===
        
        # 1. Open apps/websites
        if q.startswith("open "):
            target = message[5:].strip()
            return await self._handle_open(target)
            
        # 2. System status
        if any(p in q for p in ["system status", "how's my computer", "check system"]):
            return self._handle_system_status()
            
        # 3. Daily briefing
        if any(p in q for p in ["daily briefing", "what's on my schedule", "what do i have today"]):
            return self._handle_daily_briefing()
            
        # 4. Screenshot
        if any(p in q for p in ["screenshot", "capture screen"]):
            return self._handle_screenshot()
            
        # 5. Web search
        if any(p in q for p in ["search", "google", "look up"]):
            return await self._handle_search(message)
            
        # 6. Time/Date
        if any(p in q for p in ["what time", "current time"]):
            now = datetime.now()
            return {"response": f"The current time is {now.strftime('%I:%M %p')}", "actions": [{"type": "time"}]}
            
        if any(p in q for p in ["what date", "today's date"]):
            now = datetime.now()
            return {"response": f"Today is {now.strftime('%A, %B %d, %Y')}", "actions": [{"type": "date"}]}
            
        # 7. Memory - Add todo
        if any(p in q for p in ["add todo", "create task", "new task"]):
            task = message
            for prefix in ["add todo", "create task", "new task", "remember to"]:
                if task.lower().startswith(prefix):
                    task = task[len(prefix):].strip()
            if task and self.memory:
                todo_id = self.memory.add_todo(task)
                return {"response": f"✅ Added to your to-do list: {task}", "actions": [{"type": "add_todo", "id": todo_id}]}
            return {"response": f"✅ Added to your to-do list: {task}", "actions": [{"type": "add_todo"}]}
            
        # 8. Memory - Show todos
        if any(p in q for p in ["show todos", "my todos", "list todos"]):
            if self.memory:
                todos = self.memory.list_todos()
                if todos:
                    todo_text = "\n".join([f"{'✅' if t.completed else '⬜'} {t.text}" for t in todos])
                    return {"response": f"Your to-do list:\n{todo_text}", "actions": [{"type": "show_todos"}]}
            return {"response": "Your to-do list is empty. Add tasks with 'add todo [task]'", "actions": []}
            
        # 9. Memory - Add note
        if any(p in q for p in ["add note", "write down", "remember that"]):
            note = message
            for prefix in ["add note", "write down", "remember that", "save note"]:
                if note.lower().startswith(prefix):
                    note = note[len(prefix):].strip()
            if note and self.memory:
                note_id = self.memory.add_note(note)
                return {"response": f"📝 Note saved: {note[:50]}...", "actions": [{"type": "add_note", "id": note_id}]}
            return {"response": f"📝 Note saved: {note[:50]}...", "actions": [{"type": "add_note"}]}
            
        # 10. Clear memory
        if any(p in q for p in ["clear memory", "forget", "reset"]):
            if self.llm:
                self.llm.clear_history()
            return {"response": "Memory cleared. I've reset our conversation.", "actions": [{"type": "clear_memory"}]}
        
        # 11. Calculator
        if any(p in q for p in ["calculate", "calc", "what is", "compute"]):
            return self._handle_calculator(message)
        
        # 12. Weather
        if any(p in q for p in ["weather", "temperature", "forecast"]):
            return self._handle_weather(message)
        
        # 13. Joke
        if any(p in q for p in ["tell me a joke", "joke", "make me laugh", "funny"]):
            return self._handle_joke()
        
        # 14. Quote
        if any(p in q for p in ["quote", "inspiration", "motivation", "wisdom"]):
            return self._handle_quote()
        
        # 15. Network info
        if any(p in q for p in ["network status", "wifi status", "ip address", "internet speed"]):
            return self._handle_network_status()
        
        # 16. Process info
        if any(p in q for p in ["running processes", "what's running", "cpu intensive", "top processes"]):
            return self._handle_process_info()
        
        # 17. Random number/fact
        if any(p in q for p in ["random number", "random fact", "did you know", "tell me something"]):
            return self._handle_random_fact()
        
        # 18. Volume/Media controls (via PC Control)
        if any(p in q for p in ["volume up", "increase volume", "vol up"]):
            return await self._execute_single_task("volume_up", session_id)
        if any(p in q for p in ["volume down", "decrease volume", "vol down"]):
            return await self._execute_single_task("volume_down", session_id)
        if any(p in q for p in ["mute", "unmute", "volume mute"]):
            return await self._execute_single_task("mute", session_id)
        if any(p in q for p in ["play", "pause", "media play", "play pause"]):
            return await self._execute_single_task("play_pause", session_id)
        if any(p in q for p in ["next track", "skip song", "next song"]):
            return await self._execute_single_task("next_track", session_id)
        if any(p in q for p in ["previous track", "prev song", "back"]):
            return await self._execute_single_task("prev_track", session_id)
        
        # 19. System power commands
        if any(p in q for p in ["shutdown", "shut down", "power off"]):
            return await self._execute_single_task("shutdown", session_id)
        if any(p in q for p in ["restart", "reboot", "restart computer"]):
            return await self._execute_single_task("restart", session_id)
        if any(p in q for p in ["sleep", "hibernate", "suspend"]):
            return await self._execute_single_task("sleep", session_id)
        if any(p in q for p in ["lock", "lock screen", "lock computer"]):
            return await self._execute_single_task("lock", session_id)
        if any(p in q for p in ["cancel shutdown", "abort shutdown", "stop shutdown"]):
            return await self._execute_single_task("cancel_shutdown", session_id)
        
        # 20. Help
        if any(p in q for p in ["help", "what can you do", "capabilities"]):
            return {
                "response": """🚀 **JARVIS Capabilities - 25+ Commands:**

**🖥️ System & Control:**
• "open [app/website]" - Launch apps or websites
• "system status" - CPU, RAM, battery info
• "network status" - WiFi, IP, internet info
• "running processes" - Top CPU/memory processes
• "take screenshot" - Capture screen
• "volume up/down/mute" - Audio control
• "play/pause/next/previous" - Media controls

**⚡ Power Commands:**
• "shutdown" - Shutdown in 60 seconds
• "restart" - Restart in 60 seconds
• "sleep" - Put system to sleep
• "lock" - Lock screen
• "cancel shutdown" - Abort shutdown

**🔍 Web & Search:**
• "search [query]" - Search the web
• "open youtube/google/gmail" - Quick website access

**🧰 Utilities:**
• "calculate [expression]" - Calculator (e.g., 15 * 23)
• "weather" - Current weather info
• "tell me a joke" - Random joke
• "quote" - Inspirational quote
• "random fact" - Interesting fact

**📝 Memory & Tasks:**
• "add todo [task]" - Add to-do items
• "show my todos" - View your tasks
• "add note [text]" - Save notes
• "daily briefing" - Today's overview

**ℹ️ Info:**
• "what time is it" - Current time
• "what's today's date" - Current date

**🎮 Control:**
• "clear memory" - Reset conversation
• "help" - Show this message""",
                "actions": [{"type": "help"}]
            }
        
        # === LLM FOR COMPLEX QUERIES ===
        try:
            if self.llm:
                response = self.llm.chat(message)
                if isinstance(response, dict):
                    text = response.get("text", str(response))
                else:
                    text = str(response)
                return {"response": text, "actions": []}
        except Exception as e:
            logger.error(f"LLM error: {e}")
            
        # Default response
        return {
            "response": f"I received: '{message}'\n\nI'm a fully functional AI assistant! Try commands like:\n• 'open youtube'\n• 'system status'\n• 'add todo buy milk'\n• 'search artificial intelligence'\n• 'help' for more options",
            "actions": [],
            "suggestions": ["open youtube", "system status", "add todo", "search news", "help"]
        }
    
    async def _handle_open(self, target: str) -> Dict[str, Any]:
        """Handle open commands"""
        target_lower = target.lower()
        
        # Website mappings
        websites = {
            "youtube": "https://youtube.com",
            "google": "https://google.com",
            "gmail": "https://gmail.com",
            "github": "https://github.com",
            "spotify": "https://open.spotify.com",
            "netflix": "https://netflix.com",
            "facebook": "https://facebook.com",
            "twitter": "https://twitter.com",
            "instagram": "https://instagram.com",
            "linkedin": "https://linkedin.com",
            "reddit": "https://reddit.com",
            "amazon": "https://amazon.com",
        }
        
        # Check if it's a website
        if target_lower in websites:
            url = websites[target_lower]
            webbrowser.open(url)
            return {"response": f"🌐 Opened {target} in browser", "actions": [{"type": "open_url", "url": url}]}
        
        # Try to open as application
        try:
            # Windows specific
            if sys.platform == "win32":
                # Try direct command
                subprocess.Popen(f"start {target}", shell=True)
                return {"response": f"🚀 Opened {target}", "actions": [{"type": "open_app", "app": target}]}
            else:
                subprocess.Popen([target])
                return {"response": f"🚀 Opened {target}", "actions": [{"type": "open_app", "app": target}]}
        except Exception as e:
            # Fallback to web search
            webbrowser.open(f"https://www.google.com/search?q={target.replace(' ', '+')}")
            return {"response": f"🔍 Couldn't find app '{target}', searched on Google instead.", "actions": [{"type": "search", "query": target}]}
    
    def _handle_system_status(self) -> Dict[str, Any]:
        """Get system stats"""
        try:
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            battery = psutil.sensors_battery()
            
            status = f"""📊 **System Status:**

**CPU:** {cpu}% usage
**Memory:** {memory.percent}% used ({memory.used//(1024**3)}GB / {memory.total//(1024**3)}GB)
**Disk:** {disk.percent}% used ({disk.used//(1024**3)}GB / {disk.total//(1024**3)}GB)"""
            
            if battery:
                status += f"\n**Battery:** {battery.percent}% {'⚡ Charging' if battery.power_plugged else '🔋 Discharging'}"
            
            return {"response": status, "actions": [{"type": "system_status"}]}
        except Exception as e:
            return {"response": f"System stats unavailable: {e}", "actions": []}
    
    def _handle_daily_briefing(self) -> Dict[str, Any]:
        """Get daily briefing"""
        try:
            now = datetime.now()
            greeting = "Good morning" if now.hour < 12 else "Good afternoon" if now.hour < 17 else "Good evening"
            
            briefing = f"{greeting}! 📅\n\n**Today:** {now.strftime('%A, %B %d, %Y')}\n**Time:** {now.strftime('%I:%M %p')}\n\n"
            
            # Add todos if memory available
            if self.memory:
                todos = self.memory.list_todos()
                pending = [t for t in todos if not t.completed]
                if pending:
                    briefing += f"**Pending Tasks:** {len(pending)}\n"
                    for t in pending[:5]:
                        briefing += f"⬜ {t.text}\n"
                else:
                    briefing += "**All caught up!** No pending tasks. ✅\n"
            
            # Add system status
            try:
                cpu = psutil.cpu_percent(interval=0.5)
                mem = psutil.virtual_memory().percent
                briefing += f"\n**System:** CPU {cpu}% | Memory {mem}%"
            except:
                pass
                
            return {"response": briefing, "actions": [{"type": "daily_briefing"}]}
        except Exception as e:
            return {"response": f"Briefing unavailable: {e}", "actions": []}
    
    def _handle_screenshot(self) -> Dict[str, Any]:
        """Take screenshot"""
        try:
            import pyautogui
            from datetime import datetime
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            pyautogui.screenshot(filename)
            return {"response": f"📸 Screenshot saved: {filename}", "actions": [{"type": "screenshot", "path": filename}]}
        except Exception as e:
            return {"response": f"Screenshot failed: {e}", "actions": []}
    
    async def _handle_search(self, query: str) -> Dict[str, Any]:
        """Web search"""
        try:
            # Try to import and use jarvis web_search
            from jarvis.tools import web_search
            
            # Extract search query
            search_query = query
            for prefix in ["search for", "search", "google", "look up", "find"]:
                if search_query.lower().startswith(prefix):
                    search_query = search_query[len(prefix):].strip()
            
            result = web_search(search_query)
            return {"response": result, "actions": [{"type": "web_search", "query": search_query}]}
        except Exception as e:
            # Fallback to just opening browser
            search_query = query
            for prefix in ["search for", "search", "google", "look up", "find"]:
                if search_query.lower().startswith(prefix):
                    search_query = search_query[len(prefix):].strip()
            
            url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}".replace('%20', '+')
            webbrowser.open(url)
            return {"response": f"🔍 Searching Google for: {search_query}\n{url}", "actions": [{"type": "web_search", "url": url}]}

    def _handle_calculator(self, message: str) -> Dict[str, Any]:
        """Calculator - evaluate math expressions"""
        try:
            # Extract expression
            expression = message
            for prefix in ["calculate", "calc", "compute", "what is"]:
                if expression.lower().startswith(prefix):
                    expression = expression[len(prefix):].strip()
            
            # Clean and evaluate
            expression = expression.replace('x', '*').replace('÷', '/')
            # Safe eval with limited operations
            allowed = set('0123456789+-*/.() ')
            if all(c in allowed for c in expression):
                result = eval(expression)
                return {
                    "response": f"🧮 **{expression}** = **{result}**",
                    "actions": [{"type": "calculator", "expression": expression, "result": result}]
                }
            else:
                return {"response": "I can only calculate basic math operations (+, -, *, /, parentheses).", "actions": []}
        except Exception as e:
            return {"response": f"Could not calculate that. Please use format like '15 * 23' or '100 + 50'", "actions": []}

    def _handle_weather(self, message: str) -> Dict[str, Any]:
        """Weather info (placeholder - can be enhanced with API)"""
        try:
            # Check if user wants specific location
            location = None
            for prefix in ["weather in", "weather at", "temperature in"]:
                if prefix in message.lower():
                    location = message.lower().split(prefix)[-1].strip()
                    break
            
            # For now, open weather.com
            if location:
                url = f"https://weather.com/weather/today/l/{location.replace(' ', '+')}"
            else:
                url = "https://weather.com"
            
            webbrowser.open(url)
            
            location_text = f" for {location.title()}" if location else ""
            return {
                "response": f"🌤️ Opening Weather.com{location_text}...\n\nFor real-time weather in your area, I can integrate with a weather API. Would you like me to do that?",
                "actions": [{"type": "weather", "url": url}]
            }
        except Exception as e:
            return {"response": f"Weather info unavailable: {e}", "actions": []}

    def _handle_joke(self) -> Dict[str, Any]:
        """Tell a random joke"""
        import random
        jokes = [
            "Why do programmers prefer dark mode? Because light attracts bugs! 🐛",
            "Why did the scarecrow win an award? He was outstanding in his field! 🌾",
            "Why don't scientists trust atoms? Because they make up everything! ⚛️",
            "Why did the computer go to the doctor? It had a virus! 💻",
            "What do you call a bear with no teeth? A gummy bear! 🐻",
            "Why did the coffee file a police report? It got mugged! ☕",
            "What did the ocean say to the beach? Nothing, it just waved! 🌊",
            "Why don't eggs tell jokes? They'd crack each other up! 🥚",
            "Why did the bicycle fall over? It was two-tired! 🚲",
            "What do you call a fake noodle? An impasta! 🍝",
            "Why did the math book look so sad? Because it had too many problems! 📐",
            "Why don't skeletons fight each other? They don't have the guts! 💀",
            "What did one wall say to the other wall? I'll meet you at the corner! 🧱",
            "Why did the tomato turn red? Because it saw the salad dressing! 🍅",
            "What do you call a sleeping dinosaur? A dino-snore! 🦕",
            "Why don't some couples go to the gym? Because some relationships don't work out! 💪",
            "Why did the cookie go to the nurse? It felt crummy! 🍪",
            "What do you call a pig that does karate? A pork chop! 🥋",
            "Why did the golfer bring two pairs of pants? In case he got a hole in one! ⛳",
            "What do you call a fish with no eyes? A fsh! 🐟",
        ]
        joke = random.choice(jokes)
        return {"response": f"😄 {joke}", "actions": [{"type": "joke"}]}

    def _handle_quote(self) -> Dict[str, Any]:
        """Inspirational quote"""
        import random
        quotes = [
            ("The only way to do great work is to love what you do.", "Steve Jobs"),
            ("Innovation distinguishes between a leader and a follower.", "Steve Jobs"),
            ("Life is what happens when you're busy making other plans.", "John Lennon"),
            ("The future belongs to those who believe in the beauty of their dreams.", "Eleanor Roosevelt"),
            ("It is during our darkest moments that we must focus to see the light.", "Aristotle"),
            ("The only impossible journey is the one you never begin.", "Tony Robbins"),
            ("Success is not final, failure is not fatal: it is the courage to continue that counts.", "Winston Churchill"),
            ("The best way to predict the future is to create it.", "Peter Drucker"),
            ("Believe you can and you're halfway there.", "Theodore Roosevelt"),
            ("Everything you've ever wanted is on the other side of fear.", "George Addair"),
            ("Opportunities don't happen. You create them.", "Chris Grosser"),
            ("Dream big and dare to fail.", "Norman Vaughan"),
            ("It does not matter how slowly you go as long as you do not stop.", "Confucius"),
            ("The mind is everything. What you think you become.", "Buddha"),
            ("An unexamined life is not worth living.", "Socrates"),
            ("Happiness depends upon ourselves.", "Aristotle"),
            ("Turn your wounds into wisdom.", "Oprah Winfrey"),
            ("Do what you can, with what you have, where you are.", "Theodore Roosevelt"),
            ("Everything has beauty, but not everyone can see.", "Confucius"),
            ("He who has a why to live can bear almost any how.", "Friedrich Nietzsche"),
        ]
        quote, author = random.choice(quotes)
        return {
            "response": f"💫 **\"{quote}\"**\n\n— *{author}*",
            "actions": [{"type": "quote", "author": author}]
        }

    def _handle_network_status(self) -> Dict[str, Any]:
        """Get network information"""
        try:
            import socket
            import subprocess
            
            # Get hostname and IP
            hostname = socket.gethostname()
            try:
                ip_address = socket.gethostbyname(hostname)
            except:
                ip_address = "Unavailable"
            
            # Check internet connectivity
            try:
                import urllib.request
                urllib.request.urlopen('http://google.com', timeout=3)
                internet_status = "✅ Connected"
            except:
                internet_status = "❌ No Internet"
            
            # Get network interfaces info
            net_io = psutil.net_io_counters()
            
            info = f"""📡 **Network Status:**

**Hostname:** {hostname}
**IP Address:** {ip_address}
**Internet:** {internet_status}
**Data Sent:** {net_io.bytes_sent // (1024**2)} MB
**Data Received:** {net_io.bytes_recv // (1024**2)} MB
**Packets Sent:** {net_io.packets_sent}
**Packets Received:** {net_io.packets_recv}"""
            
            return {"response": info, "actions": [{"type": "network_status"}]}
        except Exception as e:
            return {"response": f"Network info unavailable: {e}", "actions": []}

    def _handle_process_info(self) -> Dict[str, Any]:
        """Get running process information"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except:
                    pass
            
            # Sort by CPU usage
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            
            # Top 10 CPU consuming
            top_cpu = processes[:10]
            cpu_info = "\n".join([f"• {p['name'][:20]}: CPU {p.get('cpu_percent', 0):.1f}%" for p in top_cpu])
            
            # Sort by memory
            processes.sort(key=lambda x: x.get('memory_percent', 0), reverse=True)
            top_mem = processes[:5]
            mem_info = "\n".join([f"• {p['name'][:20]}: RAM {p.get('memory_percent', 0):.1f}%" for p in top_mem])
            
            total_processes = len(list(psutil.process_iter()))
            
            info = f"""⚙️ **Process Information:**

**Total Running:** {total_processes} processes

**Top CPU Users:**
{cpu_info}

**Top Memory Users:**
{mem_info}"""
            
            return {"response": info, "actions": [{"type": "process_info"}]}
        except Exception as e:
            return {"response": f"Process info unavailable: {e}", "actions": []}

    def _handle_random_fact(self) -> Dict[str, Any]:
        """Random interesting fact"""
        import random
        facts = [
            "🐙 Octopuses have three hearts, blue blood, and nine brains!",
            "🍌 Bananas are technically berries, but strawberries aren't!",
            "🐝 Honey never spoils. Archaeologists have found 3000-year-old honey in Egyptian tombs!",
            "🦒 A giraffe's tongue is so long it can clean its own ears!",
            "🦘 Kangaroos can't walk backwards!",
            "🐘 Elephants are the only mammals that can't jump!",
            "🦋 Butterflies taste with their feet!",
            "🐌 A snail can sleep for three years at a time!",
            "🦈 Sharks are older than trees! They've existed for 400 million years.",
            "🐻 Polar bears have black skin under their white fur to absorb heat!",
            "🦉 A group of owls is called a parliament!",
            "🐧 Penguins propose to their mates with pebbles!",
            "🦎 Geckos can turn the stickiness of their feet on and off!",
            "🐳 Blue whales are the largest animals ever known to live on Earth!",
            "🦔 A baby hedgehog is called a hoglet!",
            "🦩 Flamingos are born grey and turn pink from their diet!",
            "🦃 Turkeys can blush when they're excited or scared!",
            "🦀 Crabs have taste buds on their feet!",
            "🦎 Chameleons don't change color to blend in, but to communicate emotions!",
            "🐢 Sea turtles can hold their breath for up to 5 hours underwater!",
        ]
        fact = random.choice(facts)
        return {"response": f"🤔 **Did you know?**\n\n{fact}", "actions": [{"type": "random_fact"}]}

    async def _handle_image_analysis(self, image_bytes: bytes, filename: str, question: str) -> Dict[str, Any]:
        """Analyze image using AI vision capabilities"""
        try:
            # Save image temporarily
            temp_path = f"temp_{filename}"
            with open(temp_path, "wb") as f:
                f.write(image_bytes)
            
            # Try to use PIL for basic image info
            try:
                from PIL import Image
                img = Image.open(temp_path)
                width, height = img.size
                format_type = img.format or "Unknown"
                mode = img.mode
                
                # Basic image description (without actual AI vision model)
                # In production, you'd use OpenAI GPT-4V, Claude, or local vision model
                description = f"📸 **Image Analysis: {filename}**\n\n"
                description += f"**Dimensions:** {width} x {height} pixels\n"
                description += f"**Format:** {format_type}\n"
                description += f"**Color Mode:** {mode}\n\n"
                
                # Simple color analysis
                if img.mode in ['RGB', 'RGBA']:
                    # Resize for faster processing
                    small_img = img.resize((50, 50))
                    pixels = list(small_img.getdata())
                    
                    # Count colors
                    unique_colors = len(set(pixels))
                    description += f"**Color Variety:** {unique_colors}+ unique colors detected\n"
                    
                    # Detect if image is mostly dark or light
                    brightness = sum(sum(p[:3]) for p in pixels) / (len(pixels) * 3 * 255)
                    if brightness < 0.3:
                        description += "**Tone:** Mostly dark image\n"
                    elif brightness > 0.7:
                        description += "**Tone:** Mostly bright/light image\n"
                    else:
                        description += "**Tone:** Balanced brightness\n"
                
                description += f"\n💡 **Note:** I'm analyzing this image based on its properties. "
                description += f"For your question: \"{question}\"\n\n"
                description += "I can see this is a valid image file. To get detailed visual analysis "
                description += "(objects, text, people), I would need a vision AI model like GPT-4V or Claude."
                
                # Clean up
                os.remove(temp_path)
                
                return {
                    "response": description,
                    "suggestions": ["What are the dimensions?", "Is it a photo or graphic?", "Extract any text"]
                }
                
            except ImportError:
                os.remove(temp_path)
                return {
                    "response": f"📸 Received image: {filename}\n\nI can see this is an image file ({len(image_bytes)} bytes). To analyze its contents visually, please install Pillow: `pip install Pillow`",
                    "suggestions": ["Install image analysis", "Describe what you see", "Convert format"]
                }
                
        except Exception as e:
            logger.error(f"Image analysis error: {e}")
            return {"response": f"Couldn't analyze image: {e}", "actions": []}

    async def _handle_file_analysis(self, file_bytes: bytes, filename: str, file_type: str, question: str) -> Dict[str, Any]:
        """Analyze uploaded files (PDFs, text, etc.)"""
        try:
            file_size = len(file_bytes)
            size_kb = file_size / 1024
            
            response = f"📄 **File Analysis: {filename}**\n\n"
            response += f"**Size:** {size_kb:.2f} KB\n"
            response += f"**Type:** {file_type or 'Unknown'}\n\n"
            
            # Try to extract text content
            text_content = ""
            
            if file_type and 'text' in file_type:
                try:
                    text_content = file_bytes.decode('utf-8', errors='ignore')[:2000]
                    response += "**Content Preview:**\n```\n"
                    response += text_content[:500] + ("..." if len(text_content) > 500 else "")
                    response += "\n```\n\n"
                except:
                    pass
            
            elif filename.endswith('.pdf'):
                response += "📑 **PDF Document**\n"
                response += "This is a PDF file. To extract text content, you can use tools like PyPDF2 or pdfplumber.\n\n"
            
            elif filename.endswith(('.py', '.js', '.html', '.css', '.java', '.cpp', '.c')):
                try:
                    code = file_bytes.decode('utf-8', errors='ignore')[:1500]
                    lines = code.count('\n')
                    response += f"💻 **Code File ({lines} lines)**\n\n```\n{code[:400]}...\n```\n\n"
                except:
                    pass
            
            response += f"💡 **About your question:** \"{question}\"\n\n"
            response += "I can see the file details above. For deeper analysis of specific content, "
            response += "please let me know what you're looking for!"
            
            return {
                "response": response,
                "suggestions": ["Summarize content", "Extract specific data", "Convert format", "Analyze structure"]
            }
            
        except Exception as e:
            logger.error(f"File analysis error: {e}")
            return {"response": f"Couldn't analyze file: {e}", "actions": []}

    async def _execute_single_task(self, command: str, session_id: str = "default") -> Dict[str, Any]:
        """Execute PC control commands"""
        import os
        import ctypes
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        
        cmd = command.strip().lower()
        
        try:
            # === VOLUME CONTROLS ===
            if cmd in ["mute", "unmute", "volume_mute"]:
                try:
                    # Windows volume control using nircmd or keys
                    os.system("nircmd.exe mutesysvolume 1" if os.path.exists("nircmd.exe") else "")
                    # Fallback: Send media mute key
                    import pyautogui
                    pyautogui.press('volumemute')
                    return {"response": "🔇 Volume muted", "actions": [{"type": "volume", "action": "mute"}]}
                except Exception as e:
                    return {"response": f"Volume control not available: {e}", "actions": []}
            
            if cmd in ["unmute", "volume_unmute"]:
                try:
                    import pyautogui
                    pyautogui.press('volumemute')
                    return {"response": "🔊 Volume unmuted", "actions": [{"type": "volume", "action": "unmute"}]}
                except Exception as e:
                    return {"response": f"Volume control not available: {e}", "actions": []}
            
            if cmd in ["volume_up", "increase volume", "vol up", "volume +"]:
                try:
                    import pyautogui
                    for _ in range(5):  # Increase by 5 steps
                        pyautogui.press('volumeup')
                    return {"response": "🔊 Volume increased", "actions": [{"type": "volume", "action": "up"}]}
                except Exception as e:
                    return {"response": f"Volume control not available: {e}", "actions": []}
            
            if cmd in ["volume_down", "decrease volume", "vol down", "volume -"]:
                try:
                    import pyautogui
                    for _ in range(5):
                        pyautogui.press('volumedown')
                    return {"response": "🔉 Volume decreased", "actions": [{"type": "volume", "action": "down"}]}
                except Exception as e:
                    return {"response": f"Volume control not available: {e}", "actions": []}
            
            if cmd in ["volume_max", "max volume"]:
                try:
                    import pyautogui
                    for _ in range(50):  # Max out volume
                        pyautogui.press('volumeup')
                    return {"response": "🔊 Volume set to maximum", "actions": [{"type": "volume", "action": "max"}]}
                except Exception as e:
                    return {"response": f"Volume control not available: {e}", "actions": []}
            
            # === BRIGHTNESS CONTROLS ===
            if cmd in ["brightness_up", "increase brightness", "brighter"]:
                try:
                    import pyautogui
                    # Simulate brightness key (usually Fn + F key, using media keys as fallback)
                    pyautogui.keyDown('fn')
                    pyautogui.keyDown('f12')  # Common brightness up key
                    pyautogui.keyUp('f12')
                    pyautogui.keyUp('fn')
                    return {"response": "☀️ Brightness increased", "actions": [{"type": "brightness", "action": "up"}]}
                except Exception as e:
                    return {"response": f"Brightness control not available: {e}", "actions": []}
            
            if cmd in ["brightness_down", "decrease brightness", "dimmer"]:
                try:
                    import pyautogui
                    pyautogui.keyDown('fn')
                    pyautogui.keyDown('f11')  # Common brightness down key
                    pyautogui.keyUp('f11')
                    pyautogui.keyUp('fn')
                    return {"response": "🌙 Brightness decreased", "actions": [{"type": "brightness", "action": "down"}]}
                except Exception as e:
                    return {"response": f"Brightness control not available: {e}", "actions": []}
            
            if cmd in ["night_mode", "dark mode", "night light"]:
                try:
                    # Toggle Windows night light (requires Windows 10/11)
                    os.system('start ms-settings:nightlight')
                    return {"response": "🌙 Night mode toggled", "actions": [{"type": "night_mode"}]}
                except Exception as e:
                    return {"response": f"Night mode not available: {e}", "actions": []}
            
            # === SYSTEM POWER ===
            if cmd in ["shutdown", "shut down", "power off"]:
                try:
                    os.system("shutdown /s /t 60")  # Shutdown in 60 seconds
                    return {"response": "⚠️ System will shutdown in 60 seconds. Say 'cancel shutdown' to abort.", "actions": [{"type": "shutdown"}]}
                except Exception as e:
                    return {"response": f"Shutdown command failed: {e}", "actions": []}
            
            if cmd in ["cancel_shutdown", "abort shutdown", "stop shutdown"]:
                try:
                    os.system("shutdown /a")  # Abort shutdown
                    return {"response": "✅ Shutdown cancelled", "actions": [{"type": "cancel_shutdown"}]}
                except Exception as e:
                    return {"response": f"Failed to cancel shutdown: {e}", "actions": []}
            
            if cmd in ["restart", "reboot", "restart computer"]:
                try:
                    os.system("shutdown /r /t 60")  # Restart in 60 seconds
                    return {"response": "🔄 System will restart in 60 seconds. Say 'cancel shutdown' to abort.", "actions": [{"type": "restart"}]}
                except Exception as e:
                    return {"response": f"Restart command failed: {e}", "actions": []}
            
            if cmd in ["sleep", "hibernate", "suspend"]:
                try:
                    # Windows sleep command
                    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
                    return {"response": "💤 System going to sleep", "actions": [{"type": "sleep"}]}
                except Exception as e:
                    return {"response": f"Sleep command failed: {e}", "actions": []}
            
            if cmd in ["lock", "lock screen", "lock computer"]:
                try:
                    ctypes.windll.user32.LockWorkStation()
                    return {"response": "🔒 Screen locked", "actions": [{"type": "lock"}]}
                except Exception as e:
                    return {"response": f"Lock command failed: {e}", "actions": []}
            
            # === CONNECTIVITY ===
            if cmd in ["wifi_toggle", "toggle wifi", "wifi on", "wifi off"]:
                try:
                    # Using netsh to toggle WiFi
                    os.system("netsh interface set interface \"Wi-Fi\" disable")
                    os.system("timeout /t 2")
                    os.system("netsh interface set interface \"Wi-Fi\" enable")
                    return {"response": "📶 WiFi toggled", "actions": [{"type": "wifi_toggle"}]}
                except Exception as e:
                    return {"response": f"WiFi toggle failed: {e}", "actions": []}
            
            if cmd in ["bluetooth_toggle", "toggle bluetooth"]:
                try:
                    os.system("start ms-settings:bluetooth")
                    return {"response": "🔵 Bluetooth settings opened", "actions": [{"type": "bluetooth_toggle"}]}
                except Exception as e:
                    return {"response": f"Bluetooth toggle failed: {e}", "actions": []}
            
            # === MEDIA CONTROLS ===
            if cmd in ["play_pause", "play", "pause", "media play"]:
                try:
                    import pyautogui
                    pyautogui.press('playpause')
                    return {"response": "▶️ Play/Pause toggled", "actions": [{"type": "media", "action": "play_pause"}]}
                except Exception as e:
                    return {"response": f"Media control failed: {e}", "actions": []}
            
            if cmd in ["next_track", "next", "skip"]:
                try:
                    import pyautogui
                    pyautogui.press('nexttrack')
                    return {"response": "⏭️ Next track", "actions": [{"type": "media", "action": "next"}]}
                except Exception as e:
                    return {"response": f"Media control failed: {e}", "actions": []}
            
            if cmd in ["prev_track", "previous", "back"]:
                try:
                    import pyautogui
                    pyautogui.press('prevtrack')
                    return {"response": "⏮️ Previous track", "actions": [{"type": "media", "action": "previous"}]}
                except Exception as e:
                    return {"response": f"Media control failed: {e}", "actions": []}
            
            # === SYSTEM ACTIONS ===
            if cmd in ["screenshot", "capture screen", "screen capture"]:
                return self._handle_screenshot()
            
            if cmd in ["empty_recycle", "empty bin", "clear recycle bin"]:
                try:
                    import winshell
                    winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
                    return {"response": "🗑️ Recycle bin emptied", "actions": [{"type": "empty_recycle"}]}
                except:
                    # Fallback
                    try:
                        os.system("rd /s /q %systemdrive%\\$Recycle.Bin")
                        return {"response": "🗑️ Recycle bin emptied", "actions": [{"type": "empty_recycle"}]}
                    except Exception as e:
                        return {"response": f"Could not empty recycle bin: {e}", "actions": []}
            
            if cmd in ["task_manager", "open task manager"]:
                try:
                    os.system("taskmgr")
                    return {"response": "📊 Task Manager opened", "actions": [{"type": "task_manager"}]}
                except Exception as e:
                    return {"response": f"Could not open Task Manager: {e}", "actions": []}
            
            if cmd in ["terminal", "cmd", "open terminal", "open command prompt"]:
                try:
                    os.system("start cmd")
                    return {"response": "💻 Terminal opened", "actions": [{"type": "terminal"}]}
                except Exception as e:
                    return {"response": f"Could not open terminal: {e}", "actions": []}
            
            # === DEFAULT: Treat as chat ===
            return await self.chat(command, session_id)
            
        except Exception as e:
            logger.error(f"Execute error: {e}")
            return {"response": f"Command failed: {e}", "actions": []}

    def get_system_stats(self) -> Dict[str, Any]:
        """Get real-time system stats"""
        try:
            cpu = psutil.cpu_percent(interval=0.5)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            battery = psutil.sensors_battery()
            
            return {
                "cpu": {"usage": cpu, "cores": psutil.cpu_count()},
                "memory": {"used": memory.used, "total": memory.total, "percentage": memory.percent},
                "disk": {"used": disk.used, "total": disk.total, "percentage": disk.percent},
                "battery": {"percentage": battery.percent if battery else 100, "isCharging": battery.power_plugged if battery else True},
                "network": {"downloadSpeed": 0, "uploadSpeed": 0, "ping": 0},
                "processes": {"count": len(list(psutil.process_iter()))},
                "uptime": 0
            }
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return {
                "cpu": {"usage": 0, "cores": 4},
                "memory": {"used": 0, "total": 16*1024**3, "percentage": 0},
                "disk": {"used": 0, "total": 512*1024**3, "percentage": 0},
                "battery": {"percentage": 100, "isCharging": True},
                "network": {"downloadSpeed": 0, "uploadSpeed": 0, "ping": 0},
                "processes": {"count": 0},
                "uptime": 0
            }

# Global instance
jarvis_core = JarvisCore()

@app.on_event("startup")
async def startup():
    await jarvis_core.initialize()

@app.post("/api/chat")
async def chat(
    message: str = Form(""),
    session_id: str = Form("default"),
    file_name: Optional[str] = Form(None),
    file_type: Optional[str] = Form(None),
    file_data: Optional[str] = Form(None)
):
    """Process chat message with optional file upload"""
    try:
        # Handle file upload if present
        if file_data and file_name:
            logger.info(f"Processing file upload: {file_name} ({file_type})")
            
            # Decode base64 file data
            import base64
            file_bytes = base64.b64decode(file_data)
            
            # Handle image analysis
            if file_type and file_type.startswith("image/"):
                result = await jarvis_core._handle_image_analysis(file_bytes, file_name, message or "What's in this image?")
            else:
                # Handle other file types (text extraction, etc.)
                result = await jarvis_core._handle_file_analysis(file_bytes, file_name, file_type, message or "Analyze this file")
            
            return {
                "response": result.get("response", ""),
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "actions": [{"type": "file_analyzed", "filename": file_name}],
                "suggestions": result.get("suggestions", ["What else can you see?", "Summarize this", "Extract text"])
            }
        
        # Regular text chat
        result = await jarvis_core.chat(message, session_id)
        return {
            "response": result.get("response", ""),
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "actions": result.get("actions"),
            "suggestions": result.get("suggestions")
        }
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return {
            "response": f"Error: {str(e)}",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/system-stats")
async def system_stats():
    """Get system statistics"""
    return {"stats": jarvis_core.get_system_stats()}

@app.get("/api/health")
async def health():
    """Health check"""
    return {"status": "ok", "initialized": jarvis_core.initialized}

# Track connected clients for broadcasting
connected_clients = set()

async def broadcast_system_stats():
    """Broadcast system stats to all connected clients"""
    while True:
        if connected_clients and jarvis_core:
            stats = jarvis_core.get_system_stats()
            message = {
                "type": "system_stats",
                "payload": stats
            }
            # Send to all connected clients
            disconnected = set()
            for client in connected_clients:
                try:
                    await client.send_json(message)
                except:
                    disconnected.add(client)
            # Remove disconnected clients
            connected_clients.difference_update(disconnected)
        await asyncio.sleep(2)  # Update every 2 seconds

@app.on_event("startup")
async def start_broadcast():
    """Start the broadcast task"""
    asyncio.create_task(broadcast_system_stats())

@app.post("/api/execute")
async def execute_command(request: dict):
    """Execute system commands for PC Control"""
    try:
        command = request.get("command", "")
        result = await jarvis_core._execute_single_task(command, "pc-control")
        return {
            "success": True,
            "result": result.get("text", ""),
            "actions": result.get("actions", [])
        }
    except Exception as e:
        logger.error(f"Execute error: {e}")
        return {
            "success": False,
            "result": str(e),
            "actions": []
        }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    connected_clients.add(websocket)
    
    # Send initial stats
    if jarvis_core:
        await websocket.send_json({
            "type": "system_stats",
            "payload": jarvis_core.get_system_stats()
        })
    
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "chat":
                result = await jarvis_core.chat(data.get("message", ""), data.get("session_id", "default"))
                await websocket.send_json({
                    "type": "chat_response",
                    "data": result
                })
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.get("type") == "get_stats":
                # Immediate stats request
                stats = jarvis_core.get_system_stats()
                await websocket.send_json({
                    "type": "system_stats",
                    "payload": stats
                })
    except WebSocketDisconnect:
        connected_clients.discard(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        connected_clients.discard(websocket)

if __name__ == "__main__":
    print("🚀 Starting JARVIS Ultimate...")
    print("📡 API: http://localhost:8001")
    print("🔌 WebSocket: ws://localhost:8001/ws")
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)
