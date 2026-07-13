from __future__ import annotations

import base64
import logging
import time
from dataclasses import dataclass
from typing import Any

try:
    import requests
except ImportError:
    requests = None

from jarvis import config

logger = logging.getLogger(__name__)


@dataclass
class APIResponse:
    provider: str
    ok: bool
    data: Any
    error: str = ""
    cached: bool = False
    latency_ms: float = 0.0


class TTLCache:
    def __init__(self, ttl_seconds: int | None = None, max_items: int = 256) -> None:
        self.ttl_seconds = ttl_seconds or config.API_CACHE_TTL_SECONDS
        self.max_items = max_items
        self._items: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        item = self._items.get(key)
        if not item:
            return None
        created, value = item
        if time.time() - created > self.ttl_seconds:
            self._items.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        if len(self._items) >= self.max_items:
            oldest = min(self._items, key=lambda item: self._items[item][0])
            self._items.pop(oldest, None)
        self._items[key] = (time.time(), value)


class BaseAPIService:
    provider = "base"

    def __init__(self, api_key: str = "", timeout: float | None = None, cache: TTLCache | None = None) -> None:
        self.api_key = (api_key or "").strip()
        self.timeout = timeout or config.API_TIMEOUT_SECONDS
        self.cache = cache or TTLCache()
        self.session = requests.Session() if requests is not None else None

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _missing_key(self) -> APIResponse:
        return APIResponse(self.provider, False, None, f"{self.provider} API key is not configured.")

    def _get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        cache_key: str | None = None,
    ) -> APIResponse:
        key = cache_key or f"GET:{url}:{params}:{headers}"
        cached = self.cache.get(key)
        if cached is not None:
            return APIResponse(self.provider, True, cached, cached=True)
        if self.session is None:
            return APIResponse(self.provider, False, None, "The requests package is not installed.")

        started = time.time()
        try:
            response = self.session.get(url, params=params, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            self.cache.set(key, data)
            return APIResponse(self.provider, True, data, latency_ms=(time.time() - started) * 1000)
        except Exception as exc:
            logger.warning("%s GET failed: %s", self.provider, exc)
            return APIResponse(self.provider, False, None, str(exc), latency_ms=(time.time() - started) * 1000)

    def _post(
        self,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        cache_key: str | None = None,
    ) -> APIResponse:
        key = cache_key or f"POST:{url}:{json_body}:{headers}"
        cached = self.cache.get(key)
        if cached is not None:
            return APIResponse(self.provider, True, cached, cached=True)
        if self.session is None:
            return APIResponse(self.provider, False, None, "The requests package is not installed.")

        started = time.time()
        try:
            response = self.session.post(url, json=json_body, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            data: Any = response.json() if "json" in content_type else response.content
            self.cache.set(key, data)
            return APIResponse(self.provider, True, data, latency_ms=(time.time() - started) * 1000)
        except Exception as exc:
            logger.warning("%s POST failed: %s", self.provider, exc)
            return APIResponse(self.provider, False, None, str(exc), latency_ms=(time.time() - started) * 1000)


class TavilyService(BaseAPIService):
    provider = "tavily"

    def search(self, query: str, max_results: int = 5) -> APIResponse:
        if not self.configured:
            return self._missing_key()
        return self._post(
            "https://api.tavily.com/search",
            json_body={
                "api_key": self.api_key,
                "query": query,
                "max_results": max_results,
                "include_answer": True,
            },
        )


class OpenWeatherService(BaseAPIService):
    provider = "openweather"

    def current(self, city: str) -> APIResponse:
        if not self.configured:
            return self._missing_key()
        return self._get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": self.api_key, "units": "metric"},
        )


class NewsAPIService(BaseAPIService):
    provider = "newsapi"

    def search(self, query: str, page_size: int = 5) -> APIResponse:
        if not self.configured:
            return self._missing_key()
        return self._get(
            "https://newsapi.org/v2/everything",
            params={"q": query, "pageSize": page_size, "apiKey": self.api_key, "sortBy": "publishedAt"},
        )


class AlphaVantageService(BaseAPIService):
    provider = "alpha_vantage"

    def quote(self, symbol: str) -> APIResponse:
        if not self.configured:
            return self._missing_key()
        return self._get(
            "https://www.alphavantage.co/query",
            params={"function": "GLOBAL_QUOTE", "symbol": symbol.upper(), "apikey": self.api_key},
        )


class YouTubeService(BaseAPIService):
    provider = "youtube"

    def search(self, query: str, max_results: int = 5) -> APIResponse:
        if not self.configured:
            return self._missing_key()
        return self._get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": max_results,
                "key": self.api_key,
            },
        )


class ElevenLabsService(BaseAPIService):
    provider = "elevenlabs"

    def text_to_speech(self, text: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM") -> APIResponse:
        if not self.configured:
            return self._missing_key()
        response = self._post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={"xi-api-key": self.api_key, "Content-Type": "application/json"},
            json_body={"text": text, "model_id": "eleven_multilingual_v2"},
        )
        if response.ok and isinstance(response.data, bytes):
            response.data = {"audio_base64": base64.b64encode(response.data).decode("ascii")}
        return response


class SerpAPIService(BaseAPIService):
    provider = "serpapi"

    def search(self, query: str) -> APIResponse:
        if not self.configured:
            return self._missing_key()
        return self._get("https://serpapi.com/search.json", params={"q": query, "api_key": self.api_key})


class ResendService(BaseAPIService):
    provider = "resend"

    def send_email(self, to: str, subject: str, html: str, sender: str = "JARVIS <onboarding@resend.dev>") -> APIResponse:
        if not self.configured:
            return self._missing_key()
        return self._post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json_body={"from": sender, "to": [to], "subject": subject, "html": html},
        )


class TMDBService(BaseAPIService):
    provider = "tmdb"

    def search_movie(self, query: str) -> APIResponse:
        if not self.configured:
            return self._missing_key()
        return self._get(
            "https://api.themoviedb.org/3/search/movie",
            params={"api_key": self.api_key, "query": query, "page": 1},
        )


class NASAService(BaseAPIService):
    provider = "nasa"

    def apod(self) -> APIResponse:
        if not self.configured:
            return self._missing_key()
        return self._get("https://api.nasa.gov/planetary/apod", params={"api_key": self.api_key})

    def neo_feed(self) -> APIResponse:
        if not self.configured:
            return self._missing_key()
        return self._get("https://api.nasa.gov/neo/rest/v1/feed", params={"api_key": self.api_key})


class FinnhubService(BaseAPIService):
    provider = "finnhub"

    def quote(self, symbol: str) -> APIResponse:
        if not self.configured:
            return self._missing_key()
        return self._get("https://finnhub.io/api/v1/quote", params={"symbol": symbol.upper(), "token": self.api_key})

    def company(self, symbol: str) -> APIResponse:
        if not self.configured:
            return self._missing_key()
        return self._get("https://finnhub.io/api/v1/stock/profile2", params={"symbol": symbol.upper(), "token": self.api_key})


class APINinjasService(BaseAPIService):
    provider = "api_ninjas"

    def facts(self, limit: int = 1) -> APIResponse:
        if not self.configured:
            return self._missing_key()
        return self._get(
            "https://api.api-ninjas.com/v1/facts",
            params={"limit": limit},
            headers={"X-Api-Key": self.api_key},
        )

    def sentiment(self, text: str) -> APIResponse:
        if not self.configured:
            return self._missing_key()
        return self._post(
            "https://api.api-ninjas.com/v1/sentiment",
            headers={"X-Api-Key": self.api_key, "Content-Type": "application/json"},
            json_body={"text": text},
        )


class CalendarificService(BaseAPIService):
    provider = "calendarific"

    def holidays(self, country: str = "IN", year: int | None = None) -> APIResponse:
        if not self.configured:
            return self._missing_key()
        return self._get(
            "https://calendarific.com/api/v2/holidays",
            params={"api_key": self.api_key, "country": country.upper(), "year": year or time.localtime().tm_year},
        )


class APIServiceHub:
    def __init__(self) -> None:
        self.cache = TTLCache()
        self.tavily = TavilyService(config.TAVILY_API_KEY, cache=self.cache)
        self.openweather = OpenWeatherService(config.OPENWEATHER_API_KEY, cache=self.cache)
        self.newsapi = NewsAPIService(config.NEWSAPI_KEY, cache=self.cache)
        self.alpha_vantage = AlphaVantageService(config.ALPHA_VANTAGE_KEY, cache=self.cache)
        self.youtube = YouTubeService(config.YOUTUBE_API_KEY, cache=self.cache)
        self.elevenlabs = ElevenLabsService(config.ELEVENLABS_API_KEY, cache=self.cache)
        self.serpapi = SerpAPIService(config.SERPAPI_KEY, cache=self.cache)
        self.resend = ResendService(config.RESEND_API_KEY, cache=self.cache)
        self.tmdb = TMDBService(config.TMDB_API_KEY, cache=self.cache)
        self.nasa = NASAService(config.NASA_API_KEY, cache=self.cache)
        self.finnhub = FinnhubService(config.FINNHUB_API_KEY, cache=self.cache)
        self.api_ninjas = APINinjasService(config.API_NINJAS_KEY, cache=self.cache)
        self.calendarific = CalendarificService(config.CALENDARIFIC_API_KEY, cache=self.cache)

    def key_status(self) -> dict[str, bool]:
        return {
            "TAVILY_API_KEY": self.tavily.configured,
            "OPENWEATHER_API_KEY": self.openweather.configured,
            "NEWSAPI_KEY": self.newsapi.configured,
            "ALPHA_VANTAGE_KEY": self.alpha_vantage.configured,
            "YOUTUBE_API_KEY": self.youtube.configured,
            "ELEVENLABS_API_KEY": self.elevenlabs.configured,
            "SERPAPI_KEY": self.serpapi.configured,
            "RESEND_API_KEY": self.resend.configured,
            "TMDB_API_KEY": self.tmdb.configured,
            "NASA_API_KEY": self.nasa.configured,
            "FINNHUB_API_KEY": self.finnhub.configured,
            "API_NINJAS_KEY": self.api_ninjas.configured,
            "CALENDARIFIC_API_KEY": self.calendarific.configured,
        }


api_services = APIServiceHub()
