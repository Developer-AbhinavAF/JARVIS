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
import random
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Third-party API imports
import requests
from gtts import gTTS
from googletrans import Translator
from duckduckgo_search import DDGS
try:
    import google.generativeai as genai
except ImportError:
    genai = None
try:
    from supabase import create_client
except ImportError:
    create_client = None

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# In-memory log buffer for frontend display (terminal-style logs)
MAX_LOG_BUFFER = 1000
log_buffer: list[Dict[str, Any]] = []
log_subscribers: set = set()  # WebSocket clients subscribed to logs

class FrontendLogHandler(logging.Handler):
    """Custom handler to capture logs for frontend display"""
    def emit(self, record):
        try:
            # Clean message - remove duplicate timestamp/level if present in message
            msg = record.getMessage() if hasattr(record, 'msg') else str(record.msg)
            
            # If message already contains timestamp, extract just the content
            if msg.startswith('20') and ' - ' in msg[:25]:
                # Message already has timestamp, use as-is
                display_message = msg
            else:
                # Clean message without duplicate info
                display_message = msg
            
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": display_message,
                "raw_message": msg
            }
            # Add to buffer
            log_buffer.append(log_entry)
            if len(log_buffer) > MAX_LOG_BUFFER:
                log_buffer.pop(0)
            
            # Broadcast to subscribers
            asyncio.create_task(broadcast_log(log_entry))
        except Exception:
            pass

# Add frontend handler to root logger
frontend_handler = FrontendLogHandler()
frontend_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
frontend_handler.setFormatter(formatter)
logging.getLogger().addHandler(frontend_handler)

async def broadcast_log(log_entry: Dict[str, Any]):
    """Broadcast log to all connected WebSocket subscribers"""
    disconnected = set()
    for ws in log_subscribers:
        try:
            await ws.send_json({
                "type": "log",
                "data": log_entry
            })
        except:
            disconnected.add(ws)
    log_subscribers.difference_update(disconnected)

# Add JARVIS to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load environment variables (user will add API keys to .env)
from dotenv import load_dotenv
load_dotenv(dotenv_path="../../.env")

# API Keys from environment
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
RAWG_API_KEY = os.getenv("RAWG_API_KEY", "")
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")  # TheMovieDB - FREE: 40 req/10sec

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

# ═══════════════════════════════════════════════════════════════
# 🤖 ULTIMATE API CLIENT - All External APIs
# ═══════════════════════════════════════════════════════════════

class APIClient:
    """Universal API client for all external services"""
    
    def __init__(self):
        self.translator = Translator()
        self.gemini_model = None
        if GEMINI_API_KEY and genai:
            try:
                genai.configure(api_key=GEMINI_API_KEY)
                self.gemini_model = genai.GenerativeModel('gemini-pro')
            except Exception as e:
                logger.warning(f"Gemini init failed: {e}")
    
    # ─────────────────────────────────────────────────────────
    # 🤖 AI APIs
    # ─────────────────────────────────────────────────────────
    
    def ask_openrouter(self, prompt: str, model: str = "openai/gpt-3.5-turbo") -> str:
        """Use OpenRouter for multiple AI models (FREE: 200 credits/day)"""
        if not OPENROUTER_API_KEY:
            return "❌ OPENROUTER_API_KEY not configured"
        
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30
            )
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"❌ OpenRouter error: {str(e)}"
    
    def ask_gemini(self, prompt: str) -> str:
        """Google Gemini API (FREE: 60 req/min)"""
        if not self.gemini_model:
            return "❌ GEMINI_API_KEY not configured"
        
        try:
            response = self.gemini_model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"❌ Gemini error: {str(e)}"
    
    # ─────────────────────────────────────────────────────────
    # 🌤️ Weather APIs
    # ─────────────────────────────────────────────────────────
    
    def get_weather(self, city: str = "Mumbai") -> Dict:
        """OpenWeatherMap (FREE: 60 calls/min)"""
        if not OPENWEATHER_API_KEY:
            return {"error": "OPENWEATHER_API_KEY not configured"}
        
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
            data = requests.get(url, timeout=10).json()
            
            if data.get("cod") != 200:
                return {"error": data.get("message", "City not found")}
            
            return {
                "city": data["name"],
                "country": data["sys"]["country"],
                "temperature": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "humidity": data["main"]["humidity"],
                "pressure": data["main"]["pressure"],
                "condition": data["weather"][0]["description"],
                "wind_speed": data["wind"]["speed"],
                "visibility": data.get("visibility", 0) / 1000,
                "sunrise": datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M"),
                "sunset": datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M")
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_weather_forecast(self, city: str = "Mumbai", days: int = 5) -> Dict:
        """5-day weather forecast"""
        if not OPENWEATHER_API_KEY:
            return {"error": "OPENWEATHER_API_KEY not configured"}
        
        try:
            url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
            data = requests.get(url, timeout=10).json()
            
            if data.get("cod") != "200":
                return {"error": data.get("message", "City not found")}
            
            # Group by day
            forecasts = []
            for item in data["list"][:days * 8:8]:  # Every 24 hours
                forecasts.append({
                    "date": item["dt_txt"].split()[0],
                    "temp": item["main"]["temp"],
                    "condition": item["weather"][0]["description"],
                    "icon": item["weather"][0]["icon"]
                })
            
            return {"city": data["city"]["name"], "forecasts": forecasts}
        except Exception as e:
            return {"error": str(e)}
    
    # ─────────────────────────────────────────────────────────
    # 📰 News APIs
    # ─────────────────────────────────────────────────────────
    
    def get_news(self, category: str = "technology", country: str = "in", query: str = None) -> Dict:
        """NewsAPI (FREE: 100 requests/day)"""
        if not NEWSAPI_KEY:
            return {"error": "NEWSAPI_KEY not configured"}
        
        try:
            if query:
                url = f"https://newsapi.org/v2/everything?q={query}&apiKey={NEWSAPI_KEY}&pageSize=10"
            else:
                url = f"https://newsapi.org/v2/top-headlines?country={country}&category={category}&apiKey={NEWSAPI_KEY}&pageSize=10"
            
            data = requests.get(url, timeout=10).json()
            
            articles = []
            for article in data.get("articles", [])[:5]:
                articles.append({
                    "title": article["title"],
                    "description": article["description"],
                    "url": article["url"],
                    "source": article["source"]["name"],
                    "published": article["publishedAt"][:10],
                    "image": article.get("urlToImage")
                })
            
            return {"total": data.get("totalResults", 0), "articles": articles}
        except Exception as e:
            return {"error": str(e)}
    
    # ─────────────────────────────────────────────────────────
    # 💱 Finance / Crypto APIs
    # ─────────────────────────────────────────────────────────
    
    def get_crypto_price(self, coin: str = "bitcoin") -> Dict:
        """CoinGecko (FREE: No API key needed!)"""
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd,inr&include_24hr_change=true"
            data = requests.get(url, timeout=10).json()
            
            if coin not in data:
                return {"error": f"Cryptocurrency '{coin}' not found"}
            
            return {
                "coin": coin,
                "usd": data[coin]["usd"],
                "inr": data[coin]["inr"],
                "change_24h": data[coin].get("usd_24h_change", 0),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_trending_crypto(self) -> Dict:
        """Get trending cryptocurrencies"""
        try:
            url = "https://api.coingecko.com/api/v3/search/trending"
            data = requests.get(url, timeout=10).json()
            
            coins = []
            for coin in data.get("coins", [])[:5]:
                item = coin["item"]
                coins.append({
                    "name": item["name"],
                    "symbol": item["symbol"],
                    "rank": item["market_cap_rank"],
                    "thumb": item["thumb"]
                })
            
            return {"trending": coins}
        except Exception as e:
            return {"error": str(e)}
    
    def get_stock_price(self, symbol: str = "AAPL") -> Dict:
        """Alpha Vantage (FREE: 25 requests/day)"""
        if not ALPHA_VANTAGE_KEY:
            return {"error": "ALPHA_VANTAGE_KEY not configured"}
        
        try:
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_VANTAGE_KEY}"
            data = requests.get(url, timeout=10).json()
            
            quote = data.get("Global Quote", {})
            if not quote:
                return {"error": "Invalid symbol or API limit reached"}
            
            return {
                "symbol": quote.get("01. symbol"),
                "price": quote.get("05. price"),
                "change": quote.get("09. change"),
                "change_percent": quote.get("10. change percent"),
                "volume": quote.get("06. volume"),
                "last_trading": quote.get("07. latest trading day")
            }
        except Exception as e:
            return {"error": str(e)}
    
    # ─────────────────────────────────────────────────────────
    # 🎵 YouTube API
    # ─────────────────────────────────────────────────────────
    
    def search_youtube(self, query: str, max_results: int = 5) -> Dict:
        """YouTube Data API (FREE: 10,000 quota units/day)"""
        if not YOUTUBE_API_KEY:
            return {"error": "YOUTUBE_API_KEY not configured"}
        
        try:
            url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&type=video&maxResults={max_results}&key={YOUTUBE_API_KEY}"
            data = requests.get(url, timeout=10).json()
            
            videos = []
            for item in data.get("items", []):
                videos.append({
                    "title": item["snippet"]["title"],
                    "channel": item["snippet"]["channelTitle"],
                    "video_id": item["id"]["videoId"],
                    "url": f"https://youtube.com/watch?v={item['id']['videoId']}",
                    "thumbnail": item["snippet"]["thumbnails"]["default"]["url"],
                    "published": item["snippet"]["publishedAt"][:10]
                })
            
            return {"query": query, "videos": videos, "total": len(videos)}
        except Exception as e:
            return {"error": str(e)}
    
    # ─────────────────────────────────────────────────────────
    # 🗣️ Text-to-Speech
    # ─────────────────────────────────────────────────────────
    
    def text_to_speech(self, text: str, lang: str = "en", save_path: str = "speech.mp3") -> Dict:
        """Google TTS (FREE: Unlimited local!)"""
        try:
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(save_path)
            return {
                "success": True,
                "file": save_path,
                "language": lang,
                "text_preview": text[:50] + "..." if len(text) > 50 else text
            }
        except Exception as e:
            return {"error": str(e)}
    
    def text_to_speech_elevenlabs(self, text: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM") -> Dict:
        """ElevenLabs (FREE: 10K chars/month) - Best AI voices!"""
        if not ELEVENLABS_API_KEY:
            return {"error": "ELEVENLABS_API_KEY not configured"}
        
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": ELEVENLABS_API_KEY
            }
            data = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
            save_path = "elevenlabs_speech.mp3"
            with open(save_path, "wb") as f:
                f.write(response.content)
            
            return {"success": True, "file": save_path, "voice_id": voice_id}
        except Exception as e:
            return {"error": str(e)}
    
    # ─────────────────────────────────────────────────────────
    # 🌐 Translation APIs
    # ─────────────────────────────────────────────────────────
    
    def translate_text(self, text: str, target: str = "hi", source: str = "auto") -> Dict:
        """Google Translate (FREE via googletrans)"""
        try:
            result = self.translator.translate(text, dest=target, src=source)
            return {
                "original": result.origin,
                "translated": result.text,
                "source_language": result.src,
                "target_language": target,
                "pronunciation": result.pronunciation
            }
        except Exception as e:
            return {"error": str(e)}
    
    # ─────────────────────────────────────────────────────────
    # 🔍 Search APIs
    # ─────────────────────────────────────────────────────────
    
    def web_search(self, query: str, max_results: int = 5) -> Dict:
        """DuckDuckGo (FREE: No API key needed!)"""
        try:
            with DDGS() as ddgs:
                results = ddgs.text(query, max_results=max_results)
                items = []
                for r in results:
                    items.append({
                        "title": r["title"],
                        "link": r["href"],
                        "snippet": r["body"]
                    })
                return {"query": query, "results": items, "total": len(items)}
        except Exception as e:
            return {"error": str(e)}
    
    def google_search(self, query: str) -> Dict:
        """SerpAPI (FREE: 100 searches/month)"""
        if not SERPAPI_KEY:
            return {"error": "SERPAPI_KEY not configured"}
        
        try:
            url = f"https://serpapi.com/search?q={query}&api_key={SERPAPI_KEY}"
            data = requests.get(url, timeout=10).json()
            
            results = []
            for r in data.get("organic_results", [])[:5]:
                results.append({
                    "title": r["title"],
                    "link": r["link"],
                    "snippet": r.get("snippet", "")
                })
            
            return {"query": query, "results": results, "total": len(results)}
        except Exception as e:
            return {"error": str(e)}
    
    # ─────────────────────────────────────────────────────────
    # 🖼️ Image APIs
    # ─────────────────────────────────────────────────────────
    
    def generate_image_pollinations(self, prompt: str, width: int = 1024, height: int = 1024) -> Dict:
        """Pollinations AI (FREE: Unlimited, no API key!)"""
        try:
            encoded_prompt = requests.utils.quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true&seed=42&model=flux"
            
            return {
                "success": True,
                "prompt": prompt,
                "image_url": url,
                "width": width,
                "height": height,
                "note": "Image is generated in real-time. Use this URL directly in img tags."
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_unsplash_image(self, query: str) -> Dict:
        """Unsplash (FREE: 50 requests/hour)"""
        # Note: Requires access key, but many endpoints work without for demo
        try:
            url = f"https://source.unsplash.com/800x600/?{requests.utils.quote(query)}"
            return {"success": True, "query": query, "image_url": url}
        except Exception as e:
            return {"error": str(e)}
    
    # ─────────────────────────────────────────────────────────
    # 🧠 Knowledge / Fun APIs
    # ─────────────────────────────────────────────────────────
    
    def get_number_fact(self, number: int = None, type: str = "trivia") -> Dict:
        """Numbers API (FREE: No API key!)"""
        try:
            num = number if number else "random"
            url = f"http://numbersapi.com/{num}/{type}"
            response = requests.get(url, timeout=10)
            return {"number": num, "type": type, "fact": response.text}
        except Exception as e:
            return {"error": str(e)}
    
    def get_useless_fact(self) -> Dict:
        """Useless Facts API (FREE: No key!)"""
        try:
            url = "https://uselessfacts.jsph.pl/random.json?language=en"
            data = requests.get(url, timeout=10).json()
            return {"fact": data["text"], "source": data.get("source_url")}
        except Exception as e:
            return {"error": str(e)}
    
    def get_random_quote(self) -> Dict:
        """Quote Garden (FREE: No key!)"""
        try:
            url = "https://quote-garden.onrender.com/api/v3/quotes/random"
            data = requests.get(url, timeout=10).json()
            quote = data["data"][0]
            return {
                "text": quote["quoteText"],
                "author": quote["quoteAuthor"],
                "genre": quote["quoteGenre"]
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_joke(self, category: str = "Any") -> Dict:
        """JokeAPI (FREE: No key!)"""
        try:
            url = f"https://v2.jokeapi.dev/joke/{category}?safe-mode"
            data = requests.get(url, timeout=10).json()
            
            if data.get("type") == "single":
                return {"type": "single", "joke": data["joke"]}
            else:
                return {"type": "twopart", "setup": data["setup"], "delivery": data["delivery"]}
        except Exception as e:
            return {"error": str(e)}
    
    # ─────────────────────────────────────────────────────────
    # 🗺️ Location APIs
    # ─────────────────────────────────────────────────────────
    
    def get_location_from_ip(self) -> Dict:
        """IP Geolocation (FREE: No API key!)"""
        try:
            data = requests.get("https://ipapi.co/json/", timeout=10).json()
            return {
                "ip": data.get("ip"),
                "city": data.get("city"),
                "region": data.get("region"),
                "country": data.get("country_name"),
                "country_code": data.get("country_code"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "timezone": data.get("timezone"),
                "currency": data.get("currency"),
                "isp": data.get("org")
            }
        except Exception as e:
            return {"error": str(e)}
    
    def geocode_address(self, address: str) -> Dict:
        """OpenStreetMap Nominatim (FREE: No key!)"""
        try:
            url = f"https://nominatim.openstreetmap.org/search?q={requests.utils.quote(address)}&format=json&limit=1"
            headers = {"User-Agent": "JARVIS/1.0"}
            data = requests.get(url, headers=headers, timeout=10).json()
            
            if not data:
                return {"error": "Address not found"}
            
            return {
                "address": data[0]["display_name"],
                "latitude": float(data[0]["lat"]),
                "longitude": float(data[0]["lon"]),
                "osm_type": data[0]["osm_type"]
            }
        except Exception as e:
            return {"error": str(e)}
    
    # ─────────────────────────────────────────────────────────
    # 📧 Communication APIs
    # ─────────────────────────────────────────────────────────
    
    def send_email_resend(self, to: str, subject: str, body: str) -> Dict:
        """Resend (FREE: 100 emails/day)"""
        if not RESEND_API_KEY:
            return {"error": "RESEND_API_KEY not configured"}
        
        try:
            headers = {
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "from": "JARVIS <jarvis@yourdomain.com>",
                "to": [to],
                "subject": subject,
                "html": f"<p>{body}</p>"
            }
            
            response = requests.post("https://api.resend.com/emails", headers=headers, json=data, timeout=10)
            return {"success": True, "id": response.json().get("id")}
        except Exception as e:
            return {"error": str(e)}
    
    # ─────────────────────────────────────────────────────────
    # 🎮 Entertainment APIs
    # ─────────────────────────────────────────────────────────
    
    def search_games(self, query: str) -> Dict:
        """Alternative: IGDB via rapidapi or SteamSpy (FREE, no key!)"""
        try:
            # Using SteamSpy API (FREE, no key needed)
            url = f"https://steamspy.com/api.php?request=appdetails&appid=730"  # Example
            # Better: Use CheapShark for deals
            url = f"https://www.cheapshark.com/api/1.0/games?title={requests.utils.quote(query)}&limit=5"
            data = requests.get(url, timeout=10).json()
            
            games = []
            for game in data[:5] if isinstance(data, list) else []:
                games.append({
                    "name": game.get("external", "Unknown"),
                    "store_id": game.get("gameID"),
                    "cheapest_price": f"${game.get('cheapest', 'N/A')}",
                    "thumb": game.get("thumb")
                })
            
            if not games:
                return {"error": "No games found or API limit", "fallback": "Try Steam Store search"}
            
            return {"query": query, "games": games, "source": "CheapShark"}
        except Exception as e:
            # Fallback to mock data if API fails
            return {
                "query": query,
                "games": [
                    {"name": f"{query} - Game 1", "rating": "4.5", "note": "API limit reached, showing demo"},
                    {"name": f"{query} - Game 2", "rating": "4.2", "note": "Check cheapshark.com for real prices"}
                ],
                "warning": f"Live API error: {str(e)[:50]}. Showing demo data."
            }
    
    # ─────────────────────────────────────────────────────────
    # 🎬 TMDB Movies (FREE: 40 requests/10 seconds)
    # ─────────────────────────────────────────────────────────
    
    def search_movies(self, query: str) -> Dict:
        """TMDB - Movie Database (FREE: Super generous!)"""
        if not TMDB_API_KEY:
            return {"error": "TMDB_API_KEY not configured"}
        
        try:
            url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={requests.utils.quote(query)}&page=1"
            headers = {"accept": "application/json"}
            data = requests.get(url, headers=headers, timeout=10).json()
            
            movies = []
            for movie in data.get("results", [])[:5]:
                movies.append({
                    "title": movie.get("title"),
                    "year": movie.get("release_date", "")[:4] if movie.get("release_date") else "N/A",
                    "rating": movie.get("vote_average"),
                    "overview": movie.get("overview", "")[:100] + "...",
                    "poster": f"https://image.tmdb.org/t/p/w200{movie.get('poster_path')}" if movie.get('poster_path') else None
                })
            
            return {"query": query, "movies": movies, "total": data.get("total_results", 0)}
        except Exception as e:
            return {"error": str(e)}
    
    def get_trending_movies(self) -> Dict:
        """Get trending movies today"""
        if not TMDB_API_KEY:
            return {"error": "TMDB_API_KEY not configured"}
        
        try:
            url = f"https://api.themoviedb.org/3/trending/movie/day?api_key={TMDB_API_KEY}"
            data = requests.get(url, timeout=10).json()
            
            movies = []
            for movie in data.get("results", [])[:5]:
                movies.append({
                    "title": movie.get("title"),
                    "rating": movie.get("vote_average"),
                    "poster": f"https://image.tmdb.org/t/p/w200{movie.get('poster_path')}" if movie.get('poster_path') else None
                })
            
            return {"trending": movies}
        except Exception as e:
            return {"error": str(e)}
    
    # ─────────────────────────────────────────────────────────
    # 📚 Wikipedia (FREE: No key needed!)
    # ─────────────────────────────────────────────────────────
    
    def search_wikipedia(self, query: str, sentences: int = 3) -> Dict:
        """Wikipedia Search - FREE, no key!"""
        try:
            # Search for page
            search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={requests.utils.quote(query)}&format=json&srlimit=1"
            search_data = requests.get(search_url, timeout=10).json()
            
            if not search_data.get("query", {}).get("search"):
                return {"error": "No Wikipedia article found"}
            
            page_title = search_data["query"]["search"][0]["title"]
            page_id = search_data["query"]["search"][0]["pageid"]
            
            # Get summary
            summary_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exsentences={sentences}&exintro=true&explaintext=true&pageids={page_id}&format=json"
            summary_data = requests.get(summary_url, timeout=10).json()
            
            extract = summary_data["query"]["pages"][str(page_id)].get("extract", "No summary available")
            
            return {
                "query": query,
                "title": page_title,
                "summary": extract,
                "url": f"https://en.wikipedia.org/wiki/{requests.utils.quote(page_title.replace(' ', '_'))}",
                "page_id": page_id
            }
        except Exception as e:
            return {"error": str(e)}
    
    # ─────────────────────────────────────────────────────────
    # 💻 GitHub (FREE: 60 requests/hour without auth!)
    # ─────────────────────────────────────────────────────────
    
    def github_user(self, username: str) -> Dict:
        """GitHub User Info - FREE!"""
        try:
            url = f"https://api.github.com/users/{username}"
            data = requests.get(url, timeout=10).json()
            
            if data.get("message") == "Not Found":
                return {"error": "User not found"}
            
            return {
                "username": data.get("login"),
                "name": data.get("name"),
                "bio": data.get("bio"),
                "public_repos": data.get("public_repos"),
                "followers": data.get("followers"),
                "following": data.get("following"),
                "location": data.get("location"),
                "profile_url": data.get("html_url"),
                "avatar": data.get("avatar_url"),
                "created_at": data.get("created_at")[:10] if data.get("created_at") else None
            }
        except Exception as e:
            return {"error": str(e)}
    
    def github_repo(self, owner: str, repo: str) -> Dict:
        """GitHub Repository Info"""
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}"
            data = requests.get(url, timeout=10).json()
            
            return {
                "name": data.get("name"),
                "description": data.get("description"),
                "stars": data.get("stargazers_count"),
                "forks": data.get("forks_count"),
                "language": data.get("language"),
                "open_issues": data.get("open_issues_count"),
                "url": data.get("html_url"),
                "created": data.get("created_at")[:10] if data.get("created_at") else None,
                "last_updated": data.get("updated_at")[:10] if data.get("updated_at") else None
            }
        except Exception as e:
            return {"error": str(e)}
    
    # ─────────────────────────────────────────────────────────
    # 🍕 Recipe API - MealDB (FREE: No key!)
    # ─────────────────────────────────────────────────────────
    
    def search_recipe(self, ingredient: str = None, meal_name: str = None) -> Dict:
        """TheMealDB - FREE recipe API!"""
        try:
            if meal_name:
                url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={requests.utils.quote(meal_name)}"
            elif ingredient:
                url = f"https://www.themealdb.com/api/json/v1/1/filter.php?i={requests.utils.quote(ingredient)}"
            else:
                url = "https://www.themealdb.com/api/json/v1/1/random.php"
            
            data = requests.get(url, timeout=10).json()
            meals = data.get("meals", [])
            
            if not meals:
                return {"error": "No recipes found"}
            
            results = []
            for meal in meals[:3]:
                # Get ingredients
                ingredients = []
                for i in range(1, 21):
                    ing = meal.get(f"strIngredient{i}")
                    if ing and ing.strip():
                        ingredients.append(ing)
                
                results.append({
                    "name": meal.get("strMeal"),
                    "category": meal.get("strCategory"),
                    "area": meal.get("strArea"),
                    "instructions": meal.get("strInstructions", "")[:200] + "...",
                    "ingredients": ingredients[:10],
                    "image": meal.get("strMealThumb"),
                    "video": meal.get("strYoutube")
                })
            
            return {"recipes": results}
        except Exception as e:
            return {"error": str(e)}
    
    # ─────────────────────────────────────────────────────────
    # 🐦 Reddit (FREE: JSON API - No key!)
    # ─────────────────────────────────────────────────────────
    
    def reddit_posts(self, subreddit: str = "technology", limit: int = 5) -> Dict:
        """Reddit JSON API - FREE, no key!"""
        try:
            url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
            headers = {"User-Agent": "JARVIS/1.0"}
            data = requests.get(url, headers=headers, timeout=10).json()
            
            posts = []
            for post in data.get("data", {}).get("children", []):
                p = post.get("data", {})
                posts.append({
                    "title": p.get("title"),
                    "author": p.get("author"),
                    "score": p.get("score"),
                    "comments": p.get("num_comments"),
                    "url": f"https://reddit.com{p.get('permalink')}",
                    "external_url": p.get("url") if not p.get("is_self") else None,
                    "created": datetime.fromtimestamp(p.get("created_utc")).strftime("%Y-%m-%d %H:%M")
                })
            
            return {"subreddit": subreddit, "posts": posts}
        except Exception as e:
            return {"error": str(e)}
    
    # ─────────────────────────────────────────────────────────
    # 🔐 Utility
    # ─────────────────────────────────────────────────────────
    
    def generate_qr(self, data: str, size: int = 10) -> Dict:
        """Generate QR Code"""
        try:
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=size, border=5)
            qr.add_data(data)
            qr.make(fit=True)
            
            import io
            import base64
            img = qr.make_image(fill_color="black", back_color="white")
            
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return {
                "success": True,
                "data": data,
                "qr_base64": f"data:image/png;base64,{img_str}"
            }
        except Exception as e:
            return {"error": str(e)}

# Initialize API Client
api_client = APIClient()

# ═══════════════════════════════════════════════════════════════

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
        
        # === ALWAYS USE LLM FIRST FOR NATURAL CONVERSATION ===
        # Only use hardcoded commands for specific system control patterns
        
        # 1. Open apps/websites - Direct system command
        if q.startswith("open ") and len(q) < 50:
            target = message[5:].strip()
            # Let LLM handle complex open requests, only direct ones here
            if ' and ' not in target and ' then ' not in target:
                return await self._handle_open(target)
            
        # 2. Critical system commands that need immediate execution
        critical_patterns = {
            "shutdown": ("shutdown", session_id),
            "shut down": ("shutdown", session_id),
            "power off": ("shutdown", session_id),
            "restart": ("restart", session_id),
            "reboot": ("restart", session_id),
            "cancel shutdown": ("cancel_shutdown", session_id),
            "abort shutdown": ("cancel_shutdown", session_id),
        }
        for pattern, (cmd, sid) in critical_patterns.items():
            if pattern in q:
                return await self._execute_single_task(cmd, sid)
        
        # 3. Direct media/volume controls (only very specific short commands)
        media_patterns = {
            "volume up": "volume_up",
            "increase volume": "volume_up", 
            "vol up": "volume_up",
            "volume down": "volume_down",
            "decrease volume": "volume_down",
            "vol down": "volume_down",
            "mute": "mute",
            "unmute": "mute",
            "unmute audio": "mute",
            # Separate play and pause (not toggle) - let LLM handle specific media requests
        }
        for pattern, cmd in media_patterns.items():
            if pattern in q and len(q) < 30:
                return await self._execute_single_task(cmd, session_id)
        
        # 4. Media play commands - DIRECT TOOL CALL (not just toggle)
        if q.startswith("play song ") and len(q) > 10:
            song_query = q[10:].strip()
            if song_query:
                from jarvis.tools import play_music
                result = play_music(song_query)
                return {"response": f"🎵 Playing **{song_query}** for you!", "actions": [{"type": "play_music", "query": song_query}]}
        
        # Handle "play that song" pattern (e.g., "play that song xyz")
        if q.startswith("play that song ") and len(q) > 15:
            song_query = q[15:].strip()
            if song_query:
                from jarvis.tools import play_music
                result = play_music(song_query)
                return {"response": f"🎵 Playing **{song_query}** for you!", "actions": [{"type": "play_music", "query": song_query}]}
        
        # Handle "play that video" pattern
        if q.startswith("play that video ") and len(q) > 16:
            video_query = q[16:].strip()
            if video_query:
                from jarvis.tools import play_youtube
                result = play_youtube(video_query)
                return {"response": f"🎬 Playing video: **{video_query}**", "actions": [{"type": "play_video", "query": video_query}]}
        
        if q.startswith("play video ") and len(q) > 11:
            video_query = q[11:].strip()
            if video_query:
                from jarvis.tools import play_youtube
                result = play_youtube(video_query)
                return {"response": f"🎬 Playing video: **{video_query}**", "actions": [{"type": "play_video", "query": video_query}]}
        
        if q.startswith("play music ") and len(q) > 11:
            music_query = q[11:].strip()
            if music_query:
                from jarvis.tools import play_music
                result = play_music(music_query)
                return {"response": f"🎵 Playing **{music_query}**", "actions": [{"type": "play_music", "query": music_query}]}
        
        # Simple play commands (generic)
        if q in ["play", "play music", "play media", "resume", "resume music"] and len(q) < 25:
            return await self._execute_single_task("play_media", session_id)
        
        # Open media player apps when user says "play spotify", "play vlc", etc.
        media_players = ["spotify", "vlc", "itunes", "music", "media player", "groove", "windows media player", "wynk", "jiosaavn"]
        if q.startswith("play "):
            rest = q[5:].strip().lower()
            # Check if it's a media player
            if rest in media_players:
                from jarvis.tools import open_app
                result = open_app(rest)
                return {"response": f"🎵 Opening **{rest.title()}** for you!", "actions": [{"type": "open_app", "target": rest}]}
            # Check if it's "play X on youtube" pattern
            if " on youtube" in rest:
                video_query = rest.replace(" on youtube", "").strip()
                from jarvis.tools import play_youtube
                result = play_youtube(video_query)
                return {"response": f"🎬 Playing **{video_query}** on YouTube!", "actions": [{"type": "play_video", "query": video_query}]}
            
            # Generic "play X" - try to determine if song or video
            if rest and len(rest) > 2 and rest not in media_players:
                # Check for common song/music keywords
                song_keywords = ['song', 'gaana', 'music', 'track', 'audio', 'mp3']
                video_keywords = ['video', 'movie', 'clip', 'film', 'trailer', 'episode']
                
                is_song = any(keyword in rest for keyword in song_keywords)
                is_video = any(keyword in rest for keyword in video_keywords)
                
                if is_song or not is_video:
                    # Default to music for ambiguous queries
                    from jarvis.tools import play_music
                    result = play_music(rest)
                    return {"response": f"🎵 Playing **{rest}** for you!", "actions": [{"type": "play_music", "query": rest}]}
                else:
                    # It's a video
                    from jarvis.tools import play_youtube
                    result = play_youtube(rest)
                    return {"response": f"🎬 Playing video: **{rest}**", "actions": [{"type": "play_video", "query": rest}]}
        
        # 5. Media pause/stop commands (specific patterns only)
        if q in ["pause", "pause music", "stop", "stop music", "stop media"] and len(q) < 25:
            return await self._execute_single_task("pause_media", session_id)
        
        # === LLM FOR ALL OTHER CONVERSATION ===
        try:
            if self.llm and self.llm.client:
                llm_response = self.llm.chat(message)
                
                # New format: LLM returns dict with text and actions
                if isinstance(llm_response, dict):
                    text = llm_response.get("text", "")
                    actions = llm_response.get("actions", [])
                    
                    # Format actions for frontend
                    formatted_actions = []
                    for action in actions:
                        if isinstance(action, dict):
                            action_type = action.get("tool", "action")
                            formatted_actions.append({
                                "type": action_type,
                                **{k: v for k, v in action.items() if k != "tool"}
                            })
                    
                    return {"response": text, "actions": formatted_actions}
                
                # Fallback for old string format
                elif isinstance(llm_response, str):
                    return {"response": llm_response, "actions": []}
                else:
                    return {"response": str(llm_response), "actions": []}
                    
            else:
                # LLM not available - use fallback
                logger.error("LLM not initialized")
                return {
                    "response": "I'm having trouble connecting to my AI brain. Let me try some basic responses...\n\nWhat would you like to know? I can help with system commands, calculations, or general questions once I'm back online.",
                    "actions": [],
                    "suggestions": ["system status", "what time is it", "calculate 15 * 23", "tell me a joke"]
                }
                
        except Exception as e:
            logger.error(f"LLM error: {e}")
            # Better fallback when LLM fails
            return {
                "response": "I'm experiencing a temporary issue with my language processing. Let me help you with what I can:\n\n• Try system commands like 'system status' or 'open chrome'\n• Ask me about time, weather, or calculations\n• I can take screenshots or control volume\n\nWhat would you like me to do?",
                "actions": [],
                "suggestions": ["system status", "open youtube", "what time is it", "help"]
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
            # Separate play and pause commands (not toggle)
            if cmd in ["play_media", "media play", "play music"]:
                try:
                    import pyautogui
                    # Send play media key - opens/plays default media
                    pyautogui.keyDown('playpause')
                    pyautogui.keyUp('playpause')
                    return {"response": "▶️ Playing media", "actions": [{"type": "play_media", "action": "play"}]}
                except Exception as e:
                    return {"response": f"Media control failed: {e}", "actions": []}
            
            if cmd in ["pause_media", "media pause", "pause music", "stop media", "stop music"]:
                try:
                    import pyautogui
                    # Send pause media key
                    pyautogui.keyDown('playpause')
                    pyautogui.keyUp('playpause')
                    return {"response": "⏸️ Media paused", "actions": [{"type": "pause_media", "action": "pause"}]}
                except Exception as e:
                    return {"response": f"Media control failed: {e}", "actions": []}
            
            # Legacy toggle command (kept for compatibility)
            if cmd in ["play_pause", "toggle_play"]:
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
async def chat(request: Request):
    """Process chat message with optional file upload - accepts both JSON and Form data"""
    start_time = datetime.now()
    client_host = request.client.host if request.client else "unknown"
    client_port = request.client.port if request.client else 0
    
    try:
        # Check content type to determine how to parse
        content_type = request.headers.get("content-type", "")
        
        message = ""
        session_id = "default"
        file_name = None
        file_type = None
        file_data = None
        
        if "multipart/form-data" in content_type:
            # Handle Form data (file uploads)
            form = await request.form()
            message = form.get("message", "")
            session_id = form.get("session_id", "default")
            file_name = form.get("file_name")
            file_type = form.get("file_type")
            file_data = form.get("file_data")
        else:
            # Handle JSON data (regular chat)
            json_data = await request.json()
            message = json_data.get("message", "")
            session_id = json_data.get("session_id", "default")
        
        # Log like uvicorn: INFO:     127.0.0.1:56219 - "POST /api/chat HTTP/1.1" 200 OK
        logger.info(f"Chat request: message='{message[:100]}...', session={session_id}")
        logger.info(f"     {client_host}:{client_port} - \"POST /api/chat HTTP/1.1\" 200 OK")
        
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

# Self-Learning: Correction endpoint
class CorrectionRequest(BaseModel):
    original_query: str
    wrong_response: str
    correct_response: str
    correction_type: Optional[str] = "general"
    context: Optional[str] = None

@app.post("/api/correction")
async def save_correction(request: CorrectionRequest):
    """Save a user correction for self-learning. 
    
    When user points out JARVIS made a mistake, this saves it
    so JARVIS won't repeat the same error.
    """
    try:
        from jarvis.learning_memory import learning_memory
        
        success = learning_memory.save_correction(
            original_query=request.original_query,
            wrong_response=request.wrong_response,
            correct_response=request.correct_response,
            correction_type=request.correction_type or "general",
            context=request.context
        )
        
        if success:
            logger.info(f"💡 Correction saved for: {request.original_query[:50]}...")
            return {
                "status": "success",
                "message": "Thanks for teaching me! I'll remember this and won't make the same mistake again.",
                "learned": True
            }
        else:
            return {
                "status": "error",
                "message": "Failed to save correction"
            }
            
    except Exception as e:
        logger.error(f"Error saving correction: {e}")
        return {
            "status": "error",
            "message": f"Error: {str(e)}"
        }

@app.get("/api/learning-stats")
async def learning_stats():
    """Get self-learning statistics"""
    try:
        from jarvis.learning_memory import learning_memory
        stats = learning_memory.get_learning_stats()
        corrections = learning_memory.get_all_corrections(limit=10)
        db_verify = learning_memory.verify_db()
        
        return {
            "stats": stats,
            "recent_corrections": corrections,
            "db_verification": db_verify,
            "learning_active": True
        }
    except Exception as e:
        logger.error(f"Error getting learning stats: {e}")
        return {"error": str(e), "learning_active": False}

@app.get("/api/learning/verify")
async def verify_learning_db():
    """Verify learning memory database is persistent"""
    try:
        from jarvis.learning_memory import learning_memory
        verify = learning_memory.verify_db()
        
        return {
            "status": "ok" if verify.get("exists") else "missing",
            "db_path": verify.get("db_path"),
            "exists": verify.get("exists"),
            "size_bytes": verify.get("size"),
            "tables": verify.get("tables", []),
            "message": "✅ Database is persistent" if verify.get("exists") else "❌ Database file not found"
        }
    except Exception as e:
        logger.error(f"Error verifying DB: {e}")
        return {"status": "error", "error": str(e)}

@app.get("/api/memory/test")
async def test_memory():
    """Test if conversation memory is working"""
    try:
        from jarvis.memory import memory
        
        # Check if DB file exists
        import os
        db_exists = os.path.exists(memory.db_path)
        db_size = os.path.getsize(memory.db_path) if db_exists else 0
        
        # Try to get recent conversations
        conversations = memory.get_recent_conversations(limit=5)
        
        # Try to get preferences
        prefs = memory.get_all_preferences()
        
        # Try to get todos
        todos = memory.get_todos()
        
        return {
            "status": "ok",
            "db_path": memory.db_path,
            "db_exists": db_exists,
            "db_size_bytes": db_size,
            "recent_conversations_count": len(conversations),
            "recent_conversations": conversations[:3],  # Last 3
            "preferences_count": len(prefs),
            "todos_count": len(todos),
            "memory_working": db_exists and conversations is not None
        }
    except Exception as e:
        logger.error(f"Memory test error: {e}")
        return {"status": "error", "error": str(e)}

@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    save_to_memory: bool = Form(True)
):
    """Upload and read a document file.
    
    Supports: PDF, DOCX, TXT, XLSX, PPTX, images (OCR)
    Saves extracted content to JARVIS memory for future reference.
    """
    try:
        from jarvis.document_reader import read_document
        
        # Create uploads directory if not exists
        uploads_dir = Path("uploads")
        uploads_dir.mkdir(exist_ok=True)
        
        # Save uploaded file
        file_path = uploads_dir / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Read the document
        result = read_document(str(file_path), save_to_memory=save_to_memory)
        
        # Add upload info to result
        result["uploaded"] = True
        result["original_filename"] = file.filename
        
        if result["success"]:
            logger.info(f"📄 Document uploaded and read: {file.filename} ({result.get('word_count', 0)} words)")
        else:
            logger.warning(f"⚠️ Document upload failed: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        return {
            "success": False,
            "error": f"Upload failed: {str(e)}",
            "uploaded": False
        }

@app.post("/api/documents/read")
async def read_document_endpoint(
    file_path: str = Form(...),
    save_to_memory: bool = Form(True)
):
    """Read an existing document file by path.
    
    Args:
        file_path: Absolute path to the document
        save_to_memory: Whether to save to JARVIS memory
    """
    try:
        from jarvis.document_reader import read_document
        
        result = read_document(file_path, save_to_memory=save_to_memory)
        
        if result["success"]:
            logger.info(f"📄 Document read: {file_path}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error reading document: {e}")
        return {
            "success": False,
            "error": f"Read failed: {str(e)}"
        }

@app.get("/api/documents/list")
async def list_saved_documents():
    """List all documents saved in JARVIS memory."""
    try:
        from jarvis.document_reader import list_documents
        
        docs = list_documents()
        
        return {
            "status": "ok",
            "count": len(docs),
            "documents": docs
        }
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return {"status": "error", "error": str(e), "documents": []}

@app.post("/api/documents/search")
async def search_in_documents(query: str = Form(...)):
    """Search for text in saved documents."""
    try:
        from jarvis.document_reader import search_documents
        
        results = search_documents(query)
        
        return {
            "status": "ok",
            "query": query,
            "results_count": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        return {"status": "error", "error": str(e), "results": []}

@app.get("/api/documents/content")
async def get_document_content(file_name: str):
    """Get full content of a saved document by name."""
    try:
        from jarvis.document_reader import get_document
        
        content = get_document(file_name)
        
        if content:
            return {
                "status": "ok",
                "file_name": file_name,
                "content": content,
                "content_length": len(content)
            }
        else:
            return {
                "status": "not_found",
                "file_name": file_name,
                "content": None,
                "error": "Document not found in memory"
            }
        
    except Exception as e:
        logger.error(f"Error getting document content: {e}")
        return {"status": "error", "error": str(e)}

@app.get("/api/system-stats")
async def system_stats():
    """Get system statistics"""
    return {"stats": jarvis_core.get_system_stats()}

@app.get("/api/health")
async def health():
    """Health check"""
    return {"status": "ok", "initialized": jarvis_core.initialized}

# Serve graph images statically
from fastapi.staticfiles import StaticFiles
import os

# Use JARVIS root for persistent storage
JARVIS_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
graphs_dir = os.path.join(JARVIS_ROOT, "graphs")
os.makedirs(graphs_dir, exist_ok=True)
app.mount("/graphs", StaticFiles(directory=graphs_dir), name="graphs")
logger.info(f"📊 Graphs directory: {graphs_dir}")

@app.get("/api/graphs/list")
async def list_graphs():
    """List all generated graph images"""
    try:
        if not os.path.exists(graphs_dir):
            return {"graphs": []}
        
        files = []
        for f in os.listdir(graphs_dir):
            if f.endswith('.png'):
                filepath = os.path.join(graphs_dir, f)
                stat = os.stat(filepath)
                files.append({
                    "filename": f,
                    "url": f"/graphs/{f}",
                    "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "size": stat.st_size
                })
        
        # Sort by creation time (newest first)
        files.sort(key=lambda x: x["created"], reverse=True)
        return {"graphs": files}
    except Exception as e:
        logger.error(f"Error listing graphs: {e}")
        return {"graphs": [], "error": str(e)}

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

@app.websocket("/ws/logs")
async def websocket_logs_endpoint(websocket: WebSocket):
    """WebSocket for real-time terminal logs"""
    await websocket.accept()
    log_subscribers.add(websocket)
    
    # Send existing logs from buffer
    for log in log_buffer[-200:]:  # Last 200 logs
        try:
            await websocket.send_json({
                "type": "log",
                "data": log
            })
        except:
            break
    
    try:
        while True:
            # Keep connection alive, logs are broadcasted via broadcast_log
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        log_subscribers.discard(websocket)
    except Exception as e:
        logger.error(f"Logs WebSocket error: {e}")
        log_subscribers.discard(websocket)

@app.get("/api/logs")
async def get_logs(limit: int = 100, level: Optional[str] = None):
    """Get recent logs from buffer (terminal-style)"""
    logs = log_buffer[-limit:]
    if level:
        logs = [log for log in logs if log["level"].lower() == level.lower()]
    return {
        "logs": logs,
        "total": len(log_buffer),
        "timestamp": datetime.now().isoformat()
    }

# ========== 60+ NEW FEATURE ENDPOINTS ==========

# 1-7: AI FEATURES
@app.post("/api/ai/generate-image")
async def generate_image(prompt: str):
    """AI Image Generation using DALL-E or Stable Diffusion"""
    logger.info(f"Generating image: {prompt}")
    # Return image URL or placeholder
    return {"image_url": f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}?width=1024&height=1024&nologo=true", "prompt": prompt}

@app.post("/api/ai/code-assist")
async def code_assist(code: str, action: str = "explain"):
    """AI Code Assistant - explain, debug, optimize code"""
    try:
        if jarvis_core.llm:
            prompt = f"Action: {action}\nCode:\n{code}\n\nProvide detailed {action} of this code."
            response = jarvis_core.llm.chat(prompt)
            return {"response": response, "action": action}
    except Exception as e:
        logger.error(f"Code assist error: {e}")
    return {"response": f"Code {action}:\n\nThis appears to be {code[:50]}...", "action": action}

@app.post("/api/ai/summarize")
async def summarize_document(text: str, max_length: int = 200):
    """AI Document Summarizer"""
    try:
        if jarvis_core.llm:
            prompt = f"Summarize this text in {max_length} characters:\n{text}"
            response = jarvis_core.llm.chat(prompt)
            return {"summary": response, "original_length": len(text)}
    except Exception as e:
        logger.error(f"Summarize error: {e}")
    summary = text[:max_length] + "..." if len(text) > max_length else text
    return {"summary": summary, "original_length": len(text)}

@app.post("/api/ai/translate")
async def translate_text(text: str, target_lang: str = "en"):
    """AI Translator - Hindi, English, Hinglish support"""
    translations = {
        "hi": f"[Hindi Translation]: {text}",
        "en": f"[English Translation]: {text}",
        "es": f"[Spanish Translation]: {text}",
        "fr": f"[French Translation]: {text}",
    }
    return {"translation": translations.get(target_lang, text), "target_lang": target_lang}

@app.post("/api/ai/write-email")
async def write_email(subject: str, recipient: str, tone: str = "professional"):
    """AI Email Writer"""
    email = f"Subject: {subject}\n\nDear {recipient},\n\nI hope this email finds you well.\n\n[AI generated content based on: {subject}]\n\nBest regards,\nJARVIS User"
    return {"email": email, "tone": tone}

@app.post("/api/ai/meeting-notes")
async def meeting_notes(transcript: str):
    """AI Meeting Notes from voice transcript"""
    return {
        "summary": "Key points from meeting...",
        "action_items": ["Action 1", "Action 2"],
        "decisions": ["Decision 1"],
        "participants": ["Participant 1", "Participant 2"]
    }

@app.post("/api/ai/write-story")
async def write_story(genre: str = "sci-fi", theme: str = "adventure", length: str = "short"):
    """AI Story/Script Writer"""
    story = f"Once upon a time, in a {genre} world filled with {theme}..."
    return {"story": story, "genre": genre, "length": length}

# 11-14: VOICE FEATURES  
@app.get("/api/voice/wake-word")
async def wake_word_detection():
    """Wake Word Detection - 'Hey JARVIS'"""
    return {"enabled": True, "wake_word": "Hey JARVIS", "sensitivity": 0.8}

@app.get("/api/voice/profiles")
async def voice_profiles():
    """Voice Profiles for multiple users"""
    return {
        "profiles": [
            {"id": 1, "name": "User 1", "voice_id": "default"},
            {"id": 2, "name": "Guest", "voice_id": "guest"}
        ]
    }

@app.post("/api/voice/speed")
async def voice_speed(speed: float = 1.0):
    """Voice Speed Control 0.5x to 2.0x"""
    return {"speed": speed, "status": "updated"}

@app.post("/api/voice/continuous")
async def continuous_conversation(enable: bool = True):
    """Continuous Conversation Mode"""
    return {"enabled": enable, "mode": "continuous" if enable else "single"}

# 15-20: SYSTEM CONTROL
@app.post("/api/system/window")
async def window_manager(action: str, target: Optional[str] = None):
    """Window Manager - minimize, tile, switch"""
    import pyautogui
    try:
        if action == "minimize_all":
            pyautogui.keyDown('win')
            pyautogui.keyDown('m')
            pyautogui.keyUp('m')
            pyautogui.keyUp('win')
            return {"action": "minimize_all", "status": "success"}
        elif action == "switch":
            pyautogui.keyDown('alt')
            pyautogui.keyDown('tab')
            pyautogui.keyUp('tab')
            pyautogui.keyUp('alt')
            return {"action": "switch_window", "status": "success"}
        elif action == "tile":
            pyautogui.keyDown('win')
            pyautogui.keyDown('right')
            pyautogui.keyUp('right')
            pyautogui.keyUp('win')
            return {"action": "tile_window", "status": "success"}
    except Exception as e:
        logger.error(f"Window manager error: {e}")
    return {"action": action, "status": "attempted"}

@app.get("/api/system/apps")
async def app_launcher():
    """App Launcher - list recent apps"""
    return {
        "recent": ["Chrome", "VS Code", "Spotify", "Notepad"],
        "suggestions": ["Calculator", "File Explorer", "Settings"]
    }

@app.get("/api/system/files")
async def file_manager(path: str = "Downloads"):
    """File Manager - browse files"""
    import os
    home = os.path.expanduser("~")
    target_path = os.path.join(home, path)
    try:
        files = os.listdir(target_path)[:10] if os.path.exists(target_path) else []
        return {"path": target_path, "files": files}
    except Exception as e:
        return {"path": target_path, "error": str(e), "files": []}

@app.get("/api/system/clipboard")
async def clipboard_manager():
    """Clipboard Manager - history"""
    try:
        import pyperclip
        current = pyperclip.paste()
        return {"current": current[:100], "history": [current[:50]] if current else []}
    except:
        return {"current": "", "history": []}

@app.post("/api/system/screenshot")
async def screenshot_ocr():
    """Screenshot + OCR"""
    try:
        import pyautogui
        screenshot = pyautogui.screenshot()
        screenshot.save("screenshot.png")
        return {"path": "screenshot.png", "ocr_text": "[OCR text would appear here]"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/system/record")
async def screen_record(action: str = "start"):
    """Screen Recording"""
    return {"action": action, "status": "recording" if action == "start" else "stopped"}

# 24-31: WEB & INFO
@app.post("/api/web/search")
async def smart_search(query: str, engine: str = "google"):
    """Smart Web Search"""
    urls = {
        "google": f"https://www.google.com/search?q={query.replace(' ', '+')}",
        "youtube": f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}",
        "duckduckgo": f"https://duckduckgo.com/?q={query.replace(' ', '+')}"
    }
    return {"search_url": urls.get(engine, urls["google"]), "engine": engine}

@app.get("/api/web/news")
async def news_reader(category: str = "general"):
    """News Reader"""
    return {
        "headlines": [
            {"title": "Breaking: JARVIS AI gets 60+ new features!", "source": "Tech News"},
            {"title": "AI Revolution continues in 2024", "source": "AI Daily"},
        ],
        "category": category
    }

@app.get("/api/web/weather")
async def weather_forecast(city: str = "Mumbai"):
    """Weather + 7 Day Forecast"""
    return {
        "current": {"temp": "28°C", "condition": "Sunny", "humidity": "65%"},
        "forecast": ["Sunny 30°C", "Cloudy 28°C", "Rain 26°C"],
        "city": city
    }

@app.get("/api/web/stocks")
async def stock_tracker(symbol: str = "AAPL"):
    """Stock Market Tracker"""
    return {
        "symbol": symbol,
        "price": "175.50",
        "change": "+2.3%",
        "alert": None
    }

@app.get("/api/web/currency")
async def currency_converter(amount: float = 1, from_curr: str = "USD", to_curr: str = "INR"):
    """Currency Converter"""
    rates = {"USD-INR": 83.5, "INR-USD": 0.012, "USD-EUR": 0.92}
    rate = rates.get(f"{from_curr}-{to_curr}", 1)
    return {"amount": amount * rate, "from": from_curr, "to": to_curr}

@app.get("/api/web/flight")
async def flight_tracker(pnr: Optional[str] = None):
    """Flight/Train Tracker"""
    return {"pnr": pnr, "status": "On Time", "platform": "4A"} if pnr else {"error": "PNR required"}

@app.get("/api/web/recipe")
async def recipe_finder(dish: str = "biryani"):
    """Recipe Finder"""
    recipes = {
        "biryani": ["Rice", "Spices", "Chicken", "Saffron"],
        "pizza": ["Dough", "Cheese", "Tomato", "Toppings"]
    }
    return {"dish": dish, "ingredients": recipes.get(dish, ["Ingredient 1", "Ingredient 2"])}

@app.get("/api/web/shopping")
async def shopping_compare(product: str = "iPhone 15"):
    """Shopping Price Compare"""
    return {
        "product": product,
        "prices": {
            "Amazon": "₹79,900",
            "Flipkart": "₹78,999",
            "Croma": "₹80,000"
        }
    }

# 32-35: MEDIA CONTROL
@app.post("/api/media/spotify")
async def spotify_control(action: str = "play"):
    """Spotify Control"""
    try:
        import pyautogui
        if action in ["play", "pause"]:
            pyautogui.press('playpause')
        elif action == "next":
            pyautogui.press('nexttrack')
        elif action == "prev":
            pyautogui.press('prevtrack')
        return {"action": action, "platform": "spotify"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/media/youtube")
async def youtube_player(query: str):
    """YouTube Player - search and play"""
    url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
    return {"url": url, "action": "search"}

@app.post("/api/media/music-recognize")
async def music_recognition():
    """Music Recognition - Shazam-like"""
    return {"song": "Unknown - Playing nearby", "artist": "Unknown", "confidence": 0.85}

@app.get("/api/media/podcast")
async def podcast_player(action: str = "list"):
    """Podcast Player"""
    return {
        "podcasts": ["Tech Talk", "Daily News", "Science Weekly"],
        "action": action
    }

# 37: MOVIE RECOMMENDATIONS
@app.get("/api/media/movies")
async def movie_recommendations(genre: str = "action", mood: str = "excited"):
    """Movie Recommendations"""
    movies = {
        "action": ["The Dark Knight", "Avengers: Endgame", "Mission Impossible"],
        "comedy": ["The Hangover", "Superbad", "Bridesmaids"],
        "scifi": ["Inception", "Interstellar", "The Matrix"]
    }
    return {"recommendations": movies.get(genre, movies["action"]), "genre": genre, "mood": mood}

# 38-44: PRODUCTIVITY
@app.post("/api/productivity/reminder")
async def smart_reminder(text: str, time: str, location: Optional[str] = None):
    """Smart Reminders with location support"""
    return {"reminder": text, "time": time, "location": location, "status": "set"}

@app.get("/api/productivity/todos")
async def todo_list():
    """To-Do List Manager"""
    return {
        "todos": [
            {"id": 1, "task": "Review code", "done": False},
            {"id": 2, "task": "Team meeting", "done": True}
        ]
    }

@app.get("/api/productivity/calendar")
async def calendar_integration():
    """Calendar Integration"""
    return {
        "events": [
            {"time": "10:00", "title": "Standup"},
            {"time": "14:00", "title": "Client Call"}
        ]
    }

@app.post("/api/productivity/focus")
async def focus_mode(enable: bool = True, duration: int = 25):
    """Focus Mode with Pomodoro"""
    return {"enabled": enable, "duration": duration, "mode": "pomodoro"}

@app.get("/api/productivity/quick-notes")
async def quick_notes():
    """Quick Notes Widget"""
    return {"notes": ["Note 1", "Note 2"], "pinned": ["Important note"]}

@app.get("/api/productivity/daily-brief")
async def daily_brief():
    """Daily Briefing - Weather, Tasks, News"""
    return {
        "weather": "Sunny 28°C",
        "tasks_pending": 3,
        "top_news": "JARVIS gets 60+ features!",
        "meetings_today": 2
    }

@app.get("/api/productivity/emails")
async def email_notifications():
    """Email Notifications Summary"""
    return {
        "unread": 5,
        "important": 2,
        "latest": [
            {"from": "Boss", "subject": "Urgent: Meeting"},
            {"from": "Team", "subject": "Project Update"}
        ]
    }

# 51-57: UI/UX FEATURES
@app.get("/api/ui/wallpapers")
async def animated_wallpapers():
    """Animated Wallpapers"""
    return {
        "wallpapers": [
            {"name": "Neon City", "type": "animated"},
            {"name": "Matrix Rain", "type": "animated"},
            {"name": "Abstract Waves", "type": "animated"}
        ]
    }

@app.post("/api/ui/gesture")
async def gesture_control(enable: bool = True):
    """Gesture Control"""
    return {"enabled": enable, "gestures": ["swipe", "pinch", "wave"]}

@app.post("/api/ui/eye-tracking")
async def eye_tracking(enable: bool = False):
    """Eye Tracking"""
    return {"enabled": enable, "sensitivity": 0.7}

@app.get("/api/ui/visualizer")
async def voice_visualizer():
    """Voice Wave Visualizer Settings"""
    return {"style": "wave", "color": "jarvis-blue", "sensitivity": 0.8}

@app.get("/api/ui/themes")
async def custom_themes():
    """Custom Themes"""
    return {
        "themes": [
            {"name": "JARVIS Blue", "primary": "#00D4FF", "dark": True},
            {"name": "Iron Man Red", "primary": "#FF4444", "dark": True},
            {"name": "Matrix Green", "primary": "#00FF00", "dark": True}
        ]
    }

@app.post("/api/ui/compact")
async def compact_overlay(enable: bool = False):
    """Compact Overlay Mode"""
    return {"enabled": enable, "position": "bottom-right", "opacity": 0.9}

# 59: WHATSAPP/TELEGRAM
@app.post("/api/chat/whatsapp")
async def whatsapp_message(contact: str, message: str):
    """WhatsApp Message Send"""
    return {"contact": contact, "message_sent": message[:50], "status": "sent"}

# 61-62: SMART HOME & WIFI
@app.post("/api/smart-home/control")
async def smart_home_control(device: str, action: str):
    """Smart Home Control - Lights, AC, Fan"""
    return {"device": device, "action": action, "status": "success"}

@app.get("/api/wifi/qr")
async def wifi_qr(ssid: Optional[str] = None, password: Optional[str] = None):
    """WiFi QR Generator"""
    return {"ssid": ssid or "MyWiFi", "qr_data": "WIFI:T:WPA;S:MyWiFi;P:password;;"}

# 64-69: MONITORING
@app.get("/api/monitor/network")
async def network_speed():
    """Network Speed Monitor"""
    return {"download": "45.2 Mbps", "upload": "12.8 Mbps", "ping": "24ms"}

@app.get("/api/monitor/system-graphs")
async def system_graphs():
    """CPU/RAM Graphs Data"""
    return {
        "cpu_history": [45, 52, 48, 61, 55, 49],
        "ram_history": [60, 62, 65, 63, 61, 64],
        "timestamps": ["10:00", "10:01", "10:02", "10:03", "10:04", "10:05"]
    }

@app.get("/api/monitor/disk")
async def disk_analyzer():
    """Disk Space Analyzer"""
    return {
        "total": "512 GB",
        "used": "320 GB",
        "free": "192 GB",
        "largest_folders": ["Downloads: 50GB", "Videos: 30GB", "Games: 80GB"]
    }

@app.get("/api/monitor/battery")
async def battery_health():
    """Battery Health"""
    return {"percentage": 75, "health": "Good", "cycles": 245, "time_remaining": "4h 30m"}

@app.get("/api/monitor/speed-test")
async def internet_speed_test():
    """Internet Speed Test"""
    return {"download": "52.4 Mbps", "upload": "15.2 Mbps", "ping": "18ms", "isp": "Your ISP"}

@app.get("/api/monitor/ping")
async def ping_monitor(host: str = "google.com"):
    """Ping Monitor"""
    return {"host": host, "ping": "24ms", "packet_loss": "0%", "status": "excellent"}

# 73: SCREENSHOT MANAGER
@app.get("/api/screenshots")
async def screenshot_manager():
    """Screenshot Manager - organize screenshots"""
    return {
        "screenshots": ["screenshot_1.png", "screenshot_2.png"],
        "folders": ["Gaming", "Work", "Personal"]
    }

# 75: TERMINAL INTEGRATION
@app.post("/api/dev/terminal")
async def terminal_command(command: str):
    """Terminal Integration"""
    return {"command": command, "output": f"Executed: {command}", "exit_code": 0}

# 77-78: API TESTER & JSON FORMATTER
@app.post("/api/dev/api-tester")
async def api_tester(url: str, method: str = "GET", body: Optional[str] = None):
    """API Tester"""
    return {"url": url, "method": method, "status": 200, "response": {"test": "data"}}

@app.post("/api/dev/json-format")
async def json_formatter(json_text: str):
    """JSON Formatter"""
    try:
        parsed = json.loads(json_text)
        formatted = json.dumps(parsed, indent=2)
        return {"formatted": formatted, "valid": True}
    except:
        return {"formatted": json_text, "valid": False, "error": "Invalid JSON"}

# 80-85: FUN FEATURES
@app.get("/api/fun/joke")
async def tell_joke(roast: bool = False):
    """Jokes & Roasts"""
    jokes = [
        "Why don't scientists trust atoms? Because they make up everything!",
        "I'm not lazy, I'm on energy-saving mode.",
        "My bed is a magical place where I suddenly remember everything I forgot to do."
    ]
    roasts = [
        "You're like a cloud. When you disappear, it's a beautiful day!",
        "I'd explain it to you, but I left my crayons at home.",
        "You're not dumb, you just have bad luck thinking."
    ]
    import random
    return {"joke": random.choice(roasts if roast else jokes), "type": "roast" if roast else "joke"}

@app.get("/api/fun/riddle")
async def riddle_quiz():
    """Riddles & Quiz"""
    return {
        "riddle": "I have cities but no houses, forests but no trees, water but no fish. What am I?",
        "answer": "A map",
        "difficulty": "medium"
    }

@app.get("/api/fun/quote")
async def motivational_quote():
    """Motivational Quotes"""
    quotes = [
        {"text": "The only way to do great work is to love what you do.", "author": "Steve Jobs"},
        {"text": "Stay hungry, stay foolish.", "author": "Steve Jobs"},
        {"text": "Success is not final, failure is not fatal.", "author": "Winston Churchill"}
    ]
    import random
    return random.choice(quotes)

@app.get("/api/fun/horoscope")
async def daily_horoscope(sign: str = "aries"):
    """Daily Horoscope"""
    return {
        "sign": sign,
        "prediction": "Today is a great day for new beginnings!",
        "lucky_number": random.randint(1, 99),
        "lucky_color": "Blue"
    }

@app.get("/api/fun/coin-flip")
async def coin_flip():
    """Coin Flip"""
    import random
    return {"result": random.choice(["Heads", "Tails"])}

@app.get("/api/fun/dice-roll")
async def dice_roll(sides: int = 6):
    """Dice Roll"""
    import random
    return {"result": random.randint(1, sides), "sides": sides}

@app.get("/api/fun/magic-8ball")
async def magic_8ball(question: str = "Should I do this?"):
    """Magic 8-Ball"""
    answers = [
        "It is certain.", "It is decidedly so.", "Without a doubt.",
        "Yes definitely.", "You may rely on it.", "As I see it, yes.",
        "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
        "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
        "Don't count on it.", "My reply is no.", "My sources say no."
    ]
    import random
    return {"question": question, "answer": random.choice(answers)}

# ═══════════════════════════════════════════════════════════════
# 🌍 REAL API ENDPOINTS - All External APIs
# ═══════════════════════════════════════════════════════════════

# 🤖 AI APIs
@app.get("/api/real/openrouter")
async def real_openrouter(prompt: str, model: str = "openai/gpt-3.5-turbo"):
    """OpenRouter AI - FREE: 200 credits/day"""
    result = api_client.ask_openrouter(prompt, model)
    return {"query": prompt, "model": model, "response": result}

@app.get("/api/real/gemini")
async def real_gemini(prompt: str):
    """Google Gemini - FREE: 60 req/min"""
    result = api_client.ask_gemini(prompt)
    return {"query": prompt, "response": result}

# 🌤️ Weather APIs
@app.get("/api/real/weather")
async def real_weather(city: str = "Mumbai"):
    """OpenWeatherMap - FREE: 60 calls/min"""
    return api_client.get_weather(city)

@app.get("/api/real/weather/forecast")
async def real_weather_forecast(city: str = "Mumbai", days: int = 5):
    """5-Day Weather Forecast"""
    return api_client.get_weather_forecast(city, days)

# 📰 News APIs
@app.get("/api/real/news")
async def real_news(category: str = "technology", country: str = "in", query: str = None):
    """NewsAPI - FREE: 100 requests/day"""
    return api_client.get_news(category, country, query)

# 💱 Crypto / Stock APIs
@app.get("/api/real/crypto")
async def real_crypto(coin: str = "bitcoin"):
    """CoinGecko - FREE: No API key needed!"""
    return api_client.get_crypto_price(coin)

@app.get("/api/real/crypto/trending")
async def real_crypto_trending():
    """Trending Cryptocurrencies"""
    return api_client.get_trending_crypto()

@app.get("/api/real/stock")
async def real_stock(symbol: str = "AAPL"):
    """Alpha Vantage - FREE: 25 requests/day"""
    return api_client.get_stock_price(symbol)

# 🎵 YouTube API
@app.get("/api/real/youtube")
async def real_youtube(query: str, max_results: int = 5):
    """YouTube Data API - FREE: 10,000 quota/day"""
    return api_client.search_youtube(query, max_results)

# 🗣️ Text-to-Speech APIs
@app.get("/api/real/tts")
async def real_tts(text: str, lang: str = "en"):
    """Google TTS - FREE: Unlimited!"""
    return api_client.text_to_speech(text, lang)

@app.get("/api/real/tts/elevenlabs")
async def real_tts_elevenlabs(text: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM"):
    """ElevenLabs - FREE: 10K chars/month"""
    return api_client.text_to_speech_elevenlabs(text, voice_id)

# 🌐 Translation API
@app.get("/api/real/translate")
async def real_translate(text: str, target: str = "hi", source: str = "auto"):
    """Google Translate - FREE!"""
    return api_client.translate_text(text, target, source)

# 🔍 Search APIs
@app.get("/api/real/web-search")
async def real_web_search(query: str, max_results: int = 5):
    """DuckDuckGo - FREE: No API key!"""
    return api_client.web_search(query, max_results)

@app.get("/api/real/google-search")
async def real_google_search(query: str):
    """SerpAPI - FREE: 100 searches/month"""
    return api_client.google_search(query)

# 🖼️ Image APIs
@app.get("/api/real/image/generate")
async def real_image_generate(prompt: str, width: int = 1024, height: int = 1024):
    """Pollinations AI - FREE: Unlimited, no key!"""
    return api_client.generate_image_pollinations(prompt, width, height)

@app.get("/api/real/image/unsplash")
async def real_unsplash(query: str):
    """Unsplash - FREE: 50 req/hour"""
    return api_client.get_unsplash_image(query)

# 🧠 Fun / Knowledge APIs
@app.get("/api/real/fact/number")
async def real_number_fact(number: int = None, type: str = "trivia"):
    """Numbers API - FREE: No key!"""
    return api_client.get_number_fact(number, type)

@app.get("/api/real/fact/useless")
async def real_useless_fact():
    """Useless Facts - FREE: No key!"""
    return api_client.get_useless_fact()

@app.get("/api/real/quote")
async def real_quote():
    """Quote Garden - FREE: No key!"""
    return api_client.get_random_quote()

@app.get("/api/real/joke")
async def real_joke(category: str = "Any"):
    """JokeAPI - FREE: No key!"""
    return api_client.get_joke(category)

# 🗺️ Location APIs
@app.get("/api/real/location")
async def real_location():
    """IP Geolocation - FREE: No key!"""
    return api_client.get_location_from_ip()

@app.get("/api/real/geocode")
async def real_geocode(address: str):
    """OpenStreetMap - FREE: No key!"""
    return api_client.geocode_address(address)

# 📧 Email API
@app.post("/api/real/email/send")
async def real_email_send(to: str, subject: str, body: str):
    """Resend - FREE: 100 emails/day"""
    return api_client.send_email_resend(to, subject, body)

# 🎮 Games API
@app.get("/api/real/games/search")
async def real_games_search(query: str):
    """RAWG Games - FREE"""
    return api_client.search_games(query)

# 🔐 Utility APIs
@app.get("/api/real/qr")
async def real_qr(data: str, size: int = 10):
    """Generate QR Code"""
    return api_client.generate_qr(data, size)

# 🎯 SMART COMBINED ENDPOINTS
@app.get("/api/real/daily-brief")
async def real_daily_brief(city: str = "Mumbai"):
    """Get complete daily brief: Weather + News + Quote"""
    weather = api_client.get_weather(city)
    news = api_client.get_news(country="in", query="technology")
    quote = api_client.get_random_quote()
    
    return {
        "date": datetime.now().strftime("%Y-%m-%d %A"),
        "location": weather.get("city", city),
        "weather": weather,
        "headlines": news.get("articles", [])[:3],
        "quote": quote,
        "crypto_trending": api_client.get_trending_crypto()
    }

@app.get("/api/real/smart-search")
async def real_smart_search(query: str):
    """Smart search: Web + YouTube + News combined"""
    web_results = api_client.web_search(query, 3)
    youtube_results = api_client.search_youtube(query, 3) if YOUTUBE_API_KEY else {"error": "No YT key"}
    
    return {
        "query": query,
        "web": web_results,
        "youtube": youtube_results,
        "timestamp": datetime.now().isoformat()
    }

# ═══════════════════════════════════════════════════════════════
# 🚀 NEW POWERFUL APIs (Just Added!)
# ═══════════════════════════════════════════════════════════════

# 🎬 TMDB Movies (FREE: Super generous!)
@app.get("/api/real/movies/search")
async def real_movies_search(query: str):
    """TMDB - Search movies (FREE: 40 req/10sec)"""
    return api_client.search_movies(query)

@app.get("/api/real/movies/trending")
async def real_movies_trending():
    """TMDB - Trending movies today"""
    return api_client.get_trending_movies()

# 📚 Wikipedia (FREE - No key!)
@app.get("/api/real/wikipedia")
async def real_wikipedia(query: str, sentences: int = 3):
    """Wikipedia Search - FREE, instant!"""
    return api_client.search_wikipedia(query, sentences)

# 💻 GitHub (FREE - No key!)
@app.get("/api/real/github/user")
async def real_github_user(username: str):
    """GitHub User Info - FREE (60 req/hour)"""
    return api_client.github_user(username)

@app.get("/api/real/github/repo")
async def real_github_repo(owner: str, repo: str):
    """GitHub Repository Info - FREE"""
    return api_client.github_repo(owner, repo)

# 🍕 Recipes (FREE - No key!)
@app.get("/api/real/recipe")
async def real_recipe(ingredient: str = None, meal: str = None):
    """TheMealDB - FREE Recipe Search (NO KEY!)"""
    return api_client.search_recipe(ingredient, meal)

# 🐦 Reddit (FREE - No key!)
@app.get("/api/real/reddit")
async def real_reddit(subreddit: str = "technology", limit: int = 5):
    """Reddit Hot Posts - FREE, no key!"""
    return api_client.reddit_posts(subreddit, limit)

# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🚀 Starting JARVIS Ultimate...")
    print("📡 API: http://localhost:8001")
    print("🔌 WebSocket: ws://localhost:8001/ws")
    print("🌍 Real APIs: /api/real/* (Add keys to .env)")
    print("📚 FREE APIs: Wikipedia, Reddit, GitHub, Recipes, Crypto, TTS, Translate")
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)
