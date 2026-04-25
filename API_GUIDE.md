# 🚀 JARVIS Ultimate - Real API Guide

## 📋 Quick Setup

1. Copy `.env.example` to `.env`
2. Add your FREE API keys
3. Restart JARVIS backend
4. Test endpoints at `http://localhost:8001/docs`

---

## 🎯 APIs That Work WITHOUT Keys (Instant!)

| API | Endpoint | Description |
|-----|----------|-------------|
| 💰 Crypto Prices | `/api/real/crypto?coin=bitcoin` | Live BTC, ETH prices |
| 🔥 Trending Crypto | `/api/real/crypto/trending` | Top 5 trending |
| 🔍 Web Search | `/api/real/web-search?query=AI` | DuckDuckGo search |
| 🗣️ TTS | `/api/real/tts?text=Hello&lang=hi` | Hindi/English speech |
| 🌐 Translate | `/api/real/translate?text=hello&target=hi` | 100+ languages |
| 🖼️ Image Gen | `/api/real/image/generate?prompt=cat` | AI image generation |
| 📍 Location | `/api/real/location` | Your location via IP |
| 🗺️ Geocode | `/api/real/geocode?address=Mumbai` | Address to lat/long |
| 🔢 Number Facts | `/api/real/fact/number?number=42` | Fun number facts |
| 🎭 Useless Facts | `/api/real/fact/useless` | Random facts |
| 💬 Quotes | `/api/real/quote` | Daily inspiration |
| 😂 Jokes | `/api/real/joke?category=Programming` | Programming jokes |
| 📷 QR Code | `/api/real/qr?data=wifi-password` | Generate QR |

---

## 🔑 APIs That Need Keys (FREE Tier)

### 🌤️ Weather - OpenWeatherMap
```bash
# Get key: https://home.openweathermap.org/api_keys (FREE)
GET /api/real/weather?city=Mumbai
GET /api/real/weather/forecast?city=Delhi&days=3
```

### 📰 News - NewsAPI
```bash
# Get key: https://newsapi.org/register (100 req/day FREE)
GET /api/real/news?category=technology&country=in
GET /api/real/news?query=artificial+intelligence
```

### 📈 Stocks - Alpha Vantage
```bash
# Get key: https://www.alphavantage.co/support/#api-key (25 req/day FREE)
GET /api/real/stock?symbol=AAPL      # Apple
GET /api/real/stock?symbol=RELIANCE  # Reliance (use Yahoo symbol)
```

### 🎵 YouTube
```bash
# Get key: https://console.cloud.google.com/apis/credentials (10K quota/day FREE)
GET /api/real/youtube?query=lofi+music&max_results=5
```

### 🎙️ Premium TTS - ElevenLabs
```bash
# Get key: https://elevenlabs.io (10K chars/month FREE)
GET /api/real/tts/elevenlabs?text=Hello+world
```

### 🤖 Extra AI - OpenRouter
```bash
# Get key: https://openrouter.ai/keys (200 credits/day FREE)
GET /api/real/openrouter?prompt=Explain+AI&model=openai/gpt-3.5-turbo

# Available models:
# - openai/gpt-3.5-turbo (FREE)
# - meta-llama/llama-3-70b-instruct (FREE)
# - mistralai/mixtral-8x7b-instruct (FREE)
```

### 🧠 Google Gemini
```bash
# Get key: https://makersuite.google.com/app/apikey (60 req/min FREE)
GET /api/real/gemini?prompt=Explain+quantum+computing
```

### 📧 Email - Resend
```bash
# Get key: https://resend.com/api-keys (100 emails/day FREE)
POST /api/real/email/send?to=user@example.com&subject=Hello&body=Message
```

---

## 🎯 Smart Combined Endpoints

### Daily Brief (Weather + News + Quote + Crypto)
```bash
GET /api/real/daily-brief?city=Mumbai

Response:
{
  "date": "2024-01-15 Monday",
  "location": "Mumbai",
  "weather": { "temperature": 28, "condition": "sunny" },
  "headlines": [...],
  "quote": { "text": "...", "author": "..." },
  "crypto_trending": [...]
}
```

### Smart Search (Web + YouTube)
```bash
GET /api/real/smart-search?query=Python+tutorial
```

---

## 💡 Usage Examples

### 1. Check Bitcoin Price (NO KEY!)
```bash
curl http://localhost:8001/api/real/crypto?coin=bitcoin
```

### 2. Translate to Hindi (NO KEY!)
```bash
curl "http://localhost:8001/api/real/translate?text=Hello+world&target=hi"
```

### 3. Generate AI Image (NO KEY!)
```bash
curl "http://localhost:8001/api/real/image/generate?prompt=futuristic+city&width=1024&height=1024"
```

### 4. Get Weather (NEEDS KEY)
```bash
# First: Add OPENWEATHER_API_KEY to .env
curl http://localhost:8001/api/real/weather?city=Delhi
```

### 5. Search YouTube (NEEDS KEY)
```bash
# First: Add YOUTUBE_API_KEY to .env
curl "http://localhost:8001/api/real/youtube?query=programming+tutorial&max_results=3"
```

---

## 🌐 All Endpoints List

### AI (4)
- `GET /api/real/openrouter` - Multi-model AI
- `GET /api/real/gemini` - Google Gemini
- `GET /api/ai/generate-image` - Pollinations AI
- `GET /api/real/tts/elevenlabs` - Premium voices

### Weather (2)
- `GET /api/real/weather` - Current weather
- `GET /api/real/weather/forecast` - 5-day forecast

### News (1)
- `GET /api/real/news` - Top headlines

### Finance (3)
- `GET /api/real/crypto` - Crypto prices
- `GET /api/real/crypto/trending` - Trending coins
- `GET /api/real/stock` - Stock prices

### Media (1)
- `GET /api/real/youtube` - Video search

### TTS (2)
- `GET /api/real/tts` - Google TTS (free)
- `GET /api/real/tts/elevenlabs` - AI voices

### Translation (1)
- `GET /api/real/translate` - 100+ languages

### Search (2)
- `GET /api/real/web-search` - DuckDuckGo
- `GET /api/real/google-search` - SerpAPI

### Images (2)
- `GET /api/real/image/generate` - AI generation
- `GET /api/real/image/unsplash` - Stock photos

### Fun (4)
- `GET /api/real/fact/number` - Number facts
- `GET /api/real/fact/useless` - Random facts
- `GET /api/real/quote` - Quotes
- `GET /api/real/joke` - Jokes

### Location (2)
- `GET /api/real/location` - IP geolocation
- `GET /api/real/geocode` - Address lookup

### Email (1)
- `POST /api/real/email/send` - Send emails

### Games (1)
- `GET /api/real/games/search` - Game database

### Utility (1)
- `GET /api/real/qr` - QR generator

### Combined (2)
- `GET /api/real/daily-brief` - Full daily update
- `GET /api/real/smart-search` - Multi-platform search

---

## 📊 API Free Tiers Summary

| API | Free Tier | Key Required |
|-----|-----------|--------------|
| CoinGecko | Unlimited | ❌ No |
| DuckDuckGo | Unlimited | ❌ No |
| Google TTS | Unlimited | ❌ No |
| Google Translate | Unlimited | ❌ No |
| Pollinations AI | Unlimited | ❌ No |
| Numbers API | Unlimited | ❌ No |
| JokeAPI | Unlimited | ❌ No |
| IP Geolocation | Unlimited | ❌ No |
| OpenStreetMap | Unlimited | ❌ No |
| Quote Garden | Unlimited | ❌ No |
| OpenWeatherMap | 60/min | ✅ Yes |
| NewsAPI | 100/day | ✅ Yes |
| Alpha Vantage | 25/day | ✅ Yes |
| YouTube API | 10K/day | ✅ Yes |
| ElevenLabs | 10K chars/month | ✅ Yes |
| OpenRouter | 200 credits/day | ✅ Yes |
| Gemini | 60 req/min | ✅ Yes |
| Resend | 100 emails/day | ✅ Yes |
| SerpAPI | 100/month | ✅ Yes |
| RAWG | 20K/month | ✅ Yes |

---

## 🚀 Quick Start Commands

```bash
# 1. Install dependencies (if not done)
pip install requests gtts googletrans duckduckgo-search qrcode pillow
pip install python-dotenv google-generativeai  # Optional

# 2. Create .env file
copy .env.example .env

# 3. Add at least these keys to .env:
# OPENWEATHER_API_KEY=your_key
# NEWSAPI_KEY=your_key
# YOUTUBE_API_KEY=your_key

# 4. Start JARVIS
python app.py

# 5. Test in browser:
# http://localhost:8001/api/real/crypto?coin=bitcoin
# http://localhost:8001/api/real/weather?city=Mumbai
```

---

## 🎉 That's 30+ Real APIs!

**Features without keys:** 15 APIs ready instantly!
**Features with keys:** 15 more APIs with free signup!

Total: **30 real API endpoints** ready to use! 🔥
